"""Workbook session state: persistence across Streamlit reruns."""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd
import streamlit as st

from workbook.manager import WorkbookManager


SESSION_KEY = "workbook_state"
UPLOAD_SIGNATURE_KEY = "workbook_upload_signature"
PENDING_RENAME_KEY = "workbook_pending_rename"


def upload_signature(uploaded_file) -> str:
    """Stable identifier for an uploaded file within the session."""
    payload = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _is_same_upload(uploaded_file) -> bool:
    current = upload_signature(uploaded_file)
    stored = st.session_state.get(UPLOAD_SIGNATURE_KEY)
    return stored == current and SESSION_KEY in st.session_state


def load_or_create(
    uploaded_file,
    parsed: pd.DataFrame | dict[str, pd.DataFrame],
) -> WorkbookManager:
    """Load workbook from session or initialize from a new upload."""
    signature = upload_signature(uploaded_file)

    if _is_same_upload(uploaded_file):
        state = st.session_state[SESSION_KEY]
        return WorkbookManager.from_state_dict(state)

    manager = WorkbookManager.from_upload(parsed, source_name=uploaded_file.name)
    persist(manager)
    st.session_state[UPLOAD_SIGNATURE_KEY] = signature
    st.session_state.pop(PENDING_RENAME_KEY, None)
    return manager


def persist(manager: WorkbookManager) -> None:
    """Save workbook state to Streamlit session."""
    st.session_state[SESSION_KEY] = manager.to_state_dict()


def get_pending_rename() -> str | None:
    return st.session_state.get(PENDING_RENAME_KEY)


def set_pending_rename(sheet_name: str | None) -> None:
    if sheet_name is None:
        st.session_state.pop(PENDING_RENAME_KEY, None)
    else:
        st.session_state[PENDING_RENAME_KEY] = sheet_name


def workbook_metadata(manager: WorkbookManager) -> dict[str, Any]:
    """Lightweight workbook summary for UI captions."""
    active_df = manager.get_active_dataframe()
    return {
        "source_name": manager.source_name,
        "active_sheet": manager.active_sheet,
        "sheet_count": manager.sheet_count,
        "dirty": manager.dirty,
        "active_rows": len(active_df),
        "active_columns": active_df.shape[1],
    }
