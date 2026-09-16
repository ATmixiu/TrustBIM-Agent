"""TrustBIM Agent — product-grade Streamlit UI."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from core import tools
from core import llm_client
from core.router import rule_route
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
.kv { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #eef2f8; font-size:14px;}
.kv:last-child { border-bottom:none; }
.kv .k { color:#5a6b85; }
.kv .v { color:#0F2C59; font-weight:600; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="Loading BIM & drawings...")
def boot():
    return ifc_loader.load_all(), pdf_loader.load_all()

ifc_data, pdf_data = boot()

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

eng = llm_client.engine_status()
if eng["state"] == "online":
    st.markdown(f"""
<div style="background:#e3f9ec;border:1px solid #9be2b8;border-radius:8px;
 padding:8px 16px;margin-bottom:14px;font-size:13px;color:#1a7f4b;">
<b>AI Engine:</b> ● LLM Connected — {eng['platform']} / {eng['model']} (function calling)
</div>""", unsafe_allow_html=True)
else:
    err = eng.get("error", "")
    st.markdown(f"""
<div style="background:#fff4e0;border:1px solid #f5cf8a;border-radius:8px;
 padding:8px 16px;margin-bottom:14px;font-size:13px;color:#b36b00;">
<b>AI Engine:</b> ● Offline Deterministic Fallback — {eng['platform']} / {eng['model']}<br>
<small>{err}</small>
</div>""", unsafe_allow_html=True)

tab_chat, tab_overview, tab_health, tab_coord = st.tabs(
    ["💬 AI Assistant", "📊 Project Overview", "🩺 BIM Health", "🔗 Coordination"]
)

def _is_cn(q):
    return bool(re.search(r"[\u4e00-\u9fff]", q))

def offline_answer(q):
    cn = _is_cn(q)
    intent, params, _ = rule_route(q)
    trace = ["Question received", "Mode: Offline Deterministic Fallback", f"Local rule route → {intent}"]
    if intent == "bim_query":
        et = params["ifc_type"]; mk = params.get("model","arch")
        r = tools.tool_query_ifc_entities(discipline=mk, entity_type=et, operation="count")
        n = r.get("count", 0)
        noun_map = {"IfcDoor":"门","IfcWindow":"窗","IfcWall":"墙","IfcBeam":"梁",
                    "IfcColumn":"柱","IfcPile":"桩","IfcFooting":"基础","IfcReinforcingBar":"钢筋",
                    "IfcSlab":"板","IfcStair":"楼梯","IfcRailing":"栏杆","IfcRoof":"屋顶"}
        if cn:
            ans = f"{MODEL_CN[mk]}中共有 {n} 个{noun_map.get(et, et)}。"
        else:
            ans = f"There are {n} {et} in the BIM model."
        trace += [f"Tool: query_ifc_entities({et}, count)", f"Result: {n}"]
        return ans, r.get("source",""), r.get("evidence",""), "Rule-based IFC query", trace
    if intent == "bim_health":
        h = tools.tool_health("architecture")
        warns = [f"{w['item']}={w['count']}" for w in h["warnings"]]
        if cn:
            ans = f"健康检查完成，需关注：{'; '.join(warns)}。"
        else:
            ans = f"Health check done. Warnings: {', '.join(warns)}."
        return ans, h["source"], "; ".join(warns), "BIM Health Check", trace + ["Tool: bim_health_check"]
    if intent == "coordination":
        c = tools.tool_coordination()
        reviews = [f"{i['item']} (arch={i['architecture_mm']} vs str={i['structure_mm']})" for i in c["items"] if i["status"]=="REVIEW"]
        if cn:
            ans = f"共比较 {len(c['items'])} 个标高项，需复核：{'; '.join(reviews) if reviews else '无'}。"
        else:
            ans = f"Compared {len(c['items'])} levels. Reviews: {'; '.join(reviews) if reviews else 'none'}."
        return ans, c["source"], c["evidence"], "Coordination Check", trace + ["Tool: coordination_check"]
    if intent == "drawing_query":
        r = tools.tool_extract_rooms("Level 2", "architecture")
        if r["success"]:
            if cn:
                ans = f"二层房间：{', '.join(r['rooms'])}。"
            else:
                ans = f"Level 2 rooms: {', '.join(r['rooms'])}."
            return ans, r["source"], "Room labels extracted from drawing", "Drawing text extraction", trace + ["Tool: extract_rooms"]
        if cn:
            ans = "无法从图纸中可靠提取房间信息。"
        else:
            ans = "Room information could not be reliably extracted from the drawing."
        return ans, r["source"], r["reason"], "Drawing text extraction", trace + ["Tool: extract_rooms", "Extraction failed"]
    if cn:
        return "我可以回答 BIM 数量、图纸、健康检查和协调问题。", "—", "—", "Rule router", trace
    return "I can answer BIM quantity, drawing, health and coordination questions.", "—", "—", "Rule router", trace

MODEL_CN = {"arch":"建筑模型","str":"结构模型"}

with tab_chat:
    # ---- Project source selector ----
    src_choice = st.radio("Project Source",
                          ["Sample House (Course Demo)", "Upload Your Own Project"],
                          horizontal=True, key="proj_src")
    if src_choice == "Upload Your Own Project":
        up_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp", "uploaded")
        os.makedirs(up_dir, exist_ok=True)
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            af = st.file_uploader("Architectural IFC (.ifc)", type=["ifc"], key="up_arch_ifc")
            ap = st.file_uploader("Architectural Drawing (.pdf)", type=["pdf"], key="up_arch_pdf")
        with col_up2:
            sf = st.file_uploader("Structural IFC (.ifc)", type=["ifc"], key="up_str_ifc")
            sp = st.file_uploader("Structural Drawing (.pdf)", type=["pdf"], key="up_str_pdf")
        if st.button("Load Uploaded Project", type="primary"):
            saved = []
            for upload, name in [(af,"architectural.ifc"),(ap,"architectural.pdf"),
                                 (sf,"structural.ifc"),(sp,"structural.pdf")]:
                if upload is not None:
                    with open(os.path.join(up_dir, name), "wb") as f:
                        f.write(upload.getbuffer())
                    saved.append(name)
            if saved:
                ifc_loader.set_project_dir(up_dir)
                pdf_loader.set_project_dir(up_dir)
                st.session_state["proj_loaded"] = True
                st.success(f"Loaded: {', '.join(saved)}")
                st.cache_resource.clear()
                st.rerun()
            else:
                st.warning("Please upload at least one file.")
        if st.session_state.get("proj_loaded") and st.button("Clear / Reset to Sample House"):
            ifc_loader.set_project_dir(None)
            pdf_loader.set_project_dir(None)
            st.session_state["proj_loaded"] = False
            st.cache_resource.clear()
            st.rerun()
        if st.session_state.get("proj_loaded"):
            st.info("📁 Current: Uploaded Project (session-only, not saved to GitHub)")
    else:
        ifc_loader.set_project_dir(None)
        pdf_loader.set_project_dir(None)

    q = st.text_input("Ask the agent",
                      placeholder="e.g. How many doors are in the architectural model? / 这个建筑有几扇门？")
    c1, c2 = st.columns([1, 5])
    run = c1.button("Run", type="primary")

    if run and q.strip():
        result = None
        trace = []
        mode = ""
        if llm_client.is_available():
            result, trace, err = llm_client.agent_run(q)
            if result:
                mode = "online"
            else:
                mode = "offline"
                trace.append(f"LLM failed: {err} → falling back to offline router")
        else:
            mode = "offline"
            trace = ["Question received", "Mode: Offline Deterministic Fallback"]

        if mode == "offline":
            ans, src, ev, meth, off_trace = offline_answer(q)
            trace = off_trace + trace

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="ans-label">ANSWER</div>', unsafe_allow_html=True)
        if mode == "online":
            st.markdown(f'<div class="ans-body">{result["answer"]}</div>', unsafe_allow_html=True)
            src = result.get("source",""); ev = result.get("evidence",""); meth = result.get("method","")
        else:
            st.markdown(f'<div class="ans-body">{ans}</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f'<div class="kv"><span class="k">SOURCE</span><span class="v">{src}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kv"><span class="k">EVIDENCE</span><span class="v">{ev}</span></div>', unsafe_allow_html=True)
        with col_b:
            st.markdown(f'<div class="kv"><span class="k">METHOD</span><span class="v">{meth}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="kv"><span class="k">MODE</span><span class="v">{"Online LLM Agent" if mode=="online" else "Offline Fallback"}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Agent Process** (real tool execution trace)")
        for i, s in enumerate(trace, 1):
            st.markdown(f'<div class="trace-step"><b>{i}.</b> {s}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

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

def _badge(s):
    return {"PASS":'<span class="badge badge-pass">PASS</span>',
            "WARNING":'<span class="badge badge-warn">WARNING</span>',
            "REVIEW":'<span class="badge badge-review">REVIEW</span>'}[s]

with tab_health:
    st.subheader("BIM Health Report")
    if st.button("Run BIM Health Check", type="primary"):
        h = tools.tool_health("both")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for c in h["checks"]:
            st.markdown(
                f'<div class="kv"><span class="k">{c["discipline"]} · {c["item"]}</span>'
                f'<span class="v">{c["count"]} &nbsp; {_badge(c["status"])}</span></div>',
                unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card"><b>Recommendation</b><br/>{h["recommendation"]}</div>',
                    unsafe_allow_html=True)

with tab_coord:
    st.subheader("Architecture–Structure Coordination")
    if st.button("Run Coordination Check", type="primary"):
        c = tools.tool_coordination()
        st.markdown('<div class="card">', unsafe_allow_html=True)
        for r in c["items"]:
            badge = ("<span class='badge badge-match'>MATCH</span>" if r["status"]=="MATCH"
                     else f"<span class='badge badge-review'>{r['status']}</span>")
            st.markdown(
                f'<div class="kv"><span class="k">{r["item"]}</span>'
                f'<span class="v">{r["architecture_mm"]} mm &nbsp;|&nbsp; {r["structure_mm"]} mm &nbsp; {badge}</span></div>',
                unsafe_allow_html=True)
            if r["status"] != "MATCH":
                st.caption("⚠ Potential coordination issue. Manual review recommended.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption(c["source"])
