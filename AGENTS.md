# AGENTS.md – Guidance for coding agents in this repository

This repository contains a Python project that builds a **video generation tool** using:
- Gemini text models for prompt generation,
- Gemini 2.5 Flash Image ("Nano Banana") for storyboard images,
- Veo 3.1 for short video clips,
- `ffmpeg` for concatenating clips,
- Streamlit for a guided, three-step Web UI (prompt entry → storyboard review/regeneration → video build).

The primary goals of the system are:

1. Maintain **visual consistency** (character, style, camera, and world) across a sequence of images and the resulting video.
2. Generate **videos longer than Veo’s per‑clip limit** by composing multiple Veo‑generated segments into a single output file.


## How you (the agent) should work

- Prefer offline-safe workflows; real API calls must be explicitly opted in by a human.
- You **can**:
  - Read and write files in this repository.
  - Run shell commands (for example `pip install`, `ffmpeg`, `streamlit run app.py`), if your environment allows it.
  - Run Python code and tests.

Because you cannot access online docs for `google-genai`, Veo, or Streamlit, you must rely on:
- This `AGENTS.md` file,
- The project’s `PLANS.md` file,
- Any ExecPlan files created for specific tasks,
- The existing source code.

Real calls to Gemini / Veo **cost money and quota**. In this repository, **real API usage is explicitly gated** and must never occur from automated tests. The fake client (`USE_FAKE_GENAI=1`) is the expected default when running locally or in CI.


## When to use PLANS.md and ExecPlans

- For **complex features** or **significant refactors** (anything involving the core pipeline, API usage, or Streamlit UI), you must create and follow an ExecPlan as described in `PLANS.md`.
- Treat `PLANS.md` as the **canonical guide** for:
  - How to structure an ExecPlan,
  - How to use `google-genai` and Veo in this repo,
  - How to wire the Streamlit UI to the pipeline.

Short tasks such as "fix this small bug" or "rename a function" may be done without an ExecPlan. But any multi‑file or multi‑step implementation should start by authoring an ExecPlan.


## Repository expectations and coding style

- Use **Python 3.10+** syntax and type hints.
- Prefer small, composable functions over large monolithic scripts.
- Keep side‑effects local; pipeline functions should:
  - Accept explicit parameters,
  - Return values or paths instead of relying on global state.
- Use clear, descriptive names (e.g. `generate_storyboards`, `generate_segment_video`, `concat_clips`).
- For configuration, use a dedicated module (for example `video_pipeline/config.py`) or dataclasses instead of scattering constants.


## Dependencies and environment setup

Assume a basic Python environment:

- Recommended dependencies (add to `requirements.txt` or similar):
  - `google-genai`
  - `streamlit`
  - `pillow`
  - `python-dotenv`
  - Any chosen test framework (for example `pytest`)

Typical setup commands from the repo root:

- Create and activate a virtual environment (exact commands depend on platform).
- Install dependencies:
  - `pip install -r requirements.txt`

Environment variables:

- For Gemini Developer API: set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
- For Vertex AI: optionally set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
- For **real API usage gating in this repository**:
  - `ENABLE_REAL_GENAI=1` when a human explicitly wants to run end‑to‑end with the real Gemini / Veo APIs.
  - `USE_FAKE_GENAI=1` to force the built-in offline fake client (no network, deterministic placeholder media). This is the preferred default for demos and automated tests.
  - When neither flag is present, `get_genai_client()` is expected to raise to avoid accidental network usage.

Tools:

- `ffmpeg` must be available on the PATH for video concatenation. The code extracts last frames and concatenates segments via the concat demuxer.
- You may call `ffmpeg` via `subprocess.run` in Python or via shell commands.


## google-genai usage cheat‑sheet

You should not attempt to "discover" the API by trial and error against the real service. Instead, rely on the patterns documented here and in `PLANS.md`.

In this repository, **real Gemini / Veo calls are considered an expensive resource** and must be explicitly opted in by a human. By default:

- `get_genai_client()` is required to **refuse** creating a real networked client unless `ENABLE_REAL_GENAI=1` is present in the environment.
- Automated tests (pytest or similar) must **never set `ENABLE_REAL_GENAI=1`** and must not hit the real API.

### Client creation

In most cases:

```python
from google import genai
from google.genai import types

client = genai.Client()  # uses environment variables for configuration
````

If an ExecPlan decides to use explicit configuration (e.g. Vertex AI) it should create:

```python
client = genai.Client(
    vertexai=True,
    project="your-project-id",
    location="us-central1",
)
```

ExecPlans must also document how `ENABLE_REAL_GENAI` is used:

* When `ENABLE_REAL_GENAI` is unset or not `"1"`, `get_genai_client()` must either:

  * raise a clear error (recommended for development), or
  * return a **fake client** that does not perform network I/O.
* When a human wants to run a true end‑to‑end integration (for example in Streamlit), they must:

  * set `ENABLE_REAL_GENAI=1`, and
  * be aware that API quota and billing will be consumed.

### Text generation (prompt generation for frames)

Typical usage pattern:

```python
instruction = "... long system prompt that asks for JSON ..."

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=instruction,
)

json_text = response.text
data = json.loads(json_text)
```

The ExecPlan should define the exact JSON shape (currently `{"frames": [...]}` only).

### Image generation (Nano Banana / Gemini 2.5 Flash Image)

Typical usage pattern for a single image:

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[prompt_text],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9"),
    ),
)

# Extract image
parts = getattr(response, "parts", None) or response.candidates[0].content.parts
for part in parts:
    if getattr(part, "inline_data", None) is not None:
        img_bytes = part.inline_data.data
        # Use Pillow to save the bytes
```

To **use a reference image** for consistency:

```python
from google.genai import types

ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/png")

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[ref_part, prompt_text],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9"),
    ),
)
```

### Video generation (Veo 3.1)

Standard text‑to‑video segment:

```python
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=video_prompt,
)
```

Polling until completion:

```python
from time import sleep

while not operation.done:
    sleep(10)
    operation = client.operations.get(operation)

video_obj = operation.response.generated_videos[0]
dl = client.files.download(file=video_obj.video)
# Save dl to an MP4 file
```

For **first + last frame interpolation**:

* Pass a first frame via `image=first_frame_part`.
* Pass a `GenerateVideosConfig` with:

  * `aspect_ratio="16:9"`
  * `duration_seconds=<segment_length>`
  * `last_frame=last_frame_part`.

You must never assume long continuous videos from a single call; instead, generate multiple segments and concatenate them.

## Streamlit and running the app

Basic expectations for `app.py`:

* Imports:

```python
import streamlit as st
from video_pipeline.run_pipeline import run_pipeline
```

* UI elements (current single-tab flow):

  * `st.title("Gemini + Veo Animation Builder")` (or similar)
  * Text areas for per-frame descriptions; controls to add/insert/delete frames (minimum 2).
  * A file uploader for an optional reference image.
  * Buttons to generate/regenerate each frame, generate all frames, and generate video.

* When video generation is triggered:

  * Save the uploaded file (if any) to a temporary directory.
  * Call the pipeline function(s).
  * Display progress messages.
  * When done, show the resulting video with `st.video(...)` and provide a download link.

To run locally from the repo root (when a human **explicitly** wants to hit the real APIs):

```bash
# Windows (PowerShell)
$env:ENABLE_REAL_GENAI = "1"
streamlit run app.py
```

## Testing and validation

You are encouraged to add at least basic tests. **Automated tests must not hit the real Gemini / Veo APIs.** Instead they must rely on fakes / stubs.

* Use `pytest` or the project’s existing test toolchain.
* For network‑related code:

  * Inject or monkey‑patch a **FakeGenaiClient** that mimics the methods you need (`models.generate_content`, `models.generate_videos`, etc.) and returns deterministic dummy data.
  * Do not call `get_genai_client()` from tests unless it is configured to return a fake.
* Examples:

  * A test that verifies storyboard image regeneration works with fake clients.
  * A test that verifies `concat_clips` can join small, dummy MP4 files into a single output.

Before considering a feature complete:

* Ensure the project:

  * Installs cleanly,
  * Starts the Streamlit app without errors,
  * Can successfully generate at least one output video via the UI **when a human explicitly sets `ENABLE_REAL_GENAI=1`**,
  * All automated tests pass **without** ever calling the live APIs.

## Summary

* Read and obey `PLANS.md` when authoring or following an ExecPlan.
* Treat `google-genai`, Veo 3.1, Streamlit, and `ffmpeg` usage patterns given in `PLANS.md` and this `AGENTS.md` as your only API reference.
* Always tie your changes back to the two core goals:

  1. Visual consistency.
  2. Long videos composed from multiple Veo segments.
* Be explicit about when you allow real API usage and keep automated tests **offline‑safe** by design.
