# Current Sprint

> **⚠️ This document represents ONLY the ACTIVE sprint.**  
> Completed work belongs in `PROJECT_CHARTER.md` and `CHANGELOG.md`.

---

## Sprint: Release Candidate Preparation

| Field | Value |
|-------|-------|
| **Sprint Name** | RC Prep — Documentation & Phase 5 Gate |
| **Current Phase** | Post Phase 4 / Engine 11 → Release Candidate |
| **Sprint Dates** | Jul 2026 (rolling) |

---

## Sprint Objective

Prepare ExcelMVP for Release Candidate by finalizing permanent documentation, aligning README with completed studio phases, and scoping Phase 5 (Dashboard Builder) without modifying frozen engines.

---

## Architecture Goal

- Zero changes to completed engine packages (`workbook/`, `canvas/`, `widgets/`, `decision_intelligence/`, `visualization_engine.py` core contracts)
- Documentation becomes the single source of truth for AI assistants and new developers
- Phase 5 work planned as a **new layer** on top of canvas/widget infrastructure

---

## Files Expected To Change

| File | Purpose |
|------|---------|
| `PROJECT_CHARTER.md` | Permanent vision (created) |
| `CURRENT_SPRINT.md` | Active sprint tracker (this file) |
| `ARCHITECTURE_DECISIONS.md` | ADR log (created) |
| `CHANGELOG.md` | Sprint completion entries (create when RC ships) |
| `README.md` | Align studio phase status with charter (Phase 4 applied, traceability noted) |

---

## Files That Must NOT Change

| Path | Reason |
|------|--------|
| `workbook/` | Phase 1 — frozen |
| `canvas/` (core) | Phase 2 — frozen |
| `widgets/` (core) | Phase 3 — frozen |
| `decision_intelligence/` | Engine 11 — frozen |
| `visualization_engine.py` (contracts) | Phase 4 — frozen |
| `tests/` | No test changes without explicit sprint scope |

---

## Acceptance Criteria

- [x] `PROJECT_CHARTER.md` created with vision, scope, principles, phases, roadmap, rules
- [x] `ARCHITECTURE_DECISIONS.md` created with ADR-001 through ADR-005
- [x] `CURRENT_SPRINT.md` created and scoped
- [ ] README studio section updated to reflect Phase 4 complete (no contradiction with charter)
- [ ] `CHANGELOG.md` initialized with Phases 1–4 + Engine 11 + traceability entries
- [ ] Full regression suite green (58 tests)

---

## Testing Checklist

| Check | Command / Criteria |
|-------|-------------------|
| Full regression | `python -m pytest tests/ -q` → 58 passed |
| No test file edits | `git diff tests/` empty unless sprint explicitly includes tests |
| Streamlit smoke | `streamlit run app.py` — upload, dashboard, export tabs load |
| Heavy export skip | `EXCELMVP_SKIP_HEAVY_EXPORTS=1` for CI AppTest runs |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Canvas init | < 50 ms (typical layout) |
| Canvas render | < 200 ms (≤ 20 widgets) |
| Test suite | < 60 s full run |
| Streamlit rerun | No unbounded session state growth |

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| README drift vs charter | Single documentation pass; cross-validate sections |
| Phase 5 scope creep | Drag-drop editor only; no BI platform features |
| Circular imports (DI ↔ widgets) | Import from submodules, not package `__init__` |
| Singleton DI engine state | Document `get_default_engine()` trace store behavior |

---

## Definition of Done

1. All three permanent docs exist and are internally consistent
2. No contradictions between charter, ADRs, and README studio phases
3. Regression suite passes without code changes in frozen packages
4. Sprint outcomes recorded in `CHANGELOG.md` when RC milestone closes
5. `CURRENT_SPRINT.md` replaced with Phase 5 sprint plan

---

## Open Questions

| # | Question | Owner |
|---|----------|-------|
| 1 | Should Phase 5 editor persist layouts to workbook session or separate store? | Architecture |
| 2 | Is `CHANGELOG.md` per-sprint or per-release? | PM |
| 3 | README: merge "Build Phases" and "Studio Phases" into one table? | Docs |
| 4 | RC version tag: `v0.9.0-rc` or `v1.0.0-rc1`? | Release |

---

## Next Sprint

**Sprint: Phase 5 — Excel Dashboard Builder**

| Item | Detail |
|------|--------|
| Objective | Drag-and-drop widget placement, alignment tools, keyboard shortcuts, context menus |
| Depends on | Canvas layout serialization, Widget Controller, frozen Phases 1–4 |
| Out of scope | NL→SQL, chat, enterprise SaaS, BI server features |

---

*Replace this entire file at the start of each new sprint.*
