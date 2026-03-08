"""
AdminAgent
----------
An LLM-powered admin assistant that understands natural language requests
and dispatches them to the correct admin tool.

Available tools (all implemented in AdminService):
  - list_lessons
  - get_lesson
  - update_lesson
  - list_data_files
  - add_data_file
  - delete_data_file
  - generate_embeddings
"""

import json
from pathlib import Path
from core.model_manager import ModelManager
from core.json_parser import parse_llm_json
from core.utils import log_step
from datetime import datetime

BACKEND_ROOT = Path(__file__).parent.parent
PROMPT_FILE = BACKEND_ROOT / "prompts" / "admin_agent.md"

KNOWN_TOOLS = {
    "list_lessons", "get_lesson", "update_lesson",
    "list_data_files", "add_data_file", "delete_data_file",
    "generate_embeddings",
}


class AdminAgent:
    """Interprets a natural language admin request and returns a tool call."""

    def __init__(self):
        self.prompt_template = PROMPT_FILE.read_text(encoding="utf-8")

    async def interpret(self, user_request: str) -> dict:
        """
        Parse a natural language admin request into a tool call.

        Returns:
            { "tool": str, "args": dict, "message": str (optional) }
        """
        from config.settings_loader import reload_settings
        fresh = reload_settings()
        cfg = fresh.get("agent", {})
        model_manager = ModelManager(
            cfg.get("default_model", "gemini-2.5-flash-lite"),
            provider=cfg.get("model_provider", "gemini")
        )

        prompt = (
            f"{self.prompt_template.strip()}\n\n"
            f"User request: {user_request}"
        )

        log_step(f"AdminAgent interpreting: {user_request[:60]}", symbol="🛠️")
        response = await model_manager.generate_text(prompt)

        debug_dir = BACKEND_ROOT / "memory" / "debug_logs"
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        (debug_dir / f"{ts}_AdminAgent_response.txt").write_text(response, encoding="utf-8")

        parsed = parse_llm_json(response)
        if isinstance(parsed, list):
            parsed = parsed[0]

        # Validate tool name
        tool = parsed.get("tool", "unknown")
        if tool not in KNOWN_TOOLS:
            parsed["tool"] = "unknown"
            parsed.setdefault("message", f"Tool '{tool}' is not recognised.")

        return parsed
