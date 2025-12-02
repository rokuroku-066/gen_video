from __future__ import annotations

import json
from pathlib import Path

import video_pipeline.ffmpeg_utils as ffmpeg_utils
from video_pipeline.config import PipelineConfig
from video_pipeline.fake_genai import FakeGenaiClient
from video_pipeline.run_pipeline import run_pipeline


def test_fake_generate_content_text():
    client = FakeGenaiClient()
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=["Frames to produce: A, B"])
    data = json.loads(resp.text)
    assert "frames" in data
    assert len(data["frames"]) >= 2


def test_fake_generate_content_image():
    client = FakeGenaiClient()
    resp = client.models.generate_content(model="gemini-2.5-flash-image", contents=["Frame A baseline"])
    parts = resp.parts
    assert parts
    img_bytes = parts[0].inline_data.data
    assert img_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG signature


def test_fake_generate_videos_and_download(tmp_path):
    client = FakeGenaiClient()
    op = client.models.generate_videos(model="veo-3.1-generate-preview", prompt="demo", config={"duration_seconds": 2})
    assert op.done
    video_path = op.response.generated_videos[0].video
    data = client.files.download(file=video_path)
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 0
    assert Path(video_path).exists()


def test_run_pipeline_with_fake_client(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_FAKE_GENAI", "1")
    client = FakeGenaiClient()
    cfg = PipelineConfig(outputs_root=tmp_path)
    # Avoid depending on system ffmpeg during pipeline smoke test.
    def _fake_concat(clips, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-final-video")
        return str(output_path)

    monkeypatch.setattr(ffmpeg_utils, "concat_clips", _fake_concat)

    final_path = run_pipeline(
        [{"id": "A", "prompt": "demo frame A"}, {"id": "B", "prompt": "demo frame B"}],
        client=client,
        config=cfg,
    )
    assert Path(final_path).exists()
    assert Path(final_path).stat().st_size > 0
