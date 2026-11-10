"""Draw MediaPipe pose results on copies of decoded OpenCV frames."""

from dataclasses import dataclass
import math

import cv2
import mediapipe as mp
import numpy as np

from backend.vision.pose_tracker import PoseFrameResult, PoseLandmark


POSE_CONNECTIONS = tuple(
    (connection.start, connection.end)
    for connection in mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS
)


class PoseVisualizationError(ValueError):
    """Raised when a frame or visualization setting cannot be rendered."""


@dataclass(frozen=True, slots=True)
class PoseVisualizationSettings:
    """Confidence and styling options for a body-pose overlay.

    Colors use OpenCV's BGR channel order. Confidence thresholds affect only
    drawing; the underlying ``PoseFrameResult`` is never altered.
    """

    min_visibility: float = 0.5
    min_presence: float = 0.5
    landmark_color: tuple[int, int, int] = (0, 255, 255)
    connection_color: tuple[int, int, int] = (255, 180, 0)
    outline_color: tuple[int, int, int] = (0, 0, 0)
    text_color: tuple[int, int, int] = (255, 255, 255)
    draw_debug_text: bool = True
    landmark_radius_scale: float = 0.004
    connection_thickness_scale: float = 0.002

    def __post_init__(self) -> None:
        for name, value in (
            ("min_visibility", self.min_visibility),
            ("min_presence", self.min_presence),
        ):
            if not 0 <= value <= 1:
                raise PoseVisualizationError(f"{name} must be between 0 and 1.")
        if self.landmark_radius_scale <= 0:
            raise PoseVisualizationError("landmark_radius_scale must be positive.")
        if self.connection_thickness_scale <= 0:
            raise PoseVisualizationError(
                "connection_thickness_scale must be positive."
            )
        for name, color in (
            ("landmark_color", self.landmark_color),
            ("connection_color", self.connection_color),
            ("outline_color", self.outline_color),
            ("text_color", self.text_color),
        ):
            if len(color) != 3 or any(channel < 0 or channel > 255 for channel in color):
                raise PoseVisualizationError(
                    f"{name} must contain three values between 0 and 255."
                )


class PoseVisualizer:
    """Render pose landmarks and official skeletal connections on a frame copy."""

    def __init__(
        self,
        settings: PoseVisualizationSettings | None = None,
        *,
        connections: tuple[tuple[int, int], ...] = POSE_CONNECTIONS,
    ) -> None:
        self.settings = settings or PoseVisualizationSettings()
        self.connections = connections

    def annotate(
        self,
        frame: cv2.typing.MatLike,
        result: PoseFrameResult,
    ) -> np.ndarray:
        """Return an annotated copy while leaving the source frame and pose intact."""
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
            raise PoseVisualizationError(
                "Pose visualization requires a three-channel OpenCV frame."
            )

        annotated = frame.copy()
        height, width = annotated.shape[:2]
        if width <= 0 or height <= 0:
            raise PoseVisualizationError("Pose visualization requires a nonempty frame.")

        drawable_points = self._drawable_points(
            result.normalized_landmarks if result.pose_detected else None,
            width=width,
            height=height,
        )
        shortest_dimension = min(width, height)
        radius = max(
            2,
            int(round(shortest_dimension * self.settings.landmark_radius_scale)),
        )
        connection_thickness = max(
            1,
            int(
                round(
                    shortest_dimension
                    * self.settings.connection_thickness_scale
                )
            ),
        )
        outline_thickness = max(1, connection_thickness)

        for start_index, end_index in self.connections:
            start = drawable_points.get(start_index)
            end = drawable_points.get(end_index)
            if start is None or end is None:
                continue
            cv2.line(
                annotated,
                start,
                end,
                self.settings.outline_color,
                connection_thickness + outline_thickness * 2,
                cv2.LINE_AA,
            )
            cv2.line(
                annotated,
                start,
                end,
                self.settings.connection_color,
                connection_thickness,
                cv2.LINE_AA,
            )

        for point in drawable_points.values():
            cv2.circle(
                annotated,
                point,
                radius + outline_thickness,
                self.settings.outline_color,
                cv2.FILLED,
                cv2.LINE_AA,
            )
            cv2.circle(
                annotated,
                point,
                radius,
                self.settings.landmark_color,
                cv2.FILLED,
                cv2.LINE_AA,
            )

        if self.settings.draw_debug_text:
            self._draw_debug_text(annotated, result)
        return annotated

    def _drawable_points(
        self,
        landmarks: tuple[PoseLandmark, ...] | None,
        *,
        width: int,
        height: int,
    ) -> dict[int, tuple[int, int]]:
        if not landmarks:
            return {}

        points: dict[int, tuple[int, int]] = {}
        for landmark in landmarks:
            if not _meets_threshold(
                landmark.visibility,
                self.settings.min_visibility,
            ) or not _meets_threshold(
                landmark.presence,
                self.settings.min_presence,
            ):
                continue
            point = normalized_to_pixel(
                landmark.x,
                landmark.y,
                width=width,
                height=height,
            )
            if point is not None:
                points[landmark.index] = point
        return points

    def _draw_debug_text(
        self,
        frame: np.ndarray,
        result: PoseFrameResult,
    ) -> None:
        height, width = frame.shape[:2]
        shortest_dimension = min(width, height)
        font_scale = max(0.4, min(1.0, shortest_dimension / 900))
        text_thickness = max(1, int(round(shortest_dimension / 700)))
        margin = max(6, int(round(shortest_dimension * 0.012)))
        timestamp = (
            f"{result.video_timestamp_seconds:.3f}s"
            if result.video_timestamp_seconds is not None
            else "unknown"
        )
        detection = "pose detected" if result.pose_detected else "no pose"
        label = f"Frame {result.frame_index} | {timestamp} | {detection}"
        (text_width, text_height), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_thickness,
        )
        cv2.rectangle(
            frame,
            (margin // 2, margin // 2),
            (
                min(width - 1, margin + text_width),
                min(height - 1, margin + text_height + baseline),
            ),
            self.settings.outline_color,
            cv2.FILLED,
        )
        cv2.putText(
            frame,
            label,
            (margin, min(height - 1, margin + text_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            self.settings.text_color,
            text_thickness,
            cv2.LINE_AA,
        )


def normalized_to_pixel(
    x: float | None,
    y: float | None,
    *,
    width: int,
    height: int,
) -> tuple[int, int] | None:
    """Convert normalized image coordinates to an in-bounds pixel position."""
    if width <= 0 or height <= 0:
        raise PoseVisualizationError("Frame width and height must be positive.")
    if x is None or y is None or not math.isfinite(x) or not math.isfinite(y):
        return None
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        return None
    return (
        min(int(x * width), width - 1),
        min(int(y * height), height - 1),
    )


def _meets_threshold(value: float | None, threshold: float) -> bool:
    return value is None or (math.isfinite(value) and value >= threshold)
