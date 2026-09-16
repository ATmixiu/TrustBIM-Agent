"""Scan production code for hard-coded answer strings.
Fails if demo numbers/rooms appear in production logic."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = ["app.py", "core", "parsers"]
BANNED = [
    "16 doors", "17 windows", "47 walls", "30 columns",
    "370 beams", "32 piles", "3680",
    "ARCH_ELEV", "STR_ELEV",
    "Master Bedroom", "Master Bath",  # only as hard-coded answer list
]
issues = []
for rel in PROD:
    p = os.path.join(ROOT, rel)
    if os.path.isfile(p):
        files = [p]
    else:
        files = [os.path.join(p,f) for f in os.listdir(p) if f.endswith(".py")]
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            for b in BANNED:
                if b in line and not line.strip().startswith("#"):
                    issues.append(f"{os.path.relpath(fp,ROOT)}:{i}: {line.strip()}")
if issues:
    print("FAIL: hard-coded answers found:")
    for i in issues: print(" ", i)
    sys.exit(1)
print("PASS: no hard-coded answers in production code")
