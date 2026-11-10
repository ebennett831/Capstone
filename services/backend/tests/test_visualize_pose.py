import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.vision import PoseFrameResult, PoseVisualizationSettings
from backend.vision import VideoFrame


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "visualize_pose.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("visualize_pose_script", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(SCRIPT_MODULE)
generate_pose_overlay = SCRIPT_MODULE.generate_pose_overlay
PoseOverlayVideoError = SCRIPT_MODULE.PoseOverlayVideoError


class FakePoseTracker:
    def __init__(self, _model_path: Path):
        self.closed = False

    def process(self, frame):
        return PoseFrameResult(
            frame_index=frame.index,
            video_timestamp_seconds=frame.timestamp_seconds,
            mediapipe_timestamp_ms=frame.index,
            pose_detected=False,
            normalized_landmarks=None,
            world_landmarks=None,
        )

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _write_test_video(
    path: Path,
    *,
    width: int,
    height: int,
    frame_count: int = 4,
    fps: float = 10.0,
) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        pytest.skip("The installed OpenCV backend cannot encode test MP4 videos.")
    try:
        for index in range(frame_count):
            frame = np.full((height, width, 3), index * 40, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


@pytest.mark.parametrize(
    ("width", "height"),
    [(48, 64), (64, 48)],
    ids=["portrait", "landscape"],
)
def test_generated_video_preserves_dimensions_and_frame_count(
    monkeypatch,
    tmp_path: Path,
    width: int,
    height: int,
):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    _write_test_video(source, width=width, height=height)
    monkeypatch.setattr(SCRIPT_MODULE, "PoseTracker", FakePoseTracker)

    summary = generate_pose_overlay(
        source,
        tmp_path / "unused-model.task",
        output,
        settings=PoseVisualizationSettings(draw_debug_text=False),
    )

    capture = cv2.VideoCapture(str(output))
    assert capture.isOpened()
    try:
        decoded_frames = 0
        while True:
            decoded, frame = capture.read()
            if not decoded:
                break
            decoded_frames += 1
            assert frame.shape == (height, width, 3)
    finally:
        capture.release()

    assert summary.decoded_frames == 4
    assert summary.detected_frames == 0
    assert summary.width == width
    assert summary.height == height
    assert summary.output_fps == pytest.approx(10.0)
    assert not summary.used_fps_fallback
    assert decoded_frames == 4


def test_writer_initialization_failure_releases_resources(
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    _write_test_video(source, width=64, height=48, frame_count=1)
    monkeypatch.setattr(SCRIPT_MODULE, "PoseTracker", FakePoseTracker)

    class ClosedWriter:
        def __init__(self):
            self.released = False

        def isOpened(self):
            return False

        def release(self):
            self.released = True

    closed_writer = ClosedWriter()
    monkeypatch.setattr(
        SCRIPT_MODULE.cv2,
        "VideoWriter",
        lambda *_args, **_kwargs: closed_writer,
    )

    with pytest.raises(PoseOverlayVideoError, match="could not initialize"):
        generate_pose_overlay(
            source,
            tmp_path / "unused-model.task",
            output,
        )

    assert closed_writer.released
    assert not output.exists()
    assert list(tmp_path.glob("*.partial.mp4")) == []


def test_missing_source_fps_uses_fallback_and_releases_writer(
    monkeypatch,
    tmp_path: Path,
):
    output = tmp_path / "output.mp4"

    class FakeReader:
        def __init__(self, source_path: Path):
            self.metadata = type(
                "Metadata",
                (),
                {"width": 8, "height": 6, "fps": None, "path": source_path},
            )()

        def __iter__(self):
            yield VideoFrame(
                index=0,
                timestamp_seconds=None,
                image=np.zeros((6, 8, 3), dtype=np.uint8),
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

    class OpenWriter:
        def __init__(self, path: str):
            self.path = Path(path)
            self.released = False
            self.frames = 0

        def isOpened(self):
            return True

        def write(self, _frame):
            self.frames += 1

        def release(self):
            self.released = True
            self.path.write_bytes(b"synthetic MP4")

    writers: list[OpenWriter] = []

    def open_writer(path, *_args, **_kwargs):
        writer = OpenWriter(path)
        writers.append(writer)
        return writer

    monkeypatch.setattr(SCRIPT_MODULE, "VideoReader", FakeReader)
    monkeypatch.setattr(SCRIPT_MODULE, "PoseTracker", FakePoseTracker)
    monkeypatch.setattr(SCRIPT_MODULE.cv2, "VideoWriter", open_writer)

    summary = generate_pose_overlay(
        tmp_path / "source.mov",
        tmp_path / "model.task",
        output,
        settings=PoseVisualizationSettings(draw_debug_text=False),
        fallback_fps=24.0,
    )

    assert summary.output_fps == 24.0
    assert summary.used_fps_fallback
    assert summary.decoded_frames == 1
    assert output.read_bytes() == b"synthetic MP4"
    assert writers[0].released
    assert writers[0].frames == 1


def test_existing_output_and_source_overwrite_are_rejected(tmp_path: Path):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    source.write_bytes(b"source")
    output.write_bytes(b"existing")

    with pytest.raises(PoseOverlayVideoError, match="already exists"):
        generate_pose_overlay(source, tmp_path / "model.task", output)
    with pytest.raises(PoseOverlayVideoError, match="source video"):
        generate_pose_overlay(
            source,
            tmp_path / "model.task",
            source,
            overwrite=True,
        )
