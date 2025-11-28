from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    from google.genai import types  # type: ignore
except ImportError:  # pragma: no cover - handled at call time
    types = None

from .config import PipelineConfig, get_default_config, get_genai_client


def _make_image_part(path: Path) -> types.Part:
    _require_types()
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def _extract_video_bytes(download) -> bytes:
    if isinstance(download, (bytes, bytearray)):
        return bytes(download)
    for attr in ("content", "data", "payload"):
        value = getattr(download, attr, None)
        if value is not None:
            if isinstance(value, (bytes, bytearray)):
                return bytes(value)
    read_method = getattr(download, "read", None)
    if callable(read_method):
        return read_method()
    raise ValueError("Could not extract bytes from download response")


def _require_types():
    if types is None:
        raise ImportError(
            "google-genai is required for Veo video generation. Install dependencies from requirements.txt."
        )


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

    prompt_text = (
        "Create a short, smooth video segment that starts from the first frame and moves toward the second frame. "
        "Maintain the same character, art style, camera framing, lighting, and world details across the segment. "
        f"Motion description: {motion_description or 'natural, subtle motion continuing the scene.'}"
    )

    _require_types()
    operation = genai_client.models.generate_videos(
        model=cfg.video_model,
        prompt=prompt_text,
        image=_make_image_part(frame1_path),
        config=types.GenerateVideosConfig(
            aspect_ratio=cfg.aspect_ratio,
            duration_seconds=cfg.segment_duration_seconds,
            last_frame=_make_image_part(frame2_path),
        ),
    )

    while not getattr(operation, "done", False):
        time.sleep(5)
        operation = genai_client.operations.get(operation)

    response = getattr(operation, "response", None)
    if not response or not getattr(response, "generated_videos", None):
        raise RuntimeError("Video generation operation did not return generated_videos")

    video_obj = response.generated_videos[0]
    download = genai_client.files.download(file=video_obj.video)
    video_bytes = _extract_video_bytes(download)
    output_path.write_bytes(video_bytes)
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
    clip_paths: List[str] = []
    for idx in range(len(frames) - 1):
        first = frames[idx]
        second = frames[idx + 1]
        first_id = first.get("id") or f"F{idx}"
        second_id = second.get("id") or f"F{idx+1}"
        first_path = Path(frame_image_paths[first_id])
        second_path = Path(frame_image_paths[second_id])
        motion_description = second.get("change_from_previous") or "smooth continuation"
        segment_path = segments_dir / f"segment_{first_id}_{second_id}.mp4"
        generated = generate_segment_for_pair(
            first_path,
            second_path,
            motion_description,
            segment_path,
            client=genai_client,
            config=cfg,
        )
        clip_paths.append(generated)
    return clip_paths
