import json
from pathlib import Path

# Setup Project Paths
ROOT = Path(__file__).parent.resolve() # backend/services
PROJECT_ROOT = ROOT.parent.resolve() # backend

from agents.curriculum_agent import CurriculumAgent

class CurriculumService:
    def __init__(self):
        self.agent = CurriculumAgent()
        self.data_dir = PROJECT_ROOT / "data"
        self.curriculum_dir = PROJECT_ROOT / "curriculum"
        self.curriculum_dir.mkdir(parents=True, exist_ok=True)

    async def generate_level(self, level_num: int):
        """Generates a lesson and a 25-question quiz for a specific level using the CurriculumDesignerAgent."""
        print(f"\n[CurriculumService] Generating Curriculum for Level {level_num}...")
        
        # Aggregate text from all files in the ledger that match this level
        raw_text = ""
        ledger_path = PROJECT_ROOT / "faiss_index" / "ledger.json"
        
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text())
                if "files" in ledger:
                    for rel_path, data in ledger["files"].items():
                        if data.get("level") == level_num:
                            file_path = self.data_dir / rel_path
                            if file_path.exists():
                                # Very basic text extraction for aggregation
                                if file_path.suffix == '.txt' or file_path.suffix == '.md':
                                    raw_text += f"\n\n--- Source: {rel_path} ---\n\n"
                                    raw_text += file_path.read_text(encoding="utf-8", errors="ignore")
                                # For PDFs, we'll try to get it from the fastmcp tool if available, otherwise just warn
                                elif file_path.suffix == '.pdf':
                                     raw_text += f"\n\n--- Source: {rel_path} (PDF parsed by system) ---\n\n"
                                     from mcp_servers.server_rag_civic import convert_pdf_to_markdown
                                     res = convert_pdf_to_markdown(str(file_path))
                                     raw_text += res.markdown
            except Exception as e:
                print(f"Error reading ledger for curriculum generation: {e}")
                
        # Fallback to static levelX.txt if nothing found in ledger (backward compatibility for testing)
        if not raw_text.strip():
             level_txt_file = self.data_dir / f"level{level_num}.txt"
             if level_txt_file.exists():
                 raw_text = level_txt_file.read_text(encoding="utf-8", errors="ignore")
                 
        if not raw_text.strip():
             print(f"Skipping: No raw text found for Level {level_num} in ledger or static files.")
             return False
        
        target_dir = self.curriculum_dir / f"Level_{level_num:02d}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Action: create_lesson
        print("  Calling CurriculumAgent -> create_lesson")
        lesson_input = {
            "action": "create_lesson",
            "level": level_num,
            "raw_text": raw_text
        }
        lesson_result = await self.agent.run(lesson_input)
        lesson_md = lesson_result.get("output", {}).get("lesson_markdown", "Failed to generate lesson.")
        
        lesson_path = target_dir / "lesson.md"
        lesson_path.write_text(lesson_md, encoding="utf-8")
        print("  Lesson saved successfully.")
        
        # 2. Action: create_quiz
        print("  Calling CurriculumAgent -> create_quiz")
        quiz_input = {
            "action": "create_quiz",
            "level": level_num,
            "lesson_text": lesson_md
        }
        quiz_result = await self.agent.run(quiz_input)
        
        quiz_data = quiz_result.get("output", {}).get("questions", [])
        quiz_path = target_dir / "quiz.json"
        
        if quiz_data:
            quiz_path.write_text(json.dumps(quiz_data, indent=2), encoding="utf-8")
            print(f"  Quiz saved successfully with {len(quiz_data)} questions.")
        else:
            print("  Failed to generate valid quiz questions from agent output.")
            
        print(f"[CurriculumService] Level {level_num} completed.\n")
        return True

curriculum_service = CurriculumService()
