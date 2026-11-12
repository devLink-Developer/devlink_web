# Anulaciones parciales y totales de facturas

## Intención

Dar al administrador de devLink una forma clara y segura de corregir Facturas C autorizadas mediante Notas de Crédito C asociadas. El operador debe poder encontrar las facturas de un cliente, distinguir cuáles tienen saldo, cuáles fueron anuladas parcial o totalmente y preparar anulaciones sin exceder el importe ni la cantidad originalmente facturados.

## Fuentes fiscales

- ARCA no elimina una factura electrónica autorizada: la corrección se documenta con una nota de crédito asociada.
- El WSFEv1 exige informar el comprobante asociado para notas de débito o crédito y admite Nota de Crédito C, código 13.
- Referencias: Manual para el desarrollador WSFEv1 V4.7 de ARCA y Resolución General 4540/2019.

## Objetivos

- Agregar un centro de anulaciones accesible desde la navegación de Facturación.
- Seleccionar un cliente y ver todas sus Facturas C autorizadas.
- Mostrar por factura: total original, importe acreditado, importe reservado por operaciones inciertas, saldo disponible y estado de anulación.
- Mantener visibles pero no seleccionables las facturas totalmente anuladas.
- Permitir anulación total de una o varias facturas seleccionadas.
- Permitir anulación parcial de una factura seleccionando renglones y cantidades.
- Exigir un motivo para toda nota de crédito.
- Generar borradores para revisión; nunca emitir automáticamente al seleccionar.
- Mantener una Nota de Crédito C independiente y asociada por cada factura, incluso cuando la selección total sea múltiple.
- Mostrar en el detalle de la factura sus notas de crédito y el saldo restante.
- Evitar duplicados, sobreanulación y carreras concurrentes.

## No objetivos

- No borrar, modificar ni marcar manualmente como anulada una factura autorizada.
- No emitir una única nota de crédito asociada a varias facturas.
- No permitir notas de crédito libres sin factura asociada.
- No habilitar por código la emisión real de producción ni modificar certificados ARCA.
- No automatizar el envío a ARCA: el administrador conserva la revisión y confirmación existentes.

## Enfoques considerados

### Nota de crédito libre desde “Nuevo comprobante”

Descartado. Es fácil de encontrar, pero permite crear documentos sin asociación clara y aumenta el riesgo de errores fiscales.

### Acciones únicamente desde el detalle de una factura

Seguro para una factura, pero lento cuando el administrador necesita revisar varias facturas de un cliente o distinguir cuáles ya tienen créditos.

### Centro de anulaciones por cliente más acciones en el detalle — elegido

Combina una vista consolidada por cliente con accesos contextuales desde cada factura. La selección múltiple prepara una nota independiente por factura; la anulación parcial se hace sobre una sola factura para conservar el detalle de renglones y cantidades.

## Modelo y reglas de saldo

- `Invoice` conserva el vínculo `original` entre Nota de Crédito C y Factura C.
- Cada Nota de Crédito C guarda un `cancellation_reason` obligatorio, un alcance `total` o `partial` y los muestra en su detalle y PDF.
- Cada línea de una nota de crédito guarda un vínculo `original_line` con el renglón de la factura que ajusta.
- Estados `authorized`, `sending` y `unknown` consumen o reservan saldo y cantidades.
- Estados `draft` y `rejected` no consumen saldo fiscal, pero solo puede existir un borrador editable por factura; la interfaz ofrece continuarlo en vez de crear otro.
- El saldo disponible es el total original menos notas autorizadas y operaciones pendientes o inciertas.
- Una factura queda “Anulada totalmente” cuando el saldo disponible es cero; “Anulada parcialmente” cuando el saldo es mayor que cero y menor que el total; “Sin anulaciones” cuando conserva el total.
- El cálculo definitivo se repite dentro de una transacción con bloqueo de la factura original antes de crear el borrador y antes de emitirlo.
- La anulación total usa una línea resumen por el saldo monetario exacto. Esto evita diferencias acumuladas por redondeo cuando antes hubo créditos parciales.
- Si existen notas históricas sin correspondencia verificable entre renglones, el sistema conserva el control por importe total y bloquea la anulación automática por cantidades hasta una revisión manual.
- Para facturas importadas, la anulación total se admite con el saldo local; la parcial exige que el operador confirme haber comparado los renglones con el PDF original.
- El historial actual conocido no contiene Notas de Crédito C externas. Si una factura importada hubiera sido acreditada fuera de devLink, debe incorporarse o revisarse antes de operar sobre ella; la interfaz lo advierte expresamente.
- Si ya existe un borrador o una nota rechazada editable para la factura, el sistema no crea otro: ofrece continuar o descartar el existente.
- Notas históricas sin motivo conservan el campo vacío y se presentan como “Motivo no registrado”; solo las nuevas notas requieren motivo y solo estas lo imprimen en el PDF.

## Flujo de anulación total

1. El administrador abre “Anulaciones”, selecciona un cliente y ve sus facturas.
2. Selecciona una o varias facturas con saldo disponible.
3. Escribe un motivo común y confirma “Preparar anulaciones totales”.
4. El servidor vuelve a calcular saldos bajo bloqueo y crea una Nota de Crédito C en borrador por factura, con una línea resumen por el saldo exacto disponible.
5. La interfaz presenta los borradores creados para revisarlos y emitirlos individualmente mediante el flujo actual.

## Flujo de anulación parcial

1. El administrador elige “Anular parcialmente” en una factura con saldo.
2. La pantalla muestra cada renglón, cantidad original, cantidad ya acreditada o reservada y cantidad disponible.
3. Selecciona renglones, indica cantidades positivas no mayores a las disponibles y escribe el motivo.
4. El servidor vuelve a calcular bajo bloqueo, crea el borrador con precios unitarios inmutables del original y redirige a su revisión.

## Interfaz

- Incorporar “Anulaciones” en la navegación superior del facturador.
- Añadir un estado visual por factura: sin anulaciones, parcial, total, pendiente o borrador en preparación.
- Usar tablas responsivas con casillas de selección de tamaño táctil y un resumen fijo de selección en escritorio, apilado en móvil.
- En el detalle de factura mostrar una tarjeta de saldo y una tabla de notas de crédito relacionadas.
- En el detalle de nota mostrar la factura asociada, el motivo y el alcance total o parcial.
- Mantener contraste, foco visible, navegación por teclado y mensajes de error próximos al campo.

## Compatibilidad y seguridad

- Mantener las rutas y el flujo actuales de facturas, emisión, conciliación y PDF.
- Conservar el endpoint existente de preparación de nota de crédito como compatibilidad, redirigiéndolo al flujo seguro.
- Permitir descartar únicamente notas de crédito en estado borrador o rechazado para corregir una preparación errónea; los documentos emitidos o inciertos siguen siendo inmutables.
- Todas las nuevas vistas continúan restringidas a superusuarios y usan `POST` con CSRF para crear borradores.
- No confiar en importes, precios, clientes ni asociaciones enviados por el navegador; se derivan de registros autorizados.
- Las operaciones múltiples son atómicas: si una selección deja de ser válida, no se crea ningún borrador del lote.

## Validación

- Pruebas unitarias de saldos por estado, cantidades por renglón, redondeo y notas históricas.
- Pruebas de vistas para permisos, CSRF, selección por cliente, anulaciones total y parcial y mensajes de error.
- Pruebas de concurrencia PostgreSQL para impedir sobreanulación.
- Pruebas del payload WSFEv1 para la asociación fiscal y del PDF para motivo y referencia.
- Verificación manual responsive en escritorio y móvil.

