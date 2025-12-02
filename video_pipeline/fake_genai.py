"""
Offline/demo fake client that mimics the subset of google-genai APIs used in this repo.

It provides:
- models.generate_content for text and image (returns inline PNG bytes for image).
- models.generate_videos for Veo-like calls (creates a tiny MP4 via ffmpeg).
- operations.get returning the same completed operation.
- files.download returning file bytes for a given path.

This is intentionally lightweight and deterministic so tests and demos can run without network
or real API keys. Outputs are clearly synthetic but structurally compatible with the pipeline.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Helper data structures to mirror google-genai response shapes (loosely).


@dataclass
class _InlineData:
    data: bytes


@dataclass
class _Part:
    inline_data: _InlineData


class _ContentResponse:
    def __init__(self, *, text: str | None = None, parts: Optional[List[_Part]] = None):
        self.text = text
        self.parts = parts or []
        self.candidates = []
        if not text and parts:
            # Some callers might look at candidates[0].content.parts; keep minimal shape.
            self.candidates = [type("Cand", (), {"content": type("Content", (), {"parts": parts})()})()]


class _GeneratedVideo:
    def __init__(self, video_path: str):
        self.video = video_path


class _VideoResponse:
    def __init__(self, video_path: str):
        self.generated_videos = [_GeneratedVideo(video_path)]


class _Operation:
    def __init__(self, video_path: str):
        self.done = True
        self.response = _VideoResponse(video_path)
        self.error = None


class _Files:
    @staticmethod
    def download(file: str):
        path = Path(file)
        return path.read_bytes()


class _Operations:
    @staticmethod
    def get(operation: _Operation) -> _Operation:
        return operation


# ---------------------------------------------------------------------------
# Fake media generation helpers


def _deterministic_color(seed: str) -> tuple[int, int, int]:
    # Simple hash to RGB
    h = abs(hash(seed))
    return (50 + h % 205, 50 + (h // 10) % 205, 50 + (h // 100) % 205)


def _make_png(frame_label: str, subtitle: str) -> bytes:
    width, height = 1280, 720
    image = Image.new("RGB", (width, height), _deterministic_color(frame_label + subtitle))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 64)
        small_font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    draw.text((40, 40), f"Frame {frame_label}", fill="white", font=font)
    draw.text((40, 140), subtitle[:80], fill="white", font=small_font)
    buf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    try:
        image.save(buf.name, format="PNG")
        buf.close()
        data = Path(buf.name).read_bytes()
    finally:
        Path(buf.name).unlink(missing_ok=True)
    return data


def _make_fake_video(video_path: Path, duration: int = 2):
    video_path.parent.mkdir(parents=True, exist_ok=True)
    color = "gray"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=1280x720:d={duration}",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    except Exception:
        # Fallback: write dummy bytes; downstream concat may fail, but keeps tests from crashing hard.
        video_path.write_bytes(b"FAKE_VIDEO")
    return video_path


# ---------------------------------------------------------------------------
# Fake models implementation


class _Models:
    def __init__(self, parent: "FakeGenaiClient"):
        self._parent = parent

    def generate_content(self, model: str, contents: List[Any], config: Any | None = None):
        # Determine if this is image or text based on config.response_modalities or model name.
        is_image = False
        if config and getattr(config, "response_modalities", None):
            mods = getattr(config, "response_modalities")
            is_image = "IMAGE" in mods
        if "image" in model:
            is_image = True

        if is_image:
            prompt_text = ""
            for item in contents:
                if isinstance(item, str):
                    prompt_text = item
            label = "?"
            change = "delta"
            if prompt_text:
                # Crude parse to extract "Frame X" and "Visible change: ..."
                for token in prompt_text.split():
                    if token.upper() in {"A", "B", "C", "D", "E", "F"}:
                        label = token.upper()
                        break
                if "Frame" in prompt_text:
                    parts = prompt_text.split("Frame")
                    if len(parts) > 1:
                        maybe = parts[1].strip().split()[0].strip(":")
                        if maybe:
                            label = maybe[0].upper()
                if "Visible change:" in prompt_text:
                    change = prompt_text.split("Visible change:")[1].split("\n")[0].strip()
            data = _make_png(label, change)
            return _ContentResponse(parts=[_Part(_InlineData(data))])

        # Text generation path: build deterministic JSON
        prompt_text = ""
        for item in contents:
            if isinstance(item, str):
                prompt_text = item
        frame_labels = ["A", "B", "C"]
        if "Frames to produce:" in prompt_text:
            try:
                segment = prompt_text.split("Frames to produce:")[1].splitlines()[0]
                frame_labels = [f.strip() for f in segment.split(",") if f.strip()]
            except Exception:
                frame_labels = ["A", "B", "C"]
        frames = []
        for idx, lbl in enumerate(frame_labels):
            if idx == 0:
                frames.append({"id": lbl, "prompt": f"Baseline for {lbl}", "change_from_previous": None})
            else:
                frames.append(
                    {
                        "id": lbl,
                        "prompt": f"Delta for {lbl}",
                        "change_from_previous": f"motion beat {idx}",
                    }
                )
        text = json.dumps({"frames": frames})
        return _ContentResponse(text=text)

    def generate_videos(self, model: str, prompt: str, image: Any = None, config: Any | None = None, **kwargs):
        duration = 2
        aspect_ratio = "16:9"
        if isinstance(config, dict):
            duration = config.get("duration_seconds", duration)
            aspect_ratio = config.get("aspect_ratio", aspect_ratio)
        else:
            duration = getattr(config, "duration_seconds", duration) or duration
            aspect_ratio = getattr(config, "aspect_ratio", aspect_ratio) or aspect_ratio
        # Ensure consistent output path
        tmp_dir = Path(tempfile.mkdtemp(prefix="fake_video_"))
        file_path = tmp_dir / "segment.mp4"
        # Keep duration small to speed up tests
        _make_fake_video(file_path, duration=min(duration, 3))
        return _Operation(str(file_path))


# ---------------------------------------------------------------------------
# Public fake client


class FakeGenaiClient:
    """
    Drop-in stand-in for google.genai.Client used in tests and offline demos.
    """

    def __init__(self):
        # Ensure config.use_fake_genai() sees fake mode even if the caller forgets to set the env var.
        os.environ["USE_FAKE_GENAI"] = "1"
        self.is_fake_genai = True
        self.models = _Models(self)
        self.operations = _Operations()
        self.files = _Files()


def is_fake_client(obj: Any) -> bool:
    return getattr(obj, "is_fake_genai", False)
