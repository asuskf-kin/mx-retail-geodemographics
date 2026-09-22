# %% [markdown]
# # 03 · Unión tiendas × perfil socioeconómico — ZM Mérida (canal Moderno y Tradicional)
#
# Cómo se unen las dos capas:
#
# 1. **AGEB donde está la tienda** (unión espacial punto-en-polígono) → perfil del "vecindario inmediato".
# 2. **Área de influencia (radio)** alrededor de cada tienda → se suman los hogares de todas las
#    **manzanas** cuyo centroide cae dentro del radio. Cada manzana hereda el perfil de su AGEB,
#    proporcional a sus hogares (método dasimétrico: más preciso que cortar el polígono AGEB por área).
# 3. **Competencia**: tiendas de canal moderno y tradicional, por formato (y OXXO), dentro del mismo radio.
#
# Resultado: una fila por tienda con el mismo layout del entregable (Latitud, Longitud, Región Nielsen,
# Estado, Municipio, Localidad, ZM + HHs / % / Índice por categoría).

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent / "src"))
import numpy as np
import pandas as pd
import geopandas as gpd
from sklearn.neighbors import BallTree

import config as C

RADIOS_M = [500, 1000]      # radios de influencia a calcular (metros)
R_TIERRA = 6_371_000

# %%
ageb = pd.read_parquet(C.PROC / "nse_ageb_zm_merida.parquet")
mz = pd.read_parquet(C.PROC / "manzanas_zm_merida.parquet")
tiendas = pd.read_parquet(C.PROC / "tiendas_denue_zm_merida.parquet")
geo = gpd.read_file(C.PROC / "ageb_zm_merida.gpkg")
hh_cols = [f"HHs_{c}" for c in C.CATEGORIAS]

# referencia del indice (la misma del paso 01)
if C.REFERENCIA_INDICE == "zm":
    REF = ageb[hh_cols].sum().values / ageb["Total HHs"].sum() * 100
else:
    REF = pd.read_parquet(C.PROC / "ref_estado.parquet").pct.reindex(C.CATEGORIAS).values

# hogares por categoria a nivel manzana
mz = mz.merge(ageb[["CVEGEO", "Total HHs"] + hh_cols], left_on="CVEGEO_AGEB", right_on="CVEGEO", suffixes=("", "_a"))
MZ_HH = mz[hh_cols].values * mz.share.values[:, None]
MZ_TOT = MZ_HH[:, :5].sum(axis=1)          # total hogares de la manzana (grupo tamaño suma el total)
print(f"Manzanas: {len(mz):,} | hogares: {MZ_TOT.sum():,.0f} | tiendas: {len(tiendas):,}")

# %% [markdown]
# ## 1. AGEB que contiene a cada tienda

# %%
pts = gpd.GeoDataFrame(tiendas, geometry=gpd.points_from_xy(tiendas.longitud, tiendas.latitud), crs=4326).to_crs(geo.crs)
j = gpd.sjoin(pts, geo[["CVEGEO", "geometry"]], how="left", predicate="within")
tiendas["CVEGEO_AGEB"] = j.CVEGEO.values
print("Tiendas fuera de AGEB urbana (rurales / sin hogares):", tiendas.CVEGEO_AGEB.isna().sum())

# %% [markdown]
# ## 2. Áreas de influencia y competencia

# %%
bt_mz = BallTree(np.radians(mz[["lat", "lon"]].values), metric="haversine")
bt_t = BallTree(np.radians(tiendas[["latitud", "longitud"]].values), metric="haversine")
XY_T = np.radians(tiendas[["latitud", "longitud"]].values)


def tabla_layout(hh, total, ids):
    """hh: n x categorias (HHs). Devuelve DataFrame con columnas de 2 niveles como el entregable."""
    hh = pd.DataFrame(hh, columns=C.CATEGORIAS)
    blocks = {("", k): v.values for k, v in ids.items()}
    for g, cols in C.GRUPOS.items():                       # cada grupo suma el total
        hh[cols] = hh[cols].div(hh[cols].sum(axis=1).replace(0, np.nan), axis=0).mul(total, axis=0)
    for k, c in enumerate(C.CATEGORIAS):
        pct = hh[c] / np.where(total > 0, total, np.nan) * 100
        blocks[(c, "HHs")] = hh[c].round(0).values
        blocks[(c, "%")] = pct.round(1).values
        blocks[(c, "Indice")] = (pct / REF[k] * 100).round(0).values
    out = pd.DataFrame(blocks)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    return out


ids_base = pd.DataFrame({
    "id_denue": tiendas.id, "Tienda": tiendas.nom_estab, "Canal": tiendas.canal, "Cadena": tiendas.cadena,
    "Formato": tiendas.formato, "SCIAN": tiendas.codigo_act, "Personal": tiendas.per_ocu,
    "Latitud": tiendas.latitud, "Longitud": tiendas.longitud, "Región Nielsen": C.REGION_NIELSEN,
    "Estado": C.NOM_ENT, "Municipio": tiendas.municipio, "Localidad": tiendas.localidad,
    "Zonas Metropolitanas": C.ZM_NOMBRE, "CVEGEO_AGEB": tiendas.CVEGEO_AGEB,
})

resultados = {}
for r in RADIOS_M:
    ind = bt_mz.query_radius(XY_T, r=r / R_TIERRA)
    hh = np.vstack([MZ_HH[i].sum(axis=0) if len(i) else np.zeros(len(C.CATEGORIAS)) for i in ind])
    total = np.array([MZ_TOT[i].sum() for i in ind])
    # competencia en el radio (excluye la propia tienda)
    vec = bt_t.query_radius(XY_T, r=r / R_TIERRA)
    fmt, cad, can = tiendas.formato.values, tiendas.cadena.values, tiendas.canal.values

    def contar(arr, valor):
        return [int((arr[v] == valor).sum() - (arr[k] == valor)) for k, v in enumerate(vec)]

    ids = ids_base.assign(**{
        "Radio (m)": r,
        "HHs totales en radio": total.round(0),
        "Tiendas moderno en radio": contar(can, "Moderno"),
        "Tiendas tradicional en radio": contar(can, "Tradicional"),
        "Supermercados en radio": contar(fmt, "Supermercado"),
        "Minisupers en radio": contar(fmt, "Minisuper"),
        "Abarrotes en radio": contar(fmt, "Abarrotes"),
        "OXXO en radio": contar(cad, "OXXO"),
    })
    ids["HHs por tienda en radio"] = (total / (1 + ids["Tiendas moderno en radio"] + ids["Tiendas tradicional en radio"])).round(0)
    resultados[r] = tabla_layout(hh, total, ids)
    print(f"Radio {r} m: mediana de hogares por tienda = {np.median(total):,.0f}")

resultados[RADIOS_M[-1]].head()

# %% [markdown]
# ## 3. Perfil del AGEB donde está la tienda

# %%
a = tiendas[["CVEGEO_AGEB"]].merge(ageb, left_on="CVEGEO_AGEB", right_on="CVEGEO", how="left")
tabla_ageb = tabla_layout(a[hh_cols].fillna(0).values, a["Total HHs"].fillna(0).values, ids_base)

# %% [markdown]
# ## 4. Lectura rápida: NSE promedio del área de influencia por canal / cadena / formato

# %%
r = RADIOS_M[-1]
t = resultados[r]
nse_cols = C.GRUPOS["NSE AMAI 2022"]
pct_nse = pd.DataFrame({c: t[(c, "%")] for c in nse_cols})
base = pd.concat([t[("", "Canal")].rename("Canal"), t[("", "Cadena")].rename("Cadena"),
                  t[("", "Formato")].rename("Formato"), pct_nse], axis=1)


def resumen_por(df, claves):
    res = df.groupby(claves)[nse_cols].mean().round(1)
    res["# tiendas"] = df.groupby(claves).size()
    return res.sort_values("# tiendas", ascending=False)


resumenes = {
    "Moderno": resumen_por(base[base.Canal == "Moderno"], ["Cadena"]),
    "Tradicional": resumen_por(base[base.Canal == "Tradicional"], ["Formato", "Cadena"]),
}
print(resumen_por(base, ["Canal"]))
resumenes["Moderno"]

# %% [markdown]
# ## 5. Guardar

# %%
# Un archivo por canal: Moderno (cadenas) y Tradicional (abarrotes / independientes)
for canal in C.CANALES:
    out = C.OUT / f"03_{canal.lower()}_x_nse_zm_merida.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        for r, tab in resultados.items():
            tab[tab[("", "Canal")] == canal].to_excel(xw, sheet_name=f"Radio {r} m")
        tabla_ageb[tabla_ageb[("", "Canal")] == canal].to_excel(xw, sheet_name="AGEB de la tienda")
        resumenes[canal].to_excel(xw, sheet_name=f"Resumen NSE {RADIOS_M[-1]}m")
    print(f"Guardado: {out.name} ({(tiendas.canal == canal).sum():,} tiendas)")

for r, tab in resultados.items():
    flat = tab.copy()
    flat.columns = [b if a == "" else f"{a} | {b}" for a, b in flat.columns]
    flat.to_parquet(C.PROC / f"tiendas_nse_radio_{r}m.parquet", index=False)
