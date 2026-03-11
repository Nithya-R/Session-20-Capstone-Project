"""
AdminService
------------
Implements every admin tool directly in Python.
Used by the admin router (direct API calls) and by the AdminAgent (NL dispatch).
"""

import asyncio
import json
import os
from pathlib import Path
from fastapi import UploadFile, BackgroundTasks

ROOT = Path(__file__).parent.parent
CURRICULUM_DIR = ROOT / "curriculum"
DATA_DIR = ROOT / "data"
FAISS_DIR = ROOT / "faiss_index"
LEDGER_PATH = FAISS_DIR / "ledger.json"
MAX_LEVEL = 15


# ---------------------------------------------------------------------------
# Tool: list_lessons
# ---------------------------------------------------------------------------

def list_lessons() -> dict:
    """Return metadata for every curriculum level."""
    levels = []
    for level in range(1, MAX_LEVEL + 1):
        level_dir = CURRICULUM_DIR / f"Level_{level:02d}"
        lesson_path = level_dir / "lesson.md"
        quiz_path = level_dir / "quiz.json"

        lesson_exists = lesson_path.exists()
        quiz_count = 0
        if quiz_path.exists():
            try:
                quiz_count = len(json.loads(quiz_path.read_text(encoding="utf-8")))
            except Exception:
                pass

        levels.append({
            "level": level,
            "lesson_exists": lesson_exists,
            "quiz_question_count": quiz_count,
            "lesson_size_bytes": lesson_path.stat().st_size if lesson_exists else 0,
        })
    return {"levels": levels}


# ---------------------------------------------------------------------------
# Tool: get_lesson
# ---------------------------------------------------------------------------

def get_lesson(level: int) -> dict:
    lesson_path = CURRICULUM_DIR / f"Level_{level:02d}" / "lesson.md"
    if not lesson_path.exists():
        raise FileNotFoundError(f"Lesson for Level {level} not found.")
    return {
        "level": level,
        "content": lesson_path.read_text(encoding="utf-8"),
    }


# ---------------------------------------------------------------------------
# Tool: update_lesson
# ---------------------------------------------------------------------------

async def update_lesson(level: int, content: str, regenerate_quiz: bool = False) -> dict:
    """Overwrite lesson.md and optionally regenerate the quiz via CurriculumAgent."""
    level_dir = CURRICULUM_DIR / f"Level_{level:02d}"
    level_dir.mkdir(parents=True, exist_ok=True)
    lesson_path = level_dir / "lesson.md"
    lesson_path.write_text(content, encoding="utf-8")

    result = {"level": level, "lesson_updated": True, "quiz_regenerated": False}

    if regenerate_quiz:
        from services.curriculum_service import curriculum_service
        # Pass the updated lesson directly to the quiz generator
        from agents.curriculum_agent import CurriculumAgent
        agent = CurriculumAgent()
        quiz_result = await agent.run({
            "action": "create_quiz",
            "level": level,
            "lesson_text": content,
        })
        quiz_data = quiz_result.get("output", {}).get("questions", [])
        if quiz_data:
            quiz_path = level_dir / "quiz.json"
            quiz_path.write_text(json.dumps(quiz_data, indent=2), encoding="utf-8")
            result["quiz_regenerated"] = True
            result["quiz_question_count"] = len(quiz_data)

    return result


# ---------------------------------------------------------------------------
# Tool: list_data_files
# ---------------------------------------------------------------------------

def list_data_files() -> dict:
    """List all files in the data folder with size and ledger metadata."""
    ledger = {}
    if LEDGER_PATH.exists():
        try:
            ledger = json.loads(LEDGER_PATH.read_text()).get("files", {})
        except Exception:
            pass

    files = []
    for f in sorted(DATA_DIR.iterdir()):
        if f.name == ".gitkeep" or f.is_dir():
            continue
        meta = ledger.get(f.name, {})
        files.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "extension": f.suffix,
            "level": meta.get("level"),
            "indexed": f.name in ledger,
        })
    return {"files": files, "total": len(files)}


# ---------------------------------------------------------------------------
# Tool: add_data_file
# ---------------------------------------------------------------------------

def add_data_file(filename: str, content: str) -> dict:
    """Write a new text/markdown file to the data folder."""
    allowed_extensions = {".txt", ".md", ".pdf"}
    path = DATA_DIR / filename

    if Path(filename).suffix.lower() not in allowed_extensions:
        raise ValueError(f"Only {allowed_extensions} files are allowed.")
    if path.exists():
        raise FileExistsError(f"File '{filename}' already exists. Delete it first or use a different name.")

    path.write_text(content, encoding="utf-8")
    return {
        "filename": filename,
        "size_bytes": path.stat().st_size,
        "message": f"File '{filename}' added to data folder. Run generate_embeddings to index it.",
    }


# ---------------------------------------------------------------------------
# Tool: delete_data_file
# ---------------------------------------------------------------------------

def delete_data_file(filename: str) -> dict:
    """Delete a file from the data folder and remove it from the ledger."""
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File '{filename}' not found in data folder.")

    affected_level = None
    if LEDGER_PATH.exists():
        try:
            ledger = json.loads(LEDGER_PATH.read_text())
            if filename in ledger.get("files", {}):
                affected_level = ledger["files"][filename].get("level")
                del ledger["files"][filename]
                LEDGER_PATH.write_text(json.dumps(ledger, indent=2))
        except Exception as e:
            print(f"Warning: could not update ledger: {e}")

    os.remove(file_path)
    return {
        "filename": filename,
        "deleted": True,
        "affected_level": affected_level,
        "message": "File deleted. Run generate_embeddings to update the index.",
    }


# ---------------------------------------------------------------------------
# Tool: generate_embeddings
# ---------------------------------------------------------------------------

async def generate_embeddings(force: bool = False) -> dict:
    """Trigger FAISS embedding generation for all files in the data folder."""
    try:
        from mcp_servers.server_rag_civic import reindex_documents_civic
        await reindex_documents_civic(force=force)
        return {"status": "success", "message": "Embedding generation completed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool: get_quiz
# ---------------------------------------------------------------------------

def get_quiz(level: int) -> dict:
    """Return quiz questions for a curriculum level."""
    quiz_path = CURRICULUM_DIR / f"Level_{level:02d}" / "quiz.json"
    if not quiz_path.exists():
        raise FileNotFoundError(f"Quiz for Level {level} not found.")
    questions = json.loads(quiz_path.read_text(encoding="utf-8"))
    return {"level": level, "questions": questions, "total": len(questions)}


# ---------------------------------------------------------------------------
# Tool: generate_lesson
# ---------------------------------------------------------------------------

async def generate_lesson(level: int, prompt: str, regenerate_quiz: bool = False) -> dict:
    """Use CurriculumAgent to generate a lesson from a prompt, then save it."""
    from agents.curriculum_agent import CurriculumAgent
    agent = CurriculumAgent()

    lesson_result = await agent.run({
        "action": "create_lesson",
        "level": level,
        "raw_text": prompt,
    })
    lesson_markdown = lesson_result.get("output", {}).get("lesson_markdown", "")
    if not lesson_markdown:
        raise ValueError("CurriculumAgent returned empty lesson content.")

    level_dir = CURRICULUM_DIR / f"Level_{level:02d}"
    level_dir.mkdir(parents=True, exist_ok=True)
    (level_dir / "lesson.md").write_text(lesson_markdown, encoding="utf-8")

    result = {
        "level": level,
        "lesson_generated": True,
        "lesson_markdown": lesson_markdown,
        "quiz_regenerated": False,
    }

    if regenerate_quiz:
        quiz_result = await agent.run({
            "action": "create_quiz",
            "level": level,
            "lesson_text": lesson_markdown,
        })
        quiz_data = quiz_result.get("output", {}).get("questions", [])
        if quiz_data:
            (level_dir / "quiz.json").write_text(json.dumps(quiz_data, indent=2), encoding="utf-8")
            result["quiz_regenerated"] = True
            result["quiz_question_count"] = len(quiz_data)

    return result


# ---------------------------------------------------------------------------
# Tool: get_file_content
# ---------------------------------------------------------------------------

def get_file_content(filename: str) -> Path:
    """Return the Path to a file in the data folder, validating it exists."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"File '{filename}' not found in data folder.")
    return path


# ---------------------------------------------------------------------------
# Tool: upload_data_file
# ---------------------------------------------------------------------------

async def upload_data_file(file: UploadFile, background_tasks: BackgroundTasks) -> dict:
    """Save an uploaded file to the data folder and trigger background reindexing."""
    allowed_extensions = {".txt", ".md", ".pdf"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise ValueError(f"Only {allowed_extensions} files are allowed.")

    dest = DATA_DIR / file.filename
    if dest.exists():
        raise FileExistsError(f"File '{file.filename}' already exists. Delete it first or rename.")

    content = await file.read()
    dest.write_bytes(content)

    def _reindex():
        from services.indexer_service import IndexerService
        IndexerService().sync_index()

    background_tasks.add_task(_reindex)

    return {
        "filename": file.filename,
        "size_bytes": dest.stat().st_size,
        "message": f"File '{file.filename}' uploaded. Reindexing started in background.",
    }


# ---------------------------------------------------------------------------
# Dispatcher — used by the admin router NL endpoint
# ---------------------------------------------------------------------------

async def dispatch(tool: str, args: dict) -> dict:
    """Execute a tool by name with the given args."""
    if tool == "list_lessons":
        return list_lessons()
    elif tool == "get_lesson":
        return get_lesson(int(args["level"]))
    elif tool == "update_lesson":
        return await update_lesson(
            int(args["level"]),
            args["content"],
            args.get("regenerate_quiz", False),
        )
    elif tool == "list_data_files":
        return list_data_files()
    elif tool == "add_data_file":
        return add_data_file(args["filename"], args["content"])
    elif tool == "delete_data_file":
        return delete_data_file(args["filename"])
    elif tool == "generate_embeddings":
        return await generate_embeddings(args.get("force", False))
    else:
        return {"error": f"Unknown tool: {tool}"}
