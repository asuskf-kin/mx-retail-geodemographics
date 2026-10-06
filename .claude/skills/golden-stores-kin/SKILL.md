---
name: golden-stores-kin
description: Replica para un cliente (Customer Potential con la venta media; el archivo de ventas ya no se usa) la metodología Golden Stores (NielsenIQ/Spectra) sobre sus puntos de venta de una zona metropolitana de México y genera la presentación con el estilo Kin Analytics — perfil NSE a 300 m de cada PDV en hexágonos H3, clústeres HH/HL/LH/LL (demanda × venta), semáforos, prioridad P1–P4 (Letra 1 × share Whisp si hay datos; si no, por letras), Rappi solo Coca-Cola sin marcas BRAND_x, mapa interactivo con marca Kin, entregables Excel (completo, reducido, diccionario, entregable final) y láminas que explican el mapa. Usar cuando pidan "golden stores", "tiendas más valiosas", "presentación / deck / pptx del análisis", "hazlo para otro cliente / otra ciudad / otro canal", "cuadrantes demanda × venta", "semáforos por clúster", o cuando llegue el CP (Customer Potential) de un cliente.
---

# Golden Stores × Kin (cliente con Customer Potential)

Este repo ya tiene todo el proceso. **No lo reescribas**: se configura y se corre. Lee primero `.claude/CLAUDE.md`.
Detalle de cada pieza: [metodologia_golden_stores.md](references/metodologia_golden_stores.md) (la metodología, fija),
[estilo_kin.md](references/estilo_kin.md) (diseño del deck y QA) y [datos_cliente.md](references/datos_cliente.md)
(qué pedir al cliente y cómo validarlo).

## Instalación (una vez por máquina)

```bash
uv sync                                                          # entorno del proyecto (.venv) desde uv.lock
uv run python .claude/skills/golden-stores-kin/scripts/instalar.py   # verifica paquetes, registra el kernel, LibreOffice y datos
```
Si pip dice que un archivo está en uso, cierra los kernels de Jupyter/VS Code de ese Python y repite (una instalación
interrumpida deja paquetes rotos, p. ej. pyproj sin su DLL: `instalar.py --solo-verificar` los detecta).

## Bottler o ciudad nuevos (prompt tipo "ahora femsa cdmx") — seguir en este orden
1. **Verificar datos ANTES de tocar nada:** `uv run python .claude/skills/golden-stores-kin/scripts/verificar_datos.py <ciudad>
   <cliente> [--etiquetas "CIUDAD DE MEXICO|CDMX"]` (no descarga ni corre el pipeline). Mostrar al usuario la tabla:
   - **Obligatorios** (CP en `data/raw/<ciudad>/<cliente>/cp/`, AltScore en `.../enrichedgeodata/`): si alguno dice FALTA,
     INCOMPLETO o NO CUBRE → **DETENERSE y pedirlo** (no usar el CP o AltScore de otro bottler ni de otra ciudad).
   - **Opcionales** (Rappi, Whisp): decir cuáles VIENEN y cuáles no. Lo que viene se usa y se presenta en TODO (Excel, mapa
     y las dos presentaciones); lo que no viene no frena.
   - **Configuración**: si la ciudad no está en `config.CIUDADES` → skill `/nse-tiendas-mx`; si el cliente no está en
     `config.CLIENTES` → agregarlo con `ventas=None` (las ventas ya no se usan).
2. **Preguntar lo que no se puede asumir** (ver "Decisiones que NO asumas"). CDMX: la ZM del Valle de México abarca CDMX (09),
   Estado de México (15) e Hidalgo (13); `config.CIUDADES` hoy es de un solo estado (`ENT`) → preguntar el alcance (solo las 16
   alcaldías o la ZM completa, que pide adaptar el código a varios estados) antes de configurar.
3. Correr `uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 <ciudad>` (ZM grande: proceso aparte con log).
4. Revisar (Paso 3 y 4 de abajo): Excel sin celdas vacías, mapa HTML (paso 4 de prioridad), cifras del 05 y 06.
5. **Al terminar, crear los dos artifacts con su nombre** (tipo Slides, Kin DS): "Golden Stores · Tradicional · <BOTTLER> <Ciudad>"
   y "Letras por PDV · <BOTTLER> <Ciudad>" (p. ej. "Golden Stores · Tradicional · FEMSA CDMX"), llenarlos con la receta de
   `references/claude_design_marca.md` ("Deck de un bottler nuevo") y `scripts/cifras_decks.py`, con las láminas de los datos
   opcionales que vinieron (Whisp: `prioridad` y `prio-whisp`). Registrar las URLs en la tabla del CLAUDE.md y en la memoria.
6. Actualizar CLAUDE.md (cifras de referencia de la ciudad) y, si cambió el flujo, el flujograma (archify).
7. **QA contra Nielsen (si hay línea base):** carpeta `qa/<Carpeta>/` con el Golden Stores de Nielsen y la copia del Excel de letras
   del 06; agregar la ciudad a `QA_CIUDADES` en `qa/_src/qa_linea_base_nielsen.py` y `qa2_primera_letra.py` (carpeta, archivo,
   canal, filtro de la ZM y región) y a `CARPETA` en `qa/correr_qa.py`, y correr `uv run python qa/correr_qa.py <ciudad>` (QA 1 →
   QA 2 → base vs final; Guadalajara ≈ 15 min). Sale todo: tarjeta, Whisp (sección G: ¿mueve a favor? Letra 2, clúster y
   prioridad; **Whisp no toca la Letra 1, que es NSE**), % de acierto por municipio y por estado, y el Excel "QA en %".
   Revisar primero si la 1.ª letra de esa línea base sigue su propio NSE (hoja "Qué decide la 1.ª letra"): en autoservicios sí
   (Mérida AUC 0.99); en farmacias no (Guadalajara 0.49 nacional, 0.22 en la ZM): ahí el acierto de nuestra Letra 1 tiene techo bajo.

## Paso 0 — Datos del cliente (OBLIGATORIO, sin esto no se avanza)

Busca en `data/raw/<ciudad>/<cliente>/` (Bepensa: `data/raw/merida/bepensa/`):

1. **Customer Potential** (`cp/*.csv`, OBLIGATORIO): id de PDV, **latitud y longitud**, subcanal y, por categoría, venta media
   (`PotentialQuantitative_<cat>`), potencial (`PotentialQuantitativeFinal_<cat>`) y clase (`PotentialQualitative_<cat>`).
   **El 05 y el 06 usan solo el CP** (usuario, 2026-10-01: "ya no ocupamos ventas, ahora solo ocupamos CP"): la venta de cada
   tienda es la venta media del CP de la categoría (`config.CP_CATEGORIA`, Bepensa `CustomCat_sueros`).
2. **Ventas por punto de venta: YA NO SE USAN** (usuario, 2026-10-05). No pedirlas; todas las ciudades corren `00_cp_validacion`.

3. **AltScore** (`enrichedgeodata/geohex_geodig.parquet`, OBLIGATORIO; usuario, 2026-10-05). Acepta `location.lat` + `location.lng` o
   `location.lon`, y `pos_id` UUID o numérico.
4. **Whisp** (`data/raw/whisp/Whisp.csv`, opcional, compartido): ventas por hexágono H3 res 6 y fabricante (hoy Occidente y CD.MX).
   El 07 lee `Year-Month, Categoria, Segmento, Fabricante, Región, SubTerritorio, Hexágono (Res. 6), Cajas Unidad, Revenue`.
5. **Rappi** (`data/raw/rappi/rappi.csv`, nacional, compartido). **No se toma lo que dice `BRAND_x`** (usuario, 2026-10-05): el 00c
   quita al leer las marcas anonimizadas `BRAND_####` (`config.RAPPI_EXCLUIR_MARCA`; 56.5% de las líneas, casi todos los
   competidores), así que Rappi queda solo Coca-Cola y las comparaciones contra competidores del EDA dicen "no aplica". En la Letra 2
   entran **Powerade, Flashlyte, Glacéau Vitamin Water y Vitamin Water** en cualquier subcategoría (`config.RAPPI_MARCAS_L2`).

**Datos opcionales (Rappi, Whisp): si no vienen, el proceso sigue sin ellos; si VIENEN, tienen que verse en TODO** (usuario,
2026-10-05): Excel, mapa HTML (capa y paso propios) y **las dos presentaciones** (Golden Stores y Letras). Con Whisp: el mapa trae el
paso "4. Prioridad: Letra 1 × share Whisp" (capa de hexágonos res 6 con share alto/bajo y PDV coloreados P1–P4), el deck de Letras
una lámina "Prioridad con Whisp" y el deck Golden Stores la lámina `prio-whisp` (tabla pos_id · NSE · venta · CP · Rappi · share ·
Letra 1 · Letra 2 · share alto/bajo · prioridad con 8 tiendas reales, una por combinación, y el conteo P1–P4), después de `p1`.
Sin Whisp, el paso 4 del mapa es "Prioridad por letras" y no se agregan esas láminas.

**Si falta el CP o AltScore: DETENTE y pídelo al usuario** (`src/correr.py` ya no corre la ciudad). No inventes datos ni uses otra
fuente como sustituto (p. ej. el CP de FEMSA no cubre Guadalajara: el de Guadalajara es Arca). Todo lo demás (Censo, ENIGH, Marco
Geoestadístico, DENUE, AMAI) se descarga solo. **Cada ciudad es independiente** (Mérida = Bepensa, Guadalajara = Arca).

## Paso 1 — Configurar

En `src/config.py`: el bloque de la ciudad en `CIUDADES` (si es nueva, sigue `/nse-tiendas-mx`) y su cliente en `CLIENTES`
(`cliente`, `nombre` para los textos, `cp` y `ventas` = patrón o `None`). `CLIENTE`, `CLIENTE_NOMBRE`, `CLIENTE_CP`, `CLIENTE_ALTSCORE`
salen de ahí según `CIUDAD`. `RADIO_PDV_M = 300`. Whisp: `WHISP_VENTANA`, `WHISP_KO`, `WHISP_RES`.

## Paso 2 — Correr (en paralelo, ~2 min para Mérida)

```bash
uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 <ciudad>
```
00 valida el CP (`00_cp_validacion`) · 00b AltScore · 00c Rappi (sueros e hidratación) · 01 hogares por AGEB · 02 tiendas DENUE ·
04 perfil a ≤ 300 m (variable 1: demanda potencial) · 05 Golden Stores (variable 2: venta media del CP) + deck + Excel · 06 Letra 1
(demanda: NSE del clúster) y Letra 2 (venta: venta y CP del CP + Rappi), prioridad, mapa interactivo y Excel (completo, reducido,
diccionario, entregable final) · 07 share de Coca-Cola de Whisp por hexágono res 6 → prioridad
(corre antes del 06; si Whisp no cubre el área, la prioridad queda por letras). El "00" es `00_cp_validacion` si la ciudad no declara
ventas. Para corridas largas (Guadalajara ≈ 40 min) lanzar `correr.py` como proceso aparte con log (las tareas en segundo plano se
cortan a los 30 min). Los ejecutados quedan en `notebooks/ejecutados/<ciudad>/`; los intermedios en `data/processed/<ciudad>/<cliente>/`.

## Paso 3 — Revisar antes de entregar

- **00 → hoja Hallazgos:** coordenadas, PDV en la ZM, canal y potencial vacío en PDV sin venta,
  cobertura, % de cajas sin ubicar, señales con fuga. Si la llave no se puede probar, **pregunta** antes de seguir.
- **02:** cadenas locales detectadas dentro de abarrotes (falsos positivos) y cadenas nuevas del cliente → `src/cadenas.py`.
- **04 → Robustez:** asociaciones que sobreviven al bootstrap espacial por bloques.
- **05 → sección 2b (QA) y 2c (piloto):** brecha HL vs HH real vs al azar (si son iguales, no es oportunidad),
  Spearman demanda vs venta, % frontera, excluidas sin hogares, y MDE del piloto por universo. Los títulos con cifras se
  calculan, no se escriben a mano.
- **Fuentes:** revisar si hay ediciones nuevas (Marco Geoestadístico, DENUE semestral, Intercensal, Regla AMAI) y actualizar `FUENTES`
  / `MG_VERSION` en `src/config.py`. La demanda usa hogares por área de manzana + localidades rurales, actualizados con la Intercensal.

## Paso 4 — Presentación ejecutiva y Excel (QA obligatorio)

El 05 genera, en la carpeta del cliente (solo entregables), `outputs/<ciudad>/<cliente>/cliente/05_golden_stores_<canal>_<cliente>_zm_<ciudad>.pptx`
y `.xlsx`. Los Excel de análisis y QA (00-04, 06) quedan en `outputs/<ciudad>/<cliente>/`:
- **Deck**: metodología Golden Stores intacta, contada con la skill `/executive-pitch-presentation-builder` (BLUF: resumen y
  decisión primero; costo de la inacción; solución; evidencia; caso de negocio en cajas; ruta de 90 días con puertas de
  decisión; riesgos; anexo con metodología, datos y objeciones). Titulares de acción con cifras calculadas, **ejemplos con
  tiendas reales** (una por clúster y un recorrido paso a paso) y guion en las notas de cada lámina.
- **Excel corporativo** (`src/excel_kin.py`): Portada con índice · Resumen con fórmulas vivas sobre Tiendas · Tiendas
  (clúster y semáforo con color, Prioridad (letras), P1 de Golden Stores, hogares e índice de demanda ANTES que venta e índice de
  venta, barras de datos, filtros) · Perfiles · Accionables · Guion y objeciones · Diccionario.

El 06 escribe en `cliente/` (además del pptx de letras):
- `06_letras_nse_ventas_tradicional_*.xlsx`: completo (hoja **Letras por PDV** con bloques de color, 2 niveles y 3.ª fila de fuente).
- `06_letras_nse_ventas_tradicional_reducido_*.xlsx`: el mismo formato con solo las columnas de la ficha del mapa (`RED_COLS`) y al
  final Letras base (INEGI + CP) · Letras (final) · Acción Golden Stores · Prioridad; hoja **Diccionario**.
- `06_diccionario_letras_*.xlsx`: definición, fuente/fórmula y unidad de cada columna (`DEFINICION` en el 06).
- `06_entregable_final_letras_*.xlsx`: `pos_id, lat, lon` + 3 columnas `*_TotalPortafolio` del CP tal cual + `segmento_golden_store`,
  `prioridad`, `accion` (ninguna celda vacía sin motivo).
- Mapa `outputs/<ciudad>/<cliente>/06_mapa_qa_letras_*.html` con la marca Kin (`src/mapas.py`, skill `brand-guidelines-kin`): sin la
  palabra "QA" en pantalla, pasos numerados, filtro en chips, búsqueda con Enter, leyenda flotante y ficha con chips; el PDV elegido
  lleva anillo amarillo.

- **Ninguna celda vacía** en los Excel del 06: `tabla_pdv` escribe el motivo de cada faltante (sin venta, sin NSE, fuera de AGEB
  urbana, sin dato AltScore…). Revisar con pandas que `Letras por PDV` tenga 0 NaN después de cada cambio de columnas.
- `07_whisp_share_*.xlsx` (en `outputs/<ciudad>/<cliente>/`): Resumen · Share por hexágono (Región, SubTerritorio principal y todos,
  Segmento, SOM = `share_cajas` = cajas KO / total, share por categoría) · Fabricantes por Categoría · Categorías × Segmento.

**Láminas que explican el mapa** (para pegar en un deck): `uv run python .claude/skills/golden-stores-kin/scripts/laminas_mapa.py
[--pos 2720] [--ciudad guadalajara --cliente arca]` (elegir un PDV HH con nombre comercial, Rappi a 300 m y un clúster de 3-6 PDV
para que no se encimen los números) → `cliente/laminas/` (cómo leer el mapa, la ficha del PDV, diccionario en 3) y `cliente/laminas/figuras/` (solo la
figura, para subirla como asset a Claude Design y poner el texto editable en la lámina).

QA: `python .claude/skills/golden-stores-kin/scripts/qa_deck.py <deck.pptx> [carpeta]` y **mirar cada lámina**; validar el
pptx con la skill pptx; recalcular el Excel con LibreOffice y confirmar que el Resumen coincide con el notebook.

**Presentación en Claude Design (obligatorio, usuario 2026-10-01).** La versión para presentar se crea o actualiza como artifact
del tipo **Slides** (`Artifact` → `quickstart` con `intent: "slides"`) con el design system **Kin Design System - Kin Official**
(instalarlo en el deck: `tokens.json`, fuentes `fonts/*.ttf` y logos PNG de `templates/kin-presentation/assets/`; los SVG no se
copian). Mismo contenido, cifras y notas que el pptx; tablas largas se parten en dos láminas; gráficas como barras HTML editables.
Sin signo `$`, sin "Let knowledge in", pie `kinanalytics.com` en minúsculas.
**Lineamientos de marca (usuario, 2026-10-01): skill `brand-guidelines-kin`** (en `.claude/skills/`). Portada con foto duotono y
título amarillo, divisores con panel amarillo en punta de hexágono, eyebrow gris y pie logo + URL: receta, assets a copiar del DS y
excepciones en `references/claude_design_marca.md`; `scripts/marca_claude_design.py <carpeta_deck>` normaliza las láminas de
contenido y trae `portada()`, `divisor()` y `cierre()`.
**Un bottler o ciudad nuevos = artifacts nuevos** (trazabilidad): crear dos decks ("Golden Stores · <canal> · <BOTTLER> <Ciudad>" y
"Letras por PDV · <BOTTLER> <Ciudad>") y registrar sus URLs en la tabla del CLAUDE.md ("Para empezar"); los decks de otros bottlers o
ciudades no se modifican. Si es el mismo bottler y ciudad, se actualizan sus decks registrados (misma URL).
**Cifras para los decks:** `uv run python .claude/skills/golden-stores-kin/scripts/cifras_decks.py <ciudad> <cliente> [--ejemplos
"NOMBRE|NOMBRE"]` imprime todo lo que llevan las láminas (Golden Stores sobre las letras del 06 y PDV con venta; Letras desde el Excel
y el notebook del 06). Un deck nuevo se arma copiando las láminas de los decks de Bepensa (estructura y formato del usuario) y
cambiando solo cifras, figuras y nombres: receta en `references/claude_design_marca.md` ("Deck de un bottler nuevo").

## Decisiones que NO asumas: pregúntalas

- **Canal target** del deck (`CANALES_DECK` en el 05). Bepensa: Tradicional.
- Municipios de la ZM si solo dan la ciudad · radio del área (default 300 m; 500 m se consideró demasiado lejos).
- ZM de varios estados (Valle de México: CDMX + Edo. Méx. + Hidalgo): alcance y si se adapta el código (hoy un `ENT` por ciudad).
- Qué CP usar si el bottler manda varios (región, categoría): la categoría del CP es `config.CP_CATEGORIA`.
- Clasificación de franquicias y cadenas de farmacias (Bepensa: Six = Tradicional; Modelorama y farmacias de cadena = Moderno).

## Reglas fijas (decididas con el usuario)

- **La metodología Golden Stores no se cambia** (clústeres, índice 100, accionables Atacar/Bloquear/Fortalecer/Mantener,
  semáforos, P1 = HH y LH en verde y amarillo). Solo se sustituyen las fuentes de ventas y demanda.
- **Primero la demanda, luego la venta** (usuario, 2026-10-02): 1.ª letra = demanda (NSE / hogares), 2.ª = venta, en textos,
  columnas, ejes y láminas (HL = demanda alta / venta baja = Bloquear; LH = demanda baja / venta alta = Fortalecer).
- **Prioridad** (usuario): con Whisp (paso 07) = **Letra 1 × share de Coca-Cola** del hexágono res 6 (H bajo P1 · H alto P2 · L bajo
  P3 · L alto P4; alto = share ≥ share del área); sin Whisp = por letras HH P1 · HL P2 · LH P3 · LL P4 (también en PDV sin venta).
  Convive con el P1 de Golden Stores del 05, que no cambia.
- **Decks de Claude Design: "sin cambiar formato, solo actualiza datos"** y, al agregar láminas, no tocar las demás (usuario).
- **Rappi** = solo hidratación Coca-Cola (Powerade, Flashlyte, Vitamin Water), sin marcas `BRAND_x`; pedidos/mes, nunca pesos.
- **Excel sin celdas vacías**: cada faltante lleva su motivo.
- **El CP es potencial futuro: variable de clasificación, no decisiva** (su venta media sí es la variable de venta).
- La unidad es el PDV: no calificar la ZM completa ni por demografía agregada.
- Moderno y Tradicional se analizan y entregan por separado.
