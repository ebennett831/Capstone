# AI Lacrosse Coach backend

## Inspect a local video

From `services/backend`, decode an existing locally uploaded MP4 or MOV without
starting FastAPI:

```powershell
uv run python scripts/inspect_video.py "data/uploads/<video-uuid>.mp4"
```

The command prints the container metadata and number of decoded frames. It saves
the first decoded frame under `services/backend/outputs/`, which is ignored by
Git. Use `--output path/to/frame.jpg` to choose another location.

## Inspect body-pose detection

This backend uses MediaPipe `1.2.2`, its compatible OpenCV contrib `5.0.0.93`
dependency, and the official Pose Landmarker Lite float16 version 1 model. The
model is deliberately not committed or downloaded during application startup.
Download and checksum-verify it explicitly from `services/backend`:

```powershell
uv run python scripts/download_pose_model.py
```

Then process a local upload without starting FastAPI:

```powershell
uv run python scripts/inspect_pose.py "data/uploads/<video-uuid>.mov"
```

The model is saved to the Git-ignored `services/backend/models/` directory. The
inspection command reports detection coverage as a diagnostic only; frames with
no athlete remain valid results.

`PoseTracker` rounds source timestamps to the nearest millisecond. If a timestamp
is missing, rounded to the same millisecond as the prior frame, or moves backward,
the tracker uses the prior MediaPipe timestamp plus one millisecond. The original
video timestamp is preserved separately in every result.
