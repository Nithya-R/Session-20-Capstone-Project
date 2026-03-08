"""
TrainingService
---------------
Orchestrates the full training flow. All active quiz state is persisted
in the user's JSON profile so training survives app restarts seamlessly.

Flow:
  1. GET /placement/quiz     → returns or resumes persisted placement questions
  2. POST /placement/submit  → scores, stores result, clears session
  3. GET /lesson             → returns lesson for current level
  4. GET /quiz               → returns or resumes persisted level quiz
  5. POST /quiz/submit       → scores, updates progress, clears session
"""

from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agents.initial_examiner_agent import InitialExaminerAgent
from agents.guide_agent import GuideAgent
from agents.examiner_agent import ExaminerAgent
from user_store.user_hub import (
    load_profile,
    save_active_placement_quiz,
    load_active_placement_quiz,
    set_initial_exam_result,
    save_active_level_quiz,
    load_active_level_quiz,
    record_level_quiz,
    get_current_level,
)


class TrainingService:

    def __init__(self):
        self.initial_examiner = InitialExaminerAgent()
        self.guide = GuideAgent()
        self.examiner = ExaminerAgent()

    # ------------------------------------------------------------------
    # Placement exam
    # ------------------------------------------------------------------

    def get_placement_quiz(self, user_id: str) -> dict:
        """
        Return placement quiz for the user.
        If a session already exists (from a previous visit), resume it.
        Otherwise generate fresh questions and persist them.

        Returns:
            {
              "questions": [...],  # without correct_index
              "resumed": bool      # True if continuing a previous session
            }
        """
        existing = load_active_placement_quiz(user_id)
        if existing:
            client_qs = [{k: v for k, v in q.items() if k != "correct_index"} for q in existing]
            return {"questions": client_qs, "resumed": True}

        questions = self.initial_examiner.build_placement_quiz()
        save_active_placement_quiz(user_id, questions)
        client_qs = [{k: v for k, v in q.items() if k != "correct_index"} for q in questions]
        return {"questions": client_qs, "resumed": False}

    async def submit_placement_quiz(self, user_id: str, user_answers: dict) -> dict:
        """
        Score placement quiz using the persisted questions (not re-sent by client).
        user_answers: { question_id: chosen_index }
        """
        questions = load_active_placement_quiz(user_id)
        if not questions:
            raise ValueError("No active placement quiz found. Call GET /placement/quiz first.")

        result = await self.initial_examiner.evaluate(questions, user_answers)
        # Persist result and clear session
        set_initial_exam_result(user_id, result["overall_score"], result["assessed_level"])
        return result

    # ------------------------------------------------------------------
    # Lesson delivery
    # ------------------------------------------------------------------

    async def get_lesson(self, user_id: str, user_name: str = "there") -> dict:
        """Deliver the lesson for the user's current level."""
        level = get_current_level(user_id)
        teaching = await self.guide.teach(level, user_name)
        return {"level": level, **teaching}

    # ------------------------------------------------------------------
    # Level quiz
    # ------------------------------------------------------------------

    def get_level_quiz(self, user_id: str) -> dict:
        """
        Return level quiz for the user's current level.
        Resumes existing session if available (same questions after restart).

        Returns:
            {
              "level": int,
              "questions": [...],  # without correct_index
              "attempt_number": int,
              "resumed": bool
            }
        """
        profile = load_profile(user_id)
        current_level = profile["current_level"]
        attempt_number = len(
            profile.get("level_quiz_history", {}).get(str(current_level), [])
        ) + 1

        existing = load_active_level_quiz(user_id)
        # Resume only if the session is for the same level
        if existing and existing["level"] == current_level:
            client_qs = [
                {k: v for k, v in q.items() if k != "correct_index"}
                for q in existing["questions"]
            ]
            return {
                "level": current_level,
                "questions": client_qs,
                "attempt_number": attempt_number,
                "resumed": True,
            }

        questions = self.examiner.build_level_quiz(current_level)
        save_active_level_quiz(user_id, current_level, questions)
        client_qs = [{k: v for k, v in q.items() if k != "correct_index"} for q in questions]
        return {
            "level": current_level,
            "questions": client_qs,
            "attempt_number": attempt_number,
            "resumed": False,
        }

    async def submit_level_quiz(self, user_id: str, user_answers: dict) -> dict:
        """
        Score the level quiz using persisted questions.
        user_answers: { question_id: chosen_index }
        """
        session = load_active_level_quiz(user_id)
        if not session:
            raise ValueError("No active level quiz found. Call GET /quiz first.")

        level = session["level"]
        questions = session["questions"]

        profile = load_profile(user_id)
        attempt_number = len(
            profile.get("level_quiz_history", {}).get(str(level), [])
        ) + 1

        result = await self.examiner.evaluate(level, questions, user_answers, attempt_number)
        # Persist result, clear session, advance level if passed
        record_level_quiz(user_id, level, result["score"], result["total"], result["passed"])

        updated = load_profile(user_id)
        result["current_level"] = updated["current_level"]
        result["needs_revision"] = updated.get("needs_revision", [])
        result["level_tested"] = level
        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_user_status(self, user_id: str) -> dict:
        profile = load_profile(user_id)
        return {
            "user_id": user_id,
            "initial_exam_completed": profile["initial_exam_completed"],
            "assessed_level": profile["assessed_level"],
            "current_level": profile["current_level"],
            "levels_completed": profile["levels_completed"],
            "needs_revision": profile.get("needs_revision", []),
            "has_active_placement_quiz": profile.get("active_placement_quiz") is not None,
            "has_active_level_quiz": profile.get("active_level_quiz") is not None,
        }

    def get_roadmap(self, user_id: str) -> dict:
        """Return all 15 levels with title, completion status, and snippet for hover."""
        from pathlib import Path as _Path
        import re as _re
        CURRICULUM_DIR = ROOT / "curriculum"
        profile = load_profile(user_id)
        current_level = profile["current_level"]
        levels_completed = set(profile["levels_completed"])
        needs_revision = set(profile.get("needs_revision", []))

        levels = []
        for i in range(1, 16):
            lesson_path = CURRICULUM_DIR / f"Level_{i:02d}" / "lesson.md"
            title = f"Level {i}"
            description = ""
            if lesson_path.exists():
                text = lesson_path.read_text(encoding="utf-8")
                # First non-empty line as title (strip markdown #)
                for line in text.split('\n'):
                    stripped = line.strip().lstrip('#').strip()
                    if stripped:
                        title = stripped
                        break
                # First paragraph as description
                paras = [p.strip() for p in text.split('\n\n') if p.strip()]
                if len(paras) > 1:
                    description = _re.sub(r'[#*`]', '', paras[1])[:180].strip()

            # Levels at or below current_level are unlocked (assessed placement opens them all)
            levels.append({
                "level": i,
                "title": title,
                "description": description,
                "completed": i in levels_completed,
                "current": i == current_level,
                "needs_revision": i in needs_revision,
                "locked": i > current_level,
                "available": i < current_level and i not in levels_completed,
            })

        return {
            "user_id": user_id,
            "current_level": current_level,
            "levels_completed": list(levels_completed),
            "initial_exam_completed": profile["initial_exam_completed"],
            "levels": levels,
        }


training_service = TrainingService()
