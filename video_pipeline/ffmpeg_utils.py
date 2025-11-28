from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Union


def concat_clips(clip_paths: Iterable[Union[str, Path]], output_path: Path) -> str:
    """
    Concatenate MP4 clips using ffmpeg concat demuxer.
    """
    clip_list = [Path(p) for p in clip_paths]
    if not clip_list:
        raise ValueError("No clip paths provided for concatenation")
    for clip in clip_list:
        if not clip.exists():
            raise FileNotFoundError(f"Clip not found: {clip}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as list_file:
        for clip in clip_list:
            list_file.write(f"file '{clip.as_posix()}'\n")
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
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")
    finally:
        list_file_path.unlink(missing_ok=True)
    return str(output_path)
