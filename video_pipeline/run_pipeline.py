from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from . import ffmpeg_utils
from .config import PipelineConfig, get_default_config, make_run_directory
from .images import generate_storyboard_images
from .prompts import generate_frame_prompts
from .videos import generate_all_segments


def generate_initial_frames(
    theme: str,
    num_frames: int,
    run_dir: Path,
    ref_image_path: Optional[Union[Path, str]] = None,
    motion_hint: Optional[str] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
):
    """
    Generate prompts and storyboard images for a run directory.

    Returns a tuple of (prompts_data, frame_image_paths).
    """
    cfg = config or get_default_config()

    ref_bytes = Path(ref_image_path).read_bytes() if ref_image_path else None
    prompts_data = generate_frame_prompts(
        theme,
        num_frames,
        ref_image_bytes=ref_bytes,
        motion_hint=motion_hint,
        client=client,
        config=cfg,
    )

    frame_image_paths = generate_storyboard_images(
        prompts_data,
        run_dir,
        ref_image_path=ref_image_path,
        client=client,
        config=cfg,
    )
    return prompts_data, frame_image_paths


def build_video_from_frames(
    run_dir: Path,
    prompts_data,
    frame_image_paths,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> str:
    """Generate Veo segments and concatenate them into final.mp4."""
    cfg = config or get_default_config()

    clip_paths = generate_all_segments(
        frame_image_paths,
        prompts_data,
        run_dir,
        client=client,
        config=cfg,
    )

    final_video_path = Path(run_dir) / "final.mp4"
    ffmpeg_utils.concat_clips(clip_paths, final_video_path)
    return str(final_video_path)


def run_pipeline(
    theme: str,
    num_frames: int,
    ref_image_path: Optional[Union[Path, str]] = None,
    motion_hint: Optional[str] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> str:
    """
    Full pipeline: prompts -> storyboard images -> Veo segments -> concatenated MP4.
    Returns the path to the final video file.
    """
    cfg = config or get_default_config()
    run_dir = make_run_directory(cfg)

    print(f"[pipeline] generating prompts for theme='{theme}' frames={num_frames}")
    prompts_data, frame_image_paths = generate_initial_frames(
        theme,
        num_frames,
        run_dir,
        ref_image_path=ref_image_path,
        motion_hint=motion_hint,
        client=client,
        config=cfg,
    )

    print("[pipeline] generating video segments")
    final_video_path = build_video_from_frames(
        run_dir,
        prompts_data,
        frame_image_paths,
        client=client,
        config=cfg,
    )
    print(f"[pipeline] done: {final_video_path}")
    return str(final_video_path)
