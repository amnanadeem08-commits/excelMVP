# ExcelMVP — Project Charter

Permanent vision document. Stable across sprints. For operational sprint detail, see `CURRENT_SPRINT.md`. For architectural decisions, see `ARCHITECTURE_DECISIONS.md`.

---

## Project Vision

ExcelMVP is an **enterprise-grade, AI-powered Excel Dashboard Studio** — a Python/Streamlit application that transforms uploaded spreadsheets into cleaned data, interactive dashboards, AI-style insights, and client-ready exports.

### Mission

Automate the manual Excel reporting work freelancers and small teams perform repeatedly: ingest spreadsheets, clean and analyze data, build executive dashboards, surface actionable insights, and deliver branded deliverables — without requiring a separate BI platform.

### Core Philosophy

| Principle | Application |
|-----------|-------------|
| Excel-first | Users think in sheets, tabs, and workbooks — not databases |
| Progressive enhancement | Rule-based engines work offline; AI upgrades when configured |
| Studio evolution | MVP automation → modular dashboard studio with composable engines |
| Explainability | Decisions and recommendations must be auditable, not black-box |
| Freelance-ready | Fast setup, branded exports, sellable dashboard modes |

### Target Users

- Freelancers delivering Excel/reporting projects (Fiverr, Upwork)
- Small-business owners and managers needing executive dashboards
- Analysts exploring sales, finance, operations, and HR datasets
- Future AI assistants extending the studio without rewriting core engines

### Business Goals

- Reduce time-to-deliverable for spreadsheet reporting jobs
- Produce client-ready PDF, PPT, and Excel outputs from one upload
- Support multiple dashboard personas (executive, analytical, financial, operational)
- Maintain a sellable, demo-ready Streamlit deployment path

### Long-Term Maintainability

- Modular packages (`workbook/`, `canvas/`, `widgets/`, `decision_intelligence/`, `visualization_engine.py`)
- Versioned contracts (layout serialization, decision schema, engine versions)
- Regression test suite as the non-negotiable safety net
- Documentation-first onboarding for humans and AI assistants

### AI-Ready Architecture

- Provider-pattern decision engine (rule-based today; LLM/ML/agent backends pluggable)
- Standardized Decision Object contract with traceability metadata
- Widget and visualization layers request intelligence via interfaces — no embedded business logic in renderers
- Metadata-only audit trails (no sensitive data in trace stores)

### Production Quality

- 58 automated tests across workbook, canvas, widgets, visualization, and decision intelligence
- Performance metrics on canvas operations
- Graceful degradation (offline rule-based insights when LLM unavailable)
- `EXCELMVP_SKIP_HEAVY_EXPORTS` test mode for CI-friendly runs

---

## Product Scope

Capabilities **delivered and in production** within ExcelMVP:

| Capability | Package / Module | Summary |
|------------|------------------|---------|
| **Workbook Engine** | `workbook/` | Multi-sheet CRUD, ribbon toolbar, session-persistent state |
| **Canvas Engine** | `canvas/` | Responsive grid, auto-layout, layout serialization v2.0.0 |
| **Widget Framework** | `widgets/` | Controller, renderer, data binding, 9 widget types, event bus |
| **Visualization Intelligence** | `visualization_engine.py` | Chart recommendation, auto-generation, DI hook (v1.0.0) |
| **Decision Intelligence** | `decision_intelligence/` | Decision Object contract, validation, traceability (Engine 11) |
| **Dashboard Builder** | `dashboard.py`, `dashboard_modes/` | Themes, branding, focus modes, chart density (auto-layout; no drag-drop editor) |
| **AI Insights** | `ai_insights.py` | Rule-based + optional LLM narratives (4-section report) |
| **Forecasting** | `forecasting/` | Simple forecast helpers for financial mode |
| **Exports** | `export_module.py` | Excel, CSV, PDF, PPT with embedded charts |
| **Themes** | `dashboard.py` | Preset and custom brand palettes |
| **Smart Dashboard Modes** | `dashboard_modes/` | Executive, Analytical, Financial, Operational |
| **Data Pipeline** | `data_loader.py`, `data_cleaning.py`, `analytics_engine.py` | Ingest, clean, pivots, KPIs |

### Render Pipeline (Studio)

```text
Workbook → Dashboard → Canvas → Widget Controller → Widget Renderer
                                                      ↓
                                               Data Binding
                                                      ↓
                                        Decision Intelligence Engine
```

---

## Out of Scope

These capabilities **intentionally do not belong** in ExcelMVP. They belong to the future **AI Data Bot** project:

| Out of Scope | Rationale |
|--------------|-----------|
| Power BI replacement | ExcelMVP is a spreadsheet studio, not an enterprise BI server |
| Tableau replacement | No visual analytics platform or server infrastructure |
| Enterprise BI platform | No multi-tenant SaaS, RBAC, or warehouse-scale analytics |
| Database management | No schema design, SQL administration, or ETL orchestration |
| Data warehouse | No lakehouse, dimensional modeling, or batch pipelines |
| Semantic model | No OLAP cubes or enterprise metric layers |
| NL→SQL | Natural-language querying belongs in AI Data Bot |
| RAG | Retrieval-augmented document Q&A is a separate product |
| LLM Chat | Conversational "ask the warehouse" is out of scope here |
| Enterprise SaaS | No billing, tenancy, or org management in ExcelMVP |

ExcelMVP may **optionally** call an LLM for narrative insights when configured, but it does not provide chat, RAG, or SQL generation.

---

## Architecture Principles

| Principle | ExcelMVP Application |
|-----------|---------------------|
| **Low Coupling** | Engines communicate through interfaces and adapters, not direct renderer imports |
| **High Cohesion** | Each package owns one concern (workbook state, canvas layout, widget lifecycle, decisions) |
| **SOLID** | Provider swap for DI; widget registry for extension; thin `app.py` orchestration |
| **Clean Architecture** | Domain models (`DecisionObject`, `DashboardLayout`) separate from Streamlit UI |
| **Provider Pattern** | `DecisionProvider` implementations (rule-based, future LLM/ML) |
| **Event-Driven Communication** | Widget `EventBus` for lifecycle events |
| **Plugin Architecture** | Widget registry and type subpackages (`widgets/kpi/`, `widgets/charts/`, …) |
| **Composition over Inheritance** | Adapters (`ai_adapter`, `export_adapter`, `canvas_bridge`) compose behavior |
| **Backward Compatibility** | New studio phases integrate without breaking upload → clean → dashboard flow |
| **Minimal Technical Debt** | Completed phases are frozen; changes require regression + architecture review |

---

## Completed Phases

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| **Phase 1** | Excel Workspace Foundation | ✅ Complete | `workbook/` — manager, state, ribbon UI, sheet tabs |
| **Phase 2** | Dashboard Canvas Engine | ✅ Complete | `canvas/` — grid, layout, serialization, renderer |
| **Phase 3** | Intelligent Widget Framework | ✅ Complete | `widgets/` — controller, renderer, binding, 9 types |
| **Phase 4** | Smart Visualization Engine V2 | ✅ Complete | `visualization_engine.py` — recommend, build, DI hook |
| **Engine 11** | Decision Intelligence | ✅ Complete | `decision_intelligence/` — contract, validation, traceability |

### Regression Coverage

| Area | Test Module(s) |
|------|----------------|
| Workbook | `test_workbook_manager.py`, `test_workbook_session.py` |
| Canvas | `test_canvas_engine.py`, `test_canvas_performance.py` |
| Widgets | `test_widgets_framework.py` |
| Visualization | `test_visualization_engine.py`, `test_visualization_decision_hook.py` |
| Decision Intelligence | `test_decision_intelligence.py`, `test_decision_traceability.py` |
| Integration | `test_smart_dashboard_modes.py`, `test_streamlit_smart_modes.py` |

---

## Future Roadmap

| Milestone | Scope | Status |
|-----------|-------|--------|
| **Phase 5** | Excel Dashboard Builder — drag-and-drop editor, alignment, shortcuts, context menus | Planned |
| **Release Candidate** | Full regression, performance baseline, documentation sync, README alignment | Next |
| **Version 1.0** | Stable studio release with frozen public contracts | Planned |
| **Maintenance Mode** | Bug fixes and provider additions only; no breaking phase changes | Post-1.0 |

### Deferred Build Phases (Original MVP Roadmap)

These remain on the longer horizon and are **not** studio phases 1–5:

- AI Analyst Layer (chat, tone selection, saved AI notes in exports)
- Excel Macro-Style Workflow (templates, refresh analysis, VBA stubs)
- Client Delivery Polish (saved presets, upload history, cloud deploy hardening)

---

## Development Rules

Every future change must satisfy **all** of the following:

| Gate | Requirement |
|------|-------------|
| **Regression testing** | `python -m pytest tests/ -q` — zero failures |
| **Performance review** | Canvas metrics within established baselines; no render regressions |
| **Architecture review** | No business logic in renderers; use DI interfaces and adapters |
| **AI readiness review** | New intelligence features use provider pattern and Decision Object contract |
| **Technical debt review** | No modifications to frozen completed-phase packages without explicit approval |
| **Production readiness review** | Graceful degradation preserved; no mandatory API keys for core flows |

### Phase Protection Rule

> **Never break completed phases.** Phases 1–4 and Engine 11 are frozen. Extend via adapters, new providers, or new packages — do not rewrite stable foundations.

### Documentation Rule

- Vision and scope → `PROJECT_CHARTER.md`
- Active work → `CURRENT_SPRINT.md`
- Architecture decisions → `ARCHITECTURE_DECISIONS.md`
- Setup and usage → `README.md` (operational, not architectural)

---

*Last aligned with codebase: Studio Phases 1–4, Engine 11, 58 passing tests.*
