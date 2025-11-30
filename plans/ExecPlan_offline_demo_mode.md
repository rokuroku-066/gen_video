# ExecPlan – Add offline/demo mode with fake Gemini/Veo clients

This ExecPlan is a living document for this repository. Keep the sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as you work.

If this repository includes PLANS.md, follow all rules and conventions from PLANS.md when editing this document.

## Purpose / Big Picture

Let the Streamlit app and pipeline run **without real Gemini/Veo network calls** by providing a built-in fake client and placeholder media. Goals:

1) Enable demos and local UI testing with no API keys, no cost, and no quota usage.  
2) Keep behavior close to the real pipeline (same function signatures, same file layout) so switching to real APIs is a one-flag change.  
3) Preserve visual-consistency workflow (reference anchoring, frame chaining) even in fake mode, while producing obviously synthetic outputs so users know they are stubs.

## Progress

- [x] Capture requirements and create ExecPlan.
- [x] Design fake client shapes matching `google-genai` usage in this repo.
- [x] Implement fake text/image/video generators that emit deterministic JSON/PNG/MP4 assets.
- [x] Add config flag/wiring so `get_genai_client()` returns fake when requested, real only when `ENABLE_REAL_GENAI=1`.
- [x] Update Streamlit UI to offer an "offline demo mode" toggle and surface which mode is active.
- [x] Add tests covering fake client pathways (no network).
- [x] Validate offline end-to-end run produces frames, segments, and final.mp4 with no real API access (pytest smoke with fake concat).
- [ ] Update Outcomes & Retrospective.

## Surprises & Discoveries

- On Windows, deleting the temporary PNG right after writing can fail if the file handle is open; explicitly closing the NamedTemporaryFile avoids PermissionError during tests.

## Decision Log

(Record choices such as: exact env flag name, whether fake video uses ffmpeg or static bytes, how to mark demo outputs visually.)

## Outcomes & Retrospective

- Offline demo mode implemented with `USE_FAKE_GENAI`, FakeGenaiClient, and Streamlit toggle; pytest smoke covers fake text/image/video paths and pipeline flow.
- Remaining work: manual UI check with fake mode (visual sanity) and optional validation that real mode still works when `ENABLE_REAL_GENAI=1`.

## Context and Orientation

Current state (2025-11-30):
- `get_genai_client()` raises unless `ENABLE_REAL_GENAI=1`, so the Streamlit UI cannot run without real APIs; it only shows an info message then fails when the user clicks Generate.
- Tests inject ad-hoc fakes per module but there is no shared fake client or demo asset generator.
- The pipeline functions already accept an optional `client` argument, making injection feasible.
- `ffmpeg` is already required and used in `video_pipeline/ffmpeg_utils.py`.

Pain points:
- Demoing the UI requires real API keys and incurs cost.
- Developers cannot visually inspect the UI flow or output artifacts offline.

## Plan of Work

1) Define a **FakeGenaiClient** that mirrors only the methods used here:
   - `models.generate_content` for text and image.
   - `models.generate_videos`.
   - `operations.get`.
   - `files.download`.
2) Implement deterministic generators:
   - Text: return JSON with `frames` and `change_from_previous` seeded by the theme and frame count.
   - Image: create simple 16:9 PNGs (e.g., solid color gradient with frame ID and change text overlaid) using Pillow.
   - Video: create short MP4 clips (1–2s) using `ffmpeg -f lavfi color` plus drawtext or by stitching two PNGs with `ffmpeg -loop 1` and `-t` to simulate motion; ensure duration matches config.segment_duration_seconds.
3) Configuration wiring:
   - Add env flag `USE_FAKE_GENAI=1` (or `DEMO_MODE=1`). Precedence: if `ENABLE_REAL_GENAI=1` -> real client; elif `USE_FAKE_GENAI=1` -> fake client; else raise (current behavior).
   - Surface active mode via helper (e.g., `describe_api_mode()`).
4) Streamlit updates:
   - Add a toggle/checkbox "Use offline demo (fake outputs)" shown when real mode is off.
   - Pass the selected client into `generate_initial_frames` / `build_video_from_frames`.
   - Clearly label outputs as "FAKE / DEMO" to avoid confusion.
5) Tests:
   - Unit test FakeGenaiClient text/image/video paths.
   - Pipeline smoke test: run `generate_initial_frames` and `build_video_from_frames` with fake client and assert files exist and have non-zero bytes; no network or env flags required.
6) Docs:
   - Update `AGENTS.md` and `PLANS.md` if needed to mention `USE_FAKE_GENAI`.
   - Note in app copy how to switch between fake and real.

## Concrete Steps

1) Create `video_pipeline/fake_genai.py` with `FakeGenaiClient`, `FakeModels`, `FakeOperations`, `FakeFiles`.
   - Text generation returns deterministic JSON for requested `num_frames`.
   - Image generation uses Pillow to render a 16:9 PNG with frame ID and change text.
   - Video generation writes an MP4 to a temp file using ffmpeg; store the path in the fake operation response.
2) Update `video_pipeline/config.py`:
   - Add `use_fake_genai()` helper reading `USE_FAKE_GENAI`.
   - Modify `get_genai_client()` to return fake when `USE_FAKE_GENAI=1` and real when `ENABLE_REAL_GENAI=1`; otherwise raise.
3) Thread client selection into the Streamlit UI:
   - Add a checkbox "オフラインデモ（フェイク出力）" shown when real mode is off; on click, set `use_fake=True`.
   - Build the client once per request and pass it into `generate_initial_frames` and `build_video_from_frames`.
   - Display a status badge indicating "FAKE MODE" or "REAL API".
4) Add tests:
   - `tests/test_fake_genai.py` covering text/image/video methods.
   - Pipeline smoke test using fake client to ensure `final.mp4` and frame files are created.
5) Optional UX niceties:
   - Tag generated filenames with `fake_` prefix in demo mode to avoid confusion.
   - Add a short note in the app explaining that visual fidelity will be low in demo mode.
6) Run `python -m pytest` to verify offline safety.

## Validation and Acceptance

- Running `python -m pytest` passes, including new fake-client tests, with no network calls.
- With no env vars set, enabling the UI checkbox runs the full pipeline using fake outputs, producing:
  - A set of PNG frames under `outputs/run_<timestamp>/frames/`.
  - MP4 segments under `outputs/run_<timestamp>/segments/`.
  - `final.mp4` concatenated successfully.
- With `ENABLE_REAL_GENAI=1`, real mode still works as before (manual check only).
- App clearly shows which mode is active; fake outputs are visually distinct and labeled.

## Idempotence and Recovery

- Fake generation is deterministic given theme + frame IDs; re-running creates a fresh `run_<timestamp>` without affecting prior runs.
- If ffmpeg is missing, fake video generation should raise a clear error; document fallback (e.g., skip video and warn).
- Switching between fake and real modes only requires environment or UI toggle; no code changes.

## Artifacts and Notes

- Example fake frame appearance: 16:9 PNG with a colored gradient background, large "Frame B", and the change text at the bottom.
- Example fake video: 1–2 second MP4 with a solid color and overlaid "Segment A→B (demo)"; duration matches `segment_duration_seconds`.
- Keep fake assets small (<1 MB) to speed up tests and demos.

## Interfaces and Dependencies

- New module: `video_pipeline/fake_genai.py` (pure Python + Pillow + ffmpeg).
- New env flag: `USE_FAKE_GENAI=1` to opt into fake client; `ENABLE_REAL_GENAI=1` still controls real API usage.
- `get_genai_client()` selection logic:
  - `ENABLE_REAL_GENAI=1` → real `genai.Client()`.
  - Else if `USE_FAKE_GENAI=1` → `FakeGenaiClient()`.
  - Else → raise to prevent accidental network calls.
- Streamlit UI must not call real APIs unless explicitly enabled; fake mode must never require network access.
