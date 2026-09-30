# %% [markdown]
# # 06 · Letra 1 (NSE) y Letra 2 (Ventas) por punto de venta — Bepensa · canal Tradicional · sueros e hidratación · ZM Mérida
#
# Construye las dos letras de la clasificación Golden Stores de cada punto de venta (PDV) del **canal Tradicional**, con **solo
# datos del CP** para el PDV: id, nombre, subcanal, coordenadas, venta media y potencial (regla del usuario, 2026-09-30: se
# quita todo lo del canal Moderno y no se usa el archivo de ventas). Enfoque acordado:
#
# * **Letra 1 · NSE del clúster.** La ZM se divide en hexágonos H3 de res 9 (≈ 0.1 km²): el **centro** de cada hexágono es un
#   punto NSE y su **buffer de 300 m** reúne los hogares que le dan su NSE (INEGI: regla AMAI por hexágono res 10, asegurada con
#   el Censo por manzana). Todos los PDV que caen en el hexágono **comparten** ese NSE: la Letra 1 es del clúster, no del PDV
#   (hexágonos en vez de centroides de AGEB: más simple en geografías complejas). **AltScore mueve el NSE**: su índice alrededor
#   del mismo centro se combina con el de INEGI con peso λ.
# * **Letra 2 · Ventas del PDV.** Cada PDV vale su **venta media + su potencial**, los dos del **CP**, y se compara con los PDV
#   con venta de su **buffer de 300 m** (su clúster de venta): **H** si supera su media; si es el único con venta en su buffer
#   queda **L**. **Rappi** (sueros e hidratación, notebook 00c) **premia a la locación moviendo su venta**: la venta de cada
#   tienda Rappi activa, en cajas, se reparte entre los PDV con venta de su radio y se suma a la de cada uno y a la media de su
#   clúster de venta.
# * Las letras juntas llevan la acción fija de Golden Stores (HH Atacar · HL Bloquear · LH Fortalecer · LL Mantener). El
#   entregable trae cada letra **sin y con** su fuente adicional: Letra 1 sin y con AltScore, Letra 2 sin y con Rappi.
#
# ## Fórmulas
#
# $i$ = PDV · $s(i)$ = su subcanal (CP) · $c(i)$ = su clúster NSE: la celda H3 res 9 que lo contiene ·
# $A_c=\{h:\ d(\text{centro}(h),\,\text{centro}(c))\le 300\ \text{m}\}$ = hexágonos H3 res 10 del buffer del clúster ·
# $k$ = nivel AMAI ($1$ = D/E, $2$ = D+, $3$ = C−, $4$ = C, $5$ = C+, $6$ = A/B).
#
# **Letra 1 (NSE del clúster)**
#
# $$HH_{ck}=\sum_{h\in A_c}HH_{hk}\qquad p_{ck}=\frac{HH_{ck}}{\sum_k HH_{ck}}\qquad N_c=\sum_{k=1}^{6}k\,p_{ck}$$
#
# $$\tilde N_c=Q_N\!\left(F_a(a_c)\right)\qquad N^*_c=(1-\lambda)\,N_c+\lambda\,\tilde N_c\qquad I^{N}_i=100\cdot\frac{N^*_{c(i)}}{\bar N^*_{s(i)}}\qquad L1_i=\begin{cases}H & \text{si } I^{N}_i\ge 100\\ L & \text{si } I^{N}_i<100\end{cases}$$
#
# $HH_{hk}$ = hogares 2025 del nivel $k$ en el hexágono $h$: cada manzana reparte sus hogares por **área** entre los hexágonos
# que toca (notebook 04), con la distribución NSE de su AGEB (microsimulación AMAI, notebook 01). $a_c$ = media del índice NSE
# AltScore (percentil 0-100, notebook 00b) de sus puntos a ≤ 300 m del centro; $\tilde N_c$ lo lleva a la escala de $N$ por
# cuantiles ($F_a$ = su distribución, $Q_N$ = cuantiles de $N$, en los clústeres con PDV objetivo) y $\lambda$ =
# `C.ALTSCORE_PESO_NSE`. Si el buffer tiene menos de `C.ALTSCORE_MIN_PUNTOS` puntos AltScore con índice, $N^*_c = N_c$.
#
# **Letra 2 (Ventas del PDV)**
#
# $$W_i=V_i+CP_i\qquad CP_i=\lfloor PQF_i\rfloor+\mathbb{1}\!\left[\,PQF_i-\lfloor PQF_i\rfloor\ge 0.6\,\right]\qquad C_i=\{j\text{ con venta}:\ d(i,j)\le 300\ \text{m}\}$$
#
# $$S_r=\frac{\text{botellas}_r}{b\cdot\text{meses de vida}_r}\qquad D_r=\{j\text{ con venta}:\ d(j,r)\le 300\ \text{m}\}\qquad R_i=\sum_{r:\ i\in D_r}\frac{S_r}{|D_r|}$$
#
# $$I^{V}_i=100\cdot\frac{W_i}{\overline{W}_{C_i}}\qquad I^{V*}_i=100\cdot\frac{W_i+R_i}{\overline{(W+R)}_{C_i}}\qquad L2_i=\begin{cases}H & \text{si } |C_i|\ge 2\ \text{y}\ I^{V*}_i>100\\ L & \text{en otro caso}\end{cases}$$
#
# $\bar N^*_s$ = media del subcanal sobre los PDV objetivo (con venta y con hogares en su clúster NSE). $V_i$ = venta media del
# PDV según el CP (`PotentialQuantitative_TotalPortafolio`, cajas/mes) y $PQF_i$ = su potencial
# (`PotentialQuantitativeFinal_TotalPortafolio`, cajas/mes que le faltan frente a su comparable), que entra en **cajas
# enteras** ($CP_i$: hacia abajo si el decimal es menor a `C.CP_UMBRAL_REDONDEO` = 0.6). La clase del CP (Very High → Low)
# sigue en el entregable. $C_i$ = su **clúster de venta**: los PDV con venta de su buffer, incluido él; "en otro caso" incluye al
# PDV que es el **único con venta** en su buffer. $S_r$ = venta de sueros e hidratación de la tienda Rappi **activa** $r$
# (≥ `C.RAPPI_MIN_PEDIDOS` pedidos en la ventana) en cajas por mes: $b$ = `C.RAPPI_BOTELLAS_CAJA` botellas por caja (un empaque
# múltiple cuenta sus botellas por precio). $S_r$ se reparte en partes iguales entre los PDV con venta de su radio ($D_r$) para
# no contar dos veces la misma venta, y la **media del clúster de venta también se mueve con Rappi** (regla del usuario,
# 2026-09-30): cada PDV se compara con sus vecinos con la misma vara, así que Rappi puede subir o bajar una letra.
#
# **QA con mapa en cada paso** (qué se hace y por qué): 1.1 NSE del punto · 1.2 variante INEGI por manzana · 1.3 clúster NSE ·
# 1.4 AltScore mueve el NSE · 1.5 Letra 1 · 2.1 venta media + CP · 2.2 clúster de venta · 2.3 Rappi mueve su venta ·
# 2.4 respaldo y sensibilidad · 2.5 Letra 2 · 3 letras juntas. Además, un **mapa interactivo**
# (`outputs/<ciudad>/<cliente>/06_mapa_qa_letras_*.html`, con filtro por subcanal) con los mismos pasos: clic en un hexágono o
# en un PDV dibuja su clúster NSE, su buffer y su ficha.
#
# **Entregables (carpeta del cliente):** Excel del canal Tradicional con la estructura pos_id · AltScore · INEGI · ventas (CP,
# Rappi, media) · clúster · letra 1 · letra 2 (y la acción Golden Stores), y la presentación (sección 6).
#
# **Reproducir:** `uv run python src/correr.py --pasos 06 merida` (necesita las salidas de 00, 00b, 00c, 01 y 04).

# %%
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import numpy as np
import pandas as pd
import geopandas as gpd
import h3
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from scipy import stats
from shapely.geometry import Point, Polygon
from IPython.display import display

import config as C
import altscore as A
import eda
import letras as LT
import mapas as MP
import rappi as R
from descargas import requisitos, descargar_fuente, extraer

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"Los datos de {C.CLIENTE} son de {C.CLIENTE_CIUDAD}; CIUDAD={C.CIUDAD}"
F04 = C.PROC / f"pdv_{C.CLIENTE}_hexagonos_{C.SLUG}.pkl"
F_HEX = C.PROC / f"hexagonos_h3r{C.H3_RES}_{C.CLIENTE}_{C.SLUG}.gpkg"
F_RAPPI = C.PROC / f"rappi_hidratacion_tiendas_{C.SLUG}.parquet"
F_RAPPI_LIN = C.PROC / f"rappi_hidratacion_lineas_{C.SLUG}.parquet"
F_ALT = C.PROC / f"altscore_{C.CLIENTE}_{C.SLUG}.parquet"
F_SEL = C.PROC / f"altscore_senales_{C.CLIENTE}_{C.SLUG}.csv"
requisitos({F04: "04_hexagonos_pdv", F_HEX: "04_hexagonos_pdv", C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet": "00_ventas_cp_validacion",
            C.PROC / f"ageb_{C.SLUG}.gpkg": "01_socioeconomico_merida", C.PROC / f"manzanas_{C.SLUG}.gpkg": "01_socioeconomico_merida",
            C.PROC / f"nse_ageb_{C.SLUG}.parquet": "01_socioeconomico_merida", F_RAPPI: "00c_rappi_eda",
            F_RAPPI_LIN: "00c_rappi_eda"})
eda.estilo()
pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
NSE = C.GRUPOS["NSE AMAI 2024"]
R300, BOT, THETA, FR = C.RADIO_PDV_M, C.RAPPI_BOTELLAS_CAJA, C.RAPPI_MIN_PEDIDOS, C.FRONTERA
RES_CL, LAM, MIN_ALT = C.NSE_CLUSTER_RES, C.ALTSCORE_PESO_NSE, C.ALTSCORE_MIN_PUNTOS
CMAP_NSE = LinearSegmentedColormap.from_list("nse", MP.SECUENCIAL)
CMAP_CENSO = LinearSegmentedColormap.from_list("censo", MP.AZULES)
print(f"{C.ZM_NOMBRE} · canal Tradicional · clúster NSE = hexágono H3 res {RES_CL} + buffer de {R300} m · AltScore mueve el NSE "
      f"(λ = {LAM:g}, ≥ {MIN_ALT} puntos) · Rappi mueve su venta ({BOT} botellas por caja; activa ≥ {THETA} pedidos) · frontera ±{FR}")

# %% [markdown]
# ## 0. Datos: PDV Tradicional del CP (04), clústeres NSE, hexágonos, AGEB, manzanas y tiendas Rappi (00c)
#
# Solo entran los PDV del **canal Tradicional** (abarrotes, independientes y Six; `src/cadenas.py`): se quitan los del canal
# Moderno (Modelorama y farmacias de cadena). Del PDV se usa **solo el CP**: id, nombre, subcanal, coordenadas, venta media
# (`PotentialQuantitative_TotalPortafolio`) y potencial (`PotentialQuantitativeFinal_TotalPortafolio`); "con venta" = venta
# media del CP > 0. Cada PDV cae en un **clúster NSE** (su hexágono H3 res 9) y el buffer de 300 m desde el centro del
# clúster da sus hogares.

# %%
tabla = pd.read_pickle(F04)
todos = tabla[""].reset_index(drop=True)
TRAD = todos.Canal.eq("Tradicional").to_numpy()                       # regla del usuario (2026-09-30): nada del canal Moderno
ids = todos[TRAD].copy().reset_index(drop=True)
ids["Subcanal"] = ids.Subcanal.str.replace("ABARRROTES", "ABARROTES")      # error de captura del CP (solo para mostrar)
hh04 = pd.DataFrame({c: tabla[(c, "HHs")].to_numpy(float)[TRAD] for c in NSE})   # hogares por nivel en el buffer del PDV (04)
pdv0 = pd.read_parquet(C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet").set_index("pos_id_cp")   # CP limpio (00)
hexg = gpd.read_file(F_HEX).set_index("hex")
hex_hh = hexg[[f"HHs_{c}" for c in NSE]].set_axis(NSE, axis=1)
ageb = gpd.read_file(C.PROC / f"ageb_{C.SLUG}.gpkg")
mzg = gpd.read_file(C.PROC / f"manzanas_{C.SLUG}.gpkg")
CRS = mzg.crs
rp = pd.read_parquet(F_RAPPI)
descargar_fuente(C.FUENTES["mg"])
D_MG = extraer(C.ARCHIVOS["mg"])
mun = gpd.read_file(next(D_MG.rglob(f"{C.ENT}mun.shp")))
mun = mun[mun.CVE_MUN.isin(C.ZM_MUNICIPIOS)].to_crs(CRS)
ageb_c = ageb.to_crs(CRS)
hex_c = hexg[["geometry"]].to_crs(CRS)
ref_zm = pd.read_parquet(C.PROC / f"nse_ageb_{C.SLUG}.parquet")
REF = pd.Series([ref_zm[f"HHs_{c}"].sum() / ref_zm["Total HHs"].sum() * 100 for c in NSE], index=NSE)     # % de la ZM (índice vs ZM)

MODERNO = todos.Cadena[~TRAD].value_counts()
ids["segmento"] = ids.Subcanal                                            # subcanal del CP (pos_subchannel)
ids["con_venta"] = ids.pos_id_cp.map(pdv0.PotentialQuantitative_TotalPortafolio).gt(0)   # con venta según el CP
ids["HH_area"] = ids["HHs en el área"]                                    # hogares del buffer del propio PDV (04): solo para el QA

# clúster NSE: la celda H3 res 9 del PDV; su centro es el punto NSE y el buffer de 300 m desde el centro da sus hogares
ids["cluster_nse"] = [h3.latlng_to_cell(a, b, RES_CL) for a, b in zip(ids.Latitud, ids.Longitud)]
cl = pd.DataFrame(index=pd.Index(sorted(ids.cluster_nse.unique()), name="cluster_nse"))
cl["lat"], cl["lon"] = LT.centros(cl.index)
areas_cl = LT.hexagonos_en_radio(cl.lat, cl.lon, R300, C.H3_RES)
hh_cl = LT.suma_area(hex_hh, areas_cl).set_axis(cl.index)                # hogares por nivel del buffer de cada clúster (sin redondear)
cl["hog"] = hh_cl.sum(axis=1)
ids["HH_cluster"] = ids.cluster_nse.map(cl.hog).to_numpy()
ids["con_nse"] = ids.HH_cluster > 0
ids["objetivo"] = ids.con_venta & ids.con_nse
cl["n_pdv"] = ids.groupby("cluster_nse").size()
cl["n_objetivo"] = ids[ids.objetivo].groupby("cluster_nse").size().reindex(cl.index).fillna(0).astype(int)
pts = gpd.GeoDataFrame(ids[["pos_id_cp"]], geometry=gpd.points_from_xy(ids.Longitud, ids.Latitud), crs=4326).to_crs(CRS)
UNIVERSO = (f"CP en la {C.ZM_NOMBRE}: {len(todos):,} PDV; se quitan {int((~TRAD).sum())} del canal Moderno ("
            + ", ".join(f"{k} {v}" for k, v in MODERNO.head(4).items()) + f"…) → {len(ids):,} Tradicional, {ids.con_venta.sum():,} con venta según el CP; "
            f"{ids.objetivo.sum():,} objetivo (con venta y hogares en su clúster NSE).")
print(UNIVERSO)
print(f"Clústeres NSE (H3 res {RES_CL}) con PDV: {len(cl):,} · hexágonos res 10 {len(hexg):,} · AGEB {len(ageb)} · manzanas {len(mzg):,} · "
      f"tiendas Rappi {len(rp)} ({int(rp.activa.sum())} activas, {int(rp.activa_sueros.sum())} activas en sueros)")
display(ids.groupby("segmento").agg(PDV=("pos_id_cp", "size"), con_venta=("con_venta", "sum"), objetivo=("objetivo", "sum"),
                                    clusteres=("cluster_nse", "nunique")))

# %% [markdown]
# ## 1. Letra 1 · NSE
# ### 1.1 NSE del punto geográfico
#
# **Qué se hace:** el punto es el **hexágono H3 res 10** donde está el PDV (≈ 0.015 km², del tamaño de una manzana). Su NSE
# es la distribución AMAI de los hogares que caen en ese hexágono; se resume en el **nivel NSE medio** $N=\sum_k k\,p_k$
# (1 = D/E … 6 = A/B). Al lado va el NSE de la **AGEB** que contiene al punto.
#
# **Por qué:** la microsimulación AMAI (notebook 01) es por AGEB, así que dentro de una AGEB todas las manzanas tienen la misma
# distribución. El hexágono solo cambia cuando mezcla manzanas de dos AGEB. Si el punto no tiene hogares (plaza, avenida
# comercial) su NSE no existe: por eso la letra no se toma del punto sino del **clúster NSE** (sección 1.3).

# %%
hexg["N"] = LT.nivel_medio(hex_hh)
hexg["abc"] = (hex_hh["A/B"] + hex_hh["C+"]) / hex_hh.sum(axis=1).replace(0, np.nan) * 100
ageb["N"] = LT.nivel_medio(ageb[[f"HHs_{c}" for c in NSE]].set_axis(NSE, axis=1))
ageb_c["N"] = ageb.N.to_numpy()
ids["N_punto"] = hexg.N.reindex(ids["Hexágono H3"]).to_numpy()
j = gpd.sjoin(pts, ageb_c[["CVEGEO", "N", "geometry"]], how="left", predicate="within")
j = j[~j.index.duplicated()]
ids["AGEB"], ids["N_ageb"] = j.CVEGEO.reindex(ids.index).to_numpy(), j.N.reindex(ids.index).to_numpy()
ob = ids[ids.objetivo]
ok_pa = ob.dropna(subset=["N_punto", "N_ageb"])
rho_pa = stats.spearmanr(ok_pa.N_punto, ok_pa.N_ageb)[0]
PUNTO = (f"De {len(ob):,} PDV objetivo, {ob.N_punto.notna().mean():.0%} tienen hogares en su hexágono y {ob.N_ageb.notna().mean():.0%} "
         f"caen en una AGEB urbana; NSE del punto vs NSE de su AGEB: ρ = {rho_pa:+.2f} (el hexágono hereda la AGEB salvo en sus bordes); "
         f"{ob.N_punto.isna().sum():,} PDV están en un hexágono sin hogares (zona comercial): su NSE sale del clúster.")
print(PUNTO)
display(ob.assign(punto=np.where(ob.N_punto.notna(), "con hogares", "sin hogares (comercial)")).groupby(["segmento", "punto"]).size().unstack(fill_value=0))

x0, y0, x1, y1 = pts[ids.objetivo].total_bounds
centro = pts[ids.objetivo].geometry.union_all().centroid
fig, ax = plt.subplots(1, 2, figsize=(15, 7.2))
ageb_c.plot(ax=ax[0], column="N", cmap=CMAP_NSE, vmin=1, vmax=6, edgecolor="white", lw=0.2)
pts[ids.objetivo].plot(ax=ax[0], color=eda.TINTA, markersize=1.2, alpha=0.5)
MP.fondo(ax[0], mun)
ax[0].set_xlim(x0 - 1500, x1 + 1500); ax[0].set_ylim(y0 - 1500, y1 + 1500)
ax[0].set_title("NSE por AGEB (nivel medio 1 = D/E … 6 = A/B) y PDV objetivo (puntos)")
sm = plt.cm.ScalarMappable(cmap=CMAP_NSE, norm=plt.Normalize(1, 6))
plt.colorbar(sm, ax=ax[0], shrink=0.5, label="nivel NSE medio")
cz_x, cz_y = centro.x, centro.y
cerca = hex_c.join(hexg[["N"]])
cerca = cerca[cerca.intersects(Point(cz_x, cz_y).buffer(1400))]
cerca.plot(ax=ax[1], column="N", cmap=CMAP_NSE, vmin=1, vmax=6, edgecolor="white", lw=0.3, missing_kwds={"color": eda.GRID})
ageb_c.boundary.plot(ax=ax[1], color=eda.TINTA, lw=1.2)
pz = pts[ids.objetivo & pts.intersects(Point(cz_x, cz_y).buffer(1400))]
pz.plot(ax=ax[1], color=eda.TINTA, markersize=16, edgecolor="white", lw=0.8)
MP.encuadre(ax[1], cz_x, cz_y, 1300)
ax[1].set_axis_off()
ax[1].set_title("Acercamiento: el NSE del punto es el de su hexágono (gris = sin hogares);\ncambia al cruzar el límite de AGEB (línea negra)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 1.2 Nos aseguramos del NSE: variante INEGI por manzana (Censo 2020) y variante digital (Rappi)
#
# **Qué se hace:** con los resultados del Censo 2020 **por manzana** (no por AGEB) se arma un índice de bienes y escolaridad:
# % de viviendas con auto, con computadora y con internet, y grado promedio de escolaridad. Cada variable se normaliza por
# rangos y el índice es su **primer componente principal** (mismo método que el índice AltScore del 00b), en percentil 0-100.
# Se lleva a cada hexágono por **área de manzana** ponderada por hogares y se compara con el NSE AMAI (ρ de Spearman con IC por
# bootstrap de bloques H3 res 7). Variante digital: en las tiendas Rappi, el % de pagos con Apple Pay y en efectivo contra el
# NSE INEGI de sus 300 m.
#
# **Por qué:** el NSE AMAI es un **modelo** (microsimulación por AGEB); el Censo por manzana es una **medición directa** y más
# fina. Si los dos coinciden, el NSE es confiable; donde no, el PDV se marca "NSE a revisar". Las manzanas con dato protegido
# ("*", pocas viviendas) quedan sin índice y no se imputan.

# %%
descargar_fuente(C.FUENTES["ageb"])
D_AGEB = extraer(C.ARCHIVOS["ageb"])
f_censo = next(D_AGEB.rglob("conjunto_de_datos_ageb_urbana_*_cpv2020.csv"))
COLS_CENSO = ["ENTIDAD", "MUN", "LOC", "AGEB", "MZA", "VIVPARH_CV", "VPH_AUTOM", "VPH_PC", "VPH_INTER", "GRAPROES"]
try:
    cz = pd.read_csv(f_censo, dtype=str, usecols=COLS_CENSO, encoding="utf-8-sig")
except UnicodeDecodeError:
    cz = pd.read_csv(f_censo, dtype=str, usecols=COLS_CENSO, encoding="latin-1")
cz = cz[(cz.MZA != "000") & cz.MUN.isin(C.ZM_MUNICIPIOS)].copy()
cz["CVEGEO"] = cz.ENTIDAD.str.zfill(2) + cz.MUN + cz.LOC + cz.AGEB + cz.MZA
v = cz[COLS_CENSO[5:]].apply(pd.to_numeric, errors="coerce")                  # "*" = dato protegido → NaN
viv = v.VIVPARH_CV.where(v.VIVPARH_CV > 0)
IND = pd.DataFrame({"% viviendas con auto": v.VPH_AUTOM / viv * 100, "% con computadora": v.VPH_PC / viv * 100,
                    "% con internet": v.VPH_INTER / viv * 100, "escolaridad promedio (años)": v.GRAPROES})
IND.iloc[:, :3] = IND.iloc[:, :3].clip(upper=100)
Zm = np.column_stack([A.rango_normal(IND[c]) for c in IND])
completas = ~np.isnan(Zm).any(axis=1)
val_, vec_ = np.linalg.eigh(np.corrcoef(Zm[completas], rowvar=False))
w_censo = vec_[:, -1] * np.sign(vec_[:, -1].sum())
puntaje = Zm @ w_censo
cz["indice_censo"] = np.nan
cz.loc[completas, "indice_censo"] = stats.rankdata(puntaje[completas]) / completas.sum() * 100
alfa_censo = A.alfa_cronbach(Zm[completas])
cargas_censo = pd.Series(w_censo, index=IND.columns)
g_ = cz.dropna(subset=["indice_censo"]).assign(AGEB=lambda t: t.CVEGEO.str[:13])
eta2 = 1 - ((g_.indice_censo - g_.groupby("AGEB").indice_censo.transform("mean")) ** 2).sum() / ((g_.indice_censo - g_.indice_censo.mean()) ** 2).sum()
print(f"Manzanas de la ZM: {len(cz):,} · con las 4 variables: {completas.mean():.0%} · α de Cronbach {alfa_censo:.2f} · el 1.er componente "
      f"explica {val_[-1] / val_.sum():.0%} · cargas {cargas_censo.round(2).to_dict()}")
print(f"η² del índice por AGEB = {eta2:.2f}: la AGEB explica {eta2:.0%} de la variación entre manzanas; el {1 - eta2:.0%} restante es "
      "variación DENTRO de la AGEB que el NSE AMAI (por AGEB) no ve.")

# índice del Censo por hexágono: manzanas repartidas por área y ponderadas por hogares (mismo reparto que el 04)
m_ = mzg[["CVEGEO", "hog", "geometry"]].merge(cz[["CVEGEO", "indice_censo"]], on="CVEGEO", how="left")
m_["area_mz"] = m_.geometry.area
pzs = gpd.overlay(m_, hex_c.reset_index(), how="intersection", keep_geom_type=True)
pzs["w"] = pzs.geometry.area / pzs.area_mz * pzs.hog.fillna(0)
pzs["w_ok"] = pzs.w.where(pzs.indice_censo.notna(), 0)
agg = pzs.assign(p=pzs.w_ok * pzs.indice_censo.fillna(0)).groupby("hex")[["w", "w_ok", "p"]].sum()
hexg["censo"] = (agg.p / agg.w_ok.replace(0, np.nan)).reindex(hexg.index)
hexg["censo_peso"] = agg.w_ok.reindex(hexg.index).fillna(0)
hexg["censo_cob"] = (agg.w_ok / agg.w.replace(0, np.nan)).reindex(hexg.index)
vh = hexg[(hexg["Total HHs"] >= 20) & (hexg.censo_cob >= 0.5)].dropna(subset=["N", "censo"])
rho_c, lo_c, hi_c = eda.spearman_bloques(vh.N, vh.censo, pd.Series([h3.cell_to_parent(h, 7) for h in vh.index], index=vh.index), B=300)
jm = gpd.sjoin_nearest(pts, m_[["CVEGEO", "indice_censo", "geometry"]], how="left", max_distance=50, distance_col="d_mz")
jm = jm[~jm.index.duplicated()]
ids["censo_punto"] = jm.indice_censo.reindex(ids.index).to_numpy()

# variante digital: pagos en tiendas Rappi con ≥ 30 pedidos vs NSE INEGI de sus 300 m
rpv = rp[rp.pedidos >= 30].copy()
rpv["N_300"] = LT.nivel_medio(LT.suma_area(hex_hh, LT.hexagonos_en_radio(rpv.lat, rpv.lon, R300, C.H3_RES))).to_numpy()
digital = []
for c_ in ["% pago Apple Pay", "% pago efectivo"]:
    d_ = rpv[[c_, "N_300"]].dropna()
    r_, p_ = stats.spearmanr(d_[c_], d_.N_300)
    lo_, hi_ = eda.spearman_ic(r_, len(d_))
    digital.append({"señal Rappi": c_, "tiendas": len(d_), "ρ con N INEGI (300 m)": r_, "IC95": f"[{lo_:+.2f}, {hi_:+.2f}]", "p": p_})
digital = pd.DataFrame(digital)
digital["signo esperado"] = digital["señal Rappi"].map({"% pago Apple Pay": +1, "% pago efectivo": -1})
digital["lectura"] = np.where((np.sign(digital["ρ con N INEGI (300 m)"]) == digital["signo esperado"]) & (digital.p < 0.05),
                              "confirma el NSE de INEGI", "no confirma (signo contrario o no significativa)")
VALIDEZ = (f"NSE AMAI vs índice del Censo por manzana en {len(vh):,} hexágonos: ρ = {rho_c:+.2f} (IC95 por bloques [{lo_c:+.2f}, {hi_c:+.2f}]). "
           f"Variante digital (Rappi, {len(rpv)} tiendas): " + "; ".join(f"{r['señal Rappi']} ρ = {r['ρ con N INEGI (300 m)']:+.2f} {r['IC95']} → {r.lectura}"
                                                                         for _, r in digital.iterrows()) + ".")
print(VALIDEZ)
display(digital.round(3))

fig, ax = plt.subplots(1, 3, figsize=(16, 5.4), gridspec_kw={"width_ratios": [1.1, 1.1, 0.9]})
zona = Point(cz_x, cz_y).buffer(1400)
mzz = m_[m_.intersects(zona)]
mzz.plot(ax=ax[0], column="indice_censo", cmap=CMAP_CENSO, vmin=0, vmax=100, edgecolor="white", lw=0.2, missing_kwds={"color": eda.GRID})
ageb_c.boundary.plot(ax=ax[0], color=eda.TINTA, lw=1.2)
MP.encuadre(ax[0], cz_x, cz_y, 1300); ax[0].set_axis_off()
ax[0].set_title("Índice del Censo por manzana (0-100; gris = dato protegido)\nvaría dentro de cada AGEB (línea negra)")
cerca.plot(ax=ax[1], column="N", cmap=CMAP_NSE, vmin=1, vmax=6, edgecolor="white", lw=0.3, missing_kwds={"color": eda.GRID})
ageb_c.boundary.plot(ax=ax[1], color=eda.TINTA, lw=1.2)
MP.encuadre(ax[1], cz_x, cz_y, 1300); ax[1].set_axis_off()
ax[1].set_title("NSE AMAI por hexágono (misma zona)\nel modelo es parejo dentro de la AGEB")
hb = ax[2].hexbin(vh.N, vh.censo, gridsize=35, cmap=CMAP_CENSO, mincnt=1)
ax[2].set(xlabel="nivel NSE medio AMAI del hexágono", ylabel="índice del Censo (0-100)",
          title=f"Hexágonos: ρ = {rho_c:+.2f} [{lo_c:+.2f}, {hi_c:+.2f}]")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 1.3 Clúster NSE: hexágono H3 res 9 + buffer de 300 m desde su centro
#
# **Qué se hace:** la ZM se divide en hexágonos H3 de res 9 (arista ≈ 174 m, ≈ 0.1 km²). El **centro** de cada hexágono con PDV
# es un punto NSE y su **buffer** son los hexágonos res 10 con centro a ≤ 300 m de él (≈ 19, ≈ 0.28 km²): se suman sus hogares
# por nivel y se calcula $N_c$. Cada PDV cae en un solo hexágono y **toma el NSE de su clúster**; como ningún PDV queda a más
# de ~210 m del centro de su hexágono, el buffer siempre lo contiene. Los hogares vienen de manzanas repartidas **por área**
# (nada queda fuera por usar un punto). También se calculan el % ABC+ (A/B + C+), el índice del Censo del buffer y el **NSE
# predominante** (el grupo con más hogares: bajo D+ y D/E, medio C y C−, alto C+ y A/B).
#
# **Por qué:** regla del usuario (2026-09-30): el NSE es del **clúster**, no del PDV, y los hexágonos (en vez de centroides de
# AGEB) funcionan igual en geografías complejas: una AGEB grande o alargada tiene su centroide lejos de sus PDV; el hexágono
# siempre es chico y regular. Así el PDV no decide su primera letra (la comparte con su hexágono) y sí decide la segunda (su
# venta y la venta Rappi que recibe). Los mapas muestran cuatro clústeres reales: el hexágono (azul), su buffer (punteado), los
# hexágonos res 10 del buffer (color fuerte) y los PDV que lo comparten (estrellas).

# %%
GRUPO_NSE = {"bajo": ["D+", "D/E"], "medio": ["C", "C-"], "alto": ["C+", "A/B"]}      # agrupación AMAI de mercado
cl["N"] = LT.nivel_medio(hh_cl)
cl["abc"] = (hh_cl["A/B"] + hh_cl["C+"]) / cl.hog.replace(0, np.nan) * 100
cw = LT.suma_area(hexg[["censo_peso"]], areas_cl).censo_peso.to_numpy()
cp_ = LT.suma_area((hexg.censo.fillna(0) * hexg.censo_peso).to_frame("p"), areas_cl).p.to_numpy()
cl["censo"] = cp_ / np.where(cw > 0, cw, np.nan)
parte = pd.DataFrame({g_: hh_cl[cs].sum(axis=1) for g_, cs in GRUPO_NSE.items()}).div(cl.hog.replace(0, np.nan), axis=0)
cl["clase"] = parte.fillna(-1).idxmax(axis=1).where(parte.notna().all(axis=1))
cl["clase_pct"] = parte.max(axis=1) * 100
for g_ in GRUPO_NSE:
    cl[f"p_{g_}"] = parte[g_] * 100
for c_, k_ in [("N_inegi", "N"), ("abc", "abc"), ("censo_area", "censo"), ("nse_clase", "clase"), ("nse_clase_pct", "clase_pct"),
               ("nse_bajo", "p_bajo"), ("nse_medio", "p_medio"), ("nse_alto", "p_alto"), ("n_cluster_nse", "n_pdv")]:
    ids[c_] = ids.cluster_nse.map(cl[k_]).to_numpy()
hh = hh_cl.reindex(ids.cluster_nse).reset_index(drop=True)                  # hogares por nivel del clúster de cada PDV
fc, lc = np.radians(ids.cluster_nse.map(cl.lat).to_numpy(float)), np.radians(ids.cluster_nse.map(cl.lon).to_numpy(float))
fp, lp = np.radians(ids.Latitud.to_numpy(float)), np.radians(ids.Longitud.to_numpy(float))
ids["dist_centro_m"] = 2 * 6_371_000 * np.arcsin(np.sqrt(np.sin((fc - fp) / 2) ** 2 + np.cos(fp) * np.cos(fc) * np.sin((lc - lp) / 2) ** 2))
ids["N_pdv"] = LT.nivel_medio(hh04)                    # QA: NSE del buffer del propio PDV (04; la regla anterior)
ids["pocos_hogares"] = ids.con_nse & (ids.HH_cluster < 100)
assert (ids.dist_centro_m <= R300).all(), "todo PDV debe quedar dentro del buffer de su clúster"
ob = ids[ids.objetivo]
clo = cl[cl.n_objetivo > 0]
rho_cb = stats.spearmanr(ob.N_inegi, ob.N_pdv, nan_policy="omit")[0]
CLUSTER_NSE = (f"{len(clo):,} clústeres NSE (hexágonos H3 res {RES_CL}) tienen PDV objetivo: mediana {clo.n_objetivo.median():.0f} PDV por clúster "
               f"(p90 {clo.n_objetivo.quantile(0.9):.0f}, máximo {clo.n_objetivo.max()}); {(clo.n_objetivo == 1).mean():.0%} tienen un solo PDV. "
               f"El PDV más lejano queda a {ids.dist_centro_m.max():.0f} m del centro de su hexágono (mediana {ids.dist_centro_m.median():.0f} m): "
               f"el buffer de {R300} m siempre lo contiene. NSE del clúster vs NSE del buffer del propio PDV: ρ = {rho_cb:.2f}; "
               f"{int((ids.con_venta & ~ids.con_nse).sum())} PDV con venta quedan en clústeres sin hogares a {R300} m "
               f"y {ob.pocos_hogares.mean():.1%} de los objetivo tienen < 100 hogares en su clúster (NSE más ruidoso).")
print(CLUSTER_NSE)
PREDOMINANTE = ("NSE predominante del clúster (el grupo con más hogares del buffer), en los PDV objetivo: " + ", ".join(
    f"{k} {v:.0%}" for k, v in ob.nse_clase.value_counts(normalize=True).reindex(list(GRUPO_NSE)).fillna(0).items())
    + f". El nivel NSE (media de 1 a 6) promedia hogares mezclados: {ob.N_inegi.between(2.5, 4.5).mean():.0%} de los PDV cae entre 2.5 y 4.5, "
      "por eso casi todo se lee 'medio'.")
print(PREDOMINANTE)
display(ob.groupby("segmento").agg(PDV=("pos_id_cp", "size"), clusteres=("cluster_nse", "nunique"), **{"N INEGI medio": ("N_inegi", "mean")},
                                   **{"% bajo": ("nse_clase", lambda s: (s == "bajo").mean() * 100)},
                                   **{"% medio": ("nse_clase", lambda s: (s == "medio").mean() * 100)},
                                   **{"% alto": ("nse_clase", lambda s: (s == "alto").mean() * 100)}).round(1))


def celda_poligono(c):
    """Polígono (EPSG:4326) de una celda H3."""
    return Polygon([(lo, la) for la, lo in h3.cell_to_boundary(c)])


cl_geo = gpd.GeoSeries([celda_poligono(c) for c in cl.index], index=cl.index, crs=4326).to_crs(CRS)
cl_ctr = gpd.GeoSeries(gpd.points_from_xy(cl.lon, cl.lat), index=cl.index, crs=4326).to_crs(CRS)


def panel_cluster(ax, c, titulo):
    """Clúster NSE: su hexágono res 9 (azul), el buffer de 300 m desde su centro (punteado), los hexágonos res 10 del buffer
    (color fuerte; fuera, tenues), las manzanas y los PDV del hexágono (estrellas; los demás PDV en gris)."""
    ctr = cl_ctr.loc[c]
    marco = ctr.buffer(R300 * 1.8)
    hx = hex_c.join(hexg[["N"]])
    hx = hx[hx.intersects(marco)]
    dentro = hx.index.isin(areas_cl[cl.index.get_loc(c)])
    hx[~dentro].plot(ax=ax, column="N", cmap=CMAP_NSE, vmin=1, vmax=6, alpha=0.25, edgecolor="white", lw=0.3, missing_kwds={"color": eda.GRID, "alpha": 0.3})
    hx[dentro].plot(ax=ax, column="N", cmap=CMAP_NSE, vmin=1, vmax=6, alpha=0.95, edgecolor=eda.TINTA_2, lw=0.5, missing_kwds={"color": eda.GRID})
    mzg[mzg.intersects(marco)].boundary.plot(ax=ax, color="white", lw=0.35)
    gpd.GeoSeries([cl_geo.loc[c]], crs=CRS).boundary.plot(ax=ax, color=MP.COLOR_L1["H"], lw=2.4)
    gpd.GeoSeries([ctr.buffer(R300)], crs=CRS).boundary.plot(ax=ax, color=eda.TINTA, lw=1.5, ls="--")
    ax.plot(ctr.x, ctr.y, marker="+", color=MP.COLOR_L1["H"], ms=13, mew=2.2, zorder=7)
    miembro = ids.cluster_nse.eq(c).to_numpy()
    pts[pts.geometry.within(marco).to_numpy() & ~miembro].plot(ax=ax, color=eda.MUTED, markersize=12, alpha=0.75, zorder=4)
    pts[miembro].plot(ax=ax, marker="*", color=eda.TINTA, markersize=150, edgecolor="white", lw=0.6, zorder=6)
    MP.encuadre(ax, ctr.x, ctr.y, R300 * 1.55)
    ax.set_axis_off()
    r = cl.loc[c]
    ax.set_title(f"{titulo}\n{int(r.n_pdv)} PDV en el hexágono · {r.hog:,.0f} hogares en el buffer · N {r.N:.2f} ({r.clase})", fontsize=9)


def panel_buffer(ax, i, titulo):
    """Buffer de 300 m del PDV i (su clúster de venta): hexágonos por NSE de fondo, manzanas, el radio y el PDV (estrella)."""
    x, y = pts.geometry.iloc[i].x, pts.geometry.iloc[i].y
    marco = Point(x, y).buffer(R300 * 1.8)
    hx = hex_c.join(hexg[["N"]])
    hx[hx.intersects(marco)].plot(ax=ax, column="N", cmap=CMAP_NSE, vmin=1, vmax=6, alpha=0.35, edgecolor="white", lw=0.3,
                                  missing_kwds={"color": eda.GRID, "alpha": 0.3})
    mzg[mzg.intersects(marco)].boundary.plot(ax=ax, color="white", lw=0.35)
    gpd.GeoSeries([Point(x, y).buffer(R300)], crs=CRS).boundary.plot(ax=ax, color=eda.TINTA, lw=1.6, ls="--")
    ax.plot(x, y, marker="*", color=eda.TINTA, ms=15, mec="white", mew=1, zorder=6)
    MP.encuadre(ax, x, y, R300 * 1.55)
    ax.set_axis_off()
    ax.set_title(f"{titulo}\n{str(ids.Nombre.iloc[i])[:34]}", fontsize=9)


cands = cl[(cl.n_objetivo >= 2) & cl.N.notna()]
n_ageb = ids.groupby("cluster_nse").AGEB.nunique()
mezcla = cands[cands.index.isin(n_ageb[n_ageb >= 2].index)]
ejemplos_1 = {"NSE alto (p90)": (cands.N - cands.N.quantile(0.9)).abs().idxmin(),
              "NSE bajo (p10)": (cands.N - cands.N.quantile(0.1)).abs().idxmin(),
              "El clúster con más PDV": cl.n_objetivo.idxmax(),
              "Sus PDV están en dos AGEB": mezcla.n_objetivo.idxmax() if len(mezcla) else cands.index[0]}
fig, ax = plt.subplots(2, 2, figsize=(12.5, 13))
for a_, (t_, c_) in zip(ax.flat, ejemplos_1.items()):
    panel_cluster(a_, c_, t_)
fig.colorbar(plt.cm.ScalarMappable(cmap=CMAP_NSE, norm=plt.Normalize(1, 6)), ax=ax, shrink=0.45, label="nivel NSE medio del hexágono res 10")
fig.suptitle("1.3 Clúster NSE: hexágono H3 res 9 (azul) y su buffer de 300 m desde el centro (punteado); hexágonos res 10 del buffer "
             "(color fuerte) y los PDV que lo comparten (estrellas)", x=0.02, ha="left", fontsize=10)
plt.show()

# %% [markdown]
# ### 1.4 AltScore mueve el NSE del clúster
#
# **Qué se hace:** el índice NSE AltScore (percentil 0-100 del 00b: PC1 de sus proxies digitales, elegidos por análisis de
# ítems en la ZM) de los puntos AltScore que caen en el buffer de 300 m del **centro** de cada clúster; su media es $a_c$. Se
# lleva a la escala de $N$ por **cuantiles** ($\tilde N_c$ = el valor de $N$ con el mismo percentil: los dos quedan con la misma
# distribución) y **mueve el NSE**: $N^*_c = (1-\lambda)\,N_c + \lambda\,\tilde N_c$ con $\lambda$ = `C.ALTSCORE_PESO_NSE`,
# solo en clústeres con al menos `C.ALTSCORE_MIN_PUNTOS` puntos AltScore con índice (si no, $N^*_c = N_c$). Se valida contra
# INEGI en el mismo buffer (ρ con IC por bloques H3 res 7), se mide si AltScore **agrega** información al predecir el índice
# del Censo por manzana (medición directa) y se prueba la Letra 1 con otros pesos.
#
# **Por qué:** regla del usuario (2026-09-30): AltScore es una variable socioeconómica más y **sí mueve el NSE**, igual que
# Rappi mueve la venta. INEGI pesa más ($1-\lambda$) porque el Censo por manzana lo confirma y AltScore todavía es una escala
# corta (pocos proxies, α bajo en el 00b); el peso queda por validar con el usuario. Los mismos promedios dan las señales
# AltScore del clúster que van al entregable.

# %%
alt = pd.read_parquet(F_ALT) if F_ALT.exists() else pd.DataFrame()
alt_sel = pd.read_csv(F_SEL) if F_SEL.exists() else pd.DataFrame(columns=["señal", "decisión", "nombre"])
loc_alt = A.ubicacion(alt) if len(alt) else {}
USA_ALTSCORE = bool(loc_alt.get("lat") and loc_alt.get("lon") and "indice_nse_altscore" in alt)
PROX_ALT = alt_sel.loc[alt_sel["decisión"].eq("índice NSE"), "nombre"].tolist()
ALT_SEN = [c for c in alt.columns if c not in {"pos_id", "indice_nse_altscore", "zonas_por_vector_digital", *[v for v in loc_alt.values() if v]}]
cl["alt"], cl["alt_puntos"] = np.nan, 0
if USA_ALTSCORE:
    alt = alt.dropna(subset=[loc_alt["lat"], loc_alt["lon"]]).reset_index(drop=True)
    cerca_alt = R.en_radio(cl.lat.to_numpy(), cl.lon.to_numpy(), alt[loc_alt["lat"]].to_numpy(float), alt[loc_alt["lon"]].to_numpy(float), R300)
    Va = alt[["indice_nse_altscore", *ALT_SEN]].to_numpy(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)                     # buffer sin dato en una señal → NaN
        M_alt = np.array([np.nanmean(Va[i], axis=0) if len(i) else np.full(Va.shape[1], np.nan) for i in cerca_alt])
    cl["alt"] = M_alt[:, 0]
    for k_, c_ in enumerate(ALT_SEN):
        cl[f"alt_{c_}"] = M_alt[:, k_ + 1]
    cl["alt_puntos"] = [int(np.isfinite(Va[i, 0]).sum()) for i in cerca_alt]
cl["alt_ok"] = cl.alt_puntos >= MIN_ALT
base_cl = (cl.n_objetivo > 0) & cl.N.notna() & cl.alt_ok & cl.alt.notna()   # base del mapeo por cuantiles
cl["N_alt"] = (LT.a_escala(cl.alt.where(cl.alt_ok & cl.N.notna()), cl.N[base_cl], x_base=cl.alt[base_cl]) if base_cl.sum() > 30
               else pd.Series(np.nan, index=cl.index))
cl["N_star"] = LT.mover_nse(cl.N, cl.N_alt, LAM)
L1_censo = LT.letra_media(ids.censo_area, ids.segmento, ids.objetivo)       # letra del Censo por manzana (variante de la 1.5)
PESOS = sorted({0, 0.1, 0.25, 0.5, 0.75, 1.0, LAM})
L1_por_peso = {w_: LT.letra(LT.indice(ids.cluster_nse.map(LT.mover_nse(cl.N, cl.N_alt, w_)), ids.segmento, ids.objetivo)).where(ids.objetivo)
               for w_ in PESOS}
m_ok = ids.objetivo & L1_por_peso[0].notna()
m_cz = m_ok & L1_censo.notna()
sens_alt = pd.DataFrame([{"peso de AltScore (λ)": w_, "% L1 = H": (L_[m_ok] == "H").mean() * 100,
                          "PDV que suben a H": int(((L_ == "H") & (L1_por_peso[0] == "L"))[m_ok].sum()),
                          "PDV que bajan a L": int(((L_ == "L") & (L1_por_peso[0] == "H"))[m_ok].sum()),
                          "κ con la letra del Censo": eda.kappa_cohen(L_[m_cz], L1_censo[m_cz])} for w_, L_ in L1_por_peso.items()])
sens_alt["PDV que cambian"] = sens_alt["PDV que suben a H"] + sens_alt["PDV que bajan a L"]
sens_alt["% que cambian"] = sens_alt["PDV que cambian"] / max(m_ok.sum(), 1) * 100
sa = sens_alt.set_index("peso de AltScore (λ)")
if USA_ALTSCORE and base_cl.sum() > 30:
    bl7 = pd.Series([h3.cell_to_parent(h, 7) for h in cl.index[base_cl]], index=cl.index[base_cl])
    rho_a, lo_a, hi_a = eda.spearman_bloques(cl.alt[base_cl], cl.N[base_cl], bl7, B=300)
    vc = cl[base_cl].dropna(subset=["censo"])                                # ¿AltScore agrega algo a INEGI para predecir el Censo?

    def betas(t):
        X_ = np.column_stack([np.ones(len(t)), A.rango_normal(t.N), A.rango_normal(t.alt)])
        return np.linalg.lstsq(X_, A.rango_normal(t.censo), rcond=None)[0][1:]

    b_inegi, b_alt = betas(vc)
    rng = np.random.default_rng(eda.SEMILLA)
    blq = pd.Series([h3.cell_to_parent(h, 7) for h in vc.index]).to_numpy()
    grupos = [np.flatnonzero(blq == b_) for b_ in pd.unique(blq)]
    bs = np.array([betas(vc.iloc[np.concatenate([grupos[k] for k in rng.integers(0, len(grupos), len(grupos))])]) for _ in range(300)])
    lo_b, hi_b = np.percentile(bs[:, 1], [2.5, 97.5])
    ALT_NSE = (f"AltScore: {len(alt):,} puntos en la ZM; {cl.alt_ok[cl.n_objetivo > 0].mean():.0%} de los clústeres con PDV objetivo tienen ≥ {MIN_ALT} "
               f"puntos con índice en su buffer (mediana {np.median(cl.alt_puntos[cl.n_objetivo > 0]):.0f}). Índice AltScore vs NSE INEGI del clúster: "
               f"ρ = {rho_a:+.2f} (IC95 bloques [{lo_a:+.2f}, {hi_a:+.2f}], {int(base_cl.sum()):,} clústeres). Para predecir el índice del Censo por "
               f"manzana, INEGI pesa β = {b_inegi:+.2f} y AltScore β = {b_alt:+.2f} (IC95 [{lo_b:+.2f}, {hi_b:+.2f}]): "
               + ("AltScore agrega información propia" if lo_b > 0 else "AltScore no agrega a lo que el Censo ya confirma de INEGI; es otra lectura (digital, 2025-2026)")
               + f". Con λ = {LAM:g} AltScore cambia {int(sa.loc[LAM, 'PDV que cambian'])} Letras 1 ({int(sa.loc[LAM, 'PDV que suben a H'])} suben, "
               f"{int(sa.loc[LAM, 'PDV que bajan a L'])} bajan); con λ = 0.5, {int(sa.loc[0.5, 'PDV que cambian'])}; con λ = 1 (solo AltScore), "
               f"{int(sa.loc[1.0, 'PDV que cambian'])}.")
else:
    rho_a = lo_a = hi_a = b_inegi = b_alt = lo_b = hi_b = np.nan
    ALT_NSE = "AltScore no mueve el NSE: su exportación no trae ubicación (lat/lon) o no hay suficientes clústeres con índice (notebook 00b)."
print(ALT_NSE)
display(sens_alt.round(2))

fig, ax = plt.subplots(1, 3, figsize=(17, 5.8), gridspec_kw={"width_ratios": [1.3, 1, 1]})
MP.fondo(ax[0], mun, agebs=ageb_c)
cg = gpd.GeoDataFrame(cl[["alt", "alt_ok", "n_objetivo"]], geometry=cl_geo)
cg = cg[cg.alt_ok & (cg.n_objetivo > 0)]
if len(cg):
    cg.plot(ax=ax[0], column="alt", cmap=CMAP_CENSO, vmin=0, vmax=100, lw=0)
    plt.colorbar(plt.cm.ScalarMappable(cmap=CMAP_CENSO, norm=plt.Normalize(0, 100)), ax=ax[0], shrink=0.6, label="índice NSE AltScore del buffer (0-100)")
ax[0].set_xlim(x0 - 1500, x1 + 1500); ax[0].set_ylim(y0 - 1500, y1 + 1500)
ax[0].set_title(f"Clústeres NSE con ≥ {MIN_ALT} puntos AltScore en su buffer (color = índice AltScore)", fontsize=10)
bc = cl[base_cl]
if len(bc):
    ax[1].scatter(bc.N, bc.N_alt, s=np.clip(bc.n_objetivo * 6, 6, 80), alpha=0.35, color=eda.PALETA[0], edgecolor="none")
    ax[1].plot([1, 6], [1, 6], color=eda.MUTED, ls="--", lw=1)
    ax[1].set(xlabel="nivel NSE INEGI del clúster (N)", ylabel="AltScore en la escala de N (Ñ)", xlim=(1.5, 5.8), ylim=(1.5, 5.8),
              title=f"INEGI vs AltScore por clúster: ρ = {rho_a:+.2f} [{lo_a:+.2f}, {hi_a:+.2f}]")
ax[2].bar(sens_alt["peso de AltScore (λ)"].astype(str), sens_alt["PDV que suben a H"], color=MP.COLOR_L1["H"], label="suben a H")
ax[2].bar(sens_alt["peso de AltScore (λ)"].astype(str), -sens_alt["PDV que bajan a L"], color=MP.COLOR_L1["L"], label="bajan a L")
ax[2].axhline(0, color=eda.TINTA, lw=0.8)
ax[2].set(xlabel="peso de AltScore λ (0 = solo INEGI · 1 = solo AltScore)", ylabel="PDV que cambian de Letra 1",
          title=f"Sensibilidad del peso (base λ = {LAM:g})")
ax[2].legend(fontsize=8)
plt.suptitle("1.4 AltScore mueve el NSE del clúster: N* = (1 − λ)·N INEGI + λ·AltScore en la escala de N", x=0.01, ha="left")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 1.5 Índice NSE y Letra 1 (sin y con AltScore, con concordancia entre variantes)
#
# **Qué se hace:** $I^N_i = 100\,N^*_{c(i)}/\bar N^*_{s(i)}$ con la media de los PDV objetivo de su subcanal; $L1 = H$ si
# $I^N \ge 100$. La **Letra 1 sin AltScore** usa $N_c$ (solo INEGI) con la misma regla. Se marca **frontera** si
# $|I^N - 100| \le$ 10. Para **asegurar** la letra se recalcula con cada variante (misma regla: H si el valor ≥ media del
# subcanal) y se mide la concordancia con κ de Cohen contra la letra INEGI y contra la final: % ABC+, índice del Censo del
# clúster, NSE del punto, NSE de la AGEB, el buffer del propio PDV (la regla anterior), buffers de 200 y 400 m desde el centro,
# AltScore solo y la cantidad de hogares (sin NSE).
#
# **Por qué:** una letra que cambia con cualquier definición razonable no sirve para decidir; una que se sostiene sí. "NSE
# confirmado" = la letra coincide con la del Censo por manzana (medición directa, independiente del modelo AMAI y de AltScore).

# %%
for c_, k_ in [("alt_cluster", "alt"), ("alt_puntos", "alt_puntos"), ("N_alt", "N_alt"), ("N", "N_star"),
               *[(f"alt_{s_}", f"alt_{s_}") for s_ in ALT_SEN if f"alt_{s_}" in cl]]:
    ids[c_] = ids.cluster_nse.map(cl[k_]).to_numpy()                        # N = N* del clúster: INEGI movido por AltScore
ids["I_N"] = LT.indice(ids.N, ids.segmento, ids.objetivo)
ids["L1"] = LT.letra(ids.I_N)
ids["I_N_inegi"] = LT.indice(ids.N_inegi, ids.segmento, ids.objetivo)
ids["L1_sin_alt"] = LT.letra(ids.I_N_inegi)
assert (ids.L1[ids.objetivo] == L1_por_peso[LAM][ids.objetivo]).all(), "la Letra 1 y su sensibilidad usan la misma regla"
ids["frontera_L1"] = (ids.I_N - 100).abs() <= FR
ids["sube_por_alt"] = ids.L1.eq("H") & ids.L1_sin_alt.eq("L")
ids["baja_por_alt"] = ids.L1.eq("L") & ids.L1_sin_alt.eq("H")
ids["cambia_por_alt"] = ids.sube_por_alt | ids.baja_por_alt
variantes = {"Letra 1 sin AltScore (solo INEGI)": ids.L1_sin_alt,
             "% ABC+ del clúster (INEGI)": LT.letra_media(ids.abc, ids.segmento, ids.objetivo),
             "Índice del Censo por manzana (clúster)": L1_censo,
             "NSE del punto (hexágono res 10 del PDV)": LT.letra_media(ids.N_punto, ids.segmento, ids.objetivo),
             "NSE de la AGEB del punto": LT.letra_media(ids.N_ageb, ids.segmento, ids.objetivo),
             f"Buffer de {R300} m del propio PDV (sin clúster)": LT.letra(LT.indice(ids.N_pdv, ids.segmento, ids.objetivo))}
for r_ in (200, 400):
    hh_r = LT.suma_area(hex_hh, LT.hexagonos_en_radio(cl.lat, cl.lon, r_, C.H3_RES)).set_axis(cl.index)
    variantes[f"Buffer de {r_} m desde el centro (en vez de {R300})"] = LT.letra(LT.indice(ids.cluster_nse.map(LT.nivel_medio(hh_r)), ids.segmento, ids.objetivo))
if USA_ALTSCORE:
    variantes["AltScore del clúster (solo)"] = LT.letra_media(ids.alt_cluster.where(ids.alt_puntos >= MIN_ALT), ids.segmento, ids.objetivo)
variantes["Hogares del clúster (cantidad, sin NSE)"] = LT.letra(LT.indice(ids.HH_cluster, ids.segmento, ids.objetivo))
conc = []
for k_, v_ in variantes.items():
    fila = {"variante": k_, "PDV comparables": int((ids.objetivo & v_.notna() & ids.L1.notna()).sum())}
    for nom, ref_ in [("INEGI", ids.L1_sin_alt), ("final", ids.L1)]:
        m = ids.objetivo & v_.notna() & ref_.notna()
        fila[f"% misma letra ({nom})"] = (v_[m] == ref_[m]).mean() * 100
        fila[f"κ ({nom})"] = eda.kappa_cohen(ref_[m], v_[m])
    conc.append(fila)
conc = pd.DataFrame(conc)
conc["lectura (final)"] = pd.cut(conc["κ (final)"], [-1, 0.2, 0.4, 0.6, 0.8, 1.01], labels=["pobre", "regular", "moderado", "bueno", "casi perfecto"])
ids["L1_censo"] = L1_censo
ESTABLES = ["% ABC+ del clúster (INEGI)", "Índice del Censo por manzana (clúster)", f"Buffer de 200 m desde el centro (en vez de {R300})",
            f"Buffer de 400 m desde el centro (en vez de {R300})"]
ids["variantes_iguales"] = sum((variantes[k] == ids.L1).astype(int) for k in ESTABLES).where(ids.L1.notna())   # 0-4: estabilidad de la letra
ids["nse_confirmado"] = np.where(ids.L1.isna() | ids.L1_censo.isna(), None, ids.L1 == ids.L1_censo)
ob = ids[ids.objetivo]
m_c = ob.L1_censo.notna()
conf_final, conf_inegi = (ob.L1[m_c] == ob.L1_censo[m_c]).mean(), (ob.L1_sin_alt[m_c] == ob.L1_censo[m_c]).mean()
display(conc.round(3))
LETRA1 = (f"L1 = H en {(ob.L1 == 'H').mean():.0%} de los PDV objetivo (sin AltScore {(ob.L1_sin_alt == 'H').mean():.0%}); AltScore cambia "
          f"{int(ob.cambia_por_alt.sum())} letras ({int(ob.sube_por_alt.sum())} suben, {int(ob.baja_por_alt.sum())} bajan; λ = {LAM:g}); frontera ±{FR}: "
          f"{ob.frontera_L1.mean():.0%}; confirmada por el Censo por manzana en {conf_final:.0%} (la letra solo INEGI, en {conf_inegi:.0%}); igual en "
          f"las 4 variantes principales (ABC+, Censo, 200 y 400 m) en {(ob.variantes_iguales == 4).mean():.0%}. κ contra la letra INEGI: "
          + ", ".join(f"{r.variante} {r['κ (INEGI)']:.2f}" for _, r in conc.iloc[1:].iterrows()) + ".")
print(LETRA1)
display(ob.groupby("segmento").agg(PDV=("L1", "size"), **{"% L1 = H": ("L1", lambda s: (s == "H").mean() * 100)},
                                   **{"% L1 = H sin AltScore": ("L1_sin_alt", lambda s: (s == "H").mean() * 100)},
                                   **{"N final medio": ("N", "mean")}, **{"AltScore cambia": ("cambia_por_alt", "sum")},
                                   **{"% frontera": ("frontera_L1", "mean")}).round(2))

fig, ax = plt.subplots(1, 2, figsize=(16, 7.5), gridspec_kw={"width_ratios": [1.5, 1]})
hx_all = hex_c.join(hexg[["N"]])
hx_all.plot(ax=ax[0], column="N", cmap=CMAP_NSE, vmin=1, vmax=6, alpha=0.35, lw=0)
g = pts[ids.objetivo].join(ids[["L1", "sube_por_alt", "baja_por_alt"]])
for l_, gg in g.groupby("L1"):
    gg.plot(ax=ax[0], color=MP.COLOR_L1[l_], markersize=5, alpha=0.85, label=f"L1 = {l_} ({len(gg):,})")
g[g.sube_por_alt].plot(ax=ax[0], color="none", edgecolor=eda.TINTA, markersize=40, lw=0.9, label=f"sube a H por AltScore ({int(g.sube_por_alt.sum())})")
g[g.baja_por_alt].plot(ax=ax[0], color="none", edgecolor=eda.PALETA[7], markersize=40, lw=0.9, label=f"baja a L por AltScore ({int(g.baja_por_alt.sum())})")
MP.fondo(ax[0], mun)
ax[0].set_xlim(x0 - 1500, x1 + 1500); ax[0].set_ylim(y0 - 1500, y1 + 1500)
ax[0].legend(loc="lower left", markerscale=2)
ax[0].set_title("Letra 1 por PDV (azul = NSE de su clúster ≥ media de su subcanal) sobre el NSE por hexágono", fontsize=10)
cc_ = conc.iloc[1:].sort_values("κ (INEGI)")
yy_ = np.arange(len(cc_))
ax[1].barh(yy_ - 0.2, cc_["κ (INEGI)"], height=0.38, color=[MP.COLOR_L1["H"] if k >= 0.6 else eda.MUTED for k in cc_["κ (INEGI)"]], label="vs letra INEGI")
ax[1].barh(yy_ + 0.2, cc_["κ (final)"], height=0.38, color=eda.PALETA[6], alpha=0.55, label="vs letra final (con AltScore)")
ax[1].set_yticks(yy_, cc_.variante)
for k_, (vk, pk) in enumerate(zip(cc_["κ (INEGI)"], cc_["% misma letra (INEGI)"])):
    ax[1].text(max(vk, 0) + 0.01, k_ - 0.2, f"{vk:.2f} · {pk:.0f}% igual", va="center", fontsize=7.5)
ax[1].axvline(0.6, color=eda.MUTED, ls="--", lw=1)
ax[1].set_xlim(-0.05, 1.2)
ax[1].legend(fontsize=8, loc="lower right")
ax[1].set_title("¿La Letra 1 se sostiene? κ de Cohen contra cada variante (≥ 0.6 = buena)")
ax[1].tick_params(axis="y", labelsize=8)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 2. Letra 2 · Ventas del PDV
# ### 2.1 Venta media + CP del PDV (los dos del CP)
#
# **Qué se hace:** $V_i$ = **venta media** del PDV según el CP (`PotentialQuantitative_TotalPortafolio`, cajas/mes) y $CP_i$ =
# su **potencial** (`PotentialQuantitativeFinal_TotalPortafolio`: cajas/mes que le faltan frente a su PDV comparable) en
# **cajas enteras**, hacia abajo si el decimal es menor a 0.6. El valor con que se compara cada PDV es $W_i = V_i + CP_i$
# (regla del usuario: "media + el CP"). La clase del CP (Very High → Low) sigue en el Excel.
#
# **Por qué:** el CP ya trae la venta del PDV (regla del usuario, 2026-09-30: solo datos del CP, no el archivo de ventas). El
# potencial va en cajas enteras con umbral 0.6: un potencial menor a 0.6 cajas no cuenta.

# %%
ids["V"] = ids.pos_id_cp.map(pdv0.PotentialQuantitative_TotalPortafolio).where(ids.con_venta)   # venta media del CP (cajas/mes)
ids["CP_original"] = ids.pos_id_cp.map(pdv0.PotentialQuantitativeFinal_TotalPortafolio)
ids["CP"] = LT.redondeo_cp(ids.CP_original, C.CP_UMBRAL_REDONDEO).to_numpy()      # potencial en cajas enteras (umbral 0.6)
ids["W"] = (ids.V + ids.CP.fillna(0)).where(ids.con_venta)                    # venta media + potencial (solo con venta)
ids["I_V_seg"] = LT.indice(ids.V, ids.segmento, ids.objetivo)                  # venta (CP) vs su subcanal: respaldo de Rappi
ids["clase_cp"] = ids.pos_id_cp.map(pdv0.PotentialQualitative_TotalPortafolio)
ob = ids[ids.objetivo]
VENTA = (f"PDV objetivo: venta media del CP mediana {ob.V.median():.2f} cajas/mes (p90 {ob.V.quantile(0.9):.2f}). CP original mediano "
         f"{ob.CP_original.median():.2f}; en cajas enteras {(ob.CP == 0).mean():.0%} queda en 0 (antes del redondeo {(ob.CP_original == 0).mean():.0%}) "
         f"y {(ob.CP >= 1).mean():.0%} con ≥ 1 caja; W mediana {ob.W.median():.2f}.")
print(VENTA)
display(pd.crosstab(ob.segmento, ob.clase_cp.fillna("sin clase")).reindex(columns=["Very High", "High", "Moderate", "Low", "sin clase"], fill_value=0))

SUBCANALES = ids.segmento.value_counts().index.tolist()
COLOR_SUB = {s_: eda.PALETA[k % len(eda.PALETA)] for k, s_ in enumerate(SUBCANALES)}
fig, ax = plt.subplots(figsize=(10, 8.5))
MP.fondo(ax, mun, agebs=ageb_c)
g = pts[ids.objetivo].join(ids[["W", "segmento"]])
for s_ in SUBCANALES:
    gg = g[g.segmento.eq(s_)]
    gg.plot(ax=ax, color=COLOR_SUB[s_], markersize=np.clip(gg.W * 1.5, 2, 90), alpha=0.55, label=f"{s_.title()} ({len(gg):,})")
ax.set_xlim(x0 - 1500, x1 + 1500); ax.set_ylim(y0 - 1500, y1 + 1500)
ax.legend(loc="lower left", markerscale=0.8)
ax.set_title("2.1 Venta media + CP por PDV (tamaño = V + CP en cajas/mes; color = subcanal)")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 2.2 Clúster de venta de cada PDV: los PDV con venta de su buffer de 300 m
#
# **Qué se hace:** el clúster de venta de cada PDV es su **buffer de 300 m**: dentro se toman los PDV Bepensa **con venta**
# (canal Tradicional), incluido él. Se calcula la **media de $W$** de esos PDV y el índice $I^V_i = 100\,W_i/\overline{W}_{C_i}$.
# Si el PDV es el **único con venta** en su buffer, no hay con quién compararlo y su Letra 2 queda **L** (regla del usuario).
#
# **Por qué:** así cada tienda se mide contra las tiendas que compiten por los mismos hogares, no contra todo el mercado. La
# Letra 2 es del PDV (su venta y su buffer), a diferencia de la Letra 1, que es de su clúster NSE.

# %%
ids["n_cluster"], ids["W_media_cluster"] = LT.cluster_local(ids.W, ids.Canal, ids.Latitud, ids.Longitud, R300, ids.con_venta)
ids["I_V"] = 100 * ids.W / ids.W_media_cluster
ids["solo_en_cluster"] = ids.con_venta & (ids.n_cluster < 2)
ob = ids[ids.objetivo]
clusters = ob.groupby("segmento").agg(PDV=("n_cluster", "size"), **{"mediana PDV en su buffer": ("n_cluster", "median")},
                                      **{"% solos en su buffer (→ L)": ("solo_en_cluster", "mean")},
                                      **{"% con I^V > 100": ("I_V", lambda s: (s > 100).mean())})
clusters.iloc[:, 2:] *= 100
display(clusters.round(1))
CLUSTER = (f"Clúster de venta (buffer de {R300} m del PDV): mediana {ob.n_cluster.median():.0f} PDV con venta; {ob.solo_en_cluster.mean():.0%} de los PDV "
           f"objetivo son los únicos con venta en su buffer (quedan L). Por subcanal: "
           + " · ".join(f"{c.title()} {r['% solos en su buffer (→ L)']:.0f}% solos" for c, r in clusters.iterrows()) + ".")
print(CLUSTER)

ej2 = []
for rango, meta in [((6, 12), 150), ((3, 5), 80)]:
    c_ = ob[ob.n_cluster.between(*rango)]
    if len(c_):
        ej2.append((c_.I_V - meta).abs().idxmin())
fig, ax = plt.subplots(1, len(ej2), figsize=(7 * len(ej2), 6.8), squeeze=False)
for a_, i_ in zip(ax.flat, ej2):
    rr = ids.iloc[i_]
    panel_buffer(a_, i_, f"Clúster de venta de {rr.n_cluster} PDV")
    x, y = pts.geometry.iloc[i_].x, pts.geometry.iloc[i_].y
    mismo = pts[ids.con_venta & pts.geometry.within(Point(x, y).buffer(R300))].join(ids[["W"]])
    mismo.plot(ax=a_, color=[MP.COLOR_L2["H" if v > rr.W_media_cluster else "L"] for v in mismo.W],
               markersize=np.clip(mismo.W * 8, 10, 320), edgecolor=eda.TINTA, lw=0.8, zorder=5)
    a_.text(0.02, 0.02, f"W = V + CP = {rr.V:.2f} + {rr.CP:.0f} = {rr.W:.2f}\nmedia del buffer = {rr.W_media_cluster:.2f} "
                        f"({rr.n_cluster} PDV con venta)\nI^V = {rr.I_V:.0f} → {'H' if rr.I_V > 100 else 'L'} (sin Rappi)",
            transform=a_.transAxes, fontsize=8.5, color=eda.TINTA, bbox=dict(facecolor="white", alpha=0.85, lw=0))
plt.suptitle("2.2 Clúster de venta = buffer de 300 m del PDV: círculo = V + CP (verde = sobre la media del buffer)", x=0.01, ha="left")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 2.3 Rappi premia a la locación moviendo su venta
#
# **Qué se hace:** cada tienda física Rappi **activa** del 00c (≥ 12 pedidos de sueros o derivados en ene-2025 → ago-2026)
# pasa su venta de sueros e hidratación a **cajas por mes** ($S_r$ = botellas por mes de vida entre `C.RAPPI_BOTELLAS_CAJA`
# botellas por caja; un empaque múltiple cuenta sus botellas por precio) y la **mueve** a los PDV Bepensa con venta de su
# radio de 300 m, en partes iguales ($R_i$). De cada PDV se guarda también cuántas tiendas Rappi activas tiene a ≤ 300 m y
# cuánto venden en pesos.
#
# **Por qué:** Rappi es venta **observada** de la categoría (sueros e hidratación, Coca-Cola y competidores) en el área, que
# Bepensa no ve en su propia venta, y premia a la locación **con esa venta**, no con puntos fijos (regla del usuario,
# 2026-09-30). Se pasa a cajas para sumarla con la venta Bepensa en la misma unidad y se reparte para no contar dos veces la
# misma venta (una tienda Rappi con 20 PDV cerca no suma 20 veces). Advertencia: la venta de un Turbo (dark store) llega desde
# su zona de reparto, más allá de 300 m.

# %%
lin = pd.read_parquet(F_RAPPI_LIN, columns=["tienda_fisica", "subcategoria", "beverage_sales", "beverage_units"])
lin["botellas"] = R.botellas(lin)
rp["botellas"] = rp.tienda_fisica.map(lin.groupby("tienda_fisica").botellas.sum()).fillna(0)
rp["cajas_mes"] = rp.botellas / rp.meses_vida / BOT                        # S_r: venta Rappi en cajas por mes de vida
act = rp[rp.activa].reset_index(drop=True)
ids["R_mov"], act["pdv_que_reciben"] = LT.mover_venta(act.cajas_mes, act.lat, act.lon, ids.Latitud, ids.Longitud, R300, ids.con_venta)
act["cajas_por_pdv"] = act.cajas_mes / act.pdv_que_reciben.where(act.pdv_que_reciben > 0)
vr = R.en_radio(ids.Latitud, ids.Longitud, act.lat, act.lon, R300)
ids["rappi_n"] = [len(x) for x in vr]
ids["rappi_venta"] = [act.venta_mes.to_numpy()[x].sum() for x in vr]
ids["rappi_sueros"] = [act.venta_sueros_mes.to_numpy()[x].sum() for x in vr]
ids["rappi_turbo"] = [bool(act.turbo.to_numpy()[x].any()) for x in vr]
ids["rappi_tiendas"] = [", ".join(act.nombre.to_numpy()[x][:3].astype(str)) for x in vr]
ids["P"] = (ids.rappi_n >= 1).astype(int)                                   # tienda Rappi activa a ≤ 300 m (si el PDV vende, recibe su venta)
ids["WR"] = (ids.W + ids.R_mov).where(ids.con_venta)                        # venta media + CP + venta Rappi movida
movida = ids.R_mov.sum()
assert np.isclose(movida, act.cajas_mes[act.pdv_que_reciben > 0].sum())     # se mueve toda la venta que tiene PDV cerca, una sola vez
ob = ids[ids.objetivo]
rec = ob[ob.R_mov > 0]
RAPPI = (f"{len(act)} tiendas Rappi activas venden {act.cajas_mes.sum():.0f} cajas/mes de sueros e hidratación ({BOT} botellas por caja; "
         f"los empaques múltiples suman {rp.botellas.sum() / rp.unidades.sum() - 1:.0%} de botellas sobre las unidades). Se mueven "
         f"{movida:.0f} cajas/mes ({movida / act.cajas_mes.sum():.0%}: {int((act.pdv_que_reciben == 0).sum())} tiendas no tienen PDV Bepensa con "
         f"venta a ≤ {R300} m) a {int((ids.R_mov > 0).sum()):,} PDV, {len(rec):,} de ellos objetivo ({ob.P.mean():.1%}). Cada uno recibe en la "
         f"mediana {rec.R_mov.median():.2f} cajas/mes ({(rec.R_mov / rec.W).median():.0%} de su venta + CP; máximo {rec.R_mov.max():.1f}). En total "
         f"es {movida / ids.W.sum():.1%} de la venta + CP de Bepensa.")
print(RAPPI)
display(act.sort_values("cajas_mes", ascending=False)[["nombre", "tipo", "municipio", "venta_mes", "cajas_mes", "pedidos", "% sueros", "turbo",
                                                       "pdv_que_reciben", "cajas_por_pdv"]].head(15).round(2))

ra = gpd.GeoDataFrame(act, geometry=gpd.points_from_xy(act.lon, act.lat), crs=4326).to_crs(CRS)
rx0, ry0, rx1, ry1 = ra.total_bounds
fig, ax = plt.subplots(1, 2, figsize=(17, 8.6), gridspec_kw={"width_ratios": [1.35, 1]})
MP.fondo(ax[0], mun, agebs=ageb_c)
gpd.GeoSeries(ra.buffer(R300), crs=CRS).plot(ax=ax[0], color=eda.PALETA[7], alpha=0.10, edgecolor=eda.PALETA[7], lw=0.6)
g = pts[ids.objetivo].join(ids[["R_mov"]])
g[g.R_mov == 0].plot(ax=ax[0], color=eda.MUTED, markersize=2, alpha=0.4, label=f"PDV sin venta Rappi ({int((g.R_mov == 0).sum()):,})")
g[g.R_mov > 0].plot(ax=ax[0], color=MP.COLOR_L2["H"], markersize=np.clip(g.R_mov[g.R_mov > 0] * 40, 6, 250), alpha=0.85, edgecolor="white",
                    lw=0.4, label=f"PDV que reciben venta Rappi ({int((g.R_mov > 0).sum()):,}; tamaño = cajas/mes)")
ra.plot(ax=ax[0], color=eda.PALETA[7], marker="s", markersize=np.clip(ra.cajas_mes * 12, 8, 250), edgecolor="white", lw=0.6,
        label=f"tienda Rappi activa ({len(ra)}; tamaño = cajas/mes)")
ax[0].set_xlim(rx0 - 1200, rx1 + 1200); ax[0].set_ylim(ry0 - 1200, ry1 + 1200)
ax[0].legend(loc="lower left", markerscale=0.7)
ax[0].set_title("Cada tienda Rappi activa (rojo) reparte sus cajas/mes entre los PDV con venta de su radio (verde)")
ej_r = act[act.pdv_que_reciben.between(3, 8)].nlargest(1, "cajas_mes")
if len(ej_r):
    r_ = ej_r.iloc[0]
    xr, yr = ra.geometry.iloc[ej_r.index[0]].x, ra.geometry.iloc[ej_r.index[0]].y
    MP.fondo(ax[1], mun, agebs=ageb_c)
    gpd.GeoSeries([Point(xr, yr).buffer(R300)], crs=CRS).plot(ax=ax[1], color=eda.PALETA[7], alpha=0.08, edgecolor=eda.PALETA[7], lw=1.4)
    cv = np.flatnonzero(ids.con_venta)
    reciben = cv[R.en_radio([r_.lat], [r_.lon], ids.Latitud.to_numpy()[cv], ids.Longitud.to_numpy()[cv], R300)[0]]
    cerca = pts.geometry.within(Point(xr, yr).buffer(R300 * 1.6)) & ~pts.index.isin(reciben)
    pts[cerca].plot(ax=ax[1], color=eda.MUTED, markersize=14, alpha=0.6)
    pts.iloc[reciben].plot(ax=ax[1], color=MP.COLOR_L2["H"], markersize=60, edgecolor=eda.TINTA, lw=0.8, zorder=5)
    for k_ in reciben:
        p_ = pts.geometry.iloc[k_]
        ax[1].annotate(f"+{r_.cajas_por_pdv:.2f}", (p_.x, p_.y), xytext=(5, 5), textcoords="offset points", fontsize=8, color=eda.TINTA)
    ax[1].scatter([xr], [yr], s=160, marker="s", color=eda.PALETA[7], edgecolor="white", zorder=6)
    MP.encuadre(ax[1], xr, yr, R300 * 1.5)
    ax[1].set_title(f"Ejemplo: {str(r_.nombre)[:34]}\n{r_.cajas_mes:.2f} cajas/mes ÷ {int(r_.pdv_que_reciben)} PDV con venta = "
                    f"+{r_.cajas_por_pdv:.2f} a cada uno (gris = sin venta o fuera del radio)", fontsize=10)
plt.suptitle("2.3 Rappi premia a la locación moviendo su venta (sueros e hidratación, en cajas por mes)", x=0.01, ha="left")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 2.4 ¿La venta movida tiene respaldo? Venta Bepensa con y sin Rappi cerca, y sensibilidad
#
# **Qué se hace:** dentro de cada subcanal se compara la venta de los PDV que reciben venta Rappi ($P=1$: tienda Rappi activa
# a ≤ 300 m) contra los que no (δ de Cliff sobre log1p de la venta, IC95 por **bootstrap de bloques H3 res 7**: PDV cercanos
# comparten clientes y no son independientes). Después se prueba la Letra 2 con otras **botellas por caja** (6, 12 y 24: la
# venta Rappi pesa el doble, igual o la mitad), otras definiciones de tienda Rappi (sin Turbo, solo sueros, ≥ 1 o ≥ 24
# pedidos) y otro **reparto**: que la media del clúster de venta no se mueva con Rappi, o no repartir (cada PDV recibe toda la
# venta de su radio).
#
# **Por qué:** si los PDV cerca de Rappi ya venden más, la venta movida va en la misma dirección que la venta observada; si
# no, es una apuesta por la demanda digital del área. La sensibilidad muestra cuántas letras dependen de la conversión a cajas
# (a confirmar con Bepensa) y de cómo se reparte la venta.

# %%
respaldo = []
for seg, g in ob.groupby("segmento"):
    if (g.P == 1).sum() >= 20 and (g.P == 0).sum() >= 20:
        d_, lo_, hi_ = eda.cliff_bloques(g.P == 1, np.log1p(g.V), [h3.cell_to_parent(h, 7) for h in g["Hexágono H3"]], B=300)
        respaldo.append({"subcanal": seg, "PDV con Rappi": int(g.P.sum()), "PDV sin Rappi": int((g.P == 0).sum()),
                         "mediana V con Rappi": g.V[g.P == 1].median(), "mediana V sin Rappi": g.V[g.P == 0].median(),
                         "δ de Cliff": d_, "IC95 bloques": f"[{lo_:+.2f}, {hi_:+.2f}]", "IC excluye 0": bool(lo_ > 0 or hi_ < 0),
                         "p (Mann-Whitney)": stats.mannwhitneyu(g.V[g.P == 1], g.V[g.P == 0]).pvalue})
respaldo = pd.DataFrame(respaldo)
if len(respaldo):
    respaldo["q_BH"] = stats.false_discovery_control(respaldo["p (Mann-Whitney)"], method="bh")
d_tot, lo_tot, hi_tot = eda.cliff_bloques(ob.P == 1, ob.I_V_seg, [h3.cell_to_parent(h, 7) for h in ob["Hexágono H3"]], B=300)
m_r = ob[ob.P == 1]
rho_r = stats.spearmanr(m_r.R_mov, m_r.I_V_seg)
display(respaldo.round(3))
RESPALDO = (f"Venta Bepensa (índice por subcanal) con vs sin Rappi a {R300} m: δ = {d_tot:+.2f} (IC95 bloques [{lo_tot:+.2f}, {hi_tot:+.2f}]); "
            f"entre los PDV que reciben venta Rappi, venta movida vs venta Bepensa: ρ = {rho_r[0]:+.2f} (p = {rho_r[1]:.2f}). "
            + ("La venta Bepensa ya es mayor cerca de Rappi: la venta movida va en la misma dirección." if lo_tot > 0 else
               "En total la venta Bepensa no es mayor cerca de Rappi (sí en algunos subcanales): la venta Rappi agrega información que la venta propia no tiene."
               if hi_tot >= 0 else "La venta Bepensa es MENOR cerca de Rappi: la venta movida va contra la venta observada (revisar)."))
print(RESPALDO)


def regla_l2(indice, n):
    """Letra 2 = H si hay ≥ 2 PDV con venta en su buffer y el índice es mayor a 100."""
    return (np.asarray(n) >= 2) & (np.asarray(indice) > 100)


def letra2_de(W_, R_, media_con_rappi=True):
    """Letra 2 (H/L; solo PDV objetivo) con el valor W_ y la venta Rappi movida R_. Regla del usuario (2026-09-30): la media
    del clúster de venta también se mueve con Rappi (media de W + R de los PDV con venta de su buffer); con
    media_con_rappi=False la media es la de W sola (Rappi solo premia)."""
    x = (W_ + R_).where(ids.con_venta)
    base_ = x if media_con_rappi else W_.where(ids.con_venta)
    n_, m_ = LT.cluster_local(base_, ids.Canal, ids.Latitud, ids.Longitud, R300, ids.con_venta)
    return pd.Series(np.where(regla_l2(100 * x / m_, n_), "H", "L"), index=ids.index).where(ids.objetivo)


OBJ = ids.objetivo.to_numpy()
base_h = letra2_de(ids.W, 0).eq("H").to_numpy()[OBJ]                          # Letra 2 = H sin Rappi


def fila_sens(tiendas, botellas_caja, reparto, R_, l2_):
    """Una fila de la sensibilidad: cuánto se mueve y cuántas letras suben o bajan contra la Letra 2 sin Rappi."""
    alta = l2_.eq("H").to_numpy()[OBJ]
    return {"tiendas Rappi que mueven su venta": tiendas, "botellas por caja": botellas_caja, "reparto": reparto,
            "cajas/mes movidas": float(np.sum(R_)), "PDV objetivo que reciben": int((np.asarray(R_)[OBJ] > 0).sum()),
            "% L2 = H": alta.mean() * 100, "PDV que pasan a H por Rappi": int((alta & ~base_h).sum()),
            "PDV que pasan a L por Rappi": int((~alta & base_h).sum())}


REPARTO = "partes iguales; la media del clúster de venta también con Rappi (base)"
BOTELLAS = sorted({6, 12, 24, BOT})
reglas_rappi = {"activas (base)": rp.activa, "activas sin Turbo": rp.activa & ~rp.turbo, "activas en sueros": rp.activa_sueros,
                "cualquier tienda (≥ 1 pedido)": rp.pedidos >= 1, "≥ 24 pedidos": rp.pedidos >= 24}
sens = []
for nombre, cond in reglas_rappi.items():
    t_ = rp[cond]
    for b_ in BOTELLAS:
        R_, _ = LT.mover_venta(t_.botellas / t_.meses_vida / b_, t_.lat, t_.lon, ids.Latitud, ids.Longitud, R300, ids.con_venta)
        sens.append(fila_sens(nombre, b_, REPARTO, R_, letra2_de(ids.W, R_)))
R_todo = np.array([act.cajas_mes.to_numpy()[x].sum() for x in vr]) * ids.con_venta.to_numpy()
sens += [fila_sens("activas (base)", BOT, "partes iguales; la media del clúster de venta sin Rappi (Rappi solo premia)", ids.R_mov,
                   letra2_de(ids.W, ids.R_mov, media_con_rappi=False)),
         fila_sens("activas (base)", BOT, "sin repartir: cada PDV recibe toda la venta Rappi de su radio", R_todo, letra2_de(ids.W, R_todo))]
sens = pd.DataFrame(sens)
sens["PDV que cambian por Rappi"] = sens["PDV que pasan a H por Rappi"] + sens["PDV que pasan a L por Rappi"]
es_base = sens.reparto.eq(REPARTO)
sb = sens[es_base & sens["tiendas Rappi que mueven su venta"].eq("activas (base)")].set_index("botellas por caja")
alt_ = sens[~es_base].set_index("reparto")
SENS = ("Botellas por caja: " + " · ".join(f"{k:g} → {r['PDV que pasan a H por Rappi']} suben y {r['PDV que pasan a L por Rappi']} bajan"
                                           for k, r in sb.iterrows())
        + f". Si la media del clúster de venta no se moviera con Rappi (solo premia): {alt_.iloc[0]['PDV que pasan a H por Rappi']} suben y "
          f"{alt_.iloc[0]['PDV que pasan a L por Rappi']} bajan; sin repartir (la misma venta cuenta varias veces: "
          f"{alt_.iloc[1]['cajas/mes movidas']:.0f} cajas/mes en vez de {movida:.0f}): {alt_.iloc[1]['PDV que pasan a H por Rappi']} suben y "
          f"{alt_.iloc[1]['PDV que pasan a L por Rappi']} bajan.")
print(SENS)
display(sens[es_base].pivot_table(index="tiendas Rappi que mueven su venta", columns="botellas por caja", values="PDV que cambian por Rappi").astype(int))
display(sens[sens["tiendas Rappi que mueven su venta"].eq("activas (base)") & sens["botellas por caja"].eq(BOT)].set_index("reparto").iloc[:, 2:].round(1))

fig, ax = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1.3, 1]})
segs = respaldo.subcanal.tolist() if len(respaldo) else []
for k_, seg in enumerate(segs):
    g = ob[ob.segmento.eq(seg)]
    for dx, (pp, col) in zip((-0.18, 0.18), [(0, eda.MUTED), (1, MP.COLOR_L2["H"])]):
        ax[0].boxplot(np.log1p(g.V[g.P == pp]), positions=[k_ + dx], widths=0.3, showfliers=False, patch_artist=True,
                      boxprops=dict(facecolor=col, alpha=0.45), medianprops=dict(color=eda.TINTA))
ax[0].set_xticks(range(len(segs)), [s_.title()[:22] for s_ in segs], fontsize=7.5)
ax[0].set(ylabel="log1p(cajas/mes)", title="Venta Bepensa sin (gris) y con (verde) tienda Rappi activa a 300 m")
ax[0].legend(handles=[Line2D([], [], color=eda.MUTED, lw=6, alpha=0.5), Line2D([], [], color=MP.COLOR_L2["H"], lw=6, alpha=0.5)],
             labels=["sin Rappi a 300 m", "recibe venta Rappi"], loc="upper right")
for nombre, g in sens[es_base].groupby("tiendas Rappi que mueven su venta"):
    ax[1].plot(g["botellas por caja"], g["PDV que cambian por Rappi"], "o-", ms=4, label=nombre, lw=2 if nombre == "activas (base)" else 1.2)
ax[1].set_xscale("log", base=2)
ax[1].set_xticks(BOTELLAS, [f"{v:g}" for v in BOTELLAS])
ax[1].xaxis.set_minor_locator(plt.NullLocator())
ax[1].axvline(BOT, color=eda.MUTED, ls="--", lw=1)
ax[1].text(BOT * 1.04, ax[1].get_ylim()[1] * 0.9, f"{BOT:g} botellas por caja (base)", color=eda.TINTA_2, fontsize=8)
ax[1].set(xlabel="botellas por caja (más botellas = la venta Rappi pesa menos)", ylabel="PDV que cambian de letra (suben + bajan)",
          title="Sensibilidad de la venta movida")
ax[1].legend(fontsize=7)
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 2.5 Letra 2
#
# **Qué se hace:** $I^{V*}_i = 100\,(W_i+R_i)/\overline{(W+R)}_{C_i}$ y $L2 = H$ si el PDV tiene **al menos otro PDV con
# venta** en su buffer e $I^{V*} > 100$ (su venta media + CP + la venta Rappi movida supera la media de su clúster de venta,
# que también lleva la venta Rappi de cada PDV); en otro caso $L$. Se marcan la frontera ($|I^{V*}-100|\le 10$), los PDV que
# **suben o bajan por Rappi** y los que quedan **L por estar solos** en su buffer. QA de la regla: cuántas letras cambian sin
# el CP (solo $V$), sin redondear el CP, sin Rappi y con la media sin Rappi (Rappi solo premia).
#
# **Por qué:** la media del clúster de venta también se mueve con Rappi (regla del usuario, 2026-09-30): cada PDV se compara con
# sus vecinos con la misma vara (venta media + CP + Rappi). Así Rappi premia al PDV que recibe más venta Rappi que sus vecinos,
# y uno que recibe menos que ellos puede bajar.

# %%
_, ids["WR_media_cluster"] = LT.cluster_local(ids.WR, ids.Canal, ids.Latitud, ids.Longitud, R300, ids.con_venta)   # media de W + Rappi
ids["I_V_star"] = 100 * ids.WR / ids.WR_media_cluster
ids["L2"] = pd.Series(np.where(regla_l2(ids.I_V_star, ids.n_cluster), "H", "L"), index=ids.index).where(ids.objetivo)
ids["L2_sin_rappi"] = letra2_de(ids.W, 0)
ids["L2_solo_premia"] = letra2_de(ids.W, ids.R_mov, media_con_rappi=False)       # QA: la regla anterior (la media sin Rappi)
ids["L2_sin_cp"] = letra2_de(ids.V, ids.R_mov)
ids["L2_cp_original"] = letra2_de(ids.V + ids.CP_original.fillna(0), ids.R_mov)   # QA: el potencial sin redondear
ids["frontera_L2"] = ids.objetivo & ~ids.solo_en_cluster & ((ids.I_V_star - 100).abs() <= FR)
ids["sube_por_rappi"] = ids.objetivo & ids.L2.eq("H") & ids.L2_sin_rappi.eq("L")
ids["baja_por_rappi"] = ids.objetivo & ids.L2.eq("L") & ids.L2_sin_rappi.eq("H")
ids["cambia_por_rappi"] = ids.sube_por_rappi | ids.baja_por_rappi
ob = ids[ids.objetivo]
assert (ob.L2 == letra2_de(ids.W, ids.R_mov)[ids.objetivo]).all(), "la Letra 2 y su sensibilidad usan la misma regla"
qa_l2 = pd.DataFrame([{"comparación": k, "% misma Letra 2": (ob.L2 == ob[c]).mean() * 100, "κ de Cohen": eda.kappa_cohen(ob.L2, ob[c])}
                      for k, c in [("sin el CP (solo venta media)", "L2_sin_cp"), ("con el CP sin redondear", "L2_cp_original"),
                                   ("sin la venta Rappi movida", "L2_sin_rappi"),
                                   ("con la media del clúster de venta sin Rappi (Rappi solo premia)", "L2_solo_premia")]])
display(qa_l2.round(3))
LETRA2 = (f"L2 = H en {(ob.L2 == 'H').mean():.1%} de los PDV objetivo; {int(ob.solo_en_cluster.sum())} ({ob.solo_en_cluster.mean():.0%}) quedan L por ser "
          f"los únicos con venta en su buffer; la venta Rappi movida cambia {int(ob.cambia_por_rappi.sum())} letras ({int(ob.sube_por_rappi.sum())} suben y "
          f"{int(ob.baja_por_rappi.sum())} bajan: la media del clúster de venta también se mueve); frontera ±{FR}: {ob.frontera_L2.mean():.1%}. Misma letra "
          + ", ".join(f"{r.comparación} {r['% misma Letra 2']:.0f}%" for _, r in qa_l2.iterrows()) + ".")
print(LETRA2)
display(ob.groupby("segmento").agg(PDV=("L2", "size"), **{"% L2 = H": ("L2", lambda s: (s == "H").mean() * 100)},
                                   **{"% solos (L)": ("solo_en_cluster", "mean")}, **{"suben por Rappi": ("sube_por_rappi", "sum")},
                                   **{"bajan por Rappi": ("baja_por_rappi", "sum")},
                                   **{"% H sin CP": ("L2_sin_cp", lambda s: (s == "H").mean() * 100)}).assign(**{"% solos (L)": lambda t: t["% solos (L)"] * 100}).round(1))

fig, ax = plt.subplots(figsize=(10, 8.5))
MP.fondo(ax, mun, agebs=ageb_c)
g = pts[ids.objetivo].join(ids[["L2", "sube_por_rappi", "baja_por_rappi", "solo_en_cluster"]])
for l_, gg in g.groupby("L2"):
    gg.plot(ax=ax, color=MP.COLOR_L2[l_], markersize=4, alpha=0.7, label=f"L2 = {l_} ({len(gg):,})")
g[g.solo_en_cluster].plot(ax=ax, color="none", edgecolor=eda.MUTED, markersize=30, lw=0.8, label=f"solo con venta en su buffer → L ({int(g.solo_en_cluster.sum())})")
g[g.sube_por_rappi].plot(ax=ax, color="none", edgecolor=eda.TINTA, markersize=60, lw=1.2, label=f"sube a H por Rappi ({int(g.sube_por_rappi.sum())})")
g[g.baja_por_rappi].plot(ax=ax, color="none", edgecolor=eda.PALETA[7], markersize=60, lw=1.2, label=f"baja a L por Rappi ({int(g.baja_por_rappi.sum())})")
ax.set_xlim(x0 - 1500, x1 + 1500); ax.set_ylim(y0 - 1500, y1 + 1500)
ax.legend(loc="lower left", markerscale=1.5)
ax.set_title("2.5 Letra 2 (verde = V + CP + Rappi sobre la media de su buffer, que también lleva Rappi; círculo gris = solo con venta; "
             "negro = sube por Rappi; rojo = baja por Rappi)", fontsize=9)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 3. Letras juntas con su acción Golden Stores: base (INEGI + CP) y final (con AltScore y Rappi)
#
# **Qué se hace:** el código es Letra 1 + Letra 2 (HH, HL, LH, LL) con su acción fija de Golden Stores (Atacar, Bloquear,
# Fortalecer, Mantener). Las **letras base** usan solo INEGI y el CP (Letra 1 sin AltScore + Letra 2 sin Rappi); las
# **finales**, la Letra 1 movida por AltScore y la Letra 2 con la venta Rappi movida.
#
# **Por qué:** así se ve qué PDV cambian de acción por AltScore y por Rappi, las dos fuentes que mueven las letras.

# %%
ids["letras"] = (ids.L1.fillna("") + ids.L2.fillna("")).where(ids.objetivo)
ids["letras_sin_rappi"] = (ids.L1.fillna("") + ids.L2_sin_rappi.fillna("")).where(ids.objetivo)
ids["letras_base"] = (ids.L1_sin_alt.fillna("") + ids.L2_sin_rappi.fillna("")).where(ids.objetivo)   # solo INEGI + CP
ids["accion"] = ids.letras.map(LT.ACCION)
ids["accion_base"] = ids.letras_base.map(LT.ACCION)
ob = ids[ids.objetivo]
CL = ["HH", "HL", "LH", "LL"]
panorama = ob.groupby("letras").agg(tiendas=("pos_id_cp", "size"), cajas=("V", "sum"), media=("V", "mean"), N_medio=("N", "mean"),
                                    hogares=("HH_cluster", "median"), con_rappi=("P", "mean")).reindex(CL)
panorama["% tiendas"] = panorama.tiendas / panorama.tiendas.sum() * 100
panorama["% mix ventas"] = panorama.cajas / panorama.cajas.sum() * 100
panorama["Index ventas"] = panorama.media / ob.V.mean() * 100
panorama["% con Rappi"] = panorama.con_rappi * 100
panorama.insert(0, "acción", [LT.ACCION[c] for c in CL])
panorama = panorama.drop(columns=["con_rappi"])
display(panorama.round(1))
cruce = pd.crosstab(ob.letras_base.rename("letras base (INEGI + CP)"), ob.letras.rename("letras finales (con AltScore y Rappi)")).reindex(index=CL, columns=CL, fill_value=0)
display(cruce)
igual = (ob.letras == ob.letras_base).mean()
perfil_nse = pd.DataFrame({c: hh.loc[ob.index, c] for c in NSE}).groupby(ob.letras).sum()
perfil_nse = perfil_nse.div(perfil_nse.sum(axis=1), axis=0) * 100
indice_nse = perfil_nse.div(REF, axis=1) * 100
display(perfil_nse.round(1).reindex(CL))
display(indice_nse.round(0).reindex(CL))
LETRAS = ("Tradicional: " + ", ".join(f"{c} {panorama.loc[c, '% tiendas']:.0f}% de tiendas / {panorama.loc[c, '% mix ventas']:.0f}% de venta"
                                      for c in CL if pd.notna(panorama.loc[c, "tiendas"]))
          + f". AltScore y Rappi cambian las letras de {1 - igual:.0%} de los PDV frente a las letras base (solo INEGI + CP): "
            f"AltScore {int(ob.cambia_por_alt.sum())} Letras 1 y Rappi {int(ob.cambia_por_rappi.sum())} Letras 2.")
print(LETRAS)

fig, ax = plt.subplots(1, 2, figsize=(16, 7.5), gridspec_kw={"width_ratios": [1.5, 1]})
MP.fondo(ax[0], mun, agebs=ageb_c)
g = pts[ids.objetivo].join(ids[["letras"]])
for c in ["LL", "LH", "HL", "HH"]:
    gg = g[g.letras == c]
    gg.plot(ax=ax[0], color=MP.COLOR_CLUSTER[c], markersize=6 if c == "HH" else 4, alpha=0.85, label=f"{c} · {LT.ACCION[c]} ({len(gg):,})")
ax[0].set_xlim(x0 - 1500, x1 + 1500); ax[0].set_ylim(y0 - 1500, y1 + 1500)
ax[0].legend(loc="lower left", markerscale=2)
ax[0].set_title("3. Letras finales por PDV: NSE de su clúster con AltScore (1.ª) + venta, CP y Rappi contra su buffer (2.ª)", fontsize=10)
ax[1].imshow(cruce.to_numpy(), cmap=CMAP_CENSO)
for a in range(4):
    for b_ in range(4):
        ax[1].text(b_, a, f"{cruce.iloc[a, b_]:,}", ha="center", va="center", fontsize=10, color="white" if cruce.iloc[a, b_] > cruce.to_numpy().max() * 0.5 else eda.TINTA)
ax[1].set_xticks(range(4), CL); ax[1].set_yticks(range(4), CL)
ax[1].set(xlabel="letras finales (con AltScore y Rappi)", ylabel="letras base (INEGI + CP)", title=f"Mismas letras: {igual:.0%} de los PDV")
ax[1].grid(False)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 4. Mapa interactivo de QA (canal Tradicional, con filtro por subcanal)
#
# Mismos pasos que arriba, en el navegador: cada paso enciende sus capas y explica qué se hace, por qué y la fórmula; las
# casillas de **Subcanal** muestran u ocultan los PDV. Clic en un **hexágono de clúster** o en un **PDV**: su clúster NSE (el
# hexágono en azul, el buffer de 300 m desde su centro y los PDV que lo comparten) y, en un PDV, su buffer de 300 m con los PDV
# con venta (su clúster de venta, en negro) y las tiendas Rappi; la ficha trae los valores de las fórmulas. Clic en una tienda
# Rappi: los PDV que reciben su venta. Búsqueda por ID o nombre. Se guarda en `outputs/<ciudad>/<cliente>/` (lleva datos del
# cliente: no se sube a git ni se publica).

# %%
for g_, cs in GRUPO_NSE.items():                                              # % bajo / medio / alto para los tooltips del mapa
    ageb[f"p_{g_}"] = (ageb[[f"HHs_{c}" for c in cs]].sum(axis=1) / ageb[[f"HHs_{c}" for c in NSE]].sum(axis=1).replace(0, np.nan) * 100).round(0)
    hexg[f"p_{g_}"] = (hex_hh[cs].sum(axis=1) / hex_hh.sum(axis=1).replace(0, np.nan) * 100).round(0)
ageb_js = ageb.to_crs(4326)[["CVEGEO", "N", "p_bajo", "p_medio", "p_alto", "geometry"]].assign(N=lambda t: t.N.round(2))
ageb_js["geometry"] = ageb_js.geometry.simplify(0.00004)
mun_js = mun.to_crs(4326)[["NOMGEO", "geometry"]].assign(geometry=lambda t: t.geometry.simplify(0.0002))
hex_js = hexg[["N", "censo", "Total HHs", "p_bajo", "p_medio", "p_alto"]].round(2).rename(columns={"Total HHs": "hog"})
hex_js = hex_js[(hex_js.hog > 0) | hex_js.index.isin(ids["Hexágono H3"])]
l1_cl = ob.groupby("cluster_nse").L1.agg(lambda s: " · ".join(f"{k} {v}" for k, v in s.value_counts().sort_index().items()))
clv = cl[cl.hog > 0].copy()
cl_js = pd.DataFrame({"N": clv.N.round(2), "alt": clv.alt.round(0), "Nf": clv.N_star.round(2), "n_pdv": clv.n_pdv, "hog": clv.hog.round(0),
                      "p_bajo": clv.p_bajo.round(0), "p_medio": clv.p_medio.round(0), "p_alto": clv.p_alto.round(0)}, index=clv.index)
clusters_js = pd.DataFrame({"cl": clv.index, "lat": clv.lat.round(6), "lon": clv.lon.round(6), "n_pdv": clv.n_pdv, "n_obj": clv.n_objetivo,
                            "hog": clv.hog.round(0), "N": clv.N.round(2), "clase": clv.clase, "abc": clv.abc.round(1), "censo": clv.censo.round(0),
                            "alt": clv.alt.round(0), "puntos": clv.alt_puntos, "N_alt": clv.N_alt.round(2), "Nf": clv.N_star.round(2),
                            "l1": l1_cl.reindex(clv.index).fillna("—").to_numpy(), "p_bajo": clv.p_bajo.round(0), "p_medio": clv.p_medio.round(0),
                            "p_alto": clv.p_alto.round(0)})
rappi_js = rp.merge(act[["tienda_fisica", "pdv_que_reciben", "cajas_por_pdv"]], on="tienda_fisica", how="left")[
    ["nombre", "tipo", "municipio", "lat", "lon", "venta_mes", "venta_sueros_mes", "cajas_mes", "pdv_que_reciben", "cajas_por_pdv", "pedidos", "% sueros",
     "% Coca-Cola", "activa", "turbo"]].round({"lat": 6, "lon": 6, "venta_mes": 0, "venta_sueros_mes": 0, "cajas_mes": 2, "cajas_por_pdv": 3,
                                               "% sueros": 1, "% Coca-Cola": 1})
bepensa_js = pd.DataFrame({"id": ids.pos_id_cp.astype(str), "lat": ids.Latitud.round(6), "lon": ids.Longitud.round(6)})[ids.con_venta.to_numpy()]
ESC_NSE = {"tipo": "continua", "min": 1, "max": 6, "colores": MP.SECUENCIAL, "bajo": "1 = D/E", "alto": "6 = A/B"}
DIST_NSE3 = [["Bajo (D+ y D/E)", "p_bajo", MP.COLOR_NSE3["bajo"]], ["Medio (C y C−)", "p_medio", MP.COLOR_NSE3["medio"]],
             ["Alto (C+ y A/B)", "p_alto", MP.COLOR_NSE3["alto"]]]              # barra de distribución en los tooltips
ESC_CENSO = {"tipo": "continua", "min": 0, "max": 100, "colores": MP.AZULES, "bajo": "0", "alto": "100"}
POPUP = {"pdv": [("ID PDV", "id"), ("Nombre", "nombre"), ("Subcanal", "segmento"), ("Clúster NSE (H3 res 9)", "cl"), ("PDV del clúster NSE", "ncln"),
                 ("Distancia al centro del clúster (m)", "dcen"), ("Hogares del clúster (buffer de 300 m)", "hog"),
                 ("NSE del punto (hexágono res 10)", "N_punto"), ("NSE de su AGEB", "N_ageb"), ("Nivel NSE INEGI del clúster (1-6)", "Ni"),
                 ("NSE predominante (bajo / medio / alto)", "clase"), ("% ABC+ del clúster", "abc"), ("Índice Censo del clúster (0-100)", "censo"),
                 ("Índice AltScore del clúster (0-100)", "alt"), ("NSE AltScore en escala 1-6", "N_alt"),
                 (f"Nivel NSE final = {1 - LAM:g}·INEGI + {LAM:g}·AltScore", "N"), ("I^N (índice NSE)", "I_N"), ("Letra 1 sin AltScore", "L1s"),
                 ("Letra 1 con AltScore (final)", "L1"), ("NSE confirmado por el Censo", "conf"),
                 ("V venta media del CP (cajas/mes)", "V"), ("CP potencial original (cajas/mes)", "CPo"), ("CP en cajas enteras (umbral 0.6)", "CP"),
                 ("W = V + CP", "W"), ("PDV con venta en su buffer (clúster de venta)", "ncl"), ("Media de W del buffer (sin Rappi)", "Wm"),
                 ("I^V = 100·W / media", "I_V"), ("Solo con venta en su buffer (→ L)", "solo"), ("Tiendas Rappi ACTIVAS a 300 m", "nR"),
                 ("Venta Rappi del radio (MXN/mes)", "R"), ("de sueros (MXN/mes)", "RS"), ("Venta Rappi movida al PDV (cajas/mes)", "Rm"),
                 ("W + Rappi", "WR"), ("Media de W + Rappi del buffer", "WRm"), ("I^V* = 100·(W + Rappi) / media con Rappi", "I_V_star"),
                 ("Letra 2 sin Rappi", "L2s"), ("Letra 2 con Rappi (final)", "L2"), ("Letras base (INEGI + CP)", "lb"), ("Letras finales", "letras"),
                 ("Acción", "accion"), ("Clase CP", "clase_cp")],
         "clusters": [("Clúster NSE (H3 res 9)", "cl"), ("PDV en el hexágono", "n_pdv"), ("PDV objetivo", "n_obj"),
                      ("Hogares del buffer de 300 m", "hog"), ("Nivel NSE INEGI (1-6)", "N"), ("NSE predominante", "clase"), ("% ABC+", "abc"),
                      ("Índice Censo (0-100)", "censo"), ("Índice AltScore (0-100)", "alt"), ("Puntos AltScore con índice en el buffer", "puntos"),
                      ("NSE AltScore en escala 1-6", "N_alt"), (f"Nivel NSE final = {1 - LAM:g}·INEGI + {LAM:g}·AltScore", "Nf"),
                      ("Letra 1 de sus PDV objetivo", "l1")],
         "rappi": [("Tienda Rappi", "nombre"), ("Tipo", "tipo"), ("Municipio", "municipio"), ("Venta sueros e hidratación (MXN/mes)", "venta_mes"),
                   ("de sueros (MXN/mes)", "venta_sueros_mes"), (f"Venta en cajas/mes ({BOT} botellas por caja)", "cajas_mes"),
                   ("PDV con venta a 300 m que la reciben", "pdv_que_reciben"), ("Cajas/mes a cada PDV", "cajas_por_pdv"),
                   ("Pedidos en la ventana", "pedidos"), ("% sueros", "% sueros"), ("% Coca-Cola", "% Coca-Cola"),
                   (f"Activa (≥ {THETA} pedidos)", "activa"), ("Turbo (dark store)", "turbo")]}
EXTRA_CL = [["PDV del hexágono", "n_pdv"], ["Hogares del buffer", "hog"], ["Nivel INEGI", "N"], ["Índice AltScore", "alt"], ["Nivel final", "Nf"]]
CAPAS = [
    {"id": "municipios", "nombre": "Límite municipal", "tipo": "contorno", "fuente": "municipios", "siempre": True},
    {"id": "ageb_N", "nombre": "Nivel NSE de la AGEB (media 1-6)", "tipo": "poligonos", "fuente": "agebs", "campo": "N", "etiqueta": "CVEGEO", "escala": ESC_NSE,
     "distribucion": DIST_NSE3},
    {"id": "hex_N", "nombre": "Nivel NSE del hexágono res 10 (media 1-6)", "tipo": "hex", "campo": "N", "escala": ESC_NSE, "distribucion": DIST_NSE3},
    {"id": "hex_censo", "nombre": "Índice del Censo por manzana (0-100)", "tipo": "hex", "campo": "censo", "escala": ESC_CENSO},
    {"id": "cl_N", "nombre": "Clúster NSE: nivel INEGI de su buffer (media 1-6)", "tipo": "hex", "fuente": "cl", "campo": "N", "escala": ESC_NSE,
     "borde": True, "opacidad": 0.7, "distribucion": DIST_NSE3, "extra": EXTRA_CL, "seleccion": "clusters"},
    {"id": "cl_alt", "nombre": "Clúster NSE: índice AltScore de su buffer (0-100)", "tipo": "hex", "fuente": "cl", "campo": "alt", "escala": ESC_CENSO,
     "borde": True, "opacidad": 0.7, "extra": EXTRA_CL, "seleccion": "clusters"},
    {"id": "cl_Nf", "nombre": "Clúster NSE: nivel final INEGI + AltScore (media 1-6)", "tipo": "hex", "fuente": "cl", "campo": "Nf", "escala": ESC_NSE,
     "borde": True, "opacidad": 0.7, "distribucion": DIST_NSE3, "extra": EXTRA_CL, "seleccion": "clusters"},
    {"id": "pdv_Np", "nombre": "PDV: NSE del punto", "tipo": "puntos", "dataset": "pdv", "campo": "N_punto", "escala": ESC_NSE, "radio_px": 5},
    {"id": "pdv_clase", "nombre": "PDV: NSE predominante de su clúster", "tipo": "puntos", "dataset": "pdv", "campo": "clase", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_NSE3,
                "etiquetas": {"bajo": "bajo (D+ y D/E)", "medio": "medio (C y C−)", "alto": "alto (C+ y A/B)"}}},
    {"id": "pdv_conf", "nombre": "PDV: ¿NSE confirmado por el Censo?", "tipo": "puntos", "dataset": "pdv", "campo": "conf", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": {"Sí": "#1baf7a", "No": "#e34948"}, "etiquetas": {"Sí": "la letra del Censo coincide", "No": "NSE a revisar"}}},
    {"id": "pdv_alt", "nombre": "PDV: ¿AltScore cambia su Letra 1?", "tipo": "puntos", "dataset": "pdv", "campo": "altc", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": {"sube a H": "#2a78d6", "baja a L": "#eda100", "no": "#c3c2b7"},
                "etiquetas": {"sube a H": "sube a H por AltScore", "baja a L": "baja a L por AltScore", "no": "no cambia"}}},
    {"id": "pdv_L1", "nombre": "PDV: Letra 1 (NSE de su clúster, con AltScore)", "tipo": "puntos", "dataset": "pdv", "campo": "L1", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_L1, "etiquetas": {"H": "H · NSE del clúster ≥ media del subcanal", "L": "L · por debajo"}}},
    {"id": "pdv_W", "nombre": "PDV: subcanal (tamaño = V + CP)", "tipo": "puntos", "dataset": "pdv", "campo": "segmento", "tamano": "W", "escala_tamano": 2.2,
     "escala": {"tipo": "categorica", "colores": COLOR_SUB}},
    {"id": "pdv_IV", "nombre": "PDV: V + CP contra la media de su buffer (sin Rappi)", "tipo": "puntos", "dataset": "pdv", "campo": "L2s",
     "tamano": "W", "escala_tamano": 2.2,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_L2, "etiquetas": {"H": "V + CP > media de su buffer", "L": "≤ media, o solo con venta"}}},
    {"id": "rappi_300", "nombre": "Radio de 300 m de las tiendas Rappi activas", "tipo": "circulos", "dataset": "rappi", "radio_m": R300, "filtro": ["activa", True]},
    {"id": "rappi", "nombre": "Tiendas Rappi (tamaño = cajas/mes)", "tipo": "puntos", "dataset": "rappi", "campo": "activa", "tamano": "cajas_mes", "escala_tamano": 3,
     "escala": {"tipo": "categorica", "colores": {"true": "#e34948", "false": "#c3c2b7"}, "etiquetas": {"true": "activa", "false": "esporádica"}}},
    {"id": "pdv_R", "nombre": "PDV: venta Rappi movida (tamaño = cajas/mes)", "tipo": "puntos", "dataset": "pdv", "campo": "Ptxt", "tamano": "Rm", "escala_tamano": 6,
     "escala": {"tipo": "categorica", "colores": {"sí": "#1baf7a", "no": "#c3c2b7"},
                "etiquetas": {"sí": "recibe venta Rappi", "no": "no recibe (sin Rappi activa a 300 m o sin venta)"}}},
    {"id": "pdv_L2", "nombre": "PDV: Letra 2 (venta + CP + Rappi vs su buffer)", "tipo": "puntos", "dataset": "pdv", "campo": "L2", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_L2, "etiquetas": {"H": "H · ≥ 2 con venta en su buffer e I^V* > 100", "L": "L"}}},
    {"id": "pdv_cl", "nombre": "PDV: letras finales y acción Golden Stores", "tipo": "puntos", "dataset": "pdv", "campo": "letras", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_CLUSTER, "etiquetas": {k: f"{k} · {LT.ACCION[k]}" for k in CL}}},
    {"id": "pdv_base", "nombre": "PDV: letras base (INEGI + CP, sin AltScore ni Rappi)", "tipo": "puntos", "dataset": "pdv", "campo": "lb", "radio_px": 5,
     "escala": {"tipo": "categorica", "colores": MP.COLOR_CLUSTER, "etiquetas": {k: f"{k} · {LT.ACCION[k]}" for k in CL}}},
]


def pct(s, cond):
    """% de `cond` entre los PDV con dato en `s` (las letras solo existen en los PDV objetivo)."""
    return f"{cond.sum() / max(s.notna().sum(), 1):.0%}"


def pasos_qa(s):
    """Textos del panel del mapa, con las cifras del canal Tradicional."""
    return [
        {"titulo": "1.1 NSE del punto geográfico", "capas": ["ageb_N", "pdv_Np"],
         "que": "Cada PDV toma el NSE del hexágono H3 res 10 donde está (≈ una manzana); de fondo, el NSE de cada AGEB.",
         "porque": "El NSE AMAI se estima por AGEB: el punto hereda el de su AGEB salvo en los bordes. Si el punto no tiene hogares (zona comercial), el NSE sale de su clúster.",
         "formula": "N = Σ k·p_k   (k = 1 D/E … 6 A/B)", "cifras": f"{s.N_punto.notna().mean():.0%} de los PDV tienen hogares en su hexágono."},
        {"titulo": "1.2 Nos aseguramos: Censo por manzana", "capas": ["hex_censo", "pdv_conf"],
         "que": "Índice de bienes y escolaridad del Censo 2020 por manzana (auto, computadora, internet, escolaridad) llevado a hexágonos por área.",
         "porque": "Es una medición directa y más fina que el modelo AMAI. Verde = la letra del Censo coincide con la Letra 1; rojo = NSE a revisar.",
         "formula": f"ρ(NSE AMAI, Censo) = {rho_c:+.2f} en hexágonos", "cifras": f"NSE confirmado en {pct(s.conf, s.conf.eq('Sí'))} de los PDV objetivo."},
        {"titulo": "1.3 Clúster NSE: hexágono + 300 m", "capas": ["cl_N", "pdv_clase"],
         "que": f"Cada hexágono H3 res {RES_CL} con PDV es un clúster NSE: su centro es el punto NSE y los hogares de su buffer de {R300} m le dan su NSE. "
                "Todos los PDV del hexágono lo comparten. Clic en un hexágono o en un PDV: el hexágono azul, su buffer (punteado azul) y sus PDV (anillos azules).",
         "porque": "La Letra 1 es del clúster, no del PDV. Los hexágonos son chicos y regulares: funcionan igual en geografías complejas donde un centroide de AGEB quedaría lejos.",
         "formula": "HH_ck = Σ_{h ∈ A_c} HH_hk ;  p_ck = HH_ck / Σ_k HH_ck ;  N_c = Σ_k k·p_ck",
         "cifras": f"{s.cl.nunique():,} clústeres con PDV; ningún PDV queda a más de {ids.dist_centro_m.max():.0f} m del centro de su hexágono. Predominante: "
                   + " · ".join(f"{k} {pct(s.clase, s.clase.eq(k))}" for k in ["bajo", "medio", "alto"])},
        {"titulo": "1.4 AltScore mueve el NSE", "capas": ["cl_alt", "pdv_alt"],
         "que": f"El índice NSE AltScore (0-100) de los puntos AltScore del buffer de cada clúster se lleva a la escala de N por cuantiles y se combina con "
                f"el de INEGI con peso λ = {LAM:g} (solo con ≥ {MIN_ALT} puntos). Color del PDV: si AltScore le cambia la Letra 1.",
         "porque": "AltScore es una variable socioeconómica más y sí mueve el NSE (regla del usuario), como Rappi mueve la venta. INEGI pesa más porque el Censo lo confirma.",
         "formula": f"N*_c = (1 − λ)·N_c + λ·Ñ_c ;  Ñ_c = Q_N(F_a(a_c)) ;  λ = {LAM:g}",
         "cifras": f"ρ(AltScore, INEGI) = {rho_a:+.2f} por clúster; AltScore sube {int(s.altc.eq('sube a H').sum())} y baja {int(s.altc.eq('baja a L').sum())} Letras 1."},
        {"titulo": "1.5 Letra 1 (NSE del clúster)", "capas": ["cl_Nf", "pdv_L1"],
         "que": "H si el NSE final de su clúster (INEGI + AltScore) es ≥ la media de su subcanal. De fondo, el nivel final de cada clúster.",
         "porque": "Golden Stores compara cada tienda con la media de su mercado (índice 100 por subcanal).",
         "formula": "I^N_i = 100 · N*_c(i) / N̄*_s(i) ;  L1 = H si I^N ≥ 100",
         "cifras": f"L1 = H en {pct(s.L1, s.L1.eq('H'))} de {s.L1.notna().sum():,} PDV objetivo (sin AltScore {pct(s.L1s, s.L1s.eq('H'))})."},
        {"titulo": "2.1 Venta media + CP del PDV", "capas": ["pdv_W"],
         "que": "W = venta media + potencial, los dos del CP: PotentialQuantitative (cajas/mes) + PotentialQuantitativeFinal en cajas enteras (hacia abajo si el decimal < 0.6). Tamaño = W; color = subcanal.",
         "porque": "Regla del usuario: 'media + el CP', solo con datos del CP. Reconoce a la tienda que vende poco hoy pero tiene potencial frente a su comparable.",
         "formula": "W_i = V_i + CP_i"},
        {"titulo": "2.2 Clúster de venta: su buffer", "capas": ["pdv_IV"],
         "que": "Clic en un PDV: el círculo negro punteado es su buffer de 300 m y los anillos negros, los PDV con venta dentro (su clúster de venta). La ficha trae la media de W del buffer.",
         "porque": "Cada tienda se mide contra las que compiten por los mismos hogares. Si es la única con venta en su buffer, queda L.",
         "formula": "I^V_i = 100 · W_i / media(W_j : j ∈ C_i) ;  |C_i| = 1 → L", "cifras": f"{pct(s.solo, s.solo.eq('Sí'))} de los PDV con venta están solos en su buffer."},
        {"titulo": "2.3 Rappi mueve su venta (300 m)", "capas": ["rappi_300", "pdv_R", "rappi"],
         "que": f"Cada tienda Rappi activa (rojo, ≥ {THETA} pedidos de sueros o derivados; tamaño = cajas/mes) pasa su venta a cajas ({BOT} botellas "
                "por caja) y la reparte en partes iguales entre los PDV con venta de su radio (verde; tamaño = cajas/mes que recibe). Clic en una tienda Rappi: los PDV que la reciben.",
         "porque": "Rappi premia a la locación moviendo su venta: es venta observada de la categoría que Bepensa no ve. Se reparte para no contar dos veces la misma venta.",
         "formula": f"S_r = botellas_r / meses / {BOT} ;  R_i = Σ_r S_r / |D_r|   (D_r = PDV con venta a ≤ {R300} m de r)",
         "cifras": f"{(s.Rm[s.W.notna()] > 0).mean():.1%} de los PDV con venta la reciben (mediana {s.Rm[s.Rm > 0].median():.2f} cajas/mes)."},
        {"titulo": "2.4 Letra 2 (venta + CP + Rappi vs su buffer)", "capas": ["pdv_L2"],
         "que": "H si el PDV tiene al menos otro PDV con venta en su buffer y su venta + CP + la venta Rappi movida supera la media del buffer, que también lleva la venta Rappi de cada PDV.",
         "porque": "La media del clúster de venta también se mueve con Rappi (regla del usuario): cada PDV se compara con sus vecinos con la misma vara; Rappi puede subir o bajar una letra.",
         "formula": "I^V*_i = 100 · (W_i + R_i) / media(W_j + R_j : j ∈ C_i) ;  L2 = H si |C_i| ≥ 2 e I^V* > 100",
         "cifras": f"L2 = H en {pct(s.L2, s.L2.eq('H'))}; por Rappi suben {int(s.sube.sum())} y bajan {int(s.baja.sum())}."},
        {"titulo": "3. Letras finales y acción Golden Stores", "capas": ["pdv_cl"],
         "que": "Letra 1 (con AltScore) + Letra 2 (con Rappi) con la acción fija de Golden Stores.", "porque": "HH Atacar · HL Bloquear · LH Fortalecer · LL Mantener.",
         "formula": "letras = L1 + L2", "cifras": " ".join(f"{c} {pct(s.letras, s.letras.eq(c))}" for c in CL)},
        {"titulo": "3b. Letras base (INEGI + CP)", "capas": ["pdv_base"],
         "que": "Las mismas letras sin AltScore ni Rappi: Letra 1 solo con INEGI y Letra 2 solo con la venta media y el CP.",
         "porque": "Muestra qué PDV cambian de acción por las dos fuentes que mueven las letras.",
         "cifras": f"mismas letras en {pct(s.letras, s.letras.notna() & s.letras.eq(s.lb))} de los PDV objetivo."},
    ]


g = ids[ids.con_nse]
si_no = {True: "Sí", False: "No"}
pdv_js = pd.DataFrame({
    "id": g.pos_id_cp.astype(str), "nombre": g.Nombre.astype(str).str.replace("ABARRROTES", "ABARROTES"), "segmento": g.segmento,
    "lat": g.Latitud.round(6), "lon": g.Longitud.round(6), "cl": g.cluster_nse, "ncln": g.n_cluster_nse, "dcen": g.dist_centro_m.round(0),
    "hog": g.HH_cluster.round(0), "N_punto": g.N_punto.round(2), "N_ageb": g.N_ageb.round(2), "Ni": g.N_inegi.round(2), "clase": g.nse_clase,
    "pb": g.nse_bajo.round(0), "pm": g.nse_medio.round(0), "pa": g.nse_alto.round(0), "abc": g.abc.round(1), "censo": g.censo_area.round(0),
    "alt": g.alt_cluster.round(0), "N_alt": g.N_alt.round(2), "N": g.N.round(2), "I_N": g.I_N.round(0), "L1": g.L1, "L1s": g.L1_sin_alt,
    "altc": pd.Series(np.select([g.sube_por_alt, g.baja_por_alt], ["sube a H", "baja a L"], "no"), index=g.index).where(g.objetivo),
    "conf": pd.Series(g.nse_confirmado, index=g.index).map(si_no), "V": g.V.round(2), "CPo": g.CP_original.round(2).where(g.con_venta),
    "CP": g.CP.where(g.con_venta), "W": g.W.round(2), "ncl": g.n_cluster.where(g.con_venta), "Wm": g.W_media_cluster.round(2), "I_V": g.I_V.round(0),
    "solo": g.solo_en_cluster.map(si_no).where(g.con_venta), "nR": g.rappi_n, "R": g.rappi_venta.round(0), "RS": g.rappi_sueros.round(0),
    "Rm": g.R_mov.round(3).where(g.con_venta), "WR": g.WR.round(2), "P": g.P, "Ptxt": (g.R_mov > 0).map({True: "sí", False: "no"}),
    "WRm": g.WR_media_cluster.round(2), "I_V_star": g.I_V_star.round(0), "L2": g.L2, "L2s": g.L2_sin_rappi, "letras": g.letras, "lb": g.letras_base,
    "accion": g.accion, "clase_cp": g.clase_cp, "sube": g.sube_por_rappi, "baja": g.baja_por_rappi})
MAPA_QA = C.OUT / f"06_mapa_qa_letras_{C.CLIENTE}_{C.SLUG}.html"
MP.mapa_html(MAPA_QA, "QA de las letras · canal Tradicional", f"{C.CLIENTE.title()} · {C.ZM_NOMBRE} · sueros e hidratación · clúster NSE H3 res {RES_CL} + {R300} m",
             (g.Latitud.median(), g.Longitud.median()), {"pdv": pdv_js, "clusters": clusters_js, "rappi": rappi_js, "bepensa": bepensa_js}, CAPAS,
             pasos_qa(pdv_js), POPUP, hexagonos={"hex": hex_js, "cl": cl_js}, poligonos={"agebs": ageb_js, "municipios": mun_js}, radio_m=R300,
             filtro={"dataset": "pdv", "campo": "segmento", "valores": SUBCANALES, "etiqueta": "Subcanal"},
             distribucion_popup={"pdv": {"titulo": "Hogares de su clúster NSE (buffer de 300 m desde el centro)",
                                         "partes": [[e, k, col] for (e, _, col), k in zip(DIST_NSE3, ["pb", "pm", "pa"])]},
                                 "clusters": {"titulo": "Hogares del buffer de 300 m del clúster", "partes": DIST_NSE3}},
             cluster={"dataset": "clusters", "campo": "cl", "miembros": "pdv"})
for viejo in C.OUT.glob(f"06_mapa_qa_letras_*_{C.CLIENTE}_{C.SLUG}.html"):   # versiones anteriores (un mapa por canal)
    viejo.unlink()
print(f"Mapa: {MAPA_QA.name} ({MAPA_QA.stat().st_size / 1e6:.1f} MB, {len(pdv_js):,} PDV Tradicional, {len(clusters_js):,} clústeres NSE: "
      + ", ".join(f"{k.title()} {v:,}" for k, v in pdv_js.segmento.value_counts().items()) + ")")

# %% [markdown]
# ## 5. Entregable Excel para el cliente (canal Tradicional): de dónde sale cada columna
#
# Estructura pedida por el usuario (2026-09-30): `pos_id` · **AltScore** · **datos gubernamentales (INEGI)** · **ventas** (venta
# media y CP del CP, Rappi y la media del clúster de venta) · **clúster** (NSE y de venta) · **letra 1** · **letra 2** (el share
# y su priorización se omiten por ahora) y, al final, las letras juntas con su acción Golden Stores. Cada letra va **sin y
# con** su fuente adicional. Una tercera fila de encabezado dice **de dónde sale** cada columna y la hoja **Fuentes** lo
# detalla con su cálculo. Va a la carpeta del cliente (`outputs/<ciudad>/<cliente>/cliente/`).

# %%
import excel_kin as X

hallazgos06 = pd.DataFrame([
    ("Universo", UNIVERSO, "Las letras se calculan en los PDV objetivo; los PDV sin venta reciben Letra 1 para prospección."),
    ("1.1 NSE del punto", PUNTO, "El NSE del punto hereda el de su AGEB: la letra se toma del clúster NSE."),
    ("1.2 Variante INEGI (Censo por manzana)", f"{VALIDEZ} η² por AGEB = {eta2:.2f} (α = {alfa_censo:.2f}).",
     "El NSE AMAI se confirma con una medición directa; lo que no coincide queda como 'NSE a revisar'."),
    ("1.3 Clúster NSE (hexágono + 300 m)", CLUSTER_NSE, "Todos los PDV del hexágono comparten su Letra 1 (su NSE); la Letra 2 es de cada PDV."),
    ("1.3b NSE predominante (bajo / medio / alto)", PREDOMINANTE, "La Letra 1 es relativa (contra la media de su subcanal); el NSE predominante es absoluto."),
    ("1.4 AltScore mueve el NSE", ALT_NSE, f"El peso λ = {LAM:g} está por validar con el usuario (ver hoja Sensibilidad AltScore)."),
    ("1.5 Letra 1", LETRA1, "Leer junto con 'NSE confirmado' y 'AltScore cambia la letra'."),
    ("2.1 Venta + CP (los dos del CP)", VENTA, "La venta y el potencial salen del CP (no el archivo de ventas); el potencial entra en cajas enteras (umbral 0.6)."),
    ("2.2 Clúster de venta", CLUSTER, "El único con venta en su buffer queda L: no hay con quién compararlo."),
    ("2.3 Rappi mueve su venta", RAPPI, f"Rappi solo mueve venta donde hay tiendas Rappi activas (zona urbana central); la conversión a cajas "
                                        f"({BOT} botellas por caja) está por confirmar con Bepensa."),
    ("2.4 Respaldo y sensibilidad", f"{RESPALDO} {SENS}", "Ver la hoja Sensibilidad Rappi (botellas por caja, tiendas Rappi y reparto)."),
    ("2.5 Letra 2", LETRA2, "Leer junto con 'Solo con venta en su buffer' y la venta Rappi movida."),
    ("3. Letras juntas", LETRAS, "La acción de cada combinación de letras es la fija de Golden Stores (Atacar, Bloquear, Fortalecer, Mantener)."),
], columns=["tema", "hallazgo", "implicación"])
with pd.option_context("display.max_colwidth", None):
    display(hallazgos06)

FORMULAS = [
    ("Clúster NSE (Letra 1)", [
        f"La ZM se divide en hexágonos H3 de res {RES_CL} (arista ≈ 174 m, ≈ 0.1 km²). Cada hexágono con PDV es un clúster NSE: su centro es el punto NSE.",
        f"A_c = hexágonos H3 res 10 cuyo centro está a ≤ {R300} m del centro del clúster c (≈ 19 hexágonos, ≈ 0.28 km²): su buffer. Todo PDV queda a ≤ {ids.dist_centro_m.max():.0f} m del centro de su hexágono.",
        "Todos los PDV del hexágono comparten el NSE de su clúster (la Letra 1 es del clúster, no del PDV); la Letra 2 es de cada PDV."]),
    ("Letra 1 · NSE del clúster (INEGI, movido por AltScore)", [
        "HH_ck = Σ_{h ∈ A_c} HH_hk = hogares 2025 del nivel NSE k en el buffer. Cada manzana reparte sus hogares por área entre los hexágonos que toca, con la distribución NSE AMAI de su AGEB (notebooks 01 y 04).",
        "p_ck = HH_ck / Σ_k HH_ck   ·   N_c = Σ_k k · p_ck, con k = 1 D/E, 2 D+, 3 C−, 4 C, 5 C+, 6 A/B (nivel NSE INEGI: media de 1 a 6).",
        "NSE predominante del clúster = el grupo con más hogares del buffer: bajo (D+ y D/E), medio (C y C−) o alto (C+ y A/B). Es absoluto; la Letra 1 es relativa (contra la media de su subcanal).",
        f"a_c = media del índice NSE AltScore (percentil 0-100; PC1 de {', '.join(PROX_ALT) or 'sus proxies'}, notebook 00b) de los puntos AltScore a ≤ {R300} m del centro.",
        f"Ñ_c = a_c llevado a la escala de N por cuantiles (el valor de N con el mismo percentil). N*_c = (1 − λ)·N_c + λ·Ñ_c con λ = {LAM:g}; si el buffer tiene menos de {MIN_ALT} puntos AltScore con índice, N*_c = N_c.",
        "I^N_i = 100 · N*_c(i) / media de N* en los PDV objetivo de su subcanal s(i). Letra 1 = H si I^N_i ≥ 100; L si I^N_i < 100. Letra 1 sin AltScore: la misma regla con N_c.",
        "Se asegura con variantes (misma regla): % ABC+ del clúster, índice del Censo por manzana (auto, computadora, internet, escolaridad), NSE del punto, NSE de la AGEB, el buffer del propio PDV y buffers de 200 y 400 m. 'NSE confirmado' = coincide con la del Censo."]),
    ("Letra 2 · Venta media + CP + venta Rappi movida contra su clúster de venta (reglas del usuario)", [
        "V_i = venta media del PDV según el CP: PotentialQuantitative_TotalPortafolio (cajas/mes). Solo datos del CP (regla del usuario, 2026-09-30).",
        f"CP_i = PotentialQuantitativeFinal_TotalPortafolio (cajas/mes que le faltan frente a su PDV comparable) en cajas enteras: hacia abajo si el decimal < {C.CP_UMBRAL_REDONDEO} (0.59 → 0 · 1.55 → 1 · 1.6 → 2). W_i = V_i + CP_i.",
        f"C_i = clúster de venta: PDV con venta (canal Tradicional) dentro del buffer de {R300} m del PDV, incluido él. Media del clúster = media de W en C_i.",
        "I^V_i = 100 · W_i / media del clúster de venta.",
        f"Rappi premia a la locación moviendo su venta: S_r = botellas de sueros e hidratación de la tienda Rappi activa r (≥ {THETA} pedidos, "
        f"ene-2025 → ago-2026) / meses de vida / {BOT} botellas por caja = cajas/mes (un empaque múltiple cuenta sus botellas por precio).",
        f"D_r = PDV con venta a ≤ {R300} m de r. R_i = Σ_r S_r / |D_r|: la venta de cada tienda Rappi se reparte en partes iguales entre los PDV de su radio (no se cuenta dos veces).",
        "I^V*_i = 100 · (W_i + R_i) / media de (W + R) en C_i: la media del clúster de venta también se mueve con Rappi (regla del usuario, 2026-09-30); "
        "cada PDV se compara con sus vecinos con la misma vara, así que Rappi puede subir o bajar una letra.",
        "Letra 2 = H si el clúster de venta tiene al menos 2 PDV (el PDV y otro con venta) e I^V*_i > 100; en otro caso L. El único con venta en su buffer queda L."]),
    ("Letras juntas", ["Letras finales = Letra 1 (con AltScore) + Letra 2 (con Rappi); letras base = Letra 1 sin AltScore + Letra 2 sin Rappi (solo INEGI + CP).",
                       "Acción fija de Golden Stores: HH Atacar · HL Bloquear · LH Fortalecer · LL Mantener."]),
    ("Parámetros (src/config.py)", [f"RADIO_PDV_M = {R300} · NSE_CLUSTER_RES = {RES_CL} · H3_RES = {C.H3_RES} · ALTSCORE_PESO_NSE (λ) = {LAM:g} · ALTSCORE_MIN_PUNTOS = {MIN_ALT} · "
                                    f"RAPPI_BOTELLAS_CAJA (b) = {BOT} · RAPPI_MIN_PEDIDOS (θ) = {THETA} · FRONTERA = {FR} · CP_UMBRAL_REDONDEO = {C.CP_UMBRAL_REDONDEO}."]),
]

# bloque AltScore: índice, su escala 1-6 y las señales que el 00b dejó pasar (reglas R1-R6), en el buffer del clúster NSE
ALT_COLS = {"Índice NSE AltScore del clúster (0-100)": "alt_cluster", "Puntos AltScore con índice en el buffer": "alt_puntos",
            "NSE AltScore en escala 1-6": "N_alt", **{A.corto(s_): f"alt_{s_}" for s_ in ALT_SEN}}
ALT_BLOQUE = "AltScore (buffer del clúster NSE)" if USA_ALTSCORE else "AltScore (pendiente: la exportación no trae ubicación)"
GOB = "Datos gubernamentales (INEGI)"
VEN = "Ventas (venta media y potencial del CP · Rappi · media del clúster de venta)"
CLU = "Clúster (NSE: hexágono H3 + 300 m · venta: buffer del PDV)"
ORIGEN = {}                                                   # (bloque, columna) -> de dónde sale (tercera fila y hoja Fuentes)


def tabla_pdv(d):
    """Tabla del entregable en el orden pedido: PDV · AltScore · datos gubernamentales · ventas · clúster · letra 1 · letra 2."""
    b = {}

    def col(bloque, nombre, valores, origen):
        b[(bloque, nombre)] = valores.to_numpy() if hasattr(valores, "to_numpy") else valores
        ORIGEN[(bloque, nombre)] = origen

    P_ = "Punto de venta (CP)"
    col(P_, "pos_id", d.pos_id_cp, "CP Bepensa (pos_id)")
    col(P_, "Nombre", d.Nombre.astype(str).str.replace("ABARRROTES", "ABARROTES"), "CP Bepensa (pos_name)")
    col(P_, "Subcanal", d.Subcanal, "CP Bepensa (pos_subchannel)")
    col(P_, "Latitud", d.Latitud, "CP Bepensa (pos_latitude, limpia en el 00)")
    col(P_, "Longitud", d.Longitud, "CP Bepensa (pos_longitude, limpia en el 00)")
    for nombre, c_ in ALT_COLS.items():
        valores = d[c_].round(3) if c_ in d.columns else pd.Series(np.nan, index=d.index)
        origen = {"alt_cluster": f"AltScore · PC1 de {', '.join(PROX_ALT) or 'sus proxies'} (00b), media de sus puntos a ≤ {R300} m del centro del clúster",
                  "alt_puntos": f"AltScore · puntos con índice a ≤ {R300} m del centro del clúster",
                  "N_alt": "AltScore en la escala de N (1-6) por cuantiles: el que mueve el NSE"}.get(c_, "AltScore · señal seleccionada R1-R6 (00b), media del buffer del clúster")
        col(ALT_BLOQUE, nombre, valores, origen + ("" if USA_ALTSCORE else " · falta la ubicación"))
    tot = hh.loc[d.index].sum(axis=1)
    col(GOB, "Municipio", d.Municipio, "Marco Geoestadístico INEGI (polígono)")
    col(GOB, "Hogares del clúster (buffer de 300 m)", d.HH_cluster.round(0), "INEGI Censo 2020 manzanas + ITER · ×EIC 2025 · reparto por área (04)")
    for c in NSE:
        col(GOB, f"% {c}", (hh.loc[d.index, c] / tot.where(tot > 0) * 100).round(1), "INEGI · NSE AMAI 2024 (Censo + ENIGH 2024) en el buffer del clúster")
    col(GOB, "Nivel NSE INEGI del clúster (media, 1 = D/E … 6 = A/B)", d.N_inegi.round(2), "Σ k·p_k: promedia hogares mezclados (casi siempre 2.5-4.5)")
    for g_, e_ in [("bajo", "% bajo (D+ y D/E)"), ("medio", "% medio (C y C−)"), ("alto", "% alto (C+ y A/B)")]:
        col(GOB, e_, d[f"nse_{g_}"].round(1), "INEGI · hogares del buffer del clúster por grupo")
    col(GOB, "NSE predominante del clúster", d.nse_clase, "grupo con más hogares del buffer: bajo (D+, D/E) · medio (C, C−) · alto (C+, A/B)")
    col(GOB, "% de hogares del grupo predominante", d.nse_clase_pct.round(0), "INEGI · hogares del buffer del clúster")
    col(GOB, "NSE del punto (hexágono res 10)", d.N_punto.round(2), "INEGI · hexágono H3 res 10 del PDV")
    col(GOB, "NSE de su AGEB", d.N_ageb.round(2), "INEGI · AGEB que contiene al PDV")
    col(GOB, "% ABC+ del clúster", d.abc.round(1), "INEGI · A/B + C+ en el buffer del clúster")
    col(GOB, "Índice Censo por manzana (0-100)", d.censo_area.round(0), "INEGI Censo 2020 · auto, PC, internet, escolaridad")
    col(GOB, "NSE confirmado por el Censo", pd.Series(d.nse_confirmado, index=d.index).map(si_no), "letra con el Censo = letra 1 final")
    col(VEN, "Venta media (cajas/mes)", d.V.round(2), "CP Bepensa · PotentialQuantitative_TotalPortafolio")
    col(VEN, "CP · potencial original (cajas/mes)", d.CP_original.round(2).where(d.con_venta), "CP Bepensa · PotentialQuantitativeFinal_TotalPortafolio")
    col(VEN, "CP · potencial en cajas enteras", d.CP.where(d.con_venta), f"el que se usa: hacia abajo si el decimal < {C.CP_UMBRAL_REDONDEO}")
    col(VEN, "CP · clase de potencial", d.clase_cp, "CP Bepensa · PotentialQualitative_TotalPortafolio")
    col(VEN, "Venta media + CP", d.W.round(2), "venta media + potencial CP")
    col(VEN, "Rappi · tiendas activas a 300 m", d.rappi_n, f"Rappi (00c) · ≥ {THETA} pedidos de sueros o derivados")
    col(VEN, "Rappi · venta a 300 m (MXN/mes)", d.rappi_venta.round(0), "Rappi · sueros e hidratación de las tiendas activas del radio")
    col(VEN, "Rappi · venta movida al PDV (cajas/mes)", d.R_mov.round(3).where(d.con_venta),
        f"Rappi · venta de cada tienda en cajas ({BOT} botellas) repartida entre los PDV de su radio")
    col(VEN, "Venta media + CP + Rappi", d.WR.round(2), "venta media + potencial CP + venta Rappi movida")
    col(VEN, "Media (venta media + CP) de su clúster de venta, sin Rappi", d.W_media_cluster.round(2), "referencia: media de los PDV con venta de su buffer, sin Rappi")
    col(VEN, "Media (venta media + CP + Rappi) de su clúster de venta", d.WR_media_cluster.round(2), "la que se usa: media de su buffer con la venta Rappi de cada PDV")
    col(VEN, "Índice vs su clúster de venta (con Rappi)", d.I_V_star.round(0), "100 · (venta media + CP + Rappi) / media con Rappi")
    col(CLU, "Clúster NSE (H3 res 9)", d.cluster_nse, "hexágono H3 que contiene al PDV: su centro es el punto NSE")
    col(CLU, "PDV del clúster NSE", d.n_cluster_nse, "PDV Tradicional del mismo hexágono (comparten la Letra 1)")
    col(CLU, "Distancia al centro del clúster (m)", d.dist_centro_m.round(0), f"siempre ≤ {R300} m: el buffer lo contiene")
    col(CLU, "PDV con venta en su buffer (clúster de venta)", pd.Series(d.n_cluster, index=d.index).where(d.con_venta), "PDV con venta a ≤ 300 m del PDV")
    col(CLU, "Solo con venta en su buffer (→ L)", d.solo_en_cluster.map(si_no).where(d.con_venta), "único con venta en su buffer")
    col("Letra 1", "Nivel NSE final (INEGI + AltScore)", d.N.round(2), f"N* = {1 - LAM:g} · INEGI + {LAM:g} · AltScore (escala 1-6)")
    col("Letra 1", "Índice NSE (100 = media del subcanal)", d.I_N.round(0), "100 · N* / media del subcanal")
    col("Letra 1", "Letra 1 sin AltScore", d.L1_sin_alt, "solo INEGI: H si su índice ≥ 100")
    col("Letra 1", "Letra 1 con AltScore (final)", d.L1, "H si el índice NSE final ≥ 100")
    col("Letra 1", "AltScore cambia la letra", pd.Series(np.select([d.sube_por_alt, d.baja_por_alt], ["sube a H", "baja a L"], "no"),
                                                         index=d.index).where(d.L1.notna()), "letra 1 con AltScore vs sin AltScore")
    col("Letra 2", "Letra 2 sin Rappi", d.L2_sin_rappi.fillna("sin venta"), "venta media + CP vs la media de su buffer, sin Rappi")
    col("Letra 2", "Letra 2 con Rappi (final)", d.L2.fillna("sin venta"), "H si ≥ 2 con venta en su buffer e índice con Rappi > 100")
    col("Letra 2", "Rappi cambia la letra", pd.Series(np.select([d.sube_por_rappi, d.baja_por_rappi], ["sube a H", "baja a L"], "no"),
                                                   index=d.index).where(d.objetivo), "letra 2 con Rappi vs sin Rappi")
    col("Clasificación", "Letras base (INEGI + CP)", d.letras_base, "letra 1 sin AltScore + letra 2 sin Rappi")
    col("Clasificación", "Letras (final)", d.letras, "letra 1 con AltScore + letra 2 con Rappi")
    col("Clasificación", "Acción Golden Stores", d.accion, "HH Atacar · HL Bloquear · LH Fortalecer · LL Mantener")
    t = pd.DataFrame(b)
    t.columns = pd.MultiIndex.from_tuples(t.columns)
    return t


COLORES = {"Punto de venta (CP)": X.NEGRO, ALT_BLOQUE: "4A3AA7", GOB: "1F3A5F", VEN: "1E5B45", CLU: "333333",
           "Letra 1": X.NEGRO, "Letra 2": X.NEGRO, "Clasificación": "333333"}
FMT = {"Latitud": "0.000000", "Longitud": "0.000000", "Hogares del clúster (buffer de 300 m)": "#,##0", "Venta media (cajas/mes)": "#,##0.00",
       "CP · potencial original (cajas/mes)": "#,##0.00", "CP · potencial en cajas enteras": "#,##0", "Venta media + CP": "#,##0.00",
       "Media (venta media + CP) de su clúster de venta, sin Rappi": "#,##0.00", "Media (venta media + CP + Rappi) de su clúster de venta": "#,##0.00",
       "Rappi · venta movida al PDV (cajas/mes)": "#,##0.000", "Venta media + CP + Rappi": "#,##0.00", "Distancia al centro del clúster (m)": "#,##0",
       "Rappi · venta a 300 m (MXN/mes)": "#,##0", **{f"% {c}": "0.0" for c in NSE}}
C.OUT_CLIENTE.mkdir(parents=True, exist_ok=True)
for viejo in C.OUT.glob(f"06_letras_nse_ventas_*_{C.CLIENTE}_{C.SLUG}.xlsx"):   # antes iban en la carpeta de análisis
    viejo.unlink()
d = ids
TABLA = tabla_pdv(d.sort_values(["letras", "W"], ascending=[True, False]))
fuentes = pd.DataFrame([{"bloque": k[0], "columna": k[1], "de dónde sale": v} for k, v in ORIGEN.items()]).drop_duplicates(["bloque", "columna"])
tabla_cl = cl[cl.n_pdv > 0].assign(**{"L1 = H (PDV objetivo)": ob.groupby("cluster_nse").L1.agg(lambda s: int((s == "H").sum()))})
tabla_cl = tabla_cl.reset_index()[["cluster_nse", "lat", "lon", "n_pdv", "n_objetivo", "hog", "N", "clase", "p_bajo", "p_medio", "p_alto", "abc", "censo",
                                   "alt", "alt_puntos", "N_alt", "N_star", "L1 = H (PDV objetivo)"]].rename(columns={
    "cluster_nse": "clúster NSE (H3 res 9)", "lat": "latitud del centro", "lon": "longitud del centro", "n_pdv": "PDV", "n_objetivo": "PDV objetivo",
    "hog": "hogares del buffer", "N": "nivel NSE INEGI", "clase": "NSE predominante", "p_bajo": "% bajo", "p_medio": "% medio", "p_alto": "% alto",
    "abc": "% ABC+", "censo": "índice Censo", "alt": "índice AltScore", "alt_puntos": "puntos AltScore", "N_alt": "NSE AltScore (1-6)", "N_star": "nivel NSE final"})
wb = X.libro()
X.hoja_tabla_2niveles(wb, "Letras por PDV", TABLA, titulo="Letras por punto de venta · canal Tradicional",
                      nota="pos_id · AltScore · INEGI · ventas (venta media, CP, Rappi, media del clúster de venta) · clúster (NSE y de venta) · letra 1 · letra 2 · acción Golden Stores. "
                           "La 3.ª fila dice de dónde sale cada columna; fórmulas en la hoja Fórmulas.",
                      formatos=FMT, anchos={"Nombre": 30}, colores_grupo=COLORES, fijar_cols=2,
                      fuentes={k: v for k, v in ORIGEN.items() if k in set(TABLA.columns)})
X.hoja_tabla(wb, "Fuentes", fuentes, titulo="De dónde sale cada columna del entregable",
             nota="Fuentes: CP de Bepensa (PDV, venta y potencial) · INEGI (Censo 2020, ITER, Marco Geoestadístico, ENIGH 2024, Intercensal 2025) · AltScore · Rappi.",
             anchos={"bloque": 44, "columna": 44, "de dónde sale": 70})
X.hoja_texto(wb, "Fórmulas", FORMULAS)
X.hoja_tabla(wb, "Resumen", panorama.reset_index().rename(columns={"letras": "Letras"}).round(1), titulo="Letras finales y acción Golden Stores · canal Tradicional",
             cluster_col="Letras", nota="% tiendas, % mix de ventas e Index ventas (venta media de las letras / venta media del canal × 100), N medio, hogares del clúster y % que reciben venta Rappi.",
             formatos={"tiendas": "#,##0", "cajas": "#,##0.0", "media": "0.00", "N_medio": "0.00", "hogares": "#,##0"})
X.hoja_tabla(wb, "Base vs final", cruce.reset_index().rename(columns={"letras base (INEGI + CP)": "letras base (INEGI + CP) → finales"}),
             titulo="Letras base (INEGI + CP) contra letras finales (con AltScore y Rappi)", nota=LETRAS)
X.hoja_tabla(wb, "Clústeres NSE", tabla_cl.round(2), titulo=f"Clústeres NSE: hexágonos H3 res {RES_CL} con PDV y el NSE de su buffer de {R300} m",
             nota=CLUSTER_NSE, formatos={"latitud del centro": "0.000000", "longitud del centro": "0.000000", "hogares del buffer": "#,##0"})
X.hoja_tabla(wb, "QA Letra 1", conc.round(3), titulo="¿La Letra 1 se sostiene? Concordancia con cada variante (contra la letra INEGI y la final)",
             nota=f"κ de Cohen (≥ 0.6 bueno). {VALIDEZ}", anchos={"variante": 48})
X.hoja_tabla(wb, "Sensibilidad AltScore", sens_alt.round(2), titulo="Cuánto mueve AltScore la Letra 1 según su peso λ", nota=ALT_NSE)
X.hoja_tabla(wb, "QA Letra 2", qa_l2.round(3), titulo="¿Cuánto cambia la Letra 2 con cada decisión?", nota=LETRA2, anchos={"comparación": 56})
X.hoja_tabla(wb, "Sensibilidad Rappi", sens.round(1), titulo="Sensibilidad de la venta Rappi movida", nota=SENS,
             anchos={"tiendas Rappi que mueven su venta": 34, "reparto": 62})
if len(respaldo):
    X.hoja_tabla(wb, "Respaldo Rappi", respaldo.round(3), titulo="Venta Bepensa con y sin tienda Rappi activa a 300 m, por subcanal",
                 nota="δ de Cliff sobre log1p(cajas/mes); IC95 por bootstrap de bloques H3 res 7.", anchos={"subcanal": 40})
X.hoja_tabla(wb, "Rappi a 300 m", act.assign(turbo=act.turbo.map(si_no))[
    ["nombre", "tipo", "municipio", "lat", "lon", "venta_mes", "venta_sueros_mes", "cajas_mes", "pedidos", "% sueros", "% Coca-Cola", "turbo",
     "pdv_que_reciben", "cajas_por_pdv"]].round({"lat": 6, "lon": 6, "cajas_mes": 2, "cajas_por_pdv": 3}).round(1)
             .sort_values("cajas_mes", ascending=False), titulo="Tiendas Rappi activas (sueros e hidratación): su venta en cajas y los PDV que la reciben",
             nota=f"cajas_mes = botellas / meses de vida / {BOT} botellas por caja; se reparte en partes iguales entre los PDV con venta a ≤ {R300} m.",
             formatos={"venta_mes": "#,##0", "venta_sueros_mes": "#,##0", "cajas_mes": "0.00", "cajas_por_pdv": "0.000", "lat": "0.000000", "lon": "0.000000"},
             barras=["cajas_mes"], anchos={"nombre": 42})
sin = d[d.con_venta & ~d.con_nse][["pos_id_cp", "Nombre", "Subcanal", "Latitud", "Longitud", "Municipio", "cluster_nse", "V"]]
X.hoja_tabla(wb, "Sin NSE en su clúster", sin.round(4), titulo="PDV con venta cuyo clúster NSE no tiene hogares a 300 m (no reciben letras)",
             nota="Zonas comerciales o no urbanas: no reciben letras; no desaparecen.", formatos={"Latitud": "0.000000", "Longitud": "0.000000"})
X.hoja_tabla(wb, "Hallazgos", hallazgos06.rename(columns=str.capitalize), titulo="Hallazgos del notebook 06", ajustar=True,
             anchos={"Tema": 28, "Hallazgo": 100, "Implicación": 55})
X.portada(wb, "Letras por punto de venta", f"Canal Tradicional · {C.CLIENTE.title()} · {C.ZM_NOMBRE} · sueros e hidratación · radio {R300} m",
          [("Universo", UNIVERSO),
           ("Letra 1 · NSE", f"NSE de su clúster NSE (hexágono H3 res {RES_CL} + buffer de {R300} m desde su centro): nivel NSE AMAI de sus hogares, movido por "
                             f"AltScore (λ = {LAM:g}), vs la media del subcanal; asegurado con el Censo por manzana y otras variantes."),
           ("Letra 2 · Ventas", f"Venta media + potencial (los dos del CP; potencial en cajas enteras) + venta Rappi movida vs la media de su clúster de venta "
                                f"(PDV con venta a ≤ {R300} m); el único con venta queda L."),
           ("Resultado", " · ".join(f"{c} {(ob.letras == c).mean():.0%}" for c in CL) + f" · AltScore cambia {int(ob.cambia_por_alt.sum())} Letras 1 y Rappi "
                         f"{int(ob.cambia_por_rappi.sum())} Letras 2."),
           ("Mapa de QA", f"{MAPA_QA.relative_to(BASE).as_posix()} (se abre en el navegador; filtro por subcanal)."),
           ("Elaboró", "Kin Analytics · notebooks/_src/06_letras_nse_ventas.py")],
          [("Letras por PDV", "Una fila por PDV: pos_id · AltScore · INEGI · ventas · clúster · letra 1 · letra 2 · acción."),
           ("Fuentes", "De dónde sale cada columna."), ("Fórmulas", "Cómo se calcula cada letra."), ("Resumen", "Tiendas, mix de ventas e index por letras."),
           ("Base vs final", "Qué cambian AltScore y Rappi."), ("Clústeres NSE", "Un renglón por hexágono con su NSE."),
           ("QA Letra 1", "Concordancia con variantes."), ("Sensibilidad AltScore", "Peso de AltScore en el NSE."),
           ("QA Letra 2", "Efecto del CP y de Rappi."), ("Sensibilidad Rappi", "Botellas por caja, tiendas Rappi y reparto."),
           ("Respaldo Rappi", "Venta con y sin Rappi cerca."), ("Rappi a 300 m", "Tiendas Rappi activas y a quién mueven su venta."),
           ("Sin NSE en su clúster", "PDV excluidos."), ("Hallazgos", "Qué se encontró y qué implica.")])
XLSX = C.OUT_CLIENTE / f"06_letras_nse_ventas_tradicional_{C.CLIENTE}_{C.SLUG}.xlsx"
wb.save(XLSX)
print(f"Excel: {XLSX.name} ({len(d):,} PDV Tradicional, {int(d.objetivo.sum()):,} objetivo)")

# %% [markdown]
# ## 6. Presentación de las letras (estilo Kin, carpeta del cliente)
#
# Estructura del entregable del usuario (2026-09-30): pos_id · AltScore · INEGI · venta · CP · Rappi · clúster · Letra 1 ·
# Letra 2 (el share y su priorización se omiten por ahora), solo canal Tradicional. Contado como pitch ejecutivo: resumen
# primero; el **clúster NSE** (hexágono + buffer de 300 m) y el **clúster de venta** (buffer del PDV); cómo sale cada letra y
# qué mueven AltScore y Rappi; el resultado; tiendas reales como ejemplo; el QA y lo que falta validar. Titulares con cifras
# calculadas y guion en las notas de cada lámina.

# %%
import io
import deck_kin as K
from pptx.util import Inches


def imagen(slide, fig, x, y, w, h):
    """Inserta una figura de matplotlib (PNG a 200 dpi) dentro de la caja w × h sin deformarla, centrada, y la cierra."""
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    ancho_px, alto_px = Image.open(buf).size
    escala = min(w / ancho_px, h / alto_px)
    buf.seek(0)
    slide.shapes.add_picture(buf, Inches(x + (w - ancho_px * escala) / 2), Inches(y), width=Inches(ancho_px * escala))


def fig_mapa(columna, colores, etiquetas, tam=(6.2, 5.6)):
    """Mapa de la ZM con los PDV objetivo coloreados por `columna`."""
    fig, ax = plt.subplots(figsize=tam)
    MP.fondo(ax, mun, agebs=ageb_c)
    gg = pts[ids.objetivo].join(ids[[columna]])
    for v_, col_ in colores.items():
        sub = gg[gg[columna] == v_]
        sub.plot(ax=ax, color=col_, markersize=3.5, alpha=0.85, label=f"{etiquetas.get(v_, v_)} ({len(sub):,})")
    ax.set_xlim(x0 - 800, x1 + 800); ax.set_ylim(y0 - 800, y1 + 800)
    ax.legend(loc="lower left", fontsize=9, markerscale=3, frameon=True)
    return fig


def fig_venta(i_, titulo, tam=(5.4, 5.0)):
    """El clúster de venta de un PDV: su buffer de 300 m con los PDV con venta dentro (verde = sobre la media con Rappi)."""
    fig, ax_ = plt.subplots(figsize=tam)
    panel_buffer(ax_, i_, titulo)
    xx, yy = pts.geometry.iloc[i_].x, pts.geometry.iloc[i_].y
    rr = ids.iloc[i_]
    mismo = pts[ids.con_venta & pts.geometry.within(Point(xx, yy).buffer(R300))].join(ids[["WR"]])
    mismo.plot(ax=ax_, color=[MP.COLOR_L2["H" if v > rr.WR_media_cluster else "L"] for v in mismo.WR], markersize=np.clip(mismo.WR * 8, 10, 320),
               edgecolor=eda.TINTA, lw=0.8, zorder=5)
    return fig, ax_, rr


tr = ob
hh_n, hh_mix, hh_idx = int(panorama.loc["HH", "tiendas"]), panorama.loc["HH", "% mix ventas"], panorama.loc["HH", "Index ventas"]
lh_mix = panorama.loc["LH", "% mix ventas"]
solo_tr = ob.solo_en_cluster.mean()
confirmado = conf_final
sens_base = sb["PDV que cambian por Rappi"]                                  # letras que cambia Rappi según las botellas por caja
n_alt, n_rap = int(ob.cambia_por_alt.sum()), int(ob.cambia_por_rappi.sum())
alt_05 = int(sa.loc[0.5, "PDV que cambian"]) if 0.5 in sa.index else 0
prs = K.nueva()
s = K.portada(prs, ["Letras por", "punto de venta"], f"NSE × Ventas · Canal Tradicional · Sueros e hidratación · {C.ZM_NOMBRE}",
              "Cada PDV toma el NSE de su clúster (hexágono H3 + 300 m, movido por AltScore) y su venta lo califica frente a su buffer "
              "(movida por Rappi).", "Bepensa · Septiembre 2026")
K.notas(s, "Presentación del entregable de letras del canal Tradicional: dos letras por PDV, NSE y venta, con solo datos del CP para el PDV. "
           "La primera lámina trae la conclusión y lo que pedimos validar.")

# 1 · resumen ejecutivo (BLUF)
s, y = K.lamina(prs, f"Las {hh_n:,} tiendas HH (NSE alto y venta sobre su buffer) hacen el {hh_mix:.0f}% de la venta del canal Tradicional",
                "Resumen ejecutivo",
                notas=(f"GUION 60 s: Clasificamos {len(ob):,} puntos de venta del canal Tradicional con dos letras y solo datos del CP para el PDV. "
                       f"La primera es el NSE de su clúster: la ZM se divide en hexágonos y cada hexágono toma el NSE de los hogares a 300 m de su centro "
                       f"(INEGI; el Censo por manzana lo confirma en {confirmado:.0%} de los casos); AltScore mueve ese NSE con peso {LAM:g}. La segunda es "
                       f"su venta: venta media más el potencial del CP más la venta que Rappi le mueve, contra la media de los PDV con venta de su buffer. "
                       f"Las {hh_n:,} HH venden {hh_idx - 100:+.0f}% sobre la media y hacen el {hh_mix:.0f}% de la venta. Pedimos validar tres puntos."))
for i_, (v_, e_, d_) in enumerate([(f"{len(ob):,}", "PDV Tradicional clasificados", "con venta en el CP y hogares en su clúster"),
                                   (f"{hh_n:,}", "HH · Atacar", f"{panorama.loc['HH', '% tiendas']:.0f}% de las tiendas"),
                                   (f"{hh_mix:.0f}%", "de la venta en HH", f"índice de venta {hh_idx:.0f}"),
                                   (f"{n_alt + n_rap}", "letras que cambian", f"AltScore {n_alt} · Rappi {n_rap}")]):
    K.cifra(s, K.MARGEN + i_ * 2.3, y + 0.05, 2.15, v_, e_, d_, h=1.1, oscura=(i_ == 0))
K.tarjeta(s, K.MARGEN, y + 1.35, 9.1, 1.4, "Qué pedimos validar hoy",
          f"1. Clúster NSE = hexágono H3 res {RES_CL} + buffer de {R300} m desde su centro (sus PDV comparten la Letra 1); la Letra 2 contra la media de "
          f"su buffer y el único con venta queda L ({solo_tr:.0%}).\n"
          f"2. AltScore mueve el NSE con peso {LAM:g}: cambia {n_alt} Letras 1 (con 0.5, {alt_05}).\n"
          f"3. Rappi → cajas: {BOT} botellas por caja (a confirmar); decide {n_rap} Letras 2 (con 6 botellas por caja, {int(sens_base.get(6, 0))}).", acento=True)
K.mensaje(s, "Cada columna del entregable dice de dónde sale: CP de Bepensa, INEGI, AltScore y Rappi.")

# 2 · de dónde sale cada columna (la estructura del entregable)
s, y = K.lamina(prs, "El entregable lee de izquierda a derecha: de dónde sale cada dato y cómo termina en dos letras", "Estructura del entregable",
                notas=("Es la estructura acordada: pos_id; AltScore; INEGI; venta y CP; Rappi; clúster; Letra 1 y Letra 2, cada una sin y con su "
                       "fuente adicional. Del PDV solo se usa el CP. El Excel agrega el detalle de cada bloque, con una tercera fila que dice de "
                       "dónde sale cada columna y la hoja Fuentes."))
bloques = [("pos_id", "Punto de venta", "CP Bepensa: id, nombre, subcanal, lat/lon (canal Tradicional)", K.NEGRO),
           ("AltScore", "Mueve el NSE", f"Índice NSE ({' y '.join(PROX_ALT) or 'proxies digitales'}) + {len(ALT_SEN)} señales del buffer del clúster", "4A3AA7"),
           ("INEGI", "NSE del clúster", "Hogares 2025 y % por NSE del buffer, NSE del punto y de su AGEB, Censo por manzana", "1F3A5F"),
           ("Venta + CP", "CP Bepensa", "Venta media + potencial del CP en cajas enteras (umbral 0.6)", "1E5B45"),
           ("Rappi", "Venta movida", "Sueros e hidratación de las tiendas activas a 300 m, en cajas, repartida", "1E5B45"),
           ("Clúster", "NSE y de venta", f"NSE: hexágono res {RES_CL} + {R300} m. Venta: PDV con venta del buffer del PDV", "333333"),
           ("Letra 1", "sin y con AltScore", "NSE del clúster ≥ media del subcanal", K.NEGRO),
           ("Letra 2", "sin y con Rappi", "Venta media + CP (+ Rappi) vs la media de su buffer", K.NEGRO),
           ("Acción", "Golden Stores", "HH Atacar · HL Bloquear · LH Fortalecer · LL Mantener", "333333")]
anchos_b = [0.95, 1.15, 1.2, 1.1, 1.05, 1.1, 0.8, 0.9, 0.85]
xb = K.MARGEN
for (tit, sub, cuerpo, col_), w_ in zip(bloques, anchos_b):
    K.caja(s, xb, y + 0.05, w_ - 0.06, 0.55, relleno=col_, redondeo=0.1)
    K.texto(s, xb + 0.06, y + 0.1, w_ - 0.18, 0.22, tit, tam=9, negrita=True, color=K.LIMA if col_ == K.NEGRO else K.BLANCO)
    K.texto(s, xb + 0.06, y + 0.34, w_ - 0.18, 0.2, sub, tam=6.5, color=K.GRIS_CLARO)
    K.caja(s, xb, y + 0.66, w_ - 0.06, 1.05, relleno=K.FONDO_CARD, redondeo=0.06)
    K.texto(s, xb + 0.07, y + 0.74, w_ - 0.2, 0.95, cuerpo, tam=7, color=K.NEGRO, interlineado=1.05)
    xb += w_
fila_ej = TABLA[TABLA[("Clasificación", "Letras (final)")].eq("HH") & TABLA[(CLU, "PDV con venta en su buffer (clúster de venta)")].ge(3)
                & TABLA[(CLU, "PDV del clúster NSE")].ge(2)].head(1)
if len(fila_ej):
    f_ = fila_ej.iloc[0]
    K.texto(s, K.MARGEN, y + 1.86, 9.1, 0.2, f"Ejemplo real · {f_[('Punto de venta (CP)', 'Nombre')][:40]} (pos_id {f_[('Punto de venta (CP)', 'pos_id')]})",
            tam=8, negrita=True)
    alt_v = f_[(ALT_BLOQUE, "Índice NSE AltScore del clúster (0-100)")]
    K.tabla(s, pd.DataFrame([{
        "pos_id": str(f_[("Punto de venta (CP)", "pos_id")]), "AltScore": "—" if pd.isna(alt_v) else f"{alt_v:.0f}",
        "NSE INEGI": f"{f_[(GOB, 'Nivel NSE INEGI del clúster (media, 1 = D/E … 6 = A/B)')]:.2f} · {f_[(GOB, 'NSE predominante del clúster')]}",
        "NSE final": f"{f_[('Letra 1', 'Nivel NSE final (INEGI + AltScore)')]:.2f}",
        "Venta media": f"{f_[(VEN, 'Venta media (cajas/mes)')]:.2f}", "CP": f"{f_[(VEN, 'CP · potencial en cajas enteras')]:.0f}",
        "Rappi": f"{f_[(VEN, 'Rappi · venta movida al PDV (cajas/mes)')]:.2f}",
        "Media de su buffer": f"{f_[(VEN, 'Media (venta media + CP + Rappi) de su clúster de venta')]:.2f} ({int(f_[(CLU, 'PDV con venta en su buffer (clúster de venta)')])} PDV)",
        "Clúster NSE": f"{int(f_[(CLU, 'PDV del clúster NSE')])} PDV", "L1 sin / con AltScore": f"{f_[('Letra 1', 'Letra 1 sin AltScore')]} / {f_[('Letra 1', 'Letra 1 con AltScore (final)')]}",
        "L2 sin / con Rappi": f"{f_[('Letra 2', 'Letra 2 sin Rappi')]} / {f_[('Letra 2', 'Letra 2 con Rappi (final)')]}",
        "Acción": f_[("Clasificación", "Acción Golden Stores")]}]), K.MARGEN, y + 2.1, 9.1, tam=7)
K.mensaje(s, "La 3.ª fila del Excel y la hoja Fuentes dicen de dónde sale cada columna; la hoja Fórmulas, cómo se calcula.")

K.notas(K.separador(prs, "Cómo se calcula", "Clústeres, Letra 1 y Letra 2"), "Primero los clústeres, luego la letra del NSE y la de ventas; cada una con su QA.")

# 3 · los dos clústeres: NSE (hexágono + 300 m) y de venta (buffer del PDV)
s, y = K.lamina(prs, "El NSE es del hexágono y la venta es del PDV: cada letra tiene su clúster", "Clústeres",
                notas=(f"Definición acordada: la ZM se divide en hexágonos H3 de res {RES_CL}; el centro de cada hexágono es el punto NSE y su buffer de "
                       f"{R300} m da los hogares; todos los PDV del hexágono comparten ese NSE, su primera letra (hexágonos en vez de centroides de AGEB: "
                       f"más simple en geografías complejas). La segunda letra es de cada PDV: su venta contra los PDV con venta de su propio buffer. "
                       f"Hay {len(clo):,} clústeres NSE con PDV objetivo (mediana {clo.n_objetivo.median():.0f} PDV) y ningún PDV queda a más de "
                       f"{ids.dist_centro_m.max():.0f} m del centro de su hexágono."))
K.tarjeta(s, K.MARGEN, y + 0.05, 3.9, 1.1, f"Clúster NSE = hexágono + {R300} m",
          f"Hexágono H3 res {RES_CL} (≈ 0.1 km²): su centro es el punto NSE y su buffer de {R300} m da los hogares. Sus PDV comparten la Letra 1.",
          oscura=True, compacta=True)
K.tarjeta(s, K.MARGEN, y + 1.25, 3.9, 0.95, "Letra 1 · del clúster",
          f"{len(clo):,} clústeres con PDV; mediana {clo.n_objetivo.median():.0f} PDV. Mismo NSE que el buffer de cada PDV (ρ = {rho_cb:.2f}), sin depender del punto.",
          compacta=True)
K.tarjeta(s, K.MARGEN, y + 2.3, 3.9, 0.95, "Letra 2 · del PDV",
          "Venta media + CP + Rappi contra la media de los PDV con venta de su buffer de 300 m. Si es el único con venta, queda L.", compacta=True)
ej_k = cl[(cl.n_objetivo.between(3, 6)) & cl.N.notna()]
if len(ej_k):
    c_ej = (ej_k.N - ej_k.N.quantile(0.75)).abs().idxmin()
    fig, ax_ = plt.subplots(figsize=(5.4, 5.0))
    panel_cluster(ax_, c_ej, "Clúster NSE de ejemplo")
    i_m = ids.index[ids.cluster_nse.eq(c_ej) & ids.objetivo][0]
    gpd.GeoSeries([pts.geometry.iloc[i_m].buffer(R300)], crs=CRS).boundary.plot(ax=ax_, color=eda.TINTA, lw=1.1, ls=":")
    rr = ids.iloc[i_m]
    ax_.set_title(f"Clúster NSE de ejemplo · {int(cl.loc[c_ej, 'n_pdv'])} PDV (estrellas)\nhexágono (azul), su buffer (guiones) y el buffer de un PDV (puntos)",
                  fontsize=9.5)
    ax_.text(0.02, 0.02, f"Letra 1 del clúster: {cl.loc[c_ej, 'hog']:,.0f} hogares, NSE INEGI {cl.loc[c_ej, 'N']:.2f} → final {cl.loc[c_ej, 'N_star']:.2f} "
                         f"(predominante: {cl.loc[c_ej, 'clase']}) → {rr.L1}\n"
                         f"Letra 2 de {str(rr.Nombre)[:24]}: {rr.WR:.2f} vs media {rr.WR_media_cluster:.2f} de su buffer → {rr.L2}",
             transform=ax_.transAxes, fontsize=8, bbox=dict(facecolor="white", alpha=0.9, lw=0))
    imagen(s, fig, 4.55, y - 0.05, 4.95, K.ALTO - y - 0.5)

# 4 · Letra 1
s, y = K.lamina(prs, f"La Letra 1 es el NSE de su clúster y el Censo por manzana la confirma en {confirmado:.0%} de las tiendas", "Letra 1 · NSE",
                notas=(f"El NSE sale de INEGI: la regla AMAI aplicada a los hogares del Censo por microsimulación y repartida por área de manzana en "
                       f"hexágonos. Cada clúster toma el de los hogares a {R300} m de su centro y AltScore lo mueve con peso {LAM:g}. Para asegurarlo lo "
                       f"comparamos con un índice directo del Censo por manzana (autos, computadora, internet y escolaridad): ρ = {rho_c:+.2f}. El nivel NSE "
                       f"es una media y por eso casi siempre sale entre 2.5 y 4.5; en absoluto, {PREDOMINANTE}"))
K.tarjeta(s, K.MARGEN, y + 0.05, 3.9, 1.7, "Fórmula",
          f"N = Σ k · p_k (1 = D/E … 6 = A/B) con los hogares 2025 del buffer de {R300} m de su clúster.\nNSE final = {1 - LAM:g} · INEGI + {LAM:g} · AltScore.\n"
          "Índice NSE = 100 · NSE final / media de su subcanal.\nLetra 1 = H si el índice ≥ 100; si no, L.", oscura=True)
cv_ = conc.set_index("variante")
K.tarjeta(s, K.MARGEN, y + 1.85, 3.9, 1.3, "Cómo nos aseguramos",
          f"• Censo por manzana vs NSE AMAI: ρ = {rho_c:+.2f} (IC {lo_c:+.2f} a {hi_c:+.2f}).\n• % ABC+ da la misma letra en "
          f"{cv_.loc['% ABC+ del clúster (INEGI)', '% misma letra (INEGI)']:.0f}% de las tiendas.\n• Buffer de 200 o 400 m: "
          f"{cv_.loc[f'Buffer de 200 m desde el centro (en vez de {R300})', '% misma letra (INEGI)']:.0f}% y "
          f"{cv_.loc[f'Buffer de 400 m desde el centro (en vez de {R300})', '% misma letra (INEGI)']:.0f}% igual.\n• El buffer del propio PDV: "
          f"{cv_.loc[f'Buffer de {R300} m del propio PDV (sin clúster)', '% misma letra (INEGI)']:.0f}% igual.", compacta=True)
imagen(s, fig_mapa("L1", MP.COLOR_L1, {"H": "L1 = H (NSE alto)", "L": "L1 = L"}), 4.55, y - 0.05, 4.95, K.ALTO - y - 0.5)

# 5 · AltScore mueve el NSE
s, y = K.lamina(prs, f"AltScore mueve el NSE de {cl.alt_ok[cl.n_objetivo > 0].mean():.0%} de los clústeres y cambia {n_alt} Letras 1",
                "AltScore mueve el NSE",
                notas=(f"AltScore entra como una variable socioeconómica más: su índice NSE digital (PC1 de {', '.join(PROX_ALT)}) en el buffer de cada "
                       f"clúster se pasa a la escala de INEGI por cuantiles y se combina con peso {LAM:g}. {ALT_NSE}"))
for i_, (v_, e_, d_) in enumerate([(f"{cl.alt_ok[cl.n_objetivo > 0].mean():.0%}", "clústeres con AltScore", f"≥ {MIN_ALT} puntos con índice en su buffer"),
                                   (f"{rho_a:+.2f}", "ρ AltScore vs INEGI", f"por clúster (IC {lo_a:+.2f} a {hi_a:+.2f})"),
                                   (f"{n_alt}", "Letras 1 que cambia", f"{int(ob.sube_por_alt.sum())} suben · {int(ob.baja_por_alt.sum())} bajan (λ = {LAM:g})")]):
    K.cifra(s, K.MARGEN + i_ * 3.07, y + 0.05, 2.95, v_, e_, d_, h=1.05, oscura=(i_ == 0))
sa_t = sens_alt.assign(**{"Peso de AltScore (λ)": lambda t: t["peso de AltScore (λ)"].map(lambda w_: f"{w_:g}" + (" (base)" if w_ == LAM else "")),
                          "% L1 = H": lambda t: t["% L1 = H"].map("{:.0f}%".format),
                          "Suben ↑ · bajan ↓": lambda t: t["PDV que suben a H"].astype(str) + " ↑ · " + t["PDV que bajan a L"].astype(str) + " ↓",
                          "% que cambian": lambda t: t["% que cambian"].map("{:.1f}%".format),
                          "κ con el Censo": lambda t: t["κ con la letra del Censo"].map("{:.2f}".format)})
K.tabla(s, sa_t[["Peso de AltScore (λ)", "% L1 = H", "Suben ↑ · bajan ↓", "% que cambian", "κ con el Censo"]], K.MARGEN, y + 1.3, 9.1, tam=7.5)
K.mensaje(s, f"INEGI pesa {1 - LAM:g} y AltScore {LAM:g}: el Censo confirma a INEGI y AltScore agrega la lectura digital actual (peso a validar).")

# 6 · Letra 2
s, y = K.lamina(prs, "La Letra 2 es su venta: venta media + CP + Rappi contra los PDV con venta de su buffer", "Letra 2 · Ventas",
                notas=(f"Regla definida con el cliente: se suma la venta media del PDV y su potencial, los dos del CP (el potencial en cajas enteras); se "
                       f"compara con la media de los PDV con venta de su buffer de {R300} m. Si supera la media es H. Si es la única con venta en su buffer "
                       f"queda L ({solo_tr:.0%} de las tiendas). Rappi premia a la locación moviendo su venta: la venta de sueros e hidratación de cada "
                       f"tienda Rappi activa, en cajas, se reparte entre los PDV de su buffer y se suma a su venta y a la media de su clúster de venta: "
                       f"cada PDV se compara con sus vecinos con la misma vara."))
K.tarjeta(s, K.MARGEN, y + 0.05, 3.9, 1.95, "Fórmula",
          "W = venta media + potencial, los dos del CP (cajas/mes;\nel potencial en cajas enteras: hacia abajo si el decimal < 0.6).\nRappi = su venta en cajas repartida entre los PDV del buffer.\n"
          "Media del buffer = media de W + Rappi de los PDV con venta.\nÍndice = 100 · (W + Rappi) / media del buffer.\nLetra 2 = H si hay ≥ 2 con venta e índice > 100.",
          oscura=True)
q_ = qa_l2.set_index("comparación")["% misma Letra 2"]
K.tarjeta(s, K.MARGEN, y + 2.1, 3.9, 1.3, "Qué cambia la regla",
          f"• Sin el CP cambiaría {100 - q_['sin el CP (solo venta media)']:.0f}% de las letras; sin redondearlo, {100 - q_['con el CP sin redondear']:.0f}%.\n"
          f"• Sin Rappi: {q_['sin la venta Rappi movida']:.0f}% igual.\n"
          f"• Con la media sin Rappi (Rappi solo premia): {q_['con la media del clúster de venta sin Rappi (Rappi solo premia)']:.0f}% igual.\n"
          f"• {solo_tr:.0%} son las únicas con venta en su buffer (L).", compacta=True)
ej_c = ob[ob.n_cluster.between(6, 12)]
if len(ej_c):
    i_ = (ej_c.I_V - 150).abs().idxmin()
    fig, ax_, rr = fig_venta(i_, "Clúster de venta de ejemplo")
    ax_.set_title(f"Clúster de venta de {str(rr.Nombre)[:28]} · {rr.n_cluster} PDV con venta\n(verde = sobre la media de su buffer)", fontsize=10)
    ax_.text(0.02, 0.02, f"W = {rr.V:.2f} + {rr.CP:.0f} = {rr.W:.2f} · Rappi +{rr.R_mov:.2f} · media {rr.WR_media_cluster:.2f} ({rr.n_cluster} PDV)\n"
                         f"índice {rr.I_V_star:.0f} → Letra 2 = {rr.L2}", transform=ax_.transAxes, fontsize=8.5,
             bbox=dict(facecolor="white", alpha=0.9, lw=0))
    imagen(s, fig, 4.55, y - 0.05, 4.95, K.ALTO - y - 0.5)

# 7 · Rappi
s, y = K.lamina(prs, f"Rappi mueve {movida:.0f} cajas/mes de sueros e hidratación a {int(ob.P.sum())} tiendas y decide la letra de {n_rap}",
                "Rappi mueve la venta",
                notas=(f"Usamos solo sueros y derivados de Rappi en la ZM (ene-2025 a ago-2026). {len(act)} tiendas físicas son activas (≥ {THETA} pedidos). "
                       f"Rappi premia a la locación moviendo su venta: la pasamos a cajas con {BOT} botellas por caja (dato a confirmar con Bepensa) y la "
                       f"repartimos en partes iguales entre las tiendas con venta de su buffer de {R300} m. Es {movida / ids.W.sum():.1%} de la venta + CP de "
                       f"Bepensa, por eso decide pocas letras: {int(ob.sube_por_rappi.sum())} suben y {int(ob.baja_por_rappi.sum())} bajan, porque la media del "
                       f"buffer también se mueve con Rappi. {RESPALDO}"))
for i_, (v_, e_, d_) in enumerate([(f"{len(act)}", "tiendas Rappi activas", f"≥ {THETA} pedidos de sueros o derivados"),
                                   (f"{movida:.0f}", "cajas/mes movidas", f"a {int(ob.P.sum()):,} PDV ({ob.P.mean():.1%} del total)"),
                                   (f"{n_rap}", "PDV cambian de letra", f"{int(ob.sube_por_rappi.sum())} suben · {int(ob.baja_por_rappi.sum())} bajan ({BOT} botellas/caja)")]):
    K.cifra(s, K.MARGEN + i_ * 3.07, y + 0.05, 2.95, v_, e_, d_, h=1.05, oscura=(i_ == 0))
sens_t = sens[es_base].assign(v=lambda t: t["PDV que pasan a H por Rappi"].astype(str) + " ↑ · " + t["PDV que pasan a L por Rappi"].astype(str) + " ↓") \
    .pivot(index="tiendas Rappi que mueven su venta", columns="botellas por caja", values="v")
sens_t.columns = [f"{c:g} botellas por caja" + (" (base)" if c == BOT else "") for c in sens_t.columns]
K.tabla(s, sens_t.reset_index().rename(columns={"tiendas Rappi que mueven su venta": "Tiendas Rappi que mueven su venta"}), K.MARGEN, y + 1.3, 9.1, tam=7.5)
K.mensaje(s, f"Rappi es {movida / ids.W.sum():.1%} de la venta + CP de Bepensa: premia a pocas tiendas, con venta observada de la categoría que Bepensa no ve.")

# 8 · resultado por letras
s, y = K.lamina(prs, f"Las HH son {panorama.loc['HH', '% tiendas']:.0f}% de las tiendas y {hh_mix:.0f}% de la venta; las LH suman otro {lh_mix:.0f}%",
                "Resultado",
                notas=("Letra 1 + Letra 2 con las acciones fijas de Golden Stores, en el canal Tradicional. La venta se concentra en las dos letras H de "
                       f"venta (HH y LH). Frente a las letras base (solo INEGI + CP), {igual:.0%} de los PDV conserva sus letras: AltScore cambia {n_alt} "
                       f"Letras 1 y Rappi {n_rap} Letras 2."))
p_ = panorama.reset_index()
tb = pd.DataFrame({"Letras": p_.letras, "Acción": p_["acción"], "Tiendas": p_.tiendas.fillna(0).astype(int).map("{:,}".format),
                   "% tiendas": p_["% tiendas"].map("{:.0f}%".format), "% venta": p_["% mix ventas"].map("{:.0f}%".format),
                   "Index ventas": p_["Index ventas"].map("{:.0f}".format), "NSE medio": p_.N_medio.map("{:.2f}".format),
                   "% con Rappi": p_["% con Rappi"].map("{:.0f}%".format)})
K.texto(s, K.MARGEN, y + 0.02, 5.4, 0.2, f"Canal Tradicional · {int(p_.tiendas.sum()):,} PDV · letras finales", tam=9, negrita=True)
K.tabla(s, tb, K.MARGEN, y + 0.28, 5.5, tam=7.5, resaltar=[0])
K.texto(s, K.MARGEN + 5.8, y + 0.02, 3.3, 0.2, "Letras base (filas) → finales (columnas)", tam=9, negrita=True)
K.tabla(s, cruce.reset_index().rename(columns={"letras base (INEGI + CP)": "Base"}).astype(str), K.MARGEN + 5.8, y + 0.28, 3.3, tam=7.5, resaltar=[0])
K.texto(s, K.MARGEN, y + 1.8, 9.1, 0.4, "Letra 1 = NSE de su clúster (H alto · L bajo) · Letra 2 = su venta frente a los PDV con venta de su buffer "
                                         "(H sobre la media · L debajo).", tam=8.5, color=K.GRIS)
K.mensaje(s, "HH = Atacar · HL = Bloquear · LH = Fortalecer · LL = Mantener (acciones fijas de Golden Stores).")

# 9 · ejemplos con tiendas reales (formato del entregable)
s, y = K.lamina(prs, "Así se ve cada tienda en el entregable: sus datos, sus clústeres y sus dos letras", "Ejemplos reales",
                notas=("Una tienda por combinación de letras, más una que queda L por ser la única con venta en su buffer, una a la que AltScore le "
                       "cambia la Letra 1 y una a la que Rappi le cambia la Letra 2. Los valores salen del Excel."))
ejemplos = []
for c_ in CL:
    m_ = tr[tr.letras.eq(c_) & ~tr.solo_en_cluster & ~tr.cambia_por_alt & ~tr.cambia_por_rappi]
    if len(m_):
        ejemplos.append(m_.loc[(m_.W - m_.W.median()).abs().idxmin()])
for cond in (tr.solo_en_cluster, tr.cambia_por_alt, tr.cambia_por_rappi):
    if cond.any():
        ejemplos.append(tr[cond].iloc[0])
tb = pd.DataFrame([{"pos_id": str(int(r.pos_id_cp)), "Nombre": str(r.Nombre)[:20], "Clúster NSE": f"{int(r.n_cluster_nse)} PDV",
                    "NSE INEGI → final": f"{r.N_inegi:.2f} → {r.N:.2f}", "L1 sin → con AltScore": f"{r.L1_sin_alt} → {r.L1}",
                    "Venta media": f"{r.V:.2f}", "CP": f"{r.CP:.0f}", "Rappi": f"{r.R_mov:.2f}",
                    "Media de su buffer": f"{r.WR_media_cluster:.2f} ({int(r.n_cluster)})", "L2 sin → con Rappi": f"{r.L2_sin_rappi} → {r.L2}",
                    "Acción": r.accion} for r in ejemplos])
K.tabla(s, tb, K.MARGEN, y + 0.05, 9.1, tam=7, anchos=[0.6, 1.45, 0.75, 1.0, 0.95, 0.65, 0.4, 0.5, 0.95, 0.95, 0.9])
K.mensaje(s, "NSE = media del buffer de su clúster (1 D/E … 6 A/B), movida por AltScore · Media de su buffer = venta media + CP + Rappi de los PDV con venta.")

# 10 · QA
s, y = K.lamina(prs, "Cada dato se verificó antes de entrar a una letra", "Control de calidad",
                notas="Resumen del QA de los notebooks 00b (AltScore), 00c (Rappi) y 06 (letras). Cada paso tiene su mapa en el notebook y en el mapa HTML interactivo.")
qa_items = [("Solo canal Tradicional y solo el CP", f"Se quitan {int((~TRAD).sum())} PDV Moderno; del PDV solo entran el id, el nombre, el subcanal, las "
                                                    "coordenadas, la venta media y el potencial del CP."),
            ("NSE asegurado", f"Censo por manzana ρ = {rho_c:+.2f}; % ABC+ y buffers de 200/400 m dan la misma letra INEGI en "
                              f"{cv_.loc['% ABC+ del clúster (INEGI)', '% misma letra (INEGI)']:.0f}-{cv_.loc[f'Buffer de 200 m desde el centro (en vez de {R300})', '% misma letra (INEGI)']:.0f}%."),
            (f"Clúster NSE = hexágono + {R300} m", f"Ningún PDV a más de {ids.dist_centro_m.max():.0f} m del centro; mismo NSE que el buffer de cada PDV "
                                                  f"(ρ = {rho_cb:.2f}); mediana de {clo.n_objetivo.median():.0f} PDV por clúster."),
            ("AltScore y Rappi mueven, no deciden solos", f"AltScore (ρ = {rho_a:+.2f} con INEGI) cambia {n_alt} Letras 1 con peso {LAM:g}; Rappi, "
                                                          f"{movida:.0f} cajas/mes repartidas sin contar dos veces, cambia {n_rap} Letras 2.")]
for k_, (t_, c_) in enumerate(qa_items):
    K.tarjeta(s, K.MARGEN + (k_ % 2) * 4.6, y + 0.05 + (k_ // 2) * 1.25, 4.5, 1.15, t_, c_, numero=k_ + 1, compacta=True)
K.mensaje(s, "Mapa de QA interactivo: cada paso explica qué se hace y por qué; clic en un hexágono o en una tienda muestra sus clústeres.", y=y + 2.6)

# 11 · pendientes
s, y = K.lamina(prs, "Tres respuestas dejan las dos letras listas para el entregable", "Siguientes pasos",
                notas="Lo que falta para usar estas letras como definitivas.")
for k_, (t_, c_) in enumerate([("Validar los clústeres y la Letra 2", f"Letra 1 del hexágono res {RES_CL} + {R300} m; Letra 2: venta media + potencial del CP "
                                                                     "(cajas enteras, umbral 0.6) + Rappi contra la media de su buffer; el único con venta queda L."),
                               ("Peso de AltScore (λ)", f"Con {LAM:g} AltScore cambia {n_alt} Letras 1; con 0.5, {alt_05}. Para predecir el Censo por manzana "
                                                        f"AltScore pesa β = {b_alt:+.2f}: un peso alto aleja la letra de la medición directa."),
                               ("Botellas por caja (Rappi → cajas)", f"Con {BOT} botellas por caja Rappi decide {n_rap} letras; con 6, "
                                                                     f"{int(sens_base.get(6, 0))}; con 24, {int(sens_base.get(24, 0))}. Confirmar el tamaño de la caja de sueros.")]):
    K.tarjeta(s, K.MARGEN + k_ * 3.07, y + 0.1, 2.95, 1.9, t_, c_, numero=k_ + 1)
K.mensaje(s, "Con esas tres respuestas, las dos letras quedan definitivas.", invertido=True)
K.cierre(prs)
DECK = C.OUT_CLIENTE / f"06_letras_nse_ventas_{C.CLIENTE}_{C.SLUG}.pptx"
prs.save(DECK)
print(f"Presentación: {DECK.name} ({len(prs.slides)} láminas)")

cols_guardar = ["pos_id_cp", "segmento", "objetivo", "cluster_nse", "n_cluster_nse", "dist_centro_m", "HH_cluster", "N_punto", "N_ageb", "N_pdv", "N_inegi",
                "alt_cluster", "alt_puntos", "N_alt", "N", "nse_clase", "nse_clase_pct", "nse_bajo", "nse_medio", "nse_alto", "abc", "censo_punto", "censo_area",
                "nse_confirmado", "I_N", "I_N_inegi", "L1", "L1_sin_alt", "frontera_L1", "cambia_por_alt", "sube_por_alt", "baja_por_alt", "variantes_iguales",
                "V", "CP_original", "CP", "W", "n_cluster", "W_media_cluster", "WR_media_cluster", "I_V", "solo_en_cluster", "rappi_n", "rappi_venta",
                "rappi_sueros", "rappi_turbo", "P", "R_mov", "WR", "I_V_star", "L2", "L2_sin_rappi", "L2_solo_premia", "L2_sin_cp", "L2_cp_original",
                "frontera_L2", "cambia_por_rappi", "sube_por_rappi", "baja_por_rappi", "letras", "letras_sin_rappi", "letras_base", "accion", "accion_base"]
ids[cols_guardar].assign(nse_confirmado=lambda t: t.nse_confirmado.astype(object)).to_parquet(C.PROC / f"letras_pdv_{C.CLIENTE}_{C.SLUG}.parquet", index=False)
print("Guardado:", f"letras_pdv_{C.CLIENTE}_{C.SLUG}.parquet |", MAPA_QA.name, "|", XLSX.name, "|", DECK.name)
