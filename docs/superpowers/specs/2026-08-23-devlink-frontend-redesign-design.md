# Rediseño integral del frontend de devLink

## Objetivo

Unificar toda la experiencia web de devLink bajo una identidad SaaS tecnológica moderna, clara y coherente. El rediseño debe conservar el contenido, las rutas, los nombres de navegación, los campos de formulario y la funcionalidad existente. El blanco será la superficie dominante y los colores actuales del logotipo definirán la estructura, las acciones y los detalles técnicos.

## Alcance

El cambio cubre:

- Página comercial principal y formulario de contacto.
- Inicio de sesión y recuperación de mensajes de autenticación existentes.
- Portal y dashboard de clientes.
- Reporte de WhatsApp y editor de preguntas/respuestas.
- Documentación protegida.
- Políticas de privacidad, términos de servicio y aviso de información.
- Panel administrativo completo: resumen, usuarios, productos, asignaciones, consultas y reportes.
- Plantillas de correo y vistas de previsualización que forman parte de las rutas actuales.

Quedan fuera los cambios de backend, modelos, permisos, rutas, integraciones, eventos o contenido comercial.

## Dirección visual aprobada

La dirección es **Estándar SaaS tecnológico**, usando Linear, Stripe y Vercel como referencias de nivel de acabado, no como identidades para copiar.

- `DESIGN_VARIANCE: 6`: composición limpia con asimetría moderada.
- `MOTION_INTENSITY: 4`: transiciones breves para jerarquía, feedback y cambios de estado.
- `VISUAL_DENSITY: 5`: aire en marketing y documentación; mayor densidad controlada en tablas y dashboards.
- Tema único claro. El pedido de combinar los colores del logotipo con blanco define la superficie, por lo que no se añadirá un modo oscuro.
- Paleta: blanco y grises fríos como base; azul marino para texto y estructura; azul eléctrico para acciones; cian reservado para indicadores, focos y pequeños detalles técnicos.
- Tipografía: sans serif moderna, legible y orientada a producto. Se utilizará una pila local o autoalojada para evitar dependencia visual de terceros.
- Formas: tarjetas de 16 px, campos de 12 px y botones de 10 px. Los botones compactos de icono podrán ser circulares cuando la función lo justifique.

## Arquitectura de interfaz

### Sistema compartido

Se consolidarán tokens de color, tipografía, radios, sombras, capas, espacios y estados en la hoja de estilos estática. Los estilos heredados se organizarán por fundamentos, componentes, marketing, documentación, aplicación y utilidades responsive.

Los patrones comunes serán:

- Marca y navegación pública.
- Botones primarios, secundarios, silenciosos y destructivos.
- Campos, selects, textareas, checkboxes, ayuda y errores.
- Alertas y mensajes del sistema.
- Contenedores, secciones, tarjetas, métricas y listas.
- Tablas, paginación, filtros y estados vacíos.
- Shell autenticado con cabecera, navegación contextual y área principal.

Las plantillas Django seguirán siendo renderizadas en servidor. No se añadirá un framework JavaScript ni una librería de componentes que duplique la arquitectura existente.

### Web pública

El hero tendrá composición asimétrica: propuesta y acciones en el lado principal, con una visualización editorial de las capacidades existentes en el lado complementario. No se fabricarán capturas de producto ni métricas nuevas.

Las secciones conservarán todo su contenido, pero variarán el patrón de composición para evitar repetición: métricas horizontales, servicios en cuadrícula asimétrica, Suite Lite como sistema modular, soluciones como capas conectadas, metodología como secuencia y contacto como cierre de alta claridad.

La navegación permanecerá en una línea en escritorio y utilizará un menú accesible en móvil. El footer mantendrá contacto, redes y enlaces legales.

### Portal y dashboards

Las superficies autenticadas compartirán una shell clara y compacta:

- Cabecera con marca, contexto del usuario y salida.
- Navegación persistente en escritorio y colapsable en móvil.
- Títulos y acciones principales alineados de forma consistente.
- Métricas sin adornos excesivos.
- Productos, reportes y acciones en módulos con jerarquía clara.
- Tablas con encabezados legibles, filas escaneables, paginación y acciones distinguibles.
- Formularios con etiquetas permanentes, ayuda y estados de foco/error.

La administración tendrá mayor densidad que la web comercial, pero utilizará la misma paleta, tipografía y lenguaje de componentes.

### Documentación y legales

La documentación empleará una navegación lateral fija en escritorio y un índice colapsable en móvil. El cuerpo tendrá ancho de lectura controlado, jerarquía semántica y bloques de pasos, notas y enlaces fáciles de escanear.

Las páginas legales compartirán encabezado, índice y pie de página con la identidad actualizada, sin alterar el texto legal.

### Correos

Las plantillas de correo conservarán texto, enlaces y compatibilidad con clientes de correo. El estilo se actualizará usando tablas e inline CSS donde corresponda, con una versión simplificada de los mismos tokens de marca.

## Interacción y movimiento

El movimiento comunicará jerarquía y feedback:

- Entrada breve del hero y de grupos clave.
- Hover y estado activo en controles.
- Apertura y cierre accesible de menús.
- Transiciones de alertas y estados.

Solo se animarán `transform` y `opacity`. Todas las animaciones se desactivarán o simplificarán con `prefers-reduced-motion`. No habrá scroll hijacking, cursores personalizados, fondos de neón ni animaciones perpetuas.

## Flujo de datos y comportamiento

El rediseño no modifica cómo viajan los datos:

- Los formularios mantienen `action`, `method`, `name`, CSRF y validaciones actuales.
- Los enlaces conservan rutas, nombres Django y anclas.
- Los bucles, condiciones, paginación y permisos de las plantillas no cambian.
- Los mensajes de Django se muestran con componentes visuales nuevos sin cambiar su contenido ni tipo.
- Los editores y reportes conservan sus identificadores y JavaScript funcional.

## Estados y errores

- Mensajes de éxito, advertencia y error tendrán contraste suficiente y no dependerán solo del color.
- Los dashboards mostrarán estados vacíos existentes con jerarquía y acciones claras.
- Los controles deshabilitados, activos y en foco serán visualmente distintos.
- Los formularios conservarán los mensajes existentes y evitarán placeholders como único identificador.
- Las tablas mantendrán su contenido accesible en móvil mediante contenedores con desplazamiento horizontal o adaptación explícita según el caso.

## Accesibilidad

- Contraste mínimo WCAG AA.
- Foco visible en enlaces, botones y campos.
- Navegación completa por teclado.
- `aria-expanded` y etiquetas accesibles en menús y controles interactivos.
- Encabezados y landmarks con orden lógico.
- No se usará color como único indicador de estado.
- Se respetará `prefers-reduced-motion`.

## Rendimiento

- Sin framework JavaScript adicional.
- CSS compartido y organizado para evitar duplicación.
- Imágenes con dimensiones reservadas y sin filtros costosos en contenedores desplazables.
- Fuentes locales o autoalojadas con `font-display: swap` si se incorpora una nueva familia.
- JavaScript limitado a navegación, feedback y comportamiento ya existente.

## Estrategia de implementación

1. Consolidar tokens y componentes base en los estilos compartidos.
2. Rediseñar la página pública y validar el lenguaje visual.
3. Aplicar la shell y componentes al inicio de sesión, portal y dashboards.
4. Adaptar documentación y legales.
5. Adaptar el panel administrativo completo.
6. Actualizar las superficies de correo manteniendo compatibilidad.
7. Ejecutar pruebas, detector de diseño y revisión visual en escritorio y móvil.

## Verificación

- Ejecutar la suite de pruebas Django.
- Ejecutar `python manage.py check`.
- Revisar que cada plantilla renderizada mantenga sus variables, formularios, rutas y condiciones.
- Capturar la página principal, acceso, dashboard cliente, reporte representativo y panel administrativo en escritorio y móvil.
- Comprobar overflow horizontal, navegación, foco, formularios, tablas y estados vacíos.
- Ejecutar el detector de `impeccable` una sola vez sobre los archivos modificados.
- Realizar una revisión final independiente con las capturas y el contrato de dirección visual.

## Criterios de aceptación

- Todo el contenido y comportamiento actual permanece disponible.
- Todas las superficies visibles comparten el mismo sistema visual.
- Los colores del logotipo son reconocibles y están equilibrados con blanco.
- La web pública comunica servicios y acción principal en el primer viewport.
- Portal, dashboards y administración son más claros, consistentes y responsive.
- No hay regresiones conocidas de accesibilidad, rutas, formularios o permisos.
