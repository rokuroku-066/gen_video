from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class PipelineConfig:
    text_model: str = "gemini-2.5-flash"
    image_model: str = "gemini-2.5-flash-image"
    video_model: str = "veo-3.1-generate-preview"
    aspect_ratio: str = "16:9"
    # Veo interpolation (first + last frame) requires 8-second segments.
    segment_duration_seconds: int = 8
    outputs_root: Path = Path("outputs")


def get_default_config() -> PipelineConfig:
    return PipelineConfig()


def is_real_api_enabled() -> bool:
    return os.getenv("ENABLE_REAL_GENAI") == "1"


def get_genai_client():
    if not is_real_api_enabled():
        raise RuntimeError(
            "Real Gemini/Veo usage is disabled. Set ENABLE_REAL_GENAI=1 to allow network calls."
        )
    try:
        from google import genai  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "google-genai is required to create a real client. Install dependencies from requirements.txt."
        ) from exc
    return genai.Client()


def make_run_directory(config: Optional[PipelineConfig] = None, run_name: Optional[str] = None) -> Path:
    cfg = config or get_default_config()
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_id = run_name or f"run_{timestamp}"
    run_dir = cfg.outputs_root / run_id
    frames_dir = run_dir / "frames"
    segments_dir = run_dir / "segments"
    frames_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
