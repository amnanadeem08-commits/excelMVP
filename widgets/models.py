"""Widget domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


WIDGET_SCHEMA_VERSION = "3.0.0"
COMPATIBILITY_VERSION = "3.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_widget_id() -> str:
    return str(uuid4())


@dataclass
class WidgetPlacement:
    """Canvas grid placement (layout only, no business logic)."""

    col: int = 0
    row: int = 0
    col_span: int = 4
    row_span: int = 2
    z_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "col": self.col,
            "row": self.row,
            "col_span": self.col_span,
            "row_span": self.row_span,
            "z_index": self.z_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetPlacement:
        return cls(
            col=int(data.get("col", 0)),
            row=int(data.get("row", 0)),
            col_span=int(data.get("col_span", 4)),
            row_span=int(data.get("row_span", 2)),
            z_index=int(data.get("z_index", 0)),
        )


@dataclass
class DataBinding:
    """Dataset reference without embedding dataframes."""

    dataset_id: str
    query: str | None = None
    source_uri: str | None = None
    connection_id: str | None = None
    columns: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    aggregation: str | None = None
    sort: list[str] = field(default_factory=list)
    calculated_fields: list[dict[str, Any]] = field(default_factory=list)
    cache_key: str = ""
    refresh_policy: str = "on_change"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "query": self.query,
            "source_uri": self.source_uri,
            "connection_id": self.connection_id,
            "columns": list(self.columns),
            "filters": dict(self.filters),
            "aggregation": self.aggregation,
            "sort": list(self.sort),
            "calculated_fields": list(self.calculated_fields),
            "cache_key": self.cache_key,
            "refresh_policy": self.refresh_policy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataBinding:
        return cls(
            dataset_id=str(data.get("dataset_id", "")),
            query=data.get("query"),
            source_uri=data.get("source_uri"),
            connection_id=data.get("connection_id"),
            columns=list(data.get("columns", [])),
            filters=dict(data.get("filters", {})),
            aggregation=data.get("aggregation"),
            sort=list(data.get("sort", [])),
            calculated_fields=list(data.get("calculated_fields", [])),
            cache_key=str(data.get("cache_key", "")),
            refresh_policy=str(data.get("refresh_policy", "on_change")),
        )


@dataclass
class WidgetState:
    visible: bool = True
    locked: bool = False
    selected: bool = False
    dirty: bool = False
    last_refresh: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "visible": self.visible,
            "locked": self.locked,
            "selected": self.selected,
            "dirty": self.dirty,
            "last_refresh": self.last_refresh,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetState:
        return cls(
            visible=bool(data.get("visible", True)),
            locked=bool(data.get("locked", False)),
            selected=bool(data.get("selected", False)),
            dirty=bool(data.get("dirty", False)),
            last_refresh=str(data.get("last_refresh", "")),
        )


@dataclass
class WidgetStyle:
    theme: str = "default"
    palette: list[str] = field(default_factory=list)
    css_class: str = "canvas-widget"

    def to_dict(self) -> dict[str, Any]:
        return {"theme": self.theme, "palette": list(self.palette), "css_class": self.css_class}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetStyle:
        return cls(
            theme=str(data.get("theme", "default")),
            palette=list(data.get("palette", [])),
            css_class=str(data.get("css_class", "canvas-widget")),
        )


@dataclass
class WidgetPermissions:
    can_edit: bool = True
    can_export: bool = True
    can_refresh: bool = True
    can_delete: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_edit": self.can_edit,
            "can_export": self.can_export,
            "can_refresh": self.can_refresh,
            "can_delete": self.can_delete,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetPermissions:
        return cls(
            can_edit=bool(data.get("can_edit", True)),
            can_export=bool(data.get("can_export", True)),
            can_refresh=bool(data.get("can_refresh", True)),
            can_delete=bool(data.get("can_delete", True)),
        )


@dataclass
class WidgetMetadata:
    source: str = "auto_layout"
    mode_key: str = ""
    legacy_type: str = ""
    tenant_id: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "mode_key": self.mode_key,
            "legacy_type": self.legacy_type,
            "tenant_id": self.tenant_id,
            "tags": list(self.tags),
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetMetadata:
        return cls(
            source=str(data.get("source", "auto_layout")),
            mode_key=str(data.get("mode_key", "")),
            legacy_type=str(data.get("legacy_type", "")),
            tenant_id=str(data.get("tenant_id", "")),
            tags=list(data.get("tags", [])),
            extra=dict(data.get("extra", {})),
        )
