"""Tools: engineering tools that operate on real IFC/PDF data.
Every number must come from runtime extraction; no hard-coded answers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import ifc_loader, pdf_loader

MODEL_LABEL = {"arch": "Architectural IFC", "str": "Structural IFC"}
ENTITY_HINT = {
    "door": "IfcDoor", "window": "IfcWindow", "wall": "IfcWall",
    "slab": "IfcSlab", "roof": "IfcRoof", "stair": "IfcStair",
    "railing": "IfcRailing", "curtainwall": "IfcCurtainWall",
    "beam": "IfcBeam", "column": "IfcColumn", "pile": "IfcPile",
    "footing": "IfcFooting", "rebar": "IfcReinforcingBar",
    "member": "IfcMember", "space": "IfcSpace", "covering": "IfcCovering",
    "storey": "IfcBuildingStorey", "building": "IfcBuilding",
    "project": "IfcProject", "site": "IfcSite",
}

def _discipline(key):
    return "arch" if key in ("arch", "architecture", "architectural", "a") else "str"

# ---------- Generic IFC query ----------
def tool_query_ifc_entities(discipline="architecture", entity_type="", operation="count"):
    d = _discipline(discipline)
    et = entity_type if entity_type.startswith("Ifc") else "Ifc" + entity_type.capitalize()
    avail = ifc_loader.entity_types(d)
    if et not in avail:
        return {"success": False, "reason": "entity_not_found",
                "requested": et, "available_similar": avail[:20]}
    if operation == "count":
        n = ifc_loader.count(d, et)
        return {"success": True, "discipline": d, "entity_type": et,
                "operation": "count", "count": n,
                "source": MODEL_LABEL[d], "evidence": f"{et} × {n}"}
    elif operation == "types":
        types = ifc_loader.list_types(d, et)
        return {"success": True, "discipline": d, "entity_type": et,
                "operation": "types", "types": types,
                "source": MODEL_LABEL[d],
                "evidence": f"{et} type names extracted from IFC"}
    return {"success": False, "reason": f"unknown operation {operation}"}

# ---------- Drawing search ----------
def tool_search_drawing(query="", discipline="architecture", top_k=3):
    d = _discipline(discipline)
    hits = pdf_loader.search(d, query, top_k=top_k)
    return {"success": True, "query": query, "results": hits,
            "source": f"{MODEL_LABEL[d]} (PDF)"}

# ---------- Rooms from drawing ----------
def tool_extract_rooms(level="Level 2", discipline="architecture"):
    return pdf_loader.extract_rooms_from_drawing(level=level, discipline=_discipline(discipline))

# ---------- BIM Health ----------
def tool_health(discipline="both"):
    targets_a = ["IfcProject","IfcBuilding","IfcBuildingStorey","IfcSpace","IfcDoor","IfcWindow","IfcWall"]
    targets_s = ["IfcBeam","IfcColumn","IfcPile","IfcFooting","IfcReinforcingBar","IfcBuildingStorey","IfcSpace"]
    out = []
    if discipline in ("arch","architecture","a","both"):
        for t in targets_a:
            n = ifc_loader.count("arch", t)
            status = "PASS" if n > 0 else "WARNING"
            out.append({"discipline":"architecture","item":t,"count":n,"status":status})
    if discipline in ("str","structure","s","both"):
        for t in targets_s:
            n = ifc_loader.count("str", t)
            status = "PASS" if n > 0 else "WARNING"
            out.append({"discipline":"structure","item":t,"count":n,"status":status})
    warnings = [o for o in out if o["status"] == "WARNING"]
    return {"success": True, "checks": out, "warnings": warnings,
            "source": "IFC Health Check",
            "recommendation": "Use drawings for room-related questions if IfcSpace is 0."}

# ---------- Coordination: dynamic elevations from IFC storeys ----------
def tool_coordination():
    arch_storeys = ifc_loader.storeys("arch")
    str_storeys = ifc_loader.storeys("str")
    def _by_name(storeys):
        d = {}
        for s in storeys:
            if s["name"] and s["elevation"] is not None:
                d[s["name"]] = s["elevation"]
        return d
    a = _by_name(arch_storeys)
    s = _by_name(str_storeys)
    items = []
    for name in sorted(set(a.keys()) | set(s.keys())):
        av = a.get(name)
        sv = s.get(name)
        if av is None or sv is None:
            status = "REVIEW"
        elif abs(av - sv) < 50:
            status = "MATCH"
        else:
            status = "REVIEW"
        items.append({"item": name, "architecture_mm": av, "structure_mm": sv, "status": status})
    return {"success": True, "items": items,
            "source": "Architecture + Structural IFC storeys",
            "evidence": "IfcBuildingStorey.Elevation compared across disciplines"}

# ---------- Project summary ----------
def tool_summary():
    return {"success": True,
            "architecture": {t: ifc_loader.count("arch", t) for t in
                             ["IfcDoor","IfcWindow","IfcWall","IfcBuildingStorey","IfcSpace","IfcSlab","IfcRoof","IfcStair","IfcRailing"]},
            "structure": {t: ifc_loader.count("str", t) for t in
                          ["IfcBeam","IfcColumn","IfcPile","IfcFooting","IfcReinforcingBar"]}}
