from pathlib import Path

from fastapi import FastAPI

from backend.api.analyses import router as analyses_router
from backend.services.analysis_service import AnalysisService
from backend.storage.local_storage import LocalStorage


def create_app(
    *,
    data_root: Path | None = None,
    max_upload_bytes: int = 100 * 1024 * 1024,
) -> FastAPI:
    app = FastAPI(title="AI Lacrosse Coach API")
    storage = LocalStorage(data_root=data_root)
    app.state.analysis_service = AnalysisService(
        storage=storage,
        max_upload_bytes=max_upload_bytes,
    )

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "AI Lacrosse Coach API",
        }

    app.include_router(analyses_router)
    return app


app = create_app()
