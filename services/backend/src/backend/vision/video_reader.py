"""Stream frames and metadata from a local video with OpenCV."""

from collections.abc import Iterator
from dataclasses import dataclass
import math
from os import PathLike
from pathlib import Path

import cv2


class VideoReaderError(RuntimeError):
    """Base error for videos that OpenCV cannot read."""


class VideoOpenError(VideoReaderError):
    """Raised when OpenCV cannot open a local video file."""


class VideoDecodeError(VideoReaderError):
    """Raised when an opened video does not contain a decodable frame."""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Container metadata reported by the active OpenCV video backend."""

    path: Path
    width: int | None
    height: int | None
    fps: float | None
    reported_frame_count: int | None

    @property
    def estimated_duration_seconds(self) -> float | None:
        """Estimate duration from reported FPS and frame count, when usable."""
        if self.fps is None or self.reported_frame_count is None:
            return None
        return self.reported_frame_count / self.fps


@dataclass(frozen=True, slots=True)
class VideoFrame:
    """One decoded BGR image and its position in the video."""

    index: int
    timestamp_seconds: float | None
    image: cv2.typing.MatLike


class VideoReader:
    """Read a local video sequentially without loading it all into memory.

    Use this class as a context manager so the native ``VideoCapture`` resource
    is released even if frame processing raises or stops early.
    """

    def __init__(self, video_path: str | PathLike[str]) -> None:
        path = Path(video_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Video file does not exist: {path}")
        if not path.is_file():
            raise VideoOpenError(f"Video path is not a file: {path}")

        self.path = path.resolve()
        try:
            self._capture = cv2.VideoCapture(str(self.path))
        except cv2.error as error:
            raise VideoOpenError(
                f"OpenCV failed while opening the video: {self.path}: {error}"
            ) from error
        self._next_frame_index = 0
        self._finished = False

        if not self._capture.isOpened():
            self._capture.release()
            raise VideoOpenError(
                f"OpenCV could not open the video; it may be empty, corrupted, "
                f"or use an unsupported container or codec: {self.path}"
            )

        self.metadata = VideoMetadata(
            path=self.path,
            width=_positive_int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=_positive_int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=_positive_float(self._capture.get(cv2.CAP_PROP_FPS)),
            reported_frame_count=_positive_int(
                self._capture.get(cv2.CAP_PROP_FRAME_COUNT)
            ),
        )

    @property
    def is_open(self) -> bool:
        """Whether the underlying OpenCV capture is still open."""
        return self._capture.isOpened()

    def read(self) -> VideoFrame | None:
        """Decode the next frame, returning ``None`` after the end of the clip."""
        if self._finished:
            return None
        if not self.is_open:
            raise VideoReaderError("Cannot read from a closed video reader.")

        try:
            decoded, image = self._capture.read()
        except cv2.error as error:
            self.close()
            raise VideoDecodeError(
                f"OpenCV failed while decoding frame {self._next_frame_index} "
                f"from {self.path}: {error}"
            ) from error

        if not decoded or image is None:
            failed_on_first_frame = self._next_frame_index == 0
            self._finished = True
            self.close()
            if failed_on_first_frame:
                raise VideoDecodeError(
                    "OpenCV opened the video but could not decode its first frame: "
                    f"{self.path}"
                )
            return None

        frame = VideoFrame(
            index=self._next_frame_index,
            timestamp_seconds=self._current_timestamp_seconds(),
            image=image,
        )
        self._next_frame_index += 1
        return frame

    def frames(self) -> Iterator[VideoFrame]:
        """Yield decoded frames sequentially until OpenCV reaches the end."""
        while (frame := self.read()) is not None:
            yield frame

    def __iter__(self) -> Iterator[VideoFrame]:
        return self.frames()

    def close(self) -> None:
        """Release the native decoder resource. Calling this twice is safe."""
        self._capture.release()

    def __enter__(self) -> "VideoReader":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _current_timestamp_seconds(self) -> float | None:
        timestamp_milliseconds = self._capture.get(cv2.CAP_PROP_POS_MSEC)
        if math.isfinite(timestamp_milliseconds) and timestamp_milliseconds > 0:
            return timestamp_milliseconds / 1_000

        # Some OpenCV backends do not expose per-frame timestamps. Reported FPS
        # gives a useful presentation-time estimate for constant-frame-rate video.
        if self.metadata.fps is not None:
            return self._next_frame_index / self.metadata.fps

        if (
            self._next_frame_index == 0
            and math.isfinite(timestamp_milliseconds)
            and timestamp_milliseconds == 0
        ):
            return 0.0
        return None


def _positive_float(value: float) -> float | None:
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _positive_int(value: float) -> int | None:
    positive_value = _positive_float(value)
    if positive_value is None:
        return None
    return int(round(positive_value))
