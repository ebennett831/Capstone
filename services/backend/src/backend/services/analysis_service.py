from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from backend.schemas.analysis import (
    AnalysisMetadata,
    AnalysisRecord,
    AnalysisSource,
    AnalysisStatus,
)
from backend.storage.local_storage import (
    EmptyUploadError,
    LocalStorage,
    StorageIntegrityError,
    UploadTooLargeError,
)

ALLOWED_CONTENT_TYPES = {
    ".mp4": {"video/mp4", "application/mp4"},
    ".mov": {"video/quicktime"},
}
MAX_ORIGINAL_FILENAME_LENGTH = 255


class AnalysisError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AnalysisService:
    def __init__(self, storage: LocalStorage, max_upload_bytes: int) -> None:
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be positive")
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes

    async def create_analysis(
        self,
        *,
        video: UploadFile,
        source: AnalysisSource,
        recorded_at: datetime | None,
        original_filename: str | None = None,
    ) -> AnalysisMetadata:
        upload_filename, suffix = self._validate_filename(video.filename)
        display_filename = upload_filename
        if original_filename is not None:
            display_filename, _ = self._validate_filename(original_filename)
        content_type = self._validate_content_type(video.content_type, suffix)
        normalized_recorded_at = self._normalize_recorded_at(recorded_at)
        analysis_id = uuid4()

        try:
            staged = await self.storage.stage_upload(
                upload=video,
                analysis_id=analysis_id,
                max_bytes=self.max_upload_bytes,
            )
        except EmptyUploadError as error:
            raise AnalysisError("The uploaded video is empty.", 400) from error
        except UploadTooLargeError as error:
            limit_mb = self.max_upload_bytes // (1024 * 1024)
            raise AnalysisError(
                f"The uploaded video exceeds the {limit_mb} MB limit.",
                413,
            ) from error

        try:
            self._validate_container_header(staged.header)
            stored_filename = self.storage.publish_upload(staged, suffix)
        except AnalysisError:
            self.storage.discard_staged_upload(staged)
            raise
        except OSError as error:
            self.storage.discard_staged_upload(staged)
            raise AnalysisError("The video could not be stored.", 500) from error

        record = AnalysisRecord(
            analysis_id=analysis_id,
            original_filename=display_filename,
            source=source,
            recorded_at=normalized_recorded_at,
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=staged.size_bytes,
            content_type=content_type,
            status=AnalysisStatus.UPLOADED,
            stored_filename=stored_filename,
        )

        try:
            self.storage.save_metadata(record)
        except (OSError, StorageIntegrityError) as error:
            self.storage.delete_published_video(stored_filename)
            raise AnalysisError("The video metadata could not be stored.", 500) from error

        return record.to_public_metadata()

    def list_analyses(self) -> list[AnalysisMetadata]:
        records = self.storage.list_metadata()
        records.sort(key=lambda record: record.uploaded_at, reverse=True)
        return [record.to_public_metadata() for record in records]

    def get_analysis(self, analysis_id: UUID) -> AnalysisMetadata:
        record = self.storage.load_metadata(analysis_id)
        if record is None:
            raise AnalysisError("Analysis not found.", 404)
        return record.to_public_metadata()

    def delete_analysis(self, analysis_id: UUID) -> None:
        try:
            deleted = self.storage.delete_analysis(analysis_id)
        except StorageIntegrityError as error:
            raise AnalysisError("Stored analysis metadata is invalid.", 500) from error
        if not deleted:
            raise AnalysisError("Analysis not found.", 404)

    @staticmethod
    def _validate_filename(filename: str | None) -> tuple[str, str]:
        if not filename:
            raise AnalysisError("A video filename is required.", 400)

        display_name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not display_name or len(display_name) > MAX_ORIGINAL_FILENAME_LENGTH:
            raise AnalysisError("The video filename is invalid or too long.", 400)

        suffix = Path(display_name).suffix.lower()
        if suffix not in ALLOWED_CONTENT_TYPES:
            raise AnalysisError("Only MP4 and MOV video files are supported.", 415)
        return display_name, suffix

    @staticmethod
    def _validate_content_type(content_type: str | None, suffix: str) -> str:
        normalized = (content_type or "").split(";", 1)[0].strip().lower()
        if normalized not in ALLOWED_CONTENT_TYPES[suffix]:
            raise AnalysisError(
                "The declared media type does not match a supported MP4 or MOV upload.",
                415,
            )
        return normalized

    @staticmethod
    def _normalize_recorded_at(recorded_at: datetime | None) -> datetime | None:
        if recorded_at is None:
            return None
        if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
            raise AnalysisError("recorded_at must include a timezone offset.", 422)
        return recorded_at.astimezone(timezone.utc)

    @staticmethod
    def _validate_container_header(header: bytes) -> None:
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise AnalysisError(
                "The file does not contain a recognized MP4/MOV container header.",
                400,
            )

        box_size = int.from_bytes(header[:4], byteorder="big")
        if box_size == 1:
            if len(header) < 16 or int.from_bytes(header[8:16], "big") < 16:
                raise AnalysisError("The MP4/MOV ftyp box is malformed.", 400)
        elif box_size < 12:
            raise AnalysisError("The MP4/MOV ftyp box is malformed.", 400)
