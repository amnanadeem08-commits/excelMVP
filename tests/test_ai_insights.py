"""Tests for ai_insights.py: rule-based fallback and dataset typing."""

from __future__ import annotations

import pandas as pd

from ai_insights import detect_dataset_type, generate_ai_insights
from data_cleaning import clean_data, detect_column_types

REQUIRED_KEYS = {
    "dataset_type",
    "dataset_summary",
    "key_insights",
    "anomalies",
    "recommendations",
    "ai_powered",
    "prompt",
}


def test_generate_ai_insights_structure(sales_df):
    cleaned, _ = clean_data(sales_df)
    types = detect_column_types(cleaned)
    result = generate_ai_insights(cleaned, types)

    assert REQUIRED_KEYS <= set(result)
    assert isinstance(result["dataset_summary"], str) and result["dataset_summary"]
    assert len(result["key_insights"]) >= 1
    assert len(result["anomalies"]) >= 1
    assert len(result["recommendations"]) >= 1
    assert isinstance(result["prompt"], str) and "STRICT JSON" in result["prompt"]


def test_generate_ai_insights_works_on_text_only_frame():
    df = pd.DataFrame({"name": ["a", "b", "c"], "city": ["x", "y", "z"]})
    result = generate_ai_insights(df)
    assert REQUIRED_KEYS <= set(result)
    assert result["key_insights"]  # fallback must not be empty


def test_detect_dataset_type_sales_columns(sales_df):
    types = detect_column_types(sales_df)
    domain, description = detect_dataset_type(sales_df, types)
    assert domain == "sales"
    assert "sales" in description.lower()


def test_detect_dataset_type_general_when_no_signals():
    df = pd.DataFrame({"aaa": [1, 2, 3], "bbb": ["x", "y", "z"]})
    domain, _ = detect_dataset_type(df, detect_column_types(df))
    assert domain == "general"


def test_ai_powered_flag_reflects_env_only(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    df = pd.DataFrame({"Revenue": [1.0, 2.0, 3.0], "Region": ["a", "b", "c"]})
    result = generate_ai_insights(df, detect_column_types(df))
    assert result["ai_powered"] is False
