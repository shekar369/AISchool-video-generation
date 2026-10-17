# Project context: AI School 369 video pipeline

Read this file at the start of every session. It is the source of truth for what we are building and why.

## Purpose
A semi-automated pipeline that turns a raw idea (rough text or a voice-note transcript) into a polished, upload-ready, faceless slide video for the YouTube channel "AI School 369" (AI/ML training and career guidance). The owner reviews each video at a short review gate (target: under 30 minutes), then publishes.

## Owner constraints (design around these)
- Not a full-time creator. Very limited hands-on time per video.
- Ideas fade within hours. Capture must be effortless and rough input must be acceptable.
- Perfectionism blocks publishing. The review gate has a written "publish-ready" checklist so "done" is defined, not felt.
- No on-camera videos. Slide-based video with a natural voiceover (own cloned voice with consent, or best stock voice). Robotic TTS is not acceptable.
- No budget for an editing team. Polish comes from a fixed slide template, not per-video editing.
- Low monthly cost. Python-first (FastAPI backend, React dashboard). Must be able to run as a small service later.
- Owner is an experienced Python developer. Skip beginner explanations.

## Pipeline (9 stages, in order)
1. capture: raw idea text or voice-note transcript (human)
2. script: LLM turns the capture into a structured script, one entry per slide with narration
3. fact_check: verify technical claims and code in the script, flag uncertain items (accuracy matters for teaching content)
4. slides: render each script entry as a 1920x1080 image from a fixed HTML/CSS or Marp template
5. voice: generate audio per slide, so slide timing follows audio length
6. render: stitch images and audio with ffmpeg, simple fades, burned-in captions
7. metadata: draft title, description, chapters, tags, thumbnail text
8. review: HUMAN gate. Pipeline pauses at `awaiting_review`. Approve is only possible when every checklist item is ticked.
9. upload: YouTube Data API, uploaded as PRIVATE. Owner publishes manually.

Review checklist (all required to approve):
- Hook lands in the first 15 seconds
- Facts and code are correct
- Voice sounds natural, technical terms pronounced correctly
- Slides readable on a phone
- Title and thumbnail match the content
- It would genuinely help one learner

## Architecture
- Dashboard (React) lets the owner pick the flow per run: toggle stages, choose a provider per stage, press Run. A prototype exists as a single-file HTML mock (simulated runs) and will be rebuilt in React.
- Dashboard sends `POST /runs` with a config JSON. FastAPI creates a run folder `runs/<run_id>/` and a state file `runs/<run_id>/state.json`, then a background worker executes stages in order.
- Each stage is a Python function looked up in a provider registry: `STAGES[(stage, provider)]`. A stage reads the previous stage's outputs from the run folder and writes its own. Adding a tool means adding one function and one registry entry.
- State is resumable. Each stage has a status: idle, running, done, awaiting_review, skipped, error.
- "Redo from here" resets the chosen stage and all later stages to idle and re-runs.

Config JSON shape:

```json
{
  "channel": "AI School 369",
  "title": "Working title",
  "idea": "raw idea text",
  "stages": [
    {"stage": "script", "provider": "claude"},
    {"stage": "slides", "provider": "marp"},
    {"stage": "voice", "provider": "cloned"},
    {"stage": "render", "provider": "ffmpeg"}
  ]
}
```

Planned endpoints:
- `POST /runs` create and start a run
- `GET /runs/{id}` status of all stages (dashboard polls this)
- `POST /runs/{id}/approve` resume after the review gate
- `POST /runs/{id}/changes` request changes at the review gate
- `POST /runs/{id}/redo?from=<stage>` redo from a stage

Run folder layout: `script.json`, `fact_check.json`, `slides/*.png`, `audio/*.wav|mp3`, `video.mp4`, `metadata.json`, `state.json`.

## Provider options (keep swappable behind the registry)
- script: Claude API, local model
- slides: Marp to PNG, HTML + Playwright
- voice: cloned own voice (own voice, consent required), stock voice, local draft voice. The final voice choice is still undecided and is the most important quality decision. Do not hard-wire one vendor.
- render: ffmpeg (preferred), MoviePy
- metadata: LLM draft, manual
- upload: YouTube API (private), export files only

## Non-goals
- On-camera video, channel cloning or copying other channels' style, stock footage, viral-style subtitle effects, automatic public publishing.

## Prior art and licensing
- Ideas borrowed in spirit from two open-source projects: yt-video-factory (MIT; stage CLI, resumable run state, private-draft upload) and edu-shorts (GPLv3; rebuild-from-edited-script loop, YAML config, research step).
- Write our own code. Do not copy code from GPL projects.

## Security and repo rules
- Never commit secrets. `.env` is git-ignored; commit only `.env.example`.
- YouTube OAuth must be authorized against the AI School 369 channel's Google account (not the old UrbanSchool369 channel). Keep client ID, secret and refresh token in `.env`.
- Do not put personal emails or account identifiers in the repo.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`), one commit per working step.
- Tag milestones. Keep README clean and professional: pitch, architecture diagram, quickstart, configuration, stage list, roadmap, license.

## Milestones
- v0.1.0 scaffold: registry, state file, stub stages, API skeleton, README
- v0.2.0 script, fact_check and slides stages
- v0.3.0 voice and render stages (voice provider comparison first)
- v0.4.0 metadata, review gate, dashboard wired to the API
- v0.5.0 private YouTube upload

## Working style
- Ask before adding dependencies. Prefer small, testable functions per stage.
- Show the commit log after each milestone.
