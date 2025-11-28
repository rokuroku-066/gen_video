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
