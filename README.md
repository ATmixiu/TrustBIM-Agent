# TrustBIM Agent

AI Agent prototype for reading teacher-provided BIM (IFC) and construction drawings (PDF),
answering questions, and running two automated BIM QA checks.

## Quick start

```
cd /d D:\TrustBIM_Agent
.venv\Scripts\activate
streamlit run app.py
```

Then open http://localhost:8501 in a browser.

## What it does (4 core demos)

| # | Demo | User input | Behavior |
|---|------|------------|----------|
| 1 | BIM Quantity Query | `How many doors are in the architectural model?` | Routes to IFC QueryTool, returns real count (16 doors) |
| 2 | PDF Drawing Query | `Which rooms are located on Level 2?` | Detects `IfcSpace = 0` in IFC, auto-switches to PDF (A102 Plans), lists Level 2 rooms |
| 3 | BIM Health Check | `Run BIM Health Check` | Checks IFC schema, required/optional entity counts, returns PASS / WARNING / REVIEW |
| 4 | Coordination Check | `Run Coordination Check` | Compares Level 1 / Level 2 / Ceiling / Foundation / Roof elevations between arch IFC and struct PDF |

Every answer shows **Answer / Source / Evidence / Method** plus an Agent Trace.

## Project layout

```
D:\TrustBIM_Agent\
├── .venv\                 # Python virtual env (D drive)
├── data\
│   ├── original\2026.zip  # teacher's original archive (untouched)
│   ├── architectural.ifc   # RAC sample
│   ├── architectural.pdf
│   ├── structural.ifc      # RST sample
│   └── structural.pdf
├── core\
│   ├── router.py           # rule-based intent router
│   └── tools.py            # 4 tools
├── parsers\
│   ├── ifc_loader.py       # IfcOpenShell loader + cache
│   ├── pdf_loader.py       # PyMuPDF text extractor + cache
│   └── explore.py          # one-off data exploration
├── outputs\
│   ├── ifc_summary.json
│   ├── pdf_architectural.{txt,json}
│   ├── pdf_structural.{txt,json}
│   └── test_results.csv    # 10 smoke-test Q&A
├── tests\smoke_test.py
├── app.py                  # Streamlit UI
└── requirements.txt
```

## Data notes (from this dataset)

- Architectural IFC (IFC4): 16 doors, 17 windows, 47 walls, 6 storeys, **0 spaces**
  → room semantics must come from PDF.
- Structural IFC (IFC4): 370 beams, 30 columns, 32 piles, 4 footings, 3680 rebar,
  **0 building storeys** → elevation comparison uses structural PDF Wall Section.
- Key elevations (mm): Level 1 = 0, Level 2 = 3000, Ceiling = 2700,
  Foundation arch = −800 vs struct = −1200 (→ REVIEW), Roof/Parapet = 6000.

## Out of scope today (Future Work)

Multi-agent frameworks (LangGraph/AutoGen), vector DB / RAG, Revit/RVT parsing,
2D→3D, clash detection, cost estimation, 4D, login, cloud, React/Vue,
complex 3D viewer, vision-model OCR, model auto-repair.
