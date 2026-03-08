from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.curriculum_service import curriculum_service

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

class GenerateLevelRequest(BaseModel):
    level: int

@router.post("/generate")
async def generate_curriculum(request: GenerateLevelRequest):
    """
    Triggers the CurriculumAgent to generate a lesson and quiz for the specified level.
    """
    try:
        success = await curriculum_service.generate_level(request.level)
        if success:
            return {"status": "success", "message": f"Successfully generated curriculum for Level {request.level}"}
        else:
            raise HTTPException(status_code=404, detail=f"Raw text data for Level {request.level} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
