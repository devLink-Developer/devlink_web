from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree as ET
import requests

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from billing.arca import ArcaClient, WSAA, certificate_material, parse_authorization, parse_consultation
from billing.models import ArcaConfiguration, Issuer


class ArcaBoundaryTests(SimpleTestCase):
    @override_settings(BILLING_NETWORK_ENABLED=True)
    def test_transport_uses_an_ecdhe_only_context_for_arca_tls(self):
        class Response:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def iter_content(self, _size):
                return [b'<root/>']

        session = requests.Session()
        session.post = lambda *args, **kwargs: Response()
        config = ArcaConfiguration(environment='HOMO')

        with patch('billing.arca.requests.Session', return_value=session):
            ArcaClient(config).status()

        context = session.adapters['https://'].poolmanager.connection_pool_kw.get('ssl_context')
        self.assertIsNotNone(context)
        tls12_ciphers = {cipher['name'] for cipher in context.get_ciphers() if cipher['protocol'] != 'TLSv1.3'}
        self.assertTrue(tls12_ciphers)
        self.assertTrue(all(name.startswith('ECDHE-RSA-') for name in tls12_ciphers))

    @override_settings(BILLING_NETWORK_ENABLED=True, SECRET_KEY='your-super-secret-key-change-this')
    def test_real_wsaa_credentials_are_not_cached_with_a_placeholder_server_secret(self):
        with self.assertRaises(ValidationError) as caught:
            ArcaClient(ArcaConfiguration(environment='PROD'))._credentials()
        self.assertIn('SECRET_KEY', str(caught.exception))

    @override_settings(BILLING_NETWORK_ENABLED=True)
    def test_wsaa_rpc_uses_empty_soap_action_and_unqualified_in0(self):
        config = ArcaConfiguration(environment='HOMO')
        with patch('billing.arca.requests.Session') as factory:
            session = factory.return_value.__enter__.return_value
            response = session.post.return_value.__enter__.return_value
            response.status_code = 200
            response.iter_content.return_value = [b'<root/>']
            ArcaClient(config)._post(config.authentication_url, WSAA, 'loginCms', {'in0': 'public-signed-cms'})
            sent = session.post.call_args.kwargs
            self.assertEqual(sent['headers']['SOAPAction'], '""')
            operation = ET.fromstring(sent['data']).find('.//{%s}loginCms' % WSAA)
            self.assertEqual(operation.findtext('in0'), 'public-signed-cms')

    @override_settings(BILLING_NETWORK_ENABLED=True)
    def test_transport_errors_are_actionable_and_do_not_expose_request_secrets(self):
        config = ArcaConfiguration(environment='HOMO')
        with patch('billing.arca.requests.Session') as factory:
            factory.return_value.__enter__.return_value.post.side_effect = requests.ConnectionError('private-token-secret')
            with self.assertRaises(ValidationError) as caught:
                ArcaClient(config).status()
            self.assertNotIn('private-token-secret', str(caught.exception))

    def test_malformed_approval_does_not_become_authorized(self):
        result = parse_authorization(b'<root><FeCabResp><PtoVta>7</PtoVta><CbteTipo>11</CbteTipo></FeCabResp>'
            b'<FECAEDetResponse><Resultado>A</Resultado><CbteDesde>1</CbteDesde></FECAEDetResponse></root>')
        self.assertEqual(result['outcome'], 'unknown')

    def test_complete_approval_reads_fiscal_identity_and_cae(self):
        result = parse_authorization(b'<root><FeCabResp><PtoVta>7</PtoVta><CbteTipo>11</CbteTipo></FeCabResp>'
            b'<FECAEDetResponse><Resultado>A</Resultado><CbteDesde>2</CbteDesde><CbteHasta>2</CbteHasta>'
            b'<CAE>12345678901234</CAE><CAEFchVto>20301102</CAEFchVto></FECAEDetResponse></root>')
        self.assertEqual((result['outcome'], result['number'], result['point_of_sale']), ('authorized', 2, 7))

    def test_technical_consult_error_is_not_not_found(self):
        result = parse_consultation(b'<root><Errors><Err><Code>500</Code><Msg>Servicio no disponible</Msg></Err></Errors></root>')
        self.assertEqual(result['outcome'], 'unknown')

    def test_only_arca_602_is_explicit_not_found(self):
        result = parse_consultation(b'<root><Errors><Err><Code>602</Code><Msg>No existen datos</Msg></Err></Errors></root>')
        self.assertEqual(result['outcome'], 'not_found')

    def test_xml_entities_are_rejected(self):
        with self.assertRaises(ValidationError):
            parse_authorization(b'<!DOCTYPE r [<!ENTITY x "secret">]><r>&x;</r>')

    def test_certificate_must_match_key_and_cuit_and_stay_under_private_root(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'devlink'),
                          x509.NameAttribute(NameOID.SERIAL_NUMBER, 'CUIT 20959815926')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(123).not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=30))
            .sign(key, hashes.SHA256()))
        with TemporaryDirectory() as root:
            Path(root, 'cert.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            Path(root, 'key.key').write_bytes(key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            config = ArcaConfiguration(issuer=Issuer(cuit='20959815926'), environment='PROD',
                certificate_name='cert.crt', private_key_name='key.key')
            with override_settings(BILLING_CERTIFICATE_ROOT=root):
                material = certificate_material(config)
                self.assertEqual(material['serial'], '7b')
                config.certificate_name = '../elsewhere.crt'
                with self.assertRaises(ValidationError):
                    certificate_material(config)
