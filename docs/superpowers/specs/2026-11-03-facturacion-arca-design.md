# Facturación propia de devLink con ARCA

Estado: aprobado por el usuario el 2026-11-03; implementación en curso.
Fecha: 2026-11-03.
Revisión técnica independiente: completada; no se encontraron preguntas importantes pendientes para planificar la implementación.

## Decisiones confirmadas

- El módulo es para la facturación propia de devLink, con el CUIT de Eudy David Espinoza Leal como monotributista. No habilita a los clientes a emitir con sus propios CUIT.
- Se implementará integrado en Django, siguiendo las configuraciones y los criterios de integración de LiteCore e Invoice.
- Se preservan los cambios existentes del usuario y el funcionamiento del sitio público y del portal.

## Objetivo y propuesta de alcance

Un administrador de devLink podrá mantener los datos fiscales de sus clientes, preparar un comprobante con sus servicios, revisar sus importes, autorizarlo mediante WSAA/WSFEv1 y descargar su representación PDF. Podrá consultar el historial y emitir notas de crédito vinculadas a facturas autorizadas.

Propongo que la primera entrega incluya factura C (11) y nota de crédito C (13), en pesos argentinos, con productos, servicios o ambos. No incluye facturación automática recurrente, cobros, facturación de exportación, CAEA, integración contable ni otros emisores. Estos límites son propuestas del implementador; no fueron solicitados expresamente por el usuario.

## Alternativas consideradas

1. **Módulo integrado en Django — opción elegida por el usuario.** Reutiliza los criterios de configuración de LiteCore y de autorización/recuperación de Invoice mediante un adaptador local de ARCA. Comparte autenticación y base de datos con devLink y no requiere otro servicio en ejecución.
2. **Cliente del microservicio Invoice.** Aprovecha su motor existente, pero requiere desplegar y operar el servicio, configurar su autenticación y aislar sus datos. El usuario eligió la alternativa integrada.

Los repositorios de referencia se consultan en modo lectura. No se reutilizan sus certificados, contraseñas, bases de datos, CUIT ni puntos de venta.

## Evidencia y referencias

- devLink: Django 4.2, PostgreSQL 15, plantillas de servidor, autenticación con `accounts.CustomUser` y administración restringida a superusuarios.
- LiteCore: `D:/devlink/Suite_Lite/LiteCore/LiteCore/maestros_configuraciones/models.py`, modelo `ArcaServiceParameter`; servicios WSAA y WSFE; `invoice_conection.md` y el módulo `facturacion`.
- Invoice: `D:/invoice/app/settings.py`, `app/core/wsfe_validation.py` y `app/core/arca_reconciliation.py`. Se toman como referencia los estados inciertos y la consulta previa a cualquier reintento.
- [Documentación WSAA de ARCA](https://www.arca.gob.ar/ws/documentacion/wsaa.asp).
- [Manual WSFEv1 v4.7, revisión septiembre de 2026](https://www.arca.gob.ar/ws/documentacion/manuales/manual-desarrollador-ARCA-COMPG.pdf).
- Certificado de producción serie `1d15d41dbafb4217`, vigente hasta el 02/11/2028. Correspondencia con la clave privada comprobada localmente; ambos están fuera del repositorio y del directorio público de medios.

## Experiencia y permisos

Una entrada «Facturación» en el panel administrativo abre un resumen con totales por estado, listado de comprobantes y accesos a «Nueva factura», «Clientes» y «Configuración fiscal». Se mantienen las plantillas de servidor y la identidad visual de devLink.

- Solo superusuarios autenticados acceden a vistas, acciones y PDFs. Los clientes del portal no tienen acceso a los comprobantes en esta primera entrega.
- Los clientes fiscales pueden vincularse opcionalmente a un usuario existente. También se permite facturar a clientes que no tengan cuenta en el portal.
- Un borrador permite editar receptor, líneas, fechas y notas internas. Cada línea contiene descripción, cantidad y precio unitario; el servidor calcula importes con `Decimal` y redondeo explícito a dos decimales.
- Para servicios se requieren período desde/hasta y vencimiento de pago. La vista previa muestra receptor, detalle, total, ambiente y punto de venta antes de «Emitir en ARCA».
- El usuario emite con una acción explícita POST protegida por CSRF. No se autoriza nada al guardar un borrador, visitar una página, ejecutar migraciones o lanzar pruebas.
- Un autorizado queda inmutable y admite PDF con CAE, vencimiento, número, datos fiscales, detalle y QR. Los borradores nunca se presentan como comprobantes autorizados.
- Una nota de crédito se crea desde una factura C autorizada y conserva el vínculo fiscal. Permite devolución parcial o total; el total acumulado acreditado no puede exceder la factura original. Los importes enviados a ARCA son positivos; los resúmenes descuentan las notas de crédito.

## Configuración fiscal y de servicios

Una configuración propia de devLink reúne razón social, CUIT, condición de monotributista, domicilio fiscal, ingresos brutos y fecha de inicio de actividades. Los datos faltantes se completan en el formulario; no se inventan.

Por ambiente se configuran:

- Servicio `wsfe`, ambiente `HOMO` o `PROD`, punto de venta y tiempo de espera (30 segundos por defecto).
- WSAA: `https://wsaahomo.afip.gov.ar/ws/services/LoginCms` o `https://wsaa.afip.gov.ar/ws/services/LoginCms`.
- WSFE: `https://wswhomo.afip.gov.ar/wsfev1/service.asmx` o `https://servicios1.afip.gov.ar/wsfev1/service.asmx`.
- Certificado y clave: rutas dentro de una carpeta privada configurada en el servidor, con soporte `.crt` + `.key` y `.pfx`. Las contraseñas de claves/PFX se resuelven por nombre de variable de entorno; no se guardan en texto plano en la base.
- Ventana de TRA como LiteCore: generación -5 minutos, expiración +10 minutos, firma SHA-256 y validación TLS activa.

La configuración admite verificar vigencia y coincidencia del certificado, consultar disponibilidad del servicio y obtener puntos de venta desde ARCA sin emitir facturas. Se muestran los errores de autorización de `wsfe` sin asumir que la emisión del certificado ya otorgó ese permiso.

Los endpoints se limitan a las URL oficiales correspondientes al ambiente; no se admiten destinos arbitrarios para enviar certificados o tickets. No se mezclan ambientes ni se usa un certificado de producción para homologación.

La emisión se entrega deshabilitada por defecto. La activación requiere datos fiscales completos, certificado válido, autorización al servicio y selección de un punto de venta habilitado para webservices. La configuración de desarrollo no activa producción automáticamente.

## Datos y responsabilidades

Una aplicación Django `billing` contendrá:

- **Emisor y configuración ARCA:** un único emisor y parámetros por ambiente; referencias a secretos, sin archivos privados en medios públicos.
- **Cliente fiscal:** identificación, condición frente al IVA, razón social, domicilio y vínculo opcional al cliente del portal.
- **Comprobante y líneas:** UUID, clave de idempotencia, instantánea de datos de emisor/receptor, tipo, ambiente, punto de venta, concepto, fechas, moneda, importes, número fiscal, CAE, vencimiento y comprobante asociado.
- **Intento y auditoría:** transición, usuario, fecha, método, respuesta normalizada, códigos y observaciones. Se excluyen claves, tokens, firmas y XML de autenticación de los logs.
- **Ticket WSAA:** caché privada y persistente por certificado, CUIT, servicio y ambiente, con renovación controlada. Las credenciales no se exponen en formularios ni en listados.

La lógica se divide entre formularios/modelos, adaptación SOAP y firma, coordinación de emisión/conciliación y representación PDF. Las dependencias se fijarán en el plan de implementación con soporte para el Python 3.11 del contenedor.

## Emisión y control de duplicados

Estados propuestos: borrador, en envío, autorizado, rechazado e incierto. La clave de idempotencia identifica el borrador durante toda su emisión; repetir el POST no genera otra factura.

1. Validar permisos, configuración, datos fiscales, importes, condición IVA del receptor y reglas del comprobante. Para C, IVA y exentos son cero; el subtotal se informa en `ImpNeto`, conforme al manual vigente.
2. Obtener o reutilizar el ticket WSAA. Consultar el último número autorizado en ARCA para el ambiente, CUIT, punto de venta y tipo.
3. Con exclusión mutua en PostgreSQL, impedir emisiones concurrentes de esa misma serie. Persistir la reserva y el estado «en envío» antes de enviar `FECAESolicitar`, de forma que un corte del proceso deje evidencia recuperable.
4. Persistir el resultado y observaciones. Solo un resultado aprobado con CAE y respuesta consistente marca «autorizado». Un rechazo explícito permite corregir y revalidar el borrador preservando los intentos anteriores.
5. Un timeout, respuesta incompleta, error de transporte o terminación del proceso después del envío mantiene «incierto» o «en envío» recuperable y bloquea nuevos envíos de la misma serie hasta resolverlo. No se reintenta automáticamente `FECAESolicitar`.
6. Conciliar con `FECompConsultar` por la identidad fiscal exacta. Verificar receptor, concepto, fecha e importes contra la solicitud antes de recuperar el CAE. Un comprobante ajeno que use el mismo número exige revisión y no se asocia al borrador.
7. Si ARCA devuelve una respuesta explícita de no autorizado/no encontrado, se vuelve a consultar la secuencia antes de permitir un reintento manual. Fallos técnicos de consulta conservan el estado incierto.

Las restricciones de base de datos protegen la identidad fiscal y la idempotencia. Las notas de crédito aplican exclusión mutua adicional sobre la factura original al validar el saldo acreditable, incluidos los intentos pendientes o inciertos.

## Despliegue y comprobación

- Migraciones propias, documentación de variables y montaje privado de certificados en Docker como solo lectura. Ningún secreto se versiona.
- Comando de validación local y comando de conciliación; ambos informan el ambiente. La conciliación consulta comprobantes existentes y no crea nuevos.
- Pruebas aisladas con dobles de ARCA: montos, fechas, condiciones fiscales, permisos, CSRF, idempotencia, rechazos, timeouts, respuestas incompletas, recuperación, inmutabilidad y límites de notas de crédito.
- Comprobación de concurrencia contra PostgreSQL aislado; SQLite no se considera prueba suficiente de bloqueo entre procesos.
- Comprobación visual responsive de configuración, borrador, listado y PDF. Regresión de las rutas existentes.
- No se emiten comprobantes reales ni se modifica infraestructura de producción durante el desarrollo. La entrega incluye los pasos de activación y los pendientes fiscales que requieran al titular.

## Pendientes conocidos para activación

- Confirmar que el alias `devlink` esté autorizado al servicio `wsfe`.
- Consultar y elegir un punto de venta de webservices del CUIT; no reutilizar los de LiteCore/Invoice.
- Completar domicilio fiscal, ingresos brutos y fecha de inicio de actividades.
- Para pruebas reales en homologación se necesita un certificado de ese ambiente. El certificado disponible y verificado es exclusivamente de producción.

## Aprobación solicitada

Validar este alcance de primera entrega: módulo interno integrado, clientes fiscales, borradores, factura C, nota de crédito C, configuración de ARCA, historial, PDF y recuperación sin duplicados. Una vez aprobado, se redacta el plan y se implementa en esta sesión.
