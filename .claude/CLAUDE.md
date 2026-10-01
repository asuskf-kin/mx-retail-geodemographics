# Proyecto: perfil socioeconómico de hogares × tiendas (ZM Mérida)

Pipeline reproducible con fuentes oficiales (INEGI y AMAI). Produce, **por AGEB** y **por tienda**,
la distribución de hogares por tamaño, edad del menor, edad del jefe y NSE (Regla AMAI 2024, mismos puntos que la 2022), con HHs, % e Índice.
Separa los canales **Moderno** (cadenas) y **Tradicional** (abarrotes e independientes) en el DENUE (01-03); las letras del cliente
(05 y 06) son **solo canal Tradicional**.

Para replicarlo en otra ciudad usa la skill `/nse-tiendas-mx` (en `.claude/skills/nse-tiendas-mx/`).

## Para empezar (persona o sesión nueva) — estado al 2026-10-01
**Reglas de trabajo** (pedidas por el usuario; antes vivían solo en la memoria local de una sesión):
1. **Solo ZM Mérida.** Es la única ciudad con datos del cliente; no re-correr Guadalajara ni otras al cambiar código o fuentes.
2. **Sin datos del cliente no se avanza:** el 05 necesita ventas + CP en `data/raw/merida/bepensa/{ventas,cp}`; el 06 solo el CP (trae la
   venta). Si faltan, detenerse y pedirlos (no están en git). Rappi (`data/raw/rappi/rappi.csv`) y AltScore (`enrichedgeodata/`) tampoco.
3. **Al cambiar una regla se actualiza todo:** notebook `_src` → CLAUDE.md (decisiones y cifras de referencia) → flujograma
   (`docs/flujo_pipeline.dataflow.json`, skill archify: `deliver` + `visual-check`) → entregables de `cliente/` y mapa HTML → flujo completo
   (`uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,06 merida`, ≈ 7 min) → **presentaciones en Claude Design**.
4. **Presentaciones = Claude Design** (usuario, 2026-10-01): toda presentación nueva o actualizada se hace como artifact del tipo
   **Slides** con el design system **"Kin Design System - Kin Official"** (default de la organización; Space Grotesk + Albert Sans, logos
   PNG de `templates/kin-presentation/assets/`; los SVG no se pueden copiar entre artifacts). Guarda versiones solas. El pptx de
   `src/deck_kin.py` se sigue generando en `cliente/`, pero la versión para presentar es la de Claude Design.
   **Un bottler o ciudad nuevos = artifacts nuevos** (usuario, 2026-10-01, por trazabilidad): se crean dos decks nuevos, titulados
   "Golden Stores · <canal> · <BOTTLER> <Ciudad>" y "Letras por PDV · <BOTTLER> <Ciudad>"; los de otro bottler o ciudad **no se tocan**
   (cada artifact guarda su propio historial de versiones). Un cambio de cifras o reglas del mismo bottler y ciudad actualiza sus decks
   (misma URL). Al crear uno, registrar su URL aquí:

   | Bottler · ciudad | Golden Stores (05) | Letras (06) |
   |---|---|---|
   | Bepensa · ZM Mérida | https://claude.ai/artifact/W5dGqa18ux9yws1UriJkzx | https://claude.ai/artifact/JGHg6YqT9oYVr5BJ5Vx2fn |

   Se escriben a mano con las cifras de los notebooks ejecutados (no se generan solos): si cambian las cifras, actualizar sus láminas.
   Figuras: recortar los PNG de `notebooks/ejecutados/merida/06_*.ipynb` y subirlos como asset del artifact.
5. **Estilo:** sin el signo **$** en presentaciones (Rappi va en pedidos/mes); nunca la frase "Let knowledge in"; URL `kinanalytics.com`
   en minúsculas; en el Excel ninguna celda queda vacía sin motivo ("no aplica · sin venta", "sin NSE (sin hogares a 300 m)", …);
   "la venta es la media" (no "promedio"); no inventar cifras ni fuentes.
6. Commits solo cuando el usuario lo pide.

**Pendientes de decisión del usuario** (no cambiar sin preguntar):
- Letra 2: el PDV sin Rappi a 300 m (88%) empata en el rango medio (0.56) y por eso Rappi baja 204 letras y sube 83; cualquier Rappi
  queda en el 12% de arriba. Opciones: rango neutro o score solo con venta y CP para quien no tiene Rappi.
- AltScore: índice débil (α 0.47, 2 proxies) que mueve 447 Letras 1 con λ = 0.25.
- Tiendas Rappi: hoy entran todas (221); el 00c dice que pasan las activas (106). Con solo activas cambian 91 Letras 2.
- Índice del 04/05 vs ZM: la referencia es la ZM 2020 urbana (`nse_ageb`), pero los hogares son 2025 con rurales (A/B ≈ 94, D/E ≈ 107
  para una zona con la mezcla media). Validar Nielsen (1.ª letra en sueros) cuando el usuario comparta esas tiendas.
- Share y prioridad P1–P4 (omitidos hasta que el usuario dé la fuente del share).

**Problemas conocidos** (revisión del 2026-10-01; todo lo demás cuadra con las cifras de abajo): el DENUE vigente queda fijo en la copia
local (no avisa cuando salga la 11_2026, el 2026-11-25); el factor EIC 2020→2025 es parejo dentro de cada municipio; 110 hogares rurales
sin geometría quedan fuera del 04 (0.03%); el 03 sigue con centroides de manzana (352,851 hogares) y sin rurales ni EIC.

## Estructura
```
src/config.py        ← ÚNICO lugar a editar: un bloque por ciudad en CIUDADES; la activa en CIUDAD (o env var CIUDAD)
src/descargas.py     descarga con reanudación HTTP Range (INEGI corta conexiones: ChunkedEncodingError)
src/nse.py           Regla AMAI 2024 (= puntos 2022) + logit ENIGH 2024 para # baños y # autos
src/microsim.py      IPU vectorizado (todas las AGEB a la vez)
src/eda.py           estadística del notebook 00 (port de la skill retail-math-eda: IC bootstrap, Hill, AIC, KM, δ de Cliff, BH)
src/correr.py        corre los notebooks por ciudad (en paralelo según dependencias) y guarda los ejecutados
src/cadenas.py       cadenas y canal Moderno/Tradicional: única regla para DENUE y PDV del cliente
src/altscore.py      señales AltScore del cliente: carga (geohex_geodig.parquet, centinelas → NaN), familias, ubicación (location.lat/lng)
                     e índice NSE AltScore (PC1 de los proxies que forman escala en la ZM, `seleccionar_proxies`)
src/rappi.py         Rappi: etiquetas de ciudad, regla "sueros primero" (subcategoría → marca → nombre → categoría), tiendas físicas
src/letras.py        fórmulas del 06: Letra 1 (NSE del clúster H3 res 9 + 300 m; `a_escala` y `mover_nse`: AltScore mueve el NSE) y
                     Letra 2 (`rango_desc` y `score_letra2`: rangos de venta, CP y Rappi), `centros` y áreas H3
src/mapas.py         mapas de QA: fondo estático (matplotlib) y mapa HTML interactivo (Leaflet + h3-js; fondo OpenFreeMap con datos OSM, filtro,
                     capas hex de varias fuentes y selección del clúster NSE)
src/deck_kin.py      estilo Kin para presentaciones (python-pptx) · src/excel_kin.py formato Kin para entregables Excel (00b-06)
src/py2nb.py         convierte notebooks/_src/*.py (celdas "# %%") → notebooks/*.ipynb
notebooks/_src/*.py  FUENTE de los notebooks: edita aquí, luego regenera el .ipynb
notebooks/01..03     pipeline de hogares y tiendas (correr en orden)
notebooks/00, 00b, 00c, 04, 05, 06 cliente Bepensa (solo ZM Mérida): 00 valida ventas × CP · 00b EDA AltScore · 00c EDA Rappi (sueros e
                     hidratación) · 04 perfil por PDV a ≤300 m · 05 Golden Stores (deck + Excel) · 06 letras del canal Tradicional
                     (Letra 1 = NSE del clúster hexagonal + AltScore · Letra 2 = venta y CP del CP + Rappi)
.claude/skills       nse-tiendas-mx (otra ciudad) · golden-stores-kin (cliente + deck, con scripts/instalar.py y qa_deck.py) ·
                     executive-pitch-presentation-builder · retail-math-eda · archify
data/raw/merida/bepensa/  todo lo de Mérida: ventas/ y cp/ del cliente + fuentes_oficiales/<institución>/<fuente>/ (se regeneran solas)
                     (ciudad sin cliente: data/raw/<ciudad>/fuentes_oficiales/) · data/raw/rappi/rappi.csv: Rappi nacional (fuera de git)
data/processed/merida/bepensa/   intermedios (misma estructura ciudad → bottler; ciudad sin cliente: data/processed/<ciudad>/)
outputs/merida/bepensa/          Excel de análisis y QA (00-04) y el mapa HTML de QA del 06
outputs/merida/bepensa/cliente/  SOLO lo que se entrega al cliente: 05 (deck + Excel Golden Stores) y 06 (Excel de letras del canal
                                 Tradicional + su presentación); versiones viejas en anteriores/ (crearla al guardar una)
docs/flujo_pipeline.*            flujograma del pipeline 00 → 06 (skill archify: .dataflow.json → .html con validate, deliver y
                                 visual-check); el anterior (solo 01-03) en docs/anteriores/. Se actualiza cuando cambia el flujo
pyproject.toml · uv.lock · .python-version   proyecto uv (Python 3.14, entorno en .venv; requirements.txt queda para pip)
```

## Cómo correr
```bash
uv sync                                      # crea/actualiza .venv con uv.lock (una vez por máquina; uv.lock va en git)
uv run python -m ipykernel install --user --name mx-retail-geodemographics --display-name "Python (mx-retail-geodemographics · uv .venv)"
uv run python src/correr.py merida guadalajara     # regenera los .ipynb desde _src y corre 01 → 02 → 03 por ciudad
uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,06 merida   # Bepensa completo (≈ 5 min en paralelo)
```
Orden para Bepensa: **00 → 00b → 00c → 01 → 02 → 03 → 04 → 05 → 06** (00, 00b y 00c no dependen de nadie; 04 ← 00, 00b, 01, 02;
05 ← 00, 04; 06 ← 00, 00b, 00c, 01, 04). Los notebooks también se pueden abrir y correr a mano en VS Code/Jupyter con el kernel
**"Python (mx-retail-geodemographics · uv .venv)"** (o el intérprete `.venv`): buscan la raíz del repo solos, usan Mérida por
defecto y avisan qué notebook correr si falta un archivo previo. Todo lo aleatorio usa semilla fija (`eda.SEMILLA`): dos corridas dan lo mismo.
`jupyter nbconvert` NO está instalado en esta máquina: `src/correr.py` usa nbclient directo y corre **en paralelo** lo que sus
dependencias permiten (nivel 1: 00, 00b, 00c, 01, 02 · nivel 2: 03, 04 · nivel 3: 05, 06; `--secuencial` para depurar). Las descargas y
extracciones tienen candado entre procesos. Tiempos (2026-09-30, flujo Bepensa completo en 276 s): 00 ≈ 0.5 min, 00b ≈ 1.2 min,
00c ≈ 0.7 min (lee el CSV nacional de Rappi, 769 MB), 01 ≈ 1.1 min, 02 ≈ 2.2 min, 04 ≈ 1.5 min, 05 ≈ 20 s, 06 ≈ 50 s (con mapa, Excel
y deck); Guadalajara ≈ 18 min (lo domina el IPU del 01).

## Qué se guarda (para depurar sin volver a descargar)
- `data/raw/merida/bepensa/fuentes_oficiales/` (otra ciudad sin cliente: `data/raw/<ciudad>/fuentes_oficiales/`): una carpeta por institución y fuente (`INEGI/denue/`, `INEGI/marco_geoestadistico_2025eic/`, …)
  con el zip original, lo extraído (carpeta con el nombre del zip) y `descarga.json` (institución, página, URL, edición, fecha de descarga,
  bytes, SHA-256). `fuentes.csv` en la raíz es el índice de todas. `descargar_fuente()` no re-baja un zip válido.
  Las fuentes nacionales (ENIGH, EIC) se guardan dentro de cada ciudad: cada carpeta de ciudad es autocontenida.
- `data/processed/merida/bepensa/fuentes_usadas_01.csv` y `fuentes_usadas_02.csv`: URL, edición, archivo local, bytes, fecha y SHA-256 de cada fuente usada.
- `data/processed/merida/bepensa/fuentes_cliente_<cliente>_00.csv` (y hoja "Datos del cliente" del xlsx del 00): archivo, filas, fecha y SHA-256
  de las **ventas y el CP del cliente** (insumos críticos; están en `data/raw/merida/bepensa/`, fuera de git: no se suben ni se sustituyen).
  Igual para AltScore (`fuentes_cliente_bepensa_00b.csv`) y Rappi (`fuentes_rappi_00c.csv`).
- `notebooks/ejecutados/<ciudad>/*.ipynb`: notebooks ejecutados con todas sus salidas. `notebooks/*.ipynb` quedan limpios.
- Las URLs viven solo en `src/config.py` → `FUENTES` (y `MG_VERSION`). Los notebooks 01 y 02 las muestran y verifican con HEAD.
Si un xlsx de `outputs/` está abierto en Excel, falla la escritura (aparece el archivo lock `~$...`).

## Entorno (probado)
**uv**: `pyproject.toml` + `uv.lock` (76 paquetes, pins de `requirements.txt`), Python 3.14.6 en `.venv` (`.python-version`). Kernel registrado:
"Python (mx-retail-geodemographics · uv .venv)". El Python 3.12 del sistema tiene **pyproj roto** (instalación interrumpida el 2026-09-25:
`DLL load failed while importing _context`); con `.venv` no importa. Para repararlo: cerrar sus kernels y
`python -m pip install --force-reinstall --no-deps pyproj==3.8.0` con ese intérprete.
Python 3.14 · pandas 3 · geopandas 1.1 · scikit-learn 1.9 · nbclient · openpyxl · pyarrow · requests · pypdf.
- **pandas 3 usa cadenas Arrow**: `serie.values[:, None]` falla. Usa `.to_numpy(dtype=object)`.
- En Windows se necesita `PYTHONIOENCODING=utf-8` para imprimir acentos desde bash.
- El DENUE viene en **latin-1**. Los CSV del Censo AGEB vienen en **utf-8-sig** (Yucatán) o **latin-1** (Jalisco): el notebook 01 prueba ambos.
- Overpass (OSM) **exige el header User-Agent**: sin él la petición falla con HTTPError.

## Resultados de referencia (para detectar regresiones)
Ciudades configuradas: `merida`, `guadalajara`. Fuentes (revisadas 2026-09-25, las más recientes): Censo 2020 (AGEB/manzana, ITER y muestra), Encuesta Intercensal 2025 (municipio; publicada 2026-09-22), ENIGH 2024, Marco Geoestadístico de la Intercensal 2025 (UPC 794551196649, `MG_VERSION="2025eic"`), DENUE 05_2026 (la 11_2026 sale el 2026-11-25), Regla AMAI 2024 (AMAI anunció actualización en 2026 con ENIGH 2024: revisar). Las salidas de Mérida previas a la parametrización por ciudad
están en `outputs/` (raíz). El 2026-09-29 se vació `data/processed/` (a la Papelera) y todo Mérida se regeneró en `data/processed/merida/bepensa/`
con las mismas cifras de abajo; los intermedios de Guadalajara se regeneran solo si se vuelve a correr esa ciudad.

### Mérida
- ENIGH: NSE imputado vs real en Yucatán urbano, diferencia ≤ 1.3 pp por nivel.
- ZM Mérida: 635 AGEB urbanas, 354,033 hogares, 11,716 hogares donantes en la muestra.
- ZM Mérida NSE: A/B 14.1 · C+ 16.8 · C 16.0 · C- 15.7 · D+ 13.6 · D/E 23.9 (%).
- Yucatán estatal: A/B 8.4 · D/E 40.9.
- DENUE 05_2026, ZM: 5,887 tiendas. Moderno 840, Tradicional 5,047 (Modelorama y farmacias de cadena pasaron a Moderno).
- Radio 1 km: mediana ≈ 3,972 hogares por tienda (500 m: 1,112). Con MG 2020 era 3,981.
- Con MG Intercensal 2025: 19,718 polígonos de manzana guardados; 84 manzanas del Censo sin polígono (1,182 hogares, 0.33%; en el 04 se reparten sobre su AGEB); 63 tiendas fuera de AGEB.
- Localidades rurales (ITER 2020) en la ZM: 301 con 15,239 hogares (4.1%); perfil de hogares rurales de la muestra (TAMLOC = 1) por municipio.
- Intercensal 2025, factor de población 2020→2025: Conkal ×1.398 · Kanasín ×1.259 · Mérida ×1.059 · Ucú ×1.084 · Umán ×1.184 (ZM ×1.094).
  No se usan los hogares EIC directamente: en la EIC hogar = vivienda e implican una caída de tamaño del hogar de ~10% en 5 años.

### Bepensa (ZM Mérida, notebooks 00 y 04)
- Llave: empata 73.3% de los registros de ventas (azar 3.7%); en prefijos de la ZM quedan sin ubicar 30.9% de las cajas (pocas cuentas grandes).
- 7,455 PDV del CP en la ZM, 5,978 con venta. Mediana 2.07 cajas/mes de vida; Gini 0.58; KM S(12 m) = 0.86.
- 04: hogares por **área de manzana** (no centroide) + rurales, actualizados a 2025: 403,069 hogares. Mediana 18 hexágonos por área (≈ 0.27 km²);
  53 PDV sin hogares a ≤ 300 m (con centroides eran 576). Moran I = 0.058 (p = 0.005); 83 asociaciones robustas de 90 (entran las señales AltScore).
  AltScore por buffer (media de los puntos AltScore a ≤ 300 m del PDV): 94% de los PDV con índice (mediana 25 puntos); vs % A/B + C+
  INEGI del mismo buffer: ρ = +0.47 (IC bloques +0.34 a +0.57, 6,820 PDV).
- 00b AltScore (`enrichedgeodata/geohex_geodig.parquet`, exportación del 2026-09-30): 91,677 filas de la península con `location.lat/lng`
  y `geoHexData_hexIdx_res8/9` (centinelas −999999/−999998/−999997 → NaN); 22,325 caen en la ZM (Mérida 19,142 · Kanasín 1,954 · Umán 927
  · Conkal 253 · Ucú 49) y el EDA va solo con esas. Los 4 proxies anteriores (iOS, macOS, viajes, idiomas no españoles; α 0.70 en la
  península) no forman escala en la ZM (6 a priori: α −0.04; viajes e idiomas marcan ciudades turísticas) → análisis de ítems iterativo
  (ítem-resto ≥ 0.2, `altscore.seleccionar_proxies`): índice NSE AltScore = PC1 de **iOS % y macOS %** (α 0.47, 65% de la varianza,
  cobertura 98%). Pasan el índice + 7 señales (una por dimensión; cubren 8 de 19 dimensiones). QA: la selección se reproduce en 55% de
  las mitades; α fuera de muestra 0.48 (IC 0.35–0.60). Faltantes OSM no MCAR.
- 05 Tradicional: 5,556 tiendas. HH 786 (14%, 27% de la venta, índice 189) · HL 1,922 · LH 1,138 (47% de la venta) · LL 1,710.
  P1 = 1,554 tiendas (66% de la venta ubicada); HH verde 165. HL no activas 1,070 (56%). Piloto recomendado: HH verde y amarillo (594 tiendas,
  59 zonas H3 r7, MDE 10.3% sin línea base / 6% con línea base). Excluidas sin hogares: 51 tiendas (1% de la venta).

### Rappi (notebook 00c, `data/raw/rappi/rappi.csv`, nacional: 864,704 líneas)
- ZM Mérida (polígono): 29,785 líneas; la etiqueta `city` ("Merida"/"Mérida") coincide 100% con el polígono (4 líneas sin coordenadas).
- Regla "sueros primero" en la ventana: 26,876 líneas, 21,947 pedidos, $1.35 M MXN; sale Vitamin Water (agua funcional).
  Sueros 31% de la venta, isotónicos 69%. Coca-Cola (sistema Bepensa: Powerade, Flashlyte) 48% del valor (sueros 22%, isotónicos 59%).
- **Cobertura:** oct-dic 2024 sin cadena ni vertical y sin BRAND_4866 (20% de la venta nacional) → ventana ene-2025 → ago-2026.
  `datetime` dice "Z" pero es hora local (1-6 h: 0.1% vs 25% si fuera UTC). Crecimiento ene-ago 2026 vs 2025: +3.6% (IC95 −6.3% a +15.1%).
- 555 store_id → 221 tiendas físicas (≤ 25 m); 106 activas (≥ 12 pedidos, 94% de la venta), 72 activas en sueros; 2 Turbo = 33% de la venta.
  Duplicados exactos: Coca-Cola 0.9% (base) vs competidores 19.4% (anonimizados a nivel marca): se conservan.

### Letras (notebook 06: canal Tradicional y solo datos del CP; reglas del usuario del 2026-09-30, pendiente validar λ)
- CP en la ZM: 7,455 PDV → se quitan 418 Moderno (Modelorama 148, farmacias de cadena…) → 7,037 Tradicional; 5,607 con venta según el CP
  (venta media > 0); **5,566 objetivo** (con venta y hogares en su clúster NSE).
- Clúster NSE (H3 res 9 + buffer de 300 m desde el centro): 2,004 clústeres con PDV objetivo, mediana 2 PDV (p90 5, máx. 29), 31% con un
  solo PDV; ningún PDV a más de 208 m del centro (mediana 132 m); N del clúster vs N del buffer del propio PDV: ρ = 0.99; 41 PDV con venta
  en clústeres sin hogares. NSE AMAI vs Censo por manzana: ρ = +0.93 (IC 0.90-0.94); η² por AGEB 0.78. Predominante: bajo 77 · medio 8 ·
  alto 14 (%); el nivel N cae entre 2.5 y 4.5 en 65% de los PDV (por eso "casi todo se ve medio").
- AltScore mueve el NSE: 82% de los clústeres con PDV objetivo tienen ≥ 5 puntos (mediana 20); AltScore vs N INEGI por clúster ρ = +0.47
  (IC 0.35-0.56); para predecir el Censo por manzana, INEGI β = +0.96 y AltScore β = −0.02 (IC −0.05 a +0.02): no agrega a la medición
  directa. λ = 0.25 → cambia 447 Letras 1 (299 ↑, 148 ↓; 8%); λ = 0.5 → 974; λ = 1 → 1,827 (κ con el Censo 0.76 · 0.62 · 0.32).
- Letra 1 = H en 48% (sin AltScore 46%); confirmada por el Censo en 88% (solo INEGI 91%); κ de la letra INEGI con ABC+ 0.93, Censo 0.83,
  buffer del propio PDV 0.95, buffers de 200/400 m 0.96/0.97, AltScore solo 0.26, hogares (sin NSE) 0.22.
- Letra 2 = score de rangos (usuario, 2026-09-30): H en 29.4% de los objetivo (sin Rappi 31.6%). Venta del CP mediana 2.58 cajas/mes;
  CP con decimales mediana 0.17, 19% en 0 (redondeado quedaba 79%); ρ(venta, CP) = +0.22. Rappi del buffer: 221 tiendas (106 activas),
  643 PDV objetivo (11.6%) con alguna a ≤ 300 m; el 88% sin Rappi empata en el rango 0.56. Rappi cambia 287 letras (83 ↑, **204 ↓**: el
  rango medio de "sin Rappi" baja a quien estaba cerca del corte). Misma letra: sin CP 81%, CP redondeado 88%, pesos 1·1·1 95%, corte
  0.35 / 0.45 93%, solo tiendas activas 98%, suma en vez de media 100%, empates en el peor rango 91%. Venta con vs sin Rappi: δ = −0.01.
- Letras finales: HH 815 (15% de tiendas, 24% de la venta, índice 161) · HL 1,874 · LH 824 (25%) · LL 2,053; 87% igual a las letras
  base (solo INEGI + CP). Los 1,418 PDV sin venta con NSE quedan L en la Letra 2. Excel de 16 hojas (con "Vector Letra 2"); deck de 14 láminas;
  tabla intermedia en `data/processed/merida/bepensa/letra2_vector_bepensa_zm_merida.parquet`.

### Guadalajara (10 municipios Metrópolis 2020, región Pacífico, ENIGH 01·06·14·16·18)
- **Sin datos de cliente: el trabajo con Bepensa es solo Mérida.** Estas cifras son de la corrida con MG 2025 y sin rurales ni Intercensal;
  no se re-corrió con las fuentes de 2026-09-25 (se hará solo si llega un cliente en Guadalajara).
- ENIGH: NSE imputado vs real en Jalisco urbano, diferencia ≤ 1.3 pp por nivel (8,547 hogares ENIGH).
- 2,000 AGEB urbanas, 1,443,184 hogares, 40,799 donantes (15,452 patrones de ceros).
- Con MG 2025: 56,316 manzanas; 207 sin polígono (1,587 hogares, 0.11%).
- NSE (suma AGEB): A/B 13.8 · C+ 17.1 · C 17.2 · C- 15.4 · D+ 12.9 · D/E 23.6. Jalisco: A/B 10.3 · D/E 27.0.
- Ajuste microsim: variables de hogar +5–8% sobre el Censo, `cua1` +30%; `ocup12`, `p18pb`, `esc15` ≈ 0.
  No mejora con más iteraciones (200 = 400 = 800): es inconsistencia Censo vs muestra (`ocup12` +11%, `dor1` +10%).
- DENUE 05_2026: 24,031 tiendas. Moderno 1,605 · Tradicional 22,426. 339 tiendas fuera de AGEB urbana (con MG 2020: 380).
- Radio 1 km: mediana ≈ 7,336 hogares por tienda (500 m: 2,128).
- Tiempos: 01 ≈ 10–20 min (según carga de la máquina) · 02 ≈ 4 min · 03 ≈ 5 min.

## Decisiones tomadas con el usuario (no revertir sin preguntar)
- El canal Tradicional incluye SCIAN **461110** (abarrotes), además de los independientes 462111/462112.
- Los "Abarrotes Six" (Grupo Modelo) cuentan como **Tradicional** (`CADENAS_TRADICIONALES` en el notebook 02).
- Moderno y Tradicional se entregan en **xlsx separados** (pasos 02 y 03).
- El layout de salida es un encabezado de 2 niveles: `Latitud, Longitud, Región Nielsen, Estado, Municipio, Localidad, Zonas Metropolitanas` y luego, por categoría, `HHs | % | Indice`.
- El índice se calcula contra el total de la ZM (`REFERENCIA_INDICE="zm"`). La alternativa es `"estado"`.
- **Bepensa = ZM Mérida** (`CLIENTE_CIUDAD`). Área de cada PDV: hexágonos H3 res 10 con centro a **≤ 300 m** (`RADIO_PDV_M`); 500 m es demasiado lejos.
- No calificar la ZM ni por demografía agregada: la unidad de análisis es el PDV con su venta.
- Llave ventas ↔ CP **inferida**: `pos_id` de ventas = prefijo de 4 dígitos (centro de distribución) + `pos_id` del CP a 6 dígitos (pendiente de confirmar con Bepensa).
- Señales del CP: `PotentialQuantitative` y `size_class` son fuga (derivan de la venta); el potencial útil es `PotentialQuantitativeFinal`.
  **En el 06 (usuario, 2026-09-30) la venta SALE DEL CP:** `PotentialQuantitative_TotalPortafolio` es la venta media (ya no se usa el
  archivo de ventas en las letras) y el CP es `PotentialQuantitativeFinal_TotalPortafolio` **con decimales** (usuario, 2026-09-30: "0.6
  cajas son más de 10 unidades"; el redondeo `CP_UMBRAL_REDONDEO` solo queda en el QA). El 06 ya no usa el archivo de ventas en nada, ni para el QA
  (usuario: "usa solo datos de cp"); el 05 sí lo usa.
- **El CP es potencial futuro: variable de clasificación (clase Very High → Low), no decisiva** en el 05. Ojo: la clase mide potencial
  ABSOLUTO (venta actual × brecha): Very High = 0% en la mitad inferior de venta. La brecha relativa (`PotentialEstimatedToCover`) va en el Excel.
  **Excepción decidida por el usuario (2026-09-30): en la Letra 2 del 06 el potencial (`PotentialQuantitativeFinal`) entra al score con peso 2.**
- **Los hogares ocupan toda la manzana**: se reparten por área entre hexágonos (no por centroide) y entran las localidades rurales;
  las manzanas del Censo sin polígono se reparten sobre su AGEB. Nada queda fuera del área por usar un punto.
- **QA metodológico del 05 (no quitar):** la brecha HL vs HH es por construcción (no se presenta como oportunidad); en HL se reporta
  actividad (primero reactivar); semáforo con venta y demanda en log; marcas de frontera (±10) y alta reciente; hoja de excluidas;
  piloto sorteado por zonas H3 r7 con MDE y efecto de diseño; se mide piloto vs control, nunca antes vs después.
- **Metodología Golden Stores (NielsenIQ) fija, no se cambia**: clústeres HH/HL/LH/LL con índice 100 por subcanal, Atacar/Bloquear/
  Fortalecer/Mantener, semáforos por desviación estándar, P1 = HH y LH en verde y amarillo. Deck para el canal **Tradicional**.
- **Sin datos de ventas + CP del cliente no se avanza**: se piden (el resto de fuentes se descarga solo).
- **AltScore = una variable socioeconómica más** (junto al NSE AMAI de INEGI), unida **solo por ubicación**: la exportación del 2026-09-30
  (`geohex_geodig.parquet`) trae `location.lat/lng` → cada PDV (04) o clúster NSE (06) toma la media de los puntos AltScore de su buffer de
  300 m; si una exportación solo trajera `hexIdx`, la rama hexIdx del 04 proyecta cada celda. El `pos_id` de AltScore no cruza con el CP y
  **no se infiere el cruce**. **AltScore MUEVE EL NSE** del clúster (usuario, 2026-09-30: "recuerda altscore si mueve NSE"): su índice pasa a
  la escala de N por cuantiles y N* = (1 − λ)·INEGI + λ·AltScore con `ALTSCORE_PESO_NSE` = λ = 0.25 (a validar), solo con ≥
  `ALTSCORE_MIN_PUNTOS` = 5 puntos con índice en el buffer.
- Presentación con estilo Kin y estructura de pitch ejecutivo (BLUF, titulares de acción, ejemplos con tiendas reales, notas de orador).
- Cadenas: Six = Tradicional; Modelorama y farmacias de cadena = Moderno (`src/cadenas.py`).
- **Rappi: el proyecto es sueros e hidratación.** Solo la ciudad activa; si una línea viene con otros productos, lo que importa es que
  tenga **sueros o sus derivados** (regla "sueros primero", `rappi.clasificar`): sueros = "Hidratantes Líquidos", derivados = "Isotónicos
  Líquidos"; lo genérico o "No disponible" se asigna por marca o nombre; sale solo lo que no es suero (Vitamin Water, refrescos).
- **Letras (06), reglas del usuario del 2026-09-30:** **solo canal Tradicional y solo datos del CP** para el PDV ("elimina todo lo de
  moderno y usa solo datos de cp": sin PDV, Excel, filtro ni textos Moderno; nada del archivo de ventas, ni la comparación con el 05).
  **Letra 1 = NSE del clúster NSE:** hexágono H3 res 9 (`NSE_CLUSTER_RES`; "mejor hexágonos que centroides de AGEB, más simple en
  geografías complejas"); su centro es el punto NSE y el buffer de 300 m desde el centro da los hogares; **todos los PDV del hexágono
  comparten su NSE** ("Solo la Letra 1 del clúster"); AltScore lo mueve (ver AltScore); índice 100 por subcanal del CP. **Letra 2** (del
  PDV, regla del usuario del 2026-09-30): **tabla intermedia con el vector** `pos_id, venta media, CP, Rappi`, con **Rappi = suma de los pedidos/mes
  de sueros e isotónicos de las tiendas Rappi del buffer de 300 m del PDV ÷ número de tiendas** (todas las tiendas físicas; 0 si no hay;
  **pedidos, no pesos**: usuario, 2026-10-01). En las presentaciones **no se usa el signo $** (usuario, 2026-10-01). Cada variable
  pasa a su **pct_rank descendente** entre los PDV Tradicional **con venta** (0 = el que más vende; empates con rango medio) y el **score**
  = media ponderada con **pesos venta 2 · CP 2 · Rappi 1** (`LETRA2_PESOS`); **H si score < 0.4** (`LETRA2_CORTE`), si no L. **El PDV
  sin venta es L** y no entra al ranking. Ya no hay media del buffer, ni "solo en su buffer → L", ni venta Rappi movida, ni botellas por
  caja (los rangos quitan las unidades; `RAPPI_BOTELLAS_CAJA` se eliminó). **"La venta es la media"** (usuario): en los entregables se dice
  "media", no "promedio". Fórmulas en `src/letras.py`. **QA con mapa en cada paso** (estático en el notebook + HTML interactivo; el radio
  azul del clúster NSE ya no se dibuja en el mapa: "no aporta"). Pendiente: λ de AltScore, si entran solo tiendas Rappi activas, cómo
  tratar el empate de "sin Rappi" y si el 05 usa estas letras.
- **Clústeres (usuario, 2026-09-30):** el punto NSE es un clúster y su radio es un buffer; hoy hay dos: el **clúster NSE** (hexágono H3
  res 9 + buffer de 300 m desde su centro; da la Letra 1 a todos sus PDV) y el **buffer de 300 m de cada PDV** (de ahí sale su Rappi
  para la Letra 2). **HH/HL/LH/LL no se llaman "clúster"** en el 06 (son letras) y **conservan su acción Golden Stores** (no quitarla).
- **Share y prioridad: omitidos por ahora** (usuario, 2026-09-30). Su tabla: Prioridad = Letra 1 × Share (la Letra 2 no la cambia):
  P1 = NSE alto + share bajo (la prioridad) · P2 = NSE alto + share alto · P3 = NSE bajo + share bajo · P4 = NSE bajo + share alto.
  El share aún no se calcula: no inventar fuente ni corte; se agrega cuando el usuario lo pida.
- **Entregable de letras (formato del usuario, 2026-09-30):** un solo Excel del canal Tradicional: `pos_id | AltScore (índice + señales)
  | datos gubernamentales (INEGI) | ventas (venta media, CP, Rappi del buffer, rangos y score) | clúster NSE | letra 1 |
  letra 2` (+ Letra 1 sin y con AltScore, Letra 2 sin y con Rappi con "… cambia la letra", letras base y finales, % bajo / medio / alto y
  la acción Golden Stores), con una **3.ª fila de encabezado con la fuente** de cada columna y hojas Fuentes, Fórmulas, Clústeres NSE y
  sensibilidades; lo mismo en su presentación (estilo Kin, pitch; láminas de clústeres y de AltScore con ejemplos reales). Ambos en `cliente/`.
- **Al cambiar reglas se actualiza todo** (usuario, 2026-09-30): el flujograma (`docs/flujo_pipeline.*`, skill archify), los entregables
  de `cliente/`, el mapa HTML de QA y se corre el flujo completo de Bepensa.
- Carpetas: `data/processed/<ciudad>/<bottler>/` y `outputs/<ciudad>/<bottler>/`; **el Excel final y la presentación van en `cliente/`**.
- Mapas: fondo **libre sin API key**: OpenFreeMap (datos OSM, estilo Positron, MapLibre). NO usar `tile.openstreetmap.org`: bloquea con
  403 al abrir el HTML con doble clic (file://, sin Referer); CARTO ya pide API key. **Filtro por subcanal** en el mapa (ya no hay Moderno). Entorno con **uv**.
  La selección del mapa se dibuja en el MISMO lienzo (`renderer: lienzo`): un 2.º canvas encima tapaba los clics y no dejaba elegir otro
  punto (bug corregido 2026-09-30). Tooltips de AGEB y hexágono y ficha del PDV con **barra bajo / medio / alto** (`distribucion` en la
  capa y `distribucion_popup` en `mapas.mapa_html`; colores `mapas.COLOR_NSE3`). Capas `cl_*` con los hexágonos del clúster NSE
  (`hexagonos={fuente: df}`) y `cluster=` en `mapas.mapa_html`: clic en un hexágono o en un PDV dibuja el hexágono, su centro y los PDV
  que lo comparten (azul; el buffer azul ya no se dibuja: "no aporta", usuario 2026-10-01) y, en un PDV, su buffer de 300 m con los PDV con venta (negro) y las tiendas Rappi que dan su Rappi (rojo). Probado en Chrome sin interfaz
  (sin errores JS; pasos, clic en clúster y en PDV, filtro).
