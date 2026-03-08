import os
import sys
import json
import time
from pathlib import Path

# Add backend to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

# Import the core indexing logic from the RAG server
# Since the server_rag_civic is designed as an MCP, we can also import its processing logic directly 
# or use it as a submodule.
from mcp_servers.server_rag_civic import process_documents

class IndexerService:
    def __init__(self):
        self.data_dir = BASE_DIR / "data"
        self.index_cache = BASE_DIR / "faiss_index"
        
    def sync_index(self):
        """Scan data directory and update the FAISS index."""
        print(f"🚀 [IndexerService] Starting synchronization...")
        print(f"📂 Data Directory: {self.data_dir}")
        
        try:
            start_time = time.time()
            stats = process_documents()
            duration = time.time() - start_time
            
            summary = (
                f"\n✨ Sync Completed in {duration:.2f}s\n"
                f"-----------------------------------\n"
                f"✅ Files Processed: {stats['processed']}\n"
                f"⏭️  Files Skipped:   {stats['skipped']}\n"
                f"📊 New Chunks:      {stats['new_chunks']}\n"
                f"❌ Errors:          {stats['errors']}\n"
                f"-----------------------------------\n"
            )
            print(summary)
            return stats
            
        except Exception as e:
            print(f"❌ [IndexerService] Sync failed: {e}")
            return None

if __name__ == "__main__":
    # Standalone execution
    indexer = IndexerService()
    indexer.sync_index()
