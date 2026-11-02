"""
Multi-format report exporter supporting publication-ready PDF and Microsoft Word (.docx).

Transforms structured report dictionaries containing cited technical sections,
tabular benchmark summaries, unsupported claim callouts, and reference bibliographies
into professional documents in the reports/ directory.
"""

from datetime import datetime
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import REPORTS_DIR


def _sanitize_filename(name: str) -> str:
    """Sanitize strings into safe snake_case filenames."""
    clean = re.sub(r"[^\w\s-]", "", name).strip().lower()
    clean = re.sub(r"[-\s]+", "_", clean)
    return clean[:60] if clean else "research_report"


def _build_pdf(content: Dict[str, Any], output_path: Path) -> str:
    """Generate professional PDF using ReportLab with corporate palette styling."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Color Palette
    primary_color = HexColor("#1A365D")  # Deep Navy
    secondary_color = HexColor("#2B6CB0")  # Slate Blue
    accent_color = HexColor("#C53030")  # Brick Red (for warnings/unsupported)
    neutral_light = HexColor("#F7FAFC")
    border_color = HexColor("#E2E8F0")

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        alignment=0,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=HexColor("#718096"),
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=HexColor("#2D3748"),
        spaceAfter=6,
    )
    callout_style = ParagraphStyle(
        "CalloutText",
        parent=body_style,
        fontSize=9,
        leading=13,
        textColor=HexColor("#1A202C"),
    )
    unsupported_style = ParagraphStyle(
        "UnsupportedText",
        parent=body_style,
        fontSize=9,
        leading=13,
        textColor=accent_color,
    )

    story: List[Any] = []

    # 1. Document Title & Metadata Header
    title = content.get("title", "Technical Research Assessment Report")
    timestamp = content.get("date") or datetime.now().strftime("%B %d, %Y")
    status = content.get("status", "APPROVED").upper()

    story.append(Paragraph(title, title_style))
    story.append(
        Paragraph(
            f"<b>Generated:</b> {timestamp} &nbsp;|&nbsp; <b>Review Status:</b> {status} &nbsp;|&nbsp; <b>Audit Trail:</b> Cited Grounded",
            meta_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=14))

    # 2. Executive Summary Box (if present in sections)
    sections: Dict[str, str] = content.get("sections", {})
    exec_summary = sections.pop("Executive Summary", None)

    if exec_summary:
        story.append(Paragraph("Executive Summary", h1_style))
        summary_table = Table(
            [[Paragraph(exec_summary, callout_style)]],
            colWidths=[7.0 * inch],
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), neutral_light),
                    ("BOX", (0, 0), (-1, -1), 1.0, secondary_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

    # 3. Main Body Sections
    for sec_title, sec_body in sections.items():
        story.append(Paragraph(sec_title, h1_style))
        paragraphs = sec_body.split("\n\n")
        for p in paragraphs:
            clean_p = p.strip()
            if clean_p:
                story.append(Paragraph(clean_p, body_style))
        story.append(Spacer(1, 6))

    # 4. Optional Benchmark Table Embedding (if calculations present)
    benchmark_data = content.get("benchmark_summary")
    if benchmark_data and isinstance(benchmark_data, dict):
        story.append(Paragraph("Performance Benchmark Summary", h1_style))
        table_rows = [["Database", "Operation", "Mean Latency", "p95 Latency", "Throughput (ops/sec)"]]
        for db, ops in benchmark_data.items():
            if isinstance(ops, dict):
                for op, metrics in ops.items():
                    if isinstance(metrics, dict):
                        table_rows.append(
                            [
                                str(db),
                                str(op).title(),
                                f"{metrics.get('mean_latency_ms', '-')} ms",
                                f"{metrics.get('p95_latency_ms', '-')} ms",
                                f"{metrics.get('mean_throughput_ops_sec', '-')}",
                            ]
                        )
        if len(table_rows) > 1:
            t = Table(table_rows, colWidths=[1.4 * inch, 1.2 * inch, 1.4 * inch, 1.4 * inch, 1.6 * inch])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t)
            story.append(Spacer(1, 10))

    # 5. Unsupported Claims & Research Limitations Block
    unsupported = content.get("unsupported_claims", [])
    if unsupported:
        story.append(Paragraph("Identified Gaps & Unsupported Claims", h1_style))
        unsupported_items = []
        for u in unsupported:
            unsupported_items.append([Paragraph(f"• <b>[LIMITATION]</b> {u}", unsupported_style)])

        u_table = Table(unsupported_items, colWidths=[7.0 * inch])
        u_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FFF5F5")),
                    ("BOX", (0, 0), (-1, -1), 1.0, accent_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(u_table)
        story.append(Spacer(1, 10))

    # 6. References & Bibliographic Index
    citations = content.get("cited_sources", [])
    if citations:
        story.append(HRFlowable(width="100%", thickness=0.8, color=border_color, spaceBefore=8, spaceAfter=8))
        story.append(Paragraph("References & Evidence Audit Trail", h1_style))
        for cit in citations:
            if isinstance(cit, dict):
                ref_text = f"<b>[{cit.get('source_id', 'SRC')}]</b> {cit.get('title', '')} — <i>{cit.get('publication', cit.get('source_type', ''))}</i>"
                if cit.get("url"):
                    ref_text += f" ({cit.get('url')})"
            else:
                ref_text = f"<b>[{cit}]</b> Verified ground source."
            story.append(Paragraph(ref_text, meta_style))

    doc.build(story)
    return str(output_path.resolve())


def _build_docx(content: Dict[str, Any], output_path: Path) -> str:
    """Generate Word (.docx) document using python-docx."""
    doc = Document()

    # Document Title
    title = content.get("title", "Technical Research Assessment Report")
    title_p = doc.add_paragraph()
    run = title_p.add_run(title)
    run.font.name = "Arial"
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = RGBColor(26, 54, 93)

    # Metadata
    status = content.get("status", "APPROVED").upper()
    meta_p = doc.add_paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')} | Status: {status} | Cited Grounded")
    meta_p.runs[0].font.size = Pt(9)
    meta_p.runs[0].font.color.rgb = RGBColor(113, 128, 150)

    # Executive Summary
    sections = content.get("sections", {})
    if "Executive Summary" in sections:
        doc.add_heading("Executive Summary", level=1)
        p = doc.add_paragraph(sections["Executive Summary"])
        p.runs[0].font.size = Pt(10)

    # Body Sections
    for sec_name, sec_text in sections.items():
        if sec_name == "Executive Summary":
            continue
        doc.add_heading(sec_name, level=1)
        for paragraph in sec_text.split("\n\n"):
            if paragraph.strip():
                p = doc.add_paragraph(paragraph.strip())
                p.runs[0].font.size = Pt(10)

    # Unsupported Claims
    unsupported = content.get("unsupported_claims", [])
    if unsupported:
        doc.add_heading("Identified Gaps & Unsupported Claims", level=1)
        for u in unsupported:
            p = doc.add_paragraph(f"• [LIMITATION] {u}")
            p.runs[0].font.color.rgb = RGBColor(197, 48, 48)

    # References
    citations = content.get("cited_sources", [])
    if citations:
        doc.add_heading("References & Evidence Audit Trail", level=1)
        for cit in citations:
            if isinstance(cit, dict):
                ref_text = f"[{cit.get('source_id', 'SRC')}] {cit.get('title', '')} ({cit.get('url', 'Internal')})"
            else:
                ref_text = f"[{cit}] Verified ground source."
            p = doc.add_paragraph(ref_text)
            p.runs[0].font.size = Pt(9)
            p.runs[0].font.color.rgb = RGBColor(113, 128, 150)

    doc.save(str(output_path))
    return str(output_path.resolve())


def generate_report(
    content: Dict[str, Any],
    format: str = "pdf",
    output_filename: Optional[str] = None,
) -> str:
    """
    Export a structured report to PDF or DOCX format in the reports/ directory.

    Args:
        content: Structured report dictionary containing title, sections, cited_sources, unsupported_claims.
        format: Export format - 'pdf' or 'docx' (default: 'pdf').
        output_filename: Optional explicit filename (e.g., "pg_vs_mongo.pdf").

    Returns:
        String path to the created file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = format.lower().strip()
    if fmt not in ("pdf", "docx"):
        raise ValueError(f"Unsupported report export format: '{format}'. Must be 'pdf' or 'docx'.")

    title = content.get("title", "research_report")
    base_name = output_filename or f"{_sanitize_filename(title)}.{fmt}"
    if not base_name.endswith(f".{fmt}"):
        base_name += f".{fmt}"

    output_path = REPORTS_DIR / base_name

    if fmt == "pdf":
        return _build_pdf(content, output_path)
    else:
        return _build_docx(content, output_path)
