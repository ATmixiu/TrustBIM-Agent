"""OpenAI-compatible LLM client for OpenRouter.
LLM only does intent understanding and answer polishing.
It NEVER computes BIM numbers itself.
All failures (missing key, network, timeout, 429) return None -> caller falls back to rules.
"""
import os, json, re
from typing import Optional, Dict
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

def _secret(key, default=""):
    # 1) Streamlit Cloud Secrets  2) .env / env var
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()

API_KEY = _secret("OPENROUTER_API_KEY")
BASE_URL = _secret("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
MODEL = _secret("OPENROUTER_MODEL") or "openrouter/free"

_client = None

def _get_client():
    global _client
    if _client is not None or not API_KEY:
        return _client
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=20.0)
    except Exception:
        _client = None
    return _client

def is_available() -> bool:
    return bool(API_KEY) and _get_client() is not None

def engine_status() -> Dict[str, str]:
    if is_available():
        return {"state": "online", "platform": "OpenRouter", "model": MODEL}
    return {"state": "offline", "platform": "OpenRouter", "model": MODEL or "openrouter/free"}

# ---------- Intent classification ----------
INTENT_SYS = """You are an intent classifier for a BIM agent.
Output STRICT JSON only, no prose. Map the user question to one of:
- bim_query: a count/quantity of BIM entities (door, window, wall, beam, column, pile, footing, rebar, storey).
- drawing_query: a room / drawing / sheet / plan question.
- bim_health: ask what is missing, wrong, or healthy about the BIM.
- coordination_check: compare architecture vs structure, elevations, alignment.
Return JSON:
{"intent":"...", "discipline":"architecture|structural|mixed", "entity":"door|window|...", "topic":"rooms|...", "level":"Level 2|..."}
Only include relevant fields."""

_ENTITY_MAP = {
    "door": "IfcDoor", "doors": "IfcDoor",
    "window": "IfcWindow", "windows": "IfcWindow",
    "wall": "IfcWall", "walls": "IfcWall",
    "beam": "IfcBeam", "beams": "IfcBeam",
    "column": "IfcColumn", "columns": "IfcColumn",
    "pile": "IfcPile", "piles": "IfcPile",
    "footing": "IfcFooting", "footings": "IfcFooting",
    "rebar": "IfcReinforcingBar", "reinforcing bar": "IfcReinforcingBar",
    "storey": "IfcBuildingStorey", "level": "IfcBuildingStorey",
}
_DISCIPLINE_MODEL = {"architecture": "arch", "architectural": "arch", "structural": "str", "structure": "str"}

def classify_intent(question: str) -> Optional[Dict]:
    """Return normalized tool request dict, or None on failure."""
    c = _get_client()
    if c is None:
        return None
    try:
        r = c.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYS},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        raw = r.choices[0].message.content or ""
        # extract JSON
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        data = json.loads(m.group(0))
        intent = data.get("intent")
        if intent not in ("bim_query", "drawing_query", "bim_health", "coordination_check"):
            return None
        out = {"intent": intent, "llm": True}
        if intent == "bim_query":
            ent = (data.get("entity") or "").lower()
            ifc_type = _ENTITY_MAP.get(ent)
            if not ifc_type:
                return None
            disc = (data.get("discipline") or "").lower()
            model_key = _DISCIPLINE_MODEL.get(disc, "arch")
            # structural-only entities force str
            if ifc_type in ("IfcBeam","IfcColumn","IfcPile","IfcFooting","IfcReinforcingBar"):
                model_key = "str"
            out.update({"ifc_type": ifc_type, "model": model_key})
        elif intent == "drawing_query":
            out["level"] = data.get("level") or "Level 2"
        return out
    except Exception:
        return None

# ---------- Answer polishing ----------
POLISH_SYS = """You rewrite engineering answers from a BIM agent.
RULES:
1. Use ONLY the tool-provided data. Never change numbers.
2. If data says count=16, you MUST say 16.
3. Keep it short (1-2 sentences).
4. Do NOT call a REVIEW a "design error". Say "manual review recommended".
5. Do NOT mention internal tool names, model names, or JSON.
Output the final user-facing sentence only."""

def polish_answer(question: str, tool_payload: Dict) -> Optional[str]:
    c = _get_client()
    if c is None:
        return None
    try:
        user_msg = f"User question: {question}\nTool data: {json.dumps(tool_payload, ensure_ascii=False)}"
        r = c.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": POLISH_SYS},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        txt = (r.choices[0].message.content or "").strip()
        return txt if len(txt) > 5 else None
    except Exception:
        return None
