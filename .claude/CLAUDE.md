# Proyecto: perfil socioeconómico de hogares × tiendas (ZM Mérida)

Pipeline reproducible con fuentes oficiales (INEGI y AMAI). Produce, **por AGEB** y **por tienda**,
la distribución de hogares por tamaño, edad del menor, edad del jefe y NSE (Regla AMAI 2024, mismos puntos que la 2022), con HHs, % e Índice.
Separa los canales **Moderno** (cadenas) y **Tradicional** (abarrotes e independientes).

Para replicarlo en otra ciudad usa la skill `/nse-tiendas-mx` (en `.claude/skills/nse-tiendas-mx/`).

## Estructura
```
src/config.py        ← ÚNICO lugar a editar: un bloque por ciudad en CIUDADES; la activa en CIUDAD (o env var CIUDAD)
src/descargas.py     descarga con reanudación HTTP Range (INEGI corta conexiones: ChunkedEncodingError)
src/nse.py           Regla AMAI 2024 (= puntos 2022) + logit ENIGH 2024 para # baños y # autos
src/microsim.py      IPU vectorizado (todas las AGEB a la vez)
src/eda.py           estadística del notebook 00 (port de la skill retail-math-eda: IC bootstrap, Hill, AIC, KM, δ de Cliff, BH)
src/correr.py        corre los notebooks por ciudad (en paralelo según dependencias) y guarda los ejecutados
src/cadenas.py       cadenas y canal Moderno/Tradicional: única regla para DENUE y PDV del cliente
src/deck_kin.py      estilo Kin para presentaciones (python-pptx) · src/excel_kin.py formato Kin para entregables Excel (04 y 05)
src/py2nb.py         convierte notebooks/_src/*.py (celdas "# %%") → notebooks/*.ipynb
notebooks/_src/*.py  FUENTE de los notebooks: edita aquí, luego regenera el .ipynb
notebooks/01..03     pipeline de hogares y tiendas (correr en orden)
notebooks/00, 04, 05 cliente Bepensa (solo ZM Mérida): 00 valida ventas × CP · 04 perfil por PDV a ≤300 m · 05 Golden Stores (deck + Excel)
.claude/skills       nse-tiendas-mx (otra ciudad) · golden-stores-kin (cliente + deck, con scripts/instalar.py y qa_deck.py) ·
                     executive-pitch-presentation-builder · retail-math-eda · archify
data/raw             descargas compartidas (se regeneran solas) · data/processed/<ciudad>/ intermedios · outputs/<ciudad>/ entregables xlsx
```

## Cómo correr
```bash
python src/correr.py merida guadalajara     # regenera los .ipynb desde _src y corre 01 → 02 → 03 por ciudad
python src/correr.py --pasos 00,01,02,03,04,05 merida   # Bepensa: 00 no depende de nadie; 04 ← 00,01,02; 05 ← 00,04
```
Orden para Bepensa: **00 → 01 → 02 → 03 → 04 → 05** (00 solo usa los datos del cliente y el Marco Geoestadístico, que descarga solo). Los notebooks también se pueden abrir y correr a mano en VS Code/Jupyter
(kernel Python 3.12 o 3.14 con `requirements.txt`): buscan la raíz del repo solos, usan Mérida por defecto y el 04 avisa
qué notebook correr si falta un archivo previo. Todo lo aleatorio usa semilla fija (`eda.SEMILLA`): dos corridas dan lo mismo.
`jupyter nbconvert` NO está instalado en esta máquina: `src/correr.py` usa nbclient directo y corre **en paralelo** lo que sus
dependencias permiten (nivel 1: 00, 01, 02 · nivel 2: 03 ← 01+02, 04 ← 00+01+02; `--secuencial` para depurar). Las descargas y
extracciones tienen candado entre procesos. Tiempos: Mérida con Bepensa ≈ 2 min en paralelo (≈ 2.7 min secuencial; mismas salidas),
Guadalajara ≈ 18 min (lo domina el IPU del 01).

## Qué se guarda (para depurar sin volver a descargar)
- `data/raw/`: zips originales con estado y versión en el nombre (`mg2020_31_…`, `mg2025_31_…`). `descargar()` no re-baja un zip válido.
- `data/processed/<ciudad>/fuentes_usadas_01.csv` y `fuentes_usadas_02.csv`: URL, edición, archivo local, bytes, fecha y SHA-256 de cada fuente usada.
- `data/processed/<ciudad>/fuentes_cliente_<cliente>_00.csv` (y hoja "Datos del cliente" del xlsx del 00): archivo, filas, fecha y SHA-256
  de las **ventas y el CP del cliente** (insumos críticos; están en `data/raw/<cliente>/`, fuera de git: no se suben ni se sustituyen).
- `notebooks/ejecutados/<ciudad>/*.ipynb`: notebooks ejecutados con todas sus salidas. `notebooks/*.ipynb` quedan limpios.
- Las URLs viven solo en `src/config.py` → `FUENTES` (y `MG_VERSION`). Los notebooks 01 y 02 las muestran y verifican con HEAD.
Si un xlsx de `outputs/` está abierto en Excel, falla la escritura (aparece el archivo lock `~$...`).

## Entorno (probado)
Python 3.14 · pandas 3 · geopandas 1.1 · scikit-learn 1.9 · nbclient · openpyxl · pyarrow · requests · pypdf.
- **pandas 3 usa cadenas Arrow**: `serie.values[:, None]` falla. Usa `.to_numpy(dtype=object)`.
- En Windows se necesita `PYTHONIOENCODING=utf-8` para imprimir acentos desde bash.
- El DENUE viene en **latin-1**. Los CSV del Censo AGEB vienen en **utf-8-sig** (Yucatán) o **latin-1** (Jalisco): el notebook 01 prueba ambos.
- Overpass (OSM) **exige el header User-Agent**: sin él la petición falla con HTTPError.

## Resultados de referencia (para detectar regresiones)
Ciudades configuradas: `merida`, `guadalajara`. Fuentes (revisadas 2026-09-25, las más recientes): Censo 2020 (AGEB/manzana, ITER y muestra), Encuesta Intercensal 2025 (municipio; publicada 2026-09-22), ENIGH 2024, Marco Geoestadístico de la Intercensal 2025 (UPC 794551196649, `MG_VERSION="2025eic"`), DENUE 05_2026 (la 11_2026 sale el 2026-11-25), Regla AMAI 2024 (AMAI anunció actualización en 2026 con ENIGH 2024: revisar). Las salidas de Mérida previas a la parametrización por ciudad
están en `outputs/` y `data/processed/` (raíz).

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
  53 PDV sin hogares a ≤ 300 m (con centroides eran 576). Moran I = 0.058 (p = 0.005); 75 asociaciones robustas de 82.
- 05 Tradicional: 5,556 tiendas. HH 786 (14%, 27% de la venta, índice 189) · HL 1,922 · LH 1,138 (47% de la venta) · LL 1,710.
  P1 = 1,554 tiendas (66% de la venta ubicada); HH verde 165. HL no activas 1,070 (56%). Piloto recomendado: HH verde y amarillo (594 tiendas,
  59 zonas H3 r7, MDE 10.3% sin línea base / 6% con línea base). Excluidas sin hogares: 51 tiendas (1% de la venta).

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
- **El CP es potencial futuro: variable de clasificación (clase Very High → Low), no decisiva.** Ojo: la clase mide potencial ABSOLUTO
  (venta actual × brecha): Very High = 0% en la mitad inferior de venta. La brecha relativa (`PotentialEstimatedToCover`) va en el Excel.
- **Los hogares ocupan toda la manzana**: se reparten por área entre hexágonos (no por centroide) y entran las localidades rurales;
  las manzanas del Censo sin polígono se reparten sobre su AGEB. Nada queda fuera del área por usar un punto.
- **QA metodológico del 05 (no quitar):** la brecha HL vs HH es por construcción (no se presenta como oportunidad); en HL se reporta
  actividad (primero reactivar); semáforo con venta y demanda en log; marcas de frontera (±10) y alta reciente; hoja de excluidas;
  piloto sorteado por zonas H3 r7 con MDE y efecto de diseño; se mide piloto vs control, nunca antes vs después.
- **Metodología Golden Stores (NielsenIQ) fija, no se cambia**: clústeres HH/HL/LH/LL con índice 100 por subcanal, Atacar/Bloquear/
  Fortalecer/Mantener, semáforos por desviación estándar, P1 = HH y LH en verde y amarillo. Deck para el canal **Tradicional**.
- **Sin datos de ventas + CP del cliente no se avanza**: se piden (el resto de fuentes se descarga solo).
- Presentación con estilo Kin y estructura de pitch ejecutivo (BLUF, titulares de acción, ejemplos con tiendas reales, notas de orador).
- Cadenas: Six = Tradicional; Modelorama y farmacias de cadena = Moderno (`src/cadenas.py`).
