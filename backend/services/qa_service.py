"""
QAService
---------
Answers civic knowledge questions using RAG (FAISS vector search) + Gemini.
Persists each question to the user's profile for suggestion bubbles.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from user_store.user_hub import save_qa_question, get_qa_history


async def _search(query: str) -> list[str]:
    """Run FAISS hybrid search and return top-k text chunks."""
    from mcp_servers.server_rag_civic import search_stored_documents_rag_civic
    results = search_stored_documents_rag_civic(query)
    # Filter out error strings
    return [r for r in results if not r.startswith("Error") and r != "No relevant Civic Lens documents found."]


async def _answer_with_llm(question: str, chunks: list[str]) -> str:
    from config.settings_loader import reload_settings
    from core.model_manager import ModelManager

    cfg = reload_settings().get("agent", {})
    mm = ModelManager(
        cfg.get("default_model", "gemini-2.5-flash-lite"),
        provider=cfg.get("model_provider", "gemini"),
    )

    if chunks:
        context = "\n\n---\n\n".join(chunks[:5])
        prompt = (
            f"You are a helpful civics expert for the Civic Lens platform.\n"
            f"Answer the question below using the provided context from the civic knowledge base.\n"
            f"Be clear, concise, and educational. Answer in 3-5 sentences.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
    else:
        prompt = (
            f"You are a helpful civics expert. Answer the following civics question clearly "
            f"and concisely in 3-5 sentences.\n\nQuestion: {question}\n\nAnswer:"
        )

    return await mm.generate_text(prompt)


class QAService:

    async def ask(self, user_id: str, question: str) -> dict:
        """
        Search the FAISS knowledge base, generate an answer, and persist the question.

        Returns:
            { answer: str, sources: list[str], history: list[str] }
        """
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty.")

        chunks = await _search(question)
        answer = await _answer_with_llm(question, chunks)

        # Persist to user context
        save_qa_question(user_id, question)

        # Return clean source snippets (strip [Source: ...] label for display)
        sources = []
        for chunk in chunks[:3]:
            lines = chunk.split("\n")
            source_line = next((l for l in lines if l.startswith("[Source:")), None)
            text = "\n".join(l for l in lines if not l.startswith("[Source:")).strip()
            label = source_line.strip("[]") if source_line else None
            sources.append({"text": text[:300], "label": label})

        return {
            "answer": answer,
            "sources": sources,
            "history": get_qa_history(user_id),
        }

    def history(self, user_id: str) -> list[str]:
        return get_qa_history(user_id)


qa_service = QAService()
