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
ref_file = st.file_uploader("参照画像（任意）", type=["png", "jpg", "jpeg"], key="ref_uploader")
st.caption(
    "参照画像はキャラクターや色調の一貫性を保つための手がかりになります。アップロードするとサムネイルが表示されます。"
)

if not is_real_api_enabled():
    st.info("実際のAPI呼び出しは現在無効です。フルパイプラインを動かすには環境変数 ENABLE_REAL_GENAI=1 を設定してください。")


def _save_uploaded_file(filename: str, data: bytes) -> Path:
    suffix = Path(filename).suffix or ".png"
    temp_dir = Path(tempfile.mkdtemp(prefix="ref_image_"))
    target = temp_dir / f"reference{suffix}"
    target.write_bytes(data)
    return target


state = st.session_state
state.setdefault("run_dir", None)
state.setdefault("prompts_data", None)
state.setdefault("frame_paths", None)
state.setdefault("final_video_path", None)
state.setdefault("selected_frames", [])
state.setdefault("ref_path", None)
state.setdefault("ref_preview", None)


def _reset_generation_state():
    for key in ["run_dir", "prompts_data", "frame_paths", "final_video_path", "selected_frames", "ref_path"]:
        state.pop(key, None)


def _sync_ref_preview(upload):
    if upload:
        image_bytes = upload.getvalue()
        state.ref_preview = {
            "bytes": image_bytes,
            "name": upload.name,
            "size_bytes": len(image_bytes),
        }
        state.ref_path = None
        upload.seek(0)
    elif state.get("ref_preview"):
        state.ref_preview = None
        state.ref_path = None


_sync_ref_preview(ref_file)

if state.ref_preview:
    preview_col, meta_col = st.columns([1, 1.2])
    preview_col.image(state.ref_preview["bytes"], caption="参照画像プレビュー", use_column_width=True)
    size_kb = state.ref_preview["size_bytes"] / 1024
    meta_col.markdown(
        f"**{state.ref_preview['name']}**\n\n{size_kb:.1f} KB\n\nアップロードした画像はスタイルの一貫性を保つための基準として使用されます。"
    )


if st.button("キーフレームを生成"):
    if not theme.strip():
        st.error("テーマを入力してください。")
    else:
        _reset_generation_state()
        cfg = get_default_config()
        run_dir = make_run_directory(cfg)
        ref_path: Path | None = None
        if state.ref_preview:
            ref_path = _save_uploaded_file(state.ref_preview["name"], state.ref_preview["bytes"])
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
                ref_image_path = state.ref_path
                if state.ref_preview and not ref_image_path:
                    ref_image_path = _save_uploaded_file(
                        state.ref_preview["name"], state.ref_preview["bytes"]
                    )
                    state.ref_path = ref_image_path
                updated_paths = regenerate_keyframe_images(
                    state.prompts_data,
                    state.frame_paths,
                    run_dir=state.run_dir,
                    frame_ids=selection,
                    ref_image_path=ref_image_path,
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
