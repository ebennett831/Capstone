"""Decode a local video and save its first frame for visual inspection."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

import cv2

from backend.vision import VideoReader, VideoReaderError


DEFAULT_OUTPUT_DIR = Path(__file__).parents[1] / "outputs"


def inspect_video(video_path: Path, output_path: Path) -> int:
    """Print metadata, decode all frames, and save the first decoded frame."""
    with VideoReader(video_path) as reader:
        metadata = reader.metadata
        print(f"Video: {metadata.path}")
        print(f"Dimensions: {_format_dimensions(metadata.width, metadata.height)}")
        print(f"Reported FPS: {_format_number(metadata.fps)}")
        print(f"Reported frame count: {_format_number(metadata.reported_frame_count)}")
        print(
            "Estimated duration: "
            f"{_format_seconds(metadata.estimated_duration_seconds)}"
        )

        decoded_frame_count = 0
        saved_frame_index: int | None = None
        for frame in reader:
            if saved_frame_index is None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(output_path), frame.image):
                    raise OSError(f"OpenCV could not write the frame image: {output_path}")
                saved_frame_index = frame.index
            decoded_frame_count += 1

    print(f"Decoded frames: {decoded_frame_count}")
    print(f"Saved frame {saved_frame_index} to: {output_path.resolve()}")
    return decoded_frame_count


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a local video with OpenCV and save the first decoded frame."
        )
    )
    parser.add_argument("video_path", type=Path, help="Path to a local MP4 or MOV file.")
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "JPEG output path (default: services/backend/outputs/"
            "<video-name>_inspection.jpg)."
        ),
    )
    args = parser.parse_args(argv)
    output_path = args.output or (
        DEFAULT_OUTPUT_DIR / f"{args.video_path.stem}_inspection.jpg"
    )

    try:
        inspect_video(args.video_path, output_path)
    except (FileNotFoundError, OSError, VideoReaderError) as error:
        print(f"Video inspection failed: {error}", file=sys.stderr)
        return 1
    return 0


def _format_dimensions(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return "unknown"
    return f"{width} x {height}"


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:g}"


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.3f} seconds"


if __name__ == "__main__":
    raise SystemExit(main())
