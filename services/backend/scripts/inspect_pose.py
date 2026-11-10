"""Run Pose Landmarker over a local video and report detection coverage."""

import argparse
from collections.abc import Sequence
import hashlib
from pathlib import Path
import sys

import mediapipe as mp

from backend.vision import (
    POSE_MODEL_FILENAME,
    POSE_MODEL_VARIANT,
    PoseFrameResult,
    PoseTracker,
    PoseTrackerError,
    VideoReader,
    VideoReaderError,
)


DEFAULT_MODEL_PATH = Path(__file__).parents[1] / "models" / POSE_MODEL_FILENAME


def inspect_pose(video_path: Path, model_path: Path) -> tuple[int, int]:
    """Process a video sequentially and print pose detection diagnostics."""
    total_frames = 0
    detected_frames = 0
    example: PoseFrameResult | None = None

    print(f"MediaPipe version: {mp.__version__}")
    print(f"Model: {POSE_MODEL_VARIANT}")
    print(f"Model path: {model_path.expanduser().resolve()}")
    print(f"Model SHA-256: {_sha256(model_path)}")

    with VideoReader(video_path) as reader, PoseTracker(model_path) as tracker:
        print(f"Video: {reader.metadata.path}")
        for pose_result in tracker.process_frames(reader):
            total_frames += 1
            if pose_result.pose_detected:
                detected_frames += 1
                if example is None:
                    example = pose_result

    missing_frames = total_frames - detected_frames
    coverage = detected_frames / total_frames * 100 if total_frames else 0.0
    print(f"Total decoded frames: {total_frames}")
    print(f"Frames with a detected pose: {detected_frames}")
    print(f"Frames with no detected pose: {missing_frames}")
    print(f"Pose detection coverage: {coverage:.1f}%")
    _print_example(example)
    return total_frames, detected_frames


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect MediaPipe body-pose detection coverage for a local video."
    )
    parser.add_argument("video_path", type=Path, help="Path to a local MP4 or MOV file.")
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Pose Landmarker model path (default: {DEFAULT_MODEL_PATH}).",
    )
    args = parser.parse_args(argv)

    try:
        inspect_pose(args.video_path, args.model)
    except (FileNotFoundError, OSError, PoseTrackerError, VideoReaderError) as error:
        print(f"Pose inspection failed: {error}", file=sys.stderr)
        return 1
    return 0


def _print_example(result: PoseFrameResult | None) -> None:
    if result is None or result.normalized_landmarks is None:
        print("Example landmarks: no pose was detected in this video")
        return

    landmark = result.normalized_landmarks[0]
    print(
        "Example normalized landmark: "
        f"frame={result.frame_index}, timestamp={result.video_timestamp_seconds}, "
        f"index={landmark.index}, x={landmark.x}, y={landmark.y}, z={landmark.z}, "
        f"visibility={landmark.visibility}, presence={landmark.presence}"
    )
    if result.world_landmarks:
        world = result.world_landmarks[0]
        print(
            "Example world landmark: "
            f"index={world.index}, x={world.x}, y={world.y}, z={world.z}, "
            f"visibility={world.visibility}, presence={world.presence}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.expanduser().open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
