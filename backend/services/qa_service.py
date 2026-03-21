"""
QAService
---------
Answers civic knowledge questions using two tools:
  1. Knowledge Base (FAISS vector search over ingested documents)
  2. Internet Search (Gemini Google Search grounding for current events / gaps)

The LLM decides which tool(s) to use based on the question context, then
synthesizes a single grounded answer.
"""

import os
import sys
import asyncio
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from user_store.user_hub import save_qa_question, get_qa_history


# ---------------------------------------------------------------------------
# Tool 1 — Knowledge Base (FAISS)
# ---------------------------------------------------------------------------

async def _search_knowledge_base(query: str) -> list[str]:
    """Run FAISS semantic search and return top-k text chunks."""
    from mcp_servers.server_rag_civic import search_stored_documents_rag_civic
    results = search_stored_documents_rag_civic(query)
    return [r for r in results
            if not r.startswith("Error")
            and r != "No relevant Civic Lens documents found."
            and "Index may be empty" not in r]


# ---------------------------------------------------------------------------
# Tool 2 — Internet Search (Gemini + Google Search grounding)
# ---------------------------------------------------------------------------

async def _search_internet(question: str) -> str:
    """Use Gemini with Google Search grounding to get current / supplementary info."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    google_search_tool = types.Tool(google_search=types.GoogleSearch())

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash-lite",
        contents=f"Answer this Indian civics / governance question using web search results. "
                 f"Be factual and cite sources where possible.\n\nQuestion: {question}",
        config=types.GenerateContentConfig(tools=[google_search_tool]),
    )
    return response.text.strip() if response.text else ""


# ---------------------------------------------------------------------------
# Route + Synthesize
# ---------------------------------------------------------------------------

_ROUTE_PROMPT = """\
You are a routing classifier for a civic education Q&A system about Indian governance.

Given the user question below, decide which tool(s) to use:

- "knowledge_base" — for questions about constitutional concepts, government structure, \
fundamental rights, civics theory, and anything that a textbook or the Indian Constitution would cover.
- "internet" — for questions about current events, recent news, specific dates/statistics, \
ongoing government schemes, election results, or anything that needs up-to-date information.
- "both" — when the question benefits from foundational knowledge AND current context.

Reply with EXACTLY one word: knowledge_base, internet, or both.

Question: {question}
"""

_ANSWER_PROMPT_KB = """\
You are a helpful civics expert for the Civic Lens platform (Indian governance education).
Answer the question below using the provided context from the civic knowledge base.
Be clear, concise, and educational. Answer in 3-5 sentences.
If the context doesn't fully answer the question, say so honestly.

Context:
{context}

Question: {question}

Answer:"""

_ANSWER_PROMPT_BOTH = """\
You are a helpful civics expert for the Civic Lens platform (Indian governance education).
Answer the question below using BOTH the knowledge base context AND the internet search results.
Prioritise accuracy. Be clear, concise, and educational. Answer in 3-5 sentences.
When citing current information from the internet, mention that it is from recent sources.

Knowledge Base Context:
{kb_context}

Internet Search Results:
{web_context}

Question: {question}

Answer:"""

_ANSWER_PROMPT_WEB = """\
You are a helpful civics expert for the Civic Lens platform (Indian governance education).
Answer the question below using the internet search results provided.
Be clear, concise, and educational. Answer in 3-5 sentences.

Internet Search Results:
{web_context}

Question: {question}

Answer:"""


async def _route_question(question: str) -> str:
    """Ask the LLM which tool(s) to use."""
    from config.settings_loader import reload_settings
    from core.model_manager import ModelManager

    cfg = reload_settings().get("agent", {})
    mm = ModelManager(
        cfg.get("default_model", "gemini-2.5-flash-lite"),
        provider=cfg.get("model_provider", "gemini"),
    )
    raw = await mm.generate_text(_ROUTE_PROMPT.format(question=question))
    route = raw.strip().lower().replace('"', "").replace("'", "")
    if route not in ("knowledge_base", "internet", "both"):
        route = "both"
    return route


async def _answer_with_llm(prompt: str) -> str:
    from config.settings_loader import reload_settings
    from core.model_manager import ModelManager

    cfg = reload_settings().get("agent", {})
    mm = ModelManager(
        cfg.get("default_model", "gemini-2.5-flash-lite"),
        provider=cfg.get("model_provider", "gemini"),
    )
    return await mm.generate_text(prompt)


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class QAService:

    async def ask(self, user_id: str, question: str) -> dict:
        """
        Route the question to the right tool(s), generate an answer, persist history.

        Returns:
            { answer: str, sources: list[dict], tool_used: str, history: list[str] }
        """
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty.")

        route = await _route_question(question)

        chunks = []
        web_answer = ""
        sources = []

        if route in ("knowledge_base", "both"):
            chunks = await _search_knowledge_base(question)

        if route in ("internet", "both"):
            try:
                web_answer = await _search_internet(question)
            except Exception as e:
                sys.stderr.write(f"[QA] Internet search failed: {e}\n")
                web_answer = ""

        # Build final prompt based on what we got
        kb_context = "\n\n---\n\n".join(chunks[:5]) if chunks else ""

        if chunks and web_answer:
            prompt = _ANSWER_PROMPT_BOTH.format(
                kb_context=kb_context, web_context=web_answer, question=question
            )
        elif chunks:
            prompt = _ANSWER_PROMPT_KB.format(context=kb_context, question=question)
        elif web_answer:
            prompt = _ANSWER_PROMPT_WEB.format(web_context=web_answer, question=question)
        else:
            prompt = (
                f"You are a helpful civics expert. Answer the following civics question clearly "
                f"and concisely in 3-5 sentences.\n\nQuestion: {question}\n\nAnswer:"
            )

        answer = await _answer_with_llm(prompt)

        save_qa_question(user_id, question)

        # Build source snippets for frontend
        for chunk in chunks[:3]:
            lines = chunk.split("\n")
            source_line = next((l for l in lines if l.startswith("[Source:")), None)
            text = "\n".join(l for l in lines if not l.startswith("[Source:")).strip()
            label = source_line.strip("[]") if source_line else None
            sources.append({"text": text[:300], "label": label})

        if web_answer:
            sources.append({"text": web_answer[:300], "label": "Internet Search"})

        return {
            "answer": answer,
            "sources": sources,
            "tool_used": route,
            "history": get_qa_history(user_id),
        }

    def history(self, user_id: str) -> list[str]:
        return get_qa_history(user_id)


qa_service = QAService()
