from __future__ import annotations

import os
import string
import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from video_pipeline.config import (
    describe_api_mode,
    get_default_config,
    get_genai_client,
    is_real_api_enabled,
    make_run_directory,
    use_fake_genai,
)
from video_pipeline.fake_genai import FakeGenaiClient
from video_pipeline.images import regenerate_storyboard_images
from video_pipeline.run_pipeline import build_video_from_frames


load_dotenv()

st.set_page_config(page_title="AIアニメーションビルダー", layout="centered")
st.title("AIアニメーションビルダー")

st.markdown(
    "Geminiプロンプト、Gemini 2.5 Flash Image、Veoクリップを組み合わせて、"
    "スタイルが一貫したマルチセグメント動画を生成します。"
)


def _save_uploaded_file(upload) -> Path:
    suffix = Path(upload.name).suffix or ".png"
    temp_dir = Path(tempfile.mkdtemp(prefix="ref_image_"))
    target = temp_dir / f"reference{suffix}"
    target.write_bytes(upload.read())
    return target


state = st.session_state
state.setdefault("run_dir", None)
state.setdefault("prompts_data", None)
state.setdefault("frame_paths", None)
state.setdefault("final_video_path", None)
state.setdefault("selected_frames", [])
state.setdefault("ref_path", None)
state.setdefault("use_fake_mode", use_fake_genai())
state.setdefault("frames", [{"id": "A", "prompt": ""}, {"id": "B", "prompt": ""}])


def _reset_generation_state() -> None:
    state.update(
        run_dir=None,
        prompts_data=None,
        frame_paths=None,
        final_video_path=None,
        selected_frames=[],
        ref_path=None,
    )


def _select_client(use_fake: bool):
    if is_real_api_enabled():
        return get_genai_client()
    if use_fake:
        os.environ["USE_FAKE_GENAI"] = "1"
        return FakeGenaiClient()
    return None


def _render_mode_badge():
    mode = describe_api_mode()
    if mode == "real":
        st.success("モード: REAL API (ENABLE_REAL_GENAI=1)")
    elif mode == "fake" or state.use_fake_mode:
        st.info("モード: オフラインデモ (フェイク出力使用)")
    else:
        st.warning("モード: API無効。リアルまたはフェイクを選択してください。")


_render_mode_badge()

# ---- Single-tab workflow: add/insert frames, per-frame generation, regen, and video build ---- #

real_enabled = is_real_api_enabled()
if not real_enabled:
    state.use_fake_mode = st.checkbox(
        "オフラインデモ（フェイク出力を使用）", value=state.use_fake_mode
    )
    if not state.use_fake_mode:
        st.info("実APIを使う場合は ENABLE_REAL_GENAI=1 をセットしてください。")

ref_file = st.file_uploader("参考画像（任意）", type=["png", "jpg", "jpeg"])


def _ensure_run_dir():
    if state.run_dir is None:
        cfg = get_default_config()
        state.run_dir = make_run_directory(cfg)


def _reindex_frames():
    frames = state.frames
    new_labels = list(string.ascii_uppercase[: len(frames)])
    for frame, lbl in zip(frames, new_labels):
        frame["id"] = lbl
    if state.frame_paths:
        new_paths = {}
        for frame in frames:
            fid = frame["id"]
            new_paths[fid] = state.frame_paths.get(fid, "")
        state.frame_paths = new_paths


col_add, col_ins = st.columns(2)
with col_add:
    new_prompt = st.text_input("末尾に追加するフレーム内容", key="add_prompt")
    if st.button("末尾に追加"):
        state.frames.append({"id": "Z", "prompt": new_prompt, "change_from_previous": ""})
        _reindex_frames()
with col_ins:
    if state.frames:
        positions = [f'{idx+1}: {frame["id"]}' for idx, frame in enumerate(state.frames)]
        pos = st.selectbox("挿入位置を選択", positions, index=0)
        insert_before = positions.index(pos)
        ins_prompt = st.text_input("挿入するフレーム内容", key="insert_prompt")
        if st.button("選択位置の前に挿入"):
            state.frames.insert(
                insert_before, {"id": "Z", "prompt": ins_prompt, "change_from_previous": ""}
            )
            _reindex_frames()

st.markdown("---")
st.subheader("フレーム編集と逐次生成")

if ref_file and state.ref_path is None:
    state.ref_path = _save_uploaded_file(ref_file)

client = _select_client(state.use_fake_mode)
if client is None:
    st.warning("APIモードが未設定です。REALかフェイクを選択してください。")

for idx, frame in enumerate(state.frames):
    with st.container():
        header_col, _ = st.columns([1, 3])
        with header_col:
            st.markdown(f"**Frame {frame['id']}**")

        col_prompt, col_preview = st.columns([2, 1])
        with col_prompt:
            frame["prompt"] = st.text_area(
                "フレーム説明",
                value=frame.get("prompt", ""),
                key=f"prompt_{frame['id']}",
                height=120,
            )
            frame["change_from_previous"] = st.text_input(
                "動き/変化のメモ（任意）",
                value=frame.get("change_from_previous", ""),
                key=f"change_{frame['id']}",
            )

        with col_preview:
            if state.frame_paths and frame["id"] in (state.frame_paths or {}):
                st.image(
                    state.frame_paths.get(frame["id"]),
                    caption=f"Frame {frame['id']} プレビュー",
                )

        st.markdown("---")
        col_regen, col_delete = st.columns(2)
        with col_regen:
            if st.button("このフレームを生成/再生成", key=f"regen_{frame['id']}"):
                if client is None:
                    st.error("APIモードが未設定です。REALかフェイクを選択してください。")
                else:
                    _ensure_run_dir()
                    prompts_data = {"frames": state.frames}
                    frame_paths = state.frame_paths or {}
                    with st.spinner("生成中..."):
                        try:
                            updated_paths = regenerate_storyboard_images(
                                prompts_data,
                                frame_paths,
                                run_dir=state.run_dir,
                                frame_ids=[frame["id"]],
                                ref_image_path=state.ref_path,
                                client=client,
                            )
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"生成に失敗しました: {exc}")
                        else:
                            state.frame_paths = updated_paths
                            state.prompts_data = prompts_data
                            st.success(f"Frame {frame['id']} を生成しました。")
        with col_delete:
            if len(state.frames) > 2 and st.button(
                "このフレームを削除", key=f"delete_{frame['id']}"
            ):
                del state.frames[idx]
                _reindex_frames()
                st.experimental_rerun()

st.subheader("プレビュー一覧")
if state.frame_paths:
    for frame in state.frames:
        frame_id = frame.get("id")
        frame_path = state.frame_paths.get(frame_id) if frame_id else None
        if not frame_path:
            continue
        with st.container():
            st.markdown(f"**Frame {frame_id}**\n\n{frame.get('prompt', '')}")
            st.image(frame_path)
else:
    st.info("生成済みプレビューはまだありません。")

if st.button("すべてのフレームを一括生成"):
    if client is None:
        st.error("APIモードが未設定です。REALかフェイクを選択してください。")
    else:
        _ensure_run_dir()
        prompts_data = {"frames": state.frames}
        with st.spinner("一括生成中..."):
            try:
                updated_paths = regenerate_storyboard_images(
                    prompts_data,
                    state.frame_paths or {},
                    run_dir=state.run_dir,
                    frame_ids=[f["id"] for f in state.frames],
                    ref_image_path=state.ref_path,
                    client=client,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"生成に失敗しました: {exc}")
            else:
                state.frame_paths = updated_paths
                state.prompts_data = prompts_data
                st.success("全フレームを生成しました。")

st.subheader("動画生成")
if st.button("現在のフレームで動画を生成"):
    if client is None:
        st.error("APIモードが未設定です。REALかフェイクを選択してください。")
    elif not state.frame_paths or len(state.frame_paths) < 2:
        st.error("少なくとも2フレームの画像を生成してください。")
    else:
        _ensure_run_dir()
        with st.spinner("動画を生成しています…"):
            try:
                final_path = build_video_from_frames(
                    run_dir=state.run_dir,
                    prompts_data={"frames": state.frames},
                    frame_image_paths=state.frame_paths,
                    client=client,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"動画の生成に失敗しました: {exc}")
            else:
                state.final_video_path = final_path
                st.success("動画生成が完了しました。")

if state.final_video_path:
    st.video(str(state.final_video_path))
    with open(state.final_video_path, "rb") as f:
        st.download_button(
            "動画をダウンロード",
            data=f,
            file_name=Path(state.final_video_path).name,
            mime="video/mp4",
        )
