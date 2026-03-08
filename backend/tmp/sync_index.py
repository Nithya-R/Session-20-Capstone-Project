import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path("c:/Users/Nithya/My Project - EAG/backend").resolve()))

from mcp_servers.server_rag_civic import process_documents

print("Starting indexing synchronization...")
stats = process_documents()
print(f"Indexing Complete: {stats}")
