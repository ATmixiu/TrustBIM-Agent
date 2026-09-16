"""Tools: engineering tools operating on real IFC/PDF data. No hardcoded answers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import ifc_loader, pdf_loader

MODEL_LABEL = {"arch": "Architectural IFC", "str": "Structural IFC"}

def _discipline(key):
    return "arch" if key in ("arch","architecture","architectural","a") else "str"

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

# ---------- Rooms ----------
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
            out.append({"discipline":"architecture","item":t,"count":n,
                        "status":"PASS" if n>0 else "WARNING"})
    if discipline in ("str","structure","s","both"):
        for t in targets_s:
            n = ifc_loader.count("str", t)
            out.append({"discipline":"structure","item":t,"count":n,
                        "status":"PASS" if n>0 else "WARNING"})
    warnings = [o for o in out if o["status"]=="WARNING"]
    return {"success": True, "checks": out, "warnings": warnings,
            "source": "IFC Health Check",
            "recommendation": "Use drawings for room-related questions if IfcSpace is 0."}

# ---------- Coordination: dynamic, with PDF fallback for structure ----------
def _ifc_levels(d):
    """Get {name: elevation_mm} from IFC storeys. Returns {} if none."""
    storeys = ifc_loader.storeys(d)
    out = {}
    for s in storeys:
        if s["name"] and s["elevation"] is not None:
            out[s["name"]] = s["elevation"]
    return out

def _norm(name):
    n = name.lower()
    if "level 1" in n or "ground" in n or "lower" in n:
        return "level_1"
    if "level 2" in n or "first floor" in n or "upper" in n:
        return "level_2"
    if "ceiling" in n:
        return "ceiling"
    if "foundation" in n or "footing" in n or "basement" in n:
        return "foundation"
    if "roof" in n or "parapet" in n:
        return "roof"
    return name

def tool_coordination():
    arch_levels = _ifc_levels("arch")
    str_levels = _ifc_levels("str")
    str_source = "Structural IFC"
    # If structure has no storeys, fall back to structural PDF
    if not str_levels:
        pdf_lvl = pdf_loader.extract_levels_from_drawing("str")
        for l in pdf_lvl["levels"]:
            str_levels[l["original_name"]] = l["elevation_mm"]
        str_source = "Structural PDF (dynamic extraction)"
    arch_source = "Architectural IFC" if arch_levels else "Architectural PDF"
    items = []
    all_names = set(arch_levels.keys()) | set(str_levels.keys())
    for name in sorted(all_names):
        av = arch_levels.get(name)
        sv = str_levels.get(name)
        if av is None or sv is None:
            status = "REVIEW"
        elif abs(av - sv) < 50:
            status = "MATCH"
        else:
            status = "REVIEW"
        items.append({"item": name, "architecture_mm": av, "structure_mm": sv,
                      "status": status,
                      "arch_source": arch_source, "str_source": str_source})
    return {"success": True, "items": items,
            "source": f"{arch_source} vs {str_source}",
            "evidence": "IfcBuildingStorey.Elevation / PDF level text compared across disciplines"}

# ---------- Project summary ----------
def tool_summary():
    return {"success": True,
            "architecture": {t: ifc_loader.count("arch", t) for t in
                             ["IfcDoor","IfcWindow","IfcWall","IfcBuildingStorey","IfcSpace","IfcSlab","IfcRoof","IfcStair","IfcRailing"]},
            "structure": {t: ifc_loader.count("str", t) for t in
                          ["IfcBeam","IfcColumn","IfcPile","IfcFooting","IfcReinforcingBar"]}}
