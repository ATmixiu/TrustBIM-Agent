"""Offline smoke test for the four core demos. Writes outputs/test_results.csv"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import tools
from core.router import route

QUESTIONS = [
    "How many doors are in the architectural model?",
    "Which rooms are located on Level 2?",
    "How many beams are in the structural model?",
    "How many rebar bars exist?",
    "How many windows are there?",
    "How many piles are in the foundation?",
    "Run BIM Health Check",
    "Run Coordination Check",
    "What rooms are on Level 2?",
    "Compare architecture and structure levels",
]

rows = []
print("=" * 70)
for q in QUESTIONS:
    intent, params = route(q)
    if intent == "bim_query":
        r = tools.tool_bim_query(params["ifc_type"], params.get("model", "arch"))
        ans = r["answer"]; src = r["source"]; tool = "BIM Query"
    elif intent == "drawing_query":
        r = tools.tool_drawing_query(q)
        ans = r["answer"]; src = r["source"]; tool = "Drawing Query"
    elif intent == "bim_health":
        r = tools.tool_health()
        ans = r["summary"]; src = "IFC (both)"; tool = "BIM Health"
    elif intent == "coordination":
        r = tools.tool_coordination()
        ans = f"{len(r['rows'])} items compared"; src = "IFC + PDF"; tool = "Coordination"
    else:
        ans = "UNKNOWN"; src = "-"; tool = intent
    ok = "PASS" if ans != "UNKNOWN" else "FAIL"
    rows.append([q, tool, ans, src, ok])
    print(f"[{tool:14s}] {q}")
    print(f"     -> {ans}")
    print()

os.makedirs("outputs", exist_ok=True)
with open("outputs/test_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["Question", "Selected Tool", "Answer", "Source", "Pass/Fail"])
    w.writerows(rows)
print(f"Saved outputs/test_results.csv  ({len(rows)} rows)")

# Also verify the 4 named demos explicitly
print("=" * 70)
print("DEMO 1:", tools.tool_bim_query("IfcDoor", "arch")["answer"])
print("DEMO 2:", tools.tool_drawing_query("Which rooms are located on Level 2?")["answer"])
h = tools.tool_health(); print("DEMO 3: rows =", len(h["rows"]))
c = tools.tool_coordination(); print("DEMO 4: rows =", len(c["rows"]))
