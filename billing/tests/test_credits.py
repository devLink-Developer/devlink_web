from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from billing.credits import (
    credit_summary,
    discard_credit_draft,
    prepare_partial_credit,
    prepare_total_credits,
)
from billing.models import ArcaConfiguration, Customer, Invoice, InvoiceLine, Issuer
from billing.validation import validate_invoice


class CreditSummaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('credit-admin', password='test-only')
        self.issuer = Issuer.objects.create(name='Emisor', cuit='20959815926', address='Domicilio',
            gross_income='Exento', activities_since=date(2020, 1, 1))
        self.config = ArcaConfiguration.objects.create(issuer=self.issuer, environment='HOMO', point_of_sale=7)
        self.customer = Customer.objects.create(name='Cliente', document_type=80,
            document_number='20959815926', vat_condition=6, address='Domicilio cliente')

    def make_invoice(self, quantity='10', price='10.00', *, source='wsfe'):
        quantity = Decimal(quantity)
        price = Decimal(price)
        invoice = Invoice.objects.create(configuration=self.config, customer=self.customer,
            issue_date=date.today(), concept=1, source=source, created_by=self.user)
        line = InvoiceLine.objects.create(invoice=invoice, description='Servicio', quantity=quantity, unit_price=price)
        total = line.amount
        number = Invoice.objects.filter(document_type=11, status='authorized').count() + 1
        Invoice.objects.filter(pk=invoice.pk).update(status='authorized', total=total, number=number,
            point_of_sale=7, environment='HOMO', cae='12345678901234', cae_due=date(2030, 1, 1),
            issuer_snapshot={'name': 'Emisor', 'cuit': self.issuer.cuit},
            customer_snapshot={'name': self.customer.name, 'document_type': self.customer.document_type,
                'document_number': self.customer.document_number, 'vat_condition': self.customer.vat_condition,
                'address': self.customer.address})
        invoice.refresh_from_db()
        return invoice, line

    def make_credit(self, original, amount, status, *, source_line=None, quantity='1', kind='partial'):
        amount = Decimal(amount)
        quantity = Decimal(quantity)
        note = Invoice.objects.create(configuration=self.config, customer=self.customer, original=original,
            document_type=13, cancellation_kind=kind, cancellation_reason='Ajuste', issue_date=date.today(),
            concept=1, created_by=self.user)
        InvoiceLine.objects.create(invoice=note, original_line=source_line, description='Ajuste',
            quantity=quantity, unit_price=amount / quantity)
        Invoice.objects.filter(pk=note.pk).update(status=status, total=amount)
        note.refresh_from_db()
        return note

    def test_invoice_without_credits_has_its_full_balance_available(self):
        invoice, line = self.make_invoice()

        summary = credit_summary(invoice)

        self.assertEqual(summary.available_amount, Decimal('100.00'))
        self.assertEqual(summary.state, 'open')
        self.assertEqual(summary.state_label, 'Sin anulaciones')
        self.assertEqual(summary.lines[0].line.pk, line.pk)
        self.assertEqual(summary.lines[0].available_quantity, Decimal('10.000'))

    def test_authorized_partial_credit_reduces_amount_and_line_quantity(self):
        invoice, line = self.make_invoice()
        self.make_credit(invoice, '20.00', 'authorized', source_line=line, quantity='2')

        summary = credit_summary(invoice)

        self.assertEqual(summary.authorized_amount, Decimal('20.00'))
        self.assertEqual(summary.available_amount, Decimal('80.00'))
        self.assertEqual(summary.lines[0].authorized_quantity, Decimal('2.000'))
        self.assertEqual(summary.lines[0].available_quantity, Decimal('8.000'))
        self.assertEqual(summary.state, 'partial')

    def test_pending_and_unknown_credits_reserve_balance(self):
        invoice, line = self.make_invoice()
        self.make_credit(invoice, '20.00', 'sending', source_line=line, quantity='2')
        self.make_credit(invoice, '10.00', 'unknown', source_line=line, quantity='1')

        summary = credit_summary(invoice)

        self.assertEqual(summary.reserved_amount, Decimal('30.00'))
        self.assertEqual(summary.available_amount, Decimal('70.00'))
        self.assertEqual(summary.lines[0].reserved_quantity, Decimal('3.000'))
        self.assertEqual(summary.state, 'pending')

    def test_editable_credit_does_not_reserve_balance_but_is_reported(self):
        invoice, line = self.make_invoice()
        draft = self.make_credit(invoice, '20.00', 'draft', source_line=line, quantity='2')

        summary = credit_summary(invoice)

        self.assertEqual(summary.available_amount, Decimal('100.00'))
        self.assertEqual(summary.existing_editable_note.pk, draft.pk)
        self.assertEqual(summary.state, 'draft')

    def test_fully_credited_invoice_is_cancelled(self):
        invoice, _ = self.make_invoice()
        self.make_credit(invoice, '100.00', 'authorized', kind='total')

        summary = credit_summary(invoice)

        self.assertEqual(summary.available_amount, Decimal('0.00'))
        self.assertEqual(summary.state, 'cancelled')
        self.assertEqual(summary.state_label, 'Anulada totalmente')

    def test_historical_unlinked_partial_credit_blocks_quantity_automation(self):
        invoice, line = self.make_invoice()
        self.make_credit(invoice, '20.00', 'authorized', source_line=None, quantity='1', kind='partial')

        summary = credit_summary(invoice)

        self.assertEqual(summary.available_amount, Decimal('80.00'))
        self.assertEqual(summary.lines[0].available_quantity, line.quantity)
        self.assertTrue(summary.partial_block_reason)

    def test_money_balance_remains_exact_when_line_rounding_is_not_additive(self):
        invoice, line = self.make_invoice(quantity='3', price='0.3333')
        self.make_credit(invoice, '0.33', 'authorized', source_line=line, quantity='1')

        summary = credit_summary(invoice)

        self.assertEqual(invoice.total, Decimal('1.00'))
        self.assertEqual(summary.available_amount, Decimal('0.67'))
        self.assertEqual(summary.lines[0].available_quantity, Decimal('2.000'))

    def test_total_cancellation_creates_one_exact_draft_per_invoice(self):
        first, _ = self.make_invoice(quantity='3', price='0.3333')
        second, _ = self.make_invoice(quantity='2', price='25.00')

        notes = prepare_total_credits(
            self.customer.pk,
            [first.pk, second.pk],
            'El servicio fue cancelado por el cliente.',
            self.user,
        )

        self.assertEqual(len(notes), 2)
        self.assertEqual({note.original_id for note in notes}, {first.pk, second.pk})
        for note in notes:
            self.assertEqual(note.document_type, 13)
            self.assertEqual(note.cancellation_kind, 'total')
            self.assertEqual(note.cancellation_reason, 'El servicio fue cancelado por el cliente.')
            self.assertEqual(note.lines.count(), 1)
            self.assertEqual(note.lines.get().quantity, Decimal('1.000'))
            self.assertEqual(note.lines.get().amount, note.original.total)
            self.assertIsNone(note.lines.get().original_line_id)

    def test_total_batch_is_atomic_when_one_invoice_cannot_be_cancelled(self):
        first, _ = self.make_invoice()
        second, line = self.make_invoice()
        self.make_credit(second, '10.00', 'sending', source_line=line, quantity='1')

        with self.assertRaises(ValidationError):
            prepare_total_credits(self.customer.pk, [first.pk, second.pk], 'Cancelación solicitada.', self.user)

        self.assertFalse(Invoice.objects.filter(document_type=13, status='draft').exists())

    def test_partial_cancellation_copies_source_line_and_price(self):
        invoice, line = self.make_invoice(quantity='10', price='12.3456')

        note = prepare_partial_credit(
            invoice.pk,
            {line.pk: '2.500'},
            'Ajuste parcial del servicio.',
            self.user,
        )

        credit_line = note.lines.get()
        self.assertEqual(note.cancellation_kind, 'partial')
        self.assertEqual(note.cancellation_reason, 'Ajuste parcial del servicio.')
        self.assertEqual(credit_line.original_line_id, line.pk)
        self.assertEqual(credit_line.description, line.description)
        self.assertEqual(credit_line.quantity, Decimal('2.500'))
        self.assertEqual(credit_line.unit_price, Decimal('12.3456'))
        self.assertEqual(note.total, Decimal('30.86'))

    def test_partial_cancellation_rejects_more_than_remaining_quantity(self):
        invoice, line = self.make_invoice(quantity='3', price='10.00')
        self.make_credit(invoice, '20.00', 'authorized', source_line=line, quantity='2')

        with self.assertRaises(ValidationError):
            prepare_partial_credit(invoice.pk, {line.pk: '1.001'}, 'Cantidad incorrecta.', self.user)

        self.assertEqual(invoice.credit_notes.filter(status='draft').count(), 0)

    def test_imported_invoice_requires_explicit_line_confirmation_for_partial_credit(self):
        invoice, line = self.make_invoice(source='import')

        with self.assertRaises(ValidationError):
            prepare_partial_credit(invoice.pk, {line.pk: '1'}, 'Ajuste importado.', self.user)

        note = prepare_partial_credit(
            invoice.pk,
            {line.pk: '1'},
            'Ajuste importado.',
            self.user,
            imported_lines_confirmed=True,
        )
        self.assertEqual(note.lines.get().original_line_id, line.pk)

    def test_existing_editable_note_blocks_another_cancellation_draft(self):
        invoice, line = self.make_invoice()
        draft = self.make_credit(invoice, '10.00', 'draft', source_line=line, quantity='1')

        with self.assertRaisesMessage(ValidationError, 'ya tiene una nota de crédito editable'):
            prepare_total_credits(self.customer.pk, [invoice.pk], 'Otra anulación.', self.user)

        self.assertEqual(invoice.credit_notes.filter(status='draft').get(), draft)

    def test_discard_only_removes_editable_credit_note(self):
        invoice, line = self.make_invoice()
        draft = self.make_credit(invoice, '10.00', 'draft', source_line=line, quantity='1')

        discard_credit_draft(draft.pk, self.user)

        self.assertFalse(Invoice.objects.filter(pk=draft.pk).exists())
        authorized = self.make_credit(invoice, '10.00', 'authorized', source_line=line, quantity='1')
        with self.assertRaises(ValidationError):
            discard_credit_draft(authorized.pk, self.user)

    def test_cancellation_requires_a_reason_and_an_admin(self):
        invoice, _ = self.make_invoice()
        regular = get_user_model().objects.create_user('operator', password='test-only')

        with self.assertRaises(ValidationError):
            prepare_total_credits(self.customer.pk, [invoice.pk], '   ', self.user)
        with self.assertRaises(PermissionError):
            prepare_total_credits(self.customer.pk, [invoice.pk], 'Motivo válido.', regular)

    def test_credit_validation_requires_cancellation_metadata(self):
        invoice, line = self.make_invoice()
        note = prepare_partial_credit(invoice.pk, {line.pk: '1'}, 'Motivo original.', self.user)
        note.cancellation_reason = ''

        with self.assertRaises(ValidationError):
            validate_invoice(note)

    def test_partial_credit_validation_preserves_original_unit_price(self):
        invoice, line = self.make_invoice(price='12.3456')
        note = prepare_partial_credit(invoice.pk, {line.pk: '1'}, 'Ajuste parcial.', self.user)
        credit_line = note.lines.get()
        credit_line.unit_price = Decimal('1.0000')
        credit_line.save()

        with self.assertRaises(ValidationError):
            validate_invoice(note)

    def test_total_credit_validation_uses_one_unlinked_summary_line(self):
        invoice, line = self.make_invoice()
        note = prepare_total_credits(self.customer.pk, [invoice.pk], 'Anulación total.', self.user)[0]
        credit_line = note.lines.get()
        credit_line.original_line = line
        credit_line.save()

        with self.assertRaises(ValidationError):
            validate_invoice(note)

