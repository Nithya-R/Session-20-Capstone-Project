import os
import json
import shutil
from pathlib import Path

backend_dir = Path("c:/Users/Nithya/My Project - EAG/backend")
index_dir = backend_dir / "faiss_index"

# 1. Clean up old FAISS index files to ensure we don't have dangling chunks
for f in ["index.bin", "metadata.json", "doc_index_cache.json"]:
    file_path = index_dir / f
    if file_path.exists():
        file_path.unlink()
        print(f"Deleted {f}")

# 2. Run the indexer service to rebuild the index
import sys
sys.path.append(str(backend_dir))
from services.indexer_service import IndexerService

if __name__ == "__main__":
    print("\nStarting index rebuild...")
    indexer = IndexerService()
    stats = indexer.sync_index()
    print("Rebuild complete. Stats:", json.dumps(stats, indent=2))
