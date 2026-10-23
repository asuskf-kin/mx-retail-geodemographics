"""Código postal (zipcode) de cada PDV desde el DENUE de INEGI (campo cod_postal de cada establecimiento).

El CP del cliente no trae código postal y no hay polígonos oficiales de código postal: cada PDV toma el `cod_postal` del
establecimiento DENUE más cercano de la ZM (BallTree haversine). Validación leave-one-out en el propio DENUE: a cada establecimiento
se le predice su código con su vecino más cercano (sin él mismo); en la ZM Guadalajara acierta 91% (con 5 vecinos 90%, con 10 88%).
Sin establecimiento DENUE a ≤ RADIO_MAX_M → texto con el motivo (ninguna celda vacía).
"""
import zipfile

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

import config as C
import requests

from descargas import HEADERS, descargar_fuente

RADIO_MAX_M = 500
SIN_CP = f"sin código postal (sin DENUE a {RADIO_MAX_M} m)"
_R_TIERRA = 6_371_000


def denue_zm() -> pd.DataFrame:
    """Establecimientos DENUE de la ZM con código postal válido (5 dígitos) y coordenadas."""
    descargar_fuente(C.FUENTES["denue"])
    with zipfile.ZipFile(C.ARCHIVOS["denue"]) as z:
        f = next(n for n in z.namelist() if n.startswith("conjunto_de_datos") and n.endswith(".csv"))
        d = pd.read_csv(z.open(f), dtype=str, encoding="latin-1", usecols=["cod_postal", "cve_mun", "latitud", "longitud"])
    d = d[d.cve_mun.isin(C.ZM_MUNICIPIOS)].copy()
    d["lat"], d["lon"] = pd.to_numeric(d.latitud, errors="coerce"), pd.to_numeric(d.longitud, errors="coerce")
    d["cp"] = d.cod_postal.fillna("").str.strip().str.zfill(5)
    ok = d.cp.str.fullmatch(r"\d{5}") & d.cp.ne("00000") & d.lat.notna() & d.lon.notna()
    return d.loc[ok, ["cp", "lat", "lon"]].reset_index(drop=True)


_URL_DENUE = "https://www.inegi.org.mx/contenidos/masiva/denue"


def _es_zip(url: str) -> bool:
    """INEGI responde HTML (no error) cuando el archivo no existe: se pide el primer byte y se mira el tipo."""
    try:
        r = requests.get(url, headers={**HEADERS, "Range": "bytes=0-3"}, timeout=60)
        return r.status_code in (200, 206) and "zip" in r.headers.get("content-type", "")
    except requests.RequestException:
        return False


def _archivos_denue(ent: str) -> list:
    """denue_<ent>_csv.zip o, si INEGI lo parte (estados grandes), denue_<ent>_1_csv.zip, denue_<ent>_2_csv.zip, …"""
    carpeta = C.BASE / "data" / "raw" / "denue_estados" / "INEGI" / f"denue_{ent}"
    if (carpeta / f"denue_{ent}_csv.zip").exists() or _es_zip(f"{_URL_DENUE}/denue_{ent}_csv.zip"):
        return [f"denue_{ent}_csv.zip"]
    partes, k = [], 1
    while (carpeta / f"denue_{ent}_{k}_csv.zip").exists() or _es_zip(f"{_URL_DENUE}/denue_{ent}_{k}_csv.zip"):
        partes.append(f"denue_{ent}_{k}_csv.zip"); k += 1
    if not partes:
        raise RuntimeError(f"INEGI no tiene DENUE masivo para la entidad {ent} (ni partido en _1, _2, …)")
    return partes


def denue_estados(entidades) -> pd.DataFrame:
    """Establecimientos DENUE con código postal válido de una o varias entidades (clave INEGI de 2 dígitos, p. ej. ["09", "15"]),
    para entregables sueltos de una ciudad que no está en config (version_ko.py --archivos ... --estados 09,15). Cada zip se baja una
    vez a data/raw/denue_estados/INEGI/denue_<ent>/ con su descarga.json (procedencia)."""
    partes = []
    for ent in entidades:
        ent = str(ent).zfill(2)
        for nombre in _archivos_denue(ent):          # estados grandes (p. ej. Edomex) vienen partidos: denue_15_1, denue_15_2
            f = {**C.FUENTES["denue"], "cobertura": f"entidad {ent}", "url": f"{_URL_DENUE}/{nombre}",
                 "archivo": C.BASE / "data" / "raw" / "denue_estados" / "INEGI" / f"denue_{ent}" / nombre}
            descargar_fuente(f)
            with zipfile.ZipFile(f["archivo"]) as z:
                for n in [n for n in z.namelist() if n.startswith("conjunto_de_datos") and n.endswith(".csv")]:
                    partes.append(pd.read_csv(z.open(n), dtype=str, encoding="latin-1", usecols=["cod_postal", "latitud", "longitud"]))
    d = pd.concat(partes, ignore_index=True)
    d["lat"], d["lon"] = pd.to_numeric(d.latitud, errors="coerce"), pd.to_numeric(d.longitud, errors="coerce")
    d["cp"] = d.cod_postal.fillna("").str.strip().str.zfill(5)
    ok = d.cp.str.fullmatch(r"\d{5}") & d.cp.ne("00000") & d.lat.notna() & d.lon.notna()
    return d.loc[ok, ["cp", "lat", "lon"]].reset_index(drop=True)


def asignar(lat, lon, denue: pd.DataFrame | None = None) -> pd.DataFrame:
    """Código postal del establecimiento DENUE más cercano a cada (lat, lon) y su distancia en metros."""
    denue = denue_zm() if denue is None else denue
    arbol = BallTree(np.radians(denue[["lat", "lon"]].to_numpy()), metric="haversine")
    pts = pd.DataFrame({"lat": pd.to_numeric(pd.Series(lat), errors="coerce").to_numpy(),
                        "lon": pd.to_numeric(pd.Series(lon), errors="coerce").to_numpy()})
    out = pd.DataFrame({"codigo_postal": SIN_CP, "dist_m": np.nan}, index=pts.index)
    ok = pts.notna().all(axis=1).to_numpy()
    if ok.any():
        dist, ind = arbol.query(np.radians(pts.loc[ok, ["lat", "lon"]].to_numpy()), k=1)
        dist_m = dist[:, 0] * _R_TIERRA
        cps = np.where(dist_m <= RADIO_MAX_M, denue.cp.to_numpy()[ind[:, 0]], SIN_CP)
        out.loc[ok, "codigo_postal"], out.loc[ok, "dist_m"] = cps, dist_m.round(0)
    return out


def acierto_loo(denue: pd.DataFrame, n: int = 20_000, semilla: int = 0) -> float:
    """% de establecimientos DENUE cuyo código coincide con el de su vecino más cercano (sin él mismo)."""
    X = np.radians(denue[["lat", "lon"]].to_numpy())
    idx = np.random.default_rng(semilla).choice(len(denue), min(n, len(denue)), replace=False)
    _, ind = BallTree(X, metric="haversine").query(X[idx], k=2)
    return float(np.mean(denue.cp.to_numpy()[ind[:, 1]] == denue.cp.to_numpy()[idx]))
