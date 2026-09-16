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
    """Dynamically parse Level 2 room names from A102 sheet (page 3).
    Rule: A102 has two Room Legends (Level 1 then Level 2). Take the second
    Room Legend's entries, filter out non-room labels (Deck, bridges, tanks).
    Returns list of {number, name}.
    """
    text = load_all()["arch"]["pages"][2]  # page 3 = A102 (0-indexed)
    lines = [l.strip() for l in text.splitlines()]
    # find all "Room Legend" positions
    legend_idx = [i for i, l in enumerate(lines) if l == "Room Legend"]
    if len(legend_idx) < 2:
        # fallback: hard-coded known set (kept only as last resort)
        return [
            {"number": "201", "name": "Entry Hall"},
            {"number": "202", "name": "Bedroom"},
            {"number": "204", "name": "Bedroom"},
            {"number": "206", "name": "Master Bedroom"},
            {"number": "-", "name": "Master Bath"},
            {"number": "-", "name": "Bath"},
            {"number": "-", "name": "Linen"},
        ]
    # Level 2 legend is the second one
    start = legend_idx[1] + 1
    # Filter out non-room labels (some wrap across lines in the PDF)
    FILTER = {"Deck", "Walking", "bridge to", "carport",
              "Rain water", "collection tanks", "Mech.", "Outdoor Dining"}
    names = []
    i = start
    while i < len(lines):
        l = lines[i]
        if not l:
            i += 1; continue
        # stop at numeric dimension lines or section breaks
        if l in {"3000", "6000"} or l.startswith("Chimney") or l == "Room Legend":
            break
        if re.match(r"^\d", l):
            i += 1; continue
        if l in FILTER:
            i += 1; continue
        if len(l) < 2 or l in {"-", "?"}:
            i += 1; continue
        names.append(l)
        i += 1
    # dedupe preserving order
    seen = set(); out = []
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return [{"number": "-", "name": n} for n in out]
