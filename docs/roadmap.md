# AI Lacrosse Coach - Roadmap and Milestones

**Updated:** November 9, 2026
**Repository:** https://github.com/ebennett831/Capstone

## Project goal

Build a smartphone application that accepts lacrosse shots and dodges, extracts interpretable movement data, and eventually provides feedback supported by reproducible computer vision or evaluated models.

Engineering principles:

- Build and verify a real end-to-end boundary before adding complexity.
- Keep mobile UI, HTTP, storage, vision, and analysis responsibilities separate.
- Do not claim AI, scores, or completion states that do not exist.
- Test upload, persistence, frame processing, and model quality independently.
- Protect athlete videos with explicit storage and deletion behavior.

## Milestone overview

| Milestone | Outcome | State |
| --- | --- | --- |
| 1 - Foundation | Expo and FastAPI communicate; reproducible setup/tests | Complete |
| 2 - Video pipeline | Select/record, preview, upload, persist, list, and delete | Implemented; physical-device verification pending |
| 3 - Pose extraction | Inspectable landmarks and optional overlay | Planned |
| 4 - Movement features + dataset | Reproducible calculations and labeled clips | Planned |
| 5 - Single-movement classification | Evaluated baseline for a limited action set | Planned |
| 6+ - Coaching/production | Evidence-based feedback and justified infrastructure | Future |

## Milestone 1 - Foundation

Completed:

- [x] Expo Router + React Native + TypeScript mobile app.
- [x] FastAPI backend managed with uv.
- [x] `GET /health` with a real phone-to-development-computer request.
- [x] Machine-specific API URL through ignored `.env.local`.
- [x] Reproducible Windows CMD setup.
- [x] pytest health coverage and mobile TypeScript checks.

## Milestone 2 - Video pipeline

Goal: a user explicitly selects or records a clip, previews it locally, uploads it to FastAPI, and manages truthful persisted metadata without any fake computer-vision output.

Implemented:

- [x] Photos video selection with Expo ImagePicker; no media-library deletion.
- [x] In-app CameraView recording with camera/microphone permissions, ready/recording states, native progress, and a central 20-second limit.
- [x] Local playback through `useVideoPlayer` and `VideoView`.
- [x] Explicit Upload, Retake/Replace, Discard, retry, progress, duplicate-press protection, cancellation, and timeout handling.
- [x] Current `File.createUploadTask()` multipart API; no base64 or whole-video JS buffering.
- [x] App-owned temporary recording cleanup after success/discard/retake; retention after failure.
- [x] `POST /api/v1/analyses` with typed source and optional timezone-aware timestamp.
- [x] MP4/MOV extension, declared MIME, nonempty, 100 MB, and basic `ftyp` validation.
- [x] Bounded 1 MB upload reads, temporary staging, and atomic publish.
- [x] UUID filenames, JSON metadata, UTC timestamps, and only the status `uploaded`.
- [x] Newest-first list, detail, individual delete, and safe stale-metadata cleanup.
- [x] My Uploads loading, empty, refresh, network-error, local-date, and confirmed-delete states.
- [x] Guarded command-line bulk cleanup with dry-run and explicit `DELETE` confirmation.
- [x] Runtime upload, metadata, and legacy analysis folders excluded from Git.
- [x] Backend tests isolated under pytest `tmp_path`.
- [x] Expo SDK 58 type, lint, and compatibility validation.

Remaining acceptance work:

- [ ] Run the physical-iPhone checklist in the root README against a real MP4 and MOV.
- [ ] Confirm CameraView recording is not added to Photos on the test iPhone.
- [ ] Observe the device-specific picker URI and multipart progress behavior.
- [ ] Confirm temporary recording cleanup on the test iPhone after a real successful upload.

Milestone 2 limitations:

- The `ftyp` check confirms a plausible container header, not complete decodability.
- Photos recording time remains unknown unless a reliable picker result supplies it; filesystem modification time is never substituted.
- Upload history is metadata-only. Backend video streaming is deliberately absent.
- The local unauthenticated server is for trusted development only.
- App drafts are not a persistent offline queue; the OS may clear temporary cache files.

## Milestone 3 - Pose extraction baseline

Goal: run a repeatable computer-vision pipeline on a stored upload.

- [ ] Decode frames and timestamps with OpenCV.
- [ ] Estimate body landmarks with a documented MediaPipe model/version.
- [ ] Record confidence, occlusion, and unusable-frame behavior.
- [ ] Normalize coordinates and document camera-angle limitations.
- [ ] Produce structured landmarks and an inspectable overlay.
- [ ] Introduce truthful queued/processing/completed/failed states only with real processing.
- [ ] Move CPU-heavy work out of the upload request when needed.

## Milestone 4 - Movement features and dataset

- [ ] Define measurable angles, orientation proxies, and timing features.
- [ ] Document units, smoothing, missing frames, and camera assumptions.
- [ ] Establish a standardized recording guide.
- [ ] Define consent, retention, athlete/session labels, and evaluation splits.
- [ ] Inspect feature calculations against real video.

## Milestone 5 - Individual movement recognition

- [ ] Start with a small, accurately labeled action set and simple baseline.
- [ ] Split evaluation by athlete/session to reduce leakage.
- [ ] Report per-class metrics, a confusion matrix, and failure modes.
- [ ] Version models, feature definitions, and datasets.
- [ ] Present uncertainty rather than invented precision.

## Future work

Only after the measured core pipeline justifies it:

- Lacrosse-stick keypoint detection.
- Movement segmentation and multi-move sequences.
- Feedback tied to verifiable observations.
- Validated progress/history features.
- Accounts, authentication, PostgreSQL, object storage, deployment, and retention automation.

### Future Enhancement — Video Favorites, Retention & Camera Roll Saving

**Status:** Planned — Production-level feature  
**Priority:** Low for now; revisit after the computer vision and analysis pipeline is functional.

**Goal:** Give athletes control over which videos they keep while preventing unnecessary video storage buildup.

#### 1. Optional Save to Photos

- [ ] Add a **Save to Photos** button to the in-app recording preview.
- [ ] Allow users to save recordings to their device's camera roll before uploading or discarding them.
- [ ] Request appropriate photo-library permissions when needed.
- [ ] Confirm that the video was saved successfully.
- [ ] Keep saving optional; recordings should **never automatically be added to Photos**.
- [ ] Preserve the existing temporary-recording cleanup behavior after successful uploads.

**Implementation consideration:** Investigate Expo MediaLibrary's supported `saveToLibraryAsync()` API when this feature is implemented.

#### 2. Favorite Uploaded Videos

- [ ] Add a star/favorite button to each video in My Uploads.
- [ ] Store an `is_favorite` flag in the video's metadata.
- [ ] Allow users to favorite and unfavorite videos.
- [ ] Clearly distinguish favorite videos in the upload history.
- [ ] Exclude favorited videos from automatic retention-based deletion.
- [ ] Keep explicit manual deletion available with confirmation.

#### 3. Automatic Video Retention

- [ ] Introduce a configurable retention period for non-favorited uploaded videos.
- [ ] Consider a **30-day default**, subject to future product decisions.
- [ ] Automatically delete expired, non-favorited videos.
- [ ] Remove associated metadata and generated analysis artifacts when deleting expired videos.
- [ ] Ensure cleanup never deletes videos actively being uploaded or processed.
- [ ] Show upload dates and scheduled deletion dates in My Uploads.
- [ ] Clearly communicate the retention policy before enabling automatic deletion.
- [ ] Require appropriate authentication, authorization, and ownership checks before deploying retention management for multiple users.

#### 4. Storage Management

- [ ] Display the total amount of video storage used.
- [ ] Allow filtering by Favorites, Recent Uploads, and Expiring Soon.
- [ ] Provide a way to manually delete unwanted uploads.
- [ ] Ensure any future bulk-deletion feature clearly explains whether favorites are protected.
- [ ] Investigate cloud object storage and scheduled cleanup only when production infrastructure is needed.

#### Design Principles

- **User control:** Athletes decide which videos are important enough to save or favorite.
- **Storage efficiency:** Non-favorited videos should not accumulate indefinitely.
- **Data integrity:** Video deletion must also handle associated analysis data correctly.
- **Privacy:** Videos must not be saved, shared, or retained unexpectedly.
- **Simplicity:** Do not introduce production retention infrastructure before the core analysis pipeline works.

**Current implementation:** Milestone 2 already supports local video uploads, individual deletion, and a developer-only clear-all utility. These features remain unchanged until production-level video management is implemented.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-11-09 | Expo + TypeScript mobile, FastAPI + uv backend | Appropriate mobile workflow and future Python CV integration |
| 2026-11-09 | Local files + JSON for Milestone 2 | Durable restart behavior without premature infrastructure |
| 2026-11-09 | Current Expo File upload-task API | Native multipart progress/cancellation without JS video buffering |
| 2026-11-09 | Basic ISO-BMFF header validation only | Adds a real content check without premature FFmpeg/OpenCV dependencies |
| 2026-11-09 | Only `uploaded` status | Processing does not exist yet |
| 2026-11-09 | No Photos recording-time guess | Modification time is not original capture time |
| 2026-11-09 | No bulk-delete HTTP route | Local maintenance does not belong on an unauthenticated network endpoint |
