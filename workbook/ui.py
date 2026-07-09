"""Workbook UI: ribbon toolbar and Excel-style sheet tabs."""

from __future__ import annotations

import streamlit as st

from workbook.manager import WorkbookManager
from workbook.state import get_pending_rename, persist, set_pending_rename


def inject_workbook_styles() -> None:
    """Inject CSS for ribbon and sheet tab chrome."""
    st.markdown(
        """
        <style>
        .workbook-chrome {
            border: 1px solid rgba(148, 163, 184, .35);
            border-radius: 10px;
            background: rgba(255, 255, 255, .92);
            box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
            margin-bottom: .85rem;
            overflow: hidden;
        }
        .workbook-ribbon-label {
            font-size: .72rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: var(--muted, #64748b);
            margin-bottom: .35rem;
            font-weight: 650;
        }
        .workbook-status {
            font-size: .82rem;
            color: var(--muted, #64748b);
            padding: .45rem .75rem .6rem;
            border-top: 1px solid rgba(148, 163, 184, .2);
            background: rgba(248, 250, 252, .85);
        }
        div[data-testid="stHorizontalBlock"]:has(.sheet-tab-marker) {
            gap: .25rem !important;
            align-items: flex-end !important;
        }
        .sheet-tab-marker { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_ribbon_actions(manager: WorkbookManager) -> WorkbookManager:
    """Render ribbon toolbar buttons and apply sheet operations."""
    st.markdown('<div class="workbook-chrome">', unsafe_allow_html=True)
    st.markdown('<div class="workbook-ribbon-label">Workbook</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, spacer = st.columns([1.1, 1.1, 1.1, 1.2, 3.5])
    with c1:
        if st.button("Add Sheet", key="ribbon_add_sheet", use_container_width=True):
            manager.add_sheet()
            persist(manager)
            set_pending_rename(None)
            st.rerun()
    with c2:
        if st.button("Rename Sheet", key="ribbon_rename_sheet", use_container_width=True):
            set_pending_rename(manager.active_sheet)
            st.rerun()
    with c3:
        if st.button("Delete Sheet", key="ribbon_delete_sheet", use_container_width=True):
            ok, message = manager.delete_sheet(manager.active_sheet)
            if ok:
                persist(manager)
                set_pending_rename(None)
                st.rerun()
            else:
                st.session_state["workbook_last_message"] = message
    with c4:
        if st.button("Duplicate Sheet", key="ribbon_duplicate_sheet", use_container_width=True):
            ok, result = manager.duplicate_sheet(manager.active_sheet)
            if ok:
                persist(manager)
                set_pending_rename(None)
                st.session_state["workbook_last_message"] = f"Duplicated sheet as '{result}'."
                st.rerun()
            else:
                st.session_state["workbook_last_message"] = result

    pending = get_pending_rename()
    if pending and pending in manager.sheet_names:
        with st.form("workbook_rename_form", clear_on_submit=True):
            st.caption(f"Rename sheet: **{pending}**")
            new_name = st.text_input("New sheet name", value=pending, key="workbook_rename_input")
            submit_cols = st.columns([1, 4])
            with submit_cols[0]:
                submitted = st.form_submit_button("Save", use_container_width=True)
            with submit_cols[1]:
                if st.form_submit_button("Cancel", use_container_width=True):
                    set_pending_rename(None)
                    st.rerun()
            if submitted:
                ok, message = manager.rename_sheet(pending, new_name)
                if ok:
                    persist(manager)
                    set_pending_rename(None)
                    st.session_state["workbook_last_message"] = message
                    st.rerun()
                else:
                    st.session_state["workbook_last_message"] = message

    message = st.session_state.pop("workbook_last_message", None)
    if message:
        if "Cannot" in message or "does not exist" in message or "empty" in message.lower():
            st.warning(message)
        else:
            st.success(message)

    meta = (
        f"**{manager.source_name or 'Workbook'}** · "
        f"{manager.sheet_count} sheet{'s' if manager.sheet_count != 1 else ''} · "
        f"Active: **{manager.active_sheet}**"
    )
    if manager.dirty:
        meta += " · Unsaved changes"
    st.markdown(f'<div class="workbook-status">{meta}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return manager


def _render_sheet_tabs(manager: WorkbookManager) -> WorkbookManager:
    """Render Excel-style sheet tab buttons."""
    if manager.sheet_count <= 1:
        st.caption(f"Sheet: **{manager.active_sheet}**")
        return manager

    st.markdown('<div class="workbook-chrome" style="padding:.55rem .65rem .45rem;">', unsafe_allow_html=True)
    chunk_size = 6
    names = manager.sheet_names
    for row_start in range(0, len(names), chunk_size):
        chunk = names[row_start : row_start + chunk_size]
        tab_cols = st.columns(len(chunk))
        for col, sheet_name in zip(tab_cols, chunk):
            with col:
                st.markdown('<span class="sheet-tab-marker"></span>', unsafe_allow_html=True)
                is_active = sheet_name == manager.active_sheet
                if st.button(
                    sheet_name,
                    key=f"sheet_tab_{sheet_name}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    if not is_active:
                        manager.set_active_sheet(sheet_name)
                        persist(manager)
                        set_pending_rename(None)
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    return manager


def render_workbook_chrome(manager: WorkbookManager) -> WorkbookManager:
    """Render ribbon + sheet tabs and return the updated manager."""
    inject_workbook_styles()
    manager = _render_ribbon_actions(manager)
    manager = _render_sheet_tabs(manager)
    return manager
