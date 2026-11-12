# Interfaz de facturación de devLink

Registro del módulo interno implementado, 2026-11-03. Modo **Operate**: preparar, revisar y consultar comprobantes propios. Hereda la identidad existente de devLink y las plantillas Django; este documento no redefine el diseño del sitio público.

## Identidad y composición

El encabezado azul marino (`#112b4c`) contiene la marca devLink, el acento cian (`#55d7f0`) y los accesos Comprobantes, Clientes, Configuración fiscal y Volver al panel. El azul (`#1556b8`) identifica enlaces y acciones principales. El contenido usa fondo claro (`#f3f6fa`), superficies blancas, bordes suaves y esquinas de 12 px, sin sombras decorativas.

La tipografía utiliza `system-ui`, seguida de las fuentes de sistema de Apple y Windows. El cuerpo es de 15 px, los títulos principales de 32 px (28 px en móvil) y los títulos de sección de 20 px. Importes y otras columnas numéricas usan cifras tabulares.

El área central tiene un máximo de 1240 px. El resumen distingue facturación neta de producción, borradores/corregibles y operaciones que requieren conciliación. El historial permite buscar cliente o CAE y filtrar por estado y ambiente. La próxima numeración, cuando aparece, se identifica como provisional hasta confirmarla con ARCA.

## Formularios y estados fiscales

Los formularios agrupan datos del comprobante, líneas de productos/servicios, datos del emisor y conexión con ARCA. Las etiquetas permanecen visibles; los campos obligatorios llevan asterisco y los datos técnicos incluyen ayuda contextual. Configuración fiscal separa Producción y Homologación con enlaces de ambiente y selección indicada mediante subrayado y `aria-current`.

Guardar un borrador lleva a la revisión y no solicita autorización. La revisión muestra receptor, detalle, importe y ambiente; emitir exige una casilla de confirmación y una acción explícita, diferenciada entre comprobante real y homologación. Los estados tienen texto además de color: autorizado en verde, incierto/en envío en ámbar y rechazado en rojo. La recuperación se presenta como consulta del resultado existente. Los autorizados ofrecen PDF y, para factura C, preparación de nota de crédito.

Los comprobantes importados muestran que proceden de un PDF existente y que la importación no envió una autorización nueva. Cuando existe el documento fuente, el control dice «Descargar PDF original».

## Adaptación y accesibilidad implementada

En pantallas pequeñas, encabezado, acciones y campos generales se apilan; cantidad y precio conservan una pareja de columnas dentro de cada línea. Las tablas mantienen sus columnas dentro de un contenedor con desplazamiento horizontal, sin ampliar el documento.

El código incluye enlace para saltar al contenido, etiquetas asociadas a controles, foco visible de 3 px, mensajes de estado, errores por campo y generales, y estados vacíos con una acción para comenzar o ajustar la consulta. El total estimado se anuncia con `aria-live="polite"`. Los formularios marcados deshabilitan su botón durante el envío y muestran «Procesando…». Estos mecanismos documentan la implementación; no equivalen a una auditoría con tecnología de asistencia.

## Evidencia y alcance de revisión

La revisión visual independiente terminó con disposición **ship**, limitada a las capturas responsive y fuentes de interfaz revisadas. Se inspeccionaron las capturas completas desde el inicio del documento:

- `.impeccable/review/billing/desktop.jpg` y `mobile.jpg`: resumen e historial con el comprobante histórico importado.
- `.impeccable/review/billing/form-desktop.jpg` y `form-mobile.jpg`: formulario de factura C.
- `.impeccable/review/billing/settings-desktop.jpg` y `settings-mobile.jpg`: configuración fiscal.

Las capturas móviles tienen 375 px de ancho de contenido; el navegador solicitado fue de 390 px con 15 px reservados a la barra vertical. La comprobación del implementador informó ancho de desplazamiento igual al ancho del documento. También se inspeccionó `.billing-test/preview.png`, una representación PDF de muestra en homologación, distinta del PDF original importado.

Fuentes de verdad: `PRODUCT.md`, `static/billing/billing.css`, `static/billing/billing.js` y `templates/billing/`. No se verificaron visualmente todas las variantes de error, carga, recuperación o pantallas sin captura; tampoco se probaron teclado o lectores de pantalla durante esta revisión. **ARCA en vivo y la habilitación de producción no están validados por esta revisión de interfaz.**
