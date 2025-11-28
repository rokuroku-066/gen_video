from __future__ import annotations

import json
import re
import string
from typing import Any, Dict, Optional

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client


def _letters_sequence(count: int) -> list[str]:
    if count < 1:
        return []
    alphabet = list(string.ascii_uppercase)
    if count > len(alphabet):
        raise ValueError("num_frames exceeds supported frame labels")
    return alphabet[:count]


def _build_prompt(theme: str, num_frames: int, motion_hint: Optional[str], has_reference: bool) -> str:
    frame_labels = ", ".join(_letters_sequence(num_frames))
    reference_text = (
        "You are provided with a reference image that anchors the style, character design, and camera."
        " Extract its visual style and keep it consistent across every frame."
    )
    prompt = f"""
You are a storyboard generator for a multi-segment animation.
Goal: produce a sequence of frame prompts that keep the SAME character, art style, camera angle, and world across frames, with only small motion changes between frames.

Theme: {theme}
Frames to produce: {frame_labels}
{"Reference: " + reference_text if has_reference else "No reference image is provided; establish a consistent style yourself and keep it stable."}
Motion direction: {motion_hint or "Use subtle, progressive motion so each frame flows into the next without big jumps."}

Rules:
- Maintain visual consistency: same character identity, clothing, body proportions, lighting mood, color palette, camera lens, and environment.
- Frame A sets the baseline. Each subsequent frame should be a gentle evolution of the previous frame.
- Avoid drastic scene or costume changes; only small pose/motion adjustments.
- Return ONLY JSON. Do not include markdown code fences.

Return JSON of the form:
{{
  "global_style": "<summary of the style and character identity>",
  "frames": [
    {{"id": "A", "prompt": "<detailed image prompt for frame A>", "change_from_previous": null}},
    {{"id": "B", "prompt": "<same style, small motion from A>", "change_from_previous": "<short motion description>"}},
    ...
  ]
}}
"""
    return prompt.strip()


def _extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = re.sub(r"^json", "", cleaned, flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("Model response did not contain JSON content")
    return json.loads(match.group(0))


def _require_types():
    if types is None:
        raise ImportError(
            "google-genai is required for prompt generation with reference images. "
            "Install dependencies from requirements.txt."
        )


def generate_frame_prompts(
    theme: str,
    num_frames: int,
    ref_image_bytes: Optional[bytes] = None,
    motion_hint: Optional[str] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> Dict[str, Any]:
    if num_frames < 2:
        raise ValueError("num_frames must be at least 2")

    cfg = config or get_default_config()
    genai_client = client or get_genai_client()

    instruction = _build_prompt(theme, num_frames, motion_hint, has_reference=ref_image_bytes is not None)
    contents: list[Any] = []
    if ref_image_bytes:
        _require_types()
        contents.append(types.Part.from_bytes(data=ref_image_bytes, mime_type="image/png"))
    contents.append(instruction)

    response = genai_client.models.generate_content(
        model=cfg.text_model,
        contents=contents,
    )

    response_text = getattr(response, "text", "") or ""
    if not response_text:
        # Fallback to parts aggregation if needed.
        maybe_text: list[str] = []
        parts = getattr(response, "parts", None)
        if parts:
            for part in parts:
                text_value = getattr(part, "text", None)
                if text_value:
                    maybe_text.append(text_value)
        else:
            candidates = getattr(response, "candidates", []) or []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                for part in getattr(content, "parts", []) or []:
                    text_value = getattr(part, "text", None)
                    if text_value:
                        maybe_text.append(text_value)
        response_text = "\n".join(maybe_text)
    prompts_data = _extract_json(response_text)

    # Ensure frame IDs exist and are in order; fill missing ids if necessary.
    expected_ids = _letters_sequence(num_frames)
    frames = prompts_data.get("frames") or []
    for idx, expected_id in enumerate(expected_ids):
        if idx < len(frames):
            frames[idx].setdefault("id", expected_id)
            if idx == 0:
                frames[idx].setdefault("change_from_previous", None)
        else:
            frames.append(
                {
                    "id": expected_id,
                    "prompt": f"{theme} frame {expected_id} in consistent style.",
                    "change_from_previous": None if idx == 0 else "continue smoothly",
                }
            )
    prompts_data["frames"] = frames[:num_frames]
    prompts_data.setdefault("global_style", "Consistent character and world across all frames.")
    return prompts_data
