from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_cuit(value):
    value = str(value)
    if not value.isascii() or not value.isdigit() or len(value) != 11:
        raise ValidationError('El CUIT/CUIL debe contener 11 dígitos sin separadores.')
    check = (11 - sum(int(c) * w for c, w in zip(value[:10], [5,4,3,2,7,6,5,4,3,2])) % 11) % 11
    if check == 10 or check != int(value[-1]):
        raise ValidationError('El CUIT/CUIL no tiene un dígito verificador válido.')


def validate_document(kind, value):
    value = str(value)
    if kind in (80, 86):
        validate_cuit(value)
    elif kind == 96:
        if not value.isascii() or not value.isdigit() or not 1 <= len(value) <= 8 or int(value) <= 0:
            raise ValidationError('Ingresá un DNI válido sin separadores.')
    elif kind != 99 or value != '0':
        raise ValidationError('Para receptor sin identificar, el número debe ser 0.')


def validate_invoice(invoice, *, historical=False):
    from .models import VAT_CONDITIONS
    if invoice.document_type not in (11, 13) or invoice.concept not in (1, 2, 3):
        raise ValidationError('Solo se admiten comprobantes C y conceptos válidos.')
    invoice.configuration.issuer.full_clean()
    invoice.customer.full_clean()
    if invoice.customer.vat_condition not in dict(VAT_CONDITIONS):
        raise ValidationError('Seleccioná la condición de IVA del receptor.')
    if not invoice.customer.active:
        raise ValidationError('El cliente está inactivo.')
    if invoice.concept in (2, 3):
        if not all((invoice.service_from, invoice.service_to, invoice.due_date)):
            raise ValidationError('Los servicios requieren período y vencimiento de pago.')
        if invoice.service_from > invoice.service_to or invoice.due_date < invoice.issue_date:
            raise ValidationError('Revisá el orden del período y el vencimiento de pago.')
    age = (timezone.localdate() - invoice.issue_date).days
    window = 5 if invoice.concept == 1 else 10
    if historical and age < 0:
        raise ValidationError('No se puede importar un comprobante con fecha futura.')
    if not historical and abs(age) > window:
        raise ValidationError(f'La fecha debe estar dentro de {window} días de hoy para este concepto.')
    lines = list(invoice.lines.all())
    if not lines or len(lines) > 50:
        raise ValidationError('Agregá entre 1 y 50 líneas.')
    for line in lines:
        line.full_clean()
        if not line.description.strip() or line.quantity <= 0 or line.unit_price < 0:
            raise ValidationError('Cada línea requiere descripción, cantidad positiva y precio no negativo.')
    invoice.total = sum((line.amount for line in lines), Decimal('0.00'))
    if not Decimal('0') < invoice.total <= Decimal('9999999999999.99'):
        raise ValidationError('El total debe ser positivo y estar dentro del límite de ARCA.')
    if invoice.document_type == 13:
        original = invoice.original
        if not original or original.status != 'authorized' or original.document_type != 11:
            raise ValidationError('La nota de crédito requiere una factura C autorizada.')
        if original.environment != invoice.configuration.environment or original.configuration.issuer_id != invoice.configuration.issuer_id:
            raise ValidationError('La nota y la factura deben pertenecer al mismo emisor y ambiente.')
        if str(invoice.customer.document_number) != str(original.customer_snapshot.get('document_number')) or invoice.customer.document_type != original.customer_snapshot.get('document_type'):
            raise ValidationError('La nota de crédito debe conservar la identificación del receptor original.')
    elif invoice.original_id:
        raise ValidationError('Una factura no puede tener comprobante asociado.')


def snapshots(invoice):
    issuer = invoice.configuration.issuer
    customer = invoice.customer
    return ({'name': issuer.name, 'cuit': issuer.cuit, 'address': issuer.address,
        'gross_income': issuer.gross_income, 'activities_since': issuer.activities_since.isoformat() if issuer.activities_since else ''},
        {'name': customer.name, 'document_type': customer.document_type, 'document_number': customer.document_number,
         'vat_condition': customer.vat_condition, 'address': customer.address})


def invoice_payload(invoice):
    customer = invoice.customer_snapshot or snapshots(invoice)[1]
    detail = {'Concepto': invoice.concept, 'DocTipo': customer['document_type'],
        'DocNro': customer['document_number'], 'CbteDesde': invoice.number, 'CbteHasta': invoice.number,
        'CbteFch': invoice.issue_date.strftime('%Y%m%d'), 'ImpTotal': str(invoice.total),
        'ImpTotConc': '0.00', 'ImpNeto': str(invoice.total), 'ImpOpEx': '0.00', 'ImpTrib': '0.00',
        'ImpIVA': '0.00'}
    if invoice.concept in (2, 3):
        detail.update(FchServDesde=invoice.service_from.strftime('%Y%m%d'),
            FchServHasta=invoice.service_to.strftime('%Y%m%d'), FchVtoPago=invoice.due_date.strftime('%Y%m%d'))
    detail.update(MonId='PES', MonCotiz='1.00', CondicionIVAReceptorId=customer['vat_condition'])
    if invoice.original_id:
        original = invoice.original
        detail['CbtesAsoc'] = {'CbteAsoc': [{'Tipo': 11, 'PtoVta': original.point_of_sale,
            'Nro': original.number, 'Cuit': original.issuer_snapshot['cuit'], 'CbteFch': original.issue_date.strftime('%Y%m%d')}]}
    return {'FeCabReq': {'CantReg': 1, 'PtoVta': invoice.point_of_sale or invoice.configuration.point_of_sale,
        'CbteTipo': invoice.document_type}, 'FeDetReq': {'FECAEDetRequest': [detail]}}
