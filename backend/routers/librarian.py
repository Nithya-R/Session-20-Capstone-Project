from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from services.librarian_service import librarian_service
from typing import Optional

router = APIRouter(prefix="/librarian", tags=["Librarian"])

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    sub_path: str = Query("", description="Subdirectory within the civic_lens data folder"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload and ingest a document into the Civic Lens knowledge base.
    Supports PDF, Python, and generic text formats.
    """
    try:
        result = await librarian_service.ingest_document(file, sub_path, background_tasks)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_ingestion_status():
    """Check the status of the ingestion pipeline."""
    return {"status": "active", "service": "LibrarianService"}
