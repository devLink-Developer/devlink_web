---
name: devLink
description: Infraestructura clara para servicios tecnológicos y operación de clientes.
colors:
  structural-navy: "#07162d"
  deep-navy: "#0c2343"
  interface-navy: "#10366f"
  action-blue: "#1264f6"
  bright-blue: "#1392ff"
  link-blue: "#0756db"
  cyan-signal: "#06d6ff"
  cyan-highlight: "#3df0ff"
  white: "#ffffff"
  cool-canvas: "#f6f8fc"
  cool-subtle: "#eef3f9"
  cool-muted: "#e4ebf4"
  primary-ink: "#0b1930"
  secondary-ink: "#40506a"
  muted-ink: "#5d6b82"
  inverse-ink: "#f8fbff"
  subtle-rule: "#d8e1ed"
  strong-rule: "#aebed2"
  success-surface: "#eaf8f0"
  success-ink: "#146339"
  success-rule: "#8fcda8"
  warning-surface: "#fff6dd"
  warning-ink: "#714d00"
  warning-rule: "#e0bd62"
  danger-surface: "#fff0f1"
  danger-ink: "#9e2630"
  danger-rule: "#e5a2a8"
  info-surface: "#edf5ff"
  info-ink: "#164d96"
  info-rule: "#9cbce8"
typography:
  display:
    fontFamily: '"IBM Plex Sans", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "clamp(3.4rem, 6.4vw, 5.75rem)"
    fontWeight: 700
    lineHeight: 0.98
    letterSpacing: "-0.04em"
  headline:
    fontFamily: '"IBM Plex Sans", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "clamp(2rem, 4vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.035em"
  title:
    fontFamily: '"IBM Plex Sans", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "1.05rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.025em"
  body:
    fontFamily: '"IBM Plex Sans", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: '"IBM Plex Sans", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "0.78rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.045em"
  mono:
    fontFamily: 'ui-monospace, "SFMono-Regular", Consolas, monospace'
    fontSize: "0.82rem"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  button: "10px"
  field: "12px"
  panel: "16px"
  pill: "999px"
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  "2xl": "3rem"
components:
  button-primary:
    backgroundColor: "{colors.action-blue}"
    textColor: "{colors.white}"
    rounded: "{rounded.button}"
    padding: "0.7rem 1rem"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.deep-navy}"
    rounded: "{rounded.button}"
    padding: "0.7rem 1rem"
    height: "44px"
  field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.field}"
    padding: "0.7rem 0.85rem"
    height: "44px"
  panel:
    backgroundColor: "{colors.white}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.panel}"
    padding: "1.5rem"
  status-active:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success-ink}"
    rounded: "{rounded.pill}"
    padding: "0.3rem 0.55rem"
---

# Design System: devLink

## Overview

**Creative North Star: "Infraestructura clara"**

devLink usa un **Estándar SaaS tecnológico** sereno, riguroso y orientado a la implementación. La interfaz hace visible la estructura sin volverla protagonista: campos de trabajo blancos y gris frío, reglas finas, jerarquía tipográfica contundente y geometría que recuerda sistemas, conexiones y código. La expresión comercial puede ser amplia y editorial; las superficies operativas aumentan la densidad sin cambiar de lenguaje.

La continuidad importa desde la captación hasta la operación. Marketing persuade con una propuesta espaciosa y un mapa de capacidades oscuro; autenticación, documentación y páginas legales priorizan comprensión; el portal, los dashboards y la administración priorizan escaneo y acción; los emails conservan la misma paleta y disciplina con una composición segura para clientes de correo. El sistema rechaza el cliché tecnológico oscuro con neón, la numeración decorativa de productos y el exceso de resplandores o paneles bento sin función.

**Key Characteristics:**

- Blanco y gris frío como campo de trabajo dominante.
- Azul marino para estructura, azul eléctrico para acciones y cian como señal contenida.
- IBM Plex Sans, jerarquía compacta y geometría nativa de código.
- Reglas nítidas de un píxel y paneles de 16px suavemente elevados.
- Densidad ajustada a cada superficie, con movimiento breve y prescindible.

## Colors

La paleta combina una base luminosa y fría con una estructura naval profunda; el azul de acción guía y el cian confirma conexiones sin convertirse en decoración ambiental.

### Primary

- **Azul de Acción:** activa botones principales, enlaces de alta intención, controles seleccionados y anillos de foco.
- **Noche Estructural:** construye encabezados, texto de máxima jerarquía, pies y superficies inversas de capacidad.

### Secondary

- **Azul de Interfaz:** sostiene navegación activa, iconografía funcional y estados de marca menos urgentes.
- **Azul de Enlace:** reserva una voz reconocible y accesible para enlaces dentro de texto y datos.

### Tertiary

- **Cian de Señal:** marca nodos, conectores y microindicadores; su rareza preserva su valor semántico.

### Neutral

- **Blanco de Trabajo:** superficie principal de paneles, formularios y contenido.
- **Lienzo Frío:** fondo de aplicaciones, documentación y separación tonal de secciones.
- **Gris de Apoyo:** agrupa áreas secundarias, estados en reposo y filas activables.
- **Tinta Principal:** texto de lectura y datos con máximo contraste.
- **Tinta Secundaria:** explicaciones, metadatos y navegación en reposo.
- **Regla Sutil:** borde y divisor habitual de un píxel.
- **Regla Firme:** separación que necesita más jerarquía sin aumentar el grosor.

### Named Rules

**The Contained Signal Rule.** El cian indica una conexión, un nodo o una orientación puntual; nunca forma resplandores ambientales ni compite con la acción azul.

**The Operational Canvas Rule.** Las superficies de trabajo permanecen blancas o gris frío; el marino se reserva para estructura e inversión deliberada, no para convertir toda la interfaz en modo oscuro.

## Typography

**Display Font:** IBM Plex Sans (con Segoe UI y sans-serif de sistema como respaldo)

**Body Font:** IBM Plex Sans (con Segoe UI y sans-serif de sistema como respaldo)

**Label/Mono Font:** IBM Plex Sans para etiquetas; ui-monospace, SFMono-Regular y Consolas para identificadores y datos técnicos.

**Character:** IBM Plex Sans aporta precisión técnica sin perder calidez en español. Una sola familia mantiene continuidad entre marketing y operación; el contraste aparece mediante escala, peso y espaciado, no mediante una colección de fuentes.

### Hierarchy

- **Display** (700, escala fluida amplia, 0.98): una sola proposición dominante en heroes de marketing o acceso.
- **Headline** (700, escala fluida media, 1.05): títulos de página, documentación y secciones principales.
- **Title** (700, 1.05rem, 1.3): encabezados de panel, tarjeta y grupo operativo.
- **Body** (400, 1rem, 1.6): lectura y descripción; el ancho habitual no supera 72ch.
- **Label** (700, 0.78rem, 0.045em): cabeceras de tabla, estados y metadatos compactos; las mayúsculas se usan solo cuando mejoran el escaneo.
- **Mono** (600, 0.82rem, 1.4): tenant IDs, DNS y valores de implementación.

Los emails usan Tahoma, Verdana y sans-serif como pila segura para correo, conservando escala, peso, color y ritmo del sistema web.

### Named Rules

**The One Technical Voice Rule.** IBM Plex Sans gobierna toda superficie web; el mono aparece solo cuando el contenido es realmente técnico y el stack de email cambia únicamente por compatibilidad del medio.

## Layout

El sistema usa un contenedor máximo de 1180px y una columna de lectura máxima de 72ch. Marketing combina una primera vista editorial de dos columnas con grillas de 12 columnas, colecciones de 2–3 columnas y franjas de ancho completo; documentación separa un índice lateral de 210–250px de la lectura; portal y administración usan shells centrados, métricas y paneles de datos. El espacio sigue una base de 0.5rem y crece en pasos recurrentes de 0.75, 1, 1.5, 2 y 3rem.

La densidad es específica de la tarea: espaciosa para persuadir, moderada para leer y compacta para operar. A 1080–1020px se reducen grillas amplias; a 960–899px la navegación se convierte en menú y las composiciones editoriales se apilan; a 760–680px formularios, métricas, acciones y paneles pasan a una columna; a 520–420px las acciones ocupan el ancho disponible. Las tablas conservan su geometría y se desplazan dentro de un contenedor horizontal, nunca en la página. Los emails usan una tarjeta de hasta 600px y eliminan radio exterior en 600–620px.

**The Surface Density Rule.** Una misma gramática visual admite más aire en marketing y más información en dashboards; nunca se comprime una superficie persuasiva ni se infla una tabla operativa para forzar uniformidad.

## Elevation & Depth

La profundidad es híbrida y contenida. El estado base se define con superficies tonales y reglas de un píxel; las sombras aparecen en cabeceras desplazadas, paneles elevados, modales, toasts, formularios de conversión y el mapa de capacidades. Ninguna sombra sustituye una jerarquía de borde o espaciado.

### Shadow Vocabulary

- **Elevación baja** (`0 10px 26px -18px rgba(15, 55, 95, 0.28)`): feedback sutil y controles sobre una superficie cercana.
- **Elevación media** (`0 20px 44px -26px rgba(7, 22, 45, 0.32)`): paneles elevados, toasts y formularios que necesitan separarse del lienzo.
- **Elevación alta** (`0 28px 64px -30px rgba(7, 22, 45, 0.42)`): overlays y artefactos de foco excepcional.

### Named Rules

**The Border-First Rule.** Todo panel se entiende primero por superficie y regla; la sombra solo comunica elevación real o prioridad temporal.

## Shapes

La forma canónica es un rectángulo suavemente técnico: 16px para paneles, 12px para campos, 10px para botones y controles, y píldora completa solo para estados breves. Los bordes son de un píxel. Cuadrados pequeños rotados, nodos circulares y líneas verticales aparecen como geometría de conexión; no se usan para decorar contenido sin significado. Las tarjetas editoriales pueden perder radio y trabajar como filas o celdas cuando la composición exige continuidad.

**The Honest Geometry Rule.** El radio expresa tipo y agrupación: panel, campo, control o estado. No se mezclan cápsulas, círculos y tarjetas redondeadas para fabricar variedad.

## Components

### Buttons

- **Shape:** control compacto de 10px con altura táctil mínima de 44px.
- **Primary:** azul eléctrico sobre blanco, peso fuerte y elevación azul muy breve; reserva para la acción principal del contexto.
- **Hover / Focus:** desplazamiento vertical de 1px, cambio a azul más profundo y anillo visible de 2px con halo de 3px; `:active` vuelve a la línea base.
- **Secondary / Quiet:** blanco con regla firme para acciones alternativas; fondo transparente y tinta secundaria para navegación o acciones de baja prioridad.

### Chips

- **Style:** píldora compacta con borde, fondo tonal y texto del mismo estado.
- **State:** éxito, advertencia, peligro e información usan sus tríadas de superficie, tinta y regla; nunca dependen solo del color cuando el texto o icono puede nombrar el estado.

### Cards / Containers

- **Corner Style:** panel de 16px; las tarjetas de datos administrativas usan 12px cuando la densidad es mayor.
- **Background:** blanco sobre lienzo frío; gris frío para agrupación secundaria y marino para la pieza inversa de capacidades.
- **Shadow Strategy:** borde por defecto, elevación solo cuando existe prioridad o superposición.
- **Border:** regla sutil de un píxel.
- **Internal Padding:** entre 1 y 1.5rem en operación; hasta 3rem en formularios y contenido editorial.

### Inputs / Fields

- **Style:** fondo blanco —o lienzo frío dentro de formularios comerciales—, regla firme y radio de 12px; altura mínima de 44px.
- **Focus:** borde azul y anillo de foco de 2px más halo azul translúcido.
- **Error / Disabled:** peligro usa su tinta y regla; deshabilitado usa superficie gris y mantiene texto legible.

### Navigation

La navegación web usa texto secundario y activa azul o fondo azul muy claro. El CTA de cabecera adopta el botón primario. El selector de idioma se presenta como un campo nativo compacto, conserva un objetivo táctil de al menos 42px y pasa a ocupar todo el ancho dentro del menú móvil. Por debajo de 960px la navegación se transforma en un panel blanco controlado por botón, con estado expandido, foco administrado e `inert` al cerrarse. Las barras del portal y administración aumentan densidad, permiten wrap y apilan acciones en móvil.

### Data Tables

Las cabeceras usan etiqueta compacta en mayúsculas, superficie gris fría y números tabulares. Filas y celdas se separan con reglas de un píxel; el hover es tonal. En móvil, la tabla conserva un ancho mínimo de 640–760px dentro de `.table-scroll`, que absorbe el desplazamiento horizontal.

### Capability Map

La pieza distintiva de marketing es un panel marino de 16px con una línea vertical de un píxel, nodos cian y filas internas transparentes. Es una representación de infraestructura, no una tarjeta bento ni un contenedor con brillo.

### Email Card

Los emails usan tablas de presentación, ancho máximo de 600px, blanco sobre fondo frío, borde de un píxel y cabecera o pie marino. El logotipo PNG canónico mantiene transparencia y una URL absoluta. La pila tipográfica segura y los estilos esenciales inline tienen prioridad sobre efectos web.

## Do's and Don'ts

### Do:

- **Do** mantener el blanco y el gris frío como campo dominante y usar el marino para estructura deliberada.
- **Do** reservar el azul eléctrico para acciones y foco, y el cian para señales pequeñas con significado.
- **Do** conservar reglas de un píxel, radios de 10/12/16px y espaciado basado en incrementos de 0.5rem.
- **Do** adaptar la densidad al modo: persuadir, leer u operar, sin romper la continuidad visual.
- **Do** mantener foco visible, orden semántico, objetivos táctiles de al menos 44px y movimiento reducido equivalente.
- **Do** contener tablas anchas y preservar el orden, los nombres y la legibilidad del contenido en móvil.

### Don't:

- **Don't** convertir la marca en un cliché tecnológico oscuro con neón o fondos negros permanentes.
- **Don't** añadir numeración decorativa a productos, servicios o tarjetas que no sean pasos reales.
- **Don't** usar resplandores pesados, mosaicos bento genéricos o gradientes ambientales para simular complejidad.
- **Don't** convertir cada etiqueta o acción en una píldora; la cápsula pertenece a estados compactos.
- **Don't** animar propiedades de layout ni ocultar información esencial detrás del movimiento.
- **Don't** cambiar IBM Plex Sans en la web o introducir fuentes de terceros sin licencia y procedencia registradas.
