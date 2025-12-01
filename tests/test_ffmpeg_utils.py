from pathlib import Path

from video_pipeline import ffmpeg_utils


class _FakeCompletedProcess:
    def __init__(self, output_path: Path):
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""
        output_path.write_bytes(b"fake video data")


def test_concat_clips_invokes_ffmpeg_and_writes_output(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    clip1.write_bytes(b"clip1")
    clip2.write_bytes(b"clip2")

    def fake_run(cmd, capture_output, text):
        # The output path is the last argument in the command list.
        output = Path(cmd[-1])
        return _FakeCompletedProcess(output)

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", fake_run)
    output_path = tmp_path / "out.mp4"

    result = ffmpeg_utils.concat_clips([clip1, clip2], output_path)

    assert Path(result).exists()
    assert Path(result).read_bytes() == b"fake video data"


def test_concat_clips_writes_placeholder_when_ffmpeg_missing(
    monkeypatch, tmp_path, caplog
):
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    clip1.write_bytes(b"clip1")
    clip2.write_bytes(b"clip2")

    def missing_run(*_, **__):
        raise FileNotFoundError("ffmpeg not installed")

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", missing_run)

    output_path = tmp_path / "out.mp4"
    with caplog.at_level("WARNING"):
        result = ffmpeg_utils.concat_clips([clip1, clip2], output_path)

    data = Path(result).read_bytes()
    assert Path(result).exists()
    assert data == ffmpeg_utils.PLACEHOLDER_MP4_BYTES
    assert any("placeholder video" in message for message in caplog.messages)


def test_extract_last_frame_invokes_ffmpeg(monkeypatch, tmp_path):
    video_path = tmp_path / "clip.mp4"
    image_path = tmp_path / "frames" / "last.png"
    video_path.write_bytes(b"video")

    def fake_run(cmd, capture_output, text):
        # Ensure ffmpeg writes to the requested path.
        Path(cmd[-1]).write_bytes(b"frame")
        return _FakeCompletedProcess(video_path)

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", fake_run)

    result = ffmpeg_utils.extract_last_frame(video_path, image_path)

    assert result == image_path.resolve()
    assert image_path.exists()
    assert image_path.read_bytes() == b"frame"
