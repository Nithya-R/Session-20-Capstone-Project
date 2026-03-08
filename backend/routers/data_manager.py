from fastapi import APIRouter, HTTPException, BackgroundTasks
import os
import json
from pathlib import Path
from mcp_servers.server_rag_civic import reindex_documents_civic
from services.curriculum_service import curriculum_service
import asyncio

router = APIRouter(prefix="/data", tags=["Data Management"])

# Setup Paths relative to backend
ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "faiss_index"
LEDGER_PATH = INDEX_DIR / "ledger.json"

@router.get("/files")
async def list_files():
    """Returns a list of all ingested files and their metadata from the ledger."""
    if not LEDGER_PATH.exists():
        return {"files": {}}
        
    try:
        ledger_data = json.loads(LEDGER_PATH.read_text())
        return {"files": ledger_data.get("files", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read ledger: {e}")

@router.delete("/files/{filename}")
async def delete_file(filename: str, background_tasks: BackgroundTasks):
    """
    Deletes a file, removes it from the ledger, triggers FAISS re-indexing,
    and recalculates the curriculum for the affected level.
    """
    file_path = DATA_DIR / filename
    rel_path_str = filename # Default to root of data dir for this simple implementation
    
    # Check if file exists
    if not file_path.exists() and not LEDGER_PATH.exists():
         raise HTTPException(status_code=404, detail="File not found")
         
    affected_level = None
         
    # 1. Update Ledger
    if LEDGER_PATH.exists():
        try:
            ledger = json.loads(LEDGER_PATH.read_text())
            if "files" in ledger and rel_path_str in ledger["files"]:
                affected_level = ledger["files"][rel_path_str].get("level")
                del ledger["files"][rel_path_str]
                LEDGER_PATH.write_text(json.dumps(ledger, indent=2))
        except Exception as e:
            print(f"Error updating ledger during deletion: {e}")
            
    # 2. Delete Physical File
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")
            
    # 3. Trigger Re-indexing (we use background tasks so endpoint returns fast)
    # We must await the reindex_documents_civic function because it's async in FastMCP
    def run_reindex():
        try:
             # FastMCP tools are async
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             loop.run_until_complete(reindex_documents_civic(force=True))
             loop.close()
        except Exception as e:
             print(f"Background re-index failed: {e}")

    background_tasks.add_task(run_reindex)
    
    # 4. Asynchronously Regenerate Curriculum if a level was affected
    if affected_level is not None:
        def regen_curriculum(level):
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             loop.run_until_complete(curriculum_service.generate_level(level))
             loop.close()
             
        background_tasks.add_task(regen_curriculum, affected_level)

    return {
        "status": "success", 
        "message": f"Deleted {filename}. Re-indexing and curriculum updates started in background.",
        "affected_level": affected_level
    }
