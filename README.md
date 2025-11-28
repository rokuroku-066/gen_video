# Gemini + Veo Multi-Segment Video Generator

Streamlit app and Python pipeline that generate a longer-than-single-clip video by chaining Gemini prompts, Gemini 2.5 Flash Image keyframes, Veo 3.1 video segments, and ffmpeg concatenation. The system emphasizes visual consistency (character, style, camera, world) across all frames and segments.

## Features
- Prompt generation that enforces shared global style with small per-frame motion changes.
- Keyframe images linked by references to maintain look and camera continuity.
- Veo 3.1 short clips between consecutive frames, then ffmpeg concat to one MP4.
- Streamlit UI for theme, keyframe count, optional reference upload, and motion hint.
- Offline-safe by default: real API calls are blocked unless explicitly enabled.

## Requirements
- Python 3.10+ recommended (tests exercised under 3.9; code keeps compatible imports).
- ffmpeg available on PATH.
- Dependencies: `pip install -r requirements.txt`

## Environment Variables
- `ENABLE_REAL_GENAI=1` — required to permit real Gemini/Veo calls. If unset, `get_genai_client()` raises to protect quota.
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` — for Gemini Developer API.
- Optional Vertex AI mode (if you choose to wire it): `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`.

## Quickstart (Streamlit UI)
```bash
# From repo root
python -m venv .venv && .\.venv\Scripts\activate  # adjust for your shell
pip install -r requirements.txt
set ENABLE_REAL_GENAI=1
set GEMINI_API_KEY=your_key_here  # or GOOGLE_API_KEY
ffmpeg -version  # sanity check
streamlit run app.py
```
In the browser: provide a theme, choose keyframes (min 2), optionally upload a reference image, and click "Generate video". The output MP4 is saved under `outputs/run_<timestamp>/final.mp4`.

## Programmatic Pipeline Usage
```python
from video_pipeline.run_pipeline import run_pipeline

final_path = run_pipeline(
    theme="a glowing fairy walking on a neon rooftop at night",
    num_frames=3,
    ref_image_path=None,           # or a Path to a PNG/JPEG
    motion_hint="gentle forward motion"
)
print("Video at:", final_path)
```

## Tests
Offline-safe unit tests (no real API calls):
```bash
python -m pytest
```

## Project Layout
- `app.py` — Streamlit UI entrypoint.
- `video_pipeline/`
  - `config.py` — shared config, ENABLE_REAL_GENAI gating, run directory helper.
  - `prompts.py` — Gemini text prompts for global style and per-frame descriptions.
  - `images.py` — Gemini 2.5 Flash Image keyframe generation with chaining references.
  - `videos.py` — Veo 3.1 segment generation between frames.
  - `ffmpeg_utils.py` — concat helper using ffmpeg concat demuxer.
  - `run_pipeline.py` — orchestrates prompts → frames → segments → final MP4.
- `tests/` — offline-safe tests (prompt parsing, ffmpeg concat).

## Safety and Cost Controls
- By default, real networked clients are refused. Set `ENABLE_REAL_GENAI=1` only when you intentionally want real API calls (e.g., manual Streamlit demo). Automated tests must keep it unset.
- Ensure ffmpeg is installed and clips share the same format before concatenation.

## Troubleshooting
- ImportError for `google.genai`: install deps with `pip install -r requirements.txt`.
- RuntimeError about ENABLE_REAL_GENAI: set `ENABLE_REAL_GENAI=1` when you intend to hit real APIs.
- ffmpeg concat errors: verify clip paths exist and share codecs; rerun concat after fixing inputs.
