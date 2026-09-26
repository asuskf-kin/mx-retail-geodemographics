# %% [markdown]
# # 04 · Perfil NSE e indicadores por hexágono para cada punto de venta (PDV) de Bepensa — ZM de la ciudad activa
#
# **Papel en la metodología Golden Stores (notebook 05):** construye la **variable 2, demanda potencial con base en el área
# transaccional** de cada tienda (hogares y su perfil a ≤ 300 m, más competidores). La variable 1 (ventas) viene del 00.
#
# No se califica la ZM completa ni por demografía agregada: **la unidad es el PDV**. Para cada PDV con
# coordenadas (tabla del notebook 00) se construye su área con hexágonos H3 y se calculan ahí todos los
# indicadores del pipeline, junto con su venta.
#
# **Método:**
# 1. Cada **manzana** (Censo 2020 + Marco Geoestadístico) lleva los hogares por categoría de su AGEB
#    (microsimulación del notebook 01), en proporción a sus hogares — igual que el notebook 03.
# 2. Los hogares ocupan **todo el polígono de la manzana**, no un punto: se reparten entre los hexágonos **H3**
#    (`C.H3_RES`, res 10 ≈ 0.015 km², arista ≈ 76 m) según el área de la manzana que cae en cada uno. Así una manzana
#    grande cuyo centro queda fuera del área de 300 m aporta la parte que sí está dentro. Las manzanas del Censo sin
#    polígono en el Marco vigente se reparten sobre su AGEB (notebook 01). También entran las **localidades rurales**
#    (ITER 2020 sobre sus manzanas rurales del Marco) y los hogares se **actualizan a 2025** con el crecimiento de
#    población por municipio de la Encuesta Intercensal 2025 (`C.AJUSTE_HOGARES`; notebook 01, secciones 8 y 9).
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
    C.PROC / f"nse_ageb_{C.SLUG}.parquet": "01_socioeconomico_merida", C.PROC / f"manzanas_{C.SLUG}.gpkg": "01_socioeconomico_merida", C.PROC / f"rurales_{C.SLUG}.gpkg": "01_socioeconomico_merida",
    C.PROC / f"crecimiento_municipal_{C.SLUG}.parquet": "01_socioeconomico_merida",
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
tiendas = pd.read_parquet(C.PROC / f"tiendas_denue_{C.SLUG}.parquet")
pdv = pd.read_parquet(C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet")
hh_cols = [f"HHs_{c}" for c in C.CATEGORIAS]
REF = ageb[hh_cols].sum().values / ageb["Total HHs"].sum() * 100        # índice vs total de la ZM (igual que 01 y 03)

mz = gpd.read_file(C.PROC / f"manzanas_{C.SLUG}.gpkg")                   # polígonos (CRS métrico del Marco Geoestadístico)
mz = mz.merge(ageb[["CVEGEO"] + hh_cols], left_on="CVEGEO_AGEB", right_on="CVEGEO", suffixes=("", "_a"))
mz[hh_cols] = mz[hh_cols].values * mz.share.values[:, None]
mz = mz[mz[hh_cols[0]].notna() & (mz.hog > 0)].reset_index(drop=True)
mz["MUN"], mz["ambito"] = mz.CVEGEO.str[2:5], "urbano"
# localidades rurales (ITER 2020, notebook 01): también son demanda de las tiendas cercanas
rur = gpd.read_file(C.PROC / f"rurales_{C.SLUG}.gpkg").to_crs(mz.crs)
rur["CVEGEO"] = rur.CVEGEO_LOC + "_" + rur.index.astype(str)
rur["ambito"] = "rural"
mz = pd.concat([mz[["CVEGEO", "MUN", "ambito", *hh_cols, "geometry"]], rur[["CVEGEO", "MUN", "ambito", *hh_cols, "geometry"]]],
               ignore_index=True)
mz = gpd.GeoDataFrame(mz, geometry="geometry", crs=rur.crs)
hog_2020 = mz[hh_cols[:5]].sum(axis=1)
print(f"Hogares 2020: urbanos {hog_2020[mz.ambito == 'urbano'].sum():,.0f} + rurales {hog_2020[mz.ambito == 'rural'].sum():,.0f}")
if C.AJUSTE_HOGARES == "eic2025":                                        # actualización a 2025 por municipio (notebook 01, sección 9)
    crec = pd.read_parquet(C.PROC / f"crecimiento_municipal_{C.SLUG}.parquet")
    mz[hh_cols] = mz[hh_cols].values * mz.MUN.map(crec.factor_hogares).fillna(1.0).values[:, None]
    print("Hogares actualizados a 2025 con el crecimiento de población de la EIC 2025:",
          ", ".join(f"{crec.Municipio[m]} ×{f:.3f}" for m, f in crec.factor_hogares.items()),
          f"→ {mz[hh_cols[:5]].sum(axis=1).sum():,.0f} hogares")

# rejilla H3: todos los hexágonos que tocan alguna manzana (modo "overlap") y reparto por área de intersección
celdas = set()
for geom in mz.to_crs(4326).geometry:
    for parte in getattr(geom, "geoms", [geom]):
        forma = h3.LatLngPoly([(y, x) for x, y in parte.exterior.coords], *[[(y, x) for x, y in r.coords] for r in parte.interiors])
        celdas.update(h3.h3shape_to_cells_experimental(forma, C.H3_RES, contain="overlap"))
celdas = sorted(celdas)
rejilla = gpd.GeoDataFrame({"hex": celdas}, crs=4326,
                           geometry=[Polygon([(lo, la) for la, lo in h3.cell_to_boundary(c)]) for c in celdas]).to_crs(mz.crs)
mz["area_mz"] = mz.geometry.area
pedazos = gpd.overlay(mz[["CVEGEO", "area_mz", *hh_cols, "geometry"]], rejilla, how="intersection", keep_geom_type=True)
pedazos["w"] = pedazos.geometry.area / pedazos.area_mz
pedazos[hh_cols] = pedazos[hh_cols].values * pedazos.w.values[:, None]
cobertura = pedazos.groupby("CVEGEO").w.sum()
print(f"Reparto por área: {len(mz):,} manzanas → {len(pedazos):,} pedazos manzana × hexágono | "
      f"manzanas partidas en ≥ 2 hexágonos: {(pedazos.CVEGEO.value_counts() > 1).mean():.0%} | "
      f"área cubierta por la rejilla: {cobertura.min():.4f}–{cobertura.max():.4f}")
HEX = pedazos.groupby("hex")[hh_cols].sum()
HEX["Total HHs"] = HEX[hh_cols[:5]].sum(axis=1)                         # el grupo "tamaño" suma el total de hogares
print(f"Manzanas y piezas rurales: {len(mz):,} → hexágonos con hogares: {len(HEX):,} | hogares: {HEX['Total HHs'].sum():,.0f}")

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
                 pdv_moderno=pdv.canal.eq("Moderno").astype(int), pdv_tradicional=pdv.canal.eq("Tradicional").astype(int),
                 cajas_mes=pdv.cajas_mes_vida.fillna(0),
                 potencial_incremental=pdv.PotentialQuantitativeFinal_TotalPortafolio.fillna(0)).groupby("hex")[
      ["pdv_cp", "pdv_con_venta", "pdv_activos", "pdv_moderno", "pdv_tradicional", "cajas_mes", "potencial_incremental"]].sum()
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
    "pos_id_cp": pdv_r.pos_id_cp, "Nombre": pdv_r.pos_name, "Canal": pdv_r.canal, "Cadena": pdv_r.cadena, "Subcanal": pdv_r.pos_subchannel,
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
    "PDV Bepensa en el área (CP)": rd.pdv_cp, "PDV Bepensa Moderno en el área": rd.pdv_moderno,
    "PDV Bepensa Tradicional en el área": rd.pdv_tradicional, "PDV Bepensa con venta en el área": rd.pdv_con_venta,
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
# 2. **Asociación dentro de cada segmento canal · subcanal** (el 00 mostró que el subcanal cambia la escala de venta y la
#    entrega es por canal): Spearman con IC95
#    de Fisher, información mutua y q de Benjamini-Hochberg sobre todas las pruebas. Solo PDV con venta y con hogares
#    en su área.
# 3. **Robustez** de cada asociación significativa: (a) IC95 por **bootstrap de bloques espaciales** (se remuestrean
#    celdas H3 res 7 de ≈ 5 km² completas, no PDV sueltos), (b) solo PDV **activos** al cierre (los inactivos distorsionan
#    `cajas_mes_vida`), (c) **sin atípicos** de volumen. Es *robusta* si el IC de bloques excluye 0 y el signo se mantiene
#    en (b) y (c).

# %%
plano = pd.DataFrame({"cajas_mes_vida": pdv_r.cajas_mes_vida, "subcanal": pdv_r.canal + " · " + pdv_r.pos_subchannel,   # segmento canal · subcanal
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
    ("Canal", f"{(pdv.canal == 'Moderno').sum():,} PDV Moderno y {(pdv.canal == 'Tradicional').sum():,} Tradicional; se entregan en archivos separados. "
              f"Segmentos analizados (canal · subcanal con ≥ 100 PDV con venta): {senal.subcanal.nunique()}.",
     "Leer las señales dentro de cada segmento."),
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
    ("CP: potencial futuro", "ρ con la venta por subcanal: " + ", ".join(f"{r.subcanal.title()} {r.spearman:+.2f}{'' if r.robusta else ' (no robusta)'}"
                                                                           for r in rob[rob.indicador == 'Potencial incremental del PDV'].itertuples()),
     "Variable de clasificación (potencial futuro), no decisiva; consistente con el 00 (sección 5.3)."),
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
    ("Indice (resaltado)", "En la hoja PDV: índice ≥ 105 en lima (sobrerrepresentado vs la ZM), ≤ 95 en gris (subrepresentado)."),
    ("HHs / % / Indice", "Hogares de la categoría en el área, su % y el índice vs el total de la ZM (100 = igual al promedio)."),
    ("Cajas/mes (vida)", "Cajas vendidas / meses desde la primera venta hasta el cierre (ago-2026). Señal principal (notebook 00)."),
    ("Cajas/mes (activo)", "avg_monthly_boxes de Bepensa (cajas / meses con venta). Sobreestima a PDV intermitentes."),
    ("Potencial incremental", "PotentialQuantitativeFinal del CP (= venta actual × brecha vs PDV comparable)."),
    ("Penetración Bepensa en el área %", "PDV con venta / PDV del CP en el área."),
    ("DENUE ... en el área", "Tiendas DENUE 05_2026 (supermercados, minisúpers, abarrotes) por canal y formato en el área."),
    ("Canal / Cadena", "Moderno = cadena identificada por nombre (farmacias de cadena, Modelorama, conveniencia); Tradicional = independientes y Six. Regla única en src/cadenas.py (igual que DENUE)."),
    ("Fuente de hogares", "Censo 2020 por manzana (urbano) + ITER 2020 (localidades rurales) + microsimulación (notebook 01), repartidos por "
                          "área de manzana entre hexágonos y actualizados a 2025 con el crecimiento de población municipal de la Intercensal 2025."),
], columns=["columna", "definición"])

# ---- entregable Excel con formato corporativo Kin (src/excel_kin.py) ----
import excel_kin as X

ID = list(tabla[""].columns)
corte_venta, corte_area = ID.index("Con venta"), ID.index("HHs en el hexágono")
BLOQUE = {c: ("Punto de venta" if k < corte_venta else "Venta Bepensa (notebook 00)" if k < corte_area
              else f"Área ≤ {C.RADIO_PDV_M} m: hogares, competencia y red Bepensa") for k, c in enumerate(ID)}
GRUPO_DE = {c: g for g, cs in C.GRUPOS.items() for c in cs}
COLOR_GRUPO = {"Punto de venta": X.NEGRO, "Venta Bepensa (notebook 00)": "333333", f"Área ≤ {C.RADIO_PDV_M} m: hogares, competencia y red Bepensa": X.NEGRO}
for k, (g, cs) in enumerate(C.GRUPOS.items()):
    for c in cs:
        COLOR_GRUPO[c] = "3A3A3A" if k % 2 == 0 else X.GRIS
F_PDV = {"HHs": "#,##0", "%": "0.0", "Indice": "0", "Latitud": "0.000000", "Longitud": "0.000000", "Cajas/mes (vida)": "#,##0.00",
         "Cajas/mes (activo)": "#,##0.00", "Tasa actividad": "0.00", "Potencial incremental (cajas/mes)": "#,##0.00", "Brecha vs comparable": "0.00",
         "HHs en el hexágono": "#,##0", "HHs en el área": "#,##0", "Penetración Bepensa en el área %": "0.0", "Cajas/mes Bepensa en el área": "#,##0.0",
         "Mediana cajas/mes por PDV en el área": "#,##0.00", "Cajas/mes por 1,000 HHs en el área": "#,##0.00", "Potencial incremental en el área": "#,##0.0"}


def limpio(df):
    """Solo para mostrar: corrige el error de captura del cliente ("ABARRROTES") en textos y encabezados."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == bool:                                   # Sí / No en vez de VERDADERO / FALSO
            df[c] = df[c].map({True: "Sí", False: "No"})
        elif df[c].dtype == object or str(df[c].dtype).startswith("str"):
            df[c] = df[c].map(lambda v: v.replace("ABARRROTES", "ABARROTES").replace("Abarrrotes", "Abarrotes") if isinstance(v, str)
                              else ("Sí" if v else "No") if isinstance(v, (bool, np.bool_)) else v)
    return df


def tabla_excel(t):
    """Encabezado de 2 niveles para Excel: bloques con nombre para los datos del PDV y la categoría sobre HHs | % | Indice."""
    t = t.copy()
    t.columns = pd.MultiIndex.from_tuples([(BLOQUE[sub] if g == "" else f"{GRUPO_DE.get(g, '')} · {g}" if g in GRUPO_DE else g,
                                            "ID PDV" if sub == "pos_id_cp" else sub) for g, sub in t.columns])
    return t


salidas = []
for canal in ["Moderno", "Tradicional"]:
    sel = (tabla[("", "Canal")] == canal).to_numpy()
    rob_c = rob[rob.subcanal.str.startswith(canal)]
    t_c = tabla[sel]
    out = C.OUT / f"04_pdv_{C.CLIENTE}_{canal.lower()}_hexagonos_{C.SLUG}.xlsx"
    wb = X.libro()
    # resumen por subcanal
    base = t_c[""]
    act_ = base["Estado actividad"].astype(str).eq("activo")
    res_sub = (base.assign(activo=act_, con_venta=base["Con venta"].astype(bool))
               .groupby(base.Subcanal.str.replace("ABARRROTES", "ABARROTES").str.title())
               .agg(**{"PDV (CP)": ("pos_id_cp", "size"), "Con venta": ("con_venta", "sum"), "Activos": ("activo", "sum"),
                       "Mediana hogares 300 m": ("HHs en el área", "median"), "Mediana cajas/mes (vida)": ("Cajas/mes (vida)", "median"),
                       "Mediana DENUE tradicional 300 m": ("DENUE Tradicional en el área", "median"),
                       "Mediana PDV Bepensa 300 m": ("PDV Bepensa en el área (CP)", "median")})
               .sort_values("PDV (CP)", ascending=False))
    res_sub.loc["Total"] = [res_sub["PDV (CP)"].sum(), res_sub["Con venta"].sum(), res_sub["Activos"].sum(), base["HHs en el área"].median(),
                            base["Cajas/mes (vida)"].median(), base["DENUE Tradicional en el área"].median(), base["PDV Bepensa en el área (CP)"].median()]
    res_sub.insert(2, "% con venta", res_sub["Con venta"] / res_sub["PDV (CP)"])
    res_sub.insert(4, "% activos (de con venta)", res_sub["Activos"] / res_sub["Con venta"].replace(0, np.nan))
    X.hoja_tabla(wb, "Resumen", res_sub.rename_axis("Subcanal"), indice=True, titulo=f"Resumen por subcanal · canal {canal}",
                 nota=f"PDV del Customer Potential en la {C.ZM_NOMBRE}. Medianas sobre todos los PDV del subcanal; área = hexágonos a ≤ {C.RADIO_PDV_M} m.",
                 formatos={"PDV (CP)": "#,##0", "Con venta": "#,##0", "% con venta": "0.0%", "Activos": "#,##0", "% activos (de con venta)": "0.0%",
                           "Mediana hogares 300 m": "#,##0", "Mediana cajas/mes (vida)": "#,##0.00", "Mediana DENUE tradicional 300 m": "0",
                           "Mediana PDV Bepensa 300 m": "0"}, anchos={"Subcanal": 28})
    X.hoja_tabla_2niveles(wb, "PDV", tabla_excel(limpio(t_c)), titulo=f"Perfil de hogares a ≤ {C.RADIO_PDV_M} m por punto de venta · canal {canal}",
                          nota="Una fila por PDV. Por categoría: hogares (HHs), % del área e índice vs el total de la ZM (≥ 105 lima, ≤ 95 gris). "
                               "Definiciones en la hoja Diccionario.",
                          formatos=F_PDV, anchos={"Nombre": 32, "HHs": 8, "%": 7, "Indice": 7}, colores_grupo=COLOR_GRUPO, fijar_cols=2)
    hx = geo_hex.drop(columns="geometry").loc[geo_hex.index.isin(pdv.loc[pdv.canal == canal, "hex"])].reset_index()
    X.hoja_tabla(wb, "Hexágonos con PDV", hx, titulo=f"Hexágonos H3 res {C.H3_RES} donde hay PDV del canal {canal}",
                 nota="Hogares por categoría (reparto por área de manzana, 2025), red Bepensa y competencia DENUE dentro de cada hexágono.",
                 formatos={**{c: "#,##0.0" for c in hx.columns if c.startswith("HHs_") or c == "Total HHs"},
                           **{c: "0.0" for c in hx.columns if c.startswith("% ")}, "cajas_mes": "#,##0.0", "potencial_incremental": "#,##0.0"},
                 anchos={"hex": 17})
    X.hoja_tabla(wb, "Hallazgos", limpio(hallazgos04).rename(columns=str.capitalize), titulo="Hallazgos del notebook 04", ajustar=True,
                 nota="Se recalculan en cada corrida. Estadística: Spearman dentro de cada segmento, bootstrap espacial por bloques H3 res 7.",
                 anchos={"Tema": 26, "Hallazgo": 90, "Implicación": 60})
    piv = rob_c[rob_c.robusta].pivot_table(index="indicador", columns="subcanal", values="spearman").round(3)
    piv.columns = [c.split(" · ")[-1].replace("ABARRROTES", "ABARROTES").title() for c in piv.columns]
    X.hoja_tabla(wb, "Señales robustas", piv.rename_axis("Indicador"), indice=True, escala=list(piv.columns),
                 titulo="Asociaciones robustas con la venta (ρ de Spearman por subcanal)",
                 nota="Solo las que sobreviven al bootstrap espacial por bloques, a solo activos y a quitar atípicos. Lima = positiva, gris = negativa.",
                 formatos={c: "+0.00;-0.00" for c in piv.columns}, anchos={"Indicador": 40})
    X.hoja_tabla(wb, "Robustez", limpio(rob_c), titulo="Pruebas de robustez por asociación",
                 formatos={"n": "#,##0", "spearman": "+0.000;-0.000", "MI": "0.000", "q_BH": "0.0000", "rho solo activos": "+0.000;-0.000",
                           "rho sin atípicos": "+0.000;-0.000"}, anchos={"subcanal": 34, "indicador": 38})
    X.hoja_tabla(wb, "Señales detalle", limpio(senal[senal.subcanal.str.startswith(canal)]), titulo="Todas las asociaciones probadas",
                 formatos={"n": "#,##0", "spearman": "+0.000;-0.000", "pearson_log1p": "+0.000;-0.000", "p": "0.0000", "MI": "0.000", "q_BH": "0.0000"},
                 anchos={"x": 38, "y": 18, "subcanal": 34})
    X.hoja_tabla(wb, "Diccionario", diccionario.rename(columns=str.capitalize), titulo="Diccionario de columnas", ajustar=True,
                 anchos={"Columna": 30, "Definición": 110})
    X.portada(wb, "Perfil de hogares por punto de venta", f"Canal {canal} · {C.CLIENTE.title()} · {C.ZM_NOMBRE} · área ≤ {C.RADIO_PDV_M} m",
              [("Universo", f"{int(sel.sum()):,} PDV del canal {canal} en el Customer Potential ({int(t_c[('', 'Con venta')].astype(bool).sum()):,} con venta)."),
               ("Área de cada PDV", f"Hexágonos H3 res {C.H3_RES} con centro a ≤ {C.RADIO_PDV_M} m (≈ 0.27 km²)."),
               ("Hogares", "Censo 2020 por manzana + localidades rurales (ITER), microsimulación NSE AMAI 2024, reparto por área de manzana, "
                           "actualizados a 2025 con la Encuesta Intercensal 2025."),
               ("Competencia", "DENUE 05_2026 (INEGI) · red Bepensa del Customer Potential."),
               ("Ventas", "Bepensa, oct-2024 → ago-2026 (validadas en el notebook 00)."),
               ("Uso", "Variable 2 (demanda potencial) de la metodología Golden Stores: la clasificación final está en el Excel del notebook 05."),
               ("Elaboró", "Kin Analytics · notebooks/_src/04_hexagonos_pdv.py")],
              [("Resumen", "PDV, venta, actividad y entorno por subcanal."),
               ("PDV", "Una fila por PDV: datos, venta y, por categoría, HHs · % · Índice a ≤ 300 m."),
               ("Hexágonos con PDV", "Hogares, red y competencia por hexágono (para mapas)."),
               ("Hallazgos", "Qué se encontró y qué implica."), ("Señales robustas", "Asociaciones con la venta que resisten las pruebas."),
               ("Robustez", "Detalle de las pruebas."), ("Señales detalle", "Todas las asociaciones probadas."), ("Diccionario", "Definición de cada columna.")])
    wb.save(out)
    salidas.append(f"{out.name} ({int(sel.sum()):,} PDV)")
rob.to_parquet(C.PROC / f"robustez_{C.CLIENTE}_{C.SLUG}.parquet", index=False)     # lo usa el notebook 05
tabla.to_pickle(C.PROC / f"pdv_{C.CLIENTE}_hexagonos_{C.SLUG}.pkl")
print("Guardado:", " | ".join(salidas), f"| hexágonos: {len(geo_hex):,}")
