from pathlib import Path

import numpy as np
import pytest

from backend.vision import (
    PoseFrameResult,
    PoseLandmark,
    PoseVisualizationError,
    PoseVisualizationSettings,
    PoseVisualizer,
    normalized_to_pixel,
)


def _landmark(
    index: int,
    x: float,
    y: float,
    *,
    visibility: float | None = 0.9,
    presence: float | None = 0.9,
) -> PoseLandmark:
    return PoseLandmark(
        index=index,
        x=x,
        y=y,
        z=0.0,
        visibility=visibility,
        presence=presence,
    )


def _result(
    landmarks: tuple[PoseLandmark, ...] | None,
    *,
    frame_index: int = 4,
    timestamp: float | None = 0.2,
) -> PoseFrameResult:
    return PoseFrameResult(
        frame_index=frame_index,
        video_timestamp_seconds=timestamp,
        mediapipe_timestamp_ms=200,
        pose_detected=landmarks is not None,
        normalized_landmarks=landmarks,
        world_landmarks=None,
    )


def _visualizer(**settings) -> PoseVisualizer:
    return PoseVisualizer(
        PoseVisualizationSettings(draw_debug_text=False, **settings)
    )


def test_normalized_landmarks_convert_to_pixels():
    assert normalized_to_pixel(0.5, 0.25, width=100, height=200) == (50, 50)
    assert normalized_to_pixel(0.0, 0.0, width=100, height=200) == (0, 0)
    assert normalized_to_pixel(1.0, 1.0, width=100, height=200) == (99, 199)
    assert normalized_to_pixel(-0.01, 0.5, width=100, height=200) is None
    assert normalized_to_pixel(0.5, 1.01, width=100, height=200) is None
    assert normalized_to_pixel(float("nan"), 0.5, width=100, height=200) is None
    assert normalized_to_pixel(None, 0.5, width=100, height=200) is None


def test_visualizer_draws_landmarks_and_connections_without_mutating_source():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    landmarks = (
        _landmark(11, 0.25, 0.5),
        _landmark(12, 0.75, 0.5),
    )

    annotated = _visualizer().annotate(frame, _result(landmarks))

    assert annotated.shape == frame.shape
    assert not np.shares_memory(annotated, frame)
    assert np.count_nonzero(annotated) > 0
    assert np.count_nonzero(frame) == 0
    assert np.count_nonzero(annotated[50, 100]) > 0


def test_no_pose_returns_an_unchanged_frame_copy():
    frame = np.full((60, 80, 3), 27, dtype=np.uint8)

    annotated = _visualizer().annotate(frame, _result(None))

    np.testing.assert_array_equal(annotated, frame)
    assert not np.shares_memory(annotated, frame)


def test_low_confidence_and_out_of_bounds_landmarks_are_not_drawn():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    landmarks = (
        _landmark(11, 0.25, 0.5),
        _landmark(12, 0.75, 0.5, visibility=0.1),
        _landmark(13, 1.2, 0.4),
        _landmark(14, 0.5, -0.2),
    )

    annotated = _visualizer(min_visibility=0.5).annotate(
        frame,
        _result(landmarks),
    )

    assert np.count_nonzero(annotated[50, 25]) > 0
    assert np.count_nonzero(annotated[50, 50]) == 0
    assert np.count_nonzero(annotated[50, 75]) == 0


def test_missing_confidence_is_drawn_when_coordinates_are_valid():
    frame = np.zeros((50, 50, 3), dtype=np.uint8)
    landmark = _landmark(0, 0.5, 0.5, visibility=None, presence=None)

    annotated = _visualizer().annotate(frame, _result((landmark,)))

    assert np.count_nonzero(annotated[25, 25]) > 0


@pytest.mark.parametrize(
    ("height", "width"),
    [(120, 60), (60, 120)],
    ids=["portrait", "landscape"],
)
def test_visualizer_preserves_portrait_and_landscape_dimensions(
    height: int,
    width: int,
):
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    annotated = _visualizer().annotate(
        frame,
        _result((_landmark(0, 0.5, 0.5),)),
    )

    assert annotated.shape == (height, width, 3)
    assert np.count_nonzero(annotated[height // 2, width // 2]) > 0


def test_debug_text_can_describe_a_missing_pose():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    visualizer = PoseVisualizer(PoseVisualizationSettings(draw_debug_text=True))

    annotated = visualizer.annotate(frame, _result(None))

    assert np.count_nonzero(annotated) > 0


def test_invalid_visualization_inputs_are_rejected():
    with pytest.raises(PoseVisualizationError, match="between 0 and 1"):
        PoseVisualizationSettings(min_visibility=1.1)
    with pytest.raises(PoseVisualizationError, match="positive"):
        normalized_to_pixel(0.5, 0.5, width=0, height=10)
    with pytest.raises(PoseVisualizationError, match="three-channel"):
        _visualizer().annotate(np.zeros((10, 10), dtype=np.uint8), _result(None))
