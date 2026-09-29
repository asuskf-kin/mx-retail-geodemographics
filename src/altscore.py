"""Señales AltScore (enrichedgeodata del cliente): carga, familias de variables e índice socioeconómico.

AltScore calcula sus señales por ubicación (lat/lon de la búsqueda y celdas H3 res 7-9, ver el diccionario de datos
AltScore 21/12/2022). La exportación puede venir sin esas columnas: entonces solo sirve para el EDA y no se une a nada.
Nunca se infiere el cruce con el Customer Potential: sin coordenadas o hexágono en el archivo, no hay unión.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# columnas de ubicación que AltScore entrega cuando la exportación las incluye (diccionario, págs. 2 y 8)
COLS_LAT, COLS_LON = ("lat", "latitude", "latitud"), ("lon", "lng", "longitude", "longitud")
COLS_HEX = ("hexIdx_res9", "hexIdx_res8", "hexIdx_res7")

# proxies de nivel socioeconómico: adopción de iOS y macOS, interés en viajes y contenido en idiomas distintos al español.
# Se eligieron por análisis de ítems en el notebook 00b (alfa de Cronbach 0.70, correlación ítem-resto > 0.4) y coinciden
# con el 1.er componente sin supervisión de todo el bloque digital; nunca se ajustan a la venta. Quedaron fuera por
# cargar en contra o no correlacionar: % PC, finanzas y conectividad del hexágono (esta se reporta aparte).
PROXIES_NSE = ["geoDigTrack_os_iosPct", "geoDigTrack_os_macOsPct", "geoDigTrack_cat1_travelPct", "not_sp_pt_lang_Pct"]
CANDIDATOS_NSE = PROXIES_NSE + ["geoDigTrack_device_personalComputerPct", "geoDigTrack_cat1_financePct",
                                "geoHexData_idx_techAndConnectivity_v1_adm2"]       # los 7 de partida (a priori)


def cargar(carpeta: Path) -> pd.DataFrame:
    """Lee el dataset Spark (part-*.parquet) de `carpeta` como una sola tabla."""
    partes = sorted(Path(carpeta).glob("part-*.parquet"))
    if not partes:
        raise FileNotFoundError(f"No hay part-*.parquet en {carpeta}: pedir la exportación enrichedgeodata a AltScore")
    return pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)


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
    """Columnas de ubicación presentes: {'lat': ..., 'lon': ..., 'hex': ...} (None si no vienen)."""
    buscar = lambda nombres: next((c for c in df.columns if c.lower() in {n.lower() for n in nombres}), None)
    return {"lat": buscar(COLS_LAT), "lon": buscar(COLS_LON), "hex": next((c for c in COLS_HEX if c in df.columns), None)}


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
    w = vec[:, -1] * np.sign(vec[cols.index("geoDigTrack_os_iosPct"), -1])
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
