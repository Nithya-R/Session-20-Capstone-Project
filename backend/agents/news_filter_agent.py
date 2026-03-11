"""
NewsFilterAgent
---------------
Two plain-text LLM calls:
  1. Filter  — returns comma-separated indices of political articles
  2. Translate — returns "N. English title" lines for selected articles

No JSON parsing at all.
"""

import re
from pathlib import Path
from core.model_manager import ModelManager
from config.settings_loader import reload_settings


class NewsFilterAgent:

    def _get_mm(self) -> ModelManager:
        s = reload_settings()
        ag = s.get("agent", {})
        ov = ag.get("overrides", {}).get("NewsFilterAgent", {})
        provider = ov.get("model_provider", ag.get("model_provider", "gemini"))
        model    = ov.get("model",          ag.get("default_model",   "gemini-2.0-flash"))
        return ModelManager(model, provider=provider)

    async def filter_and_translate(
        self,
        site_name: str,
        articles: list[dict],   # [{title, url, content}, ...]
    ) -> list[dict]:
        if not articles:
            return []

        mm = self._get_mm()

        # ── Step 1: filter ─────────────────────────────────────────────────
        article_list = "\n".join(
            f"{i+1}. {a['title']}"
            for i, a in enumerate(articles)
        )
        filter_prompt = (
            f"You are a strict political news filter for an Indian civic platform.\n"
            f"From the articles below from '{site_name}', return ONLY the numbers of articles "
            f"that are about politics, government, elections, parliament, ministers, MLAs, MPs, "
            f"public policy, or governance.\n"
            f"EXCLUDE: cricket, IPL, sports, movies, actors, entertainment, lifestyle, fashion, "
            f"business, technology, health tips, astrology, crime (unless involves politicians).\n\n"
            f"Articles:\n{article_list}\n\n"
            f"Reply with ONLY a comma-separated list of numbers. Example: 2, 5, 11, 23\n"
            f"If none are political, reply: none"
        )

        raw_filter = await mm.generate_text(filter_prompt)
        print(f"[NewsFilterAgent] Filter response: {raw_filter.strip()}")

        indices = [int(x) for x in re.findall(r'\d+', raw_filter)]
        indices = [i for i in indices if 1 <= i <= len(articles)][:10]

        if not indices:
            print("[NewsFilterAgent] No political articles found.")
            return []

        selected = [{"index": i, **articles[i - 1]} for i in indices]

        # ── Step 2: translate titles ───────────────────────────────────────
        titles_list = "\n".join(
            f"{s['index']}. {s['title']}"
            for s in selected
        )
        translate_prompt = (
            f"Translate these news article titles to clear, fluent English.\n"
            f"If already in English keep it unchanged.\n"
            f"Reply in the SAME numbered format, one per line.\n\n"
            f"{titles_list}"
        )

        raw_translate = await mm.generate_text(translate_prompt)
        print(f"[NewsFilterAgent] Translate response: {raw_translate.strip()}")

        # Parse "N. English title" lines
        en_titles: dict[int, str] = {}
        for line in raw_translate.splitlines():
            m = re.match(r'\s*(\d+)[.)]\s*(.+)', line)
            if m:
                en_titles[int(m.group(1))] = m.group(2).strip()

        # ── Build result ───────────────────────────────────────────────────
        result = []
        for s in selected:
            result.append({
                "title":            en_titles.get(s["index"], s["title"]),
                "title_original":   s["title"],
                "url":              s["url"],
                "content":          s.get("content", ""),
                "content_original": s.get("content", ""),
            })

        return result
