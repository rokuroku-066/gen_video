from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from video_pipeline.config import is_real_api_enabled
from video_pipeline.run_pipeline import run_pipeline


st.set_page_config(page_title="Gemini + Veo Animation Builder", layout="centered")
st.title("Gemini + Veo Animation Builder")

st.markdown(
    "Generate a multi-segment video with consistent style using Gemini prompts, Gemini 2.5 Flash Image, and Veo clips."
)

theme = st.text_area("Theme", height=120, placeholder="A glowing fairy walking on a neon rooftop at night...")
num_frames = st.number_input("Number of keyframes", min_value=2, max_value=8, value=3, step=1)
motion_hint = st.text_input(
    "Motion hint (optional)",
    placeholder="Smooth camera drift, gentle movement toward the viewer",
)
ref_file = st.file_uploader("Reference image (optional)", type=["png", "jpg", "jpeg"])

if not is_real_api_enabled():
    st.info("Real API calls are disabled. Set ENABLE_REAL_GENAI=1 in your environment to run the full pipeline.")


def _save_uploaded_file(upload) -> Path:
    suffix = Path(upload.name).suffix or ".png"
    temp_dir = Path(tempfile.mkdtemp(prefix="ref_image_"))
    target = temp_dir / f"reference{suffix}"
    target.write_bytes(upload.read())
    return target


if st.button("Generate video"):
    if not theme.strip():
        st.error("Please provide a theme before generating.")
    else:
        ref_path: Path | None = None
        if ref_file:
            ref_path = _save_uploaded_file(ref_file)
        with st.spinner("Generating video... this can take a while."):
            try:
                final_path = run_pipeline(
                    theme=theme,
                    num_frames=int(num_frames),
                    ref_image_path=ref_path,
                    motion_hint=motion_hint or None,
                )
            except Exception as exc:  # noqa: BLE001 - display errors in UI
                st.error(f"Failed to generate video: {exc}")
            else:
                st.success("Generation complete!")
                st.video(str(final_path))
                with open(final_path, "rb") as f:
                    st.download_button(
                        "Download video",
                        data=f,
                        file_name=Path(final_path).name,
                        mime="video/mp4",
                    )
