"""Explore IFC and PDF files, dump stats to outputs/explore.json."""
import json, os, sys
from collections import Counter
import ifcopenshell
import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)

TARGET_TYPES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
    "IfcDoor", "IfcWindow", "IfcWall",
    "IfcBeam", "IfcColumn", "IfcPile", "IfcFooting", "IfcReinforcingBar",
]

def explore_ifc(path, label):
    m = ifcopenshell.open(path)
    schema = m.schema
    counts = {t: len(m.by_type(t)) for t in TARGET_TYPES}
    # storeys: name + elevation
    storeys = []
    for s in m.by_type("IfcBuildingStorey"):
        elev = None
        try:
            if s.Elevation is not None:
                elev = float(s.Elevation)
        except Exception:
            pass
        storeys.append({"name": s.Name, "global_id": s.GlobalId, "elevation": elev})
    # spaces: name + storey
    spaces = []
    rel_cache = {}
    for sp in m.by_type("IfcSpace"):
        sname = sp.Name
        sclass = getattr(sp, "LongName", None)
        # find parent storey via Decomposes
        parent_storey = None
        try:
            for rel in getattr(sp, "Decomposes", []):
                obj = rel.RelatingObject
                if obj.is_a("IfcBuildingStorey"):
                    parent_storey = obj.Name
                    break
        except Exception:
            pass
        spaces.append({"name": sname, "long_name": sclass, "storey": parent_storey})
    return {
        "file": os.path.basename(path),
        "label": label,
        "schema": schema,
        "counts": counts,
        "storeys": storeys,
        "spaces_sample": spaces[:50],
        "spaces_total": len(spaces),
    }

def explore_pdf(path, label):
    doc = fitz.open(path)
    pages = doc.page_count
    page_texts = []
    for i in range(pages):
        t = doc.load_page(i).get_text()
        page_texts.append({"page": i+1, "chars": len(t), "text": t})
    return {
        "file": os.path.basename(path),
        "label": label,
        "pages": pages,
        "pages_text": page_texts,
    }

result = {
    "architectural_ifc": explore_ifc(os.path.join(DATA, "architectural.ifc"), "Architectural"),
    "structural_ifc": explore_ifc(os.path.join(DATA, "structural.ifc"), "Structural"),
}
# Save full IFC summary
with open(os.path.join(OUT, "ifc_summary.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)

# PDF: extract full text
for name, label in [("architectural.pdf", "Architectural"), ("structural.pdf", "Structural")]:
    p = explore_pdf(os.path.join(DATA, name), label)
    with open(os.path.join(OUT, f"pdf_{name.replace('.pdf','')}.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    # also plain text file for grep
    with open(os.path.join(OUT, f"pdf_{name.replace('.pdf','')}.txt"), "w", encoding="utf-8") as f:
        for pg in p["pages_text"]:
            f.write(f"\n===== PAGE {pg['page']} =====\n")
            f.write(pg["text"])

# Print concise summary
print("=== IFC COUNTS ===")
for k, v in result.items():
    print(f"\n[{v['label']}] schema={v['schema']}")
    for t, c in v["counts"].items():
        print(f"  {t:25s} {c}")
    print("  Storeys:")
    for s in v["storeys"]:
        print(f"    - {s['name']}  elev={s['elevation']}")
print("\nDone.")
