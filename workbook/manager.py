"""Workbook manager: Excel-like multi-sheet state and operations."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import pandas as pd

from data_loader import list_sheets, select_sheet


def _unique_sheet_name(existing: list[str], base: str) -> str:
    """Return a sheet name that does not collide with existing names."""
    if base not in existing:
        return base
    match = re.match(r"^(.*?)(?: \((\d+)\))?$", base)
    root = match.group(1) if match else base
    counter = 2
    while True:
        candidate = f"{root} ({counter})"
        if candidate not in existing:
            return candidate
        counter += 1


def _next_default_sheet_name(existing: list[str]) -> str:
    """Generate the next default sheet name (Sheet1, Sheet2, ...)."""
    used = {name.lower() for name in existing}
    counter = 1
    while True:
        candidate = f"Sheet{counter}"
        if candidate.lower() not in used:
            return candidate
        counter += 1


def _empty_sheet_template(active_df: pd.DataFrame | None) -> pd.DataFrame:
    """Create a new sheet scaffold matching the active sheet columns when possible."""
    if active_df is not None and not active_df.empty and len(active_df.columns) > 0:
        return pd.DataFrame(columns=list(active_df.columns))
    return pd.DataFrame({"Column1": []})


class WorkbookManager:
    """Manage workbook sheets, active selection, and sheet CRUD operations."""

    def __init__(
        self,
        sheets: dict[str, pd.DataFrame],
        *,
        active_sheet: str | None = None,
        sheet_order: list[str] | None = None,
        source_name: str = "",
    ) -> None:
        if not sheets:
            raise ValueError("Workbook must contain at least one sheet.")
        self.sheets = {name: df.copy() for name, df in sheets.items()}
        names = list(sheets.keys())
        self.sheet_order = list(sheet_order) if sheet_order else names
        self.sheet_order = [name for name in self.sheet_order if name in self.sheets]
        for name in names:
            if name not in self.sheet_order:
                self.sheet_order.append(name)
        self.active_sheet = active_sheet or self.sheet_order[0]
        if self.active_sheet not in self.sheets:
            self.active_sheet = self.sheet_order[0]
        self.source_name = source_name
        self.dirty = False

    @classmethod
    def from_upload(
        cls,
        parsed: pd.DataFrame | dict[str, pd.DataFrame],
        *,
        source_name: str = "",
    ) -> WorkbookManager:
        """Build a workbook from data_loader output (single frame or sheet dict)."""
        if isinstance(parsed, dict):
            sheets = parsed
        else:
            sheets = {"Sheet1": parsed}
        order = list_sheets(sheets)
        active = order[0] if order else None
        return cls(sheets, active_sheet=active, sheet_order=order, source_name=source_name)

    @property
    def sheet_names(self) -> list[str]:
        return list(self.sheet_order)

    @property
    def sheet_count(self) -> int:
        return len(self.sheet_order)

    def get_active_dataframe(self) -> pd.DataFrame:
        return self.sheets[self.active_sheet]

    def set_active_sheet(self, sheet_name: str) -> bool:
        if sheet_name not in self.sheets:
            return False
        self.active_sheet = sheet_name
        return True

    def add_sheet(self, name: str | None = None) -> str:
        """Add a new sheet and make it active. Returns the new sheet name."""
        name = name or _next_default_sheet_name(self.sheet_order)
        name = _unique_sheet_name(self.sheet_order, name.strip() or _next_default_sheet_name(self.sheet_order))
        active_df = self.get_active_dataframe()
        self.sheets[name] = _empty_sheet_template(active_df)
        self.sheet_order.append(name)
        self.active_sheet = name
        self.dirty = True
        return name

    def rename_sheet(self, old_name: str, new_name: str) -> tuple[bool, str]:
        """Rename a sheet. Returns (success, message)."""
        new_name = new_name.strip()
        if not new_name:
            return False, "Sheet name cannot be empty."
        if old_name not in self.sheets:
            return False, f"Sheet '{old_name}' does not exist."
        if new_name != old_name and new_name in self.sheets:
            return False, f"Sheet '{new_name}' already exists."
        if new_name == old_name:
            return True, "Sheet name unchanged."

        idx = self.sheet_order.index(old_name)
        self.sheet_order[idx] = new_name
        self.sheets[new_name] = self.sheets.pop(old_name)
        if self.active_sheet == old_name:
            self.active_sheet = new_name
        self.dirty = True
        return True, f"Renamed '{old_name}' to '{new_name}'."

    def delete_sheet(self, sheet_name: str) -> tuple[bool, str]:
        """Delete a sheet. Returns (success, message)."""
        if sheet_name not in self.sheets:
            return False, f"Sheet '{sheet_name}' does not exist."
        if len(self.sheet_order) <= 1:
            return False, "Cannot delete the last sheet in the workbook."

        self.sheet_order.remove(sheet_name)
        del self.sheets[sheet_name]
        if self.active_sheet == sheet_name:
            self.active_sheet = self.sheet_order[0]
        self.dirty = True
        return True, f"Deleted sheet '{sheet_name}'."

    def duplicate_sheet(self, sheet_name: str | None = None) -> tuple[bool, str]:
        """Duplicate a sheet. Returns (success, new_sheet_name or error message)."""
        source = sheet_name or self.active_sheet
        if source not in self.sheets:
            return False, f"Sheet '{source}' does not exist."

        base = f"Copy of {source}"
        new_name = _unique_sheet_name(self.sheet_order, base)
        self.sheets[new_name] = deepcopy(self.sheets[source])
        source_idx = self.sheet_order.index(source)
        self.sheet_order.insert(source_idx + 1, new_name)
        self.active_sheet = new_name
        self.dirty = True
        return True, new_name

    def update_sheet_data(self, sheet_name: str, df: pd.DataFrame) -> None:
        """Replace sheet data (used when reloading from upload)."""
        if sheet_name in self.sheets:
            self.sheets[sheet_name] = df.copy()

    def to_state_dict(self) -> dict[str, Any]:
        """Serialize workbook metadata for session persistence."""
        return {
            "sheets": self.sheets,
            "active_sheet": self.active_sheet,
            "sheet_order": self.sheet_order,
            "source_name": self.source_name,
            "dirty": self.dirty,
        }

    @classmethod
    def from_state_dict(cls, state: dict[str, Any]) -> WorkbookManager:
        """Restore a workbook from session state."""
        manager = cls(
            state["sheets"],
            active_sheet=state.get("active_sheet"),
            sheet_order=state.get("sheet_order"),
            source_name=state.get("source_name", ""),
        )
        manager.dirty = bool(state.get("dirty", False))
        return manager

    def as_loader_workbook(self) -> dict[str, pd.DataFrame]:
        """Expose sheets in the format expected by data_loader helpers."""
        return self.sheets

    def select_active_via_loader(self) -> pd.DataFrame:
        """Return the active sheet using data_loader.select_sheet for compatibility."""
        return select_sheet(self.as_loader_workbook(), self.active_sheet)
