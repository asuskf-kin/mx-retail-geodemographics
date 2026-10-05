# %% [markdown]
# # 00 · Customer Potential del cliente (solo CP): validación y PDV de la ZM
#
# Desde 2026-10-01 el 05 y el 06 usan **solo el CP** ("ya no ocupamos ventas, ahora solo ocupamos CP"): la venta de cada tienda es la
# **venta media de la categoría** que trae el CP (`PotentialQuantitative_<cat>`, `config.CP_CATEGORIA`). Este notebook reemplaza al
# 00 de ventas cuando el cliente no entrega archivo de ventas (lo elige `src/correr.py`) y deja la **misma tabla de PDV** que usan el
# 04, el 05 y el 06 (`pdv_<cliente>_<zm>.parquet`).
#
# * **Insumos obligatorios** (sin ellos no se avanza; se piden al cliente): el CP (`data/raw/<ciudad>/<cliente>/cp/`) y AltScore
#   (`enrichedgeodata/geohex_geodig.parquet`). Se registra su huella (filas, fecha, SHA-256).
# * **Coordenadas:** escala perdida, lat/lon invertidas y signo; se quedan las que caen en un municipio del estado (polígono del
#   Marco Geoestadístico; no se confía en `pos_city`).
# * **ZM:** municipios de la delimitación SEDATU-CONAPO-INEGI (`config.ZM_MUNICIPIOS`).
# * **Canal:** `src/cadenas.py` (misma regla que el DENUE) sobre el nombre del PDV.
# * **Venta:** con venta = venta media de la categoría > 0. Las métricas de actividad (meses, recencia) no existen sin ventas: quedan
#   vacías y la venta "de vida" del 04 es la venta media del CP.

# %%
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import numpy as np
import pandas as pd
import geopandas as gpd
from IPython.display import display

import config as C
import cadenas
import eda
from descargas import descargar_fuente, extraer

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"No hay cliente configurado para {C.CIUDAD} (config.CLIENTES)"
pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.3f}".format)
CAT = C.CP_CATEGORIA
print(f"Cliente: {C.CLIENTE_NOMBRE} · {C.ZM_NOMBRE} · categoría del CP: {CAT}")

# --- requisitos: CP y AltScore son OBLIGATORIOS (usuario): si falta uno, se detiene y se pide al cliente ---
ALT = sorted(Path(C.CLIENTE_ALTSCORE).glob("*.parquet")) if Path(C.CLIENTE_ALTSCORE).exists() else []
assert Path(C.CLIENTE_CP).exists(), f"Falta el CP del cliente: {C.CLIENTE_CP}. Pedirlo; no se puede avanzar sin él."
assert ALT, f"Falta AltScore del cliente en {C.CLIENTE_ALTSCORE} (geohex_geodig.parquet). Pedirlo; no se puede avanzar sin él."
FUENTES_CLIENTE = pd.DataFrame([{
    "insumo": "Customer Potential" if Path(f) == Path(C.CLIENTE_CP) else "AltScore", "archivo": Path(f).name,
    "ruta": str(Path(f).relative_to(BASE)), "bytes": Path(f).stat().st_size,
    "modificado": datetime.fromtimestamp(Path(f).stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    "sha256": hashlib.sha256(Path(f).read_bytes()).hexdigest()} for f in [C.CLIENTE_CP, *ALT]])
FUENTES_CLIENTE.to_csv(C.PROC / f"fuentes_cliente_{C.CLIENTE}_00.csv", index=False)
display(FUENTES_CLIENTE)
descargar_fuente(C.FUENTES["mg"])
D_MG = extraer(C.ARCHIVOS["mg"])

# %% [markdown]
# ## 1. Carga e integridad

# %%
cp = pd.read_csv(C.CLIENTE_CP)
FUENTES_CLIENTE.loc[FUENTES_CLIENTE.insumo == "Customer Potential", "filas"] = len(cp)
falt = [f"{p}_{CAT}" for p in ("PotentialQuantitative", "PotentialQuantitativeFinal", "PotentialQualitative", "PotentialEstimatedToCover")
        if f"{p}_{CAT}" not in cp.columns]
assert not falt, f"El CP no trae las columnas de la categoría {CAT}: {falt}"
assert cp.pos_id.is_unique, "pos_id repetido en el CP"
cp[["cadena", "canal"]] = cadenas.clasificar(cp.pos_name)
print(f"CP: {len(cp):,} PDV · {cp.pos_city.nunique():,} ciudades del CP · columnas {len(cp.columns)}")

# %% [markdown]
# ## 2. Coordenadas y filtro a la ZM
#
# Reglas: (1) escala: si |valor| > 1000 se divide hasta quedar con dos dígitos enteros; (2) si |lat| > 80 y |lon| < 30 se
# intercambian; (3) lat positiva, lon negativa (México); (4) el punto debe caer en un municipio del estado.

# %%
def escala(v):
    v = v.astype(float).copy()
    g = v.abs() > 1000
    v[g] = v[g] / 10 ** (np.floor(np.log10(v[g].abs())) - 1)
    return v

lat, lon = escala(cp.pos_latitude), escala(cp.pos_longitude)
inv = (lat.abs() > 80) & (lon.abs() < 30)
lat, lon = lat.where(~inv, lon), lon.where(~inv, lat)
lat, lon = lat.abs(), -lon.abs()
cambio = ~(np.isclose(lat, cp.pos_latitude) & np.isclose(lon, cp.pos_longitude))
mun = gpd.read_file(next(D_MG.rglob(f"{C.ENT}mun.shp")))[["CVE_MUN", "NOMGEO", "geometry"]]
pts = gpd.GeoDataFrame(cp[["pos_id"]], geometry=gpd.points_from_xy(lon, lat), crs=4326).to_crs(mun.crs)
j = gpd.sjoin(pts, mun, how="left", predicate="within")
j = j[~j.index.duplicated()]
cp["cve_mun"], cp["municipio_mg"] = j.CVE_MUN.reindex(cp.index), j.NOMGEO.reindex(cp.index)
en_estado = cp.cve_mun.notna()
cp["lat"], cp["lon"] = lat.where(en_estado), lon.where(en_estado)
cp["coord_estado"] = np.select([en_estado & ~cambio, en_estado], ["original", "corregida"], f"fuera de {C.NOM_ENT}")
cp["en_zm"] = cp.cve_mun.isin(C.ZM_MUNICIPIOS)
coords = cp.coord_estado.value_counts().to_frame("PDV")
display(coords)
cp = cp[cp.en_zm].copy()                                # desde aquí, universo = CP de la ZM
print(f"PDV del CP en {C.ZM_NOMBRE}: {len(cp):,} (municipios: {', '.join(C.ZM_MUNICIPIOS.values())})")
dup = cp.duplicated(["lat", "lon"], keep=False)
print(f"PDV de la ZM con coordenadas idénticas a otro PDV: {dup.sum():,} (dobles registros o geocodificación por calle)")

# %% [markdown]
# ## 3. Venta y potencial de la categoría (CP)

# %%
V = cp[f"PotentialQuantitative_{CAT}"]
cp["con_venta"] = V.gt(0)
por_mun = cp.groupby("municipio_mg").agg(PDV=("pos_id", "size"), con_venta=("con_venta", "sum"), venta=(f"PotentialQuantitative_{CAT}", "sum"))
por_mun["% con venta"] = por_mun.con_venta / por_mun.PDV * 100
por_sub = cp.groupby(["canal", "pos_subchannel"]).agg(PDV=("pos_id", "size"), con_venta=("con_venta", "sum"),
                                                     venta_media=(f"PotentialQuantitative_{CAT}", "median")).sort_values("PDV", ascending=False)
clase = pd.crosstab(cp.canal, cp[f"PotentialQualitative_{CAT}"].fillna("sin venta"))
vacios = cp.loc[~cp.con_venta, [f"PotentialQuantitativeFinal_{CAT}", f"PotentialQualitative_{CAT}"]].isna().mean() * 100
display(por_mun.round(1)); display(por_sub.head(20).round(2)); display(clase)
x = V[V > 0]
uni = pd.DataFrame({"PDV con venta": [len(x)], "mediana cajas/mes": [x.median()], "p90": [x.quantile(.9)], "media": [x.mean()],
                    "Gini": [eda.gini(x.to_numpy()) if hasattr(eda, "gini") else np.nan]}).round(3)
display(uni)

# %% [markdown]
# ## 4. Hallazgos y tabla de PDV para el 04, el 05 y el 06

# %%
hallazgos = pd.DataFrame([
    ("Datos del cliente", f"CP {Path(C.CLIENTE_CP).name}: {int(FUENTES_CLIENTE.filas.iloc[0]):,} PDV; AltScore: {', '.join(p.name for p in ALT)}. "
                          "Sin archivo de ventas: la venta es la venta media del CP.", "Huella en la hoja Datos del cliente."),
    ("Coordenadas", " · ".join(f"{k}: {v:,}" for k, v in coords.PDV.items()), "Se usan las que caen en un municipio del estado."),
    ("ZM", f"{len(cp):,} PDV en {C.ZM_NOMBRE}; {cp.con_venta.sum():,} con venta de {CAT.replace('CustomCat_', '')} ({cp.con_venta.mean():.0%}).",
     "Universo del 04, 05 y 06."),
    ("Canal", f"Moderno {(cp.canal == 'Moderno').sum():,} · Tradicional {(cp.canal == 'Tradicional').sum():,} (src/cadenas.py).",
     "Las letras y Golden Stores son del canal Tradicional."),
    ("Potencial", f"Sin venta: potencial vacío en {vacios.iloc[0]:.0f}% y clase vacía en {vacios.iloc[1]:.0f}% (el CP no lo calcula).",
     "En los entregables se dice el motivo (sin dato en el CP)."),
    ("Duplicados", f"{dup.sum():,} PDV comparten coordenadas exactas con otro.", "Se conservan (pueden ser locales del mismo predio)."),
], columns=["tema", "hallazgo", "implicación"])
with pd.option_context("display.max_colwidth", None):
    display(hallazgos)

salida = cp.set_index("pos_id").drop(columns=["pos_latitude", "pos_longitude"])
salida["cajas_mes_vida"] = salida["cajas_mes_activo"] = V.where(V > 0).to_numpy()     # sin ventas: la venta es la media del CP
for c_ in ["prefijos", "n_prefijos", "cajas_total", "meses_activos", "primera_venta", "ultima_venta", "meses_vida", "meses_span",
           "tasa_actividad", "recencia_meses", "estado_actividad"]:
    salida[c_] = np.nan
salida["alta_reciente"] = False
salida["z_robusto"] = eda.z_robusto(np.log1p(salida.cajas_mes_vida))
salida["atipico_volumen"] = salida.z_robusto.abs() > 3.5
salida.index.name = "pos_id_cp"
salida.reset_index().to_parquet(C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet", index=False)
out = C.OUT / f"00_validacion_cp_{C.CLIENTE}_{C.SLUG}.xlsx"
with pd.ExcelWriter(out) as xw:
    hallazgos.to_excel(xw, sheet_name="Hallazgos", index=False)
    FUENTES_CLIENTE.to_excel(xw, sheet_name="Datos del cliente", index=False)
    coords.to_excel(xw, sheet_name="Coordenadas")
    por_mun.round(2).to_excel(xw, sheet_name="Por municipio")
    por_sub.round(3).to_excel(xw, sheet_name="Por subcanal")
    clase.to_excel(xw, sheet_name="Clase CP")
print(f"Guardado: pdv_{C.CLIENTE}_{C.SLUG}.parquet ({len(salida):,} PDV, {int(salida.con_venta.sum()):,} con venta) | {out.name}")
