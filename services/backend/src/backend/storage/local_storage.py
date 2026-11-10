import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from pydantic import ValidationError

from backend.schemas.analysis import AnalysisRecord

CHUNK_SIZE_BYTES = 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov"}
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class EmptyUploadError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


class StorageIntegrityError(Exception):
    pass


@dataclass(frozen=True)
class StagedUpload:
    analysis_id: UUID
    path: Path
    size_bytes: int
    header: bytes


class LocalStorage:
    def __init__(self, data_root: Path | None = None) -> None:
        backend_root = Path(__file__).resolve().parents[3]
        self.data_root = (data_root or backend_root / "data").resolve()
        self.uploads_dir = self.data_root / "uploads"
        self.metadata_dir = self.data_root / "metadata"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    async def stage_upload(
        self,
        *,
        upload: UploadFile,
        analysis_id: UUID,
        max_bytes: int,
    ) -> StagedUpload:
        temp_path = self.uploads_dir / f".{analysis_id}.uploading"
        size_bytes = 0
        header = bytearray()

        try:
            with temp_path.open("xb") as output:
                while chunk := await upload.read(CHUNK_SIZE_BYTES):
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise UploadTooLargeError
                    if len(header) < 32:
                        header.extend(chunk[: 32 - len(header)])
                    output.write(chunk)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

        if size_bytes == 0:
            temp_path.unlink(missing_ok=True)
            raise EmptyUploadError

        return StagedUpload(
            analysis_id=analysis_id,
            path=temp_path,
            size_bytes=size_bytes,
            header=bytes(header),
        )

    def publish_upload(self, staged: StagedUpload, suffix: str) -> str:
        if suffix not in VIDEO_SUFFIXES:
            raise StorageIntegrityError("Unsupported managed video extension")
        stored_filename = f"{staged.analysis_id}{suffix}"
        final_path = self._safe_child(self.uploads_dir, stored_filename)
        os.replace(staged.path, final_path)
        return stored_filename

    @staticmethod
    def discard_staged_upload(staged: StagedUpload) -> None:
        staged.path.unlink(missing_ok=True)

    def save_metadata(self, record: AnalysisRecord) -> None:
        final_path = self._metadata_path(record.analysis_id)
        temp_path = self.metadata_dir / f".{record.analysis_id}.{uuid4()}.tmp"
        try:
            with temp_path.open("x", encoding="utf-8", newline="\n") as metadata_file:
                json.dump(
                    record.model_dump(mode="json"),
                    metadata_file,
                    indent=2,
                    sort_keys=True,
                )
                metadata_file.write("\n")
            os.replace(temp_path, final_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    def load_metadata(self, analysis_id: UUID) -> AnalysisRecord | None:
        path = self._metadata_path(analysis_id)
        if not path.exists():
            return None
        try:
            with path.open(encoding="utf-8") as metadata_file:
                record = AnalysisRecord.model_validate(json.load(metadata_file))
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise StorageIntegrityError(f"Invalid metadata record: {path.name}") from error
        if record.analysis_id != analysis_id:
            raise StorageIntegrityError(
                f"Metadata ID does not match its filename: {path.name}"
            )
        return record

    def list_metadata(self) -> list[AnalysisRecord]:
        records: list[AnalysisRecord] = []
        for path in self.metadata_dir.glob("*.json"):
            try:
                analysis_id = UUID(path.stem)
            except ValueError:
                continue
            record = self.load_metadata(analysis_id)
            if record is not None:
                records.append(record)
        return records

    def delete_analysis(self, analysis_id: UUID) -> bool:
        record = self.load_metadata(analysis_id)
        if record is None:
            return False

        video_path = self._trusted_video_path(record)
        video_path.unlink(missing_ok=True)
        self._metadata_path(analysis_id).unlink(missing_ok=True)
        return True

    def delete_published_video(self, stored_filename: str) -> None:
        path = self._safe_child(self.uploads_dir, stored_filename)
        path.unlink(missing_ok=True)

    def list_managed_files(self) -> list[Path]:
        managed: list[Path] = []
        for path in self.uploads_dir.iterdir():
            if path.is_file() and self._is_managed_upload_name(path.name):
                managed.append(path)
        for path in self.metadata_dir.iterdir():
            if path.is_file() and self._is_managed_metadata_name(path.name):
                managed.append(path)
        return sorted(managed, key=lambda path: str(path))

    def clear_managed_files(self, *, dry_run: bool) -> list[Path]:
        files = self.list_managed_files()
        if not dry_run:
            for path in files:
                self._safe_child(path.parent, path.name).unlink(missing_ok=True)
        return files

    def _trusted_video_path(self, record: AnalysisRecord) -> Path:
        candidate = Path(record.stored_filename)
        if (
            candidate.name != record.stored_filename
            or candidate.suffix.lower() not in VIDEO_SUFFIXES
            or candidate.stem != str(record.analysis_id)
        ):
            raise StorageIntegrityError("Metadata contains an invalid stored filename")
        return self._safe_child(self.uploads_dir, record.stored_filename)

    def _metadata_path(self, analysis_id: UUID) -> Path:
        return self._safe_child(self.metadata_dir, f"{analysis_id}.json")

    @staticmethod
    def _safe_child(parent: Path, name: str) -> Path:
        candidate = (parent / name).resolve()
        if candidate.parent != parent.resolve():
            raise StorageIntegrityError("Refusing to access a path outside managed storage")
        return candidate

    @staticmethod
    def _is_managed_upload_name(name: str) -> bool:
        path = Path(name)
        return (
            path.suffix.lower() in VIDEO_SUFFIXES and bool(UUID_PATTERN.fullmatch(path.stem))
        ) or (
            name.startswith(".")
            and name.endswith(".uploading")
            and bool(UUID_PATTERN.fullmatch(name[1:-10]))
        )

    @staticmethod
    def _is_managed_metadata_name(name: str) -> bool:
        path = Path(name)
        if path.suffix == ".json":
            return bool(UUID_PATTERN.fullmatch(path.stem))
        parts = name.split(".")
        return (
            len(parts) == 4
            and parts[0] == ""
            and bool(UUID_PATTERN.fullmatch(parts[1]))
            and bool(UUID_PATTERN.fullmatch(parts[2]))
            and parts[3] == "tmp"
        )
