# Decks en Claude Design con los lineamientos de marca Kin

Fuente de verdad: skill **`brand-guidelines-kin`** (instalada en `.claude/skills/brand-guidelines-kin/`, export sincronizado del
**Kin Design System - Kin Official**; si hay conflicto gana el DS). Su template de deck es
`project/templates/kin-presentation/KinPresentation.dc.html` dentro del DS (`https://claude.ai/artifact/Kyrvxqzwp78R1ZzWhrgBHK`);
las láminas de referencia renderizadas están en `.claude/skills/brand-guidelines-kin/assets/templates/reference-designs/`
(`cover-variants-1.png`, `kin-presentation-slide-03.png` = divisor, `kin-presentation-slide-06.png` = contenido).
Aplicado a los dos decks de Bepensa · ZM Mérida el 2026-10-01 (usuario: "recrea la presentación bajo esos lineamientos").

## Flujo para crear o rehacer un deck
1. `Artifact` → `read` del deck (`paths`: `project/deck.json` y todas las `project/slides/*.html`) → quedan en el scratchpad.
2. Contenido: `python .claude/skills/golden-stores-kin/scripts/marca_claude_design.py <carpeta_deck>` (idempotente).
3. Portada, divisores y cierre: escribirlos con `portada()`, `divisor()` y `cierre()` del mismo script (importarlo) con el texto
   del deck. Los ids de divisores empiezan con `div-` (la pasada de contenido no los toca).
4. Publicar con `url` del deck, `root` = carpeta, todas las láminas en `files` y los assets del DS copiados del lado del servidor:
   ```
   "project/ds/kin/templates/kin-presentation/assets/cover-duotone.jpg":
       {"artifact": "https://claude.ai/artifact/Kyrvxqzwp78R1ZzWhrgBHK", "path": "project/templates/kin-presentation/assets/cover-duotone.jpg"}
   "project/ds/kin/templates/kin-presentation/assets/kin-mark-yellow-hex.png": {... "path": ".../kin-mark-yellow-hex.png"}
   ```
   (`kin-analytics-logo.png`, `kin-analytics-logo-dark.png`, `kin-mark-black-hex.png`, fuentes y `tokens.json` ya vienen con la
   instalación del DS). Los SVG del DS **no** se copian entre artifacts: usar los PNG. `deck.json` solo si cambia orden o título.

## Reglas por tipo de lámina (formato Slides: 1920×1080, estilos inline, sin clip-path)
| Lámina | Regla |
|---|---|
| Portada | Variante A (foto duotono `cover-duotone.jpg` a pantalla completa). Logo corto "Kin" blanco + hexágono amarillo (`kin-mark-yellow-hex.png`) arriba a la izquierda. Caja `#141417` radio 12 px con eyebrow amarillo, **título amarillo** (Space Grotesk 600), subtítulo blanco y fila CLIENTE / PARTNER / PROYECTO **dentro de la misma caja**. Abajo a la derecha: "Kin Analytics© 2026" + "CONFIDENTIAL" amarillo (solo en portada). Sin pie de contenido. |
| Divisor | Número "01." amarillo arriba a la izquierda (132 px), título blanco y 2.ª línea con fondo amarillo y tinta negra. **Panel amarillo con punta de hexágono** (chevron, nunca un rectángulo): `<svg>` con `polygon 190,0 0,540 190,1080 730,1080 730,0` en x = 1190 (es el `clip-path` del template del DS). Logo "Kin" todo negro (`kin-mark-black-hex.png`) abajo a la derecha sobre el panel. Alternar variantes A (foto) / B (sólido `#141417`) / C (gris `#D4D5D6`, tinta oscura). Sin pie ni marca de confidencialidad. |
| Contenido | Fondo `#FFFFFF` o Gray 1 `#EFEFEE` (alternar). Eyebrow Albert Sans 24 px 600, mayúsculas, tracking 6 px, **Gray 3 `#999EA6`** (nunca amarillo sobre claro; nada de píldoras). Título Space Grotesk 600, 56–60 px, arriba. Tarjetas radio 12 px; las oscuras `#141417` con acento amarillo. Pie: logo formal `kin-analytics-logo.png` (300×60) abajo a la izquierda y `kinanalytics.com` (Albert Sans 500, 28 px, Gray 3) abajo a la derecha, pegados a las esquinas (56 px). En lámina oscura: `kin-analytics-logo-dark.png`. |
| Cierre | Foto duotono con velo, "Gracias", línea amarilla y logo formal oscuro centrado. Sin pie. "Leave it to Kin" solo si se pide. |

Colores: solo la paleta Kin (`#141417`, `#222326`, `#999EA6`, `#D4D5D6`, `#EFEFEE`, `#FFFFFF`, `#E5FF01`; `#F2F2F2` y `#444444`
existen en el DS para tarjetas y texto secundario). **Excepción a propósito:** los colores de dato que deben coincidir con los mapas
y Excel (HH/HL/LH/LL, semáforos verde/amarillo/rojo, clases CP) se conservan. Nunca "Let knowledge in"; sin signo `$`.
