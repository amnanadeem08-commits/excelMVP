"""Lightweight widget event bus."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4


EventHandler = Callable[["WidgetEvent"], None]

REQUIRED_EVENTS = (
    "widget_created",
    "widget_updated",
    "widget_deleted",
    "widget_selected",
    "widget_refreshed",
    "widget_exported",
    "widget_data_changed",
    "widget_visibility_changed",
)


@dataclass
class WidgetEvent:
    event_type: str
    widget_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )


class EventBus:
    """Simple in-process pub/sub for widget lifecycle and future integrations."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[WidgetEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: WidgetEvent) -> None:
        self._history.append(event)
        for handler in self._subscribers.get(event.event_type, []):
            handler(event)
        for handler in self._subscribers.get("*", []):
            handler(event)

    def emit(self, event_type: str, widget_id: str, **payload: Any) -> WidgetEvent:
        event = WidgetEvent(event_type=event_type, widget_id=widget_id, payload=payload)
        self.publish(event)
        return event

    def history(self, *, widget_id: str | None = None, limit: int = 50) -> list[WidgetEvent]:
        items = self._history
        if widget_id:
            items = [event for event in items if event.widget_id == widget_id]
        return items[-limit:]

    def clear(self) -> None:
        self._history.clear()
