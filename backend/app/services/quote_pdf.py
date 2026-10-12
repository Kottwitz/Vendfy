from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.enums import QuoteStatus
from app.models.quote import Quote

NAVY = colors.HexColor("#172b4d")
TEAL = colors.HexColor("#0f766e")
LIGHT = colors.HexColor("#f1f5f9")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#dbe3ec")
try:
    BRAZIL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    BRAZIL_TIMEZONE = timezone(timedelta(hours=-3), name="BRT")
MONTHS_PT_BR = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
STATUS_LABELS = {
    QuoteStatus.DRAFT: "Rascunho",
    QuoteStatus.SENT: "Enviado",
    QuoteStatus.VIEWED: "Visualizado",
    QuoteStatus.APPROVED: "Aprovado",
    QuoteStatus.REJECTED: "Recusado",
    QuoteStatus.EXPIRED: "Expirado",
    QuoteStatus.CANCELLED: "Cancelado",
}


def _format_money(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_quantity(value: Decimal) -> str:
    return f"{value:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_date(value: date | datetime | None) -> str:
    if value is None:
        return "Não informada"
    if isinstance(value, datetime):
        value = value.astimezone(BRAZIL_TIMEZONE).date()
    return f"{value.day} de {MONTHS_PT_BR[value.month - 1]} de {value.year}"


def _paragraph_text(value: str | None) -> str:
    return escape(value or "—").replace("\n", "<br/>")


def generate_quote_pdf(quote: Quote) -> bytes:
    """Render a quote and its persisted totals as a downloadable PDF."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Orçamento {quote.number:04d}",
        author="Vendfy",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Brand",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=NAVY,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=NAVY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableRight",
            parent=styles["TableCell"],
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaLabel",
            parent=styles["Small"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaValue",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeaderDetail",
            parent=styles["Small"],
            alignment=TA_RIGHT,
            fontSize=8,
            leading=11,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Total",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            alignment=TA_RIGHT,
        )
    )

    company = quote.company
    client = quote.client
    company_lines = [
        _paragraph_text(company.name),
        *(
            [_paragraph_text(company.document)]
            if company.document
            else []
        ),
        *([_paragraph_text(company.email)] if company.email else []),
        *([_paragraph_text(company.phone)] if company.phone else []),
        *([_paragraph_text(company.address)] if company.address else []),
    ]
    client_lines = [
        _paragraph_text(client.name),
        *([_paragraph_text(client.document)] if client.document else []),
        *([_paragraph_text(client.email)] if client.email else []),
        *([_paragraph_text(client.phone)] if client.phone else []),
        *([_paragraph_text(client.address)] if client.address else []),
    ]

    story = [
        Table(
            [
                [
                    Paragraph("vendfy", styles["Brand"]),
                    Paragraph(
                        "PROPOSTA COMERCIAL",
                        ParagraphStyle(
                            "ProposalLabel",
                            parent=styles["Small"],
                            alignment=TA_RIGHT,
                            textColor=TEAL,
                            fontName="Helvetica-Bold",
                        ),
                    ),
                ],
                [
                    Paragraph(_paragraph_text(company.name), styles["Small"]),
                    Paragraph(
                        (
                            f'<font name="Helvetica-Bold" size="10" color="#172b4d">'
                            f"Orçamento #{quote.number:04d}</font><br/>"
                            f'<font name="Helvetica" size="8" color="#64748b">'
                            f"Emitido em {_format_date(quote.created_at)}</font>"
                        ),
                        styles["HeaderDetail"],
                    ),
                ],
            ],
            colWidths=[document.width * 0.62, document.width * 0.38],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, -1), (-1, -1), 1.5, TEAL),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                ]
            ),
        ),
        Spacer(1, 8 * mm),
        Table(
            [
                [
                    Paragraph("STATUS DO ORÇAMENTO", styles["MetaLabel"]),
                    Paragraph("PRAZO DE VALIDADE", styles["MetaLabel"]),
                ],
                [
                    Paragraph(STATUS_LABELS[quote.status], styles["MetaValue"]),
                    Paragraph(_format_date(quote.valid_until), styles["MetaValue"]),
                ],
            ],
            colWidths=[document.width / 2] * 2,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f8fa")),
                    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("LINEBEFORE", (1, 0), (1, -1), 2, TEAL),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 11),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        ),
        Paragraph("Dados da proposta", styles["Section"]),
        Table(
            [
                [
                    Paragraph("<b>EMPRESA</b><br/>" + "<br/>".join(company_lines), styles["TableCell"]),
                    Paragraph("<b>CLIENTE</b><br/>" + "<br/>".join(client_lines), styles["TableCell"]),
                ]
            ],
            colWidths=[document.width / 2] * 2,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
    ]

    if quote.description:
        story.extend(
            [
                Paragraph("Descrição", styles["Section"]),
                Paragraph(_paragraph_text(quote.description), styles["TableCell"]),
            ]
        )

    story.extend(
        [
            Paragraph("Itens do orçamento", styles["Section"]),
        ]
    )
    item_rows = [
        [
            Paragraph("DESCRIÇÃO", styles["TableHeader"]),
            Paragraph("QUANT.", styles["TableHeader"]),
            Paragraph("VALOR UNITÁRIO", styles["TableHeader"]),
            Paragraph("SUBTOTAL", styles["TableHeader"]),
        ]
    ]
    item_rows.extend(
        [
            Paragraph(_paragraph_text(item.description), styles["TableCell"]),
            Paragraph(_format_quantity(item.quantity), styles["TableRight"]),
            Paragraph(_format_money(item.unit_price), styles["TableRight"]),
            Paragraph(_format_money(item.total), styles["TableRight"]),
        ]
        for item in quote.items
    )
    if item_rows[1:]:
        story.append(
            Table(
                item_rows,
                colWidths=[
                    document.width * 0.43,
                    document.width * 0.14,
                    document.width * 0.22,
                    document.width * 0.21,
                ],
                repeatRows=1,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, NAVY),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            )
        )
    else:
        story.append(
            Table(
                [[Paragraph("Nenhum item foi informado neste orçamento.", styles["Small"])]],
                colWidths=[document.width],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            )
        )

    totals = [
        ["Subtotal", _format_money(quote.subtotal)],
        ["Desconto", f"- {_format_money(quote.discount)}"],
        ["Total", _format_money(quote.total)],
    ]
    summary = Table(
        [
            [
                Paragraph(label, styles["TableCell"] if label != "Total" else styles["Total"]),
                Paragraph(
                    value,
                    styles["TableRight"] if label != "Total" else styles["Total"],
                ),
            ]
            for label, value in totals
        ],
        colWidths=[document.width * 0.4, document.width * 0.3],
        hAlign="RIGHT",
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 1), LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, 1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 1), 6),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#e8f3f1")),
                ("LINEABOVE", (0, 2), (-1, 2), 1, TEAL),
                ("TOPPADDING", (0, 2), (-1, 2), 8),
                ("BOTTOMPADDING", (0, 2), (-1, 2), 8),
            ]
        ),
    )
    story.extend(
        [
            Spacer(1, 4 * mm),
            KeepTogether(
                [
                    summary,
                    Spacer(1, 15 * mm),
                    Table(
                        [
                            ["", ""],
                            [
                                Paragraph("Assinatura do cliente", styles["Small"]),
                                Paragraph("Data", styles["Small"]),
                            ],
                        ],
                        colWidths=[document.width * 0.7, document.width * 0.3],
                        style=TableStyle(
                            [
                                ("LINEABOVE", (0, 1), (0, 1), 0.7, MUTED),
                                ("LINEABOVE", (1, 1), (1, 1), 0.7, MUTED),
                                ("TOPPADDING", (0, 1), (-1, 1), 5),
                            ]
                        ),
                    ),
                ]
            ),
        ]
    )

    def draw_page_number(canvas: Canvas, pdf_document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 12 * mm, "Gerado por Vendfy")
        canvas.drawRightString(
            pdf_document.pagesize[0] - 18 * mm,
            12 * mm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return output.getvalue()
