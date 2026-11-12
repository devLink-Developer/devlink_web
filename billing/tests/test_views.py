from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from billing.models import ArcaConfiguration, Customer, Invoice, InvoiceLine, Issuer


class BillingViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('admin', password='test-only')
        self.customer_user = get_user_model().objects.create_user('client', password='test-only')
        self.issuer = Issuer.objects.create(name='Emisor', cuit='20959815926', address='Dirección',
            gross_income='Exento', activities_since=date(2020, 1, 1))
        self.config = ArcaConfiguration.objects.create(issuer=self.issuer, environment='HOMO', point_of_sale=7)
        self.customer = Customer.objects.create(name='Cliente', document_type=80,
            document_number='20959815926', vat_condition=6, address='Dirección cliente')
        self.invoice = Invoice.objects.create(configuration=self.config, customer=self.customer, issue_date=date.today(), concept=1)
        InvoiceLine.objects.create(invoice=self.invoice, description='<script>hola</script>', quantity=1, unit_price='100')

    def test_clients_cannot_read_any_billing_surface(self):
        self.client.force_login(self.customer_user)
        for url in [reverse('billing:dashboard'), reverse('billing:settings'), reverse('billing:customers'),
                    reverse('billing:detail', args=[self.invoice.pk]), reverse('billing:pdf', args=[self.invoice.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_authorization_requires_csrf_and_post(self):
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.user)
        url = reverse('billing:issue', args=[self.invoice.pk])
        self.assertEqual(secure_client.post(url).status_code, 403)
        self.assertEqual(secure_client.get(url).status_code, 405)

    def test_admin_can_view_dashboard_and_draft_without_network(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('billing:dashboard'))
        self.assertContains(response, 'Facturación')
        detail = self.client.get(reverse('billing:detail', args=[self.invoice.pk]))
        self.assertContains(detail, '&lt;script&gt;hola&lt;/script&gt;')
        self.assertNotContains(detail, '<script>hola</script>')

    def test_draft_does_not_have_fiscal_pdf(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('billing:pdf', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 409)

    def test_authorized_pdf_uses_snapshot_and_cae(self):
        from io import BytesIO
        from pypdf import PdfReader
        self.client.force_login(self.user)
        Invoice.objects.filter(pk=self.invoice.pk).update(status='authorized', number=1, point_of_sale=7,
            environment='HOMO', cae='12345678901234', cae_due=date(2030, 1, 1), total='100.00',
            issuer_snapshot={'name': 'Emisor histórico', 'cuit': '20959815926', 'address': 'Dirección histórica',
                'gross_income': 'Exento', 'activities_since': '2020-01-01'},
            customer_snapshot={'name': 'Cliente histórico', 'document_type': 80, 'document_number': '20959815926',
                'vat_condition': 6, 'address': 'Dirección cliente'})
        response = self.client.get(reverse('billing:pdf', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 200)
        text = ''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('Emisor histórico', text)
        self.assertIn('12345678901234', text)
        self.assertIn('HOMOLOGACIÓN', text)

    def test_save_valid_draft_calculates_server_total(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('billing:new'), {
            'configuration': self.config.pk, 'customer': self.customer.pk, 'document_type': 11,
            'issue_date': date.today().isoformat(), 'concept': 1, 'notes': '',
            'lines-TOTAL_FORMS': '1', 'lines-INITIAL_FORMS': '0', 'lines-MIN_NUM_FORMS': '0',
            'lines-MAX_NUM_FORMS': '50', 'lines-0-description': 'Servicio', 'lines-0-quantity': '2',
            'lines-0-unit_price': '250.00', 'total': '1.00',
        })
        self.assertEqual(response.status_code, 302)
        saved = Invoice.objects.exclude(pk=self.invoice.pk).get()
        self.assertEqual(str(saved.total), '500.00')
        self.assertEqual(saved.status, 'draft')

    def test_issued_draft_cannot_be_edited(self):
        self.client.force_login(self.user)
        Invoice.objects.filter(pk=self.invoice.pk).update(status='authorized')
        self.assertEqual(self.client.post(reverse('billing:edit', args=[self.invoice.pk]), {}).status_code, 409)

    def test_rejected_invoice_review_uses_current_receiver_and_point_of_sale(self):
        self.client.force_login(self.user)
        Invoice.objects.filter(pk=self.invoice.pk).update(status='rejected', point_of_sale=99,
            customer_snapshot={'name': 'Receptor anterior', 'document_number': '0', 'address': 'Anterior'},
            issuer_snapshot={'name': 'Emisor anterior', 'cuit': '0'})
        response = self.client.get(reverse('billing:detail', args=[self.invoice.pk]))
        self.assertContains(response, 'Cliente')
        self.assertNotContains(response, 'Receptor anterior')
        self.assertNotContains(response, 'Emisor anterior')
