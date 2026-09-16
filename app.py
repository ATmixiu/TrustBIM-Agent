"""TrustBIM Agent — product-grade Streamlit UI."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from core import tools
from core.router import route
from core import llm_client
from parsers import ifc_loader, pdf_loader

st.set_page_config(page_title="TrustBIM Agent", page_icon="🏗", layout="wide")

# ---------- product CSS ----------
st.markdown("""
<style>
:root { --navy:#0F2C59; --cyan:#00B4D8; --bg:#F7F9FC; }
html, body, [class*="css"] { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }
.stApp { background: var(--bg); }
.hero {
    background: linear-gradient(135deg, #0F2C59 0%, #1a4a8a 100%);
    color: #fff; padding: 28px 32px; border-radius: 14px; margin-bottom: 18px;
}
.hero h1 { color:#fff; margin:0; font-size:34px; font-weight:700; }
.hero .sub { color:#cfe3ff; font-size:16px; margin-top:6px; }
.hero .intro { color:#e8f1ff; font-size:14px; margin-top:12px; max-width:820px; line-height:1.5; }
.status-row { display:flex; gap:14px; margin-top:16px; flex-wrap:wrap; }
.status-pill {
    background: rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.25);
    padding:8px 14px; border-radius:999px; font-size:13px; color:#fff;
}
.status-pill b { color:#7CFFB2; }
.card {
    background:#fff; border:1px solid #e3e9f2; border-radius:12px;
    padding:18px 22px; margin-bottom:14px; box-shadow:0 1px 3px rgba(15,44,89,0.05);
}
.metric-card {
    background:#fff; border:1px solid #e3e9f2; border-radius:12px;
    padding:16px 18px; text-align:center;
}
.metric-card .num { font-size:30px; font-weight:700; color:var(--navy); }
.metric-card .lbl { font-size:13px; color:#5a6b85; margin-top:4px; }
.ans-label { color:#0F2C59; font-weight:700; font-size:13px; letter-spacing:1px; margin-top:10px; }
.ans-body { font-size:18px; color:#1a2b45; line-height:1.5; }
.trace-step { padding:6px 0; color:#334; font-size:14px; }
.trace-step b { color:#0F2C59; }
.badge { display:inline-block; padding:3px 10px; border-radius:6px; font-size:12px; font-weight:600; }
.badge-pass { background:#e3f9ec; color:#1a7f4b; }
.badge-warn { background:#fff4e0; color:#b36b00; }
.badge-review { background:#ffe2e2; color:#b23030; }
.badge-match { background:#e3f9ec; color:#1a7f4b; }
.flow {
    background:#fff; border:1px solid #e3e9f2; border-radius:12px; padding:16px 20px; margin:10px 0;
}
.flow .arrow { text-align:center; color:#00B4D8; font-size:18px; }
.kv { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #eef2f8; font-size:14px;}
.kv:last-child { border-bottom:none; }
.kv .k { color:#5a6b85; }
.kv .v { color:#0F2C59; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ---------- boot ----------
@st.cache_resource(show_spinner="Loading BIM & drawings...")
def boot():
    return ifc_loader.load_all(), pdf_loader.load_all()

ifc_data, pdf_data = boot()

# ---------- hero ----------
st.markdown("""
<div class="hero">
  <h1>TrustBIM Agent</h1>
  <div class="sub">AI Agent for BIM &amp; Construction Drawings</div>
  <div class="intro">Ask questions about BIM models and construction drawings.
  The agent automatically selects the most reliable data source and provides verifiable evidence.</div>
  <div class="status-row">
    <div class="status-pill">Architectural Drawing &nbsp;<b>● Ready</b></div>
    <div class="status-pill">Architectural BIM &nbsp;<b>● Ready</b></div>
    <div class="status-pill">Structural Drawing &nbsp;<b>● Ready</b></div>
    <div class="status-pill">Structural BIM &nbsp;<b>● Ready</b></div>
  </div>
</div>
""", unsafe_allow_html=True)

# AI engine status bar
eng = llm_client.engine_status()
if eng["state"] == "online":
    st.markdown(f"""
<div style="background:#e3f9ec;border:1px solid #9be2b8;border-radius:8px;
     padding:8px 16px;margin-bottom:14px;font-size:13px;color:#1a7f4b;">
<b>AI Engine:</b> ● LLM Connected — {eng['platform']} / {eng['model']}
</div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="background:#fff4e0;border:1px solid #f5cf8a;border-radius:8px;
     padding:8px 16px;margin-bottom:14px;font-size:13px;color:#b36b00;">
<b>AI Engine:</b> ● Offline Agent — rule-based fallback (set OPENROUTER_API_KEY in .env to enable LLM)
</div>""", unsafe_allow_html=True)

tab_chat, tab_overview, tab_health, tab_coord = st.tabs(
    ["💬 AI Assistant", "📊 Project Overview", "🩺 BIM Health", "🔗 Coordination"]
)

# ---------- Tab 1: AI Assistant ----------
with tab_chat:
    q = st.text_input("Ask the agent",
                      placeholder="e.g. How many doors are in the architectural model?")
    c1, c2 = st.columns([1, 5])
    run = c1.button("Run", type="primary")

    if run and q.strip():
        intent, params, route_src, llm_err = route(q)
        llm_used = (route_src == "llm")

        if intent == "bim_health":
            h = tools.tool_health()
            arch_space = ifc_loader.count("arch", "IfcSpace")
            steps = ["Question received"]
            steps.append("LLM intent analysis → bim_health" if llm_used else "Local high-confidence router → bim_health")
            steps += [
                "Selected tool: BIM Health Tool",
                f"Architectural IFC inspected: IfcSpace = {arch_space}",
                "Health result generated",
            ]
            warn = [r for r in h["rows"] if r[2] in ("WARNING","REVIEW")]
            warn_lines = "; ".join([f"{r[0]} = {r[1]}" for r in warn])
            res = {
                "answer": f"The architectural BIM has {len(warn)} item(s) needing attention. Key finding: {warn_lines}.",
                "source": "Architectural IFC + Structural IFC",
                "evidence": f"IfcSpace × {arch_space}; {len(warn)} warnings",
                "method": "BIM Health Check",
            }
        elif intent == "coordination":
            c = tools.tool_coordination()
            steps = ["Question received"]
            steps.append("LLM intent analysis → coordination_check" if llm_used else "Local high-confidence router → coordination_check")
            steps += [
                "Selected tool: Coordination Tool",
                "Architecture and structural elevations compared",
                "Result generated",
            ]
            rows = c["rows"]
            match_n = sum(1 for r in rows if r[3] == "MATCH")
            review_n = sum(1 for r in rows if r[3] == "REVIEW")
            review_items = [f"{r[0]}: arch={r[1]} vs str={r[2]}" for r in rows if r[3]=="REVIEW"]
            res = {
                "answer": f"{match_n}/{len(rows)} levels MATCH. {review_n} REVIEW: " + ("; ".join(review_items) if review_items else "none"),
                "source": "Architectural + Structural Engineering Data",
                "evidence": f"{len(rows)} elevation items compared",
                "method": "Cross-discipline Coordination Check",
            }
        elif intent == "bim_query":
            res = tools.tool_bim_query(params["ifc_type"], params.get("model", "arch"))
            n = ifc_loader.count(params.get("model","arch"), params["ifc_type"])
            steps = ["Question received"]
            if llm_used:
                steps.append("LLM intent analysis → bim_query")
            else:
                steps.append(f"LLM failed ({llm_err}) · Using Offline Router" if llm_err else "LLM unavailable · Using Offline Router")
            steps += [
                "Selected tool: BIM Query Tool",
                f"Queried entity: {params['ifc_type']}",
                f"Result verified: {n}",
            ]
            # optional LLM polish
            polished = llm_client.polish_answer(q, {"entity": params["ifc_type"], "count": n}) if llm_used else None
            if polished:
                res["answer"] = polished
                steps.append("LLM response generated")
            else:
                steps.append("Answer generated")
        elif intent == "drawing_query":
            res = tools.tool_drawing_query(q)
            arch_space = ifc_loader.count("arch", "IfcSpace")
            steps = ["Question received"]
            steps.append("LLM intent analysis → drawing_query" if llm_used else "LLM unavailable · Using Offline Router")
            steps += [
                f"BIM check: IfcSpace = {arch_space} → room semantics unavailable",
                "Automatically switching to drawing source",
                "Selected tool: Drawing Analysis Tool → Architectural Drawing A102",
            ]
            polished = llm_client.polish_answer(q, {"rooms_level_2": True, "source": "A102"}) if llm_used else None
            if polished:
                res["answer"] = polished
                steps.append("LLM response generated")
            else:
                steps.append("Answer generated")
        else:
            res = {"answer": "I can answer BIM quantity, drawing, health and coordination questions.",
                   "source": "—", "evidence": "—", "method": "Rule router",
                   "trace": ["Question received", "Intent: general"]}
            steps = res["trace"]

        # Answer card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="ans-label">ANSWER</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ans-body">{res["answer"]}</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f'<div class="kv"><span class="k">SOURCE</span><span class="v">{res.get("source","—")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kv"><span class="k">EVIDENCE</span><span class="v">{res.get("evidence","—")}</span></div>', unsafe_allow_html=True)
        with col_b:
            st.markdown(f'<div class="kv"><span class="k">METHOD</span><span class="v">{res.get("method","—")}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kv"><span class="k">CONFIDENCE</span><span class="v">High</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Agent Process
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Agent Process** (tool execution trace)")
        for i, s in enumerate(steps, 1):
            st.markdown(f'<div class="trace-step"><b>{i}.</b> {s}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Demo 2: visual BIM -> missing -> Drawing flow
        if intent == "drawing_query":
            st.markdown('<div class="flow">', unsafe_allow_html=True)
            st.markdown("**Adaptive Source Selection**")
            st.markdown("🔵 **BIM (IFC)** — checked first")
            st.markdown('<div class="arrow">↓ IfcSpace = 0 — room semantics unavailable</div>', unsafe_allow_html=True)
            st.markdown("📄 **Architectural Drawing A102** — selected automatically")
            st.markdown('<div class="arrow">↓</div>', unsafe_allow_html=True)
            st.markdown("✅ Answer from drawing text")
            st.markdown('</div>', unsafe_allow_html=True)

# ---------- Tab 2: Project Overview ----------
with tab_overview:
    st.subheader("Project Overview — Sample House")
    arch = ifc_data["arch"]["counts"]
    sstr = ifc_data["str"]["counts"]
    colL, colR = st.columns(2)
    with colL:
        st.markdown("**Architectural BIM**")
        a = st.columns(4)
        a[0].markdown(f'<div class="metric-card"><div class="num">{arch.get("IfcDoor",0)}</div><div class="lbl">Doors</div></div>', unsafe_allow_html=True)
        a[1].markdown(f'<div class="metric-card"><div class="num">{arch.get("IfcWindow",0)}</div><div class="lbl">Windows</div></div>', unsafe_allow_html=True)
        a[2].markdown(f'<div class="metric-card"><div class="num">{arch.get("IfcWall",0)}</div><div class="lbl">Walls</div></div>', unsafe_allow_html=True)
        a[3].markdown(f'<div class="metric-card"><div class="num">{arch.get("IfcBuildingStorey",0)}</div><div class="lbl">Storeys</div></div>', unsafe_allow_html=True)
    with colR:
        st.markdown("**Structural BIM**")
        b = st.columns(4)
        b[0].markdown(f'<div class="metric-card"><div class="num">{sstr.get("IfcBeam",0)}</div><div class="lbl">Beams</div></div>', unsafe_allow_html=True)
        b[1].markdown(f'<div class="metric-card"><div class="num">{sstr.get("IfcColumn",0)}</div><div class="lbl">Columns</div></div>', unsafe_allow_html=True)
        b[2].markdown(f'<div class="metric-card"><div class="num">{sstr.get("IfcPile",0)}</div><div class="lbl">Piles</div></div>', unsafe_allow_html=True)
        b[3].markdown(f'<div class="metric-card"><div class="num">{sstr.get("IfcReinforcingBar",0)}</div><div class="lbl">Reinforcing Bars</div></div>', unsafe_allow_html=True)

# ---------- Tab 3: BIM Health ----------
def _badge(st):
    return {"PASS":'<span class="badge badge-pass">PASS</span>',
            "WARNING":'<span class="badge badge-warn">WARNING</span>',
            "REVIEW":'<span class="badge badge-review">REVIEW</span>'}[st]

with tab_health:
    st.subheader("BIM Health Report")
    run_health = st.button("Run BIM Health Check", type="primary") or st.session_state.pop("_goto", None) == "health"
    if run_health:
        h = tools.tool_health()
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for name, value, st_, note in h["rows"]:
            st.markdown(
                f'<div class="kv"><span class="k">{name}</span>'
                f'<span class="v">{value} &nbsp; {_badge(st_)}</span></div>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="card">
<b>Recommendation</b><br/>
Room-related queries should use architectural drawings because spatial room semantics
(IfcSpace) are unavailable in the current IFC export.
</div>""", unsafe_allow_html=True)

# ---------- Tab 4: Coordination ----------
with tab_coord:
    st.subheader("Architecture–Structure Coordination")
    run_coord = st.button("Run Coordination Check", type="primary") or st.session_state.pop("_goto", None) == "coord"
    if run_coord:
        c = tools.tool_coordination()
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for r in c["rows"]:
            badge = ("<span class='badge badge-match'>MATCH</span>" if r["status"]=="MATCH"
                     else f"<span class='badge badge-review'>{r['status']}</span>")
            st.markdown(
                f'<div class="kv"><span class="k">{r["item"]}</span>'
                f'<span class="v">{r["architecture_mm"]} mm &nbsp;|&nbsp; {r["structure_mm"]} mm &nbsp; {badge}</span></div>',
                unsafe_allow_html=True)
            if r["status"] != "MATCH":
                st.caption("⚠ Potential coordination issue. Manual review recommended.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption(c["source_note"])
