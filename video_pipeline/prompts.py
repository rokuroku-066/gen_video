from __future__ import annotations

import json
import re
import string
from typing import Any, Dict, Optional

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client, use_fake_genai


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
        "You are provided with a reference image that anchors the look for frame A."
        " Extract its visual style for frame A, then only describe deltas afterward."
    )
    prompt = f"""
You are a storyboard generator for a multi-segment animation.
Goal: produce a sequence of frame prompts. Frame A defines the baseline; every subsequent frame MUST show BOTH (a) a clear character pose/gesture/action change AND (b) a visible background/camera/environment change from the previous frame. No static backgrounds or frozen characters.

Theme: {theme}
Frames to produce: {frame_labels}
{"Reference: " + reference_text if has_reference else "No reference image is provided; establish the baseline in frame A."}
Motion direction: {motion_hint or "Plan a progressive motion arc spread across the whole sequence, not just the last frame."}

Rules:
- Each frame represents an 8-second interval in the movie.
- Frame A: full description (shot, composition, subject, environment) to establish the baseline.
- Each subsequent frame: describe ONLY the visible change from the previous frame (pose/action, camera move like pan/tilt/dolly/orbit/closer/wider, environment evolution like fog shifts, lighting changes, parallax). Avoid restating the baseline.
- For frames B onward: include BOTH a character motion change (pose/gesture) AND a background or camera change (lighting/weather/props/parallax/angle). Frames that keep either element static are not allowed.
- Changes must be obvious at a glance; avoid near-duplicates; never reuse the same camera angle twice in a row.
- Use "change_from_previous" to capture the specific visible change in 5-12 words; the frame prompt should focus on that delta, not repeat the whole scene.
- Return ONLY JSON. Do not include markdown code fences.

Return JSON of the form:
{{
  "frames": [
    {{"id": "A", "prompt": "<baseline description>", "change_from_previous": null}},
    {{"id": "B", "prompt": "<only the delta from frame A>", "change_from_previous": "<short motion/environment/camera change>"}},
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
    if use_fake_genai():
        return
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
        if not use_fake_genai():
            _require_types()
            contents.append(types.Part.from_bytes(data=ref_image_bytes, mime_type="image/png"))
        else:
            contents.append(ref_image_bytes)
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
                frames[idx].setdefault(
                    "change_from_previous",
                    "visible pose/camera/environment change from the previous frame",
                )
        else:
            frames.append(
                {
                    "id": expected_id,
                    "prompt": f"{theme} frame {expected_id} in consistent style.",
                    "change_from_previous": None
                    if idx == 0
                    else "visible pose/camera/environment change from the previous frame",
                }
            )
    prompts_data["frames"] = frames[:num_frames]
    return prompts_data
