"""
UserHub — Inspired by REMME's hub pattern.
All user state is persisted to backend/user_store/profiles/<user_id>.json.
This includes active quiz sessions so training survives app restarts.

Key fields:
  - initial_exam_completed / assessed_level / current_level
  - levels_completed / needs_revision / level_quiz_history
  - active_placement_quiz   — persisted quiz questions for placement exam
  - active_level_quiz       — persisted quiz questions for current level
"""

import json
from datetime import datetime
from pathlib import Path

PROFILES_DIR = Path(__file__).parent / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

MAX_LEVEL = 15


def _profile_path(user_id: str) -> Path:
    return PROFILES_DIR / f"{user_id}.json"


def _default_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        # Placement exam
        "initial_exam_completed": False,
        "initial_exam_score": None,
        "assessed_level": None,
        # Training state
        "current_level": 1,
        "levels_completed": [],
        "needs_revision": [],        # levels that took >1 attempt
        "level_quiz_history": {},    # { "3": [{"score":6,"total":7,"passed":True,"date":"..."}] }
        # Active session persistence (survive restarts)
        "active_placement_quiz": None,   # { "questions": [...] }
        "active_level_quiz": None,       # { "level": int, "questions": [...] }
        # Metadata
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Core load / save
# ---------------------------------------------------------------------------

def load_profile(user_id: str) -> dict:
    path = _profile_path(user_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return _default_profile(user_id)


def save_profile(profile: dict):
    profile["last_updated"] = datetime.now().isoformat()
    _profile_path(profile["user_id"]).write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Placement exam helpers
# ---------------------------------------------------------------------------

def save_active_placement_quiz(user_id: str, questions: list):
    """Persist placement quiz questions so the session survives restarts."""
    profile = load_profile(user_id)
    profile["active_placement_quiz"] = {"questions": questions}
    save_profile(profile)


def load_active_placement_quiz(user_id: str) -> list | None:
    profile = load_profile(user_id)
    session = profile.get("active_placement_quiz")
    return session["questions"] if session else None


def clear_active_placement_quiz(user_id: str):
    profile = load_profile(user_id)
    profile["active_placement_quiz"] = None
    save_profile(profile)


def set_initial_exam_result(user_id: str, overall_score: int, assessed_level: int):
    profile = load_profile(user_id)
    profile["initial_exam_completed"] = True
    profile["initial_exam_score"] = overall_score
    profile["assessed_level"] = assessed_level
    profile["current_level"] = assessed_level
    profile["active_placement_quiz"] = None  # clear session
    save_profile(profile)


# ---------------------------------------------------------------------------
# Level quiz helpers
# ---------------------------------------------------------------------------

def save_active_level_quiz(user_id: str, level: int, questions: list):
    """Persist level quiz questions so the session survives restarts."""
    profile = load_profile(user_id)
    profile["active_level_quiz"] = {"level": level, "questions": questions}
    save_profile(profile)


def load_active_level_quiz(user_id: str) -> dict | None:
    """Returns { level, questions } or None."""
    profile = load_profile(user_id)
    return profile.get("active_level_quiz")


def clear_active_level_quiz(user_id: str):
    profile = load_profile(user_id)
    profile["active_level_quiz"] = None
    save_profile(profile)


def record_level_quiz(user_id: str, level: int, score: int, total: int, passed: bool):
    """
    Record a quiz attempt.
    - Flag level for revision if this is not the first attempt.
    - Advance current_level on pass.
    - Clear the active level quiz session.
    """
    profile = load_profile(user_id)
    key = str(level)
    history = profile.setdefault("level_quiz_history", {}).setdefault(key, [])

    # Flag for revision if retrying
    if len(history) >= 1 and level not in profile.get("needs_revision", []):
        profile.setdefault("needs_revision", []).append(level)

    history.append({
        "score": score,
        "total": total,
        "passed": passed,
        "date": datetime.now().isoformat(),
    })

    if passed and level not in profile.get("levels_completed", []):
        profile.setdefault("levels_completed", []).append(level)
        next_level = level + 1
        if next_level <= MAX_LEVEL:
            profile["current_level"] = next_level

    profile["active_level_quiz"] = None  # clear session
    save_profile(profile)


# ---------------------------------------------------------------------------
# Convenience getters
# ---------------------------------------------------------------------------

def get_current_level(user_id: str) -> int:
    return load_profile(user_id)["current_level"]


def get_needs_revision(user_id: str) -> list:
    return load_profile(user_id).get("needs_revision", [])


def list_users() -> list:
    return [p.stem for p in PROFILES_DIR.glob("*.json")]


# ---------------------------------------------------------------------------
# Q&A history
# ---------------------------------------------------------------------------

def save_qa_question(user_id: str, question: str):
    """Persist a question the user asked in the roadmap Q&A panel (max 30, unique, newest first)."""
    profile = load_profile(user_id)
    history: list = profile.get("qa_history", [])
    if question in history:
        history.remove(question)
    history.insert(0, question)
    profile["qa_history"] = history[:30]
    save_profile(profile)


def get_qa_history(user_id: str) -> list[str]:
    return load_profile(user_id).get("qa_history", [])
