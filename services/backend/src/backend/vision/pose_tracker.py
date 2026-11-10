"""Run MediaPipe Pose Landmarker on decoded video frames."""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
import math
from os import PathLike
from pathlib import Path

import cv2
import mediapipe as mp

from backend.vision.video_reader import VideoFrame


POSE_MODEL_FILENAME = "pose_landmarker_lite.task"
POSE_MODEL_VARIANT = "Pose Landmarker Lite float16 v1"


class PoseTrackerError(RuntimeError):
    """Base error for pose model setup, processing, or cleanup failures."""


class PoseModelError(PoseTrackerError):
    """Raised when the Pose Landmarker model cannot be loaded."""


class PoseProcessingError(PoseTrackerError):
    """Raised when MediaPipe cannot process a decoded video frame."""


@dataclass(frozen=True, slots=True)
class PoseLandmark:
    """One MediaPipe landmark in the coordinate space named by its parent field."""

    index: int
    x: float | None
    y: float | None
    z: float | None
    visibility: float | None
    presence: float | None


@dataclass(frozen=True, slots=True)
class PoseFrameResult:
    """Pose information for one video frame, without retaining its image.

    ``normalized_landmarks`` contains image-relative coordinates. In that set,
    x and y are normalized by image dimensions and z is relative depth. The
    separate ``world_landmarks`` collection contains MediaPipe's estimated 3D
    coordinates in meters relative to the midpoint of the hips.
    """

    frame_index: int
    video_timestamp_seconds: float | None
    mediapipe_timestamp_ms: int
    pose_detected: bool
    normalized_landmarks: tuple[PoseLandmark, ...] | None
    world_landmarks: tuple[PoseLandmark, ...] | None


class PoseTracker:
    """Synchronously estimate one body pose per frame with MediaPipe Tasks."""

    def __init__(self, model_path: str | PathLike[str]) -> None:
        path = Path(model_path).expanduser()
        if not path.exists():
            raise PoseModelError(f"Pose Landmarker model does not exist: {path}")
        if not path.is_file():
            raise PoseModelError(f"Pose Landmarker model path is not a file: {path}")

        self.model_path = path.resolve()
        self._last_mediapipe_timestamp_ms: int | None = None
        self._closed = False
        try:
            self._landmarker = _create_landmarker(self.model_path)
        except (OSError, RuntimeError, ValueError) as error:
            raise PoseModelError(
                f"MediaPipe could not load the Pose Landmarker model "
                f"{self.model_path}: {error}"
            ) from error

    @property
    def is_open(self) -> bool:
        """Whether this tracker can still process frames."""
        return not self._closed

    def process(self, frame: VideoFrame) -> PoseFrameResult:
        """Convert and process one BGR frame while preserving its source position."""
        if self._closed:
            raise PoseTrackerError("Cannot process a frame with a closed pose tracker.")

        mediapipe_timestamp_ms = self._next_mediapipe_timestamp_ms(
            frame.timestamp_seconds
        )
        try:
            rgb_image = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
            mediapipe_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_image,
            )
            result = self._landmarker.detect_for_video(
                mediapipe_image,
                mediapipe_timestamp_ms,
            )
        except (cv2.error, RuntimeError, ValueError) as error:
            raise PoseProcessingError(
                f"MediaPipe failed while processing video frame {frame.index}: {error}"
            ) from error

        normalized_landmarks = _first_pose_landmarks(result.pose_landmarks)
        world_landmarks = _first_pose_landmarks(result.pose_world_landmarks)
        return PoseFrameResult(
            frame_index=frame.index,
            video_timestamp_seconds=frame.timestamp_seconds,
            mediapipe_timestamp_ms=mediapipe_timestamp_ms,
            pose_detected=(
                normalized_landmarks is not None or world_landmarks is not None
            ),
            normalized_landmarks=normalized_landmarks,
            world_landmarks=world_landmarks,
        )

    def process_frames(self, frames: Iterable[VideoFrame]) -> Iterator[PoseFrameResult]:
        """Process decoded frames sequentially without accumulating results."""
        for frame in frames:
            yield self.process(frame)

    def close(self) -> None:
        """Release MediaPipe's native task resources. Calling this twice is safe."""
        if self._closed:
            return
        try:
            self._landmarker.close()
        except RuntimeError as error:
            raise PoseTrackerError(f"MediaPipe failed to close cleanly: {error}") from error
        finally:
            self._closed = True

    def __enter__(self) -> "PoseTracker":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _next_mediapipe_timestamp_ms(
        self,
        video_timestamp_seconds: float | None,
    ) -> int:
        if (
            video_timestamp_seconds is not None
            and math.isfinite(video_timestamp_seconds)
            and video_timestamp_seconds >= 0
        ):
            candidate = int(math.floor(video_timestamp_seconds * 1_000 + 0.5))
        elif self._last_mediapipe_timestamp_ms is None:
            candidate = 0
        else:
            candidate = self._last_mediapipe_timestamp_ms + 1

        if (
            self._last_mediapipe_timestamp_ms is not None
            and candidate <= self._last_mediapipe_timestamp_ms
        ):
            candidate = self._last_mediapipe_timestamp_ms + 1

        self._last_mediapipe_timestamp_ms = candidate
        return candidate


def _create_landmarker(model_path: Path) -> mp.tasks.vision.PoseLandmarker:
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        output_segmentation_masks=False,
    )
    return mp.tasks.vision.PoseLandmarker.create_from_options(options)


def _first_pose_landmarks(
    poses: Sequence[
        Sequence[
            mp.tasks.components.containers.NormalizedLandmark
            | mp.tasks.components.containers.Landmark
        ]
    ],
) -> tuple[PoseLandmark, ...] | None:
    if not poses or not poses[0]:
        return None

    return tuple(
        PoseLandmark(
            index=index,
            x=_optional_float(landmark.x),
            y=_optional_float(landmark.y),
            z=_optional_float(landmark.z),
            visibility=_optional_float(landmark.visibility),
            presence=_optional_float(landmark.presence),
        )
        for index, landmark in enumerate(poses[0])
    )


def _optional_float(value: float | None) -> float | None:
    return None if value is None else float(value)
