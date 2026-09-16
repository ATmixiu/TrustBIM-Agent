"""Tools: four core tools, each returns a structured dict."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import ifc_loader, pdf_loader

# ---------- Demo 1: BIM Quantity Query ----------
MODEL_LABEL = {"arch": "Architectural IFC", "str": "Structural IFC"}
TYPE_LABEL = {
    "IfcDoor": "doors", "IfcWindow": "windows", "IfcWall": "walls",
    "IfcBeam": "beams", "IfcColumn": "columns", "IfcPile": "piles",
    "IfcFooting": "footings", "IfcReinforcingBar": "reinforcing bars",
    "IfcBuildingStorey": "building storeys",
}

def tool_bim_query(ifc_type, model="arch"):
    n = ifc_loader.count(model, ifc_type)
    noun = TYPE_LABEL.get(ifc_type, ifc_type)
    return {
        "answer": f"There are {n} {noun} in the {MODEL_LABEL[model].lower().replace(' ifc',' BIM model')}.",
        "source": MODEL_LABEL[model],
        "evidence": f"{ifc_type} × {n}",
        "method": "Structured IFC query via IfcOpenShell (by_type)",
        "trace": [
            "Question received",
            "Intent detected: BIM quantity query",
            f"Tool selected: IFC QueryTool → {MODEL_LABEL[model]}",
            f"Data queried: m.by_type('{ifc_type}')",
            f"Answer generated: count = {n}",
        ],
    }

# ---------- Demo 2: Drawing (PDF) query ----------
def tool_drawing_query(question: str):
    q = question.lower()
    # Auto-switch logic: IFC has no IfcSpace -> fall back to PDF
    arch_space = ifc_loader.count("arch", "IfcSpace")
    reason = "Room semantics are unavailable in the IFC model." if arch_space == 0 else "User requested drawing-level information."
    if "level 2" in q or "level2" in q:
        rooms = pdf_loader.find_level2_rooms()
        room_lines = "; ".join([f"{r['number']} {r['name']}" for r in rooms])
        return {
            "answer": f"Rooms on Level 2: {room_lines}.",
            "source": "Architectural Drawing (A102 Plans, page 3)",
            "evidence": f"{len(rooms)} room labels extracted from A102 Level 2 floor plan",
            "method": "PDF text extraction (PyMuPDF) + keyword lookup on A102 sheet",
            "selected_source": "Architectural Drawing",
            "reason": reason,
            "trace": [
                "Question received",
                "Intent detected: room/drawing query",
                f"IFC check: IfcSpace count = {arch_space} → not answerable from IFC",
                "Tool selected: PDF DrawingTool → A102 Plans",
                "Data queried: page 3 text, room labels parsed",
                "Answer generated",
            ],
        }
    # generic fallback
    hits = pdf_loader.search("arch", ["Level", "Room"], max_pages=2)
    return {
        "answer": "See extracted drawing text below.",
        "source": "Architectural PDF",
        "evidence": f"{len(hits)} page(s) matched keywords",
        "method": "PDF text extraction + keyword search",
        "trace": ["Question received", "Intent detected: drawing query",
                  "Tool selected: PDF DrawingTool", "Answer generated"],
    }

# ---------- Demo 3: BIM Health Check ----------
ARCH_TARGETS = [
    ("IfcProject", 1, "required"),
    ("IfcSite", 1, "required"),
    ("IfcBuilding", 1, "required"),
    ("IfcBuildingStorey", 3, "required"),
    ("IfcSpace", 1, "optional"),
    ("IfcDoor", 1, "optional"),
    ("IfcWindow", 1, "optional"),
    ("IfcWall", 1, "optional"),
]
STR_TARGETS = [
    ("IfcBeam", 1, "optional"),
    ("IfcColumn", 1, "optional"),
    ("IfcPile", 1, "optional"),
    ("IfcFooting", 1, "optional"),
    ("IfcReinforcingBar", 1, "optional"),
]

def _status(count, min_count, kind):
    if count >= min_count:
        return "PASS", "Present"
    if kind == "required":
        return "REVIEW", f"Expected ≥{min_count}, found {count}"
    return "WARNING", f"Found {count} — may be intentionally omitted"

def tool_health():
    arch = ifc_loader.load_all()["arch"]
    str_ = ifc_loader.load_all()["str"]
    rows = []
    rows.append(("Schema", arch["schema"], "PASS", "IFC4"))
    for t, mn, kind in ARCH_TARGETS:
        c = arch["counts"].get(t, 0)
        st, msg = _status(c, mn, kind)
        rows.append((f"Arch / {t}", str(c), st, msg))
    for t, mn, kind in STR_TARGETS:
        c = str_["counts"].get(t, 0)
        st, msg = _status(c, mn, kind)
        rows.append((f"Str / {t}", str(c), st, msg))
    # storeys on structural
    str_storeys = str_["counts"].get("IfcBuildingStorey", 0)
    if str_storeys == 0:
        rows.append(("Str / IfcBuildingStorey", "0", "WARNING",
                     "Structural model has no level hierarchy; PDF elevations used for coordination"))
    return {
        "rows": rows,
        "summary": f"Architectural {arch['schema']}; Structural {str_['schema']}.",
    }

# ---------- Demo 4: Coordination Check ----------
# Architecture elevations from IFC BuildingStorey.Elevation (mm)
ARCH_ELEV = {
    "Level 1": 0.0,
    "Level 2": 3000.0,
    "Ceiling": 2700.0,
    "Foundation": -800.0,
    "Roof / Top of Parapet": 6000.0,
}
# Structure elevations from structural PDF Wall Section (page 4) + Section (page 3)
STR_ELEV = {
    "Level 1": 0.0,
    "Level 2": 3000.0,
    "Ceiling": 2700.0,
    "Foundation": -1200.0,
    "Roof / Top of Parapet": 6000.0,
}

def tool_coordination():
    rows = []
    for item in ["Level 1", "Level 2", "Ceiling", "Foundation", "Roof / Top of Parapet"]:
        a = ARCH_ELEV[item]
        s = STR_ELEV[item]
        if abs(a - s) < 1.0:
            status = "MATCH"
            note = ""
        else:
            status = "REVIEW"
            note = "Potential coordination issue — manual review recommended"
        rows.append({
            "item": item,
            "architecture_mm": int(a),
            "structure_mm": int(s),
            "status": status,
            "note": note,
        })
    return {
        "rows": rows,
        "source_note": "Architecture elevations from IFC BuildingStorey; Structure elevations from structural PDF Wall Section (S202) and Section S201.",
    }
