"""End-to-end smoke test: run the full Streamlit app with a simulated upload.

``st.file_uploader`` is not supported by Streamlit's AppTest, so the main
upload widget is patched to return an in-memory CSV; every other uploader
(logo, join file) stays empty, which matches a first-run session.
"""

from __future__ import annotations

from io import BytesIO

import streamlit as st
from streamlit.testing.v1 import AppTest


class _NamedUpload(BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def test_app_renders_all_tabs_without_exceptions(monkeypatch, sales_df):
    upload = _NamedUpload(sales_df.to_csv(index=False).encode("utf-8"), "sales.csv")

    def fake_uploader(label, *args, key=None, **kwargs):
        return upload if key == "main_upload" else None

    monkeypatch.setattr(st, "file_uploader", fake_uploader)

    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()

    assert not at.exception, f"app raised an exception: {at.exception}"
    assert at.title and "Excel" in at.title[0].value
    # No in-place errors: no failed transforms, no invalid custom-chart defaults.
    assert not at.error, [element.value for element in at.error]
    # Downloads tab has the client deliverable buttons.
    downloads_tab = next((tab for tab in at.tabs if tab.label == "Downloads"), None)
    assert downloads_tab is not None, "Downloads tab missing"
    # Download buttons are inside Blocks (columns). Walk the tree to find them.
    def collect_labels(element):
        labels = []
        if hasattr(element, "label") and element.label:
            labels.append(element.label)
        if hasattr(element, "children"):
            for child in element.children.values():
                labels.extend(collect_labels(child))
        return labels
    download_labels = collect_labels(downloads_tab)
    assert "Client PDF" in download_labels
    assert "Client PPT" in download_labels
    # Data Tools tab exposes transformation actions when a transform panel is shown.
    # (Column selection is provided by the sidebar KPI controls, not a standalone button.)
    # Sidebar KPI overrides (DESIGN.md §2 step 5) are present.
    keys = {box.key for box in at.selectbox}
    assert {"kpi_metric", "kpi_agg", "client_color_theme"} <= keys


def test_dark_theme_switch_injects_dark_surfaces(monkeypatch, sales_df):
    """Switching to the Dark theme must change whole-dashboard surfaces."""
    upload = _NamedUpload(sales_df.to_csv(index=False).encode("utf-8"), "sales.csv")

    def fake_uploader(label, *args, key=None, **kwargs):
        return upload if key == "main_upload" else None

    monkeypatch.setattr(st, "file_uploader", fake_uploader)

    at = AppTest.from_file("app.py", default_timeout=120)
    upload.seek(0)
    at.run()
    assert not at.exception

    theme_box = next(box for box in at.selectbox if box.key == "client_color_theme")
    theme_box.select("Dark")
    upload.seek(0)
    at.run()
    assert not at.exception

    css = " ".join(element.value for element in at.markdown if isinstance(element.value, str))
    # Dark preset surface + card colors must appear in the injected stylesheet.
    assert "#0f172a" in css, "dark theme surfaces were not injected"
    assert "--card-bg: #1e293b" in css, "dark theme card background was not injected"
