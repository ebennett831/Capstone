# AI Lacrosse Coach

**A mobile-first capstone project for analyzing lacrosse movement from video.**

The project is being built in honest, testable stages: device-to-backend networking, a safe video pipeline, computer vision, motion features, and evaluated machine learning only when the data supports it.

> **Status (November 9, 2026):** Milestone 2 is implemented in code. The Expo app can select or record and preview short clips, upload them with progress, and manage upload metadata. FastAPI stores MP4/MOV files and JSON metadata locally. Automated checks pass; the physical-iPhone checklist below still needs to be run. Pose estimation, movement recognition, scoring, and coaching feedback are not implemented.

## Technology stack

| Part | Technology | Responsibility |
| --- | --- | --- |
| Mobile | React Native, Expo SDK 58, TypeScript, Expo Router | Selection, recording, preview, upload, and history UI |
| Device media | Expo Camera, ImagePicker, Video, FileSystem | Supported native media and transfer APIs |
| Backend | Python 3.13+, FastAPI, Uvicorn | HTTP validation and upload orchestration |
| Backend environment | uv | Dependencies and reproducible lockfile |
| Milestone 2 persistence | Local files and JSON | Development-only videos and metadata |
| Computer vision (planned) | OpenCV, MediaPipe | Future frame decoding and body landmarks |

No database, cloud storage, Docker, queue, authentication system, or AI inference is used in Milestone 2.

## Repository layout

```text
Capstone/
|-- apps/mobile/
|   |-- src/app/              # Home, Record / Upload, My Uploads
|   |-- src/components/       # Video preview and upload cards
|   |-- src/lib/              # API, formatting, and configuration
|   |-- src/types/            # Shared mobile analysis types
|   |-- app.json              # Expo permissions/plugins
|   `-- package.json
|-- services/backend/
|   |-- src/backend/
|   |   |-- api/              # FastAPI routes
|   |   |-- schemas/          # Pydantic public/internal models
|   |   |-- services/         # Upload/list/delete orchestration
|   |   `-- storage/          # Constrained filesystem and JSON access
|   |-- scripts/              # Guarded clear-all maintenance script
|   |-- tests/                # Isolated API/storage tests
|   |-- data/                 # Runtime uploads + metadata (Git-ignored)
|   `-- pyproject.toml
|-- docs/
|   |-- architecture.md
|   `-- roadmap.md
`-- .gitignore
```

## Run locally on Windows (Command Prompt)

### Prerequisites

- Git
- Node.js and npm
- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Expo Go on a physical phone, or a compatible simulator/emulator

Use separate CMD terminals for the backend and Expo. The commands assume the repository root is the current directory.

### Backend: install, test, and start

```cmd
cd services\backend
uv sync
uv run pytest
uv run uvicorn backend.main:app --reload --host 0.0.0.0
```

The development server uses port 8000:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

`--host 0.0.0.0` permits trusted-LAN access. Do not port-forward or publicly deploy this unauthenticated development server.

### Mobile: install, check, and start

Create `apps\mobile\.env.local` from `.env.example`, replacing the placeholder with the computer's active LAN IPv4 address:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.105:8000
```

Then run:

```cmd
cd apps\mobile
npm ci
npx tsc --noEmit
npx expo lint
npx expo-doctor
npx expo start
```

Find the computer's current address with `ipconfig`. A real phone must use that address; `localhost` on the phone means the phone. If `.env.local` changes, restart with `npx expo start --clear`.

The app has **Home**, **Record / Upload**, and **My Uploads** tabs. Home retains the Milestone 1 backend health check in a small development card.

## Video workflow

```text
Record a temporary clip or select a Photos video
  -> preview locally with expo-video
  -> explicitly tap Upload
  -> expo-file-system streams multipart data with progress/cancellation
  -> FastAPI validates extension, MIME type, size, and the ftyp container box
  -> UUID-named video and JSON metadata are atomically published
  -> the API returns truthful status "uploaded"
  -> My Uploads displays or deletes the persisted metadata
```

The mobile client reads only `EXPO_PUBLIC_API_URL`; components do not hardcode a development computer address. Binary videos are never converted to base64 or placed in JSON.

### API contract

| Method | Path | Success behavior |
| --- | --- | --- |
| `GET` | `/health` | `200` health JSON |
| `POST` | `/api/v1/analyses` | `201` upload metadata |
| `GET` | `/api/v1/analyses` | `200 {"items":[...]}` newest-first |
| `GET` | `/api/v1/analyses/{analysis_id}` | `200` one metadata record |
| `DELETE` | `/api/v1/analyses/{analysis_id}` | `204` after video and metadata deletion |

The upload is `multipart/form-data` with:

- `video`: required MP4 or MOV file
- `source`: required `in_app_camera` or `photo_library`
- `recorded_at`: optional timezone-aware timestamp
- `original_filename`: optional, validated display-only name used because a device picker may upload a cache filename

Example `201 Created` response:

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "overhand-shot.mov",
  "source": "in_app_camera",
  "recorded_at": "2026-11-10T01:15:00Z",
  "uploaded_at": "2026-11-10T01:15:30Z",
  "file_size_bytes": 12582912,
  "content_type": "video/quicktime",
  "status": "uploaded"
}
```

No internal path or stored filename is returned. Invalid UUID path parameters receive `422`; unknown valid UUIDs receive `404`.

## Local storage, validation, and deletion

- Videos: `services/backend/data/uploads/<uuid>.mp4|mov`
- Metadata: `services/backend/data/metadata/<uuid>.json`
- Maximum upload: 100 MB, read and written in bounded 1 MB chunks.
- A video is staged under a temporary generated name, validated, then published with `os.replace()`.
- JSON is written to a temporary file and atomically published with `os.replace()`.
- Only server-generated filenames are resolved for deletion. A stale metadata record is safely removed even if its video is already missing.
- Listing order uses backend-generated `uploaded_at`, newest first.
- Runtime data folders are Git-ignored.

Header validation confirms a basic ISO base media `ftyp` box. That is stronger than trusting a filename/MIME type, but it does **not** prove the complete file is playable. Full decoding validation is deferred until the computer-vision milestone rather than adding FFmpeg or OpenCV here.

Delete an individual item in **My Uploads**. For local bulk maintenance, first stop the FastAPI server and make sure no upload is in progress. The cleanup utility also removes managed `.uploading` temporary files, so running it beside an active server could race an in-flight upload.

Then run from `services\backend`:

```cmd
uv run python scripts\clear_uploads.py --dry-run
uv run python scripts\clear_uploads.py
```

The second command lists the managed count and requires typing `DELETE`. It cannot accept an arbitrary directory, and there is intentionally no bulk-delete HTTP endpoint.

## Timestamps and temporary media

- `uploaded_at` is generated by FastAPI with `datetime.now(timezone.utc)` only after the video is stored.
- In-app `recorded_at` is captured immediately before `recordAsync()` begins.
- Photos selection sends `null` because modification time is not treated as original capture time.
- The backend rejects naive timestamps and normalizes valid values to UTC.
- My Uploads displays dates with the device's local timezone through `Intl.DateTimeFormat`.

Expo Camera records to app temporary storage and never calls a Photos save API. Successful upload, Retake, and Discard delete only an app-owned recording. Failed or cancelled uploads keep the draft for retry. Selected Photos assets are never deleted. The operating system may independently clear temporary cache files.

## Manual iPhone verification checklist

These physical-device checks are not claimed as passed by the automated implementation:

1. Start FastAPI and open `/health` from the iPhone browser over the trusted LAN.
2. Select an MP4/MOV from Photos, preview/play it, and upload it.
3. Confirm a UUID video exists under `data\uploads` and matching JSON under `data\metadata`.
4. Inspect source, size, `recorded_at`, UTC `uploaded_at`, and `uploaded` status.
5. Record an in-app clip, stop it, preview it, and upload it.
6. Confirm the in-app recording was **not** added to Photos and its temporary draft disappears after success.
7. Stop FastAPI, attempt an upload, confirm the draft remains, restart FastAPI, and retry.
8. Delete one item from My Uploads and confirm both managed backend files disappear.
9. Restart FastAPI and verify remaining history persists.
10. Run the cleanup command with `--dry-run` and confirm it changes nothing.
11. Run `git status --short --ignored` and confirm runtime videos, JSON, and `.env.local` are ignored.

## Privacy and limitations

- Process only videos you have permission to use.
- `EXPO_PUBLIC_` variables are bundled into the app and must never contain secrets.
- The local API has no user ownership or authentication; keep it on a trusted development network.
- The only successful analysis state today is `uploaded`. No processing, classification, score, or coaching result is fabricated.
- A single phone camera cannot automatically provide calibrated 3D motion or real physical speed.

See [the roadmap](docs/roadmap.md) and [architecture notes](docs/architecture.md) for milestone boundaries and design decisions.
