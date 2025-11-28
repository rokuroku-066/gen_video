# ExecPlan – Streamlit progress updates for frame and segment generation

This ExecPlan is a living document for adding progress-aware status updates to the pipeline and Streamlit UI.
It should be sufficient for a newcomer to implement the feature without external references.

## Purpose / Big Picture

Provide clearer feedback while generating keyframes and videos. The Streamlit UI should show per-frame and per-segment progress (e.g., "3/5 フレームを再生成中…", "クリップ 2/3 を結合中…") as the pipeline runs. This keeps users informed during long operations while maintaining the project goals of visual consistency and multi-segment videos.

## Progress

- [x] Draft plan
- [x] Implement pipeline status yields
- [x] Update Streamlit UI to display incremental progress
- [x] Validate with local test runs

## Surprises & Discoveries

- None yet.

## Decision Log

- Progress information will be emitted from pipeline functions via generator-style yields or callbacks so the UI can render updates without blocking.

## Outcomes & Retrospective

(To be completed after implementation.)

## Context and Orientation

Relevant modules:
- `video_pipeline/images.py` – generates keyframe images and handles regeneration.
- `video_pipeline/videos.py` – builds Veo segments between frames.
- `video_pipeline/run_pipeline.py` – orchestrates prompts → frames → segments → final video.
- `app.py` – Streamlit UI showing progress and results.

## Plan of Work

1. Extend pipeline helpers to emit structured progress updates (e.g., stage, index, total, message) while looping over frames or segments.
2. Update regeneration and video build functions to use the new progress notifications.
3. Update Streamlit UI to consume these updates, presenting progress bars or status text that change during execution.
4. Ensure existing behavior (return values, offline safety) remains intact.

## Concrete Steps

1. Add a progress callback or generator pattern to `generate_keyframe_images` and `regenerate_keyframe_images` so callers receive per-frame updates.
2. Add progress reporting to `generate_all_segments` and `build_video_from_frames` for segment generation and concatenation.
3. Update `app.py` to replace static spinners with dynamic progress text/bars based on yielded updates from regeneration and video build flows.
4. Run relevant tests (`python -m pytest`) to confirm nothing regressed.

## Validation and Acceptance

- Trigger frame regeneration in the UI and observe per-frame progress updates.
- Trigger video build in the UI and observe per-segment and concatenation updates.
- Automated tests pass: `python -m pytest`.

## Idempotence and Recovery

- Progress callbacks should not mutate state; rerunning should simply emit updates again.
- If generation fails mid-way, previously written frames/segments remain on disk; rerunning will overwrite as before.

## Artifacts and Notes

- None yet.

## Interfaces and Dependencies

- No changes to external APIs; progress plumbing is internal to the pipeline and UI.
- Continue honoring `ENABLE_REAL_GENAI` gating via existing config.
