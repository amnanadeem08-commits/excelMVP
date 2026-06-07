"""AI insight layer.

Generates business-friendly insights, recommendations, and a plain-language
explanation of the dataset. Works fully offline with rule-based logic, and
optionally upgrades to an LLM if an API key is configured.

CUSTOMIZE / ENABLE AI:
- Set the ``OPENAI_API_KEY`` environment variable and install ``openai`` to
  enable LLM-written narratives. Without it, the rule-based fallback runs.
- Swap the provider in ``_llm_explain`` for Anthropic, Azure, Gemini, etc.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from analytics_engine import (
    analyze_dataset,
    categorical_dimensions,
    compute_growth,
    best_numeric_column,
    numeric_measures,
    top_categories,
)
from data_cleaning import detect_column_types


# CUSTOMIZE: keyword fingerprints used to guess the business domain of a file.
# The domain with the most column-name matches wins.
DATASET_TYPE_KEYWORDS: dict[str, list[str]] = {
    "sales": ["sales", "revenue", "order", "customer", "product", "quantity", "discount", "price", "region", "channel"],
    "finance": ["revenue", "expense", "cost", "profit", "budget", "account", "balance", "transaction", "invoice", "tax", "cash", "margin"],
    "hr": ["employee", "salary", "department", "hire", "attrition", "gender", "age", "performance", "manager", "tenure", "headcount", "leave"],
    "inventory": ["stock", "sku", "warehouse", "supplier", "reorder", "inventory", "units", "quantity", "category", "lead time"],
    "marketing": ["campaign", "clicks", "impressions", "ctr", "conversion", "spend", "leads", "channel", "roi", "engagement"],
}

DATASET_TYPE_LABELS: dict[str, str] = {
    "sales": "sales / retail performance data",
    "finance": "financial / accounting data",
    "hr": "human resources (HR) data",
    "inventory": "inventory / supply-chain data",
    "marketing": "marketing / campaign performance data",
    "general": "general business data",
}


def generate_insights(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]], pivots: list | None = None) -> list[str]:
    """Rule-based, business-friendly insights derived from the data."""
    insights: list[str] = []
    measures = numeric_measures(df, column_types)
    categorical = [
        col
        for col in column_types.get("categorical", []) + column_types.get("boolean", [])
        if col in df.columns and df[col].nunique(dropna=True) > 1
    ]

    insights.append(
        f"The dataset contains {summary['rows']:,} records across {summary['columns']:,} columns "
        f"with a {100 - summary['missing_pct']:.1f}% completeness score."
    )

    for cat in categorical[:3]:
        top = df[cat].astype(str).value_counts(dropna=False).head(5)
        if len(top) >= 2:
            concentration = top.iloc[0] / max(top.sum(), 1) * 100
            insights.append(
                f"{cat} is led by '{top.index[0]}', representing {concentration:.1f}% of the top five observed categories."
            )

    for measure in measures[:3]:
        series = df[measure].dropna()
        if series.empty:
            continue
        skew = series.skew()
        if abs(skew) > 1:
            direction = "right-skewed" if skew > 0 else "left-skewed"
            insights.append(f"{measure} is {direction}, so averages may be influenced by extreme values.")
        if series.std(ddof=0) and series.max() > series.mean() + 3 * series.std(ddof=0):
            insights.append(
                f"{measure} has unusually high peak values that deserve review for opportunities or data quality issues."
            )

    growth = compute_growth(df, column_types)
    if growth:
        direction = "increasing" if growth["growth_pct"] >= 0 else "declining"
        insights.append(
            f"{growth['measure']} is {direction} {abs(growth['growth_pct']):.1f}% overall "
            f"from {growth['start']} to {growth['end']}."
        )

    if isinstance(summary.get("correlations"), pd.DataFrame) and summary["correlations"].shape[0] >= 2:
        corr = summary["correlations"].where(lambda x: x.abs() < 1).stack().dropna()
        if not corr.empty:
            best_pair = corr.abs().idxmax()
            value = corr.loc[best_pair]
            insights.append(
                f"{best_pair[0]} and {best_pair[1]} show the strongest detected relationship with correlation {value:.2f}."
            )

    return insights[:10]


def generate_recommendations(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]], insights: list[str] | None = None) -> list[str]:
    """Actionable recommendations a client can use immediately."""
    recommendations: list[str] = []
    measures = numeric_measures(df, column_types)
    categorical = column_types.get("categorical", [])

    if summary["missing_pct"] > 5:
        recommendations.append(
            "Data quality warning: missing values exceed 5%, so source-system validation should be reviewed before executive reporting."
        )
    else:
        recommendations.append(
            "The dataset is clean enough for directional decision-making; continue monitoring missing values as new files arrive."
        )

    if measures and categorical:
        measure = measures[0]
        cat = categorical[0]
        grouped = df.groupby(cat)[measure].sum().sort_values(ascending=False)
        if len(grouped) >= 3:
            recommendations.append(
                f"Prioritize the top-performing {cat} segments for growth planning because they drive the largest share of {measure}."
            )
            recommendations.append(
                f"Investigate low-performing {cat} segments to separate fixable execution gaps from naturally smaller markets."
            )

    if column_types.get("datetime") and measures:
        recommendations.append(
            "Review trend charts monthly and compare recent movement against business events, campaigns, or operational changes."
        )

    if len(measures) >= 2:
        recommendations.append(
            "Use the strongest correlations as hypothesis generators, then validate with domain knowledge before making policy changes."
        )

    recommendations.append(
        "Export the cleaned workbook and pivot tables as a repeatable analytics pack for finance, operations, or leadership reviews."
    )
    return recommendations[:8]


def explain_dataset(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> str:
    """Explain the dataset in simple business language (one short paragraph)."""
    measures = numeric_measures(df, column_types)
    cats = column_types.get("categorical", [])
    dates = column_types.get("datetime", [])

    parts = [
        f"This dataset has {summary['rows']:,} rows and {summary['columns']:,} columns, "
        f"and is {100 - summary['missing_pct']:.0f}% complete."
    ]
    if measures:
        parts.append(f"It tracks {len(measures)} numeric measure(s) such as {', '.join(measures[:3])}.")
    if cats:
        parts.append(f"Records are organized into segments like {', '.join(cats[:3])}.")
    if dates:
        parts.append("Because it includes dates, trends over time can be analyzed.")

    top = top_categories(df, column_types)
    if top is not None and not top["ranking"].empty:
        leader = top["ranking"].index[0]
        parts.append(f"The leading {top['dimension']} by {top['measure']} is '{leader}'.")

    growth = compute_growth(df, column_types)
    if growth:
        trend = "grown" if growth["growth_pct"] >= 0 else "declined"
        parts.append(f"Overall, {growth['measure']} has {trend} {abs(growth['growth_pct']):.0f}% across the period.")

    return " ".join(parts)


def ai_summary(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> dict:
    """Single entry point used by the UI.

    Returns the plain-language explanation plus insights and recommendations.
    Uses an LLM when configured, otherwise falls back to rule-based output.
    """
    explanation = _llm_explain(df, summary, column_types) or explain_dataset(df, summary, column_types)
    insights = generate_insights(df, summary, column_types)
    recommendations = generate_recommendations(df, summary, column_types, insights)
    return {
        "explanation": explanation,
        "insights": insights,
        "recommendations": recommendations,
        "ai_powered": bool(os.getenv("OPENAI_API_KEY")),
    }


# ===========================================================================
# AI Insights Layer (the "brain")
# ===========================================================================
def detect_dataset_type(df: pd.DataFrame, column_types: dict[str, list[str]]) -> tuple[str, str]:
    """Guess the business domain of a dataset and describe it in one sentence.

    Returns ``(type_key, human_description)`` where ``type_key`` is one of
    sales / finance / hr / inventory / marketing / general.
    """
    columns_lower = [str(c).lower() for c in df.columns]
    scores: dict[str, int] = {}
    for domain, keywords in DATASET_TYPE_KEYWORDS.items():
        scores[domain] = sum(any(kw in col for col in columns_lower) for kw in keywords)

    best_domain = max(scores, key=scores.get) if scores else "general"
    if not scores or scores[best_domain] < 2:
        best_domain = "general"

    # Build a friendly description using a few representative fields.
    cats = column_types.get("categorical", [])
    measures = numeric_measures(df, column_types) or column_types.get("currency", [])
    highlight = [c for c in (cats[:2] + measures[:2]) if c][:3]
    fields = ", ".join(highlight) if highlight else "several descriptive fields"
    description = f"This appears to be {DATASET_TYPE_LABELS[best_domain]} with {fields} fields."
    return best_domain, description


def _performers(df: pd.DataFrame, column_types: dict[str, list[str]]) -> dict | None:
    """Identify the best and worst performing category by the primary metric."""
    measure = best_numeric_column(df, column_types)
    cats = categorical_dimensions(df, column_types)
    if measure is None or not cats:
        return None
    cat = cats[0]
    grouped = df.groupby(cat)[measure].sum().sort_values(ascending=False)
    if grouped.empty:
        return None
    total = float(grouped.sum())
    top_name = grouped.index[0]
    worst_name = grouped.index[-1]
    top_share = (float(grouped.iloc[0]) / total * 100) if total else 0.0
    return {
        "dimension": cat,
        "measure": measure,
        "top": str(top_name),
        "top_value": float(grouped.iloc[0]),
        "top_share": round(top_share, 1),
        "worst": str(worst_name),
        "worst_value": float(grouped.iloc[-1]),
        "count": int(len(grouped)),
    }


def detect_anomalies(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[str]:
    """Detect unusual spikes/drops, abnormal values, and missing-data patterns.

    Uses simple, explainable statistics (no heavy ML): deviation from the
    average trend over time, IQR-based outliers, and high missing rates.
    """
    anomalies: list[str] = []
    measures = numeric_measures(df, column_types)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

    # 1. Time-based spikes/drops vs. the average monthly trend.
    if measures and date_cols:
        measure = best_numeric_column(df, column_types) or measures[0]
        monthly = (
            df.assign(_month=pd.to_datetime(df[date_cols[0]], errors="coerce").dt.to_period("M"))
            .dropna(subset=["_month"])
            .groupby("_month")[measure]
            .sum()
            .sort_index()
        )
        if len(monthly) >= 3:
            avg = float(monthly.mean())
            if avg:
                deviations = (monthly - avg) / abs(avg) * 100
                for period, dev in deviations.items():
                    if abs(dev) >= 30:
                        label = period.strftime("%B %Y")
                        if dev < 0:
                            anomalies.append(f"{measure} dropped by {abs(dev):.0f}% in {label} compared to the average trend.")
                        else:
                            anomalies.append(f"{measure} spiked by {dev:.0f}% in {label} compared to the average trend.")

    # 2. Abnormal individual values (IQR outliers) in numeric columns.
    for measure in measures[:4]:
        series = df[measure].dropna()
        if len(series) < 8:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = int(((series < lower) | (series > upper)).sum())
        if outliers and outliers / len(series) <= 0.15:
            anomalies.append(
                f"{measure} has {outliers} abnormal value(s) outside the expected range "
                f"({lower:,.0f} to {upper:,.0f}) that are worth verifying."
            )

    # 3. Missing-data patterns.
    missing = df.isna().mean().sort_values(ascending=False)
    for col, ratio in missing.items():
        if ratio >= 0.2:
            anomalies.append(f"Column '{col}' is missing {ratio * 100:.0f}% of its values, which may bias any analysis using it.")

    if not anomalies:
        anomalies.append("No significant spikes, drops, or abnormal values were detected; the data looks stable.")
    return anomalies[:8]


def _build_dataset_summary(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> dict:
    """Build the compact, structured summary that is fed to the LLM.

    Includes shape, column names, basic stats (mean/sum/min/max), and top
    categories — exactly the context the AI needs to reason about the data.
    """
    measures = numeric_measures(df, column_types)
    stats: dict[str, dict[str, float]] = {}
    for measure in measures[:8]:
        series = df[measure].dropna()
        if series.empty:
            continue
        stats[measure] = {
            "sum": round(float(series.sum()), 2),
            "mean": round(float(series.mean()), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
        }

    top_cats: dict[str, dict] = {}
    measure = best_numeric_column(df, column_types)
    for cat in categorical_dimensions(df, column_types)[:3]:
        if measure:
            ranking = df.groupby(cat)[measure].sum().sort_values(ascending=False).head(5)
        else:
            ranking = df[cat].value_counts().head(5)
        top_cats[cat] = {str(k): round(float(v), 2) for k, v in ranking.items()}

    return {
        "rows": summary["rows"],
        "columns": summary["columns"],
        "column_names": list(df.columns),
        "primary_metric": measure,
        "stats": stats,
        "top_categories": top_cats,
    }


def _build_prompt(dataset_type: str, dataset_desc: str, structured_summary: dict) -> str:
    """Convert the structured summary into an LLM prompt."""
    return (
        "You are a senior business analyst. Analyze the dataset summary below and respond with "
        "concise, client-friendly business intelligence.\n\n"
        f"Detected dataset type: {dataset_type} ({dataset_desc})\n"
        f"Dataset facts (JSON):\n{json.dumps(structured_summary, default=str, indent=2)}\n\n"
        "Return STRICT JSON with these keys:\n"
        '  "dataset_summary": a 2-3 sentence plain-language description,\n'
        '  "key_insights": array of 3-5 short insight strings,\n'
        '  "anomalies": array of 1-4 problem/anomaly strings,\n'
        '  "recommendations": array of 3-5 actionable recommendation strings.\n'
        "Do not include any text outside the JSON object."
    )


def generate_ai_insights(df: pd.DataFrame, column_types: dict[str, list[str]] | None = None) -> dict:
    """Convert cleaned data into structured, human-readable business insights.

    This is the main entry point for the AI Insights Layer.

    Pipeline:
      1. Build a dataset summary using pandas (shape, columns, stats, top cats).
      2. Detect the dataset type and convert the summary into an LLM prompt.
      3. Send the prompt to an LLM (OpenAI/Claude) when configured.
      4. Return a structured result. Falls back to a rule-based engine so it
         works offline with any Excel dataset.

    Returns a dict with keys:
      ``dataset_type``, ``dataset_summary``, ``key_insights``,
      ``anomalies``, ``recommendations``, ``ai_powered``, ``prompt``.
    """
    if column_types is None:
        column_types = detect_column_types(df)

    summary = analyze_dataset(df, column_types)
    dataset_type, dataset_desc = detect_dataset_type(df, column_types)
    structured_summary = _build_dataset_summary(df, summary, column_types)
    prompt = _build_prompt(dataset_type, dataset_desc, structured_summary)

    # Rule-based baseline (always available, used as fallback).
    rule_based = {
        "dataset_summary": f"{dataset_desc} {explain_dataset(df, summary, column_types)}",
        "key_insights": _rule_based_key_insights(df, summary, column_types),
        "anomalies": detect_anomalies(df, column_types),
        "recommendations": _rule_based_recommendations(df, summary, column_types),
    }

    result = _llm_structured(prompt) or rule_based
    # Always keep our deterministic anomaly scan even if the LLM omits it.
    if not result.get("anomalies"):
        result["anomalies"] = rule_based["anomalies"]

    return {
        "dataset_type": dataset_type,
        "dataset_summary": result["dataset_summary"],
        "key_insights": result["key_insights"],
        "anomalies": result["anomalies"],
        "recommendations": result["recommendations"],
        "ai_powered": bool(os.getenv("OPENAI_API_KEY")),
        "prompt": prompt,
    }


def _rule_based_key_insights(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> list[str]:
    """Top performer, worst performer, trend, and key patterns (no LLM)."""
    insights: list[str] = []
    performers = _performers(df, column_types)
    if performers:
        insights.append(
            f"Top performer: '{performers['top']}' leads {performers['dimension']} by {performers['measure']}, "
            f"contributing {performers['top_share']:.0f}% of the total."
        )
        if performers["count"] >= 3:
            insights.append(
                f"Worst performer: '{performers['worst']}' is the weakest {performers['dimension']} by {performers['measure']} "
                "and may need attention or repositioning."
            )

    growth = compute_growth(df, column_types)
    if growth:
        direction = "growth" if growth["growth_pct"] >= 0 else "decline"
        insights.append(
            f"Trend: {growth['measure']} shows a {abs(growth['growth_pct']):.0f}% {direction} "
            f"from {growth['start']} to {growth['end']} ({growth['periods']} periods)."
        )

    # Reuse the existing statistical insight engine for extra patterns.
    for extra in generate_insights(df, summary, column_types)[1:4]:
        insights.append(extra)

    return insights[:6] or ["The dataset is well structured but does not contain enough numeric detail for deep performance insights."]


def _rule_based_recommendations(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> list[str]:
    """Actionable recommendations, led by a revenue-focused suggestion."""
    recommendations: list[str] = []
    performers = _performers(df, column_types)
    if performers:
        recommendations.append(
            f"Focus marketing and inventory on '{performers['top']}' as it contributes "
            f"{performers['top_share']:.0f}% of total {performers['measure']}."
        )
        if performers["count"] >= 3:
            recommendations.append(
                f"Review or reposition '{performers['worst']}' - the weakest {performers['dimension']} - "
                "to recover lost revenue or reallocate resources."
            )

    recommendations.extend(generate_recommendations(df, summary, column_types))
    # De-duplicate while preserving order.
    seen, unique = set(), []
    for rec in recommendations:
        if rec not in seen:
            seen.add(rec)
            unique.append(rec)
    return unique[:5]


def _llm_structured(prompt: str) -> dict | None:
    """Optional LLM call returning the 4 structured sections as a dict.

    Activates only when ``OPENAI_API_KEY`` is set and ``openai`` is installed.
    Never breaks the app: any error returns ``None`` (rule-based fallback).

    CUSTOMIZE: To use Anthropic Claude instead, swap this body for the
    ``anthropic`` client and parse the JSON from ``message.content``.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a senior business analyst. Always respond with strict JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return {
            "dataset_summary": str(data.get("dataset_summary", "")).strip(),
            "key_insights": [str(x) for x in data.get("key_insights", []) if str(x).strip()],
            "anomalies": [str(x) for x in data.get("anomalies", []) if str(x).strip()],
            "recommendations": [str(x) for x in data.get("recommendations", []) if str(x).strip()],
        }
    except Exception:
        return None


def _llm_explain(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> str | None:
    """Optional LLM-written explanation. Returns ``None`` if not configured.

    CUSTOMIZE: This is a safe placeholder. It only activates when both the
    ``openai`` package and an ``OPENAI_API_KEY`` are available, and it never
    breaks the app if the call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        facts = explain_dataset(df, summary, column_types)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a business analyst. Explain data clearly for a non-technical client in 3-4 sentences.",
                },
                {"role": "user", "content": f"Summarize this dataset for a client report:\n{facts}"},
            ],
            temperature=0.3,
            max_tokens=220,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None
