"""Rebuild the companion specification PDF from Markdown (requires reportlab)."""

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/Extraction_Workbench_Project_Specification.pdf"
WIDTH = A4[0] - 96
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle("Body", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=7)
)
styles.add(
    ParagraphStyle("Cell", parent=styles["Body"], fontSize=8, leading=10, spaceAfter=0)
)
styles.add(
    ParagraphStyle(
        "SpecCode", fontName="Courier", fontSize=7.5, leading=10, spaceAfter=8
    )
)
for name in ("Title", "Heading1", "Heading2", "Heading3"):
    styles[name].textColor = colors.HexColor("#153E38")
    styles[name].spaceAfter = 10


def inline(text: str) -> str:
    """Escape prose while retaining the small set of source formatting tags."""
    text = escape(text.replace("—", "-").replace("–", "-"))
    text = re.sub(r"&lt;(/?(?:b|br/|link)(?:\s.*?)?)&gt;", r"<\1>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def table(lines: list[str]) -> Table:
    rows = [
        [
            cell.replace(r"\|", "|")
            for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
        ]
        for line in lines
    ]
    rows = [
        row
        for row in rows
        if not all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in row)
    ]
    data = [
        [Paragraph(inline(cell.strip()), styles["Cell"]) for cell in row]
        for row in rows
    ]
    widths = [WIDTH / len(data[0])] * len(data[0])
    if len(widths) == 2:
        widths = [WIDTH * 0.30, WIDTH * 0.70]
    elif len(widths) == 3 and rows[0][0].strip() == "Field":
        widths = [WIDTH * 0.25, WIDTH * 0.13, WIDTH * 0.62]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEDE9")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F4F7F6")],
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#AACDC4")),
            ]
        )
    )
    return result


def footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#49615C"))
    canvas.drawString(48, 25, "Extraction Workbench | Specification | 4 October 2026")
    canvas.drawRightString(A4[0] - 48, 25, str(document.page))
    canvas.restoreState()


def build():
    lines = (
        (ROOT / "docs/PROJECT_SPECIFICATION.md")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    story = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if line.startswith("PROJECT SPECIFICATION /"):
            story.append(PageBreak())
        elif line.startswith("```"):
            code = []
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            story.append(Preformatted("\n".join(code), styles["SpecCode"]))
        elif line.startswith("|"):
            rows = [line]
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(lines[index])
                index += 1
            story.extend([table(rows), Spacer(1, 9)])
        else:
            heading = re.match(r"^(#{1,3})\s+(.*)", line)
            name = (
                ("Title", "Heading1", "Heading2")[len(heading[1]) - 1]
                if heading
                else "Body"
            )
            story.append(
                Paragraph(inline(heading[2] if heading else line), styles[name])
            )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=42,
        bottomMargin=45,
        title="Extraction Workbench - Project Specification",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()
