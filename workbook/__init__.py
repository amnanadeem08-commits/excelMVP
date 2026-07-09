"""Excel-like workbook workspace: manager, session state, and UI chrome."""

from workbook.manager import WorkbookManager
from workbook.state import load_or_create, persist, workbook_metadata
from workbook.ui import inject_workbook_styles, render_workbook_chrome

__all__ = [
    "WorkbookManager",
    "inject_workbook_styles",
    "load_or_create",
    "persist",
    "render_workbook_chrome",
    "workbook_metadata",
]
