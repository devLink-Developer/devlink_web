# Facturación propia de devLink

Módulo Django integrado para el CUIT de Eudy David Espinoza Leal, Responsable Monotributo. Acceso exclusivo de superusuarios en `/admin-panel/billing/` o desde «Facturación» en el panel administrativo.

## Incluido

Clientes fiscales vinculables al portal, borradores editables, factura C (11), nota de crédito C (13) parcial o total, pesos argentinos, productos/servicios, CAE, QR, PDF, historial de operaciones y conciliación de respuestas inciertas. No incluye cobros ni emisión automática recurrente.

## Instalación

1. Instalar `requirements.txt` o reconstruir el contenedor web.
2. Ejecutar `python manage.py migrate` y `python manage.py billing_setup` en el entorno de devLink.
3. Montar una carpeta privada, fuera del repositorio y de medios públicos, como solo lectura para la aplicación. El usuario del proceso debe poder leerla. El overlay `docker-compose.billing.yml` agrega ese montaje a la composición existente.
4. Definir `BILLING_CERTIFICATE_ROOT` con la ruta visible **dentro** del servidor/contenedor. En Docker, definir también `BILLING_CERTIFICATE_ROOT_HOST` con la ruta del host. Ver `billing.env.example`.
5. Completar «Configuración fiscal». Los archivos son nombres relativos a la carpeta privada; no se suben mediante la web. Admite CRT/PEM + KEY y PFX/P12. Las contraseñas se resuelven desde variables de entorno, nunca desde campos de texto plano en la base.

Ejemplo de montaje: `docker compose -f docker-compose.yml -f docker-compose.billing.yml up -d --build web`. Esto es una instrucción de despliegue para el operador; el desarrollo no ejecuta despliegues de producción.

El certificado propio verificado es `devlink-produccion.crt`, junto a `devlink-produccion.key`, serie `1d15d41dbafb4217`, con vencimiento el 02/11/2028. La carpeta local protegida es `C:\Users\edespinoza\AppData\Local\devLink\arca\produccion\20261103-142324`. Copiar al servidor mediante un canal privado y mantener permisos restringidos. No poner la clave en Git, correo o `media/`.

## Activación

La configuración inicial tiene emisión deshabilitada. Antes de activarla:

- Definir un `SECRET_KEY` privado, aleatorio y estable de al menos 32 caracteres. Las credenciales reales de ARCA se bloquean con los valores de ejemplo o claves inseguras de Django.
- Completar razón social, CUIT, domicilio fiscal, ingresos brutos e inicio de actividades.
- Asociar el alias `devlink` al servicio `wsfe` en el Administrador de Relaciones de ARCA, si aún no lo está.
- «Comprobar certificado y consultar ARCA» muestra vigencia, estado del servicio y puntos de venta.
- Elegir un punto de venta de webservices activo con modalidad CAE. Los puntos de venta de LiteCore/Invoice pertenecen a sus emisores y no se reutilizan.
- Para producción, establecer explícitamente `BILLING_ALLOW_PRODUCTION=True` en el servidor y luego habilitar la emisión en el formulario. Guardar valida el certificado y consulta el punto de venta antes de activar.
- Homologación utiliza su propio certificado y parámetros. El certificado disponible es de producción y no sirve para homologación.

Diagnóstico local, sin red: `python manage.py billing_check --environment PROD`.
Diagnóstico con consultas, sin emitir: `python manage.py billing_check --environment PROD --online`.

## Operación

Crear cliente → preparar borrador → guardar → revisar receptor, fechas, líneas, total, ambiente y PV → marcar la revisión → emitir. Un comprobante autorizado queda inmutable; su PDF usa las instantáneas de emisor/receptor tomadas al emitir. Las notas de crédito se preparan desde la factura original.

Si ARCA rechaza explícitamente, el borrador puede corregirse y reintentarse manualmente. Si se pierde la respuesta, queda «Resultado incierto» y se bloquea esa serie. «Consultar resultado en ARCA» usa `FECompConsultar`, verifica número/tipo/PV, receptor, concepto, fechas, importes, moneda, condición IVA y comprobante asociado contra la solicitud guardada; recupera el CAE solo si todo coincide. Nunca envía otra autorización por su cuenta. Un bloqueo de sesión PostgreSQL protege al emisor durante todo el envío o conciliación, incluso después de confirmar la reserva. Una operación activa impide liberar su reserva. Las solicitudes aún «En envío» tienen además una espera mínima de dos timeouts más 30 segundos antes de conciliar, para dar margen a la operación interrumpida.

Conciliación operativa: `python manage.py billing_reconcile --environment PROD --user <superusuario> [--invoice <uuid>]`. Procesa hasta 25 pendientes por ejecución. No se crea un scheduler ni se activa por defecto.

Si una consulta negativa fue seguida por una autorización tardía y la secuencia de ARCA ya alcanzó el número incierto, el reintento se detiene en lugar de asignar otro número al mismo borrador. También se bloquea cambiar de serie mientras exista ese antecedente incierto. Revisar el número anterior en ARCA; si corresponde, conservar/importar su comprobante existente en lugar de volver a facturarlo.

Los tickets WSAA se obtienen y guardan cifrados antes de la transacción fiscal, para no perderlos si luego falla una consulta de numeración. Se reutilizan hasta su vencimiento; durante los últimos cinco segundos la aplicación pide esperar, en lugar de solicitar anticipadamente otro ticket que ARCA podría rechazar por `alreadyAuthenticated`. La caché se vincula al ambiente/configuración y huella del certificado; su clave deriva de `SECRET_KEY`. Mantener esa clave protegida y estable. Una rotación de `SECRET_KEY` requiere gestionar la renovación de tickets y puede esperar a su vencimiento. Los logs no guardan CMS, Token, Sign ni claves privadas.

Si una activación falla después de guardar los parámetros, estos permanecen guardados con emisión deshabilitada para poder corregirlos. El ticket de autenticación ya obtenido no se pierde. Los cambios de configuración usan el mismo bloqueo del emisor para no competir con una emisión activa.

## Verificación

Imagen de pruebas Python 3.11: `docker build -f Dockerfile.billing-test -t devlink-billing-test:local .`.
Suite aislada rápida: `docker run --rm --mount type=bind,source=<repo>,target=/app devlink-billing-test:local python manage.py test --noinput`.
Para PostgreSQL, usar una base **exclusiva de pruebas** y pasar `BILLING_TEST_POSTGRES=1`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. Django crea `test_<DB_NAME>`. Nunca apuntar estas variables a bases compartidas o de producción. Las pruebas de concurrencia requieren PostgreSQL; la prueba SQLite no sustituye esos bloqueos.

`devlink_web.test_settings` bloquea todas las llamadas reales a ARCA y la emisión de producción. Las respuestas de aprobación y rechazo de los tests son datos ficticios. Los tests de PDF no generan autorizaciones reales.

## Incorporar un comprobante ya emitido

`python manage.py billing_import --manifest <datos-verificados.json> --pdf <original.pdf> --user <superusuario> [--update-issuer]`

El manifiesto describe ambiente, tipo, punto de venta, número, fechas, CAE, vencimiento, total, emisor, receptor y líneas. `source_sha256` vincula los datos al PDF verificado. El comando comprueba la identidad y el total contra el texto del PDF, valida las líneas, evita duplicados por identidad fiscal/huella y conserva el original completo en el archivo privado `BILLING_ARCHIVE_ROOT`. La descarga de ese registro devuelve el PDF original, incluidas sus copias; no genera un nuevo comprobante ni llama a ARCA. Original, duplicado y triplicado de una misma factura constituyen un solo registro.

La numeración se controla por ambiente, CUIT, punto de venta y tipo. El historial importado fija el mínimo ya registrado. El próximo número mostrado es orientativo: la emisión consulta `FECompUltimoAutorizado` y nunca puede retroceder por debajo del historial. Si ARCA informa menos, se detiene para revisar el punto de venta; no se fuerza otro número localmente. Un punto de venta de Comprobantes en Línea puede requerir otro punto específico para webservices, cuya secuencia es independiente.

El overlay Docker agrega un volumen privado persistente para los PDF originales. Respaldarlo junto con la base de datos. No servir esa carpeta desde Nginx, WhiteNoise ni `MEDIA_URL`.

## Fuentes y criterios reutilizados

Configuración por ambiente, servicio wsfe, timeout 30 s, TRA -5/+10 min y SHA-256 siguen el patrón de LiteCore. Persistencia de intentos, idempotencia y estado incierto con consulta previa siguen los criterios de Invoice. No hay dependencia en ejecución de esos repositorios ni conexión a sus bases.

- [WSAA](https://www.arca.gob.ar/ws/documentacion/wsaa.asp)
- [WSFEv1 v4.7](https://www.arca.gob.ar/ws/documentacion/manuales/manual-desarrollador-ARCA-COMPG.pdf)
- [Especificación QR](https://www.arca.gob.ar/fe/qr/documentos/QRespecificaciones.pdf)
