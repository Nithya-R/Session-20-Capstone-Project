"""
ConversationSession
-------------------
Manages persistent session state for the conversational training flow.

Adapted from AgentFramework/memory/context.py (ExecutionContextManager pattern).
Each session is stored as a JSON file in backend/memory/sessions/<session_id>.json
so conversations survive app restarts.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
SESSIONS_DIR = ROOT / "memory" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

class State:
    START                    = "start"
    PLACEMENT_QUIZ_INTRO     = "placement_quiz_intro"
    PLACEMENT_QUIZ_QUESTION  = "placement_quiz_question"
    PLACEMENT_QUIZ_RESULT    = "placement_quiz_result"
    PLACEMENT_QUIZ_REVIEW    = "placement_quiz_review"
    LESSON_SNIPPET           = "lesson_snippet"
    LESSON_DELIVERY          = "lesson_delivery"    # kept for back-compat, transitions immediately
    LEVEL_QUIZ_INTRO         = "level_quiz_intro"
    LEVEL_QUIZ_QUESTION      = "level_quiz_question"
    LEVEL_QUIZ_RESULT        = "level_quiz_result"
    COMPLETE                 = "complete"
    ERROR                    = "error"


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def create_session(user_id: str) -> dict:
    """Create a new session and persist it."""
    session_id = str(uuid.uuid4())[:8]
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "state": State.START,
        "sub_state": {},
        "active_questions": None,   # list of questions with correct_index (server-side only)
        "active_answers": {},       # question_id -> chosen_index
        "conversation_history": [],  # [{role, content, timestamp}]
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
    }
    save_session(session)
    return session


def load_session(session_id: str) -> Optional[dict]:
    """Load a session from disk. Returns None if not found."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_session(session: dict):
    """Persist session state to disk."""
    session["last_updated"] = datetime.utcnow().isoformat()
    path = _session_path(session["session_id"])
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")


def delete_session(session_id: str):
    """Remove a session file."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()


def append_message(session: dict, role: str, content: str):
    """Add a message to the conversation history (does NOT auto-save)."""
    session["conversation_history"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    })


def find_session_by_user(user_id: str) -> Optional[dict]:
    """Find the most recent active (non-complete) session for a user."""
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            s = json.loads(path.read_text(encoding="utf-8"))
            if s.get("user_id") == user_id and s.get("state") != State.COMPLETE:
                sessions.append(s)
        except Exception:
            continue
    if not sessions:
        return None
    return max(sessions, key=lambda s: s.get("last_updated", ""))
