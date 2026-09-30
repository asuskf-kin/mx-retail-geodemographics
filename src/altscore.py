"""Señales AltScore (enrichedgeodata del cliente): carga, familias de variables e índice socioeconómico.

AltScore calcula sus señales por ubicación (lat/lon de la búsqueda y celdas H3 res 7-9, ver el diccionario de datos
AltScore 21/12/2022). La exportación del 2026-09-30 (`geohex_geodig.parquet`, 786 columnas) trae `location.lat/lng` y
`geoHexData_hexIdx_res7/8/9`: se une a los PDV **por ubicación** (hexágono), nunca por `pos_id` (su `foreignKey` es un UUID
que no cruza con el CP). Los códigos −999999/−999998/−999997 son "sin dato" o error y se vuelven NaN. Sin ubicación en el
archivo (exportación anterior, `part-*.parquet`), solo sirve para el EDA y no se une a nada.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# columnas de ubicación que AltScore entrega cuando la exportación las incluye (diccionario, págs. 2 y 8)
COLS_LAT, COLS_LON = ("location.lat", "lat", "latitude", "latitud"), ("location.lng", "lon", "lng", "longitude", "longitud")
COLS_HEX = ("hexIdx_res8", "hexIdx_res9", "hexIdx_res7")        # res 8 primero: res 9 viene vacío (−999997) en ~38% de las filas
ARCHIVO = "geohex_geodig.parquet"                               # exportación con ubicación (2026-09-30)
CENTINELAS = (-999999, -999998, -999997)                        # AltScore: sin dato o error → NaN
IDIOMAS = ["ar", "da", "de", "en", "es", "fr", "it", "other", "pt", "ru", "zh"]

# proxies de nivel socioeconómico de la exportación anterior (península): adopción de iOS y macOS, interés en viajes y
# contenido en idiomas distintos al español (α de Cronbach 0.70 en la península). Dentro de la ZM viajes e idiomas no forman
# escala (marcan ciudades turísticas, no el NSE de los residentes): el 00b elige los proxies de la ZM con `seleccionar_proxies`
# (análisis de ítems sobre los candidatos a priori, sin mirar la venta ni INEGI). Nunca se ajustan a la venta.
PROXIES_NSE = ["geoDigTrack_os_iosPct", "geoDigTrack_os_macOsPct", "geoDigTrack_cat1_travelPct", "not_sp_pt_lang_Pct"]
CANDIDATOS_NSE = PROXIES_NSE + ["geoDigTrack_device_personalComputerPct", "geoDigTrack_cat1_financePct",
                                "geoHexData_idx_techAndConnectivity_v1_adm2"]       # los 7 de partida (a priori)


def archivos(carpeta: Path) -> list:
    """Archivos de la exportación: `geohex_geodig.parquet` si está (la vigente); si no, el dataset Spark part-*.parquet."""
    carpeta = Path(carpeta)
    return [carpeta / ARCHIVO] if (carpeta / ARCHIVO).exists() else sorted(carpeta.glob("part-*.parquet"))


def cargar(carpeta: Path) -> pd.DataFrame:
    """Lee la exportación como una sola tabla con `pos_id` (= foreignKey), centinelas → NaN y los agregados de idioma
    de la exportación anterior (% español, % portugués y % de los demás idiomas). `attrs['centinelas']` = celdas limpiadas."""
    fs = archivos(carpeta)
    if not fs:
        raise FileNotFoundError(f"No hay exportación AltScore en {carpeta}: pedir enrichedgeodata a AltScore")
    d = pd.concat([pd.read_parquet(p) for p in fs], ignore_index=True)
    if "pos_id" not in d.columns and "foreignKey" in d.columns:
        d = d.rename(columns={"foreignKey": "pos_id"})
    num = d.select_dtypes("number").columns
    es_c = d[num].isin(CENTINELAS)
    n_cent = int(es_c.to_numpy().sum())
    d[num] = d[num].mask(es_c)
    for c in [c for c in d.columns if "hexIdx" in c]:                   # hexágono vacío viene como texto "-999997"
        d[c] = d[c].where(~d[c].astype(str).str.startswith("-"))
    pct = {k: f"geoDigTrack_lang_{k}Pct" for k in IDIOMAS}
    if all(c in d.columns for c in pct.values()) and "sp_lang_Pct" not in d.columns:
        otros = d[[pct[k] for k in IDIOMAS if k not in ("es", "pt")]].sum(axis=1, min_count=len(IDIOMAS) - 2)
        d = pd.concat([d, pd.DataFrame({"sp_lang_Pct": d[pct["es"]], "pt_lang_Pct": d[pct["pt"]], "not_sp_pt_lang_Pct": otros})], axis=1)
    d.attrs["centinelas"] = n_cent
    return d


def senales(d: pd.DataFrame) -> list:
    """Señales del EDA: % digitales (web, dispositivo, SO, sus razones y los 3 agregados de idioma), métricas OSM del hexágono
    en res 8 y res 9 (conteos, áreas y alturas), índices de costo de vida y conectividad del municipio (adm2) y visitas si
    vienen. Quedan fuera: ubicación y control de calidad, res 7 (≈ 5 km², mucho más grande que el área de 300 m), las
    reescalas *PctOfMax (son el mismo conteo dividido entre un máximo), los índices adm0/adm1 (constantes en la ZM), los
    conteos digitales crudos (miden volumen de tráfico, no perfil) y el % por idioma (entra con los 3 agregados)."""
    fuera = ("hexIdx", "sourceVersion", "errorPct", "emptyPct", "isSuccess", "PctOfMax", "_adm0", "_adm1", "res7")
    out = []
    for c in d.columns:
        if c in ("pos_id", "requestId", "dateToAnalyze") or c.startswith("location.") or c.endswith(("_lat", "_lon")):
            continue
        if any(f in c for f in fuera) or not pd.api.types.is_numeric_dtype(d[c]):
            continue
        if c.startswith("geoDigTrack_"):
            if c.startswith("geoDigTrack_lang_") or not (c.endswith("Pct") or c.endswith("Ratio")):
                continue
        elif c.startswith("geoHexData_"):
            if "_idx_" not in c and "_res8" not in c and "_res9" not in c:
                continue
        elif not (c.endswith("lang_Pct") or "visit" in c):
            continue
        out.append(c)
    return out


def familia(col: str) -> str:
    """Familia de la señal según su prefijo (AltScore: Geo Digital Track, Geo Hex Data y visitas)."""
    if "visit" in col:
        return "visitas"
    if col.startswith("geoDigTrack_") or "lang_" in col:
        return "digital"
    if "_idx_" in col:
        return "contexto"
    if col.startswith("geoHexData_"):
        return "entorno"
    return "otra"


def ubicacion(df: pd.DataFrame) -> dict:
    """Columnas de ubicación presentes: {'lat': ..., 'lon': ..., 'hex': ...} (None si no vienen). El hexágono se busca por
    terminación (la exportación nueva lo llama geoHexData_hexIdx_res8)."""
    buscar = lambda nombres: next((c for n in nombres for c in df.columns if c.lower() == n.lower()), None)
    hexs = [next((c for c in df.columns if c.endswith(h)), None) for h in COLS_HEX]
    return {"lat": buscar(COLS_LAT), "lon": buscar(COLS_LON), "hex": next((h for h in hexs if h), None)}


def seleccionar_proxies(base: pd.DataFrame, candidatos=None, minimo: float = 0.2):
    """Análisis de ítems iterativo: parte de los candidatos a priori (con > 5 valores distintos) y quita el de menor
    correlación ítem-resto hasta que todos tengan ≥ `minimo` o queden 2. Devuelve (proxies, traza por paso). No mira la
    venta ni INEGI: la validación externa es aparte."""
    act = [c for c in (candidatos or CANDIDATOS_NSE) if c in base.columns and base[c].nunique() > 5]
    traza = []
    while True:
        Z = np.column_stack([rango_normal(base[c]) for c in act])
        Z = Z[~np.isnan(Z).any(axis=1)]
        tot = Z.sum(axis=1)
        ir = pd.Series([stats.spearmanr(Z[:, k], tot - Z[:, k])[0] for k in range(len(act))], index=act)
        traza.append({"paso": len(traza) + 1, "ítems": len(act), "α de Cronbach": alfa_cronbach(Z),
                      "sale": ir.idxmin() if ir.min() < minimo and len(act) > 2 else "—",
                      **{corto(c): v for c, v in ir.items()}})
        if ir.min() >= minimo or len(act) <= 2:
            return act, pd.DataFrame(traza)
        act.remove(ir.idxmin())


def rango_normal(x) -> np.ndarray:
    """Transformación a normal por rangos (Blom): robusta a colas pesadas y a la escala de cada señal. NaN se conserva."""
    x = np.asarray(x, float)
    out = np.full(x.shape, np.nan)
    ok = ~np.isnan(x)
    out[ok] = stats.norm.ppf((stats.rankdata(x[ok]) - 0.375) / (ok.sum() + 0.25))
    return out


def indice_nse(df: pd.DataFrame, cols=PROXIES_NSE, ajuste: pd.DataFrame | None = None):
    """Índice socioeconómico AltScore = 1.er componente principal de los proxies (normalizados por rangos).

    Se ajusta sobre `ajuste` (por defecto `df`; conviene pasar los contextos únicos para no dar más peso a las zonas
    con más PDV) y se aplica a `df`. Signo orientado para que suba con la adopción de iOS. Devuelve
    (índice 0-100 = percentil dentro de `df`, cargas, varianza explicada por el componente). NaN si falta algún proxy.
    """
    ajuste = df if ajuste is None else ajuste
    Z_aj = np.column_stack([rango_normal(ajuste[c]) for c in cols])
    Z_aj = Z_aj[~np.isnan(Z_aj).any(axis=1)]
    val, vec = np.linalg.eigh(np.corrcoef(Z_aj, rowvar=False))
    ref = cols.index("geoDigTrack_os_iosPct") if "geoDigTrack_os_iosPct" in cols else 0      # signo: sube con iOS
    w = vec[:, -1] * np.sign(vec[ref, -1])
    # aplicar con los rangos de `ajuste` (mismo mapeo x -> z para cualquier fila)
    Z = np.column_stack([_z_con_referencia(df[c], ajuste[c]) for c in cols])
    puntaje = Z @ w
    ok = ~np.isnan(puntaje)
    indice = np.full(len(df), np.nan)
    indice[ok] = stats.rankdata(puntaje[ok]) / ok.sum() * 100
    return pd.Series(indice, index=df.index), pd.Series(w, index=cols), val[-1] / val.sum()


def _z_con_referencia(x, ref) -> np.ndarray:
    """z por rangos de `x` usando la distribución de `ref` (percentil empírico -> normal)."""
    r = np.sort(np.asarray(ref, float)[~np.isnan(np.asarray(ref, float))])
    x = np.asarray(x, float)
    p = (np.searchsorted(r, x, side="left") + np.searchsorted(r, x, side="right")) / 2 / len(r)
    z = stats.norm.ppf(np.clip(p, 0.5 / len(r), 1 - 0.5 / len(r)))
    z[np.isnan(x)] = np.nan
    return z


def alfa_cronbach(Z: np.ndarray) -> float:
    """Consistencia interna de un conjunto de indicadores estandarizados (filas completas)."""
    Z = Z[~np.isnan(Z).any(axis=1)]
    k = Z.shape[1]
    return k / (k - 1) * (1 - Z.var(axis=0, ddof=1).sum() / Z.sum(axis=1).var(ddof=1))


# partes que completan una composición (suman 1 o 100) y razones derivadas de dos % que ya están: no aportan información
COMPLEMENTOS = ["geoDigTrack_os_androidPct", "geoDigTrack_device_smartphonePct", "sp_lang_Pct", "geoDigTrack_cat1_otherPct",
                "visit_index_night"]
DERIVADAS = ["geoDigTrack_os_iosAndroidRatio", "geoDigTrack_os_macOsWindowsRatio"]


def corto(col: str) -> str:
    """Nombre corto legible de una señal (para tablas y gráficos)."""
    for a, b in [("geoHexData_", ""), ("geoDigTrack_", ""), ("_v1_adm2", ""), ("idx_", "índice "), ("_count_", " "), ("_count", " edificios"),
                 ("cat1_", "web "), ("res8", "r8"), ("res9", "r9"), ("Pct", " %"), ("_", " ")]:
        col = col.replace(a, b)
    return col.strip()
