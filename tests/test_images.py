from pathlib import Path
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

    calls: list[tuple[str, list[bytes]]] = []

    def fake_generate_image_bytes(
        prompt_text: str, ref_images: list[bytes], *, client, cfg
    ):
        calls.append((prompt_text, ref_images))
        ref_marker = "-".join(img.decode() for img in ref_images) if ref_images else "none"
        return f"new-{prompt_text}-from-{ref_marker}".encode()

    monkeypatch.setattr(images, "_generate_image_bytes", fake_generate_image_bytes)

    updated = images.regenerate_keyframe_images(
        prompts_data,
        frame_paths,
        run_dir=tmp_path,
        frame_ids=["B"],
        client=object(),
    )

    prompt_text, ref_images = calls[0]
    assert ref_images == [b"A0"]  # all prior frame bytes anchor regeneration
    assert "Frame B (delta from prior frame)" in prompt_text
    assert "Additional nuance: beta" in prompt_text
    assert "Visible change: lifts hand and camera pans right" in prompt_text
    assert "Force a noticeable shift" in prompt_text
    assert Path(updated["B"]).read_bytes().startswith(b"new-")  # regenerated
    assert Path(updated["C"]).read_bytes() == b"C0"  # untouched frame remains


def test_generate_keyframe_images_accumulates_references(monkeypatch, tmp_path):
    prompts_data = {
        "frames": [
            {"id": "A", "prompt": "alpha"},
            {"id": "B", "prompt": "beta", "change_from_previous": "moves"},
            {"id": "C", "prompt": "gamma", "change_from_previous": "turns"},
        ]
    }
    ref_path = tmp_path / "ref.png"
    ref_path.write_bytes(b"REF")

    generated_lookup = {"A": b"img-A", "B": b"img-B", "C": b"img-C"}
    calls: list[tuple[str, list[bytes]]] = []

    def fake_generate_image_bytes(prompt_text: str, ref_images: list[bytes], *, client, cfg):
        frame_label = "?"
        if "Frame" in prompt_text:
            frame_label = prompt_text.split("Frame")[1].strip().split()[0].strip(":")[0]
        calls.append((frame_label, list(ref_images)))
        return generated_lookup[frame_label]

    monkeypatch.setattr(images, "_generate_image_bytes", fake_generate_image_bytes)

    images.generate_keyframe_images(
        prompts_data,
        output_dir=tmp_path,
        ref_image_path=ref_path,
        client=object(),
    )

    assert calls[0] == ("A", [b"REF"])
    assert calls[1] == ("B", [b"REF", b"img-A"])
    assert calls[2] == ("C", [b"REF", b"img-A", b"img-B"])

