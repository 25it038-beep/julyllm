"""
HS AI SOLUTIONS â€” JULY CLIENT AUTONOMOUS WEB SEARCH ENGINE
Layer: LIVE WEB ACQUISITION (july_distribution.client.web_search)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Provides real-time web search integration:
- Autonomous query intent detection (current events, recent news, live facts, dates).
- Live multi-source retrieval (DuckDuckGo HTML + Instant Answer API).
- Zero external API key dependencies.
- Structured contextual synthesis for LLM prompt grounding.
"""

from __future__ import annotations
import re
import html
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Keywords and regex patterns that indicate real-time / current information needs
TEMPORAL_PATTERNS = [
    r"\b(current|currently|latest|today|yesterday|tomorrow|tonight|recent|recently|now)\b",
    r"\b(news|weather|stock|price|score|scores|election|elections|update|updates|schedule)\b",
    r"\b(2024|2025|2026|2027)\b",
    r"\bwho is (the )?(current|new|now|president|prime minister|ceo|leader|champion)\b",
    r"\bwhat is the (current|latest|present|newest|price of|score of|status of)\b",
    r"\b(who won|what happened|when is the next|is it currently)\b"
]

EXPLICIT_SEARCH_TRIGGERS = [
    "/search", "/web", "search:", "google:", "lookup:", "browse:", "--web"
]


def should_trigger_web_search(prompt: str) -> bool:
    """Detects whether a prompt requires live real-time web search grounding."""
    p_lower = prompt.strip().lower()

    # Explicit triggers
    for trig in EXPLICIT_SEARCH_TRIGGERS:
        if p_lower.startswith(trig):
            return True

    # Pattern based triggers
    for pat in TEMPORAL_PATTERNS:
        if re.search(pat, p_lower):
            return True

    return False


def extract_search_query(prompt: str) -> str:
    """Cleans up the user prompt into a focused web search query."""
    q = prompt.strip()
    for trig in EXPLICIT_SEARCH_TRIGGERS:
        if q.lower().startswith(trig):
            q = q[len(trig):].strip()
            break

    # Strip conversational noise
    q = re.sub(r"^(please\s+)?(can\s+you\s+)?(tell\s+me\s+)?(what\s+is\s+|who\s+is\s+|search\s+for\s+)?", "", q, flags=re.IGNORECASE)
    q = re.sub(r"[?!.]+$", "", q).strip()
    return q if len(q) > 2 else prompt.strip()


def live_duckduckgo_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Performs live web search without requiring third-party API keys."""
    results = []
    encoded_query = urllib.parse.quote(query)

    # 1. Primary: DuckDuckGo HTML Search
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            snippet_matches = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)
            title_matches = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)

            for i in range(min(len(snippet_matches), len(title_matches), max_results)):
                t = html.unescape(re.sub(r"<[^>]+>", "", title_matches[i]).strip())
                s = html.unescape(re.sub(r"<[^>]+>", "", snippet_matches[i]).strip())
                if s:
                    results.append({"title": t, "snippet": s})
    except Exception:
        pass

    # 2. Secondary Fallback: DuckDuckGo Instant Answer API
    if len(results) < 2:
        try:
            api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            api_req = urllib.request.Request(api_url, headers={"User-Agent": "JulyLLM/1.0"})
            with urllib.request.urlopen(api_req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText")
                heading = data.get("Heading")
                if abstract and heading:
                    results.insert(0, {"title": heading, "snippet": abstract})
                for topic in data.get("RelatedTopics", []):
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({"title": "Related Fact", "snippet": topic["Text"]})
                        if len(results) >= max_results:
                            break
        except Exception:
            pass

    return results[:max_results]


def format_search_context(query: str, results: List[Dict[str, str]]) -> str:
    """Formats retrieved live web snippets for LLM context grounding."""
    if not results:
        return ""

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"[REAL-TIME LIVE WEB SEARCH DATA - Retrieved: {current_date}]",
        f'Query: "{query}"',
        "Use the following real-time facts to answer the user accurately:"
    ]

    for idx, r in enumerate(results, 1):
        lines.append(f"{idx}. {r['title']}: {r['snippet']}")

    return "\n".join(lines)

