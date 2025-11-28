from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from video_pipeline.config import get_default_config, is_real_api_enabled, make_run_directory
from video_pipeline.images import regenerate_keyframe_images
from video_pipeline.run_pipeline import build_video_from_frames, generate_initial_frames


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


state = st.session_state

_STATE_DEFAULTS: dict[str, object | None] = {
    "run_dir": None,
    "prompts_data": None,
    "frame_paths": None,
    "final_video_path": None,
    "selected_frames": [],
    "ref_path": None,
}


def _ensure_session_defaults() -> None:
    for key, value in _STATE_DEFAULTS.items():
        state.setdefault(key, value)


_ensure_session_defaults()


def _reset_generation_state() -> None:
    for key, value in _STATE_DEFAULTS.items():
        # Replace with fresh defaults so downstream attribute access is safe even after failures.
        # Lists get re-created to avoid sharing instances across resets.
        state[key] = [] if isinstance(value, list) else value


if st.button("キーフレームを生成"):
    if not theme.strip():
        st.error("テーマを入力してください。")
    else:
        _reset_generation_state()
        cfg = get_default_config()
        run_dir = make_run_directory(cfg)
        ref_path: Path | None = None
        if ref_file:
            ref_path = _save_uploaded_file(ref_file)
        with st.spinner("キーフレームを生成中です…"):
            try:
                prompts_data, frame_paths = generate_initial_frames(
                    theme=theme,
                    num_frames=int(num_frames),
                    run_dir=run_dir,
                    ref_image_path=ref_path,
                    motion_hint=motion_hint or None,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"画像の生成に失敗しました: {exc}")
            else:
                state.run_dir = run_dir
                state.prompts_data = prompts_data
                state.frame_paths = frame_paths
                state.ref_path = ref_path
                st.success("キーフレームの生成が完了しました。レビューしてください。")


if state.frame_paths and state.prompts_data:
    st.subheader("生成されたキーフレーム")
    columns = st.columns(2)
    for idx, frame in enumerate(state.prompts_data.get("frames", [])):
        frame_id = frame.get("id") or "?"
        prompt_text = frame.get("prompt") or ""
        with columns[idx % 2]:
            st.image(state.frame_paths.get(frame_id), caption=f"Frame {frame_id}")
            st.caption(prompt_text)

    frame_ids = [frame.get("id") or "?" for frame in state.prompts_data.get("frames", [])]
    selection = st.multiselect(
        "再生成したいフレームを選択", frame_ids, default=state.get("selected_frames", [])
    )
    state.selected_frames = selection

    if st.button("選択したフレームを再生成", disabled=not selection):
        with st.spinner("フレームを再生成中です…"):
            try:
                updated_paths = regenerate_keyframe_images(
                    state.prompts_data,
                    state.frame_paths,
                    run_dir=state.run_dir,
                    frame_ids=selection,
                    ref_image_path=state.ref_path,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"再生成に失敗しました: {exc}")
            else:
                state.frame_paths = updated_paths
                state.final_video_path = None
                st.success("選択したフレームを再生成しました。")

    if st.button("レビュー済みフレームで動画を生成"):
        with st.spinner("動画を生成中です。しばらくお待ちください。"):
            try:
                final_path = build_video_from_frames(
                    run_dir=state.run_dir,
                    prompts_data=state.prompts_data,
                    frame_image_paths=state.frame_paths,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"動画の生成に失敗しました: {exc}")
            else:
                state.final_video_path = final_path
                st.success("生成が完了しました！")

if state.final_video_path:
    st.video(str(state.final_video_path))
    with open(state.final_video_path, "rb") as f:
        st.download_button(
            "動画をダウンロード",
            data=f,
            file_name=Path(state.final_video_path).name,
            mime="video/mp4",
        )
