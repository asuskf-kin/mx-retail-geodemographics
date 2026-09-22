# Proyecto: perfil socioeconómico de hogares × tiendas (ZM Mérida)

Pipeline reproducible con fuentes oficiales (INEGI y AMAI). Produce, **por AGEB** y **por tienda**,
la distribución de hogares por tamaño, edad del menor, edad del jefe y NSE AMAI 2022, con HHs, % e Índice.
Separa los canales **Moderno** (cadenas) y **Tradicional** (abarrotes e independientes).

Para replicarlo en otra ciudad usa la skill `/nse-tiendas-mx` (en `.claude/skills/nse-tiendas-mx/`).

## Estructura
```
src/config.py        ← ÚNICO lugar a editar para otra ciudad (ENT, ABREV_MICRO, MG_SLUG, ZM_MUNICIPIOS, región Nielsen, ENIGH_ESTADOS)
src/descargas.py     descarga con reanudación HTTP Range (INEGI corta conexiones: ChunkedEncodingError)
src/nse.py           regla AMAI 2022 + logit ENIGH 2024 para # baños y # autos
src/microsim.py      IPU vectorizado (todas las AGEB a la vez)
src/py2nb.py         convierte notebooks/_src/*.py (celdas "# %%") → notebooks/*.ipynb
notebooks/_src/*.py  FUENTE de los notebooks: edita aquí, luego regenera el .ipynb
notebooks/01..03     pipeline (correr en orden, cwd = notebooks/)
data/raw             descargas (se regeneran solas) · data/processed intermedios · outputs/ entregables xlsx
```

## Cómo correr
```bash
cd notebooks
python ../src/py2nb.py _src/01_socioeconomico_merida.py 01_socioeconomico_merida.ipynb   # si editaste el .py
python -c "import nbformat;from nbclient import NotebookClient as K;n='01_socioeconomico_merida.ipynb';nb=nbformat.read(n,4);K(nb,timeout=3600,kernel_name='python3',resources={'metadata':{'path':'.'}}).execute();nbformat.write(nb,n)"
```
`jupyter nbconvert` NO está instalado en esta máquina, así que se usa nbclient directo. Tiempos aproximados: 01 ≈ 3 min, 02 ≈ 45 s (incluye Overpass), 03 ≈ 1.5 min.
Si un xlsx de `outputs/` está abierto en Excel, falla la escritura (aparece el archivo lock `~$...`).

## Entorno (probado)
Python 3.14 · pandas 3 · geopandas 1.1 · scikit-learn 1.9 · nbclient · openpyxl · pyarrow · requests · pypdf.
- **pandas 3 usa cadenas Arrow**: `serie.values[:, None]` falla. Usa `.to_numpy(dtype=object)`.
- En Windows se necesita `PYTHONIOENCODING=utf-8` para imprimir acentos desde bash.
- El DENUE viene en **latin-1**. Los CSV del Censo AGEB vienen en **utf-8-sig**.
- Overpass (OSM) **exige el header User-Agent**: sin él la petición falla con HTTPError.

## Resultados de referencia (para detectar regresiones)
- ENIGH: NSE imputado vs real en Yucatán urbano, diferencia ≤ 1.3 pp por nivel.
- ZM Mérida: 635 AGEB urbanas, 354,033 hogares, 11,716 hogares donantes en la muestra.
- ZM Mérida NSE: A/B 14.1 · C+ 16.8 · C 16.0 · C- 15.7 · D+ 13.6 · D/E 23.9 (%).
- Yucatán estatal: A/B 8.4 · D/E 40.9.
- DENUE 05_2026, ZM: 5,887 tiendas. Moderno 815, Tradicional 5,072 (5,053 abarrotes + 19 minisupers independientes).
- Radio 1 km: la mediana es ≈ 3,981 hogares por tienda.

## Decisiones tomadas con el usuario (no revertir sin preguntar)
- El canal Tradicional incluye SCIAN **461110** (abarrotes), además de los independientes 462111/462112.
- Los "Abarrotes Six" (Grupo Modelo) cuentan como **Tradicional** (`CADENAS_TRADICIONALES` en el notebook 02).
- Moderno y Tradicional se entregan en **xlsx separados** (pasos 02 y 03).
- El layout de salida es un encabezado de 2 niveles: `Latitud, Longitud, Región Nielsen, Estado, Municipio, Localidad, Zonas Metropolitanas` y luego, por categoría, `HHs | % | Indice`.
- El índice se calcula contra el total de la ZM (`REFERENCIA_INDICE="zm"`). La alternativa es `"estado"`.
