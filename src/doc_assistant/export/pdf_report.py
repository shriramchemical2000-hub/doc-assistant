from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _register_font() -> tuple[str, str]:
    regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    regular = next((p for p in regular_candidates if Path(p).exists()), None)
    bold = next((p for p in bold_candidates if Path(p).exists()), None)
    if regular and bold:
        if "DocuMindSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DocuMindSans", regular))
            pdfmetrics.registerFont(TTFont("DocuMindSans-Bold", bold))
        return "DocuMindSans", "DocuMindSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def _inline_markup(value: str) -> str:
    value = escape(value.strip())
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    value = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<u>\1</u> (\2)', value)
    return value


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def _markdown_story(markdown_text: str, styles: dict) -> list:
    lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    story: list = []
    paragraph_lines: list[str] = []
    index = 0

    def flush_paragraph():
        if paragraph_lines:
            text = " ".join(part.strip() for part in paragraph_lines)
            story.append(Paragraph(_inline_markup(text), styles["Body"]))
            story.append(Spacer(1, 5))
            paragraph_lines.clear()

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush_paragraph()
            index += 1
            continue

        if "|" in line and index + 1 < len(lines) and _is_table_separator(lines[index + 1]):
            flush_paragraph()
            raw_rows = [line]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                raw_rows.append(lines[index].strip())
                index += 1
            parsed = [
                [Paragraph(_inline_markup(cell), styles["TableHeader"] if row_no == 0 else styles["TableCell"])
                 for cell in row.strip().strip("|").split("|")]
                for row_no, row in enumerate(raw_rows)
            ]
            columns = max(len(row) for row in parsed)
            parsed = [row + [Paragraph("", styles["TableCell"])] * (columns - len(row)) for row in parsed]
            available_width = A4[0] - 38 * mm
            table = Table(parsed, colWidths=[available_width / columns] * columns, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#174B3B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F8F5")),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C9D8CE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 9)])
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            story.append(Paragraph(_inline_markup(heading.group(2)), styles[f"H{level}"]))
            story.append(Spacer(1, 4 if level == 1 else 2))
            index += 1
            continue

        if line in {"---", "***", "___"}:
            flush_paragraph()
            story.extend([HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#CBD9D0")), Spacer(1, 8)])
            index += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            item_text = bullet.group(1) if bullet else numbered.group(1)
            bullet_char = "•" if bullet else "–"
            story.append(Paragraph(f'<font color="#287653">{bullet_char}</font>  {_inline_markup(item_text)}', styles["List"]))
            index += 1
            continue

        if line.startswith(">"):
            flush_paragraph()
            story.append(Paragraph(_inline_markup(line.lstrip("> ")), styles["Quote"]))
            story.append(Spacer(1, 4))
            index += 1
            continue

        if line.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            code_text = "<br/>".join(escape(part) for part in code_lines)
            story.append(Paragraph(f'<font name="Courier">{code_text}</font>', styles["DocuMindCode"]))
            story.append(Spacer(1, 6))
            index += 1
            continue

        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    return story


def build_smart_docs_pdf(markdown_text: str, source_filename: str, task: str, instructions: str = "") -> bytes:
    """Build a polished PDF report from a Smart Docs Markdown result."""
    regular_font, bold_font = _register_font()
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontName=regular_font,
        fontSize=9.2, leading=14, textColor=colors.HexColor("#24352C"), spaceAfter=2))
    styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], fontName=bold_font,
        fontSize=16, leading=20, textColor=colors.HexColor("#174B3B"), spaceBefore=13, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], fontName=bold_font,
        fontSize=12, leading=16, textColor=colors.HexColor("#287653"), spaceBefore=10, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="H3", parent=styles["Heading3"], fontName=bold_font,
        fontSize=10, leading=13, textColor=colors.HexColor("#425B4D"), spaceBefore=7, spaceAfter=3, keepWithNext=True))
    styles.add(ParagraphStyle(name="List", parent=styles["BodyText"], fontName=regular_font,
        fontSize=9.1, leading=13, leftIndent=13, firstLineIndent=-9, textColor=colors.HexColor("#24352C"), spaceAfter=3))
    styles.add(ParagraphStyle(name="Quote", parent=styles["BodyText"], fontName=regular_font,
        fontSize=9, leading=13, leftIndent=12, borderColor=colors.HexColor("#8CC9A5"),
        borderWidth=2, borderPadding=7, textColor=colors.HexColor("#52675A")))
    styles.add(ParagraphStyle(name="DocuMindCode", parent=styles["Code"], fontName="Courier",
        fontSize=7.5, leading=10, backColor=colors.HexColor("#F1F4F2"), borderPadding=6))
    styles.add(ParagraphStyle(name="TableHeader", fontName=bold_font, fontSize=7.5, leading=10, textColor=colors.white))
    styles.add(ParagraphStyle(name="TableCell", fontName=regular_font, fontSize=7.5, leading=10, textColor=colors.HexColor("#24352C")))
    styles.add(ParagraphStyle(name="ReportTitle", fontName=bold_font, fontSize=23, leading=28,
        textColor=colors.HexColor("#174B3B"), alignment=TA_LEFT, spaceAfter=5))
    styles.add(ParagraphStyle(name="Meta", fontName=regular_font, fontSize=8.5, leading=12, textColor=colors.HexColor("#64766B")))

    def draw_page(canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(colors.HexColor("#174B3B"))
        canvas.rect(0, height - 8 * mm, width, 8 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#D8E4DC"))
        canvas.line(19 * mm, 15 * mm, width - 19 * mm, 15 * mm)
        canvas.setFont(regular_font, 7.5)
        canvas.setFillColor(colors.HexColor("#718278"))
        canvas.drawString(19 * mm, 10 * mm, "DOCUMIND  |  DOCUMENT INTELLIGENCE REPORT")
        canvas.drawRightString(width - 19 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    story = [
        Spacer(1, 8 * mm),
        Paragraph("DocuMind Report", styles["ReportTitle"]),
        Paragraph(_inline_markup(task), styles["H2"]),
        Spacer(1, 3),
        Paragraph(f"<b>Source document:</b> {_inline_markup(source_filename)}", styles["Meta"]),
        Paragraph(f"<b>Generated:</b> {datetime.now().astimezone().strftime('%d %b %Y, %I:%M %p %Z')}", styles["Meta"]),
    ]
    if instructions.strip():
        story.append(Paragraph(f"<b>Focus instructions:</b> {_inline_markup(instructions)}", styles["Meta"]))
    story.extend([Spacer(1, 8), HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#8CC9A5")), Spacer(1, 9)])
    story.extend(_markdown_story(markdown_text, styles))

    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=19 * mm, leftMargin=19 * mm,
        topMargin=17 * mm, bottomMargin=21 * mm, title=f"DocuMind - {task}",
        author="DocuMind", subject=f"Generated from {source_filename}")
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()
