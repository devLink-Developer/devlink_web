from datetime import date
from decimal import Decimal
from unittest.mock import patch
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction
from django.utils import timezone
from datetime import timedelta

from billing.models import ArcaConfiguration, Customer, Invoice, InvoiceLine, Issuer
from billing.credits import prepare_total_credits
from billing.services import _credit_balance, issue_invoice, reconcile_invoice


class FakeArca:
    last = 0
    response = None
    failure = None
    calls = []
    consultation = None

    def __init__(self, config):
        self.config = config

    def last_number(self, document_type):
        return type(self).last

    def prepare(self):
        pass

    def authorize(self, payload):
        type(self).calls.append(payload)
        if type(self).failure:
            raise type(self).failure
        return type(self).response

    def consult(self, document_type, number):
        return type(self).consultation


@patch('billing.services.ArcaClient', FakeArca)
class IssuanceTests(TransactionTestCase):
    def setUp(self):
        FakeArca.last, FakeArca.calls, FakeArca.failure = 0, [], None
        FakeArca.response = {'outcome': 'authorized', 'number': 1, 'document_type': 11,
            'point_of_sale': 7, 'cae': '12345678901234', 'cae_due': '20301102', 'messages': []}
        FakeArca.consultation = None
        self.user = get_user_model().objects.create_superuser('billingadmin', password='test-only')
        self.issuer = Issuer.objects.create(name='Emisor', cuit='20959815926', address='Domicilio',
            gross_income='Exento', activities_since=date(2020, 1, 1))
        self.config = ArcaConfiguration.objects.create(issuer=self.issuer, environment='HOMO', point_of_sale=7, enabled=True)
        self.customer = Customer.objects.create(name='Cliente', document_type=80,
            document_number='20959815926', vat_condition=6, address='Domicilio cliente')
        self.invoice = self.make_invoice()

    def make_invoice(self, amount='100.00', **kwargs):
        original = kwargs.get('original')
        is_credit = kwargs.get('document_type') == 13
        if is_credit:
            kwargs.setdefault('cancellation_kind', 'partial')
            kwargs.setdefault('cancellation_reason', 'Ajuste de prueba')
        inv = Invoice.objects.create(configuration=self.config, customer=self.customer,
            issue_date=date.today(), concept=1, **kwargs)
        if is_credit:
            source_line = original.lines.first()
            InvoiceLine.objects.create(invoice=inv, original_line=source_line,
                description=source_line.description, quantity=Decimal(amount) / source_line.unit_price,
                unit_price=source_line.unit_price)
        else:
            InvoiceLine.objects.create(invoice=inv, description='Servicio de prueba', quantity=1, unit_price=amount)
        return inv

    def test_duplicate_submission_returns_existing_authorization(self):
        issue_invoice(self.invoice.pk, self.user)
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual((self.invoice.status, self.invoice.number, self.invoice.cae), ('authorized', 1, '12345678901234'))
        self.assertEqual(len(FakeArca.calls), 1)
        self.assertEqual(self.invoice.attempts.count(), 1)

    def test_timeout_is_persisted_and_blocks_other_invoices_in_same_series(self):
        FakeArca.failure = TimeoutError('network')
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unknown')
        self.assertEqual(self.invoice.number, 1)
        with self.assertRaises(ValidationError):
            issue_invoice(self.make_invoice().pk, self.user)
        self.assertEqual(len(FakeArca.calls), 1)

    def test_incomplete_success_is_unknown_not_authorized(self):
        FakeArca.response = {'outcome': 'authorized', 'number': 1}
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unknown')
        self.assertFalse(self.invoice.cae)

    def test_explicit_rejection_releases_number_and_preserves_attempt(self):
        FakeArca.response = {'outcome': 'rejected', 'messages': [{'code': '10016', 'message': 'Revisar fecha'}]}
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'rejected')
        self.assertIsNone(self.invoice.number)
        self.assertEqual(self.invoice.attempts.get().number, 1)

    def test_reconcile_recovers_authorization_only_for_matching_fiscal_identity(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        FakeArca.consultation = {**FakeArca.response, 'document_number': '20959815926',
            'document_id_type': 80, 'concept': 1, 'issue_date': date.today().strftime('%Y%m%d'), 'total': '100.00',
            'currency': 'PES', 'exchange_rate': '1.00', 'fiscal': {'CbteHasta': '1', 'ImpTotal': '100.00',
                'ImpNeto': '100.00', 'ImpIVA': '0', 'ImpOpEx': '0', 'ImpTotConc': '0', 'ImpTrib': '0',
                'CondicionIVAReceptorId': '6', 'CbtesAsoc': [], 'Iva': False, 'Tributos': False}}
        reconcile_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'authorized')
        self.assertEqual(len(FakeArca.calls), 1)

    def test_reconciliation_does_not_claim_another_customers_invoice(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        FakeArca.consultation = {**FakeArca.response, 'document_number': '20123456789',
            'document_id_type': 80, 'concept': 1, 'issue_date': date.today().strftime('%Y%m%d'), 'total': '100.00'}
        reconcile_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unknown')

    def test_only_explicit_not_found_allows_manual_retry(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        FakeArca.consultation = {'outcome': 'not_found', 'messages': []}
        reconcile_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'rejected')
        self.assertIsNone(self.invoice.number)
        self.assertEqual(len(FakeArca.calls), 1)

    def test_credit_notes_cannot_exceed_original_including_uncertain_attempts(self):
        issue_invoice(self.invoice.pk, self.user)
        original = Invoice.objects.get(pk=self.invoice.pk)
        note = self.make_invoice('70.00', document_type=13, original=original)
        FakeArca.failure = TimeoutError()
        issue_invoice(note.pk, self.user)
        another = self.make_invoice('40.00', document_type=13, original=original)
        with self.assertRaises(ValidationError):
            issue_invoice(another.pk, self.user)
        self.assertEqual(len(FakeArca.calls), 2)

    def test_locked_credit_balance_rejects_overcrediting_one_source_line(self):
        InvoiceLine.objects.create(invoice=self.invoice, description='Segundo servicio', quantity=1, unit_price='100.00')
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        source_line = self.invoice.lines.first()
        prior = self.make_invoice('100.00', document_type=13, original=self.invoice)
        Invoice.objects.filter(pk=prior.pk).update(status='authorized', total='100.00')
        current = self.make_invoice('50.00', document_type=13, original=self.invoice)
        current.lines.update(original_line=source_line, quantity=Decimal('0.500'), unit_price=source_line.unit_price)
        Invoice.objects.filter(pk=current.pk).update(total='50.00')
        current.refresh_from_db()

        with transaction.atomic():
            with self.assertRaises(ValidationError):
                _credit_balance(current)

    def test_disabled_configuration_and_nonadmin_never_send(self):
        self.config.enabled = False
        self.config.save()
        with self.assertRaises(ValidationError):
            issue_invoice(self.invoice.pk, self.user)
        self.user.is_superuser = False
        with self.assertRaises(PermissionError):
            issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(FakeArca.calls, [])

    def test_customer_changes_do_not_change_authorized_snapshot(self):
        issue_invoice(self.invoice.pk, self.user)
        self.customer.name = 'Nombre cambiado'
        self.customer.save()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.customer_snapshot['name'], 'Cliente')
        self.assertEqual(self.invoice.total, Decimal('100.00'))

    def test_credit_note_uses_original_customer_snapshot_after_customer_changes(self):
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        original_document = self.invoice.customer_snapshot['document_number']
        self.customer.document_number = '30712345672'
        self.customer.active = False
        self.customer.save(update_fields=['document_number', 'active'])
        note = self.make_invoice('50.00', document_type=13, original=self.invoice)
        FakeArca.last = 0
        FakeArca.response = {'outcome': 'authorized', 'number': 1, 'document_type': 13,
            'point_of_sale': 7, 'cae': '22345678901234', 'cae_due': '20301102', 'messages': []}

        issue_invoice(note.pk, self.user)

        note.refresh_from_db()
        self.assertEqual(note.status, 'authorized')
        self.assertEqual(note.customer_snapshot, self.invoice.customer_snapshot)
        payload = FakeArca.calls[-1]['FeDetReq']['FECAEDetRequest'][0]
        self.assertEqual(str(payload['DocNro']), original_document)

    def test_consultation_in_another_currency_is_not_recovered(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        FakeArca.consultation = {**FakeArca.response, 'document_number': '20959815926',
            'document_id_type': 80, 'concept': 1, 'issue_date': date.today().strftime('%Y%m%d'), 'total': '100.00',
            'currency': 'DOL', 'exchange_rate': '1.00'}
        reconcile_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'unknown')

    @skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
    def test_concurrent_submission_sees_committed_reservation_and_never_sends_twice(self):
        started, release = Event(), Event()
        real_authorize = FakeArca.authorize
        other = self.make_invoice()

        def slow_authorize(client, payload):
            started.set()
            if not release.wait(15):
                raise TimeoutError()
            return real_authorize(client, payload)

        def first_request():
            try:
                return issue_invoice(self.invoice.pk, self.user).status
            finally:
                connections.close_all()

        with patch.object(FakeArca, 'authorize', slow_authorize), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(first_request)
            try:
                self.assertTrue(started.wait(15))
                self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, 'sending')
                with self.assertRaises(ValidationError):
                    issue_invoice(other.pk, self.user)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=20), 'authorized')
        self.assertEqual(len(FakeArca.calls), 1)

    @skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
    def test_concurrent_partial_credit_reserves_balance_before_total_credit_can_issue(self):
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        note = self.make_invoice('70.00', document_type=13, original=self.invoice)
        started, release = Event(), Event()

        def slow_authorize(client, payload):
            FakeArca.calls.append(payload)
            started.set()
            release.wait(15)
            raise TimeoutError()

        def first_note():
            try:
                return issue_invoice(note.pk, self.user).status
            finally:
                connections.close_all()

        with patch.object(FakeArca, 'authorize', slow_authorize), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(first_note)
            try:
                self.assertTrue(started.wait(15))
                another = Invoice.objects.create(configuration=self.config, customer=self.customer,
                    original=self.invoice, document_type=13, cancellation_kind='total',
                    cancellation_reason='Anulación total concurrente', issue_date=date.today(), concept=1,
                    created_by=self.user)
                InvoiceLine.objects.create(invoice=another, description='Anulación total concurrente',
                    quantity=1, unit_price='30.00')
                Invoice.objects.filter(pk=another.pk).update(total='30.00')
                with self.assertRaises(ValidationError):
                    issue_invoice(another.pk, self.user)
            finally:
                release.set()
            self.assertEqual(future.result(timeout=20), 'unknown')
        self.assertEqual(len(FakeArca.calls), 2)

    @skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
    def test_concurrent_total_draft_preparation_creates_only_one_editable_note(self):
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        barrier = Barrier(2)

        def prepare():
            try:
                connections.close_all()
                barrier.wait(timeout=15)
                prepare_total_credits(self.customer.pk, [self.invoice.pk], 'Solicitud concurrente.', self.user)
                return 'created'
            except ValidationError:
                return 'blocked'
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(future.result(timeout=20) for future in [pool.submit(prepare), pool.submit(prepare)])

        self.assertEqual(results, ['blocked', 'created'])
        self.assertEqual(self.invoice.credit_notes.filter(status__in=('draft', 'rejected')).count(), 1)

    @skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL operation locks')
    def test_active_suspended_sender_cannot_be_reconciled_as_not_found(self):
        started, release = Event(), Event()
        FakeArca.consultation = {'outcome': 'not_found', 'messages': []}
        actual_authorize = FakeArca.authorize

        def suspended(client, payload):
            started.set()
            release.wait(15)
            return actual_authorize(client, payload)

        def send():
            try:
                return issue_invoice(self.invoice.pk, self.user).status
            finally:
                connections.close_all()

        with patch.object(FakeArca, 'authorize', suspended), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(send)
            try:
                self.assertTrue(started.wait(15))
                Invoice.objects.filter(pk=self.invoice.pk).update(updated_at=timezone.now() - timedelta(minutes=10))
                with self.assertRaises(ValidationError):
                    reconcile_invoice(self.invoice.pk, self.user)
                self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, 'sending')
            finally:
                release.set()
            self.assertEqual(future.result(timeout=20), 'authorized')

    def test_changed_configuration_during_locking_aborts_instead_of_using_stale_one(self):
        alternative = ArcaConfiguration.objects.create(issuer=self.issuer, environment='PROD', point_of_sale=22)
        original_get = ArcaConfiguration.objects.select_for_update().select_related('issuer').get

        class RacingQuery:
            def select_related(self, *args):
                return self

            def get(inner, **kwargs):
                Invoice.objects.filter(pk=self.invoice.pk).update(configuration=alternative)
                return original_get(**kwargs)

        with patch.object(ArcaConfiguration.objects, 'select_for_update', return_value=RacingQuery()):
            with self.assertRaises(ValidationError):
                issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(FakeArca.calls, [])

    def test_matching_credit_note_for_another_original_is_not_adopted(self):
        issue_invoice(self.invoice.pk, self.user)
        self.invoice.refresh_from_db()
        note = self.make_invoice('30.00', document_type=13, original=self.invoice)
        FakeArca.failure = TimeoutError()
        issue_invoice(note.pk, self.user)
        FakeArca.consultation = {**FakeArca.response, 'document_type': 13, 'document_number': '20959815926',
            'document_id_type': 80, 'concept': 1, 'issue_date': date.today().strftime('%Y%m%d'), 'total': '30.00',
            'currency': 'PES', 'exchange_rate': '1.00', 'fiscal': {
                'CbteHasta': '1', 'ImpTotal': '30.00', 'ImpNeto': '30.00', 'ImpIVA': '0',
                'ImpOpEx': '0', 'ImpTotConc': '0', 'ImpTrib': '0', 'CondicionIVAReceptorId': '6',
                'CbtesAsoc': [{'Tipo': '11', 'PtoVta': '7', 'Nro': '999', 'Cuit': '20959815926',
                    'CbteFch': date.today().strftime('%Y%m%d')}], 'Iva': False, 'Tributos': False}}
        reconcile_invoice(note.pk, self.user)
        note.refresh_from_db()
        self.assertEqual(note.status, 'unknown')

    def test_new_wsaa_ticket_survives_failure_to_read_last_number(self):
        from datetime import datetime, timezone as datetime_timezone
        from xml.sax.saxutils import escape
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from billing.arca import ArcaClient as RealClient
        from billing.models import AccessTicket
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'fixture')])
        now = datetime.now(datetime_timezone.utc)
        cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(9).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=1)).sign(key, hashes.SHA256())
        material = {'certificate': cert, 'key': key, 'fingerprint': 'f'*64}
        expires = (timezone.now()+timedelta(hours=6)).isoformat()
        ticket_xml = '<loginTicketResponse><header><expirationTime>'+expires+'</expirationTime></header><credentials><token>fixture-private-token</token><sign>fixture-private-sign</sign></credentials></loginTicketResponse>'

        def response(client, url, namespace, method, values):
            if method == 'loginCms':
                return ('<r><loginCmsReturn>'+escape(ticket_xml)+'</loginCmsReturn></r>').encode()
            return b'<root/>'

        with patch('billing.services.ArcaClient', RealClient), patch('billing.arca.certificate_material', return_value=material), patch.object(RealClient, '_post', response):
            with self.assertRaises(ValidationError):
                issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(AccessTicket.objects.count(), 1)
        stored = AccessTicket.objects.get()
        self.assertNotIn('fixture-private-token', stored.encrypted_value)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'draft')

    def test_arca_sequence_cannot_regress_below_registered_history(self):
        old = self.make_invoice()
        Invoice.objects.filter(pk=old.pk).update(status='authorized', environment='HOMO', point_of_sale=7, number=8)
        with self.assertRaises(ValidationError):
            issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(FakeArca.calls, [])

    def test_late_authorization_after_not_found_does_not_reissue_draft_with_next_number(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        FakeArca.consultation = {'outcome': 'not_found', 'messages': []}
        reconcile_invoice(self.invoice.pk, self.user)
        FakeArca.failure = None
        FakeArca.last = 1
        FakeArca.response = {**FakeArca.response, 'number': 2}
        with self.assertRaises(ValidationError):
            issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(len(FakeArca.calls), 1)

    def test_worker_termination_attempt_also_blocks_late_next_number_retry(self):
        FakeArca.failure = TimeoutError()
        issue_invoice(self.invoice.pk, self.user)
        Invoice.objects.filter(pk=self.invoice.pk).update(status='sending', updated_at=timezone.now()-timedelta(minutes=10))
        self.invoice.attempts.filter(operation='authorize').update(outcome='sending', finished_at=None)
        FakeArca.consultation = {'outcome': 'not_found', 'messages': []}
        reconcile_invoice(self.invoice.pk, self.user)
        FakeArca.failure = None
        FakeArca.last = 1
        FakeArca.response = {**FakeArca.response, 'number': 2}
        with self.assertRaises(ValidationError):
            issue_invoice(self.invoice.pk, self.user)
        self.assertEqual(len(FakeArca.calls), 1)
