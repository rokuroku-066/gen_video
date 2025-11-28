from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def _require_types():
    if types is None:
        raise ImportError(
            "google-genai is required for image generation. Install dependencies from requirements.txt."
        )


def _extract_image_bytes(response) -> bytes:
    parts = getattr(response, "parts", None)
    if not parts:
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                break
    if not parts:
        raise ValueError("Image generation response did not include any parts")
    for part in parts:
        inline_data = getattr(part, "inline_data", None)
        if inline_data and getattr(inline_data, "data", None) is not None:
            return inline_data.data
    raise ValueError("Image generation response did not contain inline_data")


def _generate_image_bytes(
    prompt_text: str,
    ref_bytes: Optional[bytes],
    *,
    client,
    cfg: PipelineConfig,
) -> bytes:
    _require_types()
    contents = []
    if ref_bytes:
        contents.append(types.Part.from_bytes(data=ref_bytes, mime_type="image/png"))
    contents.append(prompt_text)
    response = client.models.generate_content(
        model=cfg.image_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=cfg.aspect_ratio),
        ),
    )
    return _extract_image_bytes(response)


def generate_keyframe_images(
    prompts_data,
    output_dir: Path,
    ref_image_path: Optional[Union[Path, str]] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> Dict[str, str]:
    """
    Generate keyframe images for each frame prompt.
    Returns a mapping of frame_id -> saved image path (as string).
    """
    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    run_dir = Path(output_dir)
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    prev_image_bytes: Optional[bytes] = None
    if ref_image_path:
        prev_image_bytes = Path(ref_image_path).read_bytes()

    frame_paths: Dict[str, str] = {}
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        prompt_text = frame.get("prompt") or ""
        image_bytes = _generate_image_bytes(
            prompt_text,
            prev_image_bytes,
            client=genai_client,
            cfg=cfg,
        )
        image_path = frames_dir / f"frame_{frame_id}.png"
        image_path.write_bytes(image_bytes)
        frame_paths[frame_id] = str(image_path)
        prev_image_bytes = image_path.read_bytes()
    return frame_paths


def regenerate_keyframe_images(
    prompts_data,
    frame_image_paths: Dict[str, str],
    run_dir: Path,
    frame_ids: list[str],
    ref_image_path: Optional[Union[Path, str]] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> Dict[str, str]:
    """
    Regenerate only the specified frame IDs while keeping other frames intact.

    The regeneration uses the latest prior frame (or the reference image for
    frame A) as the stylistic anchor to maintain consistency.
    """

    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    frames_dir = Path(run_dir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    target_ids = set(frame_ids)
    prev_image_bytes: Optional[bytes] = None
    if ref_image_path:
        prev_image_bytes = Path(ref_image_path).read_bytes()

    updated_paths = dict(frame_image_paths)
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        existing_path = Path(frame_image_paths.get(frame_id, frames_dir / f"frame_{frame_id}.png"))
        if not existing_path.exists():
            raise FileNotFoundError(f"Expected existing frame image at {existing_path}")

        if frame_id in target_ids:
            prompt_text = frame.get("prompt") or ""
            image_bytes = _generate_image_bytes(
                prompt_text,
                prev_image_bytes,
                client=genai_client,
                cfg=cfg,
            )
            existing_path.write_bytes(image_bytes)
        else:
            image_bytes = existing_path.read_bytes()

        updated_paths[frame_id] = str(existing_path)
        prev_image_bytes = image_bytes

    return updated_paths
