"""Intent router: LLM-first, rule-based fallback."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import llm_client

BIM_QUERY_KW = [
    "door", "window", "wall", "beam", "column", "pile", "footing",
    "rebar", "reinforcing", "storey", "level", "how many", "count",
    "quantity", "number of",
]
NOUN_MAP = [
    (r"\bdoor(s)?\b", "IfcDoor", "arch"),
    (r"\bwindow(s)?\b", "IfcWindow", "arch"),
    (r"\bwall(s)?\b", "IfcWall", "arch"),
    (r"\bbeam(s)?\b", "IfcBeam", "str"),
    (r"\bcolumn(s)?\b", "IfcColumn", "str"),
    (r"\bpile(s)?\b", "IfcPile", "str"),
    (r"\bfooting(s)?\b", "IfcFooting", "str"),
    (r"\b(rebar|reinforcing bar)s?\b", "IfcReinforcingBar", "str"),
]

def rule_route(question: str):
    q = question.lower()
    if any(k in q for k in ["health", "missing", "anything wrong", "incomplete", "quality",
                             "bim problem", "data quality", "anything missing", "run health"]):
        return "bim_health", {}, "rules"
    if any(k in q for k in ["coordination", "compare", "consistent", "consistency",
                             "elevation", "architecture and structure", "architectural and structural",
                             "difference between", "levels consistent", "run coordination"]):
        return "coordination", {}, "rules"
    if any(k in q for k in ["room", "bedroom", "kitchen", "bath", "living", "hall",
                            "closet", "drawing", "plan", "sheet", "legend",
                            "which room", "rooms on", "upstairs", "second level"]):
        return "drawing_query", {}, "rules"
    for pat, ifc_type, model in NOUN_MAP:
        if re.search(pat, q):
            return "bim_query", {"ifc_type": ifc_type, "model": model}, "rules"
    return "unknown", {}, "rules"

def route(question: str):
    """Try LLM first; fall back to rules on any failure.
    Returns (intent, params, source_label) where source_label is 'llm' or 'rules'."""
    if llm_client.is_available():
        parsed = llm_client.classify_intent(question)
        if parsed:
            intent = parsed.pop("intent")
            llm_flag = parsed.pop("llm", True)
            # map LLM intent names
            intent_map = {
                "bim_query": "bim_query",
                "drawing_query": "drawing_query",
                "bim_health": "bim_health",
                "coordination_check": "coordination",
            }
            return intent_map.get(intent, "unknown"), parsed, "llm"
    intent, params, _ = rule_route(question)
    return intent, params, "rules"
