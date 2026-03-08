import yaml
import json
import os
from pathlib import Path
from core.model_manager import ModelManager
from core.json_parser import parse_llm_json
from core.utils import log_step
from datetime import datetime

class CurriculumAgent:
    """
    Dedicated agent for designing curriculums, modeling the structure
    of the generic AgentRunner but specialized for lesson and quiz generation.
    """
    def __init__(self):
        # Load agent configurations specifically for CurriculumDesignerAgent
        config_path = Path(__file__).parent.parent / "config/agent_config.yaml"
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)["agents"].get("CurriculumDesignerAgent")
            if not self.config:
                raise ValueError("CurriculumDesignerAgent config missing in agent_config.yaml")
                
        # Resolve prompt file
        self.framework_root = Path(__file__).parent.parent
        self.prompt_template = (self.framework_root / self.config["prompt_file"]).read_text(encoding="utf-8")
        
    async def run(self, input_data: dict) -> dict:
        """Run the specialized Curriculum Agent."""
        action = input_data.get("action", "unknown_action")
        
        try:
            # 1. Build Full Prompt
            current_date = datetime.now().strftime("%Y-%m-%d")
            full_prompt = f"CURRENT_DATE: {current_date}\n\n{self.prompt_template.strip()}\n\n```json\n{json.dumps(input_data, indent=2)}\n```"

            # 📝 LOGGING: Save prompt to file for debugging
            debug_log_dir = self.framework_root / "memory" / "debug_logs"
            debug_log_dir.mkdir(parents=True, exist_ok=True)
            log_step(f"🤖 CurriculumAgent invoked for action: {action}", symbol="🎓")

            # 2. Configure ModelManager
            from config.settings_loader import reload_settings
            fresh_settings = reload_settings()
            agent_settings = fresh_settings.get("agent", {})
            
            # Check for overrides
            overrides = agent_settings.get("overrides", {})
            if "CurriculumDesignerAgent" in overrides:
                override = overrides["CurriculumDesignerAgent"]
                model_provider = override.get("model_provider", "gemini")
                model_name = override.get("model", "gemini-2.5-flash")
            else:
                model_provider = agent_settings.get("model_provider", "gemini")
                model_name = agent_settings.get("default_model", "gemini-2.5-flash")
                
            model_manager = ModelManager(model_name, provider=model_provider)
            
            # 3. Generate response
            response = await model_manager.generate_text(full_prompt)
            
            # 📝 LOGGING: Save raw response
            timestamp = datetime.now().strftime("%H%M%S")
            (debug_log_dir / f"{timestamp}_CurriculumAgent_{action}_response.txt").write_text(response, encoding="utf-8")

            # 4. Parse JSON dynamically
            output = parse_llm_json(response)
            
            # Robustness: Some models wrap JSON in a list
            if isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict):
                output = output[0]
                
            log_step(f"🟩 CurriculumAgent finished {action}", symbol="🟩")
            
            return {"output": output}
            
        except Exception as e:
            print(f"❌ CurriculumAgent failed during '{action}': {e}")
            raise e
