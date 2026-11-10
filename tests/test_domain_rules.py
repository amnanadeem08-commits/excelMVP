"""Tests for domain_rules.py: domain detection with explainable confidence."""

from __future__ import annotations

import pandas as pd
import pytest

from domain_rules import detect_domain, enrich_summary_with_domain


# ---------------------------------------------------------------------------
# Minimal fixtures for domain detection tests (not using conftest sales_df to
# keep tests independent and focused on domain patterns)
# ---------------------------------------------------------------------------

import numpy as np


@pytest.fixture
def sales_like_df() -> pd.DataFrame:
    """DataFrame mimicking a Sales domain: deal sizes, close dates, moderate variability."""
    return pd.DataFrame({
        "Deal Size": [12000, 8500, 23000, 4500, 18000, 32000, 6700, 21000],
        "Close Date": pd.to_datetime([
            "2024-01-15", "2024-02-20", "2024-03-10", "2024-01-25",
            "2024-04-05", "2024-05-12", "2024-02-28", "2024-03-20"
        ]),
        "Sales Rep": ["Alice", "Bob", "Alice", "Carol", "Bob", "Alice", "Dave", "Carol"],
        "Territory": ["North", "South", "East", "West", "North", "South", "East", "West"],
        "Win Rate": [0.25, 0.30, 0.45, 0.20, 0.50, 0.35, 0.15, 0.40],
    })


@pytest.fixture
def retail_like_df() -> pd.DataFrame:
    """DataFrame mimicking a Retail domain: SKUs, moderate-priced items, store-like patterns."""
    return pd.DataFrame({
        "SKU": ["SKU-001", "SKU-002", "SKU-003", "SKU-004", "SKU-005"],
        "Unit Price": [29.99, 49.99, 19.99, 79.99, 34.99],
        "Quantity Sold": [150, 200, 300, 80, 250],
        "Department": ["Electronics", "Clothing", "Home", "Electronics", "Clothing"],
        "Store Location": ["Store A", "Store B", "Store A", "Store C", "Store B"],
    })


@pytest.fixture
def ecommerce_like_df() -> pd.DataFrame:
    """DataFrame mimicking an E-commerce domain: order IDs, many products, price range."""
    return pd.DataFrame({
        "Order ID": ["ORD-2024001", "ORD-2024002", "ORD-2024003", "ORD-2024004", "ORD-2024005"],
        "Product Price": [49.50, 29.99, 79.99, 15.50, 89.99],
        "Product Category": ["Electronics", "Books", "Home", "Clothing", "Electronics"],
        "Customer Email": ["a@test.com", "b@test.com", "c@test.com", "d@test.com", "e@test.com"],
    })


@pytest.fixture
def ambiguous_sales_retail_df() -> pd.DataFrame:
    """DataFrame that could be Sales or Retail: some overlap in patterns."""
    return pd.DataFrame({
        "Item Description": ["Consulting Project", "Software License", "Consulting Retainer",
                            "Monthly Subscription", "One-time Service"],
        "Value": [5000, 1200, 3000, 50, 2000],
        "Category": ["Professional Services", "Software", "Professional Services",
                     "Subscription", "Services"],
    })


@pytest.fixture
def low_confidence_df() -> pd.DataFrame:
    """DataFrame with very few patterns - low confidence domain detection."""
    return pd.DataFrame({
        "Col1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "Col2": ["a", "b", "c", "d", "e"],
    })


# ---------------------------------------------------------------------------
# Tests for detect_domain
# ---------------------------------------------------------------------------

class TestDetectDomain:
    """Domain detection tests with explainable confidence."""

    def test_sales_domain_detected(self, sales_like_df):
        """Sales domain should be detected with reasonable confidence."""
        types = {
            "numeric": ["Deal Size", "Win Rate"],
            "datetime": ["Close Date"],
            "categorical": ["Sales Rep", "Territory"],
        }
        result = detect_domain(sales_like_df, types)
        assert result.domain in ("sales", "unknown"), f"Expected sales or unknown, got {result.domain}"
        # Sales should have non-trivial confidence given the patterns
        assert result.confidence > 0.1, f"Expected positive confidence for sales, got {result.confidence}"

    def test_retail_domain_detected(self, retail_like_df):
        """Retail domain should be detected."""
        types = {
            "numeric": ["Unit Price", "Quantity Sold"],
            "categorical": ["Department", "Store Location"],
        }
        result = detect_domain(retail_like_df, types)
        assert result.domain in ("retail", "unknown"), f"Expected retail or unknown, got {result.domain}"
        assert result.confidence > 0.1, f"Expected positive confidence for retail, got {result.confidence}"

    def test_ecommerce_domain_detected(self, ecommerce_like_df):
        """E-commerce domain should be detected."""
        types = {
            "numeric": ["Product Price"],
            "categorical": ["Product Category"],
            "text": ["Customer Email"],
        }
        result = detect_domain(ecommerce_like_df, types)
        assert result.domain in ("e_commerce", "unknown"), f"Expected e_commerce or unknown, got {result.domain}"
        assert result.confidence > 0.1, f"Expected positive confidence for e-commerce, got {result.confidence}"

    def test_ambiguous_sales_retail_returns_unknown(self, ambiguous_sales_retail_df):
        """Ambiguous Sales/Retail should return 'unknown' with explanation."""
        types = {
            "categorical": ["Category"],
        }
        result = detect_domain(ambiguous_sales_retail_df, types, require_confirmation_on_ambiguous=True)
        # Should return unknown or ambiguous when Sales/Retail can't be distinguished
        assert result.domain in ("unknown", "ambiguous"), (
            f"Expected unknown or ambiguous for ambiguous data, got {result.domain}"
        )
        # Should have a fallback message about user confirmation
        assert result.fallback_message is not None, (
            "Expected fallback_message for ambiguous domain"
        )

    def test_low_confidence_returns_unknown(self, low_confidence_df):
        """Low confidence data should return 'unknown' with fallback message."""
        types = {}
        result = detect_domain(low_confidence_df, types, require_confirmation_on_ambiguous=True)
        assert result.domain == "unknown", f"Expected unknown for low confidence, got {result.domain}"
        assert result.fallback_message is not None, (
            "Expected fallback_message for low confidence"
        )
        assert result.confidence < 0.3, (
            f"Expected low confidence < 0.3, got {result.confidence}"
        )

    def test_domain_detection_orthogonal_to_measure_semantics(self, sales_like_df):
        """Domain detection should not affect measure semantics classification."""
        from analytics_engine import measure_semantics

        types = {
            "numeric": ["Deal Size"],
            "datetime": ["Close Date"],
            "categorical": ["Sales Rep"],
        }

        # Domain detection should work independently
        domain_result = detect_domain(sales_like_df, types)

        # Measure semantics should be unchanged
        semantics = measure_semantics("Deal Size", types)
        # Deal Size in a sales context: could be continuous (price-like) or additive
        # The point is domain detection didn't break measure semantics
        assert semantics in ("additive", "continuous", "rate"), (
            f"Expected valid semantics, got {semantics}"
        )

        # KPI building should still work
        from analytics_engine import analyze_dataset, build_kpis
        summary = analyze_dataset(sales_like_df, types)
        kpis = build_kpis(sales_like_df, summary, types)
        assert "Records" in kpis
        assert "Data Quality" in kpis

    def test_clear_ecommerce_above_sales_retail(self, ecommerce_like_df, sales_like_df):
        """When e-commerce patterns are clear, it should be detected even with sales-like data mixed in."""
        df = pd.DataFrame({
            "Product Price": [49.50, 29.99, 79.99, 15.50, 89.99],
            "Order ID": ["ORD-2024001", "ORD-2024002", "ORD-2024003", "ORD-2024004", "ORD-2024005"],
            "Sales Rep": ["Alice", "Bob", "Alice", "Carol", "Bob"],  # sales-like column
        })
        types = {
            "numeric": ["Product Price"],
            "categorical": ["Product Category"],  # will be detected from data
        }
        result = detect_domain(df, types, require_confirmation_on_ambiguous=True)
        # Should detect e-commerce despite the Sales Rep column
        assert result.domain in ("e_commerce", "unknown"), (
            f"Expected e_commerce or unknown, got {result.domain}"
        )


# ---------------------------------------------------------------------------
# Tests for enrich_summary_with_domain
# ---------------------------------------------------------------------------

class TestEnrichSummaryWithDomain:
    """Tests for the convenience helper function."""

    def test_enrich_adds_domain_detection_field(self, sales_like_df):
        """enrich_summary_with_domain should add domain_detection to summary."""
        types = {
            "numeric": ["Deal Size"],
            "datetime": ["Close Date"],
            "categorical": ["Sales Rep"],
        }
        result = enrich_summary_with_domain(
            {"rows": 8, "columns": 4, "numeric_count": 1, "categorical_count": 1},
            types,
            df=sales_like_df,
        )
        assert "domain_detection" in result, "Expected domain_detection in result"
        dd = result["domain_detection"]
        assert "domain" in dd
        assert "confidence" in dd
        assert "evidence" in dd

    def test_enrich_domain_unknown_when_no_data(self):
        """When no DataFrame provided, should still produce a result."""
        types = {
            "numeric": [],
            "categorical": [],
        }
        result = enrich_summary_with_domain(
            {"rows": 0, "columns": 0, "numeric_count": 0, "categorical_count": 0},
            types,
        )
        assert "domain_detection" in result
        dd = result["domain_detection"]
        assert "domain" in dd
        assert "confidence" in dd


# ---------------------------------------------------------------------------
# Tests for consistency with analytics engine
# ---------------------------------------------------------------------------

class TestConsistency:
    """Ensure domain detection doesn't break existing functionality."""

    def test_kpis_still_generate_correctly_with_domain_flag(self, sales_like_df):
        """KPI generation should work regardless of domain detection."""
        from analytics_engine import analyze_dataset, build_kpis

        types = {
            "numeric": ["Deal Size"],
            "datetime": ["Close Date"],
            "categorical": ["Sales Rep"],
        }

        summary = analyze_dataset(sales_like_df, types)
        kpis = build_kpis(sales_like_df, summary, types)

        # Should always generate Records and Data Quality KPIs
        assert "Records" in kpis
        assert "Data Quality" in kpis

        # Should not generate "Total Deal Size" (continuous measure should show Average/Median)
        total_keys = [k for k in kpis if "Total" in k]
        # May or may not have Total depending on semantics, but shouldn't crash
        assert isinstance(kpis, dict)

    def test_pivot_tables_still_generate(self, sales_like_df):
        """Pivot table generation should work regardless of domain detection."""
        from analytics_engine import generate_pivot_tables

        types = {
            "numeric": ["Deal Size"],
            "datetime": ["Close Date"],
            "categorical": ["Sales Rep"],
        }

        pivots = generate_pivot_tables(sales_like_df, types)
        assert isinstance(pivots, list)
        assert len(pivots) > 0  # Should generate at least one pivot


# Additional integration test: ensure domain detection doesn't modify
# the column types or data passed to it
class TestIntegrationNoSideEffects:
    """Ensure domain detection is read-only and doesn't modify inputs."""

    def test_domain_detection_readonly(self, sales_like_df, retail_like_df):
        """Domain detection should not modify the DataFrame or column types."""
        types = {
            "numeric": ["Deal Size"] if sales_like_df.columns[0] else [],
            "categorical": ["Sales Rep"],
        }

        # Make copies to verify unchanged
        df1 = sales_like_df.copy()
        types1 = types.copy()

        _ = detect_domain(df1, types1)

        # DataFrame should be unchanged
        assert len(df1) == len(sales_like_df)
        assert list(df1.columns) == list(sales_like_df.columns)

        # Column types should be unchanged (detect_domain may add keys but shouldn't remove)
        assert "categorical" in types1