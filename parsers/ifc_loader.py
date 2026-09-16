"""IFC loader: parse both IFCs once, cache all entity types, storeys, elevations."""
import os, re, threading
import ifcopenshell

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

_project_dir = None

def set_project_dir(d):
    global _project_dir, _cache
    _project_dir = d
    _cache = {}

def _paths():
    if _project_dir:
        return (os.path.join(_project_dir, "architectural.ifc"),
                os.path.join(_project_dir, "structural.ifc"))
    return (os.path.join(DATA, "architectural.ifc"),
            os.path.join(DATA, "structural.ifc"))

_lock = threading.Lock()
_cache = {}

# Types we always track for health/summary
DEFAULT_TARGETS = [
    "IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcSpace",
    "IfcDoor","IfcWindow","IfcWall","IfcSlab","IfcRoof","IfcStair",
    "IfcRailing","IfcCurtainWall","IfcBeam","IfcColumn","IfcPile",
    "IfcFooting","IfcReinforcingBar","IfcMember","IfcCovering",
]

def _build(path, label):
    m = ifcopenshell.open(path)
    # discover all entity types actually present
    present = set()
    try:
        for elem in m:
            present.add(elem.is_a())
    except Exception:
        pass
    counts = {t: len(m.by_type(t)) for t in present if t.startswith("Ifc")}
    storeys = []
    for s in m.by_type("IfcBuildingStorey"):
        elev = None
        try:
            if s.Elevation is not None:
                elev = round(float(s.Elevation), 1)
        except Exception:
            pass
        storeys.append({"name": s.Name or "", "elevation": elev})
    return {
        "model": m,
        "label": label,
        "schema": m.schema,
        "counts": counts,
        "storeys": storeys,
        "entity_types": sorted(counts.keys()),
    }

def load_all():
    with _lock:
        if _cache:
            return _cache
        arch_p, str_p = _paths()
        _cache["arch"] = _build(arch_p, "Architectural") if os.path.exists(arch_p) else None
        _cache["str"]  = _build(str_p, "Structural") if os.path.exists(str_p) else None
        return _cache

def count(model_key, ifc_type):
    d = load_all()
    data = d.get(model_key)
    if data is None:
        return 0
    if ifc_type in data["counts"]:
        return data["counts"][ifc_type]
    m = data["model"]
    try:
        n = len(m.by_type(ifc_type))
        data["counts"][ifc_type] = n
        return n
    except Exception:
        return 0

def storeys(model_key):
    d = load_all()
    data = d.get(model_key)
    return data["storeys"] if data else []

def schema(model_key):
    d = load_all()
    data = d.get(model_key)
    return data["schema"] if data else ""

def get_model(model_key):
    d = load_all()
    data = d.get(model_key)
    return data["model"] if data else None

def entity_types(model_key=None):
    d = load_all()
    if model_key:
        data = d.get(model_key)
        return data["entity_types"] if data else []
    return {"arch": (d.get("arch") or {}).get("entity_types", []),
            "str": (d.get("str") or {}).get("entity_types", [])}

def list_types(model_key, ifc_type):
    m = get_model(model_key)
    if m is None:
        return []
    bases = set()
    try:
        for elem in m.by_type(ifc_type):
            n = getattr(elem, "Name", None)
            if n:
                base = re.sub(r":\d+$", "", str(n))
                bases.add(base)
            ot = getattr(elem, "ObjectType", None)
            if ot:
                bases.add(str(ot))
    except Exception:
        pass
    return sorted(bases)
