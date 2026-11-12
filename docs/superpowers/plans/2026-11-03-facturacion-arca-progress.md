# SDD ledger — plan: docs/superpowers/plans/2026-11-03-facturacion-arca.md

Ruling: rama propia en el checkout actual, conservando archivos modificados del usuario — permite revisar el módulo sin duplicar ni perder trabajo existente.
Ruling: ejecutar en esta sesión con revisión independiente final — la aprobación del alcance autoriza implementación; no se agrega otra pausa para decisiones rutinarias.
Pre-flight: modelos → servicios → vistas/PDF; interfaces coherentes con el diseño aprobado.
Baseline: pruebas existentes de accounts/admin_panel/dashboard son archivos vacíos; el venv local no tiene Django. Se preparará un entorno Python 3.11 y PostgreSQL aislado para comprobación real.

Task 1: complete — modelos, migraciones y validación; pruebas fiscales observadas fallar y pasar.
Task 2: complete — SOAP contrastado con WSDL públicos; reserva persistida y bloqueo de sesión PostgreSQL; TA cifrado guardado fuera de la transacción fiscal; conciliación completa contra la solicitud original.
Task 3: complete — interfaz superusuario, formulario guardado desde navegador, PDF generado/renderizado, capturas completas escritorio/móvil sin desbordamiento de viewport; revisión visual independiente: ship al alcance revisado.
Task 4: complete — revisión técnica independiente completada; los cinco hallazgos iniciales se corrigieron con regresiones. Imagen Docker construida y verificada sin montaje del host: 53 pruebas verdes (3 solo PostgreSQL omitidas), usuario no root, archivo privado escribible y archivos locales sensibles/de pruebas excluidos. Emisión real y despliegue no ejecutados.

Verificación: suite rápida completa 53 casos, verde, 3 pruebas solo PostgreSQL omitidas en SQLite. Suite PostgreSQL anterior completa de 44 casos verde, incluidas las tres de concurrencia; los incrementos de importación/contador y lectura de PDF protegido también pasaron en PostgreSQL.
Revisiones: pendientes activos no se liberan por simple antigüedad; configuración obsoleta aborta; recuperación compara importes/IVA/asociaciones; ticket no se revierte con el comprobante; borrador corregido muestra datos actuales. Revisión enfocada del importador cerrada tras reemplazar subcadenas por identificadores delimitados y total etiquetado.
Regresiones finales: una autorización tardía posterior a una consulta negativa no permite reenviar el mismo borrador con el número siguiente, tanto si el intento persistió como `unknown` como si un trabajador terminó dejándolo `sending`. Ambas regresiones pasaron también en PostgreSQL; revisión enfocada cerrada.

Ruling: extensión solicitada por el usuario — importar un único comprobante histórico, conservando el PDF original y registrándolo sin nueva autorización. Las tres páginas son copias del mismo comprobante; importación idempotente y verificada por huella. Archivos de fuente y manifiesto fuera de Git, con copia privada local.
Ruling: el historial fija un mínimo de numeración, pero ARCA confirma el próximo número de cada serie. Si el número remoto retrocede, se bloquea la emisión. No se fuerza la continuidad de un punto de venta que no admita webservices.
Ruling: los tres comprobantes ficticios creados por el agente para la vista previa se retiraron por sus UUID exactos después de la importación real. No se borró información previa del usuario.

Entorno local: contenedor devlink-billing-dev, base aislada devlink_billing_test, servidor ligado solo a 127.0.0.1:8003. Sin llamadas de autorización a ARCA. El archivo original importado tiene copia privada y su hash coincide con el documento aportado.

Protección final: WSAA real rechaza SECRET_KEY corto o de ejemplo antes de leer certificados. Regresión roja/verde y revisión enfocada completadas. Servidor local reiniciado con el código final; historial y próxima numeración confirmados nuevamente en el navegador.
