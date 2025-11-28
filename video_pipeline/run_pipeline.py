from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .config import PipelineConfig, get_default_config, make_run_directory
from .ffmpeg_utils import concat_clips
from .images import generate_keyframe_images
from .prompts import generate_frame_prompts
from .videos import generate_all_segments


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
    Full pipeline: prompts -> keyframe images -> Veo segments -> concatenated MP4.
    Returns the path to the final video file.
    """
    cfg = config or get_default_config()
    run_dir = make_run_directory(cfg)

    ref_bytes = Path(ref_image_path).read_bytes() if ref_image_path else None

    print(f"[pipeline] generating prompts for theme='{theme}' frames={num_frames}")
    prompts_data = generate_frame_prompts(
        theme,
        num_frames,
        ref_image_bytes=ref_bytes,
        motion_hint=motion_hint,
        client=client,
        config=cfg,
    )

    print("[pipeline] generating keyframe images")
    frame_image_paths = generate_keyframe_images(
        prompts_data,
        run_dir,
        ref_image_path=ref_image_path,
        client=client,
        config=cfg,
    )

    print("[pipeline] generating video segments")
    clip_paths = generate_all_segments(
        frame_image_paths,
        prompts_data,
        run_dir,
        client=client,
        config=cfg,
    )

    final_video_path = Path(run_dir) / "final.mp4"
    print("[pipeline] concatenating clips")
    concat_clips(clip_paths, final_video_path)
    print(f"[pipeline] done: {final_video_path}")
    return str(final_video_path)
