from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client, use_fake_genai
from .fake_genai import is_fake_client
from .ffmpeg_utils import extract_last_frame


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def _is_fake_mode(client) -> bool:
    return use_fake_genai() or is_fake_client(client)


def _make_image_input(path: Path, *, client) -> types.Image:
    if _is_fake_mode(client):
        return path
    _require_types(fake_mode=False)
    return types.Image.from_file(
        path=str(path),
        mime_type=_guess_mime_type(path),
    )


def _require_types(fake_mode: bool):
    if fake_mode:
        return
    if types is None:
        raise ImportError(
            "google-genai is required for Veo video generation. Install dependencies from requirements.txt."
        )


def _extract_generated_videos(operation, response):
    """
    Extract generated videos from a completed operation, handling both camelCase and snake_case.
    """
    if response is None:
        return None
    # Attribute-style access (protobuf / SDK objects)
    for attr in ("generated_videos", "generatedVideos", "videos"):
        value = getattr(response, attr, None)
        if value:
            return value
    # Dict-style access (rest/raw responses)
    if isinstance(response, dict):
        for key in ("generated_videos", "generatedVideos", "videos"):
            value = response.get(key)
            if value:
                return value
    return None


def generate_segment_for_pair(
    frame1_path: Path,
    frame2_path: Path,
    motion_description: str,
    output_path: Path,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> str:
    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fake_mode = _is_fake_mode(genai_client)

    prompt_text = (
        "Create a short, smooth video segment that starts from the first frame and moves toward the second frame. "
        "Maintain the same character, art style, camera framing, lighting, and world details across the segment. "
        f"Motion description: {motion_description or 'natural, subtle motion continuing the scene.'}"
    )

    duration_seconds = cfg.segment_duration_seconds
    if fake_mode:
        operation = genai_client.models.generate_videos(
            model=cfg.video_model,
            prompt=prompt_text,
            image=_make_image_input(frame1_path, client=genai_client),
            config={
                "aspect_ratio": cfg.aspect_ratio,
                "duration_seconds": duration_seconds,
                "last_frame": _make_image_input(frame2_path, client=genai_client),
            },
        )
    else:
        _require_types(fake_mode)
        # Veo interpolation mode (image + last_frame) only supports 8-second clips.
        if duration_seconds != 8:
            duration_seconds = 8

        operation = genai_client.models.generate_videos(
            model=cfg.video_model,
            prompt=prompt_text,
            image=_make_image_input(frame1_path, client=genai_client),
            config=types.GenerateVideosConfig(
                aspect_ratio=cfg.aspect_ratio,
                duration_seconds=duration_seconds,
                last_frame=_make_image_input(frame2_path, client=genai_client),
            ),
        )

    while not getattr(operation, "done", False):
        time.sleep(5)
        operation = genai_client.operations.get(operation)

    # Surface explicit backend error if present.
    op_error = getattr(operation, "error", None)
    if op_error is None and isinstance(operation, dict):
        op_error = operation.get("error")
    if op_error:
        raise RuntimeError(f"Veo operation failed: {op_error}")

    response = getattr(operation, "response", None) or getattr(operation, "result", None)
    if response is None and isinstance(operation, dict):
        response = operation.get("response") or operation.get("result")

    generated_videos = _extract_generated_videos(operation, response)
    if not generated_videos:
        debug_keys = []
        if isinstance(response, dict):
            debug_keys = list(response.keys())
        else:
            debug_keys = [attr for attr in dir(response) if not attr.startswith("_")] if response else []
        raise RuntimeError(
            "Video generation operation completed but did not return generated_videos "
            f"(available fields: {debug_keys})"
        )

    video_obj = generated_videos[0]
    genai_client.files.download(file=video_obj.video, download_path=str(output_path))
    return str(output_path)


def generate_all_segments(
    frame_image_paths: Dict[str, str],
    prompts_data,
    output_dir: Path,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> List[str]:
    cfg = config or get_default_config()
    genai_client = client or get_genai_client()
    segments_dir = Path(output_dir) / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    frames = prompts_data.get("frames", [])
    if len(frames) < 2:
        raise ValueError("At least 2 frames are required to generate segments.")

    clip_paths: List[str] = []
    first_frame = frames[0]
    first_id = first_frame.get("id") or "F0"
    try:
        current_start_image = Path(frame_image_paths[first_id])
    except KeyError as exc:
        raise KeyError(f"frame_image_paths is missing image for first frame id={first_id}") from exc

    for idx in range(len(frames) - 1):
        second = frames[idx + 1]
        second_id = second.get("id") or f"F{idx+1}"
        try:
            second_path = Path(frame_image_paths[second_id])
        except KeyError as exc:
            raise KeyError(f"frame_image_paths is missing image for frame id={second_id}") from exc
        motion_description = second.get("change_from_previous") or "smooth continuation"
        segment_path = segments_dir / f"segment_{idx:03d}_{first_id}_{second_id}.mp4"

        generated = generate_segment_for_pair(
            current_start_image,
            second_path,
            motion_description,
            segment_path,
            client=genai_client,
            config=cfg,
        )
        clip_paths.append(generated)

        last_frame_image = segments_dir / f"segment_{idx:03d}_{first_id}_{second_id}_last.png"
        current_start_image = extract_last_frame(Path(generated), last_frame_image)
        first_id = second_id
    return clip_paths
