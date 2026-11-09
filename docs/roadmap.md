# AI Lacrosse Coach — Roadmap and Milestones

**Updated:** November 9, 2026<br>
**Repository:** https://github.com/ebennett831/Capstone<br>
**Approach:** Learn the system architecture and data flow while using AI assistance for UI and routine implementation.

## 1. Project goal

Build a smartphone application that accepts videos of lacrosse shots and dodges, extracts interpretable movement data, and eventually delivers useful coaching feedback. Longer-term possibilities include stick tracking, recognition of multi-move sequences, athlete history, and progress tracking.

**North star:** A user can submit an actual clip and receive an analysis whose outputs are backed by reproducible computer vision or evaluated models, rather than placeholder scores.

### Engineering principles

- **End-to-end first:** Make each stage work with real data before expanding its complexity.
- **Separate responsibilities:** Mobile UI, HTTP API, video processing, and ML code should remain distinguishable.
- **No fake AI:** Explicitly label unimplemented features; avoid invented form/explosiveness scores.
- **Test each boundary:** Verify networking, upload, frame processing, and model results independently.
- **Document decisions:** Record tradeoffs, limitations, bugs, and what was learned.
- **Protect athlete data:** Use consent, storage controls, and a deletion plan before collecting a dataset.

## 2. Milestone overview

| Milestone | Outcome | State |
| --- | --- | --- |
| **1 — Foundation** | Expo app and FastAPI server communicate; tests and docs added | **In progress — core flow works** |
| **2 — Video upload** | Upload a real phone video and retrieve job status | Planned |
| **3 — Pose extraction** | Inspectable landmarks and optional overlay from video | Planned |
| **4 — Movement features + dataset** | Reproducible calculations and consistently labeled clips | Planned |
| **5 — Single-movement classification** | Evaluated baseline recognizing supported actions | Planned |
| **6+ — Coaching and production features** | Stick tracking, sequences, validated feedback, cloud services | Future / scope-dependent |

These are **technical milestones**, not promised calendar dates. Scope depends on data quality, capstone requirements, and available time.

## 3. Milestone 1 — Foundation (current)

**Goal:** Two independent applications in one GitHub monorepo; the phone sends a real HTTP request and displays the response from FastAPI.

### Completed

- [x] Create and clone the new GitHub repository.
- [x] Scaffold the React Native + Expo + TypeScript mobile app.
- [x] Launch the app on an iPhone using Expo Go.
- [x] Initialize the Python backend with uv and a `src/backend` package.
- [x] Implement `GET /health` returning `{"status":"ok","service":"AI Lacrosse Coach API"}`.
- [x] Run FastAPI locally using Uvicorn.
- [x] Reach `/health` from the iPhone over the local network.
- [x] Call `/health` from React Native and display connected/error/loading states.
- [x] Review `.gitignore` and push the initial working commit.

### Finish before calling Milestone 1 done

- [ ] Add a root `README.md` with reproducible **Windows CMD** setup instructions.
- [ ] Commit `docs/roadmap.md` and `docs/architecture.md`.
- [ ] Add `apps/mobile/.env.example` and verify `.env.local` remains ignored.
- [ ] Add a `pytest`/`httpx` health endpoint test.
- [ ] Run `npx tsc --noEmit` and the backend tests; fix actual failures.
- [ ] Add a basic GitHub Actions CI workflow for frontend type checks and backend tests (recommended; can be completed as follow-up cleanup).

**Definition of done:** Another developer can clone the repo, follow the README, start both apps, call `/health`, and run the tests without needing the original machine's hidden settings.

**Concepts to know:** Monorepo, React state, frontend vs. backend, REST/HTTP GET, JSON, local IP vs. `localhost`, package managers, Git, basic test assertions.

## 4. Milestone 2 — Video upload

**Goal:** Select a video on the phone, upload it to FastAPI, store it safely, and show its real upload state.

### Build

- [ ] Add a mobile video picker and an upload screen.
- [ ] Define `POST /api/v1/analyses` to accept multipart video uploads.
- [ ] Validate content type, maximum size, and basic video readability; handle errors clearly.
- [ ] Save uploads to a Git-ignored local directory using generated IDs (not untrusted filenames).
- [ ] Return an analysis ID and a truthful initial status (such as `uploaded`).
- [ ] Add `GET /api/v1/analyses/{id}` to read status/metadata.
- [ ] Show upload progress, success, and failure in the mobile app.
- [ ] Add endpoint tests for valid and invalid uploads.

**Definition of done:** One real video from the iPhone reaches the backend, is persisted locally, and can be referenced by an analysis ID. **No computer vision is claimed yet.**

**Key learning:** Multipart HTTP, file I/O, API schemas, client/server validation, safe filenames, and response codes.

## 5. Milestone 3 — Pose extraction baseline

**Goal:** Run a repeatable computer vision pipeline on an uploaded video.

### Build

- [ ] Use OpenCV to decode video frames and capture timestamps.
- [ ] Use MediaPipe Pose Landmarker to estimate body landmarks.
- [ ] Track detection confidence/visibility and clearly report unusable frames.
- [ ] Normalize pose coordinates; document normalization method and limitations.
- [ ] Save structured per-frame data and generate a visual overlay for inspection.
- [ ] Define analysis job statuses (for example `uploaded`, `processing`, `completed`, `failed`).
- [ ] Move CPU-heavy work out of the HTTP request handler into an appropriate worker when necessary.
- [ ] Test against varied real clips, including occlusion and poor camera angles.

**Definition of done:** A real clip produces viewable landmarks and structured output, with explicit failures if detection is unreliable.

**Key learning:** Video frame rate, frame coordinates, model confidence, data pipelines, and background jobs.

## 6. Milestone 4 — Biomechanics features and dataset

**Goal:** Convert landmarks into explainable features and begin assembling a trustworthy labeled dataset.

### Build

- [ ] Define a limited set of measurable features (joint angles, torso orientation, hip/shoulder rotation proxies, timing).
- [ ] Document coordinate systems, units, smoothing, missing-frame behavior, and camera-angle sensitivity.
- [ ] Establish a standardized phone recording guide (full body, useful angle, consistent framing).
- [ ] Define clip labels and athlete/session metadata with consent and retention rules.
- [ ] Collect representative clips from different athletes and conditions.
- [ ] Build a repeatable labeling and train/validation/test split process.

**Definition of done:** Features are reproducible, interpretable, and inspected against videos; labels and splits are documented.

**Key learning:** Signal processing, biomechanics assumptions, dataset bias, label quality, and evaluation design.

## 7. Milestone 5 — Individual movement recognition

**Goal:** Classify a **small, clearly defined** set of single-movement clips using measured results.

Potential actions: overhand shot, sidearm shot, underhand shot, split dodge, roll dodge, face dodge. Start with fewer classes if the dataset is limited.

### Build

- [ ] Establish a simple baseline before trying a Transformer or other complex architecture.
- [ ] Evaluate on held-out athletes/sessions to reduce data leakage.
- [ ] Report per-class metrics, confusion matrix, and common failure modes.
- [ ] Version models, feature definitions, and evaluation datasets.
- [ ] Display classifications with uncertainty/limitations rather than implying certainty.

**Definition of done:** A measured and repeatable classifier performs meaningfully on held-out videos, with limitations documented.

**Key learning:** Model training, temporal data, overfitting, metrics, and generalization.

## 8. Milestone 6+ — Stretch goals and long-term vision

Potential directions, prioritized by capstone timeline and evidence:

- Custom lacrosse-stick keypoint detection (head, shaft midpoint, butt end).
- Movement segmentation and multi-movement sequence recognition.
- Coaching explanations tied to verifiable motion observations.
- Technique/form assessment validated with knowledgeable coaches.
- Explosiveness **proxies** (not claims of actual speed without calibration).
- Accounts, saved sessions, history, and progress charts.
- PostgreSQL, object storage, deployment, observability, and retention controls.

**Do not begin these before the core pipeline and dataset quality justify them.**

## 9. Current next actions

1. Add the three project documents in this package: root README, roadmap, architecture.
2. Add `.env.example` and a backend health test; run the checks locally.
3. Make a small **Milestone 1 completion** commit.
4. Design the upload request/response and local storage conventions for Milestone 2.
5. Implement a video upload **without** computer vision first.

## 10. Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-11-09 | Fresh repository instead of continuing the old prototype | Simpler foundation and clearer ownership of each component |
| 2026-11-09 | Expo + React Native + TypeScript for mobile | Shared mobile codebase and easy device testing |
| 2026-11-09 | Python + FastAPI + uv for backend | Straightforward API development and future CV/ML integration |
| 2026-11-09 | Keep one monorepo with two independently running apps | Low infrastructure complexity and clear boundaries |
| 2026-11-09 | Milestone 1 ends at a real health check from the phone | Proves networking before introducing video or AI |
| 2026-11-09 | Use AI for UI and scaffolding but learn architecture/data flow | Prioritizes practical understanding and demonstrable engineering decisions |

## 11. Reference material

The original capstone concept envisioned ten phases, including body pose estimation, stick tracking, biomechanics, temporal classification, scoring, and sequence coaching. The previous prototype has Python pose-processing ideas to reassess in Milestone 3; it should **not** be copied wholesale into the new repo.

See [architecture.md](architecture.md) for the system design and [../README.md](../README.md) for local setup.
