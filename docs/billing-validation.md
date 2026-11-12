# Verificación de facturación

Fecha: 2026-11-03. Rama: `codex/facturacion-arca`. Implementación local, sin despliegue ni emisión de comprobantes reales.

## Pruebas automatizadas

- `python manage.py test --noinput` con `devlink_web.test_settings`: 53 casos; verde. SQLite omite 3 casos que requieren bloqueo PostgreSQL.
- Suite PostgreSQL completa de 44 casos: verde, incluidas las 3 pruebas de concurrencia (mismo comprobante/serie, saldo de nota de crédito y emisor suspendido durante el envío).
- Incrementos de importación histórica, secuencia mínima y lectura de PDF protegido: verificados también contra PostgreSQL aislado. No se usaron las bases de LiteCore o Invoice.
- `makemigrations --check --dry-run`: sin cambios pendientes; `manage.py check`: sin problemas; migraciones aplicadas al entorno local.
- Configuración combinada de Compose validada sin iniciar producción.
- Imagen final `devlink-web-billing:local` construida; las 53 pruebas se ejecutaron también desde esa imagen, sin montar el código del host: verde, 3 omitidas por SQLite. Proceso sin privilegios, archivo privado escribible y ausencia de `.env`, SQLite local, capturas y directorios de pruebas comprobados.

Las pruebas observadas fallar antes de corregirlas cubren, entre otros, respuestas incompletas, modificación de líneas autorizadas, moneda incorrecta, orden XML, reserva liberada con un proceso activo, configuración cambiada durante el bloqueo, nota de crédito asociada a otra factura, ticket revertido, datos desactualizados en revisión y subcadenas numéricas al importar un PDF.
También se verificaron los casos de autorización tardía tras una consulta negativa y de terminación del trabajador con el intento todavía `sending`: se impide crear otra autorización con el número siguiente.
La obtención de credenciales reales también se bloquea con un `SECRET_KEY` corto o de ejemplo; regresión observada fallar y pasar, con revisión técnica enfocada cerrada.

## Interfaz y PDF

Guardado de un borrador desde el navegador: 2 × 2500 = 5000 calculados por el servidor; sin envío a ARCA. Luego se retiraron únicamente esos datos ficticios de la vista previa.

Escritorio y móvil: historial, formulario y configuración fiscal. Capturas completas desde el inicio de la página; ancho de contenido y de viewport iguales en móvil. La revisión visual independiente emitió `ship` al alcance de esas capturas y del código de interfaz. El detector mecánico se ejecutó en modo degradado; no sustituye la revisión visual.

PDF generado con datos ficticios: renderizado y revisado. Para el comprobante histórico se sirve el PDF original íntegro; su huella y descarga sin cambios se verificaron. Original, duplicado y triplicado se registran como una sola factura.

## Revisiones independientes

Revisión técnica del módulo y de los cinco riesgos de emisión/conciliación: cerrada después de las correcciones y regresiones. Revisión enfocada adicional de importación y numeración: cerrada. Límites: no se probó una autorización real en ARCA ni se emitió un dictamen de cumplimiento fiscal del formato PDF.

## Activación pendiente

Montar los certificados en el servidor, comprobar permiso al servicio `wsfe` y confirmar un punto de venta activo para webservices. El próximo número mostrado proviene del historial; se confirma en ARCA al emitir. La emisión de producción permanece deshabilitada hasta activación explícita. Ver `docs/billing.md`.

Los datos de importación y documentos privados no se versionan. Conservar la copia privada y ejecutar `billing_import` sobre la base del despliegue cuando se publique el módulo; el comando es idempotente y no pide una nueva autorización.
