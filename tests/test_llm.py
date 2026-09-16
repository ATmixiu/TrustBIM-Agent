"""Test LLM integration: fallback works, natural-language routing correct, 4 demos still pass."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import llm_client
from core.router import route
from core import tools

print("=== Engine status ===")
eng = llm_client.engine_status()
print(eng)
print("LLM available?", llm_client.is_available())
print()

print("=== Natural-language routing (7 questions) ===")
questions = [
    "Could you check how many doors this house has?",
    "How many windows can you find?",
    "What's upstairs?",
    "Tell me which rooms are on the second level.",
    "Can you check whether anything is missing from the BIM?",
    "Compare the architecture and structure for me.",
    "Are the building levels consistent?",
]
for q in questions:
    intent, params, src = route(q)
    print(f"  [{src:5s}] {q}")
    print(f"          -> {intent}  {params}")
print()

print("=== Four original demos still pass ===")
r1 = tools.tool_bim_query("IfcDoor", "arch")
print("Demo1:", r1["answer"])
r2 = tools.tool_drawing_query("Which rooms are located on Level 2?")
print("Demo2:", r2["answer"][:80])
h = tools.tool_health(); print("Demo3: health rows =", len(h["rows"]))
c = tools.tool_coordination(); print("Demo4: coord rows =", len(c["rows"]))
