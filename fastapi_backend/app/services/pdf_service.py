"""Generate clean, structured PDF reports from incident analysis responses."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_ACCENT = colors.HexColor("#2563eb")
_DARK = colors.HexColor("#111827")
_MUTED = colors.HexColor("#4b5563")
_BORDER = colors.HexColor("#d1d5db")
_PANEL = colors.HexColor("#f3f4f6")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontSize=20, leading=24,
            textColor=_DARK, alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=base["Normal"], fontSize=10, leading=13,
            textColor=_MUTED, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], fontSize=12.5, leading=15,
            textColor=_ACCENT, spaceBefore=14, spaceAfter=6, spaceKeepWithNext=1,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontSize=9.5, leading=13.5,
            textColor=_DARK, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontSize=8, leading=10.5, textColor=_MUTED,
        ),
        "mono": ParagraphStyle(
            "Mono", parent=base["BodyText"], fontName="Courier", fontSize=7.6,
            leading=9.6, textColor=_DARK,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["BodyText"], fontSize=8, leading=10.5, textColor=_DARK,
        ),
        "cellhead": ParagraphStyle(
            "CellHead", parent=base["BodyText"], fontSize=8, leading=10.5,
            textColor=colors.white, fontName="Helvetica-Bold",
        ),
    }


def _para(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text if text is not None else "")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _meta_table(pairs: list[tuple[str, Any]], st: dict[str, ParagraphStyle]) -> Table:
    data = [[_para(k, st["small"]), _para(v, st["cell"])] for k, v in pairs]
    table = Table(data, colWidths=[38 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), _PANEL),
                ("TEXTCOLOR", (0, 0), (0, -1), _MUTED),
                ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _grid_table(
    headers: list[str],
    rows: list[list[Any]],
    widths: list[float] | None,
    st: dict[str, ParagraphStyle],
) -> Table:
    data = [[_para(h, st["cellhead"]) for h in headers]]
    for row in rows:
        data.append([_para(c, st["cell"]) for c in row])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(16 * mm, 10 * mm, "GraphRCA — Incident Analysis Report")
    canvas.drawRightString(
        A4[0] - 16 * mm, 10 * mm, f"Page {doc.page}"
    )
    canvas.restoreState()


def build_analysis_pdf(analysis: dict[str, Any]) -> bytes:
    st = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Incident Analysis Report",
        author="GraphRCA: Graph-Based Root Cause Analysis",
    )

    story: list[Any] = []
    title = analysis.get("title") or "Incident Analysis Report"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    story.append(_para("INCIDENT ANALYSIS REPORT", st["subtitle"]))
    story.append(_para(title, st["title"]))
    story.append(
        _para(
            f"Incident ID: {analysis.get('incident_id', '—')}  |  Generated: {generated}",
            st["subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=10))

    # Overview metadata
    story.append(_para("Overview", st["h2"]))
    story.append(
        _meta_table(
            [
                ("Service", analysis.get("service", "—")),
                ("Team", analysis.get("team", "—")),
                ("Severity", analysis.get("severity", "—")),
                ("Risk", analysis.get("risk_severity", "—")),
                ("Status", analysis.get("status", "—")),
                ("Confidence", analysis.get("confidence", "—")),
                ("Evidence Items", len(analysis.get("evidence") or [])),
                ("Graph Links", len(analysis.get("graph_relationships") or [])),
                ("Sources", len(analysis.get("sources") or [])),
            ],
            st,
        )
    )

    # Root cause + solution
    story.append(_para("Root Cause", st["h2"]))
    story.append(_para(analysis.get("root_cause", "Not determined"), st["body"]))

    story.append(_para("Potential Root Cause", st["h2"]))
    story.append(_para(analysis.get("potential_root_cause", "Not determined"), st["body"]))

    story.append(_para("Impact", st["h2"]))
    story.append(_para(analysis.get("impact", "Not determined"), st["body"]))

    story.append(_para("Possible Solution / Resolution", st["h2"]))
    resolution = analysis.get("resolution") or "No resolution derived."
    for line in str(resolution).split("\n"):
        if line.strip():
            story.append(_para(line, st["body"]))

    # Timeline
    timeline = analysis.get("timeline") or []
    if timeline:
        story.append(_para("Timeline", st["h2"]))
        rows = [
            [t.get("timestamp", "—"), t.get("event", "—"), t.get("actor", "—")]
            for t in timeline
            if isinstance(t, dict)
        ]
        story.append(_grid_table(["Timestamp", "Event", "Actor"], rows, [42 * mm, None, 30 * mm], st))

    # Matched log evidence
    evidence = analysis.get("evidence") or []
    story.append(_para(f"Matched Logs & Evidence ({len(evidence)})", st["h2"]))
    if not evidence:
        story.append(_para("No evidence was retrieved for this query.", st["body"]))
    else:
        for index, ev in enumerate(evidence, start=1):
            meta = ev.get("metadata") or {}
            header = (
                f"#{index}  [{ev.get('type', 'unknown')}]"
                f"  service={meta.get('service', '—')}"
                f"  level={meta.get('level') or meta.get('severity') or '—'}"
                f"  score={round(ev.get('score', 0) or 0, 3)}"
            )
            details = (
                f"source={meta.get('source_file') or ev.get('source', '—')}"
                f"  |  chunk={ev.get('chunk_id') or ev.get('node_id') or '—'}"
                f"  |  timestamp={meta.get('timestamp', '—')}"
            )
            block = [
                _para(header, st["small"]),
                _para(details, st["small"]),
                _para((ev.get("content") or "").strip(), st["mono"]),
                Spacer(1, 5),
            ]
            story.append(KeepTogether(block))

    # Graph relationships
    graph_rels = analysis.get("graph_relationships") or []
    if graph_rels:
        story.append(_para(f"Graph Relationships ({len(graph_rels)})", st["h2"]))
        rows = [
            [r.get("source", "—"), r.get("type", "—"), r.get("target", "—")]
            for r in graph_rels
            if isinstance(r, dict)
        ]
        story.append(_grid_table(["Source", "Relationship", "Target"], rows, [55 * mm, 32 * mm, None], st))

    # Verified sources
    sources = analysis.get("sources") or []
    if sources:
        story.append(_para(f"Verified Sources ({len(sources)})", st["h2"]))
        rows = [
            [
                s.get("source_file", "—"),
                s.get("service", "—"),
                s.get("source_type", "—"),
                round(s.get("retrieval_score", 0) or 0, 3),
                s.get("timestamp", "—"),
            ]
            for s in sources
            if isinstance(s, dict)
        ]
        story.append(
            _grid_table(
                ["Source File", "Service", "Type", "Score", "Timestamp"],
                rows,
                [55 * mm, 28 * mm, 20 * mm, 16 * mm, None],
                st,
            )
        )

    # Recommendations
    recommendations = analysis.get("recommended_investigation") or []
    if recommendations:
        story.append(_para("Recommended Investigation Steps", st["h2"]))
        for index, rec in enumerate(recommendations, start=1):
            story.append(_para(f"{index}. {rec}", st["body"]))

    # Lessons learned
    lessons = analysis.get("lessons_learned") or []
    if lessons:
        story.append(_para("Lessons Learned", st["h2"]))
        for lesson in lessons:
            story.append(_para(f"• {lesson}", st["body"]))

    # Raw log snippets
    snippets = analysis.get("log_snippets") or []
    if snippets:
        story.append(_para("Log Snippets", st["h2"]))
        for snippet in snippets:
            story.append(_para(snippet, st["mono"]))
            story.append(Spacer(1, 3))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
