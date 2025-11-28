from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from video_pipeline.config import is_real_api_enabled
from video_pipeline.run_pipeline import run_pipeline


st.set_page_config(page_title="Gemini + Veo アニメーションビルダー", layout="centered")
st.title("Gemini + Veo アニメーションビルダー")

st.markdown(
    "Geminiプロンプト、Gemini 2.5 Flash Image、Veoクリップを使って、スタイルが一貫したマルチセグメント動画を生成します。"
)

theme = st.text_area("テーマ", height=120, placeholder="夜のネオン屋上を歩く光る妖精...")
num_frames = st.number_input("キーフレーム数", min_value=2, max_value=8, value=3, step=1)
motion_hint = st.text_input(
    "動きのヒント（任意）",
    placeholder="カメラがゆっくり寄る／滑らかな動き",
)
ref_file = st.file_uploader("参照画像（任意）", type=["png", "jpg", "jpeg"])

if not is_real_api_enabled():
    st.info("実際のAPI呼び出しは現在無効です。フルパイプラインを動かすには環境変数 ENABLE_REAL_GENAI=1 を設定してください。")


def _save_uploaded_file(upload) -> Path:
    suffix = Path(upload.name).suffix or ".png"
    temp_dir = Path(tempfile.mkdtemp(prefix="ref_image_"))
    target = temp_dir / f"reference{suffix}"
    target.write_bytes(upload.read())
    return target


if st.button("動画を生成"):
    if not theme.strip():
        st.error("テーマを入力してください。")
    else:
        ref_path: Path | None = None
        if ref_file:
            ref_path = _save_uploaded_file(ref_file)
        with st.spinner("動画を生成中です。しばらくお待ちください。"):
            try:
                final_path = run_pipeline(
                    theme=theme,
                    num_frames=int(num_frames),
                    ref_image_path=ref_path,
                    motion_hint=motion_hint or None,
                )
            except Exception as exc:  # noqa: BLE001 - display errors in UI
                st.error(f"動画の生成に失敗しました: {exc}")
            else:
                st.success("生成が完了しました！")
                st.video(str(final_path))
                with open(final_path, "rb") as f:
                    st.download_button(
                        "動画をダウンロード",
                        data=f,
                        file_name=Path(final_path).name,
                        mime="video/mp4",
                    )
