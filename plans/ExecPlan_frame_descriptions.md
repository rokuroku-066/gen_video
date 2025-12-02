# ExecPlan – Accept per-frame descriptions instead of a single theme

This ExecPlan is a living document for this repository. Keep the sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as you work.

If this repository includes PLANS.md, follow all rules and conventions from PLANS.md when editing this document.

## Purpose / Big Picture

Let users provide **frame-by-frame descriptions** up front (e.g., “A: wide establishing city shot”, “B: hero turns to camera”) instead of one global theme. The system should still produce consistent storyboards and multi-segment videos while respecting those per-frame inputs and the optional reference image.

## Progress

- [x] 2025-12-02 Created plan and captured goal.
- [x] 2025-12-02 Updated prompt builder and pipeline signatures to accept per-frame descriptions.
- [x] 2025-12-02 Updated Streamlit UI to collect per-frame descriptions and pass them through.
- [x] 2025-12-02 Refreshed docs (README/AGENTS/PLANS) and automated tests to match the new inputs.
- [x] 2025-12-02 Ran offline-safe validation (`python -m pytest`) and captured next manual check guidance.

## Surprises & Discoveries

- None yet.

## Decision Log

- Replace the single `theme` input with an ordered list of per-frame descriptions while keeping `change_from_previous` in the JSON so video segments still know the motion between frames.
- Removed the optional `motion_hint`; per-frame descriptions alone drive motion and camera progression.
- Preserve API gating: real Gemini/Veo calls only when `ENABLE_REAL_GENAI=1`; default flows use the fake client.

## Outcomes & Retrospective

- Per-frame descriptions now flow through prompts → images → segments, with UI, docs, and tests aligned. Offline pytest passes; real API run remains optional when `ENABLE_REAL_GENAI=1`.

## Context and Orientation

Relevant files:
- (Deprecated) `video_pipeline/prompts.py` – no longer used; user supplies frame prompts directly.
- `video_pipeline/run_pipeline.py` – orchestrates prompts → storyboards → segments → final MP4.
- `app.py` – Streamlit UI (collects per-frame descriptions).
- `README.md`, `AGENTS.md` – describe usage and expected inputs.
- Tests: `tests/test_fake_genai.py` (and image/video tests) cover the current user-supplied frame flow.

## Plan of Work

1. Redesign `generate_frame_prompts` to accept a list of frame descriptions, generate IDs (A, B, …), and instruct Gemini to return structured prompts with `change_from_previous`.
2. Adjust pipeline helpers (`generate_initial_frames`, `run_pipeline`) to take the new input shape and remove reliance on `num_frames` except for validation.
3. Update Streamlit UI step 1 to render per-frame description text areas based on the chosen frame count and send that list to the pipeline.
4. Refresh docs (README, AGENTS) to explain the new input flow and sample code.
5. Update/align tests to the new signatures and run pytest (offline/fake clients).

## Concrete Steps

- Remove prompt-generation module usage; rely on user-supplied frame descriptions end to end.
- Update `run_pipeline.py` to pass the list of descriptions through to prompt/image generation and to derive frame count from that list.
- Revise `app.py` step 1 to collect per-frame descriptions (text areas per frame) instead of a single theme string; propagate them to `generate_initial_frames`.
- Update docs (`README.md`, `AGENTS.md`) and any referenced sample code to reflect per-frame inputs.
- Fix tests (`tests/test_fake_genai.py`, others if needed) for the new signatures and expectations.
- Run `python -m pytest`; note manual UI check guidance for real API mode.

## Validation and Acceptance

- Automated: `python -m pytest` passes without hitting real APIs (use fake client by default).
- Manual (optional, requires `ENABLE_REAL_GENAI=1`): run `streamlit run app.py`, enter per-frame descriptions, optionally upload a reference image, confirm storyboards follow the provided descriptions, and the final video concatenates segments.

## Idempotence and Recovery

- Rerunning with the same inputs creates a new `run_<timestamp>`; previous outputs remain intact.
- If a frame regeneration or segment build fails, re-run just that step (existing helpers already support regenerating selected frames and rebuilding the final video).

## Artifacts and Notes

- Outputs remain under `outputs/run_<timestamp>/frames/` and `segments/` with `final.mp4` in the same run directory.
- Keep `USE_FAKE_GENAI=1` for tests/demos to avoid real API usage.

## Interfaces and Dependencies

- `generate_frame_prompts(frame_descriptions, ref_image_bytes=None, client=None, config=None) -> dict` returns `{"frames": [{"id": "A", "prompt": "...", "change_from_previous": "..."}]}`.
- Pipeline entry: `run_pipeline(frame_descriptions, ref_image_path=None, client=None, config=None)`; frame count is derived from `len(frame_descriptions)` and must be ≥2.
- Streamlit input: per-frame description text areas + optional reference image; storyboard count controls how many description fields appear.
- Dependencies remain the same (`google-genai`, `streamlit`, `ffmpeg`, `python-dotenv`); real calls gated by `ENABLE_REAL_GENAI=1`, fake mode via `USE_FAKE_GENAI=1`.
