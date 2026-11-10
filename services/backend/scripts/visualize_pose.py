"""Generate an MP4 video with MediaPipe body-pose overlays."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import math
import os
from pathlib import Path
import sys
from uuid import uuid4

import cv2

from backend.vision import (
    POSE_MODEL_FILENAME,
    PoseTracker,
    PoseTrackerError,
    PoseVisualizationError,
    PoseVisualizationSettings,
    PoseVisualizer,
    VideoReader,
    VideoReaderError,
)


DEFAULT_MODEL_PATH = Path(__file__).parents[1] / "models" / POSE_MODEL_FILENAME
DEFAULT_OUTPUT_DIR = Path(__file__).parents[1] / "outputs"
DEFAULT_FALLBACK_FPS = 30.0


class PoseOverlayVideoError(RuntimeError):
    """Raised when an annotated video cannot be created safely."""


@dataclass(frozen=True, slots=True)
class PoseOverlayVideoSummary:
    source_path: Path
    output_path: Path
    width: int
    height: int
    output_fps: float
    used_fps_fallback: bool
    decoded_frames: int
    detected_frames: int

    @property
    def missing_frames(self) -> int:
        return self.decoded_frames - self.detected_frames

    @property
    def detection_coverage_percent(self) -> float:
        if self.decoded_frames == 0:
            return 0.0
        return self.detected_frames / self.decoded_frames * 100


def generate_pose_overlay(
    video_path: Path,
    model_path: Path,
    output_path: Path,
    *,
    settings: PoseVisualizationSettings | None = None,
    overwrite: bool = False,
    fallback_fps: float = DEFAULT_FALLBACK_FPS,
) -> PoseOverlayVideoSummary:
    """Stream a source video through pose tracking and an MP4 overlay writer."""
    source_path = video_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if output_path.suffix.lower() != ".mp4":
        raise PoseOverlayVideoError("Pose overlay output must use the .mp4 extension.")
    if source_path == output_path:
        raise PoseOverlayVideoError("Refusing to overwrite the source video.")
    if output_path.exists() and not overwrite:
        raise PoseOverlayVideoError(
            f"Output already exists: {output_path}. Use --overwrite to replace it."
        )
    if not math.isfinite(fallback_fps) or fallback_fps <= 0:
        raise PoseOverlayVideoError("Fallback FPS must be a positive number.")

    visualizer = PoseVisualizer(settings)
    temporary_path = output_path.with_name(
        f".{output_path.stem}.{uuid4().hex}.partial.mp4"
    )
    decoded_frames = 0
    detected_frames = 0

    try:
        with VideoReader(source_path) as reader, PoseTracker(model_path) as tracker:
            width = reader.metadata.width
            height = reader.metadata.height
            if width is None or height is None:
                raise PoseOverlayVideoError(
                    "OpenCV did not report usable source video dimensions."
                )

            used_fps_fallback = reader.metadata.fps is None
            output_fps = reader.metadata.fps or fallback_fps
            output_path.parent.mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(
                str(temporary_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                output_fps,
                (width, height),
            )
            if not writer.isOpened():
                writer.release()
                raise PoseOverlayVideoError(
                    "OpenCV could not initialize the MP4 video writer for "
                    f"{output_path}."
                )

            try:
                for video_frame in reader:
                    pose_result = tracker.process(video_frame)
                    annotated = visualizer.annotate(video_frame.image, pose_result)
                    if annotated.shape[:2] != (height, width):
                        raise PoseOverlayVideoError(
                            "Annotated frame dimensions changed unexpectedly at frame "
                            f"{video_frame.index}."
                        )
                    writer.write(annotated)
                    decoded_frames += 1
                    if pose_result.pose_detected:
                        detected_frames += 1
            except cv2.error as error:
                raise PoseOverlayVideoError(
                    f"OpenCV failed while writing frame {decoded_frames}: {error}"
                ) from error
            finally:
                writer.release()

        if decoded_frames == 0:
            raise PoseOverlayVideoError("The source video contained no decoded frames.")
        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise PoseOverlayVideoError(
                "OpenCV closed the video writer without producing an output file."
            )
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return PoseOverlayVideoSummary(
        source_path=source_path,
        output_path=output_path,
        width=width,
        height=height,
        output_fps=output_fps,
        used_fps_fallback=used_fps_fallback,
        decoded_frames=decoded_frames,
        detected_frames=detected_frames,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an MP4 with MediaPipe body-pose landmarks and connections."
    )
    parser.add_argument("video_path", type=Path, help="Path to a local MP4 or MOV file.")
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Pose Landmarker model path (default: {DEFAULT_MODEL_PATH}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "MP4 output path (default: services/backend/outputs/"
            "<video-name>_pose_overlay.mp4)."
        ),
    )
    parser.add_argument(
        "--min-visibility",
        type=float,
        default=0.5,
        help="Minimum landmark visibility confidence to draw (default: 0.5).",
    )
    parser.add_argument(
        "--min-presence",
        type=float,
        default=0.5,
        help="Minimum landmark presence confidence to draw (default: 0.5).",
    )
    parser.add_argument(
        "--fallback-fps",
        type=float,
        default=DEFAULT_FALLBACK_FPS,
        help="Output FPS when the source does not report one (default: 30).",
    )
    parser.add_argument(
        "--no-debug-text",
        action="store_false",
        dest="draw_debug_text",
        help="Do not draw the frame, timestamp, and detection-status label.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace an existing output after successful processing.",
    )
    args = parser.parse_args(argv)
    output_path = args.output or (
        DEFAULT_OUTPUT_DIR / f"{args.video_path.stem}_pose_overlay.mp4"
    )

    try:
        summary = generate_pose_overlay(
            args.video_path,
            args.model,
            output_path,
            settings=PoseVisualizationSettings(
                min_visibility=args.min_visibility,
                min_presence=args.min_presence,
                draw_debug_text=args.draw_debug_text,
            ),
            overwrite=args.overwrite,
            fallback_fps=args.fallback_fps,
        )
    except (
        FileNotFoundError,
        OSError,
        PoseOverlayVideoError,
        PoseTrackerError,
        PoseVisualizationError,
        VideoReaderError,
    ) as error:
        print(f"Pose visualization failed: {error}", file=sys.stderr)
        return 1

    fps_note = " (fallback)" if summary.used_fps_fallback else ""
    print(f"Source: {summary.source_path}")
    print(f"Output: {summary.output_path}")
    print(f"Dimensions: {summary.width} x {summary.height}")
    print(f"Output FPS: {summary.output_fps:g}{fps_note}")
    print(f"Frames written: {summary.decoded_frames}")
    print(f"Frames with a detected pose: {summary.detected_frames}")
    print(f"Frames with no detected pose: {summary.missing_frames}")
    print(f"Pose detection coverage: {summary.detection_coverage_percent:.1f}%")
    print("Audio: not copied (OpenCV VideoWriter writes video frames only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
