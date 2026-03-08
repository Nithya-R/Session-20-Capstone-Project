import os
import sys
import json
from pathlib import Path

# Setup Pathing
BACKEND_ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(BACKEND_ROOT))

# Force load .env from backend
from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

import numpy as np

# Mocking heavy dependencies to test embedding integration directly
from unittest.mock import MagicMock
mock_modules = ["markitdown", "trafilatura", "pymupdf4llm", "fitz"]
for module in mock_modules:
    sys.modules[module] = MagicMock()

from mcp_servers.server_rag_civic import get_embedding
from config.settings_loader import settings

def test_embedding_provider():
    print("--- Starting Refined Embedding Provider Test ---\n")
    
    # Testing the currently configured provider (likely huggingface/local)
    # And specifically testing Gemini if creds available
    providers = [settings["models"].get("embedding_provider", "huggingface"), "gemini"]
    
    for provider in providers:
        print(f"Testing Provider: {provider}")
        test_text = "Civic Lens is an adaptive learning platform for Indian politics."
        
        try:
            from mcp_servers.server_rag_civic import get_embedding_hf, get_embedding_gemini
            
            if provider == "huggingface":
                embedding = get_embedding_hf(test_text)
                print(f"SUCCESS: Hugging Face (Local)")
            elif provider == "gemini" and os.getenv("GEMINI_API_KEY"):
                embedding = get_embedding_gemini(test_text)
                print(f"SUCCESS: Gemini")
            else:
                print(f"Skipping {provider}")
                continue
                
            print(f"Dimension: {embedding.shape[0]}")
            print(f"Sample: {embedding[:3]}...")
            
        except Exception as e:
            print(f"FAILURE: {provider} - {e}")
        print("-" * 30)
        
    print("\n--- Test Completed ---")

if __name__ == "__main__":
    test_embedding_provider()
