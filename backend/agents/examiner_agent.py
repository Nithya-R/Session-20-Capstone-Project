"""
ExaminerAgent
-------------
Administers a 7-question quiz sampled randomly from a level's 25-question pool.
Pass threshold: 6 correct out of 7.
Scoring is done in Python; LLM generates personalised feedback.
If user takes >1 attempt, the level is flagged for revision in user_hub.
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
PROMPT_FILE = BACKEND_ROOT / "prompts" / "examiner_agent.md"

QUIZ_QUESTIONS = 7
PASS_THRESHOLD = 6   # must score 6/7 to pass


class ExaminerAgent:

    def __init__(self):
        self.prompt_template = PROMPT_FILE.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Quiz building
    # ------------------------------------------------------------------

    def build_level_quiz(self, level: int) -> list[dict]:
        """Randomly sample QUIZ_QUESTIONS questions from the level's pool."""
        quiz_path = CURRICULUM_DIR / f"Level_{level:02d}" / "quiz.json"
        if not quiz_path.exists():
            raise FileNotFoundError(f"Quiz not found for Level {level}")
        pool = json.loads(quiz_path.read_text(encoding="utf-8"))
        return random.sample(pool, min(QUIZ_QUESTIONS, len(pool)))

    # ------------------------------------------------------------------
    # Scoring (pure Python)
    # ------------------------------------------------------------------

    def _score(self, questions: list[dict], answers: dict) -> dict:
        correct = 0
        wrong = []
        for q in questions:
            qid = q["id"]
            user_ans = answers.get(qid)
            if user_ans == q["correct_index"]:
                correct += 1
            else:
                wrong.append({
                    "question_id": qid,
                    "question": q["question"],
                    "correct_answer": q["options"][q["correct_index"]],
                    "your_answer": q["options"][user_ans] if user_ans is not None else "No answer",
                    "explanation": q.get("explanation", ""),
                })
        return {
            "score": correct,
            "total": QUIZ_QUESTIONS,
            "passed": correct >= PASS_THRESHOLD,
            "wrong_questions": wrong,
        }

    # ------------------------------------------------------------------
    # Feedback (LLM)
    # ------------------------------------------------------------------

    async def _generate_feedback(self, level: int, scored: dict, attempt_number: int) -> str:
        from config.settings_loader import reload_settings
        fresh = reload_settings()
        cfg = fresh.get("agent", {})
        model_manager = ModelManager(
            cfg.get("default_model", "gemini-2.5-flash-lite"),
            provider=cfg.get("model_provider", "gemini")
        )
        payload = {
            "level": level,
            "score": scored["score"],
            "total": scored["total"],
            "passed": scored["passed"],
            "wrong_questions": scored["wrong_questions"],
            "attempt_number": attempt_number,
        }
        prompt = (
            f"{self.prompt_template.strip()}\n\n"
            f"```json\n{json.dumps(payload, indent=2)}\n```"
        )
        response = await model_manager.generate_text(prompt)
        parsed = parse_llm_json(response)
        if isinstance(parsed, list):
            parsed = parsed[0]
        return parsed.get("feedback", "Quiz complete. Keep going!")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def evaluate(self, level: int, questions: list[dict],
                       answers: dict, attempt_number: int = 1) -> dict:
        """
        Score a level quiz and return full result with feedback.

        Args:
            level:          level number being tested
            questions:      list returned by build_level_quiz()
            answers:        { question_id: chosen_index (int) }
            attempt_number: 1 for first try, 2+ for retries

        Returns:
            { score, total, passed, wrong_questions, feedback }
        """
        log_step(f"ExaminerAgent: scoring Level {level} quiz (attempt {attempt_number})", symbol="📋")
        scored = self._score(questions, answers)

        feedback = await self._generate_feedback(level, scored, attempt_number)

        debug_dir = BACKEND_ROOT / "memory" / "debug_logs"
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        (debug_dir / f"{ts}_ExaminerAgent_L{level}_a{attempt_number}.json").write_text(
            json.dumps({**scored, "feedback": feedback}, indent=2), encoding="utf-8"
        )

        return {
            "score": scored["score"],
            "total": scored["total"],
            "passed": scored["passed"],
            "wrong_questions": scored["wrong_questions"],
            "feedback": feedback,
        }
