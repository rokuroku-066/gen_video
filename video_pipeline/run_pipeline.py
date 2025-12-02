from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from . import ffmpeg_utils
from .config import PipelineConfig, get_default_config, make_run_directory
from .images import generate_storyboard_images
from .videos import generate_all_segments


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
    frames: list[dict],
    ref_image_path: Optional[Union[Path, str]] = None,
    *,
    client=None,
    config: Optional[PipelineConfig] = None,
) -> str:
    """
    Full pipeline: user-provided frames -> storyboard images -> Veo segments -> concatenated MP4.
    Returns the path to the final video file.
    """
    cfg = config or get_default_config()
    run_dir = make_run_directory(cfg)
    prompts_data = {"frames": frames}
    print(f"[pipeline] generating storyboard images for {len(frames)} frames")
    frame_image_paths = generate_storyboard_images(
        prompts_data,
        run_dir,
        ref_image_path=ref_image_path,
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
