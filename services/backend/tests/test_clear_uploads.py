import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.storage.local_storage import LocalStorage
from conftest import upload_video

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "clear_uploads.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("clear_uploads_script", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
SCRIPT_MODULE = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(SCRIPT_MODULE)
clear_uploads = SCRIPT_MODULE.clear_uploads


def test_clear_uploads_dry_run_does_not_delete(
    tmp_path: Path,
    mp4_bytes: bytes,
):
    client = TestClient(create_app(data_root=tmp_path))
    upload_video(client, mp4_bytes)
    storage = LocalStorage(data_root=tmp_path)
    output: list[str] = []

    result = clear_uploads(storage, dry_run=True, output_fn=output.append)

    assert result == 0
    assert "Would delete 2 managed file(s)" in output[0]
    assert len(storage.list_managed_files()) == 2


def test_confirmed_clear_only_deletes_managed_test_files(
    tmp_path: Path,
    mov_bytes: bytes,
):
    client = TestClient(create_app(data_root=tmp_path))
    upload_video(
        client,
        mov_bytes,
        filename="clip.mov",
        content_type="video/quicktime",
    )
    storage = LocalStorage(data_root=tmp_path)
    unmanaged = storage.uploads_dir / "keep-me.txt"
    unmanaged.write_text("not managed")
    output: list[str] = []

    result = clear_uploads(
        storage,
        dry_run=False,
        input_fn=lambda _: "DELETE",
        output_fn=output.append,
    )

    assert result == 0
    assert storage.list_managed_files() == []
    assert unmanaged.read_text() == "not managed"
    assert output[-1] == "Deleted 2 managed file(s)."


def test_cancelled_clear_deletes_nothing(tmp_path: Path, mp4_bytes: bytes):
    client = TestClient(create_app(data_root=tmp_path))
    upload_video(client, mp4_bytes)
    storage = LocalStorage(data_root=tmp_path)

    result = clear_uploads(
        storage,
        dry_run=False,
        input_fn=lambda _: "no",
        output_fn=lambda _: None,
    )

    assert result == 1
    assert len(storage.list_managed_files()) == 2
