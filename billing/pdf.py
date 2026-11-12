"""Fiscal representation from immutable snapshots; entirely generated in memory."""
import base64
import json
from io import BytesIO
from urllib.parse import quote
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

from .models import VAT_CONDITIONS


def qr_url(invoice):
    data = {'ver': 1, 'fecha': invoice.issue_date.isoformat(), 'cuit': int(invoice.issuer_snapshot['cuit']),
        'ptoVta': invoice.point_of_sale, 'tipoCmp': invoice.document_type, 'nroCmp': invoice.number,
        'importe': float(invoice.total), 'moneda': 'PES', 'ctz': 1,
        'tipoDocRec': invoice.customer_snapshot['document_type'], 'nroDocRec': int(invoice.customer_snapshot['document_number']),
        'tipoCodAut': 'E', 'codAut': int(invoice.cae)}
    encoded = base64.b64encode(json.dumps(data, separators=(',', ':')).encode()).decode()
    return 'https://www.arca.gob.ar/fe/qr/?p=' + quote(encoded, safe='')


def invoice_pdf(invoice):
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Fiscal', fontName='Helvetica', fontSize=9, leading=14, textColor=colors.HexColor('#20334e')))
    styles.add(ParagraphStyle('Amount', parent=styles['Fiscal'], alignment=TA_RIGHT))
    p = lambda value: Paragraph(escape(str(value)), styles['Fiscal'])
    issuer, receiver = invoice.issuer_snapshot, invoice.customer_snapshot
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=24*mm, bottomMargin=20*mm, title=str(invoice), author=issuer['name'])
    story = []
    if invoice.environment != 'PROD':
        story.extend([Paragraph('HOMOLOGACIÓN - SIN VALIDEZ FISCAL', styles['Heading2']), Spacer(1, 5*mm)])
    story.extend([Paragraph(invoice.get_document_type_display().upper() + ' · C', styles['Heading1']),
        p(f'Código {invoice.document_type:03d} · Original · N.º {invoice.fiscal_number}'),
        p(f'Fecha de emisión: {invoice.issue_date:%d/%m/%Y}'), Spacer(1, 5*mm)])
    data = [[p(issuer['name']), p(receiver['name'])],
        [p(f'CUIT: {issuer["cuit"]}'), p(f'Documento: {receiver["document_number"]}')],
        [p(issuer['address']), p(receiver['address'])],
        [p('Responsable Monotributo'), p(dict(VAT_CONDITIONS).get(receiver['vat_condition'], ''))],
        [p(f'Ingresos brutos: {issuer.get("gross_income", "")}'), p('')],
        [p(f'Inicio de actividades: {issuer.get("activities_since", "")}'), p('')]]
    identity = Table(data, colWidths=[87*mm, 87*mm])
    identity.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.extend([identity, Spacer(1, 6*mm)])
    if invoice.concept in (2, 3):
        story.extend([p(f'Período del servicio: {invoice.service_from:%d/%m/%Y} al {invoice.service_to:%d/%m/%Y}'),
            p(f'Vencimiento de pago: {invoice.due_date:%d/%m/%Y}'), Spacer(1, 5*mm)])
    if invoice.original_id:
        story.extend([p(f'Comprobante asociado: Factura C {invoice.original.fiscal_number}'), Spacer(1, 4*mm)])
    rows = [[p('Descripción'), p('Cantidad'), p('Precio unitario'), p('Subtotal')]]
    for line in invoice.lines.all():
        rows.append([p(line.description), p(f'{line.quantity:f}'), p(f'$ {line.unit_price:,.4f}'), p(f'$ {line.amount:,.2f}')])
    table = Table(rows, colWidths=[88*mm, 20*mm, 33*mm, 33*mm], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#edf3f8')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING',(0,0),(-1,-1),9),
        ('BOTTOMPADDING',(0,0),(-1,-1),9), ('LINEBELOW',(0,0),(-1,0),0.7,colors.HexColor('#9aadc0')),
        ('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#dce3eb'))]))
    story.extend([table, Spacer(1, 7*mm), Paragraph(f'TOTAL ARS $ {invoice.total:,.2f}', styles['Heading2']), Spacer(1, 5*mm)])
    qr = QrCodeWidget(qr_url(invoice))
    bounds = qr.getBounds()
    size = 32*mm
    drawing = Drawing(size, size, transform=[size/(bounds[2]-bounds[0]),0,0,size/(bounds[3]-bounds[1]),0,0])
    drawing.add(qr)
    validation = Table([[drawing, [p(f'CAE: {invoice.cae}'), p(f'Vencimiento CAE: {invoice.cae_due:%d/%m/%Y}'),
        p('Comprobante autorizado por ARCA.'), p('La autorización no valida los datos de la operación.')]]], colWidths=[40*mm,134*mm])
    validation.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(KeepTogether([validation]))

    def page_header(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#10294c'))
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(18*mm, A4[1]-15*mm, 'devLink')
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(A4[0]-18*mm, A4[1]-15*mm, invoice.fiscal_number)
        canvas.drawRightString(A4[0]-18*mm, 12*mm, f'Página {document.page}')
        canvas.restoreState()
    doc.build(story, onFirstPage=page_header, onLaterPages=page_header)
    return output.getvalue()
