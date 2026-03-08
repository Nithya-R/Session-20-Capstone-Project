"""
InitialExaminerAgent
--------------------
Administers a placement quiz (1 question from alternating levels: 1,3,5,7,9,11,13)
to determine where a new user should start training.

Proficiency logic (rounding DOWN):
  - Find the last *consecutive* alternating level (from level 1 upward) the user answered correctly.
  - assessed_level = that level + 1  (they start training from the next level).
  - If user fails level 1 → assessed_level = 1 (start from the beginning).
  - If user passes all tested levels → assessed_level = MAX_LEVEL.
"""

import json
import random
from pathlib import Path
from core.model_manager import ModelManager
from core.json_parser import parse_llm_json
from core.utils import log_step
from datetime import datetime

BACKEND_ROOT = Path(__file__).parent.parent
CURRICULUM_DIR = BACKEND_ROOT / "curriculum"
PROMPT_FILE = BACKEND_ROOT / "prompts" / "initial_examiner.md"

# Alternating levels to sample from (1 question each → 7 questions total)
ALTERNATING_LEVELS = [1, 3, 5, 7, 9, 11, 13]
MAX_LEVEL = 15


class InitialExaminerAgent:

    def __init__(self):
        self.prompt_template = PROMPT_FILE.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Quiz building
    # ------------------------------------------------------------------

    def build_placement_quiz(self) -> list[dict]:
        """Return 1 random question from each alternating level."""
        questions = []
        for level in ALTERNATING_LEVELS:
            quiz_path = CURRICULUM_DIR / f"Level_{level:02d}" / "quiz.json"
            if not quiz_path.exists():
                continue
            pool = json.loads(quiz_path.read_text(encoding="utf-8"))
            q = random.choice(pool).copy()
            q["level"] = level
            questions.append(q)
        return questions

    # ------------------------------------------------------------------
    # Scoring (pure Python — no LLM needed for the logic)
    # ------------------------------------------------------------------

    def _compute_result(self, questions: list[dict], answers: dict) -> dict:
        """
        Score answers and determine assessed_level by rounding down.

        Returns:
            per_level_results  – { level_int: True/False }
            correct_count      – int
            overall_score      – 0-100 int
            assessed_level     – int (where the user should start training)
        """
        per_level: dict[int, bool] = {}
        correct_count = 0

        for q in questions:
            qid = q["id"]
            level = q["level"]
            user_ans = answers.get(qid)
            is_correct = (user_ans == q["correct_index"])
            per_level[level] = is_correct
            if is_correct:
                correct_count += 1

        total = len(questions)
        overall_score = round((correct_count / total) * 100) if total else 0

        # Find last consecutive correct alternating level starting from level 1
        last_correct_level = 0
        for lvl in ALTERNATING_LEVELS:
            if per_level.get(lvl):
                last_correct_level = lvl
            else:
                break  # stop at first failure (consecutive requirement)

        # assessed_level = last correct + 1, clamped to [1, MAX_LEVEL]
        assessed_level = max(1, min(last_correct_level + 1, MAX_LEVEL))

        return {
            "per_level_results": per_level,
            "correct_count": correct_count,
            "overall_score": overall_score,
            "assessed_level": assessed_level,
        }

    # ------------------------------------------------------------------
    # Feedback (LLM-generated, single call)
    # ------------------------------------------------------------------

    async def _generate_feedback(self, overall_score: int, assessed_level: int,
                                  per_level_results: dict) -> str:
        from config.settings_loader import reload_settings
        fresh = reload_settings()
        cfg = fresh.get("agent", {})
        model_manager = ModelManager(
            cfg.get("default_model", "gemini-2.5-flash-lite"),
            provider=cfg.get("model_provider", "gemini")
        )
        payload = {
            "overall_score": overall_score,
            "assessed_level": assessed_level,
            "per_level_results": {str(k): v for k, v in per_level_results.items()},
        }
        prompt = f"{self.prompt_template.strip()}\n\n```json\n{json.dumps(payload, indent=2)}\n```"
        response = await model_manager.generate_text(prompt)
        parsed = parse_llm_json(response)
        if isinstance(parsed, list):
            parsed = parsed[0]
        return parsed.get("feedback", "Good effort! Your placement is complete.")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def evaluate(self, questions: list[dict], answers: dict) -> dict:
        """
        Score the placement quiz and return full result.

        Args:
            questions: list returned by build_placement_quiz()
            answers:   { question_id: chosen_index (int) }

        Returns:
            {
              overall_score, per_level_results, assessed_level, feedback
            }
        """
        log_step("InitialExaminerAgent: scoring placement quiz", symbol="📝")
        result = self._compute_result(questions, answers)

        feedback = await self._generate_feedback(
            result["overall_score"],
            result["assessed_level"],
            result["per_level_results"],
        )

        # Debug log
        debug_dir = BACKEND_ROOT / "memory" / "debug_logs"
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        (debug_dir / f"{ts}_InitialExaminer_result.json").write_text(
            json.dumps({**result, "feedback": feedback}, indent=2), encoding="utf-8"
        )

        return {
            "overall_score": result["overall_score"],
            "per_level_results": {str(k): v for k, v in result["per_level_results"].items()},
            "assessed_level": result["assessed_level"],
            "feedback": feedback,
        }
