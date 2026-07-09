"""Base widget contract."""

from __future__ import annotations

from abc import ABC
from typing import Any

from widgets.lifecycle import LifecycleHooks
from widgets.models import (
    COMPATIBILITY_VERSION,
    WIDGET_SCHEMA_VERSION,
    DataBinding,
    WidgetMetadata,
    WidgetPermissions,
    WidgetPlacement,
    WidgetState,
    WidgetStyle,
    new_widget_id,
    utc_now,
)
from widgets.validators import validate_widget


class BaseWidget(LifecycleHooks, ABC):
    """Enterprise widget base. No rendering or business logic here."""

    widget_type: str = "base"

    def __init__(
        self,
        *,
        widget_id: str | None = None,
        widget_name: str = "",
        widget_title: str = "",
        widget_version: str = "1.0.0",
        schema_version: str = WIDGET_SCHEMA_VERSION,
        compatibility_version: str = COMPATIBILITY_VERSION,
        placement: WidgetPlacement | None = None,
        widget_state: WidgetState | None = None,
        widget_settings: dict[str, Any] | None = None,
        widget_style: WidgetStyle | None = None,
        widget_permissions: WidgetPermissions | None = None,
        widget_metadata: WidgetMetadata | None = None,
        data_binding: DataBinding | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        self.widget_id = widget_id or new_widget_id()
        self.widget_name = widget_name or self.widget_type
        self.widget_title = widget_title
        self.widget_version = widget_version
        self.schema_version = schema_version
        self.compatibility_version = compatibility_version
        self.created_at = created_at or utc_now()
        self.updated_at = updated_at or self.created_at
        self.placement = placement or WidgetPlacement()
        self.widget_state = widget_state or WidgetState()
        self.widget_settings = dict(widget_settings or {})
        self.widget_style = widget_style or WidgetStyle()
        self.widget_permissions = widget_permissions or WidgetPermissions()
        self.widget_metadata = widget_metadata or WidgetMetadata()
        self.data_binding = data_binding or DataBinding(dataset_id="")

    def touch(self) -> None:
        self.updated_at = utc_now()
        self.widget_state.dirty = True

    def validate(self, *, theme: str | None = None) -> list[str]:
        return validate_widget(
            widget_type=self.widget_type,
            settings=self.widget_settings,
            binding=self.data_binding,
            placement=self.placement,
            style=self.widget_style,
            theme=theme,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_name": self.widget_name,
            "widget_title": self.widget_title,
            "widget_type": self.widget_type,
            "widget_version": self.widget_version,
            "schema_version": self.schema_version,
            "compatibility_version": self.compatibility_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "placement": self.placement.to_dict(),
            "widget_state": self.widget_state.to_dict(),
            "widget_settings": dict(self.widget_settings),
            "widget_style": self.widget_style.to_dict(),
            "widget_permissions": self.widget_permissions.to_dict(),
            "widget_metadata": self.widget_metadata.to_dict(),
            "data_binding": self.data_binding.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseWidget:
        widget_type = data.get("widget_type", "base")
        from widgets.registry import get_widget_class

        widget_cls = get_widget_class(widget_type)
        widget = widget_cls(
            widget_id=data.get("widget_id"),
            widget_name=data.get("widget_name", widget_type),
            widget_title=data.get("widget_title", ""),
            widget_version=data.get("widget_version", "1.0.0"),
            schema_version=data.get("schema_version", WIDGET_SCHEMA_VERSION),
            compatibility_version=data.get("compatibility_version", COMPATIBILITY_VERSION),
            placement=WidgetPlacement.from_dict(data.get("placement", {})),
            widget_state=WidgetState.from_dict(data.get("widget_state", {})),
            widget_settings=dict(data.get("widget_settings", {})),
            widget_style=WidgetStyle.from_dict(data.get("widget_style", {})),
            widget_permissions=WidgetPermissions.from_dict(data.get("widget_permissions", {})),
            widget_metadata=WidgetMetadata.from_dict(data.get("widget_metadata", {})),
            data_binding=DataBinding.from_dict(data.get("data_binding", {})),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        return widget
