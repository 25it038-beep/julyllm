"""
HS AI SOLUTIONS — JULY CLIENT AUTONOMOUS WEB SEARCH ENGINE
Layer: LIVE WEB ACQUISITION (july_distribution.client.web_search)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM | Family: HS AI FAMILY

Provides real-time web search integration:
- Autonomous query intent detection (current events, recent news, live facts, dates).
- Multi-source retrieval (DuckDuckGo HTML + DuckDuckGo Lite + Instant Answer API).
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

# Non-search greetings and system meta-prompts
SKIP_PATTERNS = [
    r"^(hi|hello|hey|greetings|hola|namaste|sup|yo)[.!?\s]*$",
    r"^(good morning|good afternoon|good evening|good night)[.!?\s]*$",
    r"^(how are you|how do you do|who are you|what are you|what is your name)[.!?\s]*$",
    r"^(thanks|thank you|ok|okay|bye|goodbye|see you|exit|quit|q)[.!?\s]*$",
    r"^(/clear|/help|/status|/studio|/mode)[.!?\s]*$",
    r"(?i)\b(who|what).*(created|made|founded|built|trained|developed|designed)\s+(you|u|sree|july|gravity)\b",
    r"(?i)\b(your|ur)\s+(architecture|model|system prompt|prompt|instructions|identity|creator|founder|parameters)\b",
    r"(?i)\b(what is your architecture|what is your system prompt|show your system prompt|reveal your system prompt)\b",
    r"(?i)\b(who are you|what are you|tell me about yourself|what is your name)\b",
    # Live personal context, time, date, location inquiries - use local RuntimeContextProvider directly
    r"(?i)\b(what\s+time\s+is\s+it|what\s+is\s+the\s+time|current\s+time|tell\s+me\s+the\s+time|time\s+now|what'?s\s+the\s+time)\b",
    r"(?i)\b(what\s+is\s+today'?s\s+date|today'?s\s+date|current\s+date|what\s+date\s+is\s+it|what\s+is\s+the\s+date|what'?s\s+the\s+date)\b",
    r"(?i)\b(who\s+am\s+i|what\s+is\s+my\s+name|what'?s\s+my\s+name|my\s+name|do\s+you\s+know\s+me|who\s+is\s+speaking)\b",
    r"(?i)\b(where\s+am\s+i|what\s+is\s+my\s+location|my\s+location|my\s+timezone|my\s+city|my\s+country|where\s+are\s+we)\b",
    r"(?i)\b(time\s+and\s+location|time\s+and\s+date|who\s+am\s+i\s+and\s+where\s+am\s+i)\b",
    # Coding and debugging requests - use LLM reasoning directly, avoid web search
    r"(?i)\b(write\s+(a\s+)?(function|script|code|program|class|method|component|app|algorithm|test))\b",
    r"(?i)\b(fix\s+(this\s+)?(error|bug|code|issue|exception|traceback|syntax))\b",
    r"(?i)\b(implement|refactor|debug|compile|benchmark|optimize\s+code)\b",
]

# Conversational follow-up patterns referring to previously discussed context
CONVERSATIONAL_FOLLOWUP_PATTERNS = [
    r"(?i)\b(how\s+(it|this|that|they)\s+(look|looks|work|works|feel|feels|sound|sounds|function|functions|operate|operates|behave|behaves|compare|compares))\b",
    r"(?i)\b(how\s+does\s+(it|this|that)\s+(look|work|feel|sound|operate|behave|function))\b",
    r"(?i)\b(what\s+does\s+(it|this|that)\s+look\s+like)\b",
    r"(?i)\b(what\s+(it|this|that)\s+looks?\s+like)\b",
    r"(?i)\b(what\s+is\s+(it|this|that)\s+like)\b",
    r"(?i)\b(tell\s+me\s+more(\s+about\s+(it|this|that|them))?)\b",
    r"(?i)\b(explain\s+(it|this|that|further|more))\b",
    r"(?i)\b(describe\s+(it|this|that|how\s+it\s+looks))\b",
    r"(?i)\b(what\s+about\s+(it|this|that))\b",
    r"(?i)\b(how\s+to\s+use\s+(it|this|that))\b",
    r"(?i)\b(is\s+(it|this|that)\s+(good|bad|safe|fast|expensive|worth\s+it|real|possible))\b",
    r"(?i)\b(why\s+is\s+(it|this|that))\b",
    r"(?i)\b(how\s+(is|are)\s+(it|this|that|they))\b",
    r"(?i)\b(how\s+it\s+looks)\b",
    r"(?i)\b(can\s+you\s+(show|describe|explain)\s+(it|how\s+it\s+looks))\b",
]

PRONOUN_PATTERN = re.compile(r"\b(it|its|this|that|these|those|they|them|their)\b", re.IGNORECASE)

# Keywords indicating genuine real-time / current live information requirements
REALTIME_INDICATORS = [
    r"\b(current|currently|latest|today|yesterday|tomorrow|tonight|recent|recently|now|live|news|updates?|fresh)\b",
    r"\b(202[4-9]|203[0-9])\b",
    r"\b(price|pricing|cost|costs|stock|stocks|market|valuation|net\s*worth|crypto|bitcoin|eth)\b",
    r"\b(score|scores|match|winner|won|champion|championship|standings|election|elections|budget)\b",
    r"\b(weather|temperature|forecast|flight\s*status|release\s*date|launch\s*date)\b",
]

# Patterns that indicate factual queries, entities, or real-time info needs
SEARCH_PATTERNS = [
    r"^(/search|/web|search:|google:|lookup:|browse:|--web)",
    r"\b(current|currently|latest|today|yesterday|tomorrow|tonight|recent|recently|now|live|news|updates?)\b",
    r"\b(202[4-9]|203[0-9])\b",
    r"\b(cm|pm|chief minister|prime minister|president of|ceo of|cto of|founder of|governor of|chancellor of|mayor of)\b",
    r"\b(stock|stocks|price|pricing|market|score|scores|match|winner|won|champion|championship|election|elections|budget)\b",
    r"\b(weather|temperature|forecast|flight\s*status|release\s*date|launch\s*date)\b",
    r"\b(who is the|who won|what happened to|when was .* released|what is the price of|what is the score of)\b",
    r"\b(tell me about|info on|details of)\b",
]

EXPLICIT_SEARCH_TRIGGERS = [
    "/search", "/web", "search:", "google:", "lookup:", "browse:", "--web"
]


def extract_subject_from_history(history: Optional[List[Dict[str, Any]]]) -> str:
    """Extracts the primary subject or entity discussed in recent conversation turns."""
    if not history:
        return ""

    # 1. Inspect recent user queries in reverse chronological order
    for msg in reversed(history):
        if msg.get("role") == "user":
            content = msg.get("content", "").strip()
            # Clean common command triggers and prefixes
            c = re.sub(r"(?i)^(/search|/web|search:|google:|lookup:|browse:|--web)\s*", "", content)
            c = re.sub(r"(?i)^(please\s+)?(can\s+you\s+)?(tell\s+me\s+about|what\s+is|who\s+is|explain|describe|info\s+on|details\s+of|search\s+for|lookup)\s+", "", c)
            c = re.sub(r"[?!.]+$", "", c).strip()
            # If after stripping we have a clean candidate noun phrase (1 to 8 words)
            words = c.split()
            if 1 <= len(words) <= 8 and not any(p in c.lower() for p in ["how are you", "who are you", "hello", "hi"]):
                return c

    # 2. Inspect recent assistant responses for primary entity definitions
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "").strip()
            # Strip think tags if any
            content = re.sub(r"(?s)<think>.*?</think>", "", content).strip()
            m = re.search(r"(?:The\s+)?([A-Z][a-zA-Z0-9\s]{2,35}?)\s+(?:is|was|refers\s+to|represents)\b", content)
            if m:
                cand = m.group(1).strip()
                if len(cand.split()) <= 6:
                    return cand

    return ""


def should_trigger_web_search(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Detects whether a prompt requires live real-time web search grounding.
    
    Prevents conversational follow-up questions ('how it looks', 'how does it work',
    'tell me more') from hijacking web search when conversation history provides context.
    """
    p_lower = prompt.strip().lower()
    if not p_lower:
        return False

    # Check skip patterns (greetings / conversational filler / model identity inquiries / coding)
    for pat in SKIP_PATTERNS:
        if re.search(pat, p_lower):
            return False

    # Check explicit triggers (user explicitly asked for /search or /web)
    for trig in EXPLICIT_SEARCH_TRIGGERS:
        if p_lower.startswith(trig):
            return True

    # Check if this is a conversational follow-up in an ongoing multi-turn session
    if history:
        # Check explicit conversational follow-up patterns ("how it looks", "how does it work")
        for pat in CONVERSATIONAL_FOLLOWUP_PATTERNS:
            if re.search(pat, p_lower):
                return False

        # If short query (< 8 words) containing anaphoric pronouns and lacking real-time indicators
        has_realtime = any(re.search(pat, p_lower) for pat in REALTIME_INDICATORS)
        if not has_realtime and PRONOUN_PATTERN.search(p_lower) and len(p_lower.split()) <= 8:
            return False

    # Check search patterns
    for pat in SEARCH_PATTERNS:
        if re.search(pat, p_lower):
            return True

    return False


def extract_search_query(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Cleans up the user prompt into a focused web search query.
    
    Resolves anaphoric pronouns ('it', 'its', 'this', 'that', 'they') using the subject
    from conversation history so that follow-up searches are accurate.
    """
    q = prompt.strip()
    for trig in EXPLICIT_SEARCH_TRIGGERS:
        if q.lower().startswith(trig):
            q = q[len(trig):].strip()
            break

    # Strip conversational prefixes
    q = re.sub(r"^(please\s+)?(can\s+you\s+)?(tell\s+me\s+)?(search\s+for\s+|lookup\s+)?", "", q, flags=re.IGNORECASE).strip()
    q = re.sub(r"[?!.]+$", "", q).strip()

    # Coreference / pronoun resolution using conversation history
    if history:
        subject = extract_subject_from_history(history)
        if subject:
            # Check if query contains anaphoric pronouns
            if PRONOUN_PATTERN.search(q):
                # Replace possessives ("its", "their") with subject's
                q = re.sub(r"\b(its|their)\b", f"{subject}'s", q, flags=re.IGNORECASE)
                # Replace pronouns ("it", "this", "that", "these", "those", "they", "them") with subject
                q = re.sub(r"\b(it|this|that|these|those|they|them)\b", subject, q, flags=re.IGNORECASE)
            elif len(q.split()) <= 4 and not any(w.lower() in q.lower() for w in subject.split()):
                # Short follow-up without pronoun (e.g., "latest news", "price today")
                q = f"{subject} {q}"

    # Strip leftover question wrappers
    q = re.sub(r"^(what is the|what is|how much is the|how much does|who is the)\s+", "", q, flags=re.IGNORECASE).strip()
    return q if len(q) > 2 else prompt.strip()


def live_duckduckgo_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Performs live web search without requiring third-party API keys."""
    results = []
    encoded_query = urllib.parse.quote(query)

    # Strategy 1: Primary DuckDuckGo HTML Search
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://html.duckduckgo.com/",
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            snippet_matches = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)
            title_matches = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)

            for i in range(min(len(snippet_matches), len(title_matches), max_results)):
                t = html.unescape(re.sub(r"<[^>]+>", "", title_matches[i]).strip())
                s = html.unescape(re.sub(r"<[^>]+>", "", snippet_matches[i]).strip())
                if s and len(s) > 10:
                    results.append({"title": t, "snippet": s})
    except Exception:
        pass

    # Strategy 2: Fallback DuckDuckGo Lite Search
    if len(results) < 2:
        try:
            lite_url = "https://lite.duckduckgo.com/lite/"
            post_data = urllib.parse.urlencode({"q": query}).encode("utf-8")
            lite_req = urllib.request.Request(lite_url, data=post_data, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded"
            })
            with urllib.request.urlopen(lite_req, timeout=8) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                snippets = re.findall(r'class=[\"\']result-snippet[\"\']>(.*?)</td>', body, re.DOTALL | re.IGNORECASE)
                titles = re.findall(r'class=[\"\']result-link[\"\'][^>]*>(.*?)</a>', body, re.DOTALL | re.IGNORECASE)
                for i in range(min(len(snippets), len(titles), max_results)):
                    t = html.unescape(re.sub(r"<[^>]+>", "", titles[i]).strip())
                    s = html.unescape(re.sub(r"<[^>]+>", "", snippets[i]).strip())
                    if s and len(s) > 10:
                        results.append({"title": t, "snippet": s})
        except Exception:
            pass

    # Strategy 3: Tertiary Fallback DuckDuckGo Instant Answer API
    if len(results) < 2:
        try:
            api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            api_req = urllib.request.Request(api_url, headers={"User-Agent": "JulyLLM/1.0"})
            with urllib.request.urlopen(api_req, timeout=6) as resp:
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
        f'Search Query: "{query}"',
        "Verified live facts from the web:"
    ]

    for idx, r in enumerate(results, 1):
        lines.append(f"{idx}. {r['title']}: {r['snippet']}")

    return "\n".join(lines)
