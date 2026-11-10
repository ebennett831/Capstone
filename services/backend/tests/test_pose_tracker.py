import json
from dataclasses import asdict
from pathlib import Path

import mediapipe as mp
import numpy as np
import pytest

import backend.vision.pose_tracker as pose_tracker_module
from backend.vision import (
    POSE_MODEL_FILENAME,
    PoseModelError,
    PoseProcessingError,
    PoseTracker,
    PoseTrackerError,
    VideoFrame,
)


MODEL_PATH = Path(__file__).parents[1] / "models" / POSE_MODEL_FILENAME


class FakeLandmarker:
    def __init__(self, results=None, error: Exception | None = None):
        self.results = list(results or [])
        self.error = error
        self.calls: list[tuple[np.ndarray, int]] = []
        self.close_count = 0

    def detect_for_video(self, image: mp.Image, timestamp_ms: int):
        self.calls.append((np.array(image.numpy_view(), copy=True), timestamp_ms))
        if self.error is not None:
            raise self.error
        if self.results:
            return self.results.pop(0)
        return _pose_result()

    def close(self) -> None:
        self.close_count += 1


@pytest.fixture
def model_path(tmp_path: Path) -> Path:
    path = tmp_path / "model.task"
    path.write_bytes(b"test model placeholder")
    return path


def _pose_result(
    normalized=None,
    world=None,
) -> mp.tasks.vision.PoseLandmarkerResult:
    return mp.tasks.vision.PoseLandmarkerResult(
        pose_landmarks=[] if normalized is None else [normalized],
        pose_world_landmarks=[] if world is None else [world],
    )


def _frame(
    index: int = 7,
    timestamp_seconds: float | None = 1.25,
    image: np.ndarray | None = None,
) -> VideoFrame:
    if image is None:
        image = np.zeros((2, 2, 3), dtype=np.uint8)
    return VideoFrame(index=index, timestamp_seconds=timestamp_seconds, image=image)


def _install_fake(monkeypatch, fake: FakeLandmarker) -> None:
    monkeypatch.setattr(
        pose_tracker_module,
        "_create_landmarker",
        lambda _: fake,
    )


def test_converts_pose_result_and_preserves_frame_position(
    monkeypatch, model_path: Path
):
    normalized = [
        mp.tasks.components.containers.NormalizedLandmark(
            x=index / 100,
            y=index / 50,
            z=-index / 100,
            visibility=0.9,
            presence=0.8,
        )
        for index in range(33)
    ]
    world = [
        mp.tasks.components.containers.Landmark(
            x=index / 10,
            y=index / 20,
            z=index / 30,
            visibility=0.7,
            presence=0.6,
        )
        for index in range(33)
    ]
    fake = FakeLandmarker([_pose_result(normalized, world)])
    _install_fake(monkeypatch, fake)

    with PoseTracker(model_path) as tracker:
        result = tracker.process(_frame())

    assert result.frame_index == 7
    assert result.video_timestamp_seconds == 1.25
    assert result.mediapipe_timestamp_ms == 1250
    assert result.pose_detected
    assert result.normalized_landmarks is not None
    assert result.world_landmarks is not None
    assert len(result.normalized_landmarks) == 33
    assert len(result.world_landmarks) == 33
    assert result.normalized_landmarks[12].x == pytest.approx(0.12)
    assert result.world_landmarks[12].x == pytest.approx(1.2)
    assert "image" not in asdict(result)
    json.dumps(asdict(result))


def test_no_pose_is_explicit_and_does_not_stop_later_detection(
    monkeypatch, model_path: Path
):
    landmark = mp.tasks.components.containers.NormalizedLandmark(x=0.5, y=0.4)
    fake = FakeLandmarker([_pose_result(), _pose_result([landmark])])
    _install_fake(monkeypatch, fake)

    with PoseTracker(model_path) as tracker:
        results = list(
            tracker.process_frames(
                [_frame(0, 0.0), _frame(1, 1 / 30)],
            )
        )

    assert not results[0].pose_detected
    assert results[0].normalized_landmarks is None
    assert results[0].world_landmarks is None
    assert results[1].pose_detected
    assert results[1].normalized_landmarks is not None


def test_partially_visible_landmark_confidence_is_preserved(
    monkeypatch, model_path: Path
):
    partial = mp.tasks.components.containers.NormalizedLandmark(
        x=1.2,
        y=-0.1,
        z=0.3,
        visibility=0.08,
        presence=0.15,
    )
    fake = FakeLandmarker([_pose_result([partial])])
    _install_fake(monkeypatch, fake)

    with PoseTracker(model_path) as tracker:
        result = tracker.process(_frame())

    assert result.normalized_landmarks is not None
    landmark = result.normalized_landmarks[0]
    assert landmark.x == pytest.approx(1.2)
    assert landmark.y == pytest.approx(-0.1)
    assert landmark.visibility == pytest.approx(0.08)
    assert landmark.presence == pytest.approx(0.15)


def test_converts_opencv_bgr_to_mediapipe_rgb(monkeypatch, model_path: Path):
    fake = FakeLandmarker()
    _install_fake(monkeypatch, fake)
    bgr = np.array([[[10, 20, 30]]], dtype=np.uint8)

    with PoseTracker(model_path) as tracker:
        tracker.process(_frame(image=bgr))

    converted_image, _ = fake.calls[0]
    np.testing.assert_array_equal(converted_image, np.array([[[30, 20, 10]]]))


def test_mediapipe_timestamps_are_strictly_increasing(
    monkeypatch, model_path: Path
):
    fake = FakeLandmarker()
    _install_fake(monkeypatch, fake)
    frames = [
        _frame(0, 0.0),
        _frame(1, 0.0004),
        _frame(2, 0.0004),
        _frame(3, None),
        _frame(4, 0.01),
    ]

    with PoseTracker(model_path) as tracker:
        results = list(tracker.process_frames(frames))

    assert [result.video_timestamp_seconds for result in results] == [
        0.0,
        0.0004,
        0.0004,
        None,
        0.01,
    ]
    assert [result.mediapipe_timestamp_ms for result in results] == [0, 1, 2, 3, 10]
    assert [timestamp for _, timestamp in fake.calls] == [0, 1, 2, 3, 10]


def test_context_manager_releases_media_pipe_resources(
    monkeypatch, model_path: Path
):
    fake = FakeLandmarker()
    _install_fake(monkeypatch, fake)

    with PoseTracker(model_path) as tracker:
        assert tracker.is_open

    assert not tracker.is_open
    assert fake.close_count == 1
    tracker.close()
    assert fake.close_count == 1


def test_missing_and_invalid_models_report_loading_errors(
    monkeypatch, tmp_path: Path, model_path: Path
):
    with pytest.raises(PoseModelError, match="does not exist"):
        PoseTracker(tmp_path / "missing.task")

    monkeypatch.setattr(
        pose_tracker_module,
        "_create_landmarker",
        lambda _: (_ for _ in ()).throw(RuntimeError("invalid model bundle")),
    )
    with pytest.raises(PoseModelError, match="invalid model bundle"):
        PoseTracker(model_path)


def test_processing_errors_include_frame_index(monkeypatch, model_path: Path):
    fake = FakeLandmarker(error=RuntimeError("inference failed"))
    _install_fake(monkeypatch, fake)

    with PoseTracker(model_path) as tracker:
        with pytest.raises(PoseProcessingError, match="video frame 7"):
            tracker.process(_frame())


def test_closed_tracker_rejects_processing(monkeypatch, model_path: Path):
    fake = FakeLandmarker()
    _install_fake(monkeypatch, fake)
    tracker = PoseTracker(model_path)
    tracker.close()

    with pytest.raises(PoseTrackerError, match="closed"):
        tracker.process(_frame())


@pytest.mark.model
@pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="Official Pose Landmarker model has not been downloaded.",
)
def test_official_model_loads_and_processes_one_frame():
    black_frame = np.zeros((64, 64, 3), dtype=np.uint8)

    with PoseTracker(MODEL_PATH) as tracker:
        result = tracker.process(_frame(index=0, timestamp_seconds=0.0, image=black_frame))

    assert result.frame_index == 0
    assert result.mediapipe_timestamp_ms == 0
    assert not result.pose_detected
