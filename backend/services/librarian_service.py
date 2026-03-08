import os
import json
from pathlib import Path
from fastapi import UploadFile, BackgroundTasks
import sys

# Setup Project Paths
ROOT = Path(__file__).parent.resolve() # backend/services
PROJECT_ROOT = ROOT.parent.resolve() # backend

# Import from local backend components
from agents.base_agent import AgentRunner
from shared.state import get_multi_mcp, PROJECT_ROOT as FRAMEWORK_ROOT
from mcp_servers.server_rag_civic import convert_pdf_to_markdown
from services.curriculum_service import curriculum_service
import asyncio

class LibrarianService:
    def __init__(self):
        self.multi_mcp = get_multi_mcp()
        self.agent_runner = AgentRunner(self.multi_mcp)
        
        # ISOLATION: Point to local backend data and index
        self.data_dir = PROJECT_ROOT / "data"
        self.index_dir = PROJECT_ROOT / "faiss_index"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_document(self, file: UploadFile, sub_path: str = "", background_tasks: BackgroundTasks = None):
        """
        Full ingestion pipeline:
        1. Save file
        2. Extract text (PDF, Web, etc.)
        3. Classify with LibrarianAgent
        4. Re-index with metadata in isolated RAG
        """
        target_dir = self.data_dir
        if sub_path:
            target_dir = self.data_dir / sub_path.strip("/")
            target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / file.filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 2. Extract Text
        markdown_content = ""
        if file.filename.lower().endswith(".pdf"):
            extraction = convert_pdf_to_markdown(str(file_path))
            markdown_content = extraction.markdown
        else:
            try:
                markdown_content = content.decode("utf-8")
            except:
                markdown_content = f"[Binary/Unknown Content: {file.filename}]"

        # 3. Classify with LibrarianAgent
        analysis_text = markdown_content[:8000]
        agent_input = {
            "text": analysis_text,
            "filename": file.filename
        }
        
        classification_result = await self.agent_runner.run_agent("LibrarianAgent", agent_input)
        
        metadata = classification_result.get("output", {
            "level": 1,
            "level_name": "Unclassified",
            "topics": ["General"],
            "summary": "Processing failed or no output."
        })

        # 4. Trigger Re-indexing via the SPECIALIZED Civic RAG MCP Tool
        # We use the 'rag_civic' server registered in config
        reindex_args = {
            "target_path": str(file_path.relative_to(PROJECT_ROOT / "data")),
            "force": True
        }
        
        try:
            # Note: 'rag_civic' must be registered in the backend's mcp_config.json
            await self.multi_mcp.call_tool("rag_civic", "reindex_documents_civic", reindex_args)
        except Exception as e:
            print(f"RAG Indexing failed: {e}")
        
        # Update isolated ledger
        self._update_ledger_metadata(file_path.relative_to(self.data_dir), metadata)
        
        # 5. Asynchronously Regenerate Curriculum for the assigned level
        assigned_level = metadata.get("level")
        if assigned_level and background_tasks:
            def regen_curriculum(level):
                 loop = asyncio.new_event_loop()
                 asyncio.set_event_loop(loop)
                 loop.run_until_complete(curriculum_service.generate_level(level))
                 loop.close()
                 
            background_tasks.add_task(regen_curriculum, assigned_level)

        return {
            "status": "success",
            "file": file.filename,
            "analysis": metadata
        }

    def _update_ledger_metadata(self, rel_path, metadata):
        ledger_path = self.index_dir / "ledger.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        rel_path_str = str(rel_path).replace("\\", "/")
        
        ledger = {"files": {}}
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text())
            except Exception as e:
                print(f"Error reading ledger: {e}")
                
        if "files" not in ledger:
             ledger["files"] = {}
             
        # Create or Update the entry
        if rel_path_str not in ledger["files"]:
            ledger["files"][rel_path_str] = {}
            
        file_entry = ledger["files"][rel_path_str]
        file_entry["librarian_metadata"] = metadata
        file_entry["level"] = metadata.get("level")
        file_entry["topics"] = metadata.get("topics")
        
        try:
             ledger_path.write_text(json.dumps(ledger, indent=2))
        except Exception as e:
             print(f"Error writing ledger: {e}")

librarian_service = LibrarianService()
