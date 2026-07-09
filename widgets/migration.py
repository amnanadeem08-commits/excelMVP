"""Widget schema version migration."""

from __future__ import annotations

from typing import Any


def migrate_widget_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate widget payloads across schema versions."""
    version = str(data.get("schema_version", "3.0.0"))
    migrated = dict(data)
    if version.startswith("2."):
        binding = dict(migrated.get("data_binding", {}))
        binding.setdefault("source_uri", None)
        binding.setdefault("connection_id", None)
        migrated["data_binding"] = binding
        metadata = dict(migrated.get("widget_metadata", {}))
        metadata.setdefault("tenant_id", "")
        migrated["widget_metadata"] = metadata
        migrated["schema_version"] = "3.0.0"
    return migrated
