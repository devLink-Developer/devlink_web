from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from billing.models import ArcaConfiguration, Customer, Invoice, InvoiceLine, Issuer
from billing.validation import invoice_payload, validate_invoice


class FiscalValidationTests(TestCase):
    def setUp(self):
        self.issuer = Issuer.objects.create(name='Emisor de prueba', cuit='20959815926',
            address='Domicilio fiscal de prueba', gross_income='Exento', activities_since=date(2020, 1, 1))
        self.config = ArcaConfiguration.objects.create(issuer=self.issuer, environment='HOMO', point_of_sale=7)
        self.customer = Customer.objects.create(name='Cliente <prueba>', document_type=80,
            document_number='20959815926', vat_condition=6, address='Domicilio del cliente')
        self.invoice = Invoice.objects.create(configuration=self.config, customer=self.customer,
            issue_date=date.today(), concept=2, service_from=date.today(), service_to=date.today(), due_date=date.today())
        InvoiceLine.objects.create(invoice=self.invoice, description='Servicio', quantity='3', unit_price='10.125')

    def test_c_invoice_rounds_money_and_omits_vat_breakdown(self):
        validate_invoice(self.invoice)
        self.assertEqual(self.invoice.total, Decimal('30.38'))
        self.invoice.number = 9
        detail = invoice_payload(self.invoice)['FeDetReq']['FECAEDetRequest'][0]
        self.assertEqual(detail['ImpNeto'], '30.38')
        self.assertEqual(detail['ImpIVA'], '0.00')
        self.assertEqual(detail['CondicionIVAReceptorId'], 6)
        self.assertNotIn('Iva', detail)

    def test_service_dates_must_be_ordered(self):
        self.invoice.service_to = date(2000, 1, 1)
        with self.assertRaises(ValidationError):
            validate_invoice(self.invoice)

    def test_service_dates_precede_currency_in_wsfe_xml_schema_order(self):
        import xml.etree.ElementTree as ET
        from billing.arca import append_xml, WSFE
        validate_invoice(self.invoice)
        self.invoice.number = 9
        root = ET.Element('request')
        append_xml(root, invoice_payload(self.invoice), WSFE)
        detail = root.find('.//{%s}FECAEDetRequest' % WSFE)
        tags = [node.tag.rsplit('}', 1)[-1] for node in detail]
        self.assertLess(tags.index('FchServDesde'), tags.index('MonId'))
        self.assertLess(tags.index('FchServHasta'), tags.index('MonCotiz'))
        self.assertLess(tags.index('FchVtoPago'), tags.index('CondicionIVAReceptorId'))

    def test_zero_quantity_and_negative_prices_cannot_be_issued(self):
        line = self.invoice.lines.get()
        line.quantity = 0
        line.save()
        with self.assertRaises(ValidationError):
            validate_invoice(self.invoice)

    def test_credit_note_requires_an_authorized_original(self):
        self.invoice.document_type = 13
        with self.assertRaises(ValidationError):
            validate_invoice(self.invoice)

    def test_enabled_configuration_requires_point_of_sale(self):
        self.config.enabled = True
        self.config.point_of_sale = None
        with self.assertRaises(ValidationError):
            self.config.full_clean()

    def test_authorized_invoice_and_lines_are_immutable(self):
        Invoice.objects.filter(pk=self.invoice.pk).update(status='authorized', issuer_snapshot={'name': 'Original'})
        self.invoice.refresh_from_db()
        self.invoice.issue_date = date(2000, 1, 1)
        with self.assertRaises(ValidationError):
            self.invoice.save()
        line = self.invoice.lines.get()
        line.unit_price = 1
        with self.assertRaises(ValidationError):
            line.save()

    def test_invalid_cuit_is_rejected(self):
        self.customer.document_number = '20959815920'
        with self.assertRaises(ValidationError):
            self.customer.full_clean()

    def test_authorized_line_cannot_be_moved_to_a_draft(self):
        Invoice.objects.filter(pk=self.invoice.pk).update(status='authorized')
        draft = Invoice.objects.create(configuration=self.config, customer=self.customer)
        line = self.invoice.lines.get()
        line.invoice = draft
        with self.assertRaises(ValidationError):
            line.save()

    def test_single_issuer_cannot_be_replaced(self):
        with self.assertRaises(ValidationError):
            Issuer.objects.create(name='Otro', cuit='20959815926')
