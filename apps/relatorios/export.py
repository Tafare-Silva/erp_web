import csv
import io
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import quote

from .columns import ReportResult, export_value, format_value


def _meta_lines(meta: dict) -> list[tuple[str, str]]:
    lines = []
    if meta.get("brand_name"):
        lines.append(("Empresa", meta["brand_name"]))
    if meta.get("subtitle"):
        lines.append(("Período / resumo", meta["subtitle"]))
    if meta.get("mode_label"):
        lines.append(("Modelo", meta["mode_label"]))
    for item in meta.get("filters_summary", []):
        lines.append((item["label"], item["value"]))
    if meta.get("generated_at"):
        lines.append(("Gerado em", meta["generated_at"]))
    return lines


def build_csv(result: ReportResult) -> bytes:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow([column.label for column in result.columns])
    for row in result.rows:
        writer.writerow([export_value(row.get(column.key), column.kind) for column in result.columns])
    if result.totals:
        totals_line = []
        for index, column in enumerate(result.columns):
            if index == 0:
                totals_line.append("TOTAIS")
            elif column.key in result.totals:
                totals_line.append(export_value(result.totals.get(column.key), column.kind))
            else:
                totals_line.append("")
        writer.writerow(totals_line)
    return buffer.getvalue().encode("utf-8")


def build_xlsx(result: ReportResult, meta: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Relatório"

    brand_color = (meta.get("brand_color") or "#0F1E36").replace("#", "")
    header_fill = PatternFill("solid", fgColor=brand_color)
    header_font = Font(color="FFFFFF", bold=True, size=9)
    title_font = Font(bold=True, size=14, color=brand_color)
    meta_font = Font(size=9, color="475569")
    border = Border(bottom=Side(style="thin", color="CBD5E1"))

    row_index = 1
    sheet.cell(row=row_index, column=1, value=meta.get("title") or "Relatório").font = title_font
    row_index += 1
    for label, value in _meta_lines(meta):
        sheet.cell(row=row_index, column=1, value=label).font = Font(bold=True, size=9, color="334155")
        sheet.cell(row=row_index, column=2, value=value).font = meta_font
        row_index += 1
    row_index += 1

    header_row = row_index
    for column_index, column in enumerate(result.columns, start=1):
        cell = sheet.cell(row=header_row, column=column_index, value=column.label)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="right" if column.is_numeric else "left", vertical="center", wrap_text=True
        )
    sheet.row_dimensions[header_row].height = 24

    for row in result.rows:
        row_index += 1
        for column_index, column in enumerate(result.columns, start=1):
            value = row.get(column.key)
            if column.kind in ("money", "number", "percent") and value not in (None, ""):
                if isinstance(value, Decimal):
                    value = float(value)
            if isinstance(value, datetime):
                value = value.date()
            cell = sheet.cell(row=row_index, column=column_index, value=value)
            cell.border = border
            if column.kind == "money":
                cell.number_format = 'R$ #,##0.00'
            elif column.kind == "number":
                cell.number_format = '#,##0.0000'
            elif column.kind == "percent":
                cell.number_format = '0.00"%"'
            elif column.kind == "date":
                cell.number_format = 'dd/mm/yyyy'
            cell.alignment = Alignment(horizontal="right" if column.is_numeric else "left")

    if result.totals:
        row_index += 1
        for column_index, column in enumerate(result.columns, start=1):
            if column_index == 1:
                value = "TOTAIS"
            elif column.key in result.totals:
                value = result.totals.get(column.key)
                if isinstance(value, Decimal):
                    value = float(value)
            else:
                value = ""
            cell = sheet.cell(row=row_index, column=column_index, value=value)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="E2E8F0")
            if column.kind == "money":
                cell.number_format = 'R$ #,##0.00'
            elif column.kind == "number":
                cell.number_format = '#,##0.0000'
            elif column.kind == "percent":
                cell.number_format = '0.00"%"'

    for column_index, column in enumerate(result.columns, start=1):
        width = column.width or max(len(column.label), 10)
        for row in result.rows[:200]:
            text = format_value(row.get(column.key), column.kind)
            width = max(width, min(len(text), 42))
        sheet.column_dimensions[get_column_letter(column_index)].width = min(width + 2, 45)

    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=1)
    if result.rows:
        sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(len(result.columns))}{header_row + len(result.rows)}"

    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def build_pdf(result: ReportResult, meta: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    brand_color = meta.get("brand_color") or "#0F1E36"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=meta.get("title") or "Relatório",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor(brand_color),
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=7.8,
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.white,
    )

    story = []
    story.append(Paragraph(meta.get("title") or "Relatório", title_style))
    if meta.get("brand_name"):
        story.append(Paragraph(meta["brand_name"], subtitle_style))
    if meta.get("subtitle"):
        story.append(Paragraph(meta["subtitle"], subtitle_style))
    if meta.get("mode_label"):
        story.append(Paragraph(f"Modelo: {meta['mode_label']}", subtitle_style))
    filtros = meta.get("filters_summary", [])
    if filtros:
        texto = " · ".join(f"<b>{item['label']}:</b> {item['value']}" for item in filtros)
        story.append(Paragraph(texto, subtitle_style))
    if meta.get("generated_at"):
        story.append(Paragraph(f"Gerado em {meta['generated_at']}", subtitle_style))
    story.append(Spacer(1, 5 * mm))

    if not result.columns:
        story.append(Paragraph("Nenhum resultado para os filtros informados.", subtitle_style))
        doc.build(story)
        return buffer.getvalue()

    header = [Paragraph(column.label, header_style) for column in result.columns]
    data = [header]
    for row in result.rows:
        line = []
        for column in result.columns:
            text = format_value(row.get(column.key), column.kind)
            text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            line.append(Paragraph(text, cell_style))
        data.append(line)

    if result.totals:
        totals_line = []
        for index, column in enumerate(result.columns):
            if index == 0:
                text = "TOTAIS"
            elif column.key in result.totals:
                text = format_value(result.totals.get(column.key), column.kind)
            else:
                text = ""
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            totals_line.append(Paragraph(f"<b>{text}</b>", cell_style))
        data.append(totals_line)

    available = doc.width
    widths = []
    for column in result.columns:
        if column.width:
            widths.append(column.width)
        else:
            widths.append(1)
    base = available / len(result.columns)
    col_widths = [base * (1.35 if not column.is_numeric else 0.85) for column in result.columns]
    scale = available / sum(col_widths)
    col_widths = [width * scale for width in col_widths]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(brand_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    if result.totals:
        table_style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")))
    table.setStyle(TableStyle(table_style))
    story.append(table)

    if result.notes:
        story.append(Spacer(1, 4 * mm))
        for note in result.notes:
            story.append(Paragraph(note, subtitle_style))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(10 * mm, 7 * mm, (meta.get("brand_name") or "") + " · " + (meta.get("title") or ""))
        canvas.drawRightString(doc.pagesize[0] - 10 * mm, 7 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def safe_filename(text: str) -> str:
    from django.utils.text import slugify

    return slugify(text) or "relatorio"
