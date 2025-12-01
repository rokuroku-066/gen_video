from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st

from video_pipeline.config import (
    describe_api_mode,
    get_default_config,
    get_genai_client,
    is_real_api_enabled,
    make_run_directory,
    use_fake_genai,
)
from video_pipeline.fake_genai import FakeGenaiClient
from video_pipeline.images import regenerate_keyframe_images
from video_pipeline.run_pipeline import build_video_from_frames, generate_initial_frames


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
state.setdefault("step1_complete", False)
state.setdefault("step2_complete", False)
state.setdefault("step3_complete", False)
state.setdefault("prompt_inputs", {})
state.setdefault("use_fake_mode", use_fake_genai())


def _reset_generation_state() -> None:
    for key in list(state.keys()):
        if str(key).startswith("prompt_input_"):
            del state[key]

    state.update(
        run_dir=None,
        prompts_data=None,
        frame_paths=None,
        final_video_path=None,
        selected_frames=[],
        ref_path=None,
        step1_complete=False,
        step2_complete=False,
        step3_complete=False,
        prompt_inputs={},
    )


def _render_step_indicator() -> None:
    steps = [
        ("1. テーマと設定", True, state.step1_complete),
        ("2. キーフレーム確認・再生成", state.step1_complete, state.step2_complete),
        ("3. 動画生成", state.step2_complete, state.step3_complete),
    ]
    completed = sum(int(complete) for _, __, complete in steps)
    st.progress(completed / len(steps))
    cols = st.columns(len(steps))
    for col, (label, unlocked, complete) in zip(cols, steps):
        status = "✅" if complete else ("🟢" if unlocked else "🔒")
        col.markdown(f"{status} {label}")


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


_render_step_indicator()
_render_mode_badge()

tabs = st.tabs(["テーマと設定", "キーフレーム確認・再生成", "動画生成"])


with tabs[0]:
    theme = st.text_area("テーマ", height=120, placeholder="夜のネオン屋上を歩く小さな妖精...")
    num_frames = st.number_input("キーフレーム数", min_value=2, max_value=8, value=3, step=1)
    motion_hint = st.text_input(
        "動きのヒント（任意）",
        placeholder="カメラがゆっくり寄る、滑らかな動き",
    )
    ref_file = st.file_uploader("参考画像（任意）", type=["png", "jpg", "jpeg"])

    real_enabled = is_real_api_enabled()
    if not real_enabled:
        state.use_fake_mode = st.checkbox(
            "オフラインデモ（フェイク出力を使用）", value=state.use_fake_mode
        )
        if not state.use_fake_mode:
            st.info("実APIを使う場合は ENABLE_REAL_GENAI=1 をセットしてください。")

    if st.button("キーフレームを生成"):
        if not theme.strip():
            st.error("テーマを入力してください。")
        else:
            client = _select_client(state.use_fake_mode)
            if client is None:
                st.error("APIモードが未設定です。REALかフェイクを選択してください。")
            else:
                _reset_generation_state()
                cfg = get_default_config()
                run_dir = make_run_directory(cfg)
                ref_path: Optional[Path] = None
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
                            client=client,
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"画像生成に失敗しました: {exc}")
                    else:
                        state.run_dir = run_dir
                        state.prompts_data = prompts_data
                        state.frame_paths = frame_paths
                        state.ref_path = ref_path
                        state.step1_complete = True
                        state.step2_complete = False
                        state.step3_complete = False
                        st.success("キーフレーム生成が完了しました。レビューしてください。")


with tabs[1]:
    if not state.step1_complete:
        st.info("まず「テーマと設定」タブでキーフレームを生成してください。")

    if state.frame_paths and state.prompts_data:
        st.subheader("生成されたキーフレーム")
        columns = st.columns(2)

        frames = state.prompts_data.get("frames", [])
        for frame in frames:
            frame_id = frame.get("id") or "?"
            prompt_text = frame.get("prompt") or ""
            state.prompt_inputs.setdefault(frame_id, prompt_text)

        for idx, frame in enumerate(frames):
            frame_id = frame.get("id") or "?"
            prompt_text = state.prompt_inputs.get(frame_id, frame.get("prompt") or "")
            with columns[idx % 2]:
                st.image(state.frame_paths.get(frame_id), caption=f"Frame {frame_id}")
                edited_prompt = st.text_area(
                    "再生成用プロンプトを編集",
                    key=f"prompt_input_{frame_id}",
                    value=prompt_text,
                    height=140,
                )
                state.prompt_inputs[frame_id] = edited_prompt
                frame["prompt"] = edited_prompt

        frame_ids = [frame.get("id") or "?" for frame in frames]
        selection = st.multiselect(
            "再生成したいフレームを選択", frame_ids, default=state.get("selected_frames", [])
        )
        state.selected_frames = selection

        if st.button("選択したフレームを再生成", disabled=not selection or not state.step1_complete):
            client = _select_client(state.use_fake_mode)
            if client is None:
                st.error("APIモードが未設定です。REALかフェイクを選択してください。")
            else:
                with st.spinner("フレームを再生成中です…"):
                    try:
                        updated_paths = regenerate_keyframe_images(
                            state.prompts_data,
                            state.frame_paths,
                            run_dir=state.run_dir,
                            frame_ids=selection,
                            ref_image_path=state.ref_path,
                            client=client,
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"再生成に失敗しました: {exc}")
                    else:
                        state.frame_paths = updated_paths
                        state.final_video_path = None
                        state.step2_complete = False
                        state.step3_complete = False
                        st.success("選択したフレームを再生成しました。")

        if st.button("フレーム確認済みとして次へ進む", disabled=not state.step1_complete):
            state.step2_complete = True
            state.step3_complete = False
            st.success("フレーム確認が完了しました。『動画生成』タブへどうぞ。")


with tabs[2]:
    if not state.step2_complete:
        st.info("『キーフレーム確認・再生成』タブでフレーム確認を完了してください。")

    if st.button("レビュー済みフレームで動画を生成", disabled=not state.step2_complete):
        client = _select_client(state.use_fake_mode)
        if client is None:
            st.error("APIモードが未設定です。REALかフェイクを選択してください。")
        else:
            with st.spinner("動画を生成中です。しばらくお待ちください…"):
                try:
                    final_path = build_video_from_frames(
                        run_dir=state.run_dir,
                        prompts_data=state.prompts_data,
                        frame_image_paths=state.frame_paths,
                        client=client,
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"動画の生成に失敗しました: {exc}")
                else:
                    state.final_video_path = final_path
                    state.step3_complete = True
                    st.success("生成が完了しました。")

    if state.final_video_path:
        st.video(str(state.final_video_path))
        with open(state.final_video_path, "rb") as f:
            st.download_button(
                "動画をダウンロード",
                data=f,
                file_name=Path(state.final_video_path).name,
                mime="video/mp4",
            )
