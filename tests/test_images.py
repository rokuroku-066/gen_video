from pathlib import Path

import pytest

from video_pipeline import images


def test_regenerate_keyframe_images_overwrites_selected(monkeypatch, tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = {
        "A": str(frames_dir / "frame_A.png"),
        "B": str(frames_dir / "frame_B.png"),
        "C": str(frames_dir / "frame_C.png"),
    }
    Path(frame_paths["A"]).write_bytes(b"A0")
    Path(frame_paths["B"]).write_bytes(b"B0")
    Path(frame_paths["C"]).write_bytes(b"C0")

    prompts_data = {
        "frames": [
            {"id": "A", "prompt": "alpha"},
            {"id": "B", "prompt": "beta"},
            {"id": "C", "prompt": "gamma"},
        ]
    }

    calls: list[tuple[str, bytes | None]] = []

    def fake_generate_image_bytes(prompt_text: str, ref_bytes: bytes | None, *, client, cfg):
        calls.append((prompt_text, ref_bytes))
        ref_marker = ref_bytes.decode() if ref_bytes else "none"
        return f"new-{prompt_text}-from-{ref_marker}".encode()

    monkeypatch.setattr(images, "_generate_image_bytes", fake_generate_image_bytes)

    updated = images.regenerate_keyframe_images(
        prompts_data,
        frame_paths,
        run_dir=tmp_path,
        frame_ids=["B"],
        client=object(),
    )

    assert Path(updated["B"]).read_bytes().startswith(b"new-beta")
    assert calls[0] == ("beta", b"A0")  # prior frame bytes anchor regeneration
    assert Path(updated["C"]).read_bytes() == b"C0"  # untouched frame remains

