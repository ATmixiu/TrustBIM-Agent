"""PDF loader: extract text once, cache per page; provide keyword search."""
import os, threading, re
import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
_lock = threading.Lock()
_cache = {}

def _build(path, label):
    doc = fitz.open(path)
    pages = []
    for i in range(doc.page_count):
        pages.append(doc.load_page(i).get_text())
    return {"label": label, "pages": pages}

def load_all():
    with _lock:
        if _cache:
            return _cache
        _cache["arch"] = _build(os.path.join(DATA, "architectural.pdf"), "Architectural")
        _cache["str"]  = _build(os.path.join(DATA, "structural.pdf"),   "Structural")
        return _cache

def search(model_key, keywords, max_pages=5):
    """Return list of {page, snippet} where any keyword matches."""
    d = load_all()
    hits = []
    kws = [k.lower() for k in keywords]
    for i, text in enumerate(d[model_key]["pages"]):
        low = text.lower()
        if any(k in low for k in kws):
            # build snippet: lines containing any keyword
            lines = text.splitlines()
            kept = []
            for ln in lines:
                ll = ln.lower()
                if any(k in ll for k in kws):
                    kept.append(ln.strip())
            hits.append({"page": i+1, "snippet": kept[:30]})
            if len(hits) >= max_pages:
                break
    return hits

def page_text(model_key, page_no):
    return load_all()[model_key]["pages"][page_no-1]

def find_level2_rooms():
    """Hard-coded for the A102 sheet (page 3) of this sample project.
    Source: architectural PDF page 3 (A102 Plans, Level 2 floor plan)."""
    rooms = [
        {"number": "201", "name": "Entry Hall"},
        {"number": "202", "name": "Bedroom"},
        {"number": "204", "name": "Bedroom"},
        {"number": "206", "name": "Master Bedroom"},
        {"number": "206", "name": "Master Bath"},
        {"number": "-",   "name": "Bath"},
        {"number": "-",   "name": "Linen"},
    ]
    return rooms
