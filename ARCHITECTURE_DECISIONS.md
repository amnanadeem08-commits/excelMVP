# Architecture Decision Records (ADR)

Permanent log of significant architectural decisions. For project vision see `PROJECT_CHARTER.md`. For active work see `CURRENT_SPRINT.md`.

---

## Index

| ADR | Title | Status | Phase |
|-----|-------|--------|-------|
| [ADR-001](#adr-001-workbook-engine) | Workbook Engine | Accepted | Phase 1 |
| [ADR-002](#adr-002-canvas-engine) | Canvas Engine | Accepted | Phase 2 |
| [ADR-003](#adr-003-widget-framework) | Widget Framework | Accepted | Phase 3 |
| [ADR-004](#adr-004-visualization-intelligence) | Visualization Intelligence | Accepted | Phase 4 |
| [ADR-005](#adr-005-decision-intelligence) | Decision Intelligence | Accepted | Engine 11 |

---

## ADR-001: Workbook Engine

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026 |
| **Related Phase** | Phase 1 — Excel Workspace Foundation |
| **Related Modules** | `workbook/manager.py`, `workbook/state.py`, `workbook/ui.py`, `app.py` |

### Context

ExcelMVP originally used a sidebar sheet selector. Users expect Excel-like workbook behavior: multiple sheets, tabs, ribbon actions, and session persistence across Streamlit reruns.

### Problem

- No Excel mental model for multi-sheet workbooks
- Sheet state lost on Streamlit rerun
- Sidebar-only navigation insufficient for studio UX

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep sidebar selectbox | Not Excel-like; poor studio UX |
| External state store (Redis) | Over-engineered for MVP; Streamlit session sufficient |
| Embed Excel via COM/activex | Platform-locked; not deployable on Streamlit Cloud |

### Decision Made

Introduce a dedicated `workbook/` package with `WorkbookManager` (sheet CRUD), `WorkbookState` (session persistence), and `workbook/ui.py` (ribbon + tabs). Integrate in `app.py` without changing the analytics pipeline.

### Reasoning

Sheet management is a stable, bounded concern. Isolating it enables Phase 2+ to key canvas state off `workbook + sheet + mode` without touching data loading or cleaning.

### Benefits

- Excel-familiar UX (add, rename, delete, duplicate sheets)
- Session-persistent active sheet and workbook metadata
- Clean integration point for per-sheet dashboards

### Trade-offs

- Streamlit session state size grows with sheet count
- No real-time collaborative editing
- Sheet operations are in-memory until file re-upload

### Future Impact

Canvas and widget state managers key off workbook context. Phase 5 editor will read/write layouts scoped to active workbook sheet.

---

## ADR-002: Canvas Engine

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026 |
| **Related Phase** | Phase 2 — Dashboard Canvas Engine |
| **Related Modules** | `canvas/engine.py`, `canvas/grid.py`, `canvas/layout.py`, `canvas/serialization.py`, `canvas/state.py`, `canvas/renderer.py` |

### Context

Dashboards were rendered as ad-hoc Streamlit columns. The studio roadmap requires a responsive grid, layout persistence, and a foundation for widget placement.

### Problem

- No reusable layout model
- No responsive breakpoints
- No serialization for future drag-and-drop editor
- Dashboard render logic tightly coupled to `dashboard.py`

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| CSS-only grid in `dashboard.py` | Not reusable; no serialization |
| Third-party dashboard builder lib | Dependency risk; limited Streamlit integration |
| Fixed column layout | Not responsive; blocks Phase 5 editor |

### Decision Made

Create modular `canvas/` package: `GridConfig` + `WidgetPlacement`, `LayoutManager` for auto-layout from artifacts, `DashboardLayout` serialization v2.0.0, `CanvasEngine` with performance metrics, and `canvas/renderer.py` as the dashboard render entry point.

### Reasoning

Separating layout from widget content allows Phase 3 widgets and Phase 5 editor to share one layout contract.

### Benefits

- Responsive grid (desktop / laptop / tablet-ready breakpoints)
- Auto-layout from analytics artifacts (no manual editing yet)
- Layout persistence per workbook + sheet + dashboard mode
- Performance telemetry (`init_ms`, `render_ms`, `peak_memory_kb`)

### Trade-offs

- Auto-layout only — no user-positioned widgets until Phase 5
- Streamlit rendering constraints limit true pixel-perfect Excel grid
- Layout migration required if schema version changes

### Future Impact

Phase 5 drag-and-drop editor will mutate `DashboardLayout` placements. Widget bridge already routes render through canvas.

---

## ADR-003: Widget Framework

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026 |
| **Related Phase** | Phase 3 — Intelligent Widget Framework |
| **Related Modules** | `widgets/` (base, controller, renderer, registry, databinding, adapters, 9 type packages), `widgets/canvas_bridge.py` |

### Context

Canvas needed typed, reusable dashboard components with data binding, lifecycle management, and extension points for AI and export.

### Problem

- Charts and KPIs were functions in `dashboard.py`, not composable components
- No standard widget contract for canvas placement
- No event system for lifecycle hooks
- AI logic risked embedding in renderers

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Streamlit components only | No shared lifecycle or serialization |
| Single monolithic Widget class | Violates OCP; hard to extend types |
| Inherit all types from BaseChart | Deep inheritance tree; poor cohesion |

### Decision Made

Enterprise `widgets/` package:

- `BaseWidget` + `WidgetController` (state/lifecycle only)
- `WidgetRenderer` + type subpackages (KPI, Chart, Table, Pivot, Text, Image, Logo, Divider, Shape)
- `DataBinding` + dataset registry
- `EventBus` for widget lifecycle events
- `ai_adapter.py` and `export_adapter.py` as composition adapters
- `canvas_bridge.py` (`DashboardWidgetBridge`) connecting canvas to widget pipeline

### Reasoning

Controller/renderer split keeps Streamlit rendering separate from state. Registry + factory enable plugin-style type registration without modifying core controller code.

### Benefits

- Pipeline: Workbook → Canvas → Widget Controller → Renderer → Data Binding
- Nine widget types architected and test-covered
- AI and export concerns delegated to adapters
- Canvas bridge enables batch decision evaluation

### Trade-offs

- More packages and indirection than monolithic dashboard
- Circular import risk between `widgets` and `decision_intelligence` — mitigated via submodule imports
- Not all nine types have full custom render implementations yet

### Future Impact

Phase 5 editor manipulates widget instances via `WidgetController`. New widget types register through `registry` without canvas changes.

---

## ADR-004: Visualization Intelligence

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026 |
| **Related Phase** | Phase 4 — Smart Visualization Engine V2 |
| **Related Modules** | `visualization_engine.py`, `dashboard.py`, `analytics_engine.py` |

### Context

Chart selection logic was scattered across `dashboard.py`. Phase 4 required centralized recommendation, generation, and a clean hook to Decision Intelligence.

### Problem

- Duplicate chart-type heuristics
- No versioned visualization contract
- Business recommendations mixed with rendering
- Hard to test chart selection in isolation

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep logic in `dashboard.py` | Violates SRP; untestable in isolation |
| ML-based chart recommender | Over-engineered for MVP; needs training data |
| Embed DI logic in `VisualizationEngine` | Couples visualization to business rules |

### Decision Made

Extract `VisualizationEngine` class in `visualization_engine.py`:

- `recommend()` — structure-aware chart recommendations with priority scores
- `build_auto_charts()` — generates Plotly figures for recommended types
- `request_decision_for_recommendation()` — delegates to DI via `build_source_from_chart` + `get_default_engine()`
- `VISUALIZATION_ENGINE_VERSION = "1.0.0"` for traceability

### Reasoning

Visualization selects **how** to show data; Decision Intelligence decides **what it means**. Interface delegation preserves independence.

### Benefits

- 15+ chart types in recommendation and auto-build paths
- Testable recommendation coverage (`test_visualization_engine.py`)
- DI hook without embedding business logic in renderer
- Backward-compatible upgrade path for existing dashboard flows

### Trade-offs

- Recommendation heuristics are rule-based, not learned
- Plotly/Streamlit constraints on some advanced chart types
- Lazy import of DI in `request_decision_for_recommendation()` to avoid circular deps

### Future Impact

ML recommender can replace `recommend()` internals. Traceability records `visualization_version` on every decision.

---

## ADR-005: Decision Intelligence

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Date** | 2026 |
| **Related Phase** | Engine 11 — Decision Intelligence |
| **Related Modules** | `decision_intelligence/` (engine, models, interface, contract, validators, integration, traceability, providers/) |

### Context

Dashboard and widget layers needed standardized, auditable business recommendations — insight, reason, impact, actions, priority, confidence, evidence — independent of chart rendering.

### Problem

- AI insights were narrative-only (`ai_insights.py`), not structured decisions
- No validation dimensions (relevance, actionability, explainability)
- No provider swap for future LLM/ML backends
- No audit trail for recommendation drift over time

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Extend `ai_insights.py` | Wrong abstraction; insights ≠ actionable decisions |
| LLM-only decisions | Requires API key; breaks offline guarantee |
| Store full evidence payloads in traces | Sensitive data risk; violates explainability-only rule |

### Decision Made

Create `decision_intelligence/` package:

| Component | Responsibility |
|-----------|----------------|
| `DecisionObject` | Standardized output contract (schema v1.1.0) |
| `DecisionIntelligenceEngine` | Orchestrates provider → validate → trace |
| `RuleBasedDecisionProvider` | Default offline provider (`rule_based_v1`) |
| `validate_decision()` | Six-dimension quality scoring |
| `DecisionTraceability` + `DecisionTraceStore` | Metadata-only audit trail |
| `integration.py` | Widget/visualization source builders |
| `contract.py` | Serialize/deserialize decisions |

Traceability fields: `decision_id`, `widget_id`, `dataset_id`, `generated_at`, `engine_version`, `visualization_version`, `confidence_version`, `evidence_references`, `reasoning_path`.

### Reasoning

Provider pattern enables LLM/ML/agent backends without changing widget or canvas code. Traceability enables temporal comparison and AI audit without storing sensitive values.

### Benefits

- Independent from visualization rendering
- Quality validation flags low-confidence decisions
- Executive summary aggregation across widget decisions
- 15 tests (8 DI + 7 traceability)
- `get_default_engine()` singleton accumulates traces across renders

### Trade-offs

- Rule-based provider produces template-style recommendations
- In-memory trace store (not persisted across server restarts)
- Submodule imports required to avoid `widgets` ↔ `decision_intelligence` circular imports

### Future Impact

- Swap `RuleBasedDecisionProvider` for LLM/ML providers via `set_provider()`
- Persist `DecisionTraceStore` to session or file for cross-session audit
- Prediction accuracy validation against historical traces

---

## ADR Template (for future entries)

```markdown
## ADR-NNN: Title

| Field | Value |
|-------|-------|
| **Status** | Proposed / Accepted / Deprecated |
| **Date** | YYYY-MM-DD |
| **Related Phase** | Phase N |
| **Related Modules** | `path/` |

### Context
### Problem
### Alternatives Considered
### Decision Made
### Reasoning
### Benefits
### Trade-offs
### Future Impact
```

---

*Add new ADRs here. Do not modify accepted ADRs — supersede with a new ADR entry.*
