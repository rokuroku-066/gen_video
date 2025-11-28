# ExecPlan – Gemini + Veo multi‑segment video generator with Streamlit UI

This ExecPlan is a living design document for this repository.  
It explains how to implement an end‑to‑end system that:

1. Maintains **visual consistency** across a sequence of keyframe images and video segments.
2. Produces a **final video longer than Veo’s per‑clip duration limit** by composing multiple Veo segments into one file.

Follow the conventions described in `PLANS.md` and `AGENTS.md` when editing this document.  
Keep the sections **Progress**, **Surprises & Discoveries**, **Decision Log**, and **Outcomes & Retrospective** up to date as you work.


## Purpose / Big Picture

From a user’s perspective:

- The user opens a **Streamlit Web UI**.
- In the UI, the user can:
  - Optionally upload a **reference image** (used to anchor the character / style of frame A).
  - Type a **theme / prompt** (e.g. “a glowing fairy walking on a neon rooftop at night”).
  - Choose the **number of keyframes** (e.g. 3–6).
- When the user clicks “Generate video”:
  1. The system calls a **Gemini text model** to generate:
     - A **global style description** (character, art style, camera, world),
     - A list of **per‑frame prompts** (A, B, C, …) that share the same style but differ in pose / motion.
  2. The system calls **Gemini 2.5 Flash Image** (“Nano Banana”) to generate keyframe images for all frames:
     - Frame A optionally anchored on the user’s reference image.
     - Frame B generated with frame A as a reference image.
     - Frame C generated with frame B as a reference image.
     - And so on.
  3. For each consecutive pair of frames (A→B, B→C, …), the system calls **Veo 3.1** to generate a short video segment that:
     - Starts close to the first frame,
     - Ends close to the second frame,
     - Interpolates motion according to the textual motion description.
  4. The system uses **ffmpeg** to concatenate all segments into a single MP4.
  5. The Streamlit app displays the resulting video and offers a download link.

The two core goals are:

1. **Consistency**  
   Keep character, style, camera angle, and world visually coherent across frames and segments, while allowing small “creative” deviations.

2. **Longer‑than‑Veo‑limit videos**  
   Generate multiple Veo 3.1 segments and concatenate them into a final video whose duration can exceed the per‑clip limit (for example 20–60 seconds).


## Progress

(Keep this section current. Update as you work.)

- [x] Repo dependencies defined (`requirements.txt`).
- [x] `video_pipeline` package created with modules:
  - [x] `config.py`
  - [x] `prompts.py`
  - [x] `images.py`
  - [x] `videos.py`
  - [x] `ffmpeg_utils.py`
  - [x] `run_pipeline.py`
- [x] Basic Streamlit UI (`app.py`) implemented.
- [ ] End‑to‑end happy‑path tested (single run with a simple theme).
- [x] Minimal tests added (`tests/`).
- [ ] This ExecPlan updated with final Outcomes & Retrospective.


## Surprises & Discoveries

(Record unexpected behavior here as you find it. Examples:)

- [x] Local runtime is Python 3.9; kept type hints/imports compatible for tests even though target is 3.10+.


## Decision Log

(Record major design choices and rationale.)

- [x] Use Gemini Developer API by default via `genai.Client()` and environment API keys.
- [x] Default aspect ratio set to `"16:9"` for images and videos.
- [x] Per‑segment video duration set to 6 seconds.
- [x] Outputs stored under `outputs/run_<timestamp>/` with `frames/`, `segments/`, and `final.mp4`.
- [x] `get_genai_client()` raises when `ENABLE_REAL_GENAI` is unset to prevent accidental real API usage.


## Outcomes & Retrospective

(Fill this in after implementing the plan.)

- What works end‑to‑end?
- How long did it actually take?
- Any design choices that should be revisited?
- Any future work that should get its own ExecPlan?


## Context and Orientation

### Repository layout (target structure)

This ExecPlan assumes the repository will be organized roughly as follows:

- `PLANS.md`  
  Global guidance on ExecPlans and this project’s expectations.

- `AGENTS.md`  
  Instructions for coding agents on how to work in this repo.

- `ExecPlan.md`  
  This plan.

- `requirements.txt`  
  Python dependencies.

- `app.py`  
  Streamlit entrypoint.

- `video_pipeline/`
  - `__init__.py`
  - `config.py`  
    Global configuration (model names, environment options, output paths).
  - `prompts.py`  
    Functions to call Gemini text model and produce JSON describing:
      - `global_style`
      - `frames` (A, B, C, …)
  - `images.py`  
    Functions to call **Gemini 2.5 Flash Image** to generate keyframe images from prompts (and reference images).
  - `videos.py`  
    Functions to call Veo 3.1 to generate per‑segment videos from frame images and motion descriptions.
  - `ffmpeg_utils.py`  
    Wrapper functions to concatenate MP4 clips into a final video.
  - `run_pipeline.py`  
    High‑level “glue” for the end‑to‑end flow (theme → prompts → images → segments → concatenated video).

- `tests/`
  - `test_prompts.py`
  - `test_ffmpeg_utils.py`
  - Others as needed.

You may adjust exact paths as long as you update this ExecPlan accordingly. Any change that affects how the API client is instantiated or how `ENABLE_REAL_GENAI` is used must also be reflected here and in `AGENTS.md` / `PLANS.md`.


### Technology constraints

- You **cannot access the internet** or online documentation.  
  All necessary API usage for `google-genai`, Gemini, and Veo must be inferred from this ExecPlan and `PLANS.md`.
- You must treat real calls to Gemini / Veo as **explicit, human‑triggered actions**.  
  Automated tests and default runs must not hit the real APIs; this is enforced via an `ENABLE_REAL_GENAI` environment flag and fake clients where needed.


### External tools and environment

- Python 3.10+.
- `ffmpeg` installed and on PATH.
- Environment variables for Gemini Developer API:
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY` (for non‑Vertex usage).
- Environment variable for optional Vertex AI usage:
  - `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`.
- Environment variable for **real API usage gating**:
  - `ENABLE_REAL_GENAI=1` when a human explicitly wants to run end‑to‑end with real Gemini / Veo.
  - When unset or `"0"`, the code must behave in a way that does **not** hit the real APIs (typically by raising in `get_genai_client()` or returning a fake).


## Plan of Work

High‑level steps:

1. **Set up Python environment and dependencies**
   - Create `requirements.txt` including at least:
     - `google-genai`
     - `streamlit`
     - `pillow`
     - `python-dotenv`
   - Ensure `ffmpeg` is installed.

2. **Implement configuration module (`video_pipeline/config.py`)**
   - Centralize:
     - Model names (e.g. `"gemini-2.5-flash"`, `"gemini-2.5-flash-image"`, `"veo-3.1-generate-preview"`),
     - Aspect ratio (`"16:9"`),
     - Default per‑segment duration (e.g. 6 seconds),
     - Output directory pattern (`outputs/run_<timestamp_or_uuid>/`).
   - Implement `get_genai_client()` with **gating**:
     - Read `ENABLE_REAL_GENAI` from the environment.
     - If it is not `"1"`, either:
       - raise a `RuntimeError` clearly indicating that real API usage is disabled, or
       - return a fake client (if you choose that approach).
     - Only construct a real `genai.Client()` when `ENABLE_REAL_GENAI=1` is set.  
       This prevents automated tests or agents from accidentally consuming API quota.

3. **Implement Gemini client helpers**
   - Optionally, create a separate module (e.g. `video_pipeline/clients.py`) that exposes `get_genai_client()` and related helpers.

4. **Implement prompt generation (`video_pipeline/prompts.py`)**
   - Provide a function `generate_frame_prompts(theme, num_frames, ref_image_bytes=None, motion_hint=None) -> dict`.
   - Use a Gemini text model (`gemini-2.5-flash`) via `google-genai` to:
     - Optionally **describe style** from the reference image (if provided),
     - Produce JSON with:
       - `global_style`: string,
       - `frames`: list of `{ "id": "A" | "B" | ..., "prompt": string, "change_from_previous": string | null }`.
   - Ensure the prompts enforce:
     - Stable character & style,
     - Stable camera & environment,
     - Only small, progressive motion changes between frames.

5. **Implement image generation (`video_pipeline/images.py`)**
   - Provide functions:
     - `generate_keyframe_images(prompts_data, output_dir, ref_image_path=None) -> dict[str, str]`
       - Returns a mapping `{frame_id: image_path}`.
   - Use `"gemini-2.5-flash-image"` model to generate:
     - Frame A:
       - With optional reference image supplied as `types.Part.from_bytes`.
     - Frame B:
       - With frame A’s image as a reference image.
     - Frame C:
       - With frame B’s image as a reference image.
     - And so on.

6. **Implement video segments with Veo 3.1 (`video_pipeline/videos.py`)**
   - Provide functions:
     - `generate_segment_for_pair(frame1_path, frame2_path, motion_description, output_path) -> str`
     - `generate_all_segments(frame_image_paths, prompts_data, output_dir) -> list[str]`
   - Use `client.models.generate_videos` with:
     - `model="veo-3.1-generate-preview"`,
     - First frame as `image`,
     - Last frame via `config=GenerateVideosConfig(last_frame=..., aspect_ratio="16:9", duration_seconds=segment_duration)`.
   - Poll operations until done and download videos to disk.

7. **Implement concatenation with ffmpeg (`video_pipeline/ffmpeg_utils.py`)**
   - Provide:
     - `concat_clips(clip_paths, output_path) -> str`
   - Use the ffmpeg concat demuxer: create a text file listing clips, then run `ffmpeg -f concat -safe 0 -i list.txt -c copy output_path`.

8. **Implement pipeline orchestrator (`video_pipeline/run_pipeline.py`)**
   - Provide:
     - `run_pipeline(theme, num_frames, ref_image_path=None, motion_hint=None) -> str`
       - Returns the final video path.
   - Steps:
     - Create a new run directory (`outputs/run_<timestamp_or_uuid>/`).
     - Call `generate_frame_prompts`.
     - Call `generate_keyframe_images`.
     - Call `generate_all_segments`.
     - Call `concat_clips`.
     - Return final MP4 path.

9. **Implement Streamlit UI (`app.py`)**
   - Provide UI elements:
     - Theme text input / text area,
     - Keyframe count input (min 2),
     - Optional file uploader for reference image,
     - Generate button.
   - On button click:
     - Save the uploaded file to a temporary path,
     - Call `run_pipeline`,
     - Show progress messages,
     - Display the final video (`st.video`) and download button.

10. **Add minimal tests and run a manual validation**
    - Write small tests for non‑networked logic (prompt parsing, ffmpeg concat, etc.).
    - For any functions that would normally call `get_genai_client()`:
      - In tests, inject or monkey‑patch a **FakeGenaiClient** that does not perform real network I/O.
      - Never set `ENABLE_REAL_GENAI=1` during automated tests.
    - Manually run the Streamlit app and confirm the end‑to‑end flow works for at least one simple scenario **with `ENABLE_REAL_GENAI=1` set by a human**.


## Concrete Steps

(Concrete code snippets・テスト例などはこのExecPlan内にすでに十分入っているので、そのまま実装ガイドとして使える想定。  
必要ならここに更に細かい手順を追記していく運用にする。)


## Validation and Acceptance

To consider this ExecPlan implemented successfully, the following manual checks should pass.

1. **Environment setup**

   - `pip install -r requirements.txt` completes without errors.
   - `ffmpeg -version` works in the shell.

2. **Streamlit app runs**

   - From the repo root:

     ```bash
     # Windows PowerShell example
     $env:ENABLE_REAL_GENAI = "1"
     streamlit run app.py
     ```

   - The browser opens with the app showing theme input, keyframe selector, reference image uploader, and generate button.

3. **End‑to‑end video generation**

   - In the Streamlit app (with `ENABLE_REAL_GENAI=1` set in the environment):
     - Enter a simple theme (e.g. “a yellow fairy standing on a rooftop at night, slowly walking toward the camera”).
     - Set `num_frames = 3`.
     - Optionally upload a small PNG or JPEG as reference.
     - Click “Generate video”.
   - The app shows progress (“Generating video…”).
   - After some time, it shows:
     - A success message,
     - A video player with the generated MP4,
     - A download button.

4. **Visual inspection**

   - The video:
     - Is longer than a single Veo segment duration (in practice, at least the sum of all segments).
     - Shows a character and style that are recognizably consistent across the whole video.
     - Has no jarring hard cuts between segments (ideally only subtle transitions).

5. **No uncaught errors**

   - The Streamlit server log should not show tracebacks for the happy‑path scenario.
   - Automated tests should pass without ever toggling `ENABLE_REAL_GENAI` or calling the live APIs.


## Idempotence and Recovery

- Prompt generation, image generation, and video segment generation are **purely additive**:
  - Re‑running the pipeline for the same theme will create a new `run_<id>` folder without affecting earlier runs.
- If Veo segment generation fails for a particular pair:
  - Delete the partial clip file, fix the issue, and re‑run `generate_all_segments` or `run_pipeline`.
- If ffmpeg concatenation fails:
  - Confirm that all segment paths exist and share the same format.
  - Inspect the ffmpeg error message, fix inputs, then re‑run `concat_clips`.

Where possible, functions should log to stdout or to simple text logs under each run directory, so that failures can be debugged after the fact.


## Artifacts and Notes

- Example structure of a prompt JSON returned by `generate_frame_prompts`:

  ```json
  {
    "global_style": "Anime style, flat colors, small round yellow fairy character...",
    "frames": [
      {
        "id": "A",
        "prompt": "Base frame prompt for a standing pose...",
        "change_from_previous": null
      },
      {
        "id": "B",
        "prompt": "Same character and world, now taking one step forward...",
        "change_from_previous": "takes a small step forward"
      },
      {
        "id": "C",
        "prompt": "Same character, closer to camera, waving at viewer...",
        "change_from_previous": "moves closer and waves"
      }
    ]
  }
````

* Example naming convention in `outputs/`:

  ```text
  outputs/
    run_2025-11-28T14-03-12/
      frames/
        frame_A.png
        frame_B.png
        frame_C.png
      segments/
        segment_A_B.mp4
        segment_B_C.mp4
      final.mp4
  ```

* The system intentionally allows **slight visual drift** between frames; this is acceptable as “artistic flavor” as long as identity and world remain recognizable.

## Interfaces and Dependencies

Summary of assumed interfaces to external libraries. These are not exact type signatures from the SDK but practical patterns to follow.

* `google.genai.Client`:

  * Creation:

    ```python
    from google import genai
    client = genai.Client()  # uses environment API key
    ```

  * Text generation:

    ```python
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[instruction_string],
    )
    text = response.text
    ```

  * Image generation:

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
    # Then extract inline image data from response parts.
    ```

  * Image part from bytes:

    ```python
    from google.genai import types
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png",
    )
    ```

  * Video generation (Veo 3.1):

    ```python
    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=video_prompt,
        image=first_frame_part,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=6,
            last_frame=last_frame_part,
        ),
    )

    # Poll until done, then:
    video_obj = operation.response.generated_videos[0]
    dl = client.files.download(file=video_obj.video)
    # Save bytes from dl to an MP4 file.
    ```

* `streamlit`:

  * Basic usage:

    ```python
    import streamlit as st

    st.title("...")
    theme = st.text_area("Theme")
    num_frames = st.number_input("Frames", min_value=2, max_value=8, value=3)
    file = st.file_uploader("Reference image", type=["png", "jpg", "jpeg"])

    if st.button("Generate video"):
        # call run_pipeline and show st.video(...)
    ```

This concludes the ExecPlan for the Gemini + Veo multi‑segment video generator with Streamlit UI.
