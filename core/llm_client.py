"""LLM client with true OpenAI function-calling agent loop.
LLM = brain (language understanding + tool selection).
Tools = engineering ground truth (IfcOpenShell / PyMuPDF).
"""
import os, json, re, time as _time
from typing import Optional, Dict, List
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

def _secret(key, default=""):
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()

_QWEN_KEY = _secret("QWEN_API_KEY")
_QWEN_URL = _secret("QWEN_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
_QWEN_MODEL = _secret("QWEN_MODEL") or "qwen3.7-flash"

_OR_KEY = _secret("OPENROUTER_API_KEY")
_OR_URL = _secret("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
_OR_MODEL = _secret("OPENROUTER_MODEL") or "openai/gpt-oss-20b:free"

if _QWEN_KEY:
    API_KEY, BASE_URL, MODEL = _QWEN_KEY, _QWEN_URL, _QWEN_MODEL
    PROVIDER = "Qwen / Alibaba Cloud Model Studio"
elif _OR_KEY:
    API_KEY, BASE_URL, MODEL = _OR_KEY, _OR_URL, _OR_MODEL
    PROVIDER = "OpenRouter"
else:
    API_KEY, BASE_URL, MODEL = "", _QWEN_URL, _QWEN_MODEL
    PROVIDER = "Qwen / Alibaba Cloud Model Studio"

_client = None
_last_error = None
_ping_ok = None

def _get_client():
    global _client
    if _client is not None or not API_KEY:
        return _client
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=15.0)
    except Exception as e:
        global _last_error
        _last_error = f"client_init:{type(e).__name__}:{e}"
        _client = None
    return _client

def _ping():
    global _ping_ok, _last_error
    if _ping_ok is not None:
        return _ping_ok
    c = _get_client()
    if c is None:
        _ping_ok = False; return False
    try:
        c.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":"Reply with exactly: OK"}],
            max_tokens=5, temperature=0.0)
        _ping_ok = True
    except Exception as e:
        _ping_ok = False
        code = getattr(e,"status_code",None) or getattr(e,"code",None)
        _last_error = f"ping:HTTP{code}:{type(e).__name__}:{str(e)[:200]}"
    return _ping_ok

def is_available():
    return bool(API_KEY) and _ping()

def engine_status():
    if is_available():
        return {"state":"online","platform":PROVIDER,"model":MODEL,"error":""}
    return {"state":"offline","platform":PROVIDER,"model":MODEL,"error":_last_error or "no key"}

# ---------- Tool schemas (OpenAI function calling format) ----------
TOOL_SCHEMAS = [
    {
        "type":"function",
        "function":{
            "name":"query_ifc_entities",
            "description":"Query an IFC BIM model. Use operation=count to count entities, operation=types to list distinct type names.",
            "parameters":{"type":"object","properties":{
                "discipline":{"type":"string","enum":["architecture","structure"]},
                "entity_type":{"type":"string","description":"e.g. IfcDoor, IfcWindow, IfcBeam, IfcColumn, IfcPile, IfcSlab, IfcStair, IfcRailing, IfcSpace, IfcBuildingStorey, IfcReinforcingBar, IfcFooting, IfcRoof, IfcCurtainWall"},
                "operation":{"type":"string","enum":["count","types"]}
            },"required":["discipline","entity_type","operation"]}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"search_drawing",
            "description":"Search PDF construction drawings for a query term. Returns matching sheets/pages with snippets.",
            "parameters":{"type":"object","properties":{
                "discipline":{"type":"string","enum":["architecture","structure"]},
                "query":{"type":"string"}
            },"required":["discipline","query"]}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"extract_rooms",
            "description":"Extract room names from a floor plan drawing for a given level. Use when IFC has no IfcSpace.",
            "parameters":{"type":"object","properties":{
                "discipline":{"type":"string","enum":["architecture","structure"]},
                "level":{"type":"string","description":"e.g. Level 1, Level 2, upstairs, downstairs"}
            },"required":["discipline"]}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"bim_health_check",
            "description":"Check BIM data quality: presence of key entities like IfcSpace, IfcDoor, IfcBeam, etc.",
            "parameters":{"type":"object","properties":{
                "discipline":{"type":"string","enum":["architecture","structure","both"]}
            },"required":["discipline"]}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"coordination_check",
            "description":"Compare architectural and structural elevations/levels from IFC storeys.",
            "parameters":{"type":"object","properties":{}}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"project_summary",
            "description":"Get a dynamic summary of all available BIM entity counts in both disciplines.",
            "parameters":{"type":"object","properties":{}}
        }
    },
]

# ---------- Tool dispatcher ----------
def _dispatch(name, args):
    from core import tools
    try:
        if name == "query_ifc_entities":
            return tools.tool_query_ifc_entities(**args)
        elif name == "search_drawing":
            return tools.tool_search_drawing(**args)
        elif name == "extract_rooms":
            return tools.tool_extract_rooms(**args)
        elif name == "bim_health_check":
            return tools.tool_health(**args)
        elif name == "coordination_check":
            return tools.tool_coordination()
        elif name == "project_summary":
            return tools.tool_summary()
        return {"success": False, "reason": f"unknown tool {name}"}
    except Exception as e:
        return {"success": False, "reason": f"tool_error:{type(e).__name__}:{e}"}

SYSTEM_PROMPT = """You are TrustBIM Agent, an engineering-data assistant for BIM and construction drawings.

You MUST answer project-specific engineering questions ONLY by calling the provided tools.
Rules:
1. Never invent project-specific engineering facts (counts, materials, elevations, room names).
2. Use tools for quantities, types, materials, levels, rooms, drawings and model info.
3. Prefer structured IFC when it directly answers the question.
4. If IFC evidence is missing (e.g. IfcSpace = 0), consider drawing tools.
5. You may call multiple tools across steps when necessary.
6. Base the final answer ONLY on tool observations.
7. Clearly state when evidence is insufficient.
8. Do NOT turn a potential coordination issue into a confirmed design error. Say "manual review recommended".
9. Do NOT use general world knowledge to invent BIM/project values.
10. Include source and evidence when possible.
Answer in 1-3 short sentences, English."""

MAX_STEPS = 4
_RETRYABLE = {429, 500, 502, 503, 504}

def agent_run(question: str):
    """Run the Qwen function-calling loop.
    Returns (result_dict, trace_list, error_str).
    result_dict has answer/source/evidence/method."""
    c = _get_client()
    if c is None:
        return None, ["Question received", "No LLM client"], "no_client"
    messages = [
        {"role":"system","content":SYSTEM_PROMPT},
        {"role":"user","content":question},
    ]
    trace = ["Question received"]
    tool_results = []
    for step in range(MAX_STEPS):
        try:
            resp = c.chat.completions.create(
                model=MODEL, messages=messages,
                tools=TOOL_SCHEMAS, tool_choice="auto",
                temperature=0.0, max_tokens=400,
            )
        except Exception as e:
            code = getattr(e,"status_code",None) or getattr(e,"code",None)
            if code in (401,403):
                return None, trace, f"auth_error:{code}"
            # retry once
            _time.sleep(1.0)
            try:
                resp = c.chat.completions.create(
                    model=MODEL, messages=messages,
                    tools=TOOL_SCHEMAS, tool_choice="auto",
                    temperature=0.0, max_tokens=400)
            except Exception as e2:
                return None, trace, f"api_error:{type(e2).__name__}:{str(e2)[:150]}"
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            final = (msg.content or "").strip()
            trace.append("Qwen final answer generated")
            # determine source/evidence from last tool result
            src = tool_results[-1].get("source","") if tool_results else ""
            ev = tool_results[-1].get("evidence","") if tool_results else ""
            method = "Qwen function-calling agent"
            return {"answer": final, "source": src, "evidence": ev, "method": method}, trace, None
        # process tool calls
        messages.append(msg)
        for tc in msg.tool_calls:
            fname = tc.function.name
            try:
                fargs = json.loads(tc.function.arguments or "{}")
            except Exception:
                fargs = {}
            trace.append(f"Qwen requested tool: {fname} args={json.dumps(fargs, ensure_ascii=False)}")
            result = _dispatch(fname, fargs)
            tool_results.append(result)
            trace.append(f"Tool result: {json.dumps(result, ensure_ascii=False)[:200]}")
            messages.append({
                "role":"tool",
                "tool_call_id": tc.id,
                "name": fname,
                "content": json.dumps(result, ensure_ascii=False),
            })
    return None, trace, "max_steps_exceeded"
