# ExecPlan – Increase per-frame variation while keeping visual consistency

This ExecPlan is a living document for this repository. Keep the sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as you work.

If this repository includes PLANS.md, follow all rules and conventions from PLANS.md when editing this document.

## Purpose / Big Picture

Make consecutive storyboard images show clearer motion and composition changes while preserving the same character, style, and world. The goal is to adjust prompt wording and image-generation inputs so frames do not look nearly identical, yet still support multi-segment videos that maintain continuity.

## Progress

- [x] Capture requirements and create ExecPlan.
- [x] Strengthen prompt template to demand visible per-frame changes.
- [x] Enrich image-generation prompts with global style + explicit change descriptions.
- [x] Update/extend tests to match the new prompt composition.
- [x] Validate with offline-safe checks (e.g., pytest) and note manual review guidance.

## Surprises & Discoveries

- Existing frames in `outputs/run_20251129T011905/frames/` look very similar across A–D, likely because prompts emphasize “small motion changes” and images chain tightly to the previous frame reference.

## Decision Log

- Will keep reference-image chaining for consistency but inject stronger textual cues per frame so changes are visible.
- Will compose image prompts from both `global_style` and each frame’s `change_from_previous` to push distinct poses/camera while keeping identity.
- Will not change API gating; real calls remain behind `ENABLE_REAL_GENAI=1`.

## Outcomes & Retrospective

- Prompt template now requires noticeable pose/camera changes per frame while keeping style/identity consistent.
- Image generation composes prompts from `global_style` + per-frame text + change descriptions to force visible variation and reduce near-identical frames even with reference chaining.
- Offline validation: `python -m pytest` passes; manual visual review with real APIs is still needed when `ENABLE_REAL_GENAI=1` is enabled.

## Context and Orientation

Key files:
- `video_pipeline/prompts.py` – builds storyboard prompts.
- `video_pipeline/images.py` – turns prompts into storyboard images (Gemini 2.5 Flash Image).
- `video_pipeline/run_pipeline.py` – orchestrates prompt→images flow.
- `tests/` – prompt and image helper tests.
- `outputs/run_20251129T011905/frames/` – current example showing minimal variation.

## Plan of Work

1. Refine the text prompt template to require meaningful pose/camera progression per frame, still keeping consistent character/style.
2. Add an image-prompt composer that blends `global_style`, per-frame prompt, and `change_from_previous` with explicit “visible change” instructions; reuse it for generation and regeneration paths.
3. Update tests to align with the richer prompt text while preserving checks on reference chaining.
4. Run offline-safe validation (pytest) and note manual review steps for real API runs.

## Concrete Steps

- Edit `prompts.py` `_build_prompt` to emphasize progressive action, camera movement, and non-identical frames; keep JSON schema unchanged.
- In `images.py`, add a helper to compose per-frame image prompt strings using `global_style` + `change_from_previous` + consistency reminders; use it in `generate_storyboard_images` and `regenerate_storyboard_images`.
- Adjust `tests/test_images.py` (and others if needed) to assert the new composed prompt structure while keeping reference-byte anchoring behavior.
- Optionally log or document sample output prompts for manual verification.

## Validation and Acceptance

- `python -m pytest` passes without hitting real APIs (no `ENABLE_REAL_GENAI=1` in tests).
- Manual guidance: with `ENABLE_REAL_GENAI=1`, run the Streamlit flow and confirm generated frames show clear pose/camera progression (not near-identical) while the character/style remains consistent; final video still composes segments normally.

## Idempotence and Recovery

- Prompt/template changes are deterministic; rerunning frame generation creates a new `run_<timestamp>` without harming prior runs.
- Regeneration overwrites only targeted frames; can be repeated safely.

## Artifacts and Notes

- Outputs stay under `outputs/run_<timestamp>/frames/` and `segments/`; final video at `final.mp4`.
- Stronger text cues should reduce “identical-looking” frames even with reference chaining.

## Interfaces and Dependencies

- No new dependencies; continue using `google-genai`, `streamlit`, `ffmpeg`.
- Real API usage remains gated by `ENABLE_REAL_GENAI=1`; default/test runs must stay offline-safe.
- Functions touched:
  - `generate_frame_prompts(...)` in `prompts.py` (template change only).
  - `generate_storyboard_images(...)` and `regenerate_storyboard_images(...)` in `images.py` (prompt composition change).
