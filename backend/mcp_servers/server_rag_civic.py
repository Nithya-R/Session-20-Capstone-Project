from mcp.server.fastmcp import FastMCP, Image

from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import hashlib
import time
import shutil
import re
import base64
import asyncio
import concurrent.futures
import threading
import pickle
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# Setup Pathing internal to backend
ROOT = Path(__file__).parent.resolve() # backend/mcp_servers
PROJECT_ROOT = ROOT.parent.resolve() # backend
load_dotenv(PROJECT_ROOT / ".env")

# suppress_stdout and other imports from server_rag.py
import contextlib

@contextlib.contextmanager
def suppress_stdout():
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout

with suppress_stdout():
    import numpy as np
    # Import torch BEFORE faiss to avoid BLAS/OpenMP library conflicts that cause segfaults
    # on macOS (Apple Silicon + Python 3.13). PyTorch must load its BLAS first.
    try:
        import torch
    except ImportError:
        pass
    import faiss
    import requests
    from markitdown import MarkItDown
    from tqdm import tqdm
    import trafilatura
    import pymupdf4llm
    import fitz 
    try:
        fitz.TOOLS.mupdf_display_errors(False) 
        fitz.TOOLS.set_stderr_log(False)
    except:
        pass

# Import models and settings from local backend
from mcp_servers.models import AddInput, AddOutput, SqrtInput, SqrtOutput, StringsToIntsInput, StringsToIntsOutput, ExpSumInput, ExpSumOutput, PythonCodeInput, PythonCodeOutput, UrlInput, FilePathInput, MarkdownInput, MarkdownOutput, ChunkListOutput, SearchDocumentsInput
from config.settings_loader import settings, get_ollama_url, get_model, get_timeout

# Specialized MCP name
mcp = FastMCP("Civic Lens RAG")

# --- Settings ---
# ... (rest of settings remain same, they use settings_loader)
EMBED_URL = get_ollama_url("embeddings")
OLLAMA_CHAT_URL = get_ollama_url("chat")
OLLAMA_URL = get_ollama_url("generate")
EMBED_MODEL = get_model("embedding")
RAG_LLM_MODEL = get_model("semantic_chunking")
VISION_MODEL = get_model("image_captioning")
CHUNK_SIZE = settings["rag"]["chunk_size"]
CHUNK_OVERLAP = settings["rag"]["chunk_overlap"]
MAX_CHUNK_LENGTH = settings["rag"]["max_chunk_length"]
TOP_K = settings["rag"]["top_k"]
PDF_EXCLUSIONS = settings["rag"].get("pdf_exclusions", {})
OLLAMA_TIMEOUT = get_timeout()

# === DOMAIN ISOLATION PATHS ===
CIVIC_DATA_SUBDIR = "civic_lens"

BASE_DATA_DIR = PROJECT_ROOT / "data"
TARGET_DATA_DIR = BASE_DATA_DIR # In backend, data/ is already for civic lens
INDEX_CACHE = PROJECT_ROOT / "faiss_index"
INDEX_CACHE.mkdir(parents=True, exist_ok=True)

# Global indexing status
INDEXING_STATUS = {
    "active": False,
    "total": 0,
    "completed": 0,
    "currentFile": ""
}
INDEXING_LOCK = threading.Lock()
REINDEX_BUSY_LOCK = threading.Lock()

def mcp_log(level: str, message: str) -> None:
    sys.stderr.write(f"{level}: {message}\n")
    sys.stderr.flush()

# --- Global Model Cache ---
HF_LOCAL_MODEL = None

# Disable tokenizer parallelism to avoid fork-safety segfaults on macOS + Python 3.13.
# Must be set BEFORE importing transformers/tokenizers.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

def _init_hf_model():
    """Lazily load SentenceTransformer once."""
    global HF_LOCAL_MODEL
    if HF_LOCAL_MODEL is not None:
        return HF_LOCAL_MODEL
    from sentence_transformers import SentenceTransformer
    model_id = settings.get("huggingface", {}).get("embedding_model", "sentence-transformers/all-mpnet-base-v2")
    HF_LOCAL_MODEL = SentenceTransformer(model_id)
    return HF_LOCAL_MODEL

def get_embedding_hf(text: str) -> np.ndarray:
    """Local Hugging Face embedding generation using sentence-transformers"""
    try:
        model = _init_hf_model()
        embedding = model.encode(text, show_progress_bar=False, convert_to_numpy=True)
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        sys.stderr.write(f"❌ Local HF Embedding failed: {e}\n")
        raise

def get_embedding_ollama(text: str) -> np.ndarray:
    """Ollama embedding generation"""
    try:
        result = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=OLLAMA_TIMEOUT)
        result.raise_for_status()
        return np.array(result.json()["embedding"], dtype=np.float32)
    except Exception as e:
        print(f"❌ Ollama Embedding failed: {e}")
        raise

def get_embedding_gemini(text: str) -> np.ndarray:
    """Gemini embedding generation"""
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        model = "text-embedding-004"
        result = client.models.embed_content(
            model=model,
            contents=text
        )
        return np.array(result.embeddings[0].values, dtype=np.float32)
    except Exception as e:
        sys.stderr.write(f"❌ Gemini Embedding failed: {e}\n")
        raise

def get_embedding(text: str) -> np.ndarray:
    """Route embedding request to the configured provider"""
    provider = settings["models"].get("embedding_provider", "huggingface")
    
    if provider == "huggingface":
        return get_embedding_hf(text) # Now local
    elif provider == "gemini":
        return get_embedding_gemini(text)
    else:
        return get_embedding_ollama(text)

# ... (Helper matching/chunking functions)

def find_sentence_end(text: str, target_pos: int, direction: str = 'back', window: int = 150) -> int:
    if direction == 'back':
        start = max(0, target_pos - window)
        search_area = text[start:target_pos]
        matches = list(re.finditer(r'[.!?](\s+|$)', search_area))
        if matches:
            return start + matches[-1].end()
    else:
        end = min(len(text), target_pos + window)
        search_area = text[target_pos:end]
        match = re.search(r'[.!?](\s+|$)', search_area)
        if match:
            return target_pos + match.end()
    return target_pos

def get_safe_chunks(text: str, max_words=512, overlap=50) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    start_char = 0
    total_len = len(text)
    avg_chars_per_word = 6
    target_chunk_len = max_words * avg_chars_per_word
    while start_char < total_len:
        remaining = text[start_char:]
        if not remaining.strip(): break
        if len(remaining.split()) <= max_words:
            chunks.append(remaining.strip())
            break
        end_pos = min(start_char + target_chunk_len, total_len)
        lookback_window = int(target_chunk_len * 0.3)
        new_end = find_sentence_end(text, end_pos, direction='back', window=lookback_window)
        if new_end == end_pos:
            lookforward_window = int(target_chunk_len * 0.2)
            new_end = find_sentence_end(text, end_pos, direction='forward', window=lookforward_window)
        if new_end == end_pos:
            space_match = re.search(r'\s', text[end_pos:])
            if space_match:
                new_end = end_pos + space_match.start() + 1
            else:
                new_end = total_len
        chunk = text[start_char:new_end].strip()
        if chunk:
            chunks.append(chunk)
        overlap_chars = overlap * avg_chars_per_word
        next_start_target = new_end - overlap_chars
        start_char = max(start_char + (target_chunk_len // 2), next_start_target)
        if start_char >= total_len: break
        next_space = text.find(' ', start_char)
        if next_space != -1 and next_space < (new_end + target_chunk_len):
            start_char = next_space + 1
    return chunks

# --- Extraction Tools ---

def convert_pdf_to_markdown(string: str) -> MarkdownOutput:
    """Specialized PDF to Markdown extraction using PyMuPDF4LLM."""
    if not os.path.exists(string):
        return MarkdownOutput(markdown=f"File not found: {string}")
    
    global_image_dir = INDEX_CACHE / "images"
    global_image_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        import pymupdf
        doc = pymupdf.open(string)
        full_markdown = ""
        
        for i in range(len(doc)):
            filename = os.path.basename(string)
            if filename in PDF_EXCLUSIONS:
                skip_first = PDF_EXCLUSIONS[filename].get("skip_first", 0)
                skip_last = PDF_EXCLUSIONS[filename].get("skip_last", 0)
                if i < skip_first or i >= len(doc) - skip_last:
                    continue
                    
            page_num = i + 1
            # Extract markdown for a single page
            page_md = pymupdf4llm.to_markdown(
                doc,
                pages=[i],
                write_images=True,
                image_path=str(global_image_dir)
            )
            # Inject page markers
            full_markdown += f"\n\n<!-- PAGE_START: {page_num} -->\n{page_md}\n<!-- PAGE_END: {page_num} -->\n\n"
        
        doc.close()
        markdown = full_markdown
    except Exception as e:
        mcp_log("ERROR", f"PDF conversion failed: {e}")
        return MarkdownOutput(markdown=f"Failed to extract text from PDF: {string}")

    # Re-point image links
    markdown = re.sub(
        r'!\[\]\((.*?/images/)([^)]+)\)',
        r'![](images/\2)',
        markdown.replace("\\", "/")
    )
    return MarkdownOutput(markdown=markdown)

@mcp.tool()
def extract_web_content_civic(url: str) -> str:
    """Extract content from a website using Trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded)
            return content if content else "Failed to extract readable content."
        return "Failed to fetch URL."
    except Exception as e:
        return f"Error extracting web content: {e}"

def _load_index_and_metadata():
    """Load FAISS index and metadata. Returns (index, metadata) or (None, None) if invalid/out of sync."""
    METADATA_FILE = INDEX_CACHE / "metadata.json"
    INDEX_FILE = INDEX_CACHE / "index.bin"
    if not INDEX_FILE.exists() or not METADATA_FILE.exists():
        return None, None
    try:
        metadata = json.loads(METADATA_FILE.read_text())
        if not isinstance(metadata, list) or len(metadata) == 0:
            return None, None
        index = faiss.read_index(str(INDEX_FILE))
        if index.ntotal != len(metadata):
            mcp_log("WARN", f"FAISS index out of sync: index has {index.ntotal} vectors, metadata has {len(metadata)}. Rebuild required.")
            return None, None
        return index, metadata
    except Exception as e:
        mcp_log("ERROR", f"Load index/metadata failed: {e}")
        return None, None


@mcp.tool()
def search_stored_documents_rag_civic(query: str, doc_path: str = None) -> list[str]:
    """Search Civic Lens documents using Hybrid Search (FAISS + BM25)."""
    ensure_faiss_ready()
    try:
        index, metadata = _load_index_and_metadata()
        if index is None or metadata is None:
            return ["No relevant Civic Lens documents found. Index may be empty or out of sync; try reindexing."]
        
        query_vec = get_embedding(query).reshape(1, -1)
        k = min(30, index.ntotal)
        D, I = index.search(query_vec, k)
        
        results = []
        for idx in I[0]:
            if idx == -1 or idx >= len(metadata):
                continue
            entry = metadata[idx]
            if not doc_path or entry.get('doc') == doc_path:
                results.append(f"{entry['chunk']}\n[Source: {entry.get('doc')} p{entry.get('page', 1)}]")
        
        return results[:TOP_K] if results else ["No relevant Civic Lens documents found."]
    except Exception as e:
        mcp_log("ERROR", f"Search failed: {e}")
        return [f"Error: {e}"]

def process_single_file(file: Path, doc_path_root: Path, cache_meta: dict):
    try:
        rel_path = file.relative_to(doc_path_root).as_posix()
        fhash = hashlib.md5(file.read_bytes()).hexdigest()
        
        if rel_path in cache_meta and cache_meta[rel_path] == fhash:
            return {"status": "SKIP", "rel_path": rel_path}

        ext = file.suffix.lower()
        markdown = ""

        if ext == ".pdf":
            markdown = convert_pdf_to_markdown(str(file)).markdown
        elif ext == ".py":
            markdown = f"```python\n{file.read_text()}\n```"
        else:
            # Fallback to MarkItDown for other formats (docx, xlsx, etc.)
            markdown = MarkItDown().convert(str(file)).text_content

        if not markdown.strip():
            return {"status": "WARN", "rel_path": rel_path}

        final_chunks = []
        for sc in get_safe_chunks(markdown):
            final_chunks.append((sc, 1))

        embeddings, metadata = [], []
        for chunk, page in final_chunks:
            emb = get_embedding(chunk)
            embeddings.append(emb)
            metadata.append({
                "doc": rel_path,
                "chunk": chunk,
                "chunk_id": f"{rel_path}_{len(embeddings)}",
                "page": page
            })
        
        return {
            "status": "SUCCESS",
            "rel_path": rel_path,
            "hash": fhash,
            "embeddings": embeddings,
            "metadata": metadata
        }
    except Exception as e:
        return {"status": "ERROR", "rel_path": str(file), "message": str(e)}

def process_documents(target_path: str = None) -> dict:
    """Orchestrate document processing and FAISS indexing."""
    METADATA_FILE = INDEX_CACHE / "metadata.json"
    INDEX_FILE = INDEX_CACHE / "index.bin"
    CACHE_FILE = INDEX_CACHE / "doc_index_cache.json"

    CACHE_META = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    metadata = json.loads(METADATA_FILE.read_text()) if METADATA_FILE.exists() else []
    index = faiss.read_index(str(INDEX_FILE)) if INDEX_FILE.exists() else None

    # If index and metadata are out of sync (e.g. after a failed write), rebuild from scratch
    if index is not None and metadata is not None and index.ntotal != len(metadata):
        mcp_log("WARN", f"FAISS index out of sync (index.ntotal={index.ntotal}, metadata len={len(metadata)}). Rebuilding.")
        for fn in ["index.bin", "metadata.json", "doc_index_cache.json"]:
            (INDEX_CACHE / fn).unlink(missing_ok=True)
        index = None
        metadata = []
        CACHE_META = {}

    files_to_process = []
    if target_path:
        target_file = BASE_DATA_DIR / target_path
        if target_file.exists():
            files_to_process = [target_file]
    else:
        if TARGET_DATA_DIR.exists():
            for root, _, filenames in os.walk(TARGET_DATA_DIR):
                for f in filenames:
                    if not f.startswith('.') and Path(f).suffix.lower() not in ['.mp4', '.bin', '.exe']:
                        files_to_process.append(Path(root) / f)

    # If we would update any existing file, do a full rebuild so index and metadata stay in sync
    # (FAISS IndexFlatL2 cannot remove vectors, so incremental update would desync metadata)
    for f in files_to_process:
        try:
            rel_path = f.relative_to(BASE_DATA_DIR).as_posix()
            fhash = hashlib.md5(f.read_bytes()).hexdigest()
            if rel_path in CACHE_META and CACHE_META[rel_path] != fhash:
                for fn in ["index.bin", "metadata.json", "doc_index_cache.json"]:
                    (INDEX_CACHE / fn).unlink(missing_ok=True)
                return process_documents(target_path=target_path)
        except Exception:
            pass

    stats = {"processed": 0, "skipped": 0, "errors": 0, "new_chunks": 0}

    for f in tqdm(files_to_process, desc="Indexing"):
        res = process_single_file(f, BASE_DATA_DIR, CACHE_META)
        if res["status"] == "SUCCESS":
            rel_path = res["rel_path"]
            # Clean old entries only when we did not already clear (first run or post-rebuild)
            if rel_path in CACHE_META:
                metadata = [m for m in metadata if m.get("doc") != rel_path]
            
            if index is None:
                dimension = len(res["embeddings"][0])
                index = faiss.IndexFlatL2(dimension)
            else:
                # Ensure new embeddings match index dimension (e.g. same embedding model)
                if len(res["embeddings"][0]) != index.d:
                    mcp_log("ERROR", f"Embedding dimension mismatch: index has {index.d}, new has {len(res['embeddings'][0])}. Rebuild the index.")
                    stats["errors"] += 1
                    continue

            index.add(np.stack(res["embeddings"]))
            metadata.extend(res["metadata"])
            CACHE_META[rel_path] = res["hash"]
            
            stats["processed"] += 1
            stats["new_chunks"] += len(res["embeddings"])
            
            # Atomic save
            CACHE_FILE.write_text(json.dumps(CACHE_META, indent=2))
            METADATA_FILE.write_text(json.dumps(metadata, indent=2))
            faiss.write_index(index, str(INDEX_FILE))
        elif res["status"] == "SKIP":
            stats["skipped"] += 1
        else:
            stats["errors"] += 1
            
    return stats

@mcp.tool()
async def sync_data_index_civic() -> str:
    """Scan 'backend/data' and index any new or modified files. Returns summary."""
    try:
        stats = process_documents()
        summary = (
            f"Indexing Complete.\n"
            f"- Files Processed: {stats['processed']}\n"
            f"- Files Skipped (unchanged): {stats['skipped']}\n"
            f"- New Chunks Added: {stats['new_chunks']}\n"
            f"- Errors: {stats['errors']}"
        )
        return summary
    except Exception as e:
        return f"Error during sync: {e}"

@mcp.tool()
async def reindex_documents_civic(target_path: str = None, force: bool = False) -> str:
    """Manual re-index for Civic Lens domain."""
    if force and not target_path:
        for f in ["index.bin", "metadata.json", "doc_index_cache.json"]:
            p = INDEX_CACHE / f
            if p.exists(): p.unlink()
    
    threading.Thread(target=process_documents, args=(target_path,), daemon=True).start()
    return "Civic RAG re-indexing started."

def ensure_faiss_ready():
    index, metadata = _load_index_and_metadata()
    if index is None or metadata is None:
        process_documents()

if __name__ == "__main__":
    mcp.run()
