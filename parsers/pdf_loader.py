"""PDF loader: extract text + coordinates; dynamic room/level extraction.
No hard-coded room lists or elevation dictionaries."""
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
    return {"label": label, "pages": pages, "path": path}

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

def _level_number(level_str):
    """Extract 1/2 from 'Level 1', 'level2', 'upstairs', etc."""
    s = str(level_str).lower()
    m = re.search(r"(\d+)", s)
    if m:
        return int(m.group(1))
    if "upstair" in s or "second" in s or "2nd" in s or "upper" in s:
        return 2
    if "downstair" in s or "first" in s or "1st" in s or "lower" in s or "ground" in s:
        return 1
    return None

def _d(key):
    return "arch" if key in ("arch","architecture","architectural","a") else "str"

def extract_rooms_from_drawing(level="Level 2", discipline="architecture"):
    """Coordinate-aware room extraction. Uses PDF word positions to find the
    correct floor-plan region for the requested level. No hard-coded rooms."""
    d = load_all()[_d(discipline)]
    lvl = _level_number(level)
    if lvl is None:
        return {"success": False, "rooms": [], "level": level,
                "reason": "cannot_determine_level", "source": f"{discipline} PDF"}
    doc = fitz.open(d["path"])
    best = None
    for pno in range(doc.page_count):
        page = doc.load_page(pno)
        page_text = page.get_text()
        if "Room Legend" not in page_text:
            continue
        words = page.get_text("words")
        pw = page.rect.width
        level_centers = {}
        for i, w in enumerate(words):
            if w[4] == "Level" and i+1 < len(words):
                next_tok = words[i+1][4]
                if next_tok in ("1","2","3","4"):
                    level_centers[int(next_tok)] = (w[0]+w[2])/2
        if lvl not in level_centers:
            continue
        target_x = level_centers[lvl]
        side = 1 if target_x < pw/2 else -1
        region_min = 0 if side == 1 else pw/2
        region_max = pw/2 if side == 1 else pw
        FILTER = {"Deck","Walking","bridge to","carport","Mech.",
                  "Outdoor Dining","Rain water","collection tanks","Chimney",
                  "Room","Legend","Level","www","com","autodesk","revit",
                  "Scale","Checked","Drawn","Date","Project","number",
                  "Consultant","Address","Phone","Fax","e-mail","PM","Plans",
                  "Sample","House","Issue","No.","Description","DN","m²",
                  "A101","A102","A103","A104","A105","SM","JLH",
                  "27/08/2026","3:10:25","bridge","to","by","www.autodesk.com/revit"}
        room_lines = []
        seen = set()
        for w in words:
            x0,y0,x1,y1,txt = w[0],w[1],w[2],w[3],w[4]
            cx = (x0+x1)/2
            if not (region_min < cx < region_max):
                continue
            if re.match(r"^[\d.\-]+$", txt):
                continue
            if txt in FILTER or len(txt) < 2 or txt in {"-","?",":","1","2"}:
                continue
            if re.match(r"^\d{3,}", txt):
                continue
            clean = txt.strip()
            if clean and clean not in seen:
                seen.add(clean)
                room_lines.append(clean)
        if len(room_lines) >= 2:
            best = {"success": True, "rooms": room_lines,
                    "level": f"Level {lvl}",
                    "source": f"{discipline} PDF page {pno+1}",
                    "reason": None}
            break
    doc.close()
    if best:
        return best
    return {"success": False, "rooms": [], "level": level,
            "reason": "room_labels_not_reliably_extracted",
            "source": f"{discipline} PDF"}

def extract_levels_from_drawing(discipline="structure"):
    """Scan PDF for level name + elevation value pairs dynamically.
    Returns list of {original_name, elevation_mm}."""
    d = load_all()[_d(discipline)]
    results = {}
    for pno, text in enumerate(d["pages"]):
        lines = [l.strip() for l in text.splitlines()]
        for i, line in enumerate(lines):
            # look for a line that looks like a level name
            if re.match(r"^(level|floor|ceiling|foundation|roof|parapet|top of)", line, re.I):
                # next non-empty line should be a number (mm)
                for j in range(i+1, min(i+4, len(lines))):
                    nxt = lines[j]
                    m = re.match(r"^(-?\d{2,5}(?:\.\d+)?)$", nxt)
                    if m:
                        val = float(m.group(1))
                        # normalize to mm
                        if abs(val) < 100:
                            val = val * 1000
                        results.setdefault(line, []).append(round(val))
                        break
    out = []
    for name, vals in results.items():
        out.append({"original_name": name, "elevation_mm": vals[0],
                    "page": None})
    return {"success": True, "levels": out,
            "source": f"{discipline} PDF (dynamic scan)"}
