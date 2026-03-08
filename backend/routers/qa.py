from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.qa_service import qa_service

router = APIRouter(prefix="/qa", tags=["Q&A"])


class AskRequest(BaseModel):
    user_id: str
    question: str


@router.post("/ask")
async def ask_question(req: AskRequest):
    """
    Answer a civic knowledge question using RAG (FAISS) + LLM.
    Saves the question to the user's Q&A history for future suggestions.
    """
    try:
        return await qa_service.ask(req.user_id, req.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_history(user_id: str):
    """Return the user's past Q&A questions for suggestion bubbles."""
    return {"history": qa_service.history(user_id)}
