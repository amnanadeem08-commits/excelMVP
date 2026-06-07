"""Export system.

Produces client deliverables from the analyzed data:
- Cleaned dataset as Excel or CSV.
- A multi-sheet Excel summary report (overview, KPIs, insights, pivots).
- Chart PNG images.
- Branded PDF report and PowerPoint deck.

CUSTOMIZE:
- Rebrand the PDF/PPT cover text and colors in the theme blocks below.
- Add or remove summary sheets in ``export_summary_report``.
"""

from __future__ import annotations

import html
import tempfile
from io import BytesIO
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ---------------------------------------------------------------------------
# Spreadsheet exports
# ---------------------------------------------------------------------------
def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """Export a DataFrame to CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel(df: pd.DataFrame, pivots: list[Any] | None = None) -> bytes:
    """Export the cleaned dataset (and optional pivots) to an Excel workbook."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cleaned Data")
        for pivot in pivots or []:
            sheet_name = pivot.title[:31].replace("/", "-").replace("\\", "-")
            pivot.data.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def export_summary_report(
    summary: dict,
    cleaning_report: dict,
    kpis: dict[str, dict[str, str]],
    insights: list[str],
    recommendations: list[str],
    pivots: list[Any] | None = None,
) -> bytes:
    """Export a structured, multi-sheet Excel summary report.

    Sheets: Overview, KPIs, Cleaning Report, Insights, Recommendations, and
    one sheet per pivot table.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        overview = pd.DataFrame(
            {
                "Metric": ["Rows", "Columns", "Missing %", "Completeness %", "Numeric Fields", "Categorical Fields", "Datetime Fields"],
                "Value": [
                    summary["rows"],
                    summary["columns"],
                    summary["missing_pct"],
                    round(100 - summary["missing_pct"], 1),
                    summary["numeric_count"],
                    summary["categorical_count"],
                    summary["datetime_count"],
                ],
            }
        )
        overview.to_excel(writer, index=False, sheet_name="Overview")

        kpi_df = pd.DataFrame(
            [{"KPI": label, "Value": metric["value"], "Detail": metric.get("note", "")} for label, metric in kpis.items()]
        )
        kpi_df.to_excel(writer, index=False, sheet_name="KPIs")

        pd.DataFrame([cleaning_report]).T.reset_index().rename(
            columns={"index": "Step", 0: "Value"}
        ).to_excel(writer, index=False, sheet_name="Cleaning Report")

        pd.DataFrame({"Insight": insights}).to_excel(writer, index=False, sheet_name="Insights")
        pd.DataFrame({"Recommendation": recommendations}).to_excel(writer, index=False, sheet_name="Recommendations")

        for pivot in pivots or []:
            sheet_name = pivot.title[:31].replace("/", "-").replace("\\", "-")
            pivot.data.to_excel(writer, index=False, sheet_name=sheet_name)

    return output.getvalue()


# ---------------------------------------------------------------------------
# Chart images
# ---------------------------------------------------------------------------
def export_chart_images(charts: list[Any]) -> list[dict[str, Any]]:
    """Render Plotly charts to high-resolution PNG bytes (requires kaleido)."""
    exported = []
    for chart in charts:
        try:
            image_bytes = chart.figure.to_image(format="png", width=1400, height=820, scale=2)
            temp = tempfile.NamedTemporaryFile(prefix="excel_ai_chart_", suffix=".png", delete=False)
            temp.write(image_bytes)
            temp.close()
            exported.append({"title": chart.title, "bytes": image_bytes, "path": temp.name})
        except Exception:
            continue
    return exported


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------
def make_custom_pdf_report(
    summary: dict,
    cleaning_report: dict,
    insights: list[str],
    recommendations: list[str],
    pivots: list[Any],
    charts: list[Any],
    include_tables: bool,
    include_charts: bool,
) -> bytes:
    """Build a branded, client-ready PDF report."""
    chart_images = export_chart_images(charts) if include_charts else []
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles["Title"].fontSize = 24
    styles["Title"].textColor = colors.HexColor("#111827")
    styles["Heading1"].textColor = colors.HexColor("#111827")
    styles["Heading2"].textColor = colors.HexColor("#1F2937")
    styles["BodyText"].fontSize = 9.5
    styles["BodyText"].leading = 13
    story = [
        _pdf_cover_block("Excel AI Analytics Assistant", "Client-ready business intelligence report"),
        Spacer(1, 12),
        _pdf_kpi_cards(summary),
        Spacer(1, 14),
        Paragraph("Executive Summary", styles["Heading1"]),
    ]

    for insight in insights[:5]:
        story.append(Paragraph(f"- {html.escape(insight)}", styles["BodyText"]))
        story.append(Spacer(1, 4))

    story.extend([
        Spacer(1, 10),
        Paragraph("Cleaning Report", styles["Heading2"]),
        _styled_table([[key.replace("_", " ").title(), str(value)] for key, value in cleaning_report.items()]),
        Spacer(1, 12),
        Paragraph("Recommendations", styles["Heading2"]),
    ])
    for recommendation in recommendations[:8]:
        story.append(Paragraph(f"- {html.escape(recommendation)}", styles["BodyText"]))
        story.append(Spacer(1, 4))

    if include_tables and pivots:
        story.append(PageBreak())
        story.append(Paragraph("Pivot Tables", styles["Heading1"]))
        for pivot in pivots[:6]:
            story.append(Spacer(1, 8))
            story.append(Paragraph(html.escape(pivot.title), styles["Heading2"]))
            story.append(_dataframe_pdf_table(pivot.data.head(12)))

    if include_charts and chart_images:
        story.append(PageBreak())
        story.append(Paragraph("Visual Analytics", styles["Heading1"]))
        for idx, chart_image in enumerate(chart_images):
            if idx:
                story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(Paragraph(html.escape(chart_image["title"]), styles["Heading2"]))
            story.append(RLImage(BytesIO(chart_image["bytes"]), width=7.2 * inch, height=4.22 * inch))

    doc.build(story)
    return buffer.getvalue()


def _pdf_cover_block(title: str, subtitle: str) -> Table:
    table = Table(
        [[Paragraph(
            f"<font color='white' size='18'><b>{html.escape(title)}</b></font><br/>"
            f"<font color='#CBD5E1' size='10'>{html.escape(subtitle)}</font>",
            getSampleStyleSheet()["BodyText"],
        )]],
        colWidths=[7.25 * inch],
        rowHeights=[0.85 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 13),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
            ]
        )
    )
    return table


def _pdf_kpi_cards(summary: dict) -> Table:
    data = [[
        _kpi_card_para("Records", f"{summary['rows']:,}"),
        _kpi_card_para("Columns", f"{summary['columns']:,}"),
        _kpi_card_para("Completeness", f"{100 - summary['missing_pct']:.1f}%"),
        _kpi_card_para("Measures", f"{summary['numeric_count']:,}"),
    ]]
    table = Table(data, colWidths=[1.72 * inch] * 4, rowHeights=[0.72 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5EAF3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _kpi_card_para(label: str, value: str) -> Paragraph:
    return Paragraph(
        f"<font size='7' color='#64748B'><b>{html.escape(label.upper())}</b></font><br/>"
        f"<font size='16' color='#111827'><b>{html.escape(value)}</b></font>",
        getSampleStyleSheet()["BodyText"],
    )


def _dataframe_pdf_table(df: pd.DataFrame) -> Table:
    limited = df.head(12).iloc[:, :6].copy()
    rows = [[str(col)[:24] for col in limited.columns]]
    for _, row in limited.iterrows():
        rows.append([str(value)[:34] for value in row])
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF4FF")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _styled_table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT", colWidths=[180, 300])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF4FF")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D5DD")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------
# PowerPoint deck
# ---------------------------------------------------------------------------
def make_ppt_report(
    summary: dict,
    cleaning_report: dict,
    insights: list[str],
    recommendations: list[str],
    pivots: list[Any],
    charts: list[Any],
    include_tables: bool,
    include_charts: bool,
) -> bytes:
    """Build a branded, client-ready PowerPoint deck."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    chart_images = export_chart_images(charts) if include_charts else []
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    theme = {
        "ink": RGBColor(17, 24, 39),
        "muted": RGBColor(100, 116, 139),
        "blue": RGBColor(37, 99, 235),
        "cyan": RGBColor(8, 145, 178),
        "green": RGBColor(5, 150, 105),
        "amber": RGBColor(217, 119, 6),
        "panel": RGBColor(248, 250, 252),
        "line": RGBColor(226, 232, 240),
        "navy": RGBColor(15, 23, 42),
    }

    def set_bg(slide, color=RGBColor(255, 255, 255)):
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = color

    def add_title(slide, title: str, subtitle: str = ""):
        set_bg(slide)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = theme["blue"]
        bar.line.fill.background()
        box = slide.shapes.add_textbox(Inches(0.55), Inches(0.28), Inches(12.2), Inches(0.55))
        p = box.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = theme["ink"]
        if subtitle:
            sub = slide.shapes.add_textbox(Inches(0.58), Inches(0.92), Inches(11.8), Inches(0.35))
            sp = sub.text_frame.paragraphs[0]
            sp.text = subtitle
            sp.font.size = Pt(11)
            sp.font.color.rgb = theme["muted"]

    def add_card(slide, x, y, w, h, label: str, value: str, accent):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(255, 255, 255)
        shape.line.color.rgb = theme["line"]
        stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Inches(0.08), h)
        stripe.fill.solid()
        stripe.fill.fore_color.rgb = accent
        stripe.line.fill.background()
        label_box = slide.shapes.add_textbox(x + Inches(0.22), y + Inches(0.16), w - Inches(0.35), Inches(0.22))
        lp = label_box.text_frame.paragraphs[0]
        lp.text = label.upper()
        lp.font.size = Pt(8)
        lp.font.bold = True
        lp.font.color.rgb = theme["muted"]
        value_box = slide.shapes.add_textbox(x + Inches(0.22), y + Inches(0.45), w - Inches(0.35), Inches(0.42))
        vp = value_box.text_frame.paragraphs[0]
        vp.text = value
        vp.font.size = Pt(18)
        vp.font.bold = True
        vp.font.color.rgb = theme["ink"]

    def add_bullets(slide, x, y, w, h, title: str, items: list[str]):
        panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        panel.fill.solid()
        panel.fill.fore_color.rgb = RGBColor(248, 250, 252)
        panel.line.color.rgb = theme["line"]
        title_box = slide.shapes.add_textbox(x, y, w, Inches(0.35))
        tp = title_box.text_frame.paragraphs[0]
        tp.text = title
        tp.font.bold = True
        tp.font.size = Pt(15)
        tp.font.color.rgb = theme["ink"]
        title_box.left = x + Inches(0.25)
        title_box.top = y + Inches(0.18)
        title_box.width = w - Inches(0.5)
        body = slide.shapes.add_textbox(x + Inches(0.25), y + Inches(0.65), w - Inches(0.5), h - Inches(0.8))
        tf = body.text_frame
        tf.word_wrap = True
        for idx, item in enumerate(items[:7]):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.text = item
            p.level = 0
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(45, 55, 72)

    def add_df_table(slide, df: pd.DataFrame, x, y, w, h):
        table_df = df.head(8).iloc[:, :5].copy()
        rows, cols = table_df.shape[0] + 1, max(table_df.shape[1], 1)
        table = slide.shapes.add_table(rows, cols, x, y, w, h).table
        for col_idx, col in enumerate(table_df.columns):
            cell = table.cell(0, col_idx)
            cell.text = str(col)[:28]
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(239, 246, 255)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.bold = True
                paragraph.font.size = Pt(8)
                paragraph.font.color.rgb = theme["ink"]
        for row_idx, (_, row) in enumerate(table_df.iterrows(), start=1):
            for col_idx, value in enumerate(row):
                cell = table.cell(row_idx, col_idx)
                cell.text = str(value)[:40]
                for paragraph in cell.text_frame.paragraphs:
                    paragraph.font.size = Pt(7)
                    paragraph.alignment = PP_ALIGN.LEFT
                    paragraph.font.color.rgb = RGBColor(51, 65, 85)

    title_slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(title_slide, theme["navy"])
    accent = title_slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    accent.fill.solid()
    accent.fill.fore_color.rgb = theme["navy"]
    accent.line.fill.background()
    ribbon = title_slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
    ribbon.fill.solid()
    ribbon.fill.fore_color.rgb = theme["blue"]
    ribbon.line.fill.background()
    title_box = title_slide.shapes.add_textbox(Inches(0.85), Inches(0.85), Inches(8.8), Inches(1.2))
    p = title_box.text_frame.paragraphs[0]
    p.text = "Excel AI Analytics Assistant"
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    sub_box = title_slide.shapes.add_textbox(Inches(0.9), Inches(1.95), Inches(7.5), Inches(0.5))
    sp = sub_box.text_frame.paragraphs[0]
    sp.text = "Client-ready analytics export with automated insights, pivots, and dashboard visuals"
    sp.font.size = Pt(14)
    sp.font.color.rgb = RGBColor(203, 213, 225)
    kpi_values = [
        ("Records", f"{summary['rows']:,}", theme["blue"]),
        ("Columns", f"{summary['columns']:,}", theme["cyan"]),
        ("Completeness", f"{100 - summary['missing_pct']:.1f}%", theme["green"]),
        ("Measures", f"{summary['numeric_count']:,}", theme["amber"]),
    ]
    for idx, (label, value, color) in enumerate(kpi_values):
        add_card(title_slide, Inches(0.9 + idx * 3.05), Inches(3.05), Inches(2.65), Inches(1.15), label, value, color)
    add_bullets(
        title_slide,
        Inches(0.9),
        Inches(4.75),
        Inches(5.85),
        Inches(1.75),
        "Executive highlights",
        [
            f"{summary['rows']:,} records analyzed across {summary['columns']:,} columns.",
            f"Data completeness score: {100 - summary['missing_pct']:.1f}%.",
            f"{summary['numeric_count']:,} numeric fields and {summary['categorical_count']:,} segment fields detected.",
        ],
    )
    add_bullets(title_slide, Inches(7.05), Inches(4.75), Inches(5.45), Inches(1.75), "AI recommendations", recommendations)

    insight_slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(insight_slide, "AI Insights", "Business-friendly findings generated from the uploaded dataset")
    for idx, (label, value, color) in enumerate(kpi_values):
        add_card(insight_slide, Inches(0.65 + idx * 3.05), Inches(1.35), Inches(2.65), Inches(1.0), label, value, color)
    add_bullets(insight_slide, Inches(0.75), Inches(2.7), Inches(5.75), Inches(3.95), "Detected insights", insights)
    add_bullets(insight_slide, Inches(6.75), Inches(2.7), Inches(5.75), Inches(3.95), "Recommended actions", recommendations)

    if include_tables:
        for pivot in pivots:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            add_title(slide, pivot.title, "Top rows from the automatically generated pivot table")
            add_df_table(slide, pivot.data, Inches(0.65), Inches(1.35), Inches(12.1), Inches(5.55))

    if include_charts:
        for chart_image in chart_images:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            add_title(slide, chart_image["title"], "Dashboard-matched chart exported at high resolution")
            frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.68), Inches(1.23), Inches(11.95), Inches(5.85))
            frame.fill.solid()
            frame.fill.fore_color.rgb = RGBColor(255, 255, 255)
            frame.line.color.rgb = theme["line"]
            slide.shapes.add_picture(BytesIO(chart_image["bytes"]), Inches(2.05), Inches(1.55), height=Inches(5.22))

    output = BytesIO()
    prs.save(output)
    return output.getvalue()
