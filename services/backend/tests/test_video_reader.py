import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.vision import VideoReader, VideoReaderError


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "inspect_video.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("inspect_video_script", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(SCRIPT_MODULE)
inspect_video = SCRIPT_MODULE.inspect_video


def _write_test_video(
    path: Path,
    *,
    width: int = 64,
    height: int = 48,
    fps: float = 10.0,
    frame_count: int = 4,
) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        pytest.skip("The installed OpenCV backend cannot encode temporary test videos.")

    try:
        for index in range(frame_count):
            image = np.full((height, width, 3), index * 50, dtype=np.uint8)
            writer.write(image)
    finally:
        writer.release()


@pytest.mark.parametrize("extension", [".mp4", ".mov"])
def test_reads_video_metadata_and_frames(tmp_path: Path, extension: str):
    video_path = tmp_path / f"clip{extension}"
    _write_test_video(video_path)

    with VideoReader(video_path) as reader:
        assert reader.metadata.path == video_path.resolve()
        assert reader.metadata.width == 64
        assert reader.metadata.height == 48
        assert reader.metadata.fps == pytest.approx(10.0)
        assert reader.metadata.reported_frame_count == 4
        assert reader.metadata.estimated_duration_seconds == pytest.approx(0.4)

        frames = list(reader)

    assert not reader.is_open
    assert [frame.index for frame in frames] == [0, 1, 2, 3]
    assert [frame.timestamp_seconds for frame in frames] == pytest.approx(
        [0.0, 0.1, 0.2, 0.3]
    )
    assert all(frame.image.shape == (48, 64, 3) for frame in frames)


def test_releases_capture_when_iteration_stops_early(tmp_path: Path):
    video_path = tmp_path / "clip.mp4"
    _write_test_video(video_path)

    with VideoReader(video_path) as reader:
        frame = reader.read()
        assert frame is not None
        assert frame.index == 0
        assert reader.is_open

    assert not reader.is_open


def test_nonexistent_video_is_rejected(tmp_path: Path):
    missing_path = tmp_path / "missing.mp4"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        VideoReader(missing_path)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("empty.mp4", b""),
        ("corrupted.mp4", b"not a video"),
        ("unsupported.mov", b"not a supported MOV codec"),
    ],
)
def test_invalid_video_is_rejected(tmp_path: Path, filename: str, content: bytes):
    video_path = tmp_path / filename
    video_path.write_bytes(content)

    with pytest.raises(VideoReaderError):
        with VideoReader(video_path) as reader:
            reader.read()


def test_inspection_script_decodes_video_and_saves_frame(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    video_path = tmp_path / "clip.mp4"
    output_path = tmp_path / "inspection" / "frame.jpg"
    _write_test_video(video_path)

    decoded_count = inspect_video(video_path, output_path)

    output = capsys.readouterr().out
    assert decoded_count == 4
    assert "Dimensions: 64 x 48" in output
    assert "Decoded frames: 4" in output
    saved_image = cv2.imread(str(output_path))
    assert saved_image is not None
    assert saved_image.shape == (48, 64, 3)
