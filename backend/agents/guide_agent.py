"""
GuideAgent
----------
Delivers the lesson for a given level in an engaging, conversational style.
"""

import json
from pathlib import Path
from core.model_manager import ModelManager
from core.json_parser import parse_llm_json
from core.utils import log_step
from datetime import datetime

BACKEND_ROOT = Path(__file__).parent.parent
CURRICULUM_DIR = BACKEND_ROOT / "curriculum"
DATA_DIR      = BACKEND_ROOT / "data"
PROMPT_FILE = BACKEND_ROOT / "prompts" / "guide_agent.md"


class GuideAgent:

    def __init__(self):
        self.prompt_template = PROMPT_FILE.read_text(encoding="utf-8")

    def get_lesson(self, level: int) -> str:
        # Prefer the raw source file — it is the authoritative content
        # that the quiz was built from, ensuring full alignment.
        raw_path = DATA_DIR / f"level{level}.txt"
        if raw_path.exists():
            return raw_path.read_text(encoding="utf-8")

        # Fall back to generated lesson.md
        lesson_path = CURRICULUM_DIR / f"Level_{level:02d}" / "lesson.md"
        if lesson_path.exists():
            return lesson_path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Lesson not found for Level {level}")

    async def teach(self, level: int, user_name: str = "there") -> dict:
        """
        Generate a teaching message for the given level.

        Returns:
            { teaching_content: str }
        """
        lesson_md = self.get_lesson(level)

        from config.settings_loader import reload_settings
        fresh = reload_settings()
        cfg = fresh.get("agent", {})
        model_manager = ModelManager(
            cfg.get("default_model", "gemini-2.5-flash-lite"),
            provider=cfg.get("model_provider", "gemini")
        )

        payload = {
            "level": level,
            "lesson_markdown": lesson_md,
            "user_name": user_name,
        }
        prompt = (
            f"{self.prompt_template.strip()}\n\n"
            f"```json\n{json.dumps(payload, indent=2)}\n```"
        )

        log_step(f"GuideAgent teaching Level {level}", symbol="📖")
        response = await model_manager.generate_text(prompt)

        debug_dir = BACKEND_ROOT / "memory" / "debug_logs"
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        (debug_dir / f"{ts}_GuideAgent_L{level}_response.txt").write_text(
            response, encoding="utf-8"
        )

        result = parse_llm_json(response)
        if isinstance(result, list):
            result = result[0]
        return result
