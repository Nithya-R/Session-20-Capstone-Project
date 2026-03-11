from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional

from agents.admin_agent import AdminAgent
from services.admin_service import dispatch, list_lessons, get_lesson, list_data_files, get_file_content, upload_data_file, get_quiz, generate_lesson

router = APIRouter(prefix="/admin", tags=["admin"])
_agent = AdminAgent()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class NLRequest(BaseModel):
    request: str                    # natural language admin request

class UpdateLessonRequest(BaseModel):
    level: int
    content: str
    regenerate_quiz: Optional[bool] = False

class AddFileRequest(BaseModel):
    filename: str
    content: str

class GenerateEmbeddingsRequest(BaseModel):
    force: Optional[bool] = False

class GenerateLessonRequest(BaseModel):
    prompt: str
    regenerate_quiz: Optional[bool] = False


# ---------------------------------------------------------------------------
# Natural language endpoint (AdminAgent interprets and dispatches)
# ---------------------------------------------------------------------------

@router.post("/ask")
async def admin_ask(req: NLRequest):
    """
    Send a natural language admin request.
    The AdminAgent interprets it and executes the appropriate tool.

    Example: { "request": "show me the lesson for level 5" }
    """
    try:
        tool_call = await _agent.interpret(req.request)
        tool = tool_call.get("tool", "unknown")
        args = tool_call.get("args", {})

        if tool == "unknown":
            return {
                "interpreted_as": tool_call,
                "result": {"message": tool_call.get("message", "Could not understand the request.")},
            }

        result = await dispatch(tool, args)
        return {"interpreted_as": tool_call, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Direct tool endpoints
# ---------------------------------------------------------------------------

@router.get("/lessons")
def admin_list_lessons():
    """List all curriculum levels and their status."""
    try:
        return list_lessons()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/{level}")
def admin_get_lesson(level: int):
    """Get the lesson markdown content for a specific level."""
    try:
        return get_lesson(level)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/{level}/quiz")
def admin_get_quiz(level: int):
    """Get quiz questions for a specific level."""
    try:
        return get_quiz(level)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lessons/{level}/generate")
async def admin_generate_lesson(level: int, req: GenerateLessonRequest):
    """Generate a lesson for a level from an LLM prompt and save it."""
    try:
        return await generate_lesson(level, req.prompt, req.regenerate_quiz)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/lessons/{level}")
async def admin_update_lesson(level: int, req: UpdateLessonRequest):
    """Update the lesson content for a specific level. Optionally regenerate its quiz."""
    try:
        result = await dispatch("update_lesson", {
            "level": level,
            "content": req.content,
            "regenerate_quiz": req.regenerate_quiz,
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/files")
def admin_list_data_files():
    """List all files in the data folder."""
    try:
        return list_data_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/files")
async def admin_add_data_file(req: AddFileRequest):
    """Add a new text/markdown file to the data folder."""
    try:
        return await dispatch("add_data_file", {"filename": req.filename, "content": req.content})
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data/files/{filename}")
async def admin_delete_data_file(filename: str):
    """Delete a file from the data folder and remove it from the index ledger."""
    try:
        return await dispatch("delete_data_file", {"filename": filename})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/generate")
async def admin_generate_embeddings(req: GenerateEmbeddingsRequest):
    """Trigger FAISS embedding generation for all files in the data folder."""
    try:
        return await dispatch("generate_embeddings", {"force": req.force})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/files/{filename}/content")
def admin_get_file_content(filename: str):
    """Serve a file from the data folder for viewing (PDF or text)."""
    try:
        path = get_file_content(filename)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return FileResponse(
                str(path),
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{filename}"'},
            )
        else:
            content = path.read_text(encoding="utf-8", errors="replace")
            return PlainTextResponse(content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/upload")
async def admin_upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a new file (PDF/TXT/MD) to the data folder and trigger reindexing."""
    try:
        result = await upload_data_file(file, background_tasks)
        return result
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
