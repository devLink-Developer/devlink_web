"""ARCA WSAA/WSFE boundaries. No authorization retries and no credential logging."""
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7, pkcs12
from cryptography.x509.oid import NameOID
from defusedxml import ElementTree as SafeET
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AccessTicket, ArcaConfiguration

SOAP = 'http://schemas.xmlsoap.org/soap/envelope/'
WSFE = 'http://ar.gov.afip.dif.FEV1/'
WSAA = 'http://wsaa.view.sua.dvadac.desein.afip.gov'
MAX_RESPONSE = 2 * 1024 * 1024


def private_file(name):
    configured = settings.BILLING_CERTIFICATE_ROOT
    if not configured or not name:
        raise ValidationError('Configurá la carpeta privada y los nombres de archivos del certificado.')
    root = Path(configured).resolve()
    for public_root in (settings.MEDIA_ROOT, settings.STATIC_ROOT, settings.BASE_DIR):
        if root.is_relative_to(Path(public_root).resolve()):
            raise ValidationError('La carpeta de certificados debe estar fuera del repositorio y de los medios públicos.')
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file():
        raise ValidationError('No se encontró el archivo dentro de la carpeta privada autorizada.')
    if path.stat().st_size > MAX_RESPONSE:
        raise ValidationError('El archivo del certificado supera el tamaño permitido.')
    return path


def certificate_material(config):
    path = private_file(config.certificate_name)
    password = None
    if config.password_env:
        value = os.environ.get(config.password_env)
        if value is None:
            raise ValidationError('No está definida la variable de contraseña del certificado.')
        password = value.encode()
    try:
        raw = path.read_bytes()
        if path.suffix.lower() in ('.pfx', '.p12'):
            key, cert, _ = pkcs12.load_key_and_certificates(raw, password)
        else:
            cert = x509.load_pem_x509_certificate(raw) if b'-----BEGIN' in raw else x509.load_der_x509_certificate(raw)
            key = serialization.load_pem_private_key(private_file(config.private_key_name).read_bytes(), password=password)
        if not cert or not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
            raise ValueError('RSA certificate required')
        encoding, fmt = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        if key.public_key().public_bytes(encoding, fmt) != cert.public_key().public_bytes(encoding, fmt):
            raise ValueError('key mismatch')
        now = datetime.now(dt_timezone.utc)
        if not cert.not_valid_before_utc <= now < cert.not_valid_after_utc:
            raise ValueError('certificate expired or not yet valid')
        serials = cert.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
        if not any(a.value.strip() == f'CUIT {config.issuer.cuit}' for a in serials):
            raise ValueError('CUIT mismatch')
        issuers = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        if config.environment == 'HOMO' and any(a.value.lower() == 'computadores' for a in issuers):
            raise ValidationError('Este certificado es de producción; homologación requiere otro certificado.')
        if config.environment == 'PROD' and any('test' in a.value.lower() or 'homo' in a.value.lower() for a in issuers):
            raise ValidationError('Este certificado es de homologación; producción requiere otro certificado.')
    except (ValueError, TypeError, OSError) as exc:
        raise ValidationError('Revisá vigencia, CUIT, contraseña y correspondencia entre certificado y clave privada.') from exc
    return {'key': key, 'certificate': cert, 'fingerprint': cert.fingerprint(hashes.SHA256()).hex(),
        'expires_at': cert.not_valid_after_utc, 'serial': format(cert.serial_number, 'x')}


def xml_root(raw):
    try:
        if len(raw) > MAX_RESPONSE:
            raise ValueError('large response')
        root = SafeET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        for element in root.iter():
            element.tag = element.tag.rsplit('}', 1)[-1]
        return root
    except Exception as exc:
        raise ValidationError('ARCA devolvió XML inválido o no seguro; el resultado debe verificarse.') from exc


def text(root, name, default=''):
    return root.findtext('.//' + name, default=default) if root is not None else default


def integer(root, name):
    try:
        return int(text(root, name))
    except (ValueError, TypeError):
        return None


def messages(root):
    return [{'code': text(node, 'Code')[:20], 'message': text(node, 'Msg')[:500]}
        for node in root.findall('.//Err') + root.findall('.//Obs') + root.findall('.//Evt')]


def valid_cae(cae, due):
    try:
        datetime.strptime(due, '%Y%m%d')
        return len(cae) == 14 and cae.isascii() and cae.isdigit() and int(cae) > 0
    except (ValueError, TypeError):
        return False


def parse_authorization(raw):
    root = xml_root(raw)
    detail = root.find('.//FECAEDetResponse')
    header = root.find('.//FeCabResp')
    result = {'outcome': 'unknown', 'messages': messages(root)}
    if detail is not None and text(detail, 'Resultado') == 'R':
        result['outcome'] = 'rejected'
    if detail is not None and text(detail, 'Resultado') == 'A':
        cae, due = text(detail, 'CAE'), text(detail, 'CAEFchVto')
        number = integer(detail, 'CbteDesde')
        if valid_cae(cae, due) and number and number == integer(detail, 'CbteHasta') and header is not None:
            result.update(outcome='authorized', number=number, document_type=integer(header, 'CbteTipo'),
                point_of_sale=integer(header, 'PtoVta'), cae=cae, cae_due=due)
    return result


def parse_consultation(raw):
    root = xml_root(raw)
    result = {'outcome': 'unknown', 'messages': messages(root)}
    detail = root.find('.//ResultGet')
    if detail is None:
        if any(m['code'] == '602' for m in result['messages']):
            result['outcome'] = 'not_found'
        return result
    cae, due = text(detail, 'CodAutorizacion'), text(detail, 'FchVto')
    if valid_cae(cae, due) and text(detail, 'EmisionTipo') in ('CAE', ''):
        result.update(outcome='authorized', number=integer(detail, 'CbteDesde'),
            document_type=integer(detail, 'CbteTipo'), point_of_sale=integer(detail, 'PtoVta'),
            cae=cae, cae_due=due, concept=integer(detail, 'Concepto'),
            document_id_type=integer(detail, 'DocTipo'), document_number=text(detail, 'DocNro'),
            issue_date=text(detail, 'CbteFch'), total=text(detail, 'ImpTotal'),
            currency=text(detail, 'MonId'), exchange_rate=text(detail, 'MonCotiz'),
            service_from=text(detail, 'FchServDesde'), service_to=text(detail, 'FchServHasta'),
            due_date=text(detail, 'FchVtoPago'))
        result['fiscal'] = {name: text(detail, name) for name in (
            'CbteHasta', 'ImpTotal', 'ImpNeto', 'ImpIVA', 'ImpOpEx', 'ImpTotConc', 'ImpTrib', 'CondicionIVAReceptorId')}
        result['fiscal'].update(CbtesAsoc=[{name: text(node, name) for name in ('Tipo', 'PtoVta', 'Nro', 'Cuit', 'CbteFch')}
            for node in detail.findall('.//CbteAsoc')], Iva=detail.find('.//AlicIva') is not None,
            Tributos=detail.find('.//Tributo') is not None)
    return result


def append_xml(parent, values, namespace):
    for name, value in values.items():
        if isinstance(value, list):
            for item in value:
                child = ET.SubElement(parent, f'{{{namespace}}}{name}')
                append_xml(child, item, namespace)
        else:
            child = ET.SubElement(parent, f'{{{namespace}}}{name}')
            if isinstance(value, dict):
                append_xml(child, value, namespace)
            elif value is not None:
                child.text = str(value)


class ArcaClient:
    def __init__(self, configuration):
        self.config = configuration
        self._auth = None

    def prepare(self):
        self._auth = self._credentials()

    def _post(self, url, namespace, method, values):
        if not settings.BILLING_NETWORK_ENABLED:
            raise ValidationError('Las llamadas a ARCA están deshabilitadas en este entorno de pruebas.')
        if url not in (self.config.authentication_url, self.config.webservice_url):
            raise ValidationError('Destino ARCA no autorizado.')
        envelope = ET.Element(f'{{{SOAP}}}Envelope')
        body = ET.SubElement(envelope, f'{{{SOAP}}}Body')
        operation = ET.SubElement(body, f'{{{namespace}}}{method}')
        if namespace == WSAA:
            ET.SubElement(operation, 'in0').text = values['in0']
        else:
            append_xml(operation, values, namespace)
        try:
            return self._transport(url, namespace, method, envelope)
        except requests.RequestException as exc:
            raise ValidationError('No se pudo comunicar con ARCA. Revisá la conexión y volvé a consultar el estado.') from None

    def _transport(self, url, namespace, method, envelope):
        # Explicitly disable retries, redirections, netrc credentials and proxy discovery.
        with requests.Session() as session:
            session.trust_env = False
            with session.post(url, data=ET.tostring(envelope, encoding='utf-8', xml_declaration=True),
                    headers={'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '""' if namespace == WSAA else f'"{namespace}{method}"'},
                    timeout=(5, self.config.timeout), allow_redirects=False, stream=True) as response:
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_RESPONSE:
                        raise ValidationError('ARCA devolvió una respuesta demasiado grande.')
                    chunks.append(chunk)
                raw = b''.join(chunks)
                if response.status_code != 200:
                    raise ValidationError(f'ARCA no confirmó la operación (HTTP {response.status_code}). Revisá conexión, certificado y autorización wsfe.')
                return raw

    def _credentials(self):
        if settings.BILLING_NETWORK_ENABLED and (
            len(settings.SECRET_KEY) < 32
            or settings.SECRET_KEY.startswith('django-insecure-')
            or settings.SECRET_KEY in {
                'your-super-secret-key-change-this',
                'devlink-isolated-billing-tests-only',
            }
        ):
            raise ValidationError(
                'Configurá un SECRET_KEY seguro y estable antes de obtener credenciales reales de ARCA.'
            )
        material = certificate_material(self.config)
        cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(
            ('devlink-billing-ticket:' + settings.SECRET_KEY).encode()).digest()))
        with transaction.atomic():
            ArcaConfiguration.objects.select_for_update().get(pk=self.config.pk)
            ticket = AccessTicket.objects.filter(configuration=self.config, fingerprint=material['fingerprint']).first()
            if ticket and ticket.expires_at > timezone.now():
                if ticket.expires_at <= timezone.now() + timedelta(seconds=5):
                    raise ValidationError('El ticket está por vencer. Esperá unos segundos y volvé a intentar.')
                try:
                    return json.loads(cipher.decrypt(ticket.encrypted_value.encode()))
                except Exception as exc:
                    raise ValidationError('El ticket guardado no puede descifrarse. Revisá la clave del servidor antes de renovarlo.') from exc
            now = timezone.now()
            tra = ET.Element('loginTicketRequest', version='1.0')
            header = ET.SubElement(tra, 'header')
            ET.SubElement(header, 'uniqueId').text = str(int(now.timestamp()))
            ET.SubElement(header, 'generationTime').text = (now + timedelta(minutes=self.config.generation_offset)).isoformat()
            ET.SubElement(header, 'expirationTime').text = (now + timedelta(minutes=self.config.expiration_window)).isoformat()
            ET.SubElement(tra, 'service').text = 'wsfe'
            cms = (pkcs7.PKCS7SignatureBuilder().set_data(ET.tostring(tra, encoding='utf-8', xml_declaration=True))
                .add_signer(material['certificate'], material['key'], hashes.SHA256())
                .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary]))
            raw = self._post(self.config.authentication_url, WSAA, 'loginCms', {'in0': base64.b64encode(cms).decode()})
            response = xml_root(raw)
            inner = text(response, 'loginCmsReturn')
            if not inner:
                raise ValidationError('WSAA no otorgó un ticket. Revisá la autorización del certificado al servicio wsfe.')
            ticket_xml = xml_root(inner.encode())
            try:
                expires_at = datetime.fromisoformat(text(ticket_xml, 'expirationTime').replace('Z', '+00:00'))
                if expires_at.tzinfo is None or expires_at <= timezone.now() + timedelta(seconds=5):
                    raise ValueError('invalid expiration')
                auth = {'Token': text(ticket_xml, 'token'), 'Sign': text(ticket_xml, 'sign'), 'Cuit': self.config.issuer.cuit}
                if not auth['Token'] or not auth['Sign']:
                    raise ValueError('missing credentials')
            except (ValueError, TypeError) as exc:
                raise ValidationError('WSAA devolvió un ticket incompleto o vencido.') from exc
            AccessTicket.objects.update_or_create(configuration=self.config, fingerprint=material['fingerprint'],
                defaults={'encrypted_value': cipher.encrypt(json.dumps(auth).encode()).decode(), 'expires_at': expires_at})
            return auth

    def _wsfe(self, method, values):
        if self._auth is None:
            self.prepare()
        return self._post(self.config.webservice_url, WSFE, method, {'Auth': self._auth, **values})

    def last_number(self, document_type):
        root = xml_root(self._wsfe('FECompUltimoAutorizado', {'PtoVta': self.config.point_of_sale, 'CbteTipo': document_type}))
        number = integer(root, 'CbteNro')
        if number is None or number < 0 or root.find('.//Err') is not None:
            raise ValidationError('ARCA no confirmó el último número autorizado; no se reservó otro número.')
        return number

    def authorize(self, payload):
        return parse_authorization(self._wsfe('FECAESolicitar', {'FeCAEReq': payload}))

    def consult(self, document_type, number):
        return parse_consultation(self._wsfe('FECompConsultar', {'FeCompConsReq': {
            'CbteTipo': document_type, 'CbteNro': number, 'PtoVta': self.config.point_of_sale}}))

    def points_of_sale(self):
        root = xml_root(self._wsfe('FEParamGetPtosVenta', {}))
        if root.find('.//Err') is not None:
            raise ValidationError('ARCA no permitió consultar los puntos de venta. Revisá la autorización wsfe.')
        return [{'number': integer(node, 'Nro'), 'emission_type': text(node, 'EmisionTipo'),
            'blocked': text(node, 'Bloqueado').upper() not in ('N', 'NO', 'FALSE', '0', ''),
            'closed': text(node, 'FchBaja') not in ('', 'NULL', '0')} for node in root.findall('.//PtoVenta')]

    def status(self):
        root = xml_root(self._post(self.config.webservice_url, WSFE, 'FEDummy', {}))
        return {key: text(root, key) for key in ('AppServer', 'DbServer', 'AuthServer')}
