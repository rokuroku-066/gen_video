from pathlib import Path
from typing import Optional

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
            {"id": "A", "prompt": "alpha", "change_from_previous": None},
            {"id": "B", "prompt": "beta", "change_from_previous": "lifts hand and camera pans right"},
            {"id": "C", "prompt": "gamma", "change_from_previous": "leans closer to camera"},
        ]
    }

    calls: list[tuple[str, Optional[bytes]]] = []

    def fake_generate_image_bytes(prompt_text: str, ref_bytes: Optional[bytes], *, client, cfg):
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

    prompt_text, ref_bytes = calls[0]
    assert ref_bytes == b"A0"  # prior frame bytes anchor regeneration
    assert "Frame B (delta from prior frame)" in prompt_text
    assert "Additional nuance: beta" in prompt_text
    assert "Visible change: lifts hand and camera pans right" in prompt_text
    assert "Force a noticeable shift" in prompt_text
    assert Path(updated["B"]).read_bytes().startswith(b"new-")  # regenerated
    assert Path(updated["C"]).read_bytes() == b"C0"  # untouched frame remains

