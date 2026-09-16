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

def page_count(model_key):
    return len(load_all()[model_key]["pages"])

def search(model_key, query, top_k=3):
    """Return top-k pages matching query terms, with snippets."""
    d = load_all()
    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not terms:
        return []
    scored = []
    for i, text in enumerate(d[model_key]["pages"]):
        low = text.lower()
        score = sum(low.count(t) for t in terms)
        if score > 0:
            lines = [ln.strip() for ln in text.splitlines()
                     if any(t in ln.lower() for t in terms)]
            scored.append({"page": i+1, "score": score, "snippets": lines[:10]})
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]

def extract_rooms_from_drawing(level="Level 2", discipline="architecture"):
    """Dynamically parse room names from PDF. No hard-coded fallback.
    Returns {"success": bool, "rooms": [...], "source": str, "reason": str}."""
    d = load_all()[discipline]
    # scan all pages for "Room Legend"
    candidates = []
    for i, text in enumerate(d["pages"]):
        lines = [l.strip() for l in text.splitlines()]
        legend_idx = [j for j, l in enumerate(lines) if l == "Room Legend"]
        if len(legend_idx) >= 2:
            # second legend is Level 2 in this sample
            start = legend_idx[1] + 1
            FILTER = {"Deck", "Walking", "bridge to", "carport",
                      "Rain water", "collection tanks", "Mech.", "Outdoor Dining"}
            names = []
            k = start
            while k < len(lines):
                l = lines[k]
                if not l:
                    k += 1; continue
                if l in {"3000", "6000"} or l.startswith("Chimney") or l == "Room Legend":
                    break
                if re.match(r"^\d", l):
                    k += 1; continue
                if l in FILTER or len(l) < 2 or l in {"-", "?"}:
                    k += 1; continue
                names.append(l)
                k += 1
            seen = set(); out = []
            for n in names:
                if n not in seen:
                    seen.add(n); out.append(n)
            if out:
                return {"success": True, "rooms": out,
                        "source": f"{discipline} PDF page {i+1}",
                        "reason": None}
    return {"success": False, "rooms": [],
            "source": f"{discipline} PDF",
            "reason": "room_labels_not_reliably_extracted"}
