from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.training_service import training_service

router = APIRouter(prefix="/training", tags=["training"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PlacementSubmitRequest(BaseModel):
    user_id: str
    answers: dict   # { "q1": 2, "q3": 0, ... }

class LessonRequest(BaseModel):
    user_id: str
    user_name: Optional[str] = "there"

class QuizSubmitRequest(BaseModel):
    user_id: str
    answers: dict   # { "q1": 2, "q3": 0, ... }


# ---------------------------------------------------------------------------
# Placement exam
# ---------------------------------------------------------------------------

@router.get("/placement/quiz")
def get_placement_quiz(user_id: str):
    """
    Get the placement quiz for a user.
    Returns the same questions if a session already exists (session-persistent).
    """
    try:
        return training_service.get_placement_quiz(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/placement/submit")
async def submit_placement_quiz(request: PlacementSubmitRequest):
    """Score the placement quiz and determine the user's starting level."""
    try:
        result = await training_service.submit_placement_quiz(request.user_id, request.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------

@router.post("/lesson")
async def get_lesson(request: LessonRequest):
    """Deliver the lesson for the user's current level via the GuideAgent."""
    try:
        return await training_service.get_lesson(request.user_id, request.user_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Level quiz
# ---------------------------------------------------------------------------

@router.get("/quiz")
def get_level_quiz(user_id: str):
    """
    Get the level quiz for the user's current level.
    Returns the same questions if a session already exists (session-persistent).
    """
    try:
        return training_service.get_level_quiz(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quiz/submit")
async def submit_level_quiz(request: QuizSubmitRequest):
    """Score the level quiz and update the user's progress."""
    try:
        result = await training_service.submit_level_quiz(request.user_id, request.answers)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status")
def get_user_status(user_id: str):
    """Get a user's full training status and progress."""
    return training_service.get_user_status(user_id)


@router.get("/roadmap")
def get_roadmap(user_id: str):
    """Get the full level roadmap with completion status and lesson titles."""
    return training_service.get_roadmap(user_id)
