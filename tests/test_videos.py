from pathlib import Path

import pytest

from video_pipeline.fake_genai import FakeGenaiClient
from video_pipeline import videos


def test_generate_all_segments_reuses_last_frame(monkeypatch, tmp_path):
    frames = {
        "A": tmp_path / "A.png",
        "B": tmp_path / "B.png",
        "C": tmp_path / "C.png",
    }
    for path in frames.values():
        path.write_bytes(b"img")

    prompts_data = {
        "frames": [
            {"id": "A", "prompt": "p0"},
            {"id": "B", "prompt": "p1", "change_from_previous": "move1"},
            {"id": "C", "prompt": "p2", "change_from_previous": "move2"},
        ]
    }

    start_images = []

    def fake_generate_segment_for_pair(frame1_path, frame2_path, motion_description, output_path, **kwargs):
        start_images.append(Path(frame1_path))
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"video")
        return str(output)

    last_frame_files = []

    def fake_extract_last_frame(video_path, output_image_path):
        out_path = Path(output_image_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"last")
        last_frame_files.append(out_path)
        return out_path

    monkeypatch.setattr(videos, "generate_segment_for_pair", fake_generate_segment_for_pair)
    monkeypatch.setattr(videos, "extract_last_frame", fake_extract_last_frame)

    results = videos.generate_all_segments(frames, prompts_data, tmp_path, client=FakeGenaiClient())

    assert len(results) == 2
    assert start_images[0] == frames["A"].resolve()
    assert start_images[1] == last_frame_files[0].resolve()


def test_generate_all_segments_requires_two_frames(tmp_path):
    prompts_data = {"frames": [{"id": "A", "prompt": "only one"}]}
    frames = {"A": str(tmp_path / "A.png")}

    with pytest.raises(ValueError):
        videos.generate_all_segments(frames, prompts_data, tmp_path, client=FakeGenaiClient())

