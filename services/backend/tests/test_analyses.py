import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.analysis_service import AnalysisService
from backend.storage.local_storage import LocalStorage
from conftest import upload_video


@pytest.mark.parametrize(
    ("fixture_name", "filename", "content_type"),
    [
        ("mp4_bytes", "overhand-shot.mp4", "video/mp4"),
        ("mov_bytes", "overhand-shot.mov", "video/quicktime"),
    ],
)
def test_valid_mp4_and_mov_uploads(
    request,
    client: TestClient,
    tmp_path: Path,
    fixture_name: str,
    filename: str,
    content_type: str,
):
    content = request.getfixturevalue(fixture_name)
    response = upload_video(
        client,
        content,
        filename=filename,
        content_type=content_type,
        source="in_app_camera",
        recorded_at="2026-11-09T20:15:00-05:00",
    )

    assert response.status_code == 201
    body = response.json()
    analysis_id = UUID(body["analysis_id"])
    assert body == {
        "analysis_id": str(analysis_id),
        "original_filename": filename,
        "source": "in_app_camera",
        "recorded_at": "2026-11-10T01:15:00Z",
        "uploaded_at": body["uploaded_at"],
        "file_size_bytes": len(content),
        "content_type": content_type,
        "status": "uploaded",
    }
    assert datetime.fromisoformat(body["uploaded_at"].replace("Z", "+00:00")).tzinfo
    assert (tmp_path / "uploads" / f"{analysis_id}{Path(filename).suffix}").read_bytes() == content
    metadata = json.loads((tmp_path / "metadata" / f"{analysis_id}.json").read_text())
    assert metadata["stored_filename"] == f"{analysis_id}{Path(filename).suffix}"


def test_generated_analysis_id_is_a_uuid(client: TestClient, mp4_bytes: bytes):
    response = upload_video(client, mp4_bytes)
    assert response.status_code == 201
    assert str(UUID(response.json()["analysis_id"])) == response.json()["analysis_id"]


def test_optional_original_filename_is_display_only(client: TestClient, mp4_bytes: bytes):
    response = client.post(
        "/api/v1/analyses",
        data={
            "source": "photo_library",
            "original_filename": "library-shot.mp4",
        },
        files={"video": ("picker-cache-name.mp4", mp4_bytes, "video/mp4")},
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "library-shot.mp4"


def test_metadata_persists_when_storage_is_recreated(tmp_path: Path, mp4_bytes: bytes):
    client = TestClient(create_app(data_root=tmp_path))
    created = upload_video(client, mp4_bytes).json()

    recreated_service = AnalysisService(
        storage=LocalStorage(data_root=tmp_path),
        max_upload_bytes=100 * 1024 * 1024,
    )
    persisted = recreated_service.get_analysis(UUID(created["analysis_id"]))

    assert str(persisted.analysis_id) == created["analysis_id"]
    assert persisted.file_size_bytes == len(mp4_bytes)


def test_recorded_timestamp_is_normalized_and_uploaded_timestamp_is_utc(
    client: TestClient,
    mp4_bytes: bytes,
):
    before = datetime.now(timezone.utc)
    response = upload_video(
        client,
        mp4_bytes,
        recorded_at="2026-11-09T20:15:00+02:30",
    )
    after = datetime.now(timezone.utc)

    assert response.status_code == 201
    assert response.json()["recorded_at"] == "2026-11-09T17:45:00Z"
    uploaded_at = datetime.fromisoformat(response.json()["uploaded_at"].replace("Z", "+00:00"))
    assert before <= uploaded_at <= after


def test_recorded_timestamp_may_be_null(client: TestClient, mp4_bytes: bytes):
    response = upload_video(client, mp4_bytes)
    assert response.status_code == 201
    assert response.json()["recorded_at"] is None


def test_naive_recorded_timestamp_is_rejected(client: TestClient, mp4_bytes: bytes):
    response = upload_video(client, mp4_bytes, recorded_at="2026-11-09T20:15:00")
    assert response.status_code == 422
    assert "timezone" in response.json()["detail"]


@pytest.mark.parametrize(
    ("filename", "content_type", "expected_status"),
    [
        ("notes.txt", "text/plain", 415),
        ("clip.mp4", "video/quicktime", 415),
        ("clip.mov", "video/mp4", 415),
    ],
)
def test_unsupported_extension_or_mime_type_is_rejected(
    client: TestClient,
    mp4_bytes: bytes,
    filename: str,
    content_type: str,
    expected_status: int,
):
    response = upload_video(
        client,
        mp4_bytes,
        filename=filename,
        content_type=content_type,
    )
    assert response.status_code == expected_status


def test_invalid_container_header_is_rejected_and_staging_is_cleaned(
    client: TestClient,
    tmp_path: Path,
):
    response = upload_video(client, b"not an ISO base media file")
    assert response.status_code == 400
    assert "container header" in response.json()["detail"]
    assert list((tmp_path / "uploads").iterdir()) == []
    assert list((tmp_path / "metadata").iterdir()) == []


def test_empty_file_is_rejected(client: TestClient, tmp_path: Path):
    response = upload_video(client, b"")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]
    assert list((tmp_path / "uploads").iterdir()) == []


def test_oversized_upload_stops_and_removes_partial_file(tmp_path: Path, mp4_bytes: bytes):
    client = TestClient(create_app(data_root=tmp_path, max_upload_bytes=16))
    response = upload_video(client, mp4_bytes)

    assert response.status_code == 413
    assert list((tmp_path / "uploads").iterdir()) == []
    assert list((tmp_path / "metadata").iterdir()) == []


def test_list_is_newest_first_and_detail_is_readable(client: TestClient, mp4_bytes: bytes):
    first = upload_video(client, mp4_bytes, filename="first.mp4").json()
    second = upload_video(client, mp4_bytes, filename="second.mp4").json()

    listing = client.get("/api/v1/analyses")
    detail = client.get(f"/api/v1/analyses/{first['analysis_id']}")

    assert listing.status_code == 200
    assert [item["analysis_id"] for item in listing.json()["items"]] == [
        second["analysis_id"],
        first["analysis_id"],
    ]
    assert detail.status_code == 200
    assert detail.json() == first
    assert "stored_filename" not in detail.json()


def test_individual_deletion_removes_video_and_metadata(
    client: TestClient,
    tmp_path: Path,
    mov_bytes: bytes,
):
    created = upload_video(
        client,
        mov_bytes,
        filename="clip.mov",
        content_type="video/quicktime",
    ).json()

    response = client.delete(f"/api/v1/analyses/{created['analysis_id']}")

    assert response.status_code == 204
    assert list((tmp_path / "uploads").iterdir()) == []
    assert list((tmp_path / "metadata").iterdir()) == []
    assert client.get(f"/api/v1/analyses/{created['analysis_id']}").status_code == 404


def test_deletion_cleans_stale_metadata_when_video_is_missing(
    client: TestClient,
    tmp_path: Path,
    mp4_bytes: bytes,
):
    created = upload_video(client, mp4_bytes).json()
    next((tmp_path / "uploads").iterdir()).unlink()

    response = client.delete(f"/api/v1/analyses/{created['analysis_id']}")

    assert response.status_code == 204
    assert list((tmp_path / "metadata").iterdir()) == []


def test_unknown_and_invalid_ids_are_rejected(client: TestClient):
    assert client.get(f"/api/v1/analyses/{uuid4()}").status_code == 404
    assert client.delete(f"/api/v1/analyses/{uuid4()}").status_code == 404
    assert client.get("/api/v1/analyses/not-a-uuid").status_code == 422


def test_submitted_path_is_display_only_and_cannot_escape_storage(
    client: TestClient,
    tmp_path: Path,
    mp4_bytes: bytes,
):
    response = upload_video(client, mp4_bytes, filename="../../outside.mp4")

    assert response.status_code == 201
    assert response.json()["original_filename"] == "outside.mp4"
    assert not (tmp_path.parent / "outside.mp4").exists()
    assert len(list((tmp_path / "uploads").glob("*.mp4"))) == 1


def test_tampered_metadata_cannot_delete_outside_managed_storage(
    client: TestClient,
    tmp_path: Path,
    mp4_bytes: bytes,
):
    created = upload_video(client, mp4_bytes).json()
    outside = tmp_path / "do-not-delete.mp4"
    outside.write_bytes(b"safe")
    metadata_path = tmp_path / "metadata" / f"{created['analysis_id']}.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["stored_filename"] = "../do-not-delete.mp4"
    metadata_path.write_text(json.dumps(metadata))

    response = client.delete(f"/api/v1/analyses/{created['analysis_id']}")

    assert response.status_code == 500
    assert outside.read_bytes() == b"safe"
    assert metadata_path.exists()


def test_mismatched_metadata_id_cannot_delete_another_video(
    client: TestClient,
    tmp_path: Path,
    mp4_bytes: bytes,
):
    first = upload_video(client, mp4_bytes, filename="first.mp4").json()
    second = upload_video(client, mp4_bytes, filename="second.mp4").json()
    first_id = UUID(first["analysis_id"])
    second_id = UUID(second["analysis_id"])
    first_metadata_path = tmp_path / "metadata" / f"{first_id}.json"
    second_metadata_path = tmp_path / "metadata" / f"{second_id}.json"

    second_metadata_path.write_text(first_metadata_path.read_text())

    response = client.delete(f"/api/v1/analyses/{second_id}")

    assert response.status_code == 500
    assert (tmp_path / "uploads" / f"{first_id}.mp4").exists()
    assert (tmp_path / "uploads" / f"{second_id}.mp4").exists()
    assert first_metadata_path.exists()
    assert second_metadata_path.exists()


def test_invalid_source_is_rejected_by_schema(client: TestClient, mp4_bytes: bytes):
    response = upload_video(client, mp4_bytes, source="unknown")
    assert response.status_code == 422
