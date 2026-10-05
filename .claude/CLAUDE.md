# Proyecto: perfil socioeconómico de hogares × tiendas (ZM Mérida)

Pipeline reproducible con fuentes oficiales (INEGI y AMAI). Produce, **por AGEB** y **por tienda**,
la distribución de hogares por tamaño, edad del menor, edad del jefe y NSE (Regla AMAI 2024, mismos puntos que la 2022), con HHs, % e Índice.
Separa los canales **Moderno** (cadenas) y **Tradicional** (abarrotes e independientes) en el DENUE (01-03); las letras del cliente
(05 y 06) son **solo canal Tradicional**.

Para replicarlo en otra ciudad usa la skill `/nse-tiendas-mx` (en `.claude/skills/nse-tiendas-mx/`).

## Para empezar (persona o sesión nueva) — estado al 2026-10-05
**Reglas de trabajo** (pedidas por el usuario; antes vivían solo en la memoria local de una sesión):
1. **Ciudades con cliente (independientes):** ZM Mérida = **Bepensa** y ZM Guadalajara = **Arca** (usuario, 2026-10-05; `config.CLIENTES`).
   Cada ciudad usa solo sus datos y un cambio para una no debe alterar la otra; no correr otras ciudades. (El CP de FEMSA no cubre
   Guadalajara: es Valle de México y Bajío.)
2. **Sin datos del cliente no se avanza:** **CP y AltScore son obligatorios** (`data/raw/<ciudad>/<cliente>/cp/` y `enrichedgeodata/`;
   usuario, 2026-10-05: "altscore también es obligatorio… si no parar el proceso"): `src/correr.py` no corre la ciudad si falta uno.
   El 05 y el 06 usan **solo el CP** (trae la venta media): "ya no ocupamos ventas" (2026-10-01). **Las ventas ya no se usan para nada**
   (usuario, 2026-10-05): todas las ciudades corren `00_cp_validacion` (`ventas=None` en `config.CLIENTES`; el notebook
   `00_ventas_cp_validacion` queda solo como histórico y no se pide el archivo de ventas). Rappi (`data/raw/rappi/`)
   y Whisp (`data/raw/whisp/Whisp.csv`, opcional) tampoco están en git.
3. **Al cambiar una regla se actualiza todo:** notebook `_src` → CLAUDE.md (decisiones y cifras de referencia) → flujograma
   (`docs/flujo_pipeline.dataflow.json`, skill archify: `deliver` + `visual-check`) → entregables de `cliente/` y mapa HTML → flujo completo
   (`uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 <ciudad>`, Mérida ≈ 7 min; Guadalajara ≈ 40 min: lanzarlo
   como proceso aparte con log, las tareas en segundo plano se cortan a los 30 min) → **presentaciones en Claude Design**.
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
   | Arca · ZM Guadalajara | https://claude.ai/artifact/PB7D5xmEtodZcPNCB3zxpd | https://claude.ai/artifact/2QEewJnoTgRVjmTy3R2FCr |
   | FEMSA · CDMX | (crear al terminar la corrida) | (crear al terminar la corrida) |

   **Lineamientos de marca = skill `brand-guidelines-kin`** (usuario, 2026-10-01; instalada en `.claude/skills/brand-guidelines-kin/`,
   export del Kin Design System, que gana si hay conflicto). Los dos decks de Bepensa se rehicieron con ella el 2026-10-01 (portada
   con foto duotono y título amarillo, divisores con panel en punta de hexágono, eyebrow gris, pie logo + `kinanalytics.com`).
   Para crear o rehacer un deck: `.claude/skills/golden-stores-kin/references/claude_design_marca.md` y
   `scripts/marca_claude_design.py` (misma skill). Los colores de dato (HH/HL/LH/LL, semáforos) se conservan para cuadrar con mapas y Excel.
   Se escriben a mano con las cifras de los notebooks ejecutados (no se generan solos): si cambian las cifras, actualizar sus láminas.
   Cifras: `uv run python .claude/skills/golden-stores-kin/scripts/cifras_decks.py <ciudad> <cliente>` (el deck Golden Stores del
   usuario usa las letras del 06 sobre los PDV con venta y el semáforo PotentialQualitative; el perfil del hogar viene del Excel del 05).
   Deck de un bottler nuevo: receta en `golden-stores-kin/references/claude_design_marca.md` ("Deck de un bottler nuevo").
   Figuras: recortar los PNG de `notebooks/ejecutados/merida/06_*.ipynb` y subirlos como asset del artifact.
   **Sección "Mapa" del deck Golden Stores (usuario, 2026-10-02):** después de su lámina "Diccionario de datos" van "Mapa" (su lámina:
   se conservaron su eyebrow y título; se agregó la figura numerada + lista editable), "Ficha de cada tienda" y "Diccionario 1-3 de 3"
   (ids `7fb474c6`, `mapa-ficha`, `mapa-dicc-1..3`). Las figuras salen de `cliente/laminas/figuras/` (`laminas_mapa.py --pos 2720`).
   Regla del usuario al editar decks: **"sin cambiar formato, solo actualiza datos"** y, al agregar láminas, **no tocar las demás**.
5. **Estilo:** sin el signo **$** en presentaciones (Rappi va en pedidos/mes); nunca la frase "Let knowledge in"; URL `kinanalytics.com`
   en minúsculas; en el Excel ninguna celda queda vacía sin motivo ("no aplica · sin venta", "sin NSE (sin hogares a 300 m)", …);
   "la venta es la media" (no "promedio"); no inventar cifras ni fuentes.
6. Commits solo cuando el usuario lo pide.
7. **Bottler o ciudad nuevos (p. ej. "ahora femsa cdmx"):** primero `uv run python .claude/skills/golden-stores-kin/scripts/verificar_datos.py
   <ciudad> <cliente>` y mostrar la tabla: obligatorios (CP, AltScore) que falten → detenerse y pedirlos; opcionales (Rappi,
   Whisp) → decir cuáles vienen (los que vienen van en Excel, mapa y los dos decks). Ciudad sin configurar → `/nse-tiendas-mx`; CDMX:
   la ZM del Valle de México es de 3 estados y `config.CIUDADES` es de uno solo → preguntar el alcance. **Al terminar la corrida se
   crean los dos artifacts** "Golden Stores · Tradicional · <BOTTLER> <Ciudad>" y "Letras por PDV · <BOTTLER> <Ciudad>" y se registran
   abajo. Pasos completos: sección "Bottler o ciudad nuevos" de la skill golden-stores-kin.

**Pendientes de decisión del usuario** (no cambiar sin preguntar):
- Letra 2: el PDV sin Rappi a 300 m (91% en Mérida) empata en el rango medio (0.55) y por eso Rappi baja 198 letras y sube 65;
  cualquier Rappi queda en el 9% de arriba. Opciones: rango neutro o score solo con venta y CP para quien no tiene Rappi.
- AltScore: índice débil (α 0.47, 2 proxies) que mueve 447 Letras 1 con λ = 0.25.
- Tiendas Rappi: hoy entran todas (Mérida 172); el 00c dice que pasan las activas (89). Con solo activas cambian 69 Letras 2.
- Índice del 04/05 vs ZM: la referencia es la ZM 2020 urbana (`nse_ageb`), pero los hogares son 2025 con rurales (A/B ≈ 94, D/E ≈ 107
  para una zona con la mezcla media). Validar Nielsen (1.ª letra en sueros) cuando el usuario comparta esas tiendas.
- Share = **Whisp** (paso 07, 2026-10-05). Corte "alto" = share del hexágono ≥ share de toda el área (índice 100; elegido por el
  usuario entre opciones) y productos = sueros + isotónicos (como su código). Validar si conviene solo sueros.

**Problemas conocidos** (revisión del 2026-10-01; todo lo demás cuadra con las cifras de abajo):  el DENUE vigente queda fijo en la copia
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
notebooks/00, 00b, 00c, 04, 05, 06, 07 cliente de la ciudad (Mérida = Bepensa · Guadalajara = Arca): 00 valida ventas × CP (o
                     00_cp_validacion: solo CP) · 00b EDA AltScore · 00c EDA Rappi (sueros e hidratación) · 04 perfil por PDV a ≤300 m ·
                     05 Golden Stores (deck + Excel) · 07 share Coca-Cola de Whisp por hexágono res 6 (opcional; corre ANTES del 06) ·
                     06 letras del canal Tradicional (Letra 1 = NSE del clúster + AltScore · Letra 2 = venta y CP + Rappi · prioridad)
.claude/skills       nse-tiendas-mx (otra ciudad) · golden-stores-kin (cliente + deck, con scripts/instalar.py, qa_deck.py,
                     marca_claude_design.py, laminas_mapa.py: láminas que explican el mapa y el diccionario, y cifras_decks.py: cifras de los decks) · brand-guidelines-kin (marca Kin: logos, fuentes, colores, template de deck) ·
                     executive-pitch-presentation-builder · retail-math-eda · archify
data/raw/<ciudad>/<cliente>/ cp/, enrichedgeodata/ (AltScore) y fuentes_oficiales/<institución>/<fuente>/ (se
                     regeneran solas): merida/bepensa · guadalajara/arca (ciudad sin cliente: data/raw/<ciudad>/fuentes_oficiales/) ·
                     data/raw/rappi/rappi.csv (Rappi nacional) y data/raw/whisp/Whisp.csv (Whisp, opcional), fuera de git
data/processed/merida/bepensa/   intermedios (misma estructura ciudad → bottler; ciudad sin cliente: data/processed/<ciudad>/)
outputs/merida/bepensa/          Excel de análisis y QA (00-04) y el mapa HTML del 06 (06_mapa_qa_letras_*.html; en pantalla ya no dice "QA")
outputs/merida/bepensa/cliente/  SOLO lo que se entrega al cliente: 05 (deck + Excel Golden Stores) y 06 (Excel de letras completo,
                                 reducido, diccionario y entregable final + su presentación); laminas/ (PNG 1920×1080 que explican el
                                 mapa y el diccionario + figuras/ para Claude Design, de laminas_mapa.py); versiones viejas en anteriores/
docs/flujo_pipeline.*            flujograma del pipeline 00 → 07 (skill archify: .dataflow.json → .html con validate, deliver y
                                 visual-check); el anterior (solo 01-03) en docs/anteriores/. Se actualiza cuando cambia el flujo
qa/                  QA contra la línea base de Nielsen: `qa/_src/qa_linea_base_nielsen.py` (fuente) → `qa/qa_linea_base_nielsen.ipynb`;
                     línea base `qa/Golden Stores Sueros R.Sur - KO FY'23.xlsx` (fuera de git, *.xlsx); salida en `qa/salidas/`
pyproject.toml · uv.lock · .python-version   proyecto uv (Python 3.14, entorno en .venv; requirements.txt queda para pip)
```

## Cómo correr
```bash
uv sync                                      # crea/actualiza .venv con uv.lock (una vez por máquina; uv.lock va en git)
uv run python -m ipykernel install --user --name mx-retail-geodemographics --display-name "Python (mx-retail-geodemographics · uv .venv)"
uv run python src/correr.py merida guadalajara     # regenera los .ipynb desde _src y corre 01 → 02 → 03 por ciudad
uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 merida   # Bepensa completo (≈ 7 min en paralelo)
uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 guadalajara   # Arca (≈ 40 min; proceso aparte con log)
```
Orden por ciudad con cliente: **00 → 00b → 00c → 01 → 02 → 03 → 04 → 05 → 07 → 06** (00, 00b y 00c no dependen de nadie; 04 ← 00,
00b, 01, 02; 05 ← 00, 04; 07 ← 00; 06 ← 00, 00b, 00c, 01, 04, 07). Comando: `uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 <ciudad>`. Los notebooks también se pueden abrir y correr a mano en VS Code/Jupyter con el kernel
**"Python (mx-retail-geodemographics · uv .venv)"** (o el intérprete `.venv`): buscan la raíz del repo solos, usan Mérida por
defecto y avisan qué notebook correr si falta un archivo previo. Todo lo aleatorio usa semilla fija (`eda.SEMILLA`): dos corridas dan lo mismo.
`jupyter nbconvert` NO está instalado en esta máquina: `src/correr.py` usa nbclient directo y corre **en paralelo** lo que sus
dependencias permiten (nivel 1: 00, 00b, 00c, 01, 02 · nivel 2: 03, 04, 07 · nivel 3: 05, 06; `--secuencial` para depurar). Las descargas y
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
- (Histórico, con el archivo de ventas que ya no se usa) Llave: empata 73.3% de los registros de ventas (azar 3.7%); en prefijos de la ZM quedan sin ubicar 30.9% de las cajas (pocas cuentas grandes).
- 7,455 PDV del CP en la ZM, 5,978 con venta. (Histórico, con el archivo de ventas: mediana 2.07 cajas/mes de vida; Gini 0.58; KM S(12 m) = 0.86.)
  Desde 2026-10-05 Mérida corre `00_cp_validacion` (sin ventas): mismas 7,455 PDV, letras, prioridades y clústeres del 05 que con ventas.
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
- 05 Tradicional (solo CP desde 2026-10-01: venta = `PotentialQuantitative_CustomCat_sueros`): 5,556 tiendas. HH 771 (14%, 24% de la
  venta, índice 174) · HL 1,937 · LH 1,109 (42% de la venta) · LL 1,739. P1 = 1,503 tiendas (58% de la venta; 12,500 cajas/mes, +10% =
  1,250); HH verde 154. Venta del canal 21,395 cajas/mes. ρ(hogares, venta) = −0.11. Piloto recomendado: HH verde y amarillo (573 tiendas,
  59 zonas H3 r7, MDE 10% sin línea base / 6% con línea base). Excluidas sin hogares: 51 tiendas (1% de la venta). La versión con el archivo
  de ventas (P1 1,554 · 66% · índice HH 189) quedó en `cliente/anteriores/*_2026-09-30_con_ventas.*`.

### Rappi (notebook 00c, `data/raw/rappi/rappi.csv`, nacional: 864,704 líneas)
- ZM Mérida (polígono): 29,785 líneas; la etiqueta `city` ("Merida"/"Mérida") coincide 100% con el polígono (4 líneas sin coordenadas).
- **Sin BRAND_x (usuario, 2026-10-05: "no tomes en rappi lo que dice BRAND_x"):** el 00c quita al leer las líneas con marca
  anonimizada `BRAND_####` (`config.RAPPI_EXCLUIR_MARCA`): 488,683 de 864,704 líneas nacionales (56.5%; 58% del importe). Son casi todos
  los competidores (solo quedan 121 líneas "No disponible", ninguna en Mérida ni Guadalajara): Rappi queda **solo Coca-Cola** y las
  comparaciones contra competidores del EDA (duplicados, faltantes, precio, canasta, participación) dicen "no aplica".
- Mérida en la ventana: 13,130 líneas; sueros 14% de la venta, isotónicos 86% (Powerade 86% · Flashlyte 14% · Vitamin Water < 1%).
  (Antes, con competidores: 26,876 líneas, Coca-Cola 48% del valor.)
- **Cobertura:** oct-dic 2024 sin cadena ni vertical y sin BRAND_4866 (20% de la venta nacional) → ventana ene-2025 → ago-2026.
  `datetime` dice "Z" pero es hora local (1-6 h: 0.1% vs 25% si fuera UTC). Crecimiento ene-ago 2026 vs 2025: +3.6% (IC95 −6.3% a +15.1%).
- 453 store_id → 172 tiendas físicas (≤ 25 m; con BRAND_x eran 221); 89 activas (≥ 12 pedidos, 92% de la venta), 20 activas en sueros;
  2 Turbo = 41% de la venta. Duplicados exactos Coca-Cola 0.9%: se conservan.
- Guadalajara: 1,544 store_id → 594 tiendas físicas, 259 activas (89% de la venta); sueros 15% · isotónicos 84%; 23 Turbo = 59%.

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
- Letra 2 = score de rangos (usuario, 2026-09-30; corrida del 2026-10-05 con Rappi = hidratación Coca-Cola sin BRAND_x): H en 29.3% de
  los objetivo (sin Rappi 31.7%). Venta del CP (sueros) mediana 2.57 cajas/mes; CP con decimales mediana 0.17, 19% en 0 (redondeado
  quedaba 79%); ρ(venta, CP) = +0.22. Rappi del buffer: 172 tiendas (89 activas), 505 PDV objetivo (9.1%) con alguna a ≤ 300 m; el 91%
  sin Rappi empata en el rango 0.55. Rappi cambia 263 letras (65 ↑, **198 ↓**: el rango medio de "sin Rappi" baja a quien estaba cerca
  del corte). Misma letra: sin CP 80%, CP redondeado 88%, pesos 1·1·1 96%, corte 0.35 / 0.45 94% / 93%, solo tiendas activas 98.8%
  (cambian 69), sin Turbo 100%, empates en el peor rango 90%.
- Letras finales (corrida del 2026-10-05): HH 799 (14% de tiendas, 23% de la venta, índice 160) · HL 1,890 (24%) · LH 830 (25%) · LL 2,047
  (28%); prioridad por letras (Whisp sin datos para Mérida): P1 799 · P2 2,684 · P3 830 · P4 2,671 (53 sin NSE); 88% igual a las letras
  base (solo INEGI + CP). Los 1,418 PDV sin venta con NSE quedan L en la Letra 2. Excel de 16 hojas (con "Vector Letra 2"); deck de 14 láminas;
  tabla intermedia en `data/processed/merida/bepensa/letra2_vector_bepensa_zm_merida.parquet`.

### QA contra Nielsen (qa/, 2026-10-01; línea base = Golden Stores Sueros FY'23, canal Autoservicios, Región Sur)
- Nielsen es **Moderno** (supermercados) y nuestras letras **Tradicional**: no hay comparación tienda a tienda; se compara la **zona**.
  65 autoservicios en la ZM Mérida (HL 33 · LL 17 · HH 12 · LH 3). Su número de hogares no se reproduce con ningún radio ni con la AGEB
  (ρ ≤ 0.14): su área depende del formato. El **perfil NSE** sí: ρ(N) 0.90 a 300 m (0.95 a 1.5 km), error 2.9 pp por nivel. Tamaño,
  niños y edad del jefe se alejan (5 · 11 · 6 pp; categorías definidas distinto).
- Su 1.ª letra es NSE contra una **referencia regional fija** (A/B 10.7% … D/E 30.2%, N = 3.01; reproduce 95% de sus letras), no el
  número de hogares (AUC 0.51). Nuestro NSE del clúster en su coordenada: AUC 0.99; letra igual en 88% (κ 0.74) con corte relativo y
  80% (κ 0.43) con el corte de nuestros PDV Tradicional.
- Geografía (nuestros PDV a ≤ 500 m): Letra 1 75% (κ 0.36), Letra 2 77% (κ 0.25, esperado bajo: otro canal). Rappi de la misma
  cadena a ≤ 200 m anticipa su 2.ª letra: AUC 0.88 [0.63, 1.00] en 39 tiendas.

### Guadalajara (10 municipios Metrópolis 2020, región Pacífico, ENIGH 01·06·14·16·18)
- **Cliente Arca (desde 2026-10-05; CP `cp_arca_mex_sueros_202609.csv` + AltScore, sin archivo de ventas → `00_cp_validacion`).**
  Corrida del 2026-10-05:
  - 05 Tradicional: 24,525 tiendas · HH 3,501 (14%, 24% de la venta, índice 171) · HL 8,468 · LH 5,029 (40% de la venta) · LL 7,527;
    P1 = 6,978 tiendas (58% de la venta; 58,260 cajas/mes). Venta del canal 100,507 cajas/mes. Ojo: el CP de Arca solo marca 50 Moderno
    (los nombres de cadena de `cadenas.py` casi no aparecen).
  - 06: 39,186 PDV Tradicional, 24,548 objetivo; L1 H 48% (AltScore cambia 2,786); L2 H 30.1% (Rappi cambia 1,274: 387 ↑ / 887 ↓);
    letras HH 3,669 · HL 8,102 · LH 3,710 · LL 9,067; 84% igual a las letras base. Rappi: 594 tiendas físicas (259 activas), 3,591 PDV
    objetivo (14.6%) con Rappi a 300 m. Prioridad con Whisp (Letra 1 × share): P1 12,600 · P2 7,230 · P3 9,379 · P4 9,858
    (38,289 por Whisp, 778 por letras sin venta Whisp en su hexágono, 119 sin NSE).
  - 07 Whisp: 54 de 91 hexágonos res 6 con venta; share KO del área 26.7% (isotónicos 52.8% · sueros 3.2%; Pisa 93% de sueros);
    33 hexágonos con share alto.
- Cifras de abajo (INEGI y DENUE) de la corrida con MG 2025 y sin rurales ni Intercensal; el 01-04 de Arca ya corrió con las fuentes
  de 2026-09-25 pero sus cifras de INEGI no se han copiado aquí.
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
- (Histórico) Llave ventas ↔ CP **inferida**: `pos_id` de ventas = prefijo de 4 dígitos (centro de distribución) + `pos_id` del CP a 6 dígitos (pendiente de confirmar con Bepensa).
- Señales del CP: `PotentialQuantitative` y `size_class` son fuga (derivan de la venta); el potencial útil es `PotentialQuantitativeFinal`.
  **En el 06 (usuario, 2026-09-30) la venta SALE DEL CP:** `PotentialQuantitative_TotalPortafolio` es la venta media (ya no se usa el
  archivo de ventas en las letras) y el CP es `PotentialQuantitativeFinal_TotalPortafolio` **con decimales** (usuario, 2026-09-30: "0.6
  cajas son más de 10 unidades"; el redondeo `CP_UMBRAL_REDONDEO` solo queda en el QA). El 06 ya no usa el archivo de ventas en nada, ni para el QA
  (usuario: "usa solo datos de cp"). **El 05 tampoco desde 2026-10-01** (usuario: "ya no ocupamos ventas ahora solo ocupamos CP"): su venta
  es la venta media de sueros del CP (`PotentialQuantitative_{CP_CATEGORIA}`), "con venta" = venta media > 0, clase y brecha de sueros.
- **El CP es potencial futuro: variable de clasificación (clase Very High → Low), no decisiva** en el 05. Ojo: la clase mide potencial
  ABSOLUTO (venta actual × brecha): Very High = 0% en la mitad inferior de venta. La brecha relativa (`PotentialEstimatedToCover`) va en el Excel.
  **Excepción decidida por el usuario (2026-09-30): en la Letra 2 del 06 el potencial (`PotentialQuantitativeFinal`) entra al score con peso 2.**
- **Los hogares ocupan toda la manzana**: se reparten por área entre hexágonos (no por centroide) y entran las localidades rurales;
  las manzanas del Censo sin polígono se reparten sobre su AGEB. Nada queda fuera del área por usar un punto.
- **QA metodológico del 05 (no quitar):** la brecha HL vs HH es por construcción (no se presenta como oportunidad); semáforo con venta
  y demanda en log; marcas de frontera (±10); hoja de excluidas (actividad, alta reciente y "HL no activas" se quitaron el 2026-10-01: el CP
  no trae fechas; decisión del usuario);
  piloto sorteado por zonas H3 r7 con MDE y efecto de diseño; se mide piloto vs control, nunca antes vs después.
- **Metodología Golden Stores (NielsenIQ) fija, no se cambia**: clústeres HH/HL/LH/LL con índice 100 por subcanal, Atacar/Bloquear/
  Fortalecer/Mantener, semáforos por desviación estándar, P1 = HH y LH en verde y amarillo. Deck para el canal **Tradicional**.
- **Sin el CP del cliente no se avanza**: se pide (el resto de fuentes se descarga solo). El 05 y el 06 ya no usan el archivo de ventas.
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
  Líquidos"; lo genérico o "No disponible" se asigna por marca o nombre. **Las líneas con marca `BRAND_x` no se toman** (usuario,
  2026-10-05; competidores anonimizados): el universo Rappi (tiendas físicas, activas, EDA y Rappi de la Letra 2) es solo Coca-Cola. **Vitamin Water entra** (subcategoría "Agua funcional (Vitamin
  Water)", usuario 2026-10-05; antes se excluía); sale solo lo que no es hidratación (refrescos, agua sola).
- **Letras (06), reglas del usuario del 2026-09-30:** **solo canal Tradicional y solo datos del CP** para el PDV ("elimina todo lo de
  moderno y usa solo datos de cp": sin PDV, Excel, filtro ni textos Moderno; nada del archivo de ventas, ni la comparación con el 05).
  **Letra 1 = NSE del clúster NSE:** hexágono H3 res 9 (`NSE_CLUSTER_RES`; "mejor hexágonos que centroides de AGEB, más simple en
  geografías complejas"); su centro es el punto NSE y el buffer de 300 m desde el centro da los hogares; **todos los PDV del hexágono
  comparten su NSE** ("Solo la Letra 1 del clúster"); AltScore lo mueve (ver AltScore); índice 100 por subcanal del CP. **Letra 2** (del
  PDV, regla del usuario del 2026-09-30): **tabla intermedia con el vector** `pos_id, venta media, CP, Rappi`, con **Rappi = suma de los pedidos/mes
  de sueros e isotónicos de las tiendas Rappi del buffer de 300 m del PDV ÷ número de tiendas** (todas las tiendas físicas; 0 si no hay;
  **pedidos, no pesos**: usuario, 2026-10-01). En las presentaciones **no se usa el signo $** (usuario, 2026-10-01).
  **Guiado por el CP (usuario, 2026-10-01):** la categoría del cliente es **sueros** (`CustomCat_sueros`; Nielsen "T. Sueros" vs
  "Electrolit + Suerox"): venta media, potencial y clase salen de las columnas `*_CustomCat_sueros` (`config.CP_CATEGORIA`; antes
  `_TotalPortafolio`, que solo coincide en 81.5% de los PDV) y Rappi cuenta la **hidratación Coca-Cola: Powerade, Flashlyte,
  Glacéau Vitamin Water y Vitamin Water** (usuario, 2026-10-05: "en todos los casos"; `config.RAPPI_MARCAS_L2`, cualquier subcategoría;
  antes solo Flashlyte). Los competidores quedan fuera. Trazabilidad de los
  productos tomados y excluidos: `outputs/merida/bepensa/06_rappi_productos_tomados_bepensa_zm_merida.xlsx`. Cada variable
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
- **Prioridad con Whisp (usuario, 2026-10-05, paso 07):** si Whisp tiene datos para el área, **prioridad = Letra 1 × share de
  Coca-Cola** (H bajo P1 · H alto P2 · L bajo P3 · L alto P4; la Letra 2 no la cambia; `letras.PRIORIDAD_SHARE`). Share = cajas unidad
  `COCA-COLA COMPANY` / total del hexágono H3 res 6 (sueros + isotónicos, `WHISP_VENTANA` 202508–202608); alto si ≥ share del área.
  Sin Whisp para el área (Mérida) o sin ventas en el hexágono del PDV → prioridad por letras (abajo); la columna "Fuente de la
  prioridad" lo dice.
  **Datos opcionales (usuario, 2026-10-05): si vienen, van en todo** — Excel, mapa (paso "4. Prioridad: Letra 1 × share Whisp" con
  la capa `wh_share` de hexágonos res 6 y la capa `pdv_prio` P1–P4; sin Whisp el paso 4 es "Prioridad por letras") y los dos decks
  (Letras: lámina `prioridad`; Golden Stores: lámina `prio-whisp` con la tabla Letra 1 × Letra 2 × share de 8 tiendas reales).
  El 07 guarda `share_area` en su parquet para el texto del mapa. El 07 escribe `whisp_share_<cliente>_<zm>.parquet` y `07_whisp_share_*.xlsx` (hojas Resumen · Share por hexágono con Región,
  SubTerritorio principal y todos, Segmento y share KO por categoría · Fabricantes por Categoría · Categorías × Segmento; usuario, 2026-10-05); el 06 lo lee (Excel completo y
  reducido con share, share alto/bajo y fuente; mapa y deck).
- **Prioridad por letras en el 06 (usuario, 2026-10-02): primero la demanda (Letra 1, NSE) y después la venta (Letra 2):
  HH = P1 · HL = P2 · LH = P3 · LL = P4** (`letras.PRIORIDAD`; sale solo de las letras: el PDV sin venta también la tiene, solo el PDV sin NSE no). Va en el Excel
  (columna Prioridad y hoja Resumen), el mapa HTML y el deck; el Excel del 05 lleva también "Prioridad (letras)" y pone la demanda
  antes que la venta en columnas, textos y láminas (1.ª letra = demanda, 2.ª = venta; HL Bloquear, LH Fortalecer). Reemplaza la tabla anterior Letra 1 × Share. **El share sigue omitido**:
  no inventar fuente ni corte. El P1 del 05 (HH y LH en verde y amarillo, Golden Stores) es otra regla y no cambió.
- **Entregable final (usuario, 2026-10-02):** `cliente/06_entregable_final_letras_bepensa_zm_merida.xlsx`, lo escribe el 06. Una fila por
  PDV Tradicional (7,037) y 9 columnas en este orden: `pos_id, lat, lon, PotentialQuantitative_TotalPortafolio,
  PotentialQuantitativeFinal_TotalPortafolio, PotentialQualitative_TotalPortafolio` (tal cual del CP) + `segmento_golden_store` (letras
  finales), `prioridad` (P1–P4 por letras) y `accion` (Golden Stores). El CP viene vacío en los 1,430 PDV sin venta → "sin dato en el
  CP (PDV sin venta)". Ojo: las letras se calculan con las columnas de sueros (`CP_CATEGORIA`), pero el formato pide las de TotalPortafolio.
- **Excel reducido (usuario, 2026-10-02):** `cliente/06_letras_nse_ventas_tradicional_reducido_bepensa_zm_merida.xlsx` (lo escribe el 06):
  las columnas de la ficha del PDV del mapa HTML (`POPUP["pdv"]`, función `ficha_pdv`) para los 7,037 PDV Tradicional y al final Letras
  base (INEGI + CP) · Letras (final) · Acción Golden Stores · Prioridad (43 columnas con Share KO Whisp, share alto/bajo y fuente de la
  prioridad). **Ninguna celda vacía** en el Excel completo ni en el reducido (2026-10-05): `tabla_pdv` pone el motivo de cada faltante
  ("no aplica · sin venta", "sin NSE (sin hogares a 300 m)", "fuera de AGEB urbana", "sin dato AltScore en el buffer del clúster"…).
- **Mapa HTML con marca Kin (2026-10-02):** `src/mapas.py` toma de la skill brand-guidelines-kin los tokens, las fuentes (base64) y el logo
  IV_19 / favicon S_14 (`_marca()`); panel con encabezado oscuro, pasos numerados con anterior/siguiente y flechas, filtro en chips,
  búsqueda con Enter/Esc, leyenda flotante abajo a la derecha y ficha con chips de letras, prioridad y acción; el PDV elegido lleva
  anillo amarillo. **Sin "QA" en pantalla** (usuario, 2026-10-02): eyebrow "Mapa interactivo", título "Letras por punto de venta · canal
  Tradicional", sección "Pasos" (el archivo conserva el nombre `06_mapa_qa_letras_*.html`). Probado en el navegador (1440×900, sin
  errores JS). Para verlo: `.claude/launch.json` → servidor `mapa-qa` (puerto 8765).
- **Láminas del mapa (2026-10-02):** `uv run python .claude/skills/golden-stores-kin/scripts/laminas_mapa.py [--pos 2720]` captura el
  mapa con Chrome sin interfaz (los números los dibuja el propio mapa; sin fondo de calles porque no hay WebGL) y arma 5 PNG con marca
  Kin en `cliente/laminas/` + `figuras/`: cómo leer el mapa (8 elementos), la ficha del PDV (7 secciones) y el diccionario (3 partes,
  desde `06_diccionario_letras_*.xlsx`). Si cambian columnas o reglas, correr el 06 y luego este script.
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
