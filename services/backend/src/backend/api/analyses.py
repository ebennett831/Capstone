from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from backend.schemas.analysis import AnalysisListResponse, AnalysisMetadata, AnalysisSource
from backend.services.analysis_service import AnalysisError, AnalysisService

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


ServiceDependency = Annotated[AnalysisService, Depends(get_analysis_service)]


def raise_http_error(error: AnalysisError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@router.post("", response_model=AnalysisMetadata, status_code=201)
async def upload_analysis(
    service: ServiceDependency,
    video: Annotated[UploadFile, File()],
    source: Annotated[AnalysisSource, Form()],
    recorded_at: Annotated[datetime | None, Form()] = None,
    original_filename: Annotated[str | None, Form(max_length=255)] = None,
) -> AnalysisMetadata:
    try:
        return await service.create_analysis(
            video=video,
            source=source,
            recorded_at=recorded_at,
            original_filename=original_filename,
        )
    except AnalysisError as error:
        raise_http_error(error)
    finally:
        await video.close()


@router.get("", response_model=AnalysisListResponse)
def list_analyses(service: ServiceDependency) -> AnalysisListResponse:
    return AnalysisListResponse(items=service.list_analyses())


@router.get("/{analysis_id}", response_model=AnalysisMetadata)
def get_analysis(analysis_id: UUID, service: ServiceDependency) -> AnalysisMetadata:
    try:
        return service.get_analysis(analysis_id)
    except AnalysisError as error:
        raise_http_error(error)


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: UUID, service: ServiceDependency) -> Response:
    try:
        service.delete_analysis(analysis_id)
    except AnalysisError as error:
        raise_http_error(error)
    return Response(status_code=204)
