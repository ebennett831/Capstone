import struct

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


def make_iso_bmff_header(major_brand: bytes) -> bytes:
    payload = major_brand + b"\x00\x00\x00\x00" + major_brand + b"isom"
    return struct.pack(">I4s", len(payload) + 8, b"ftyp") + payload


@pytest.fixture
def mp4_bytes() -> bytes:
    return make_iso_bmff_header(b"isom") + b"\x00" * 32


@pytest.fixture
def mov_bytes() -> bytes:
    return make_iso_bmff_header(b"qt  ") + b"\x00" * 32


@pytest.fixture
def client(tmp_path) -> TestClient:
    return TestClient(create_app(data_root=tmp_path))


def upload_video(
    client: TestClient,
    content: bytes,
    *,
    filename: str = "practice.mp4",
    content_type: str = "video/mp4",
    source: str = "photo_library",
    recorded_at: str | None = None,
):
    data = {"source": source}
    if recorded_at is not None:
        data["recorded_at"] = recorded_at
    return client.post(
        "/api/v1/analyses",
        data=data,
        files={"video": (filename, content, content_type)},
    )
