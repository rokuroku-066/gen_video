from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Union

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client, use_fake_genai
from .fake_genai import is_fake_client


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def _is_fake_mode(client) -> bool:
    return use_fake_genai() or is_fake_client(client)


def _require_types(fake_mode: bool):
    if fake_mode:
        return
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


def _compose_image_prompt(frame: dict) -> str:
    """
    Use the frame prompt produced by prompts.py as-is (minimal additions).
    Fallback to change_from_previous if prompt text is missing.
    """
    base_prompt = frame.get("prompt") or ""
    if base_prompt:
        return base_prompt
    change = frame.get("change_from_previous")
    return change or "incremental change from previous frame"


def _generate_image_bytes(
    prompt_text: str,
    ref_images: Optional[Sequence[bytes]],
    *,
    client,
    cfg: PipelineConfig,
) -> bytes:
    fake_mode = _is_fake_mode(client)
    _require_types(fake_mode)
    contents = []
    for ref_bytes in ref_images or []:
        if fake_mode:
            contents.append(ref_bytes)
        else:
            contents.append(types.Part.from_bytes(data=ref_bytes, mime_type="image/png"))
    contents.append(prompt_text)
    response = client.models.generate_content(
        model=cfg.image_model,
        contents=contents,
        config=None
        if fake_mode
        else types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=cfg.aspect_ratio),
        ),
    )
    return _extract_image_bytes(response)


def generate_storyboard_images(
    prompts_data,
    output_dir: Path,
    ref_image_path: Optional[Union[Path, str]] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> Dict[str, str]:
    """
    Generate storyboard images for each frame prompt.
    Returns a mapping of frame_id -> saved image path (as string).
    """
    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    run_dir = Path(output_dir)
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    reference_images: list[bytes] = []
    if ref_image_path:
        reference_images.append(Path(ref_image_path).read_bytes())

    generated_images: list[bytes] = []

    frame_paths: Dict[str, str] = {}
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        prompt_text = _compose_image_prompt(frame)
        image_bytes = _generate_image_bytes(
            prompt_text,
            reference_images + generated_images,
            client=genai_client,
            cfg=cfg,
        )
        image_path = frames_dir / f"frame_{frame_id}.png"
        image_path.write_bytes(image_bytes)
        frame_paths[frame_id] = str(image_path)
        generated_images.append(image_bytes)
    return frame_paths


def regenerate_storyboard_images(
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

    The regeneration uses all prior frames (plus the optional reference image for
    frame A) as stylistic anchors to maintain consistency.
    """

    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    frames_dir = Path(run_dir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    target_ids = set(frame_ids)
    reference_images: list[bytes] = []
    if ref_image_path:
        reference_images.append(Path(ref_image_path).read_bytes())

    generated_images: list[bytes] = []

    updated_paths = dict(frame_image_paths)
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        existing_path = Path(frame_image_paths.get(frame_id, frames_dir / f"frame_{frame_id}.png"))
        if not existing_path.exists():
            raise FileNotFoundError(f"Expected existing frame image at {existing_path}")

        if frame_id in target_ids:
            prompt_text = _compose_image_prompt(frame)
            image_bytes = _generate_image_bytes(
                prompt_text,
                reference_images + generated_images,
                client=genai_client,
                cfg=cfg,
            )
            existing_path.write_bytes(image_bytes)
        else:
            image_bytes = existing_path.read_bytes()

        updated_paths[frame_id] = str(existing_path)
        generated_images.append(image_bytes)

    return updated_paths
