import hashlib
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from reportlab.pdfgen import canvas

from billing.importing import import_historical_invoice
from billing.models import Invoice


def historical_fixture():
    stream = BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(40, 800, 'CUIT 20959815926 - DNI 12345678 - 00001 00000001')
    pdf.drawString(40, 780, '15/01/2020 CAE 12345678901234 - Total 1500,00')
    pdf.save()
    raw = stream.getvalue()
    return raw, {'environment': 'PROD', 'document_type': 11, 'point_of_sale': 1, 'number': 1,
        'issue_date': '2020-01-15', 'concept': 2, 'service_from': '2020-01-01', 'service_to': '2020-01-15',
        'due_date': '2020-01-15', 'cae': '12345678901234', 'cae_due': '2020-01-25', 'total': '1500.00',
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'issuer': {'name': 'Emisor histórico', 'cuit': '20959815926', 'address': 'Domicilio fiscal',
            'gross_income': 'Exento', 'activities_since': '2020-01-01'},
        'customer': {'name': 'Cliente histórico', 'document_type': 96, 'document_number': '12345678',
            'vat_condition': 5, 'address': 'Domicilio receptor'},
        'lines': [{'description': 'Servicio uno', 'quantity': '1', 'unit_price': '1000.00'},
                  {'description': 'Servicio dos', 'quantity': '1', 'unit_price': '500.00'}]}


class HistoricalImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('import-admin', password='test-only')

    def test_existing_invoice_is_imported_once_with_original_pdf_and_number(self):
        raw, data = historical_fixture()
        with TemporaryDirectory() as root, override_settings(BILLING_ARCHIVE_ROOT=root):
            invoice = import_historical_invoice(data, raw, self.user, update_issuer=True)
            again = import_historical_invoice(data, raw, self.user, update_issuer=True)
            self.assertEqual(invoice.pk, again.pk)
            self.assertEqual(Invoice.objects.count(), 1)
            self.assertEqual((invoice.status, invoice.number, invoice.point_of_sale), ('authorized', 1, 1))
            self.assertEqual(invoice.source, 'import')
            self.assertEqual(str(invoice.total), '1500.00')
            self.client.force_login(self.user)
            response = self.client.get(f'/admin-panel/billing/{invoice.pk}/pdf/')
            self.assertEqual(response.content, raw)
            self.assertEqual(invoice.attempts.get().operation, 'import')

    def test_mismatched_pdf_and_total_do_not_create_authorized_records(self):
        raw, data = historical_fixture()
        with TemporaryDirectory() as root, override_settings(BILLING_ARCHIVE_ROOT=root):
            data['total'] = '1501.00'
            with self.assertRaises(ValidationError):
                import_historical_invoice(data, raw, self.user)
            self.assertFalse(Invoice.objects.exists())
            data['total'] = '1500.00'
            with self.assertRaises(ValidationError):
                import_historical_invoice(data, raw+b'changed', self.user)
            self.assertFalse(Invoice.objects.exists())

    def test_dashboard_shows_next_number_from_historical_series(self):
        raw, data = historical_fixture()
        with TemporaryDirectory() as root, override_settings(BILLING_ARCHIVE_ROOT=root):
            import_historical_invoice(data, raw, self.user)
            self.client.force_login(self.user)
            response = self.client.get('/admin-panel/billing/')
            self.assertContains(response, '00001-00000002')
            self.assertContains(response, 'ARCA')

    def test_owner_protected_pdf_with_empty_read_password_can_be_archived_unchanged(self):
        from pypdf import PdfReader, PdfWriter
        raw, data = historical_fixture()
        writer = PdfWriter(clone_from=PdfReader(BytesIO(raw)))
        writer.encrypt(user_password='', owner_password='fixture-owner', algorithm='AES-128')
        encrypted = BytesIO()
        writer.write(encrypted)
        raw = encrypted.getvalue()
        data['source_sha256'] = hashlib.sha256(raw).hexdigest()
        with TemporaryDirectory() as root, override_settings(BILLING_ARCHIVE_ROOT=root):
            invoice = import_historical_invoice(data, raw, self.user)
            self.client.force_login(self.user)
            self.assertEqual(self.client.get(f'/admin-panel/billing/{invoice.pk}/pdf/').content, raw)

    def test_numeric_substrings_cannot_replace_total_or_recipient(self):
        raw, data = historical_fixture()
        with TemporaryDirectory() as root, override_settings(BILLING_ARCHIVE_ROOT=root):
            data['total'] = '500.00'
            data['lines'] = [{'description': 'Incorrect amount', 'quantity': '1', 'unit_price': '500.00'}]
            with self.assertRaises(ValidationError):
                import_historical_invoice(data, raw, self.user)
            raw, data = historical_fixture()
            data['customer']['document_number'] = '2345678'
            with self.assertRaises(ValidationError):
                import_historical_invoice(data, raw, self.user)
            self.assertFalse(Invoice.objects.exists())
