from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from billing.credits import prepare_partial_credit, prepare_total_credits
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

    def authorize(self, invoice=None, *, number=1, source='wsfe'):
        invoice = invoice or self.invoice
        total = sum((line.amount for line in invoice.lines.all()), 0)
        Invoice.objects.filter(pk=invoice.pk).update(status='authorized', number=number, point_of_sale=7,
            environment='HOMO', cae='12345678901234', cae_due=date(2030, 1, 1), total=total, source=source,
            issuer_snapshot={'name': 'Emisor', 'cuit': self.issuer.cuit},
            customer_snapshot={'name': invoice.customer.name, 'document_type': invoice.customer.document_type,
                'document_number': invoice.customer.document_number, 'vat_condition': invoice.customer.vat_condition,
                'address': invoice.customer.address})
        invoice.refresh_from_db()
        return invoice

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
        self.assertContains(response, 'Anulaciones')
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

    def test_cancellation_surfaces_are_admin_only_and_csrf_protected(self):
        self.authorize()
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse('billing:cancellations')).status_code, 403)
        self.assertEqual(self.client.get(reverse('billing:cancellation_partial', args=[self.invoice.pk])).status_code, 403)

        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.user)
        self.assertEqual(secure_client.post(reverse('billing:cancellations'), {
            'customer': self.customer.pk, 'invoices': [self.invoice.pk], 'reason': 'Motivo',
        }).status_code, 403)
        self.assertEqual(secure_client.get(reverse('billing:credit_discard', args=[self.invoice.pk])).status_code, 405)

    def test_cancellation_workspace_filters_invoices_by_customer_and_marks_cancelled(self):
        self.authorize()
        other_customer = Customer.objects.create(name='Otro', document_type=80,
            document_number='30712345672', vat_condition=6, address='Otra dirección')
        other = Invoice.objects.create(configuration=self.config, customer=other_customer,
            issue_date=date.today(), concept=1, created_by=self.user)
        InvoiceLine.objects.create(invoice=other, description='Otro servicio', quantity=1, unit_price='50')
        self.authorize(other, number=2)
        note = prepare_total_credits(self.customer.pk, [self.invoice.pk], 'Anulación completa.', self.user)[0]
        Invoice.objects.filter(pk=note.pk).update(status='authorized', number=1, point_of_sale=7,
            environment='HOMO', cae='22345678901234', cae_due=date(2030, 1, 1))

        self.client.force_login(self.user)
        response = self.client.get(reverse('billing:cancellations'), {'customer': self.customer.pk})

        self.assertEqual(response.status_code, 200)
        summaries = response.context['summaries']
        self.assertEqual([item.invoice.pk for item in summaries], [self.invoice.pk])
        self.assertEqual(summaries[0].state, 'cancelled')
        self.assertContains(response, 'Anulada totalmente')
        self.assertContains(response, f'value="{self.invoice.pk}" disabled', html=False)

    def test_total_cancellation_post_creates_one_draft_per_selected_invoice(self):
        self.authorize()
        second = Invoice.objects.create(configuration=self.config, customer=self.customer,
            issue_date=date.today(), concept=1, created_by=self.user)
        InvoiceLine.objects.create(invoice=second, description='Segundo servicio', quantity=1, unit_price='50')
        self.authorize(second, number=2)
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:cancellations'), {
            'customer': self.customer.pk,
            'invoices': [str(self.invoice.pk), str(second.pk)],
            'reason': 'El cliente solicitó la anulación total.',
        })

        self.assertRedirects(response, reverse('billing:cancellations') + f'?customer={self.customer.pk}',
            fetch_redirect_response=False)
        self.assertEqual(Invoice.objects.filter(document_type=13, status='draft').count(), 2)

    def test_partial_cancellation_uses_server_side_line_data_and_import_confirmation(self):
        self.authorize(source='import')
        line = self.invoice.lines.get()
        self.client.force_login(self.user)
        url = reverse('billing:cancellation_partial', args=[self.invoice.pk])

        rejected = self.client.post(url, {'reason': 'Ajuste parcial.', f'line_{line.pk}': '0.500'})
        self.assertEqual(rejected.status_code, 200)
        self.assertFalse(self.invoice.credit_notes.exists())

        accepted = self.client.post(url, {
            'reason': 'Ajuste parcial.', f'line_{line.pk}': '0.500', 'confirm_imported': 'on',
        })
        note = self.invoice.credit_notes.get()
        self.assertRedirects(accepted, reverse('billing:detail', args=[note.pk]), fetch_redirect_response=False)
        credit_line = note.lines.get()
        self.assertEqual(credit_line.original_line_id, line.pk)
        self.assertEqual(credit_line.unit_price, line.unit_price)

    def test_old_credit_note_action_continues_existing_draft_without_duplication(self):
        self.authorize()
        line = self.invoice.lines.get()
        draft = prepare_partial_credit(self.invoice.pk, {line.pk: '0.500'}, 'Ajuste previo.', self.user)
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:credit_note', args=[self.invoice.pk]))

        self.assertRedirects(response, reverse('billing:detail', args=[draft.pk]), fetch_redirect_response=False)
        self.assertEqual(self.invoice.credit_notes.count(), 1)

    def test_discard_route_only_removes_editable_credit_notes(self):
        self.authorize()
        draft = prepare_total_credits(self.customer.pk, [self.invoice.pk], 'Borrador descartable.', self.user)[0]
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:credit_discard', args=[draft.pk]))

        self.assertRedirects(response, reverse('billing:cancellations') + f'?customer={self.customer.pk}',
            fetch_redirect_response=False)
        self.assertFalse(Invoice.objects.filter(pk=draft.pk).exists())

        authorized = prepare_total_credits(self.customer.pk, [self.invoice.pk], 'Nota autorizada.', self.user)[0]
        Invoice.objects.filter(pk=authorized.pk).update(status='authorized')
        response = self.client.post(reverse('billing:credit_discard', args=[authorized.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Invoice.objects.filter(pk=authorized.pk).exists())

    def test_total_selection_rejects_invoice_from_another_customer(self):
        self.authorize()
        other_customer = Customer.objects.create(name='Otro', document_type=80,
            document_number='30712345672', vat_condition=6, address='Otra dirección')
        other = Invoice.objects.create(configuration=self.config, customer=other_customer,
            issue_date=date.today(), concept=1, created_by=self.user)
        InvoiceLine.objects.create(invoice=other, description='Otro servicio', quantity=1, unit_price='50')
        self.authorize(other, number=2)
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:cancellations'), {
            'customer': self.customer.pk, 'invoices': [str(other.pk)], 'reason': 'Selección inválida.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invoice.objects.filter(document_type=13).exists())

    def test_cancellation_workspace_shows_balances_and_continue_existing_draft(self):
        self.authorize()
        line = self.invoice.lines.get()
        draft = prepare_partial_credit(self.invoice.pk, {line.pk: '0.250'}, 'Ajuste en preparación.', self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse('billing:cancellations'), {'customer': self.customer.pk})

        self.assertContains(response, 'Anulación en preparación')
        self.assertContains(response, '$ 100,00')
        self.assertContains(response, reverse('billing:detail', args=[draft.pk]))
        self.assertContains(response, 'Continuar borrador')

    def test_detail_shows_cancellation_reason_and_related_credit_notes(self):
        self.authorize()
        line = self.invoice.lines.get()
        note = prepare_partial_credit(self.invoice.pk, {line.pk: '0.500'}, 'Bonificación acordada con el cliente.', self.user)
        self.client.force_login(self.user)

        note_detail = self.client.get(reverse('billing:detail', args=[note.pk]))
        self.assertContains(note_detail, 'Anulación parcial')
        self.assertContains(note_detail, 'Bonificación acordada con el cliente.')

        original_detail = self.client.get(reverse('billing:detail', args=[self.invoice.pk]))
        self.assertContains(original_detail, 'Notas de crédito asociadas')
        self.assertContains(original_detail, 'Bonificación acordada con el cliente.')
        self.assertContains(original_detail, reverse('billing:detail', args=[note.pk]))

    def test_credit_note_cannot_be_edited_with_generic_invoice_form(self):
        self.authorize()
        note = prepare_total_credits(self.customer.pk, [self.invoice.pk], 'Anulación total.', self.user)[0]
        self.client.force_login(self.user)

        response = self.client.get(reverse('billing:edit', args=[note.pk]))

        self.assertEqual(response.status_code, 409)
