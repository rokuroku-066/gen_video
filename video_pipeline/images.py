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
    """
    Attempt to pull inline image bytes from various google-genai response shapes.
    Falls back to common dict representations as well.
    """
    # Direct bytes
    if isinstance(response, (bytes, bytearray)):
        return response

    # Attributes-based (SDK objects)
    parts = getattr(response, "parts", None)
    if not parts:
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if parts:
                break
    if parts:
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None) is not None:
                return inline_data.data

    # Dict-based responses
    if isinstance(response, dict):
        # direct inline_data
        inline = response.get("inline_data") or response.get("inlineData")
        if inline:
            data = inline.get("data") if isinstance(inline, dict) else None
            if data:
                return data
        # candidates path
        for cand in response.get("candidates", []) or []:
            content = cand.get("content") or {}
            for part in content.get("parts", []) or []:
                if isinstance(part, dict):
                    inline = part.get("inline_data") or part.get("inlineData")
                    if inline:
                        data = inline.get("data") if isinstance(inline, dict) else None
                        if data:
                            return data
        # generated_images style
        for key in ("images", "generated_images", "generatedImages"):
            imgs = response.get(key)
            if imgs and isinstance(imgs, list):
                first = imgs[0]
                if isinstance(first, (bytes, bytearray)):
                    return first
                if isinstance(first, dict):
                    data = first.get("data")
                    if data:
                        return data

    debug_keys = []
    if isinstance(response, dict):
        debug_keys = list(response.keys())
    elif response is not None:
        debug_keys = [attr for attr in dir(response) if not attr.startswith("_")]
    raise ValueError(
        "Image generation response did not include any parts/inline_data "
        f"(type={type(response)}, keys={debug_keys})"
    )


def _compose_image_prompt(frame: dict) -> str:
    """
    Use the frame prompt provided by the user (minimal additions).
    Fallback to change_from_previous if prompt text is missing.
    """
    base_prompt = frame.get("prompt") or ""
    if base_prompt:
        return base_prompt
    change = frame.get("change_from_previous")
    return change or "incremental change from previous frame"


def _generate_image_bytes(
    prompt_text: str,
    ref_images: Optional[Sequence[Union[bytes, tuple[bytes, str]]]],
    *,
    client,
    cfg: PipelineConfig,
    max_attempts: int = 2,
) -> bytes:
    fake_mode = _is_fake_mode(client)
    _require_types(fake_mode)
    contents = []
    for ref in ref_images or []:
        ref_bytes, mime = (ref, "image/png") if isinstance(ref, (bytes, bytearray)) else ref
        if fake_mode:
            contents.append(ref_bytes)
        else:
            contents.append(types.Part.from_bytes(data=ref_bytes, mime_type=mime))
    contents.append(prompt_text)
    modality = None
    if not fake_mode and hasattr(types, "Modality"):
        modality = types.Modality.IMAGE

    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=cfg.image_model,
                contents=contents,
                config=None
                if fake_mode
                else types.GenerateContentConfig(
                    response_modalities=[modality] if modality else ["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=cfg.aspect_ratio),
                ),
            )
            return _extract_image_bytes(response)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue

    assert last_exc is not None
    raise last_exc


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
        ref_path = Path(ref_image_path)
        reference_images.append(ref_path.read_bytes())

    generated_images: list[bytes] = []

    frame_paths: Dict[str, str] = {}
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        prompt_text = _compose_image_prompt(frame)
        ref_list = list(reference_images) + list(generated_images)
        image_bytes = _generate_image_bytes(
            prompt_text,
            ref_list,
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
    Regenerate (or generate if missing) only the specified frame IDs while keeping other frames intact.

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
        ref_path = Path(ref_image_path)
        reference_images.append(ref_path.read_bytes())

    generated_images: list[bytes] = []

    updated_paths = dict(frame_image_paths)
    frames = prompts_data.get("frames", [])
    for frame in frames:
        frame_id = frame.get("id") or "X"
        existing_path = Path(frame_image_paths.get(frame_id, frames_dir / f"frame_{frame_id}.png"))
        needs_generate = frame_id in target_ids or not existing_path.exists()

        if needs_generate:
            prompt_text = _compose_image_prompt(frame)
            ref_list = list(reference_images) + list(generated_images)
            image_bytes = _generate_image_bytes(
                prompt_text,
                ref_list,
                client=genai_client,
                cfg=cfg,
            )
            existing_path.parent.mkdir(parents=True, exist_ok=True)
            existing_path.write_bytes(image_bytes)
        else:
            image_bytes = existing_path.read_bytes()

        updated_paths[frame_id] = str(existing_path)
        generated_images.append(image_bytes)

    return updated_paths
