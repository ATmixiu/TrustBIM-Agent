"""IFC loader: parse both IFCs once, cache stats and storeys."""
import json, os, threading
import ifcopenshell

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

TARGET_ARCH = ["IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcSpace",
               "IfcDoor","IfcWindow","IfcWall"]
TARGET_STR = ["IfcBeam","IfcColumn","IfcPile","IfcFooting","IfcReinforcingBar",
              "IfcBuildingStorey","IfcSpace"]

_lock = threading.Lock()
_cache = {}

def _build(path, label, targets):
    m = ifcopenshell.open(path)
    counts = {t: len(m.by_type(t)) for t in targets}
    storeys = []
    for s in m.by_type("IfcBuildingStorey"):
        elev = None
        try:
            if s.Elevation is not None:
                elev = round(float(s.Elevation), 1)
        except Exception:
            pass
        storeys.append({"name": s.Name, "elevation": elev})
    return {
        "label": label,
        "schema": m.schema,
        "counts": counts,
        "storeys": storeys,
    }

def load_all():
    with _lock:
        if _cache:
            return _cache
        _cache["arch"] = _build(os.path.join(DATA, "architectural.ifc"), "Architectural", TARGET_ARCH)
        _cache["str"]  = _build(os.path.join(DATA, "structural.ifc"),   "Structural",   TARGET_STR)
        return _cache

def count(model_key, ifc_type):
    d = load_all()
    return d[model_key]["counts"].get(ifc_type, 0)

def storeys(model_key):
    return load_all()[model_key]["storeys"]

def schema(model_key):
    return load_all()[model_key]["schema"]
