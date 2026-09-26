# %% [markdown]
# # 04 · Perfil NSE e indicadores por hexágono para cada punto de venta (PDV) de Bepensa — ZM de la ciudad activa
#
# No se califica la ZM completa ni por demografía agregada: **la unidad es el PDV**. Para cada PDV con
# coordenadas (tabla del notebook 00) se construye su área con hexágonos H3 y se calculan ahí todos los
# indicadores del pipeline, junto con su venta.
#
# **Método:**
# 1. Cada **manzana** (Censo 2020 + Marco Geoestadístico) lleva los hogares por categoría de su AGEB
#    (microsimulación del notebook 01), en proporción a sus hogares — igual que el notebook 03.
# 2. Cada manzana cae en un hexágono **H3** (`C.H3_RES`, res 10 ≈ 0.015 km², arista ≈ 76 m: del tamaño de una
#    manzana). El hexágono suma sus manzanas.
# 3. El **área del PDV** = los hexágonos cuyo centro está a **≤ `C.RADIO_PDV_M` (300 m)** del PDV (≈ 19 hexágonos,
#    ≈ 0.28 km²). Se calcula por PDV (depende de su ubicación exacta, no solo de su hexágono).
# 4. En esa área: HHs, % e Índice (vs total de la ZM) de tamaño de hogar, edad del menor, edad del jefe y
#    NSE AMAI 2024; competencia DENUE por canal y formato; PDV Bepensa (con y sin venta) y su venta.
#
# **Entradas:** `data/processed/<ciudad>/` → `manzanas_*`, `nse_ageb_*`, `tiendas_denue_*` (notebooks 01-02)
# y `pdv_bepensa_*` (notebook 00). La celda de abajo verifica que existan y dice qué notebook correr si falta alguno.
#
# **Reproducir:** orden 00 → 01 → 02 → 03 → 04 (o `python src/correr.py --pasos 00,01,02,03,04 merida`). Este notebook necesita
# las salidas de 00, 01 y 02.

# %%
import os
import sys
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")       # Bepensa se analiza para la ZM Mérida; cambiar antes de importar config

BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())   # raíz del repo
sys.path.insert(0, str(BASE / "src"))
import numpy as np
import pandas as pd
import geopandas as gpd
import h3
from shapely.geometry import Polygon
from IPython.display import display

import config as C
import eda
from descargas import requisitos

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"Los datos de {C.CLIENTE} son de {C.CLIENTE_CIUDAD}; CIUDAD={C.CIUDAD}"
requisitos({
    C.PROC / f"nse_ageb_{C.SLUG}.parquet": "01_socioeconomico_merida", C.PROC / f"manzanas_{C.SLUG}.parquet": "01_socioeconomico_merida",
    C.PROC / f"tiendas_denue_{C.SLUG}.parquet": "02_tiendas_denue_merida", C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet": "00_ventas_cp_validacion",
})

pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
ARISTA_M = h3.average_hexagon_edge_length(C.H3_RES, "m")
print(f"{C.ZM_NOMBRE} · H3 res {C.H3_RES} (arista {ARISTA_M:.0f} m, área {h3.average_hexagon_area(C.H3_RES, 'km^2'):.3f} km²) · "
      f"área del PDV: hexágonos a ≤ {C.RADIO_PDV_M} m")

# %% [markdown]
# ## 1. Hogares por categoría en cada manzana → hexágono

# %%
ageb = pd.read_parquet(C.PROC / f"nse_ageb_{C.SLUG}.parquet")
mz = pd.read_parquet(C.PROC / f"manzanas_{C.SLUG}.parquet")
tiendas = pd.read_parquet(C.PROC / f"tiendas_denue_{C.SLUG}.parquet")
pdv = pd.read_parquet(C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet")
hh_cols = [f"HHs_{c}" for c in C.CATEGORIAS]
REF = ageb[hh_cols].sum().values / ageb["Total HHs"].sum() * 100        # índice vs total de la ZM (igual que 01 y 03)

mz = mz.merge(ageb[["CVEGEO"] + hh_cols], left_on="CVEGEO_AGEB", right_on="CVEGEO", suffixes=("", "_a"))
mz[hh_cols] = mz[hh_cols].values * mz.share.values[:, None]
mz["hex"] = [h3.latlng_to_cell(a, b, C.H3_RES) for a, b in zip(mz.lat, mz.lon)]
HEX = mz.groupby("hex")[hh_cols].sum()
HEX["Total HHs"] = HEX[hh_cols[:5]].sum(axis=1)                         # el grupo "tamaño" suma el total de hogares
print(f"Manzanas: {len(mz):,} → hexágonos con hogares: {len(HEX):,} | hogares: {HEX['Total HHs'].sum():,.0f}")

# %% [markdown]
# ## 2. Hexágono y área de cada PDV

# %%
pdv["hex"] = [h3.latlng_to_cell(a, b, C.H3_RES) for a, b in zip(pdv.lat, pdv.lon)]
tiendas["hex"] = [h3.latlng_to_cell(a, b, C.H3_RES) for a, b in zip(tiendas.latitud, tiendas.longitud)]

K = int(np.ceil((C.RADIO_PDV_M + ARISTA_M) / (np.sqrt(3) * ARISTA_M))) + 1     # anillos candidatos que cubren el radio
def hex_en_radio(lat, lon, h):
    cand = list(h3.grid_disk(h, K))
    c = np.radians([h3.cell_to_latlng(x) for x in cand])
    la, lo = np.radians(lat), np.radians(lon)
    d = 2 * 6_371_000 * np.arcsin(np.sqrt(np.sin((c[:, 0] - la) / 2) ** 2 + np.cos(la) * np.cos(c[:, 0]) * np.sin((c[:, 1] - lo) / 2) ** 2))
    return [x for x, di in zip(cand, d) if di <= C.RADIO_PDV_M]

area = [hex_en_radio(a, b, h) for a, b, h in zip(pdv.lat, pdv.lon, pdv.hex)]   # una lista de hexágonos por PDV
print(f"Hexágonos por área de PDV: mediana {np.median([len(a) for a in area]):.0f} "
      f"(≈ {np.median([len(a) for a in area]) * h3.average_hexagon_area(C.H3_RES, 'km^2'):.2f} km²)")

def suma_area(tabla: pd.DataFrame) -> pd.DataFrame:
    """Suma, para cada PDV, las filas de `tabla` (indexada por hex) que caen en su área de ≤ 300 m."""
    M = tabla.to_numpy(float)
    pos = pd.Series(np.arange(len(tabla)), index=tabla.index)
    out = np.zeros((len(area), M.shape[1]))
    for i, v in enumerate(area):
        idx = pos.reindex(v).dropna().to_numpy(int)
        if idx.size:
            out[i] = M[idx].sum(axis=0)
    return pd.DataFrame(out, columns=tabla.columns)

HH_AREA = suma_area(HEX)
print(f"PDV: {len(pdv):,} | PDV sin hogares a ≤ {C.RADIO_PDV_M} m (zona no urbana o fuera de manzanas): "
      f"{(HH_AREA['Total HHs'] == 0).sum():,}")

# %% [markdown]
# ## 3. Competencia DENUE y red Bepensa en el área

# %%
comp = pd.crosstab(tiendas.hex, [tiendas.canal]).add_prefix("DENUE ").join(
       pd.crosstab(tiendas.hex, tiendas.formato).add_prefix("DENUE "), how="outer")
comp["DENUE OXXO"] = tiendas[tiendas.cadena == "OXXO"].groupby("hex").size()
COMP_AREA = suma_area(comp.fillna(0))

pdv["activo"] = pdv.estado_actividad.astype(str).eq("activo")
red = pdv.assign(pdv_cp=1, pdv_con_venta=pdv.con_venta.astype(int), pdv_activos=pdv.activo.astype(int),
                 cajas_mes=pdv.cajas_mes_vida.fillna(0),
                 potencial_incremental=pdv.PotentialQuantitativeFinal_TotalPortafolio.fillna(0)).groupby("hex")[
      ["pdv_cp", "pdv_con_venta", "pdv_activos", "cajas_mes", "potencial_incremental"]].sum()
RED_AREA = suma_area(red)
RED_AREA["penetracion_%"] = RED_AREA.pdv_con_venta / RED_AREA.pdv_cp * 100
RED_AREA["cajas_mes_mediana_pdv"] = [pdv.loc[pdv.hex.isin(v) & pdv.con_venta, "cajas_mes_vida"].median() for v in area]

# %% [markdown]
# ## 4. Tabla por PDV (layout del entregable: HHs · % · Índice por categoría)

# %%
hh = HH_AREA
tot = hh["Total HHs"].to_numpy()
pdv_r = pdv.reset_index(drop=True)
cp_ = COMP_AREA
rd = RED_AREA

ids = pd.DataFrame({
    "pos_id_cp": pdv_r.pos_id_cp, "Nombre": pdv_r.pos_name, "Subcanal": pdv_r.pos_subchannel,
    "Tamaño PDV": pdv_r.pos_size_classification, "Latitud": pdv_r.lat, "Longitud": pdv_r.lon,
    "Región Nielsen": C.REGION_NIELSEN, "Estado": C.NOM_ENT, "Municipio": pdv_r.municipio_mg,
    "Localidad": pdv_r.pos_city, "Zonas Metropolitanas": C.ZM_NOMBRE, "Hexágono H3": pdv_r.hex,
    # venta del PDV (señales validadas en el notebook 00)
    "Con venta": pdv_r.con_venta, "Estado actividad": pdv_r.estado_actividad.astype(str).replace("nan", "sin venta"),
    "Cajas/mes (vida)": pdv_r.cajas_mes_vida, "Cajas/mes (activo)": pdv_r.cajas_mes_activo,
    "Tasa actividad": pdv_r.tasa_actividad, "Recencia (meses)": pdv_r.recencia_meses,
    "Potencial incremental (cajas/mes)": pdv_r.PotentialQuantitativeFinal_TotalPortafolio,
    "Brecha vs comparable": pdv_r.PotentialEstimatedToCover_TotalPortafolio,
    "Atípico volumen": pdv_r.atipico_volumen.fillna(False),
    # área (hexágono + anillo)
    "HHs en el hexágono": HEX["Total HHs"].reindex(pdv.hex).fillna(0).to_numpy().round(0),
    "HHs en el área": tot.round(0),
    **{f"{c} en el área": cp_[c].to_numpy() for c in cp_.columns},
    "PDV Bepensa en el área (CP)": rd.pdv_cp, "PDV Bepensa con venta en el área": rd.pdv_con_venta,
    "Penetración Bepensa en el área %": rd["penetracion_%"].round(1),
    "Cajas/mes Bepensa en el área": rd.cajas_mes.round(1), "Mediana cajas/mes por PDV en el área": rd.cajas_mes_mediana_pdv.round(2),
    "Cajas/mes por 1,000 HHs en el área": np.where(tot > 0, rd.cajas_mes / np.where(tot > 0, tot, 1) * 1000, np.nan).round(2),
    "Potencial incremental en el área": rd.potencial_incremental.round(1),
})
blocks = {("", k): v.values for k, v in ids.items()}
for k, c in enumerate(C.CATEGORIAS):
    pct = hh[f"HHs_{c}"].to_numpy() / np.where(tot > 0, tot, np.nan) * 100
    blocks[(c, "HHs")] = hh[f"HHs_{c}"].round(0).to_numpy()
    blocks[(c, "%")] = np.round(pct, 1)
    blocks[(c, "Indice")] = np.round(pct / REF[k] * 100, 0)
tabla = pd.DataFrame(blocks)
tabla.columns = pd.MultiIndex.from_tuples(tabla.columns)
tabla.head()

# %% [markdown]
# ## 5. ¿Qué indicadores del área se asocian con la venta del PDV?
#
# Mismo rigor que el notebook 00, más un problema propio de este análisis: **PDV cercanos comparten hogares en su
# área de 300 m**, así que no son observaciones independientes y las p clásicas salen optimistas.
#
# 1. **Dependencia espacial:** I de Moran de la venta (log1p, descontada la mediana de su subcanal) entre PDV a
#    ≤ 300 m. I > 0 significativo confirma que los vecinos se parecen.
# 2. **Asociación dentro de cada subcanal** (el 00 mostró que el subcanal cambia la escala de venta): Spearman con IC95
#    de Fisher, información mutua y q de Benjamini-Hochberg sobre todas las pruebas. Solo PDV con venta y con hogares
#    en su área.
# 3. **Robustez** de cada asociación significativa: (a) IC95 por **bootstrap de bloques espaciales** (se remuestrean
#    celdas H3 res 7 de ≈ 5 km² completas, no PDV sueltos), (b) solo PDV **activos** al cierre (los inactivos distorsionan
#    `cajas_mes_vida`), (c) **sin atípicos** de volumen. Es *robusta* si el IC de bloques excluye 0 y el signo se mantiene
#    en (b) y (c).

# %%
plano = pd.DataFrame({"cajas_mes_vida": pdv_r.cajas_mes_vida, "subcanal": pdv_r.pos_subchannel,
                      "activo": pdv_r.activo.values, "atipico": pdv_r.atipico_volumen.fillna(False).astype(bool).values,
                      "lat": pdv_r.lat, "lon": pdv_r.lon, "bloque": [h3.cell_to_parent(h, 7) for h in pdv_r.hex],
                      "HHs en el área": tot, "Penetración Bepensa %": rd["penetracion_%"],
                      "Potencial incremental del PDV": pdv_r.PotentialQuantitativeFinal_TotalPortafolio,
                      **{f"% {c}": hh[f"HHs_{c}"] / np.where(tot > 0, tot, np.nan) * 100 for c in C.CATEGORIAS},
                      **{f"{c} (área)": cp_[c] for c in cp_.columns}})
plano = plano[pdv_r.con_venta.values & (tot > 0)].reset_index(drop=True)
meta = ["cajas_mes_vida", "subcanal", "activo", "atipico", "lat", "lon", "bloque"]
x_cols = [c for c in plano.columns if c not in meta]

# 5.1 dependencia espacial de la venta (descontado el subcanal)
resid = np.log1p(plano.cajas_mes_vida) - plano.groupby("subcanal").cajas_mes_vida.transform(lambda v: np.log1p(v).median())
vec = eda.vecinos_radio(plano.lat, plano.lon, C.RADIO_PDV_M)
moran = eda.moran_i(resid, vec)
print(f"I de Moran (venta log, sin efecto subcanal, vecinos ≤ {C.RADIO_PDV_M} m): I = {moran['I']:.3f} "
      f"(E[I] = {moran['E[I]']:.4f}), p de permutación = {moran['p_perm']:.3f}; PDV con al menos un vecino: {moran['con_vecinos_%']:.0f}%")
print(f"Bloques espaciales para el bootstrap: {plano.bloque.nunique():,} celdas H3 res 7 "
      f"(mediana {plano.groupby('bloque').size().median():.0f} PDV por bloque)")

# 5.2 asociación por subcanal
senal = []
for sc, g in plano.groupby("subcanal"):
    if len(g) >= 100:
        senal.append(eda.dependencias(g, x_cols, ["cajas_mes_vida"]).assign(subcanal=sc, n_subcanal=len(g)))
senal = pd.concat(senal, ignore_index=True)
senal["q_BH"] = eda.stats.false_discovery_control(senal.p.to_numpy(), method="bh")   # corrección sobre todas las pruebas
senal["significativa"] = senal.q_BH < 0.05

# 5.3 robustez de las asociaciones significativas
rob = []
for r in senal[senal.significativa].itertuples():
    g = plano[plano.subcanal == r.subcanal]
    rho_b, lo_b, hi_b = eda.spearman_bloques(g[r.x], g.cajas_mes_vida, g.bloque, B=300)
    ga, gs = g[g.activo], g[~g.atipico]
    rho_a = eda.stats.spearmanr(ga[r.x], ga.cajas_mes_vida, nan_policy="omit")[0] if len(ga) > 30 else np.nan
    rho_s = eda.stats.spearmanr(gs[r.x], gs.cajas_mes_vida, nan_policy="omit")[0]
    signo = np.sign(r.spearman)
    rob.append({"subcanal": r.subcanal, "indicador": r.x, "n": r.n, "spearman": r.spearman, "IC95 Fisher": r.IC95,
                "IC95 bloques": f"[{lo_b:+.2f}, {hi_b:+.2f}]", "MI": r.MI, "q_BH": r.q_BH,
                "rho solo activos": rho_a, "rho sin atípicos": rho_s,
                "robusta": bool((lo_b > 0 or hi_b < 0) and np.sign(rho_a) == signo and np.sign(rho_s) == signo)})
rob = pd.DataFrame(rob).sort_values(["robusta", "spearman"], key=lambda c: c.abs() if c.name == "spearman" else c, ascending=False)
print(f"Asociaciones significativas (q < 0.05): {len(rob)} | robustas: {rob.robusta.sum()} "
      f"| se caen con el bootstrap de bloques u otra prueba: {(~rob.robusta).sum()}")
resumen = (rob[rob.robusta].pivot_table(index="indicador", columns="subcanal", values="spearman")
           .reindex(x_cols).dropna(how="all"))
display(resumen.round(2))
print("Celdas vacías = asociación no significativa o no robusta en ese subcanal.")
with pd.option_context("display.max_rows", 200):
    display(rob.round(3))

# %% [markdown]
# ### 5.4 Hallazgos del notebook 04

# %%
fuerte = rob[rob.robusta].reindex(rob[rob.robusta].spearman.abs().sort_values(ascending=False).index).head(5)
hallazgos04 = pd.DataFrame([
    ("Área de 300 m", f"Mediana de {np.median([len(a) for a in area]):.0f} hexágonos H3 res {C.H3_RES} por PDV; {(tot == 0).sum():,} de {len(pdv):,} PDV "
                      f"no tienen hogares a ≤ {C.RADIO_PDV_M} m (zonas no urbanas o fuera de manzanas).",
     "Esos PDV no tienen perfil NSE; se conservan con HHs = 0."),
    ("Dependencia espacial", f"I de Moran = {moran['I']:.3f} (p = {moran['p_perm']:.3f}); {moran['con_vecinos_%']:.0f}% de los PDV con venta tienen otro a ≤ {C.RADIO_PDV_M} m.",
     ("Dependencia débil: los IC por bloques casi no cambian las conclusiones." if moran["I"] < 0.1 else "Dependencia relevante: interpretar solo los IC por bloques.")
     + " Se exige IC por bootstrap de bloques espaciales."),
    ("Asociaciones", f"{len(rob)} significativas tras BH; {int(rob.robusta.sum())} sobreviven a bloques, solo activos y sin atípicos.",
     "Usar solo las robustas para interpretar."),
    ("Más fuertes (robustas)", "; ".join(f"{r['indicador']} en {r['subcanal'].title()} ρ = {r['spearman']:+.2f} (IC bloques {r['IC95 bloques']})" for _, r in fuerte.iterrows()) if len(fuerte) else "ninguna",
     "Magnitudes chicas (|ρ| ≲ 0.3): el entorno explica poco de la venta de un PDV individual."),
    ("Potencial incremental", "ρ con la venta por subcanal: " + ", ".join(f"{r.subcanal.title()} {r.spearman:+.2f}{'' if r.robusta else ' (no robusta)'}"
                                                                           for r in rob[rob.indicador == 'Potencial incremental del PDV'].itertuples()),
     "Comparar con el 00 (sección 5.3): debe aparecer en los mismos subcanales."),
], columns=["tema", "hallazgo", "implicación"])
with pd.option_context("display.max_colwidth", None):
    display(hallazgos04)

# %% [markdown]
# ## 6. Hexágonos (para mapas) y guardado

# %%
hexs = pd.Index(sorted(set(HEX.index) | set(pdv.hex)))
geo_hex = gpd.GeoDataFrame(
    HEX.reindex(hexs).fillna(0).join(red.reindex(hexs).fillna(0)).join(comp.reindex(hexs).fillna(0)),
    geometry=[Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(h)]) for h in hexs], crs=4326)
geo_hex.index.name = "hex"
for c in C.CATEGORIAS:
    geo_hex[f"% {c}"] = geo_hex[f"HHs_{c}"] / geo_hex["Total HHs"].replace(0, np.nan) * 100
geo_hex.reset_index().to_file(C.PROC / f"hexagonos_h3r{C.H3_RES}_{C.CLIENTE}_{C.SLUG}.gpkg", driver="GPKG")

diccionario = pd.DataFrame([
    ("Hexágono H3", f"Celda H3 resolución {C.H3_RES} donde está el PDV (área media {h3.average_hexagon_area(C.H3_RES, 'km^2'):.2f} km²)."),
    ("... en el área", f"Suma de los hexágonos H3 res {C.H3_RES} cuyo centro está a ≤ {C.RADIO_PDV_M} m del PDV."),
    ("HHs / % / Indice", "Hogares de la categoría en el área, su % y el índice vs el total de la ZM (100 = igual al promedio)."),
    ("Cajas/mes (vida)", "Cajas vendidas / meses desde la primera venta hasta el cierre (ago-2026). Señal principal (notebook 00)."),
    ("Cajas/mes (activo)", "avg_monthly_boxes de Bepensa (cajas / meses con venta). Sobreestima a PDV intermitentes."),
    ("Potencial incremental", "PotentialQuantitativeFinal del CP (= venta actual × brecha vs PDV comparable)."),
    ("Penetración Bepensa en el área %", "PDV con venta / PDV del CP en el área."),
    ("DENUE ... en el área", "Tiendas DENUE 05_2026 (supermercados, minisúpers, abarrotes) por canal y formato en el área."),
    ("Fuente de hogares", "Censo 2020 por AGEB y manzana + microsimulación (notebook 01); no proyectado a 2026."),
], columns=["columna", "definición"])

out = C.OUT / f"04_pdv_{C.CLIENTE}_hexagonos_{C.SLUG}.xlsx"
with pd.ExcelWriter(out) as xw:
    tabla.to_excel(xw, sheet_name="PDV")
    geo_hex.drop(columns="geometry").loc[geo_hex.pdv_cp > 0].to_excel(xw, sheet_name="Hexagonos con PDV")
    hallazgos04.to_excel(xw, sheet_name="Hallazgos", index=False)
    resumen.round(3).to_excel(xw, sheet_name="Señales robustas")
    rob.to_excel(xw, sheet_name="Robustez", index=False)
    senal.to_excel(xw, sheet_name="Señales detalle", index=False)
    diccionario.to_excel(xw, sheet_name="Diccionario", index=False)
tabla.to_pickle(C.PROC / f"pdv_{C.CLIENTE}_hexagonos_{C.SLUG}.pkl")
print(f"Guardado: {out} ({len(tabla):,} PDV) | hexágonos: {len(geo_hex):,}")
