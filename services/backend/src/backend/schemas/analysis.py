from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisSource(StrEnum):
    IN_APP_CAMERA = "in_app_camera"
    PHOTO_LIBRARY = "photo_library"


class AnalysisStatus(StrEnum):
    UPLOADED = "uploaded"


class AnalysisMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    original_filename: str
    source: AnalysisSource
    recorded_at: datetime | None
    uploaded_at: datetime
    file_size_bytes: int
    content_type: str
    status: AnalysisStatus


class AnalysisRecord(AnalysisMetadata):
    stored_filename: str

    def to_public_metadata(self) -> AnalysisMetadata:
        return AnalysisMetadata.model_validate(
            self.model_dump(exclude={"stored_filename"})
        )


class AnalysisListResponse(BaseModel):
    items: list[AnalysisMetadata]
