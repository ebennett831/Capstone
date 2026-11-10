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

## Generate a pose-overlay video

`PoseVisualizer` draws confidence-filtered landmarks and MediaPipe's official
skeletal connections on copies of decoded frames. Generate the two local
development overlays from `services/backend` with:

```powershell
uv run python scripts/visualize_pose.py "data/uploads/cd6efbf3-cd26-4ee1-bfb7-9af8da86fc7e.mov"
uv run python scripts/visualize_pose.py "data/uploads/86c00cb9-a050-4fef-9950-308862bb1619.mov"
```

Outputs are written to the Git-ignored `services/backend/outputs/` directory as
`<video-name>_pose_overlay.mp4`. Existing outputs are protected unless
`--overwrite` is supplied. Use `--min-visibility` and `--min-presence` to adjust
drawing thresholds, or `--no-debug-text` to hide frame diagnostics.

Normalized coordinates become pixels using `int(x * width)` and
`int(y * height)`, clamped at the final pixel for a coordinate of exactly `1.0`.
Coordinates outside `[0.0, 1.0]` are not drawn. A connection is drawn only when
both endpoints are in bounds and satisfy available visibility and presence
thresholds. These confidences control display only; they are not measurements of
biomechanical accuracy, and the original pose results remain unchanged.

The MP4 uses OpenCV's `mp4v` codec and the source-reported FPS, falling back to
30 FPS only when the decoder reports no usable value. OpenCV preserves decoded
frame dimensions and orientation but does not copy the source audio track. Open
the resulting MP4 from the VS Code Explorer, Windows Media Player, VLC, or another
MP4-compatible player for the important visual tracking review.
