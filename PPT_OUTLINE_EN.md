# TrustBIM Agent — PPT Outline (English, 8 slides)

## Slide 1 — Team & Project
- Team name, course, date
- Project: **TrustBIM Agent**
- One-line: *A tool-using AI agent that reads teacher-provided BIM (IFC) and construction drawings (PDF) and answers questions with provenance.*

## Slide 2 — Problem
- BIM (IFC) and construction drawings (PDF) are two separate silos.
- Practitioners need to jump between Revit, PDF viewers and guesswork to answer even simple questions.
- LLM-only answers hallucinate quantities and elevations.
- No lightweight agent that routes natural language to the right structured data source.

## Slide 3 — Solution
- **TrustBIM Agent**: a rule-router + Python-tools agent.
- User question → intent classification → IFC tool or PDF tool → real data → answer.
- Every answer ships with **Answer / Source / Evidence / Method**.
- No LLM required for the demo; LLM is an optional polish layer.

## Slide 4 — Agent Architecture
- Input: natural language question (English).
- Router: keyword + regex intent classifier (BIM query / drawing query / health / coordination).
- Tools:
  - `IfcQueryTool` → IfcOpenShell, `by_type()` counts.
  - `DrawingTool` → PyMuPDF text extraction, keyword lookup on A102 sheet.
  - `HealthCheckTool` → required/optional entity presence table.
  - `CoordinationTool` → arch IFC elevations vs struct PDF elevations.
- Output: structured result + trace (Question → Intent → Tool → Data → Answer).

## Slide 5 — Prototype
- Stack: Python 3.14, Streamlit, IfcOpenShell 0.8, PyMuPDF.
- Data: RAC (architectural) + RST (structural) sample, 1 IFC + 1 PDF each.
- UI: 4 tabs — AI Assistant, Project Overview, BIM Health, Coordination.
- Key real numbers discovered:
  - Arch: 16 doors, 17 windows, 47 walls, 6 storeys, **0 spaces**.
  - Struct: 370 beams, 30 columns, 32 piles, 4 footings, 3680 rebar, **0 storeys**.

## Slide 6 — Demo / Testing
- Four live demos:
  1. "How many doors are in the architectural model?" → 16 (IFC).
  2. "Which rooms are on Level 2?" → auto-switches to PDF A102 (IFC has no spaces).
  3. BIM Health Check → PASS / WARNING / REVIEW table.
  4. Coordination Check → Foundation −800 (arch) vs −1200 (struct) → REVIEW.
- 10-question smoke test saved at `outputs/test_results.csv`, all PASS.

## Slide 7 — Innovation
- **Tool-using, not LLM-guessing**: counts and elevations come from real file parsing.
- **Self-aware fallback**: when IFC lacks `IfcSpace`, the agent reasons about its own gap and switches to PDF.
- **Conservative coordination language**: REVIEW + "manual review recommended", never "design error".
- **Full provenance on every answer** — Source / Evidence / Method.

## Slide 8 — Future Work
- LLM layer for intent polish and paraphrased answer generation.
- Vector RAG over drawing text; vision OCR for raster sheets.
- Revit/RVT parsing; clash detection; cost estimation; 4D scheduling.
- Multi-agent framework (LangGraph), user login, cloud deployment, 3D viewer with element highlighting.
