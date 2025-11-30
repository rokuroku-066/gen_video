# ExecPlan – Add keyframe review & selective regeneration before video creation

This ExecPlan is a living document for this repository. Keep the sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as you work.

If this repository includes PLANS.md, follow all rules and conventions from PLANS.md when editing this document.

## Purpose / Big Picture

Enable a two-stage creation flow: after Gemini 2.5 Flash Image generates keyframes, the user can review them in the Streamlit UI, choose specific frames to regenerate, and only then trigger Veo video generation. This improves visual quality and still targets the core goals of consistent imagery and multi-segment videos.

## Progress

- [x] Capture requirements and create ExecPlan.
- [x] Implement reusable pipeline steps for generating frames and building videos.
- [x] Add selective keyframe regeneration utility.
- [x] Update Streamlit UI to support review/regeneration before video creation.
- [x] Add tests for prompt parsing and regeneration helper behaviors.
- [x] Validate flow with offline-safe tests.

## Surprises & Discoveries

- Prompt parsing helpers in `prompts.py` were missing imports for `json`/`re`; added them to keep tests operational.

## Decision Log

- Plan to expose pipeline in two stages: (1) prompt + keyframe generation, (2) video assembly using confirmed frames.
- Selective regeneration will preserve existing frame files and only overwrite chosen IDs, using the latest preceding frame (or reference image) as the stylistic anchor for consistency.
- Streamlit will keep session state (`prompts`, `frames`, `run_dir`, `ref_image`) to let the user iteratively regenerate frames before launching video generation.

## Outcomes & Retrospective

- Staged pipeline helpers now support separate keyframe review and final video assembly, and the Streamlit UI exposes the new flow with selective regeneration and a simple three-step indicator.
- Regeneration chains reference bytes from the latest prior frame (or the uploaded reference) to keep style anchored while allowing targeted fixes.
- Offline pytest suite passes, covering prompt parsing and regeneration anchoring logic; integration with real APIs still requires a human to set `ENABLE_REAL_GENAI=1`.

## Context and Orientation

Current layout:
- `video_pipeline/run_pipeline.py` orchestrates prompts → keyframes → segments → concat.
- `video_pipeline/images.py` handles Gemini 2.5 Flash Image calls to produce keyframes in `outputs/run_<timestamp>/frames/`.
- `video_pipeline/videos.py` creates Veo segments between consecutive frames.
- `app.py` Streamlit UI directly runs `run_pipeline` with a single "動画を生成" button.

Target change:
- Provide a reusable entrypoint to generate prompts + frames and return their paths without starting video generation.
- Provide a helper to regenerate only selected frames while keeping others intact.
- Offer a UI flow where the user reviews frames, optionally regenerates some, and then triggers video generation.

## Plan of Work

1. Introduce staged pipeline helpers in `video_pipeline/run_pipeline.py` to separate frame creation from video assembly while keeping `run_pipeline` backward compatible.
2. Extend `video_pipeline/images.py` with a selective regeneration function that respects frame ordering and reference anchoring.
3. Update `app.py` UI to manage session state for prompts/frames, display generated images, allow selecting frames for regeneration, and finally build the video using confirmed frames.
4. Add/adjust tests to keep prompt parsing covered and validate regeneration logic with fake clients (offline-safe).
5. Run pytest to ensure regressions are caught.

## Concrete Steps

1. Create helper `generate_initial_frames(...)` in `run_pipeline.py` that wraps prompt generation, run directory creation, and keyframe generation, returning `(run_dir, prompts_data, frame_paths)`.
2. Add helper `build_video_from_frames(...)` that accepts confirmed frames and assembles segments + final MP4; keep `run_pipeline` delegating to these helpers for backward compatibility.
3. In `images.py`, add `regenerate_keyframe_images(...)` that takes `prompts_data`, existing `frame_image_paths`, target `frame_ids`, and regenerates only those IDs while chaining reference bytes from the latest prior frame (or initial reference image). Return updated mapping.
4. Update Streamlit UI flow:
   - Provide a button to generate keyframes (using new helper) and store state (`run_dir`, `prompts_data`, `frame_paths`, `ref_image_path`).
   - Render frames with checkboxes/multiselect for regeneration and a button to regenerate selected frames via `regenerate_keyframe_images`.
   - Add a button to build the video using `build_video_from_frames` once the user is satisfied; display video and download link.
   - Keep the existing notice about `ENABLE_REAL_GENAI` and handle errors gracefully.
5. Extend/adjust tests:
   - Fix missing imports in `prompts.py` to keep JSON parsing operational.
   - Add a unit test for `regenerate_keyframe_images` that uses a fake client returning deterministic bytes to ensure only targeted frames change and chaining uses prior frame bytes.
6. Run `python -m pytest` to verify all tests pass offline.

## Validation and Acceptance

- `python -m pytest` passes without performing real network calls.
- Manually (offline) confirm that generating frames shows them in the UI and that regeneration updates only selected frames (visual verification when real APIs are enabled by a human).
- Final video creation uses the latest regenerated frames and writes `final.mp4` under the same `run_dir`.

## Idempotence and Recovery

- Frame regeneration overwrites only chosen frame files; rerunning regeneration or video assembly on the same `run_dir` should work without cleanup.
- If UI errors occur, clearing Streamlit session state should allow starting a fresh run.

## Artifacts and Notes

- Outputs remain under `outputs/run_<timestamp>/` with `frames/`, `segments/`, and `final.mp4`.

## Interfaces and Dependencies

- No new external dependencies beyond existing `streamlit`, `google-genai`, `ffmpeg` expectations.
- All functions must remain offline-safe by default; real API calls require `ENABLE_REAL_GENAI=1` and are not executed in tests.
