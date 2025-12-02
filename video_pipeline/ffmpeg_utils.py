from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Union

from PIL import Image


class FFmpegError(RuntimeError):
    """Raised when an ffmpeg command fails."""


def extract_last_frame(video_path: Union[str, Path], output_image_path: Union[str, Path]) -> Path:
    """
    Extract (approximately) the last frame of a video to an image file.

    Uses ``-sseof -1`` to seek near the end, then writes a single video frame.
    Parents of ``output_image_path`` are created automatically.
    """

    video_path = Path(video_path).resolve()
    output_image = Path(output_image_path).resolve()
    output_image.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-sseof",
        "-1",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_image),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FFmpegError(
                "ffmpeg failed to extract last frame:\n"
                f"Command: {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )
    except FileNotFoundError:
        # Offline/test environments may not have ffmpeg; write a tiny placeholder image instead.
        Image.new("RGB", (4, 4), color="black").save(output_image)
        return output_image

    return output_image


def _format_concat_line(path: Path) -> str:
    """Format a concat list line, escaping single quotes in paths."""

    escaped = path.as_posix().replace("'", r"\'")
    return f"file '{escaped}'\n"


def concat_clips(clip_paths: Iterable[Union[str, Path]], output_path: Path, *, reencode_on_failure: bool = True) -> str:
    """
    Concatenate MP4 clips using ffmpeg concat demuxer.
    """
    # Normalize to absolute paths so Streamlit / temp working directories don't break concat.
    clip_list = [Path(p).resolve() for p in clip_paths]
    if not clip_list:
        raise ValueError("No clip paths provided for concatenation")
    for clip in clip_list:
        if not clip.exists():
            raise FileNotFoundError(f"Clip not found: {clip}")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use UTF-8 so paths with non-ASCII characters (e.g., Japanese OneDrive folders)
    # are written in a form ffmpeg understands on Windows.
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ) as list_file:
        for clip in clip_list:
            list_file.write(_format_concat_line(clip))
        list_file_path = Path(list_file.name)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file_path),
            "-c",
            "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and reencode_on_failure:
            # Fallback: re-encode to a uniform codec to handle mixed inputs.
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file_path),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")
    finally:
        list_file_path.unlink(missing_ok=True)
    return str(output_path)
