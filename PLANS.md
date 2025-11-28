# Codex Execution Plans for the Gemini + Veo video generator

This `PLANS.md` describes how to write and maintain execution plans ("ExecPlans") for this repository.
An ExecPlan is a self‑contained design document that a coding agent (or a human novice) can follow to implement or modify the system.
All ExecPlan documents live under the `plans/` directory so they are easy to discover and keep together.

The agent that reads ExecPlans **cannot browse the internet** and **cannot open online documentation** for `google-genai`, Veo, or Streamlit. Every ExecPlan in this repo must therefore embed enough detail that a novice can complete the work using only:
- the current working tree,
- this `PLANS.md` file,
- the ExecPlan being followed.


## How to use ExecPlans in this repository

- When implementing a **non‑trivial feature** (for example: building or refactoring the end‑to‑end video‑generation pipeline, changing API usage, or restructuring the Streamlit UI), first create an ExecPlan file under `plans/` and follow the structure defined in this `PLANS.md`.
- Treat the ExecPlan as a **living document**:
  - Update the `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections as work advances.
  - Keep the document self‑contained at all times: if new decisions or constraints appear, write them down in the plan.
- When resuming work later, a coding agent should be able to:
  - Read the ExecPlan from start to finish,
  - Follow the steps,
  - Produce a working feature **without any external context**.


## Non‑negotiable requirements for ExecPlans

Every ExecPlan in this repo must:

1. Be **self‑contained**.  
   It must contain all domain knowledge, library usage notes, and project‑specific context needed to complete the task. Do not rely on external blogs or docs. If the work depends on `google-genai`, Veo, Streamlit, or `ffmpeg`, summarize the relevant API usage inside the plan.

2. Assume the reader is a **beginner in this codebase**.  
   Explain file paths, modules, and key concepts as if the reader has never seen the repo before.

3. Be **outcome‑focused**.  
   The plan must describe what the user will be able to do after the work is finished (for example: "From the Streamlit page, the user can upload an image, type a theme, choose the number of keyframes, click Generate, and download a long video created from multiple Veo clips").

4. Remain a **living document**.  
   As the agent discovers issues, edge cases, or better designs, it must:
   - Update `Surprises & Discoveries` with short evidence,
   - Update `Decision Log` with what changed and why,
   - Keep `Progress` accurate.

5. Describe **how to validate** the work.  
   The plan must include exact commands to run (for example `streamlit run app.py`, `python -m pytest`, or `ffmpeg ...`) and what output or behavior to look for.

6. Respect **API usage and cost controls**.  
   ExecPlans in this repo must:
   - Treat real calls to Gemini / Veo as **explicit, human‑driven integration steps**, not as something that happens in automated tests.
   - Specify how to prevent accidental API use (e.g. via an `ENABLE_REAL_GENAI` environment flag and fake clients for tests).
   - Make it clear which commands / steps will actually hit external APIs so that a human can make an informed decision.


## Formatting and skeleton of a good ExecPlan

Each ExecPlan file in this repo should contain **one Markdown document** with the following sections, in this order. Store the file under `plans/` and use a descriptive name for multi‑plan repos (e.g., `plans/ExecPlan_image_review.md`):

```md
# <Short, action‑oriented description>

This ExecPlan is a living document for this repository. Keep the sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as you work.

If this repository includes PLANS.md, follow all rules and conventions from PLANS.md when editing this document.

## Purpose / Big Picture

## Progress

## Surprises & Discoveries

## Decision Log

## Outcomes & Retrospective

## Context and Orientation

## Plan of Work

## Concrete Steps

## Validation and Acceptance

## Idempotence and Recovery

## Artifacts and Notes

## Interfaces and Dependencies
````

Guidelines for these sections:

* **Purpose / Big Picture**
  Explain, in plain language, what new behavior a user gets. For this repo, always tie it back to:

  1. Maintaining visual consistency across images and video segments.
  2. Creating videos **longer than a single Veo clip** by composing multiple segments.

* **Progress**
  Use a checklist with timestamps. Every time work pauses, update this section so it tells the truth about what is done and what remains.

* **Surprises & Discoveries**
  Record anything unexpected (for example: Veo API returning a different structure, `google-genai` raising a type error, Streamlit not re‑running as expected). Include tiny code or log snippets as evidence.

* **Decision Log**
  Every significant design choice (for example: "we concatenate Veo clips with `ffmpeg concat` instead of using Veo's video‑extension feature") should be written here with a rationale.

* **Outcomes & Retrospective**
  At the end of an ExecPlan, summarize what was achieved, what is left, and what you learned for future work.

* **Context and Orientation**
  Describe the current repository layout and the parts relevant to this ExecPlan. Name files and directories explicitly (for example: `app.py`, `video_pipeline/`, `tests/`).

* **Plan of Work**
  Narratively describe the steps (modules to create, functions to add or modify) in the approximate order they will be implemented.

* **Concrete Steps**
  List concrete commands and exact file edits. For example:

  * "From the repo root, run `pip install -r requirements.txt`."
  * "Create `video_pipeline/prompts.py` with a `generate_frame_prompts(...)` function as described in Interfaces and Dependencies."

* **Validation and Acceptance**
  Explain how to run and test the system end‑to‑end, and how a human can tell that it works. For this project, that usually means running the Streamlit app, creating a test video, and checking that:

  * The character and style are reasonably consistent across frames,
  * The final video length exceeds a single Veo clip’s maximum duration,
  * No obvious errors occur.
  * Real APIs are only hit when `ENABLE_REAL_GENAI=1` is set by a human.

* **Idempotence and Recovery**
  Mention which steps can be safely repeated and how to recover from partial failures (for example: if one Veo operation fails, you can delete its partial clip and re‑run only that part, then re‑concat).

* **Artifacts and Notes**
  Include short log snippets, example prompts, and example configuration entries that clarify how everything fits together.

* **Interfaces and Dependencies**
  This section is **critical** in this repo. It must spell out the expected public functions, classes, and usage patterns for:

  * `google-genai` and Gemini models (text, image, and Veo video),
  * Streamlit Web UI,
  * `ffmpeg` usage for concatenating clips,
  * Any helper modules in `video_pipeline/` or similar packages.
    It must also document:
  * How `get_genai_client()` behaves when `ENABLE_REAL_GENAI` is unset (e.g. raises, returns fake),
  * How to construct fake clients for unit tests,
  * Which commands / flows are allowed to use the real APIs and under which environment settings.

## Repository‑specific architecture: Gemini + Veo + Streamlit

This repository’s main goal is to build a **video generator** that:

1. Keeps **visual consistency** across a sequence of keyframe images and the videos generated from them (same character, style, camera angle, and world).
2. Produces a **final video longer than Veo’s per‑clip limit**, by generating multiple segments and stitching them together.

From the end user’s point of view, the Web UI should:

* Allow the user to:

  * Upload an **optional reference image** (used to anchor style and character for frame A).
  * Enter a **theme / prompt** in natural language.
  * Choose a **number of keyframes** (e.g. 3–6).
* When the user clicks a **Generate** button:

  * Generate a set of keyframe prompts with a text Gemini model.
  * Generate keyframe images with the Gemini 2.5 Flash Image model ("Nano Banana").
  * Generate short video clips for each consecutive pair of frames (A→B, B→C, …) with Veo 3.1.
  * Concatenate those clips into one longer video file (MP4).
  * Display the resulting video in the Web UI and provide a download link.

Recommended (but not mandatory) file structure for this repo:

* `app.py`
  Streamlit entrypoint (UI + calling into the pipeline).

* `video_pipeline/__init__.py`

* `video_pipeline/config.py`
  Holds configuration such as model names, environment variables, output directories, and per‑segment duration.
  It is also responsible for:

  * Exposing `get_genai_client()` (or similar),
  * Enforcing the `ENABLE_REAL_GENAI` contract (i.e. refusing to create a real network client unless that flag is set),
  * Optionally providing or delegating to fake clients for tests.

* `video_pipeline/prompts.py`
  Functions that call a Gemini text model to:

  * Optionally **describe the style** of the reference image,
  * Generate per‑frame prompts (A, B, C, …) that share a common "global style" and vary only in motion/pose.

* `video_pipeline/images.py`
  Functions that call the Gemini 2.5 Flash Image model (Nano Banana) to generate keyframe images.

* `video_pipeline/videos.py`
  Functions that call Veo 3.1 via `google-genai` to generate short clips between pairs of frames, and possibly to extend clips if needed.

* `video_pipeline/ffmpeg_utils.py`
  Functions that run `ffmpeg` to concatenate MP4 clips safely.

* `video_pipeline/run_pipeline.py`
  High‑level orchestration: theme → prompts → images → segments → final MP4.

* `tests/`
  Basic smoke tests (for example: generating prompts without hitting external APIs via fakes, or verifying that `concat_videos` joins small dummy MP4 files).

## Interfaces and Dependencies (summary)

### Environment assumptions

* Python 3.10+.
* `pip install` the following (ExecPlan should ensure a `requirements.txt` exists):

  * `google-genai`
  * `streamlit`
  * `pillow`
  * `python-dotenv`
* `ffmpeg` must be installed and available on the PATH.
* For Gemini Developer API:

  * Set environment variable `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
* For optional Vertex AI:

  * Set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
* For controlling **real API usage in this repository**:

  * Use `ENABLE_REAL_GENAI=1` to explicitly allow real network calls.
  * Leave it unset (default) to keep the system in "offline / no‑real‑API" mode, which is what automated tests should assume.

ExecPlans should decide which mode to use and state it clearly in `Context and Orientation` and `Interfaces and Dependencies`. They must also spell out:

* How `ENABLE_REAL_GENAI` gates real calls,
* Which commands require setting it (e.g. manual Streamlit demo),
* A clear warning that enabling it consumes quota / billing.

### google-genai usage (text, image, video)

ExecPlans should include concrete code examples (see `AGENTS.md` and the main ExecPlan) showing:

* How to create a `genai.Client`.
* How to:

  * Call `client.models.generate_content` for text and image.
  * Wrap reference images using `types.Part.from_bytes`.
  * Call `client.models.generate_videos` with Veo 3.1:

    * Use `image=<first_frame>`,
    * Use `GenerateVideosConfig(aspect_ratio="16:9", duration_seconds=<N>, last_frame=<last_frame>)`,
    * Poll operations until done,
    * Download the resulting file via `client.files.download`.

ExecPlans must **never** encourage using real API calls in automated tests. Instead, they must define and use fake / stub clients for tests.

### Streamlit UI

ExecPlans should document:

* Expected inputs:

  * Theme,
  * Keyframe count,
  * Optional reference image.
* Expected behavior on "Generate":

  * Call the pipeline,
  * Display progress,
  * Show a final video and download link.
* How to run the app:

  * From the repo root, with `ENABLE_REAL_GENAI=1` set in the environment.

## Example high‑level ExecPlan outline for this repo

When creating the first ExecPlan to implement the pipeline, use a description such as:

* Title: "Implement Gemini + Veo multi‑segment video generator with Streamlit UI".

* `Purpose / Big Picture`:

  * After this work, a user can open the Streamlit app, provide a theme, optional reference image, and keyframe count, and obtain a longer‑than‑Veo‑limit video that maintains a consistent character and style.

* `Plan of Work` should roughly include:

  1. Setting up the Python environment and dependencies.
  2. Implementing `video_pipeline/config.py` with `get_genai_client()` gating based on `ENABLE_REAL_GENAI`.
  3. Implementing a prompt generation module that calls a Gemini text model and returns JSON with global style and per‑frame prompts.
  4. Implementing an image generation module using Gemini 2.5 Flash Image ("Nano Banana") to produce keyframe PNG files.
  5. Implementing a video generation module using Veo 3.1 to create clips between consecutive frames.
  6. Implementing a concat module using `ffmpeg` to join the clips into a single MP4.
  7. Implementing the Streamlit UI (`app.py`) that glues user inputs to the pipeline.
  8. Adding minimal tests (with fake clients) and a validation scenario.

* `Validation and Acceptance` should include:

  * Running the Streamlit app and successfully generating at least one video with `ENABLE_REAL_GENAI=1`.
  * Verifying that the final video duration exceeds the per‑segment limit.
  * Visually checking that the character and style remain recognizably consistent across the video.
  * Ensuring automated tests pass without real API calls.

## Final notes

* When you revise this `PLANS.md`, ensure that:

  * All descriptions of library usage stay consistent with the actual code in the repo.
  * Any breaking change in folder structure or main entrypoints is reflected here.
  * Any change in how real API usage is gated (e.g. changes to `ENABLE_REAL_GENAI` logic) is documented here and in `AGENTS.md`.
* ExecPlans in this repository must never assume access to external documentation. Instead, treat this `PLANS.md` as the canonical source of truth for how to use `google-genai`, Veo, and Streamlit in this project.
* ExecPlans must be careful to **separate offline‑safe tests from online, human‑triggered integration runs**, to avoid wasting Gemini / Veo API calls.
