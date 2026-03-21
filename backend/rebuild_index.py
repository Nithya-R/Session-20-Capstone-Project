import os
import sys
import json
import shutil
import multiprocessing
from pathlib import Path

# MUST happen before importing torch/tokenizers — avoids segfault on macOS + Python 3.13
if sys.platform == "darwin":
    multiprocessing.set_start_method("spawn", force=True)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Use script location so rebuild works on any machine
backend_dir = Path(__file__).resolve().parent
index_dir = backend_dir / "faiss_index"
sys.path.insert(0, str(backend_dir))

# 1. Clean up old FAISS index files to ensure we don't have dangling chunks
for f in ["index.bin", "metadata.json", "doc_index_cache.json"]:
    file_path = index_dir / f
    if file_path.exists():
        file_path.unlink()
        print(f"Deleted {f}")

# 2. Run the indexer service to rebuild the index
from services.indexer_service import IndexerService

if __name__ == "__main__":
    print("\nStarting index rebuild...")
    indexer = IndexerService()
    stats = indexer.sync_index()
    print("Rebuild complete. Stats:", json.dumps(stats, indent=2))
