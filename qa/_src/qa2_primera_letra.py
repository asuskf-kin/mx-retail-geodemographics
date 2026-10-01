# %% [markdown]
# # QA 2 · La primera letra paso a paso contra Nielsen — Bepensa · ZM Mérida · sueros
#
# **Pregunta:** si aplicamos **todo nuestro proceso de la Letra 1** (INEGI, NSE AMAI, Censo por manzana, clúster hexagonal y
# AltScore) en la coordenada de cada autoservicio de la línea base de Nielsen (`qa/Golden Stores Sueros R.Sur - KO FY'23.xlsx`),
# ¿cuánto le atinamos a **su primera letra**? Y ¿qué paso del proceso nos acerca o nos aleja?
#
# **Alcance:** los 65 autoservicios de la línea base que caen en la **ZM Mérida**, que es donde tenemos todos los insumos (hogares por
# hexágono, NSE AMAI por AGEB, Censo por manzana y AltScore). Solo la **primera letra** (NSE): la segunda (venta) está en el QA 1.
#
# **Cómo se lee:** la sección 1 arma, para cada tienda, cada insumo del proceso; la 2 mide cada paso contra Nielsen (AUC: ¿ordena
# igual?; exactitud y κ: ¿da la misma letra?) con cuatro cortes; la 3 prueba el peso de AltScore y el radio; la 4 da la exactitud
# del proceso tal como lo usa hoy el 06 y la del mejor proceso; la 5 escribe el **Excel ejecutivo** con QA 1 + QA 2.
#
# **Reproducir:** `uv run python src/py2nb.py qa/_src/qa2_primera_letra.py qa/qa2_primera_letra.ipynb` y correr el notebook (antes
# el pipeline 00 → 06 y `qa/qa_linea_base_nielsen.ipynb`, de donde salen los resultados del QA 1).

# %%
import os
import sys
import hashlib
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import numpy as np
import pandas as pd
import geopandas as gpd
import h3
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.metrics import roc_auc_score
from shapely.geometry import Point
from IPython.display import display

import config as C
import altscore as A
import eda
import letras as LT
import rappi as R
from descargas import descargar_fuente, extraer

eda.estilo()
pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.3f}".format)
QA, OUT = BASE / "qa", BASE / "qa" / "salidas"
OUT.mkdir(exist_ok=True)
F_NIELSEN = QA / "Golden Stores Sueros R.Sur - KO FY'23.xlsx"
F_LETRAS = C.PROC / f"letras_pdv_{C.CLIENTE}_{C.SLUG}.parquet"
F_HEX = C.PROC / f"hexagonos_h3r{C.H3_RES}_{C.CLIENTE}_{C.SLUG}.gpkg"
F_AGEB = C.PROC / f"ageb_{C.SLUG}.gpkg"
F_MZ = C.PROC / f"manzanas_{C.SLUG}.gpkg"
F_ALT = C.PROC / f"altscore_{C.CLIENTE}_{C.SLUG}.parquet"
for f_ in [F_NIELSEN, F_LETRAS, F_HEX, F_AGEB, F_MZ, F_ALT]:
    assert f_.exists(), f"Falta {f_.relative_to(BASE)}: correr el pipeline 00 → 06"
R300, RES_CL, LAM, MIN_ALT = C.RADIO_PDV_M, C.NSE_CLUSTER_RES, C.ALTSCORE_PESO_NSE, C.ALTSCORE_MIN_PUNTOS
NSE = ["A/B", "C+", "C", "C-", "D+", "D/E"]
K_NSE = pd.Series({"A/B": 6, "C+": 5, "C": 4, "C-": 3, "D+": 2, "D/E": 1})
RNG = np.random.default_rng(eda.SEMILLA)


def boot(fn, *arrs, B=2000):
    """IC95 por bootstrap de tiendas (semilla fija)."""
    n, vals = len(arrs[0]), []
    for _ in range(B):
        i = RNG.integers(0, n, n)
        try:
            vals.append(fn(*[np.asarray(a)[i] for a in arrs]))
        except ValueError:
            continue
    return np.nanpercentile(vals, [2.5, 97.5])


def lectura_k(k):
    return str(pd.cut([k], [-1, 0.2, 0.4, 0.6, 0.8, 1.01], labels=["pobre", "regular", "moderado", "bueno", "casi perfecto"])[0])


def medir(paso, variable, corte, ref, x, umbral):
    """Una fila: exactitud y κ (con IC95) de la letra H si x ≥ umbral (umbral escalar o serie por tienda) contra Nielsen."""
    ok = pd.notna(x)
    r_, x_ = np.asarray(ref)[ok], np.asarray(x, float)[ok]
    u_ = np.asarray(umbral, float)[ok] if np.ndim(umbral) else umbral
    p_ = np.where(x_ >= u_, "H", "L")
    acc = (r_ == p_).mean()
    k = eda.kappa_cohen(pd.Series(r_), pd.Series(p_))
    lo_k, hi_k = boot(lambda a, b: eda.kappa_cohen(pd.Series(a), pd.Series(b)), r_, p_)
    lo_a, hi_a = boot(lambda a, b: (a == b).mean(), r_, p_)
    return {"paso": paso, "variable": variable, "corte": corte, "n": int(ok.sum()), "exactitud": acc, "IC95 exactitud": f"[{lo_a:.2f}, {hi_a:.2f}]",
            "κ de Cohen": k, "IC95 κ": f"[{lo_k:.2f}, {hi_k:.2f}]", "lectura κ": lectura_k(k), "% H nuestro": (p_ == "H").mean() * 100,
            "% H Nielsen": (r_ == "H").mean() * 100}


print(f"{C.ZM_NOMBRE} · radio {R300} m · clúster NSE H3 res {RES_CL} · AltScore λ = {LAM:g} (≥ {MIN_ALT} puntos)")

# %% [markdown]
# ## 0. La línea base y su regla de la primera letra
#
# **Qué se hace:** se leen los 65 autoservicios de la ZM Mérida con su clúster y su perfil NSE (los % de A/B … D/E del área que
# reporta Nielsen). De ahí se calcula su nivel NSE N = Σ k·p_k (1 = D/E … 6 = A/B) y se despeja la referencia fija de su índice
# (ref = % / índice × 100). Es el **techo**: con su propio perfil y su referencia, ¿cuánto se reproducen sus letras?
#
# **Por qué:** si la regla de Nielsen es "NSE del área contra una referencia regional", nuestro mejor resultado posible es
# reproducir su perfil NSE y usar un corte equivalente; lo que falte de ahí es error de insumos (sección 2) o de corte.

# %%
raw = pd.read_excel(F_NIELSEN, sheet_name=0, header=None)
h1, h2 = raw.iloc[7].ffill(), raw.iloc[8]
cols = [f"{' '.join(str(a).split())}|{b}" if pd.notna(a) and b in ("HHs", "%", "Indice") else str(b).strip() for a, b in zip(h1, h2)]
nie = raw.iloc[9:].copy()
nie.columns = cols
nie = nie[nie["Nielsen ID"].notna()].reset_index(drop=True)
for c in NSE:
    for s_ in ("%", "Indice"):
        nie[f"{c}|{s_}"] = pd.to_numeric(nie[f"{c}|{s_}"], errors="coerce")
pn_all = nie[[f"{c}|%" for c in NSE]].set_axis(NSE, axis=1)
REF_N = (pn_all / nie[[f"{c}|Indice" for c in NSE]].set_axis(NSE, axis=1) * 100).median()
REF_N = REF_N / REF_N.sum()
N_REF = float((REF_N * K_NSE).sum())
zm = nie[nie["Zonas Metropolitanas"].eq("MERIDA")].reset_index(drop=True)
zm["lat"], zm["lon"] = zm.Latitud.astype(float), zm.Longitud.astype(float)
zm["cluster_n"] = zm["Cluster"].astype(str).str.strip()
zm["L1n"] = zm.cluster_n.str[0]
zm["cadena"] = zm["Cadena de Autoservicios"].astype(str).str.strip()
pz = zm[[f"{c}|%" for c in NSE]].set_axis(NSE, axis=1)
zm["N_nielsen"] = (pz * K_NSE).sum(axis=1) / pz.sum(axis=1)
techo = medir("0 · Techo", "N de Nielsen (su propio perfil)", f"su referencia regional (N ≥ {N_REF:.2f})", zm.L1n, zm.N_nielsen, N_REF)
print(f"{len(zm)} autoservicios en la ZM · Nielsen H {(zm.L1n == 'H').mean():.0%} · referencia regional de su índice: "
      + ", ".join(f"{c} {v * 100:.1f}%" for c, v in REF_N.items()) + f" (N = {N_REF:.2f})")
print(f"Techo: con su propio perfil y su referencia, sus letras se reproducen en {techo['exactitud']:.0%} (κ {techo['κ de Cohen']:.2f}).")
display(zm.groupby("cadena").agg(tiendas=("L1n", "size"), **{"% H Nielsen": ("L1n", lambda s: (s == "H").mean() * 100)}).round(0))

# %% [markdown]
# ## 1. Nuestro proceso en la coordenada de cada autoservicio
#
# **Qué se hace:** para cada tienda se calcula cada insumo del proceso, en el orden en que la Letra 1 los usa:
#
# | Paso | Insumo | De dónde sale |
# |---|---|---|
# | 1 | NSE del **punto** (hexágono H3 res 10 de la tienda) | hogares AMAI por hexágono del 04 |
# | 2 | NSE de su **AGEB** | microsimulación AMAI del 01 |
# | 3 | **Índice del Censo** por manzana (auto, computadora, internet, escolaridad) en 300 m del centro del clúster | Censo 2020, manzanas del 01 |
# | 4 | **Clúster NSE**: hexágono H3 res 9 + buffer de 300 m desde su centro (N INEGI) — la Letra 1 del 06 sin AltScore | 04 + regla del 06 |
# | 5 | **AltScore** del clúster (índice NSE digital 0-100, puntos a ≤ 300 m del centro) | 00b |
# | 6 | Clúster **con AltScore**: N* = (1 − λ)·N + λ·Ñ (λ = 0.25) — la Letra 1 final del 06 | 06 |
# | 7 | **% ABC+** del clúster (A/B + C+) y buffer de la **propia tienda** (sin clúster) | 04 |
#
# **Por qué:** así se ve en qué paso se gana o se pierde exactitud, no solo el resultado final.

# %%
hexg = gpd.read_file(F_HEX).set_index("hex")
hx = hexg[[f"HHs_{c}" for c in NSE]].set_axis(NSE, axis=1)
ageb = gpd.read_file(F_AGEB)
mzg = gpd.read_file(F_MZ)
let = pd.read_parquet(F_LETRAS)
ob = let[let.objetivo]

# paso 1 · punto (hexágono res 10)
zm["hex10"] = [h3.latlng_to_cell(a, b, C.H3_RES) for a, b in zip(zm.lat, zm.lon)]
zm["N_punto"] = LT.nivel_medio(hx.reindex(zm.hex10).reset_index(drop=True)).to_numpy()
# paso 2 · AGEB
pts = gpd.GeoDataFrame(zm[["Nielsen ID"]], geometry=gpd.points_from_xy(zm.lon, zm.lat), crs=4326).to_crs(ageb.crs)
j_ = gpd.sjoin(pts, ageb[["CVEGEO", *[f"HHs_{c}" for c in NSE], "geometry"]], how="left", predicate="within")
j_ = j_[~j_.index.duplicated()]
zm["AGEB"] = j_.CVEGEO.reindex(zm.index).to_numpy()
zm["N_ageb"] = LT.nivel_medio(j_[[f"HHs_{c}" for c in NSE]].set_axis(NSE, axis=1).reindex(zm.index)).to_numpy()
# paso 4 · clúster NSE (hexágono res 9 + 300 m desde su centro)
zm["cl"] = [h3.latlng_to_cell(a, b, RES_CL) for a, b in zip(zm.lat, zm.lon)]
cla, clo = LT.centros(zm.cl)
hh_cl = LT.suma_area(hx, LT.hexagonos_en_radio(cla, clo, R300, C.H3_RES)).set_axis(NSE, axis=1)
zm["N_cluster"] = LT.nivel_medio(hh_cl).to_numpy()
zm["abc_cluster"] = ((hh_cl["A/B"] + hh_cl["C+"]) / hh_cl.sum(axis=1).replace(0, np.nan) * 100).to_numpy()
zm["hog_cluster"] = hh_cl.sum(axis=1).to_numpy()
# paso 7b · buffer de la propia tienda (sin clúster)
hh_pr = LT.suma_area(hx, LT.hexagonos_en_radio(zm.lat, zm.lon, R300, C.H3_RES)).set_axis(NSE, axis=1)
zm["N_buffer_tienda"] = LT.nivel_medio(hh_pr).to_numpy()

# paso 3 · índice del Censo por manzana (mismo método que el 06: rangos normalizados → PC1 → percentil 0-100)
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
v = cz[COLS_CENSO[5:]].apply(pd.to_numeric, errors="coerce")
viv = v.VIVPARH_CV.where(v.VIVPARH_CV > 0)
IND = pd.DataFrame({"auto": v.VPH_AUTOM / viv * 100, "pc": v.VPH_PC / viv * 100, "internet": v.VPH_INTER / viv * 100, "escolaridad": v.GRAPROES})
IND.iloc[:, :3] = IND.iloc[:, :3].clip(upper=100)
Zm = np.column_stack([A.rango_normal(IND[c]) for c in IND])
comp = ~np.isnan(Zm).any(axis=1)
_, vec_ = np.linalg.eigh(np.corrcoef(Zm[comp], rowvar=False))
w_ = vec_[:, -1] * np.sign(vec_[:, -1].sum())
cz["indice_censo"] = np.nan
cz.loc[comp, "indice_censo"] = stats.rankdata((Zm @ w_)[comp]) / comp.sum() * 100
mzc = mzg[["CVEGEO", "hog", "geometry"]].merge(cz[["CVEGEO", "indice_censo"]], on="CVEGEO", how="left")
mzc["area"] = mzc.area
centros = gpd.GeoSeries(gpd.points_from_xy(clo, cla), crs=4326).to_crs(mzc.crs)
indc = []
for g_ in centros.buffer(R300):
    sub = mzc[mzc.intersects(g_)]
    w = sub.hog * sub.intersection(g_).area / sub.area
    ok = sub.indice_censo.notna() & (w > 0)
    indc.append(float((sub.indice_censo[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else np.nan)
zm["censo_cluster"] = indc

# pasos 5 y 6 · AltScore (misma escala que el 06: cuantiles de los clústeres con PDV objetivo)
alt = pd.read_parquet(F_ALT)
loc = A.ubicacion(alt)
alt = alt.dropna(subset=[loc["lat"], loc["lon"]]).reset_index(drop=True)
va = alt.indice_nse_altscore.to_numpy(float)
cer = R.en_radio(cla, clo, alt[loc["lat"]].to_numpy(float), alt[loc["lon"]].to_numpy(float), R300)
zm["alt_cluster"] = [np.nanmean(va[i]) if len(i) and np.isfinite(va[i]).any() else np.nan for i in cer]
zm["alt_puntos"] = [int(np.isfinite(va[i]).sum()) for i in cer]
base_cl = ob.drop_duplicates("cluster_nse")
zm["N_alt"] = LT.a_escala(zm.alt_cluster.where(zm.alt_puntos >= MIN_ALT), base_cl.N_inegi, x_base=base_cl.alt_cluster).to_numpy()


def n_star(lam):
    return LT.mover_nse(zm.N_cluster, zm.N_alt, lam).to_numpy()


zm["N_cluster_alt"] = n_star(LAM)
insumos = zm[["Nielsen ID", "Store Name", "cadena", "Municipio", "cluster_n", "L1n", "N_nielsen", "N_punto", "N_ageb", "censo_cluster",
              "N_cluster", "alt_cluster", "alt_puntos", "N_alt", "N_cluster_alt", "abc_cluster", "N_buffer_tienda", "hog_cluster"]]
display(insumos.head(10).round(2))
corr_ = insumos[["N_nielsen", "N_punto", "N_ageb", "censo_cluster", "N_cluster", "alt_cluster", "N_cluster_alt", "abc_cluster", "N_buffer_tienda"]].corr("spearman")
display(corr_.round(2))

# %% [markdown]
# ## 2. Cada paso contra la primera letra de Nielsen
#
# **Qué se hace:** para cada insumo: (a) **AUC** = probabilidad de que una tienda H de Nielsen tenga un valor mayor que una L (1 =
# ordena perfecto, 0.5 = azar), con IC95 por bootstrap; (b) la letra con **cuatro cortes**, igual que se pidió:
#
# | Corte | Qué es | Para qué variables |
# |---|---|---|
# | relativo | la media de las 65 tiendas | todas |
# | por cadena | la media de su cadena (el análogo del **subcanal** con que compara el 06) | todas |
# | del 06 | la media de nuestros **PDV Tradicional objetivo** (el corte que usa hoy la Letra 1) | escala N (1-6) |
# | referencia Nielsen | N de su referencia regional (N ≥ 3.01) | escala N (1-6) |
#
# **Por qué:** el AUC dice si el insumo **ordena** las zonas como Nielsen sin depender del corte; la exactitud dice si con ese corte
# sale la **misma letra**. Separar ambas cosas dice si lo que hay que cambiar es el insumo o el corte.

# %%
media_cadena = lambda col: zm.groupby("cadena")[col].transform("mean")
ESCALA_N = {"1 · NSE del punto (hexágono res 10)": "N_punto", "2 · NSE de su AGEB": "N_ageb", "4 · Clúster NSE (INEGI)": "N_cluster",
            "6 · Clúster NSE + AltScore (Letra 1 del 06)": "N_cluster_alt", "7b · Buffer de la propia tienda": "N_buffer_tienda"}
OTRAS = {"3 · Índice del Censo por manzana (clúster)": "censo_cluster", "5 · AltScore solo (clúster)": "alt_cluster",
         "7 · % ABC+ del clúster": "abc_cluster"}
CORTE_06 = {"N_punto": ob.N_punto.mean(), "N_ageb": ob.N_ageb.mean(), "N_cluster": ob.N_inegi.mean(), "N_cluster_alt": ob.N.mean(),
            "N_buffer_tienda": ob.N_pdv.mean()}
pasos, auc = [], []
for nombre, col in {**ESCALA_N, **OTRAS}.items():
    x_ = zm[col]
    ok = x_.notna()
    a_ = roc_auc_score(zm.L1n[ok] == "H", x_[ok])
    lo_, hi_ = boot(lambda y, x: roc_auc_score(y, x), (zm.L1n[ok] == "H").to_numpy(), x_[ok].to_numpy())
    auc.append({"paso": nombre, "AUC": a_, "IC95 AUC": f"[{lo_:.2f}, {hi_:.2f}]", "n": int(ok.sum()),
                "ρ con el N de Nielsen": stats.spearmanr(x_[ok], zm.N_nielsen[ok])[0]})
    pasos.append(medir(nombre, col, "relativo (media de las 65)", zm.L1n, x_, x_.mean()))
    pasos.append(medir(nombre, col, "por cadena (análogo del subcanal)", zm.L1n, x_, media_cadena(col)))
    if col in ESCALA_N.values():
        pasos.append(medir(nombre, col, "del 06 (media de nuestros PDV Tradicional)", zm.L1n, x_, CORTE_06[col]))
        pasos.append(medir(nombre, col, f"referencia Nielsen (N ≥ {N_REF:.2f})", zm.L1n, x_, N_REF))
auc = pd.DataFrame(auc)
pasos = pd.DataFrame(pasos)
display(auc.round(3))
display(pasos.round(3))
mejor_auc = auc.loc[auc.AUC.idxmax()]
PASOS = (f"Todos los insumos NSE ordenan las zonas como Nielsen (AUC de {auc.AUC.min():.2f} a {auc.AUC.max():.2f}); el que más se acerca es "
         f"{mejor_auc.paso} (AUC {mejor_auc.AUC:.2f} {mejor_auc['IC95 AUC']}). AltScore solo es el más débil (AUC "
         f"{auc.set_index('paso').loc['5 · AltScore solo (clúster)', 'AUC']:.2f}). La exactitud depende sobre todo del corte (tabla de pasos).")
print(PASOS)

fig, ax = plt.subplots(1, 2, figsize=(17, 6))
aa = auc.sort_values("AUC")
ax[0].barh(aa.paso, aa.AUC, color=[eda.PALETA[0] if "06" in p_ else eda.MUTED for p_ in aa.paso])
ax[0].axvline(0.5, color=eda.PALETA[7], ls="--", lw=1)
ax[0].set(xlim=(0.4, 1.0), xlabel="AUC contra la 1.ª letra de Nielsen (0.5 = azar)", title="2. ¿Cada paso ordena las zonas como Nielsen?")
ax[0].tick_params(axis="y", labelsize=8)
pv = pasos.pivot_table(index="paso", columns="corte", values="exactitud")
pv.plot.barh(ax=ax[1], width=0.8)
ax[1].set(xlabel="exactitud (misma letra que Nielsen)", title="… y ¿con qué corte sale la misma letra?", xlim=(0.4, 1.0))
ax[1].legend(fontsize=7, loc="lower right")
ax[1].tick_params(axis="y", labelsize=8)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 3. Sensibilidad: peso de AltScore (λ) y radio del buffer
#
# **Qué se hace:** se repite el paso 6 con λ de 0 a 1 y el paso 4 con buffers de 200 m a 1.5 km desde el centro del clúster, con el
# corte relativo y el del 06.
#
# **Por qué:** λ = 0.25 y 300 m son decisiones nuestras; si otro valor acerca mucho más a Nielsen, es evidencia para cambiarlo.

# %%
sens = []
for lam in [0, 0.1, 0.25, 0.5, 0.75, 1.0]:
    x_ = pd.Series(n_star(lam))
    corte_06_lam = float(LT.mover_nse(ob.N_inegi, ob.N_alt, lam).mean())      # media de nuestros PDV con ese mismo λ
    for corte, u_ in [("relativo", x_.mean()), ("del 06", corte_06_lam)]:
        f_ = medir("λ AltScore", f"λ = {lam:g}", corte, zm.L1n, x_, u_)
        f_["AUC"] = roc_auc_score(zm.L1n == "H", x_)
        sens.append(f_)
for r_ in [200, 300, 400, 600, 800, 1000, 1500]:
    hh_r = LT.suma_area(hx, LT.hexagonos_en_radio(cla, clo, r_, C.H3_RES)).set_axis(NSE, axis=1)
    x_ = LT.nivel_medio(hh_r)
    f_ = medir("radio del clúster", f"{r_} m", "relativo", zm.L1n, x_, x_.mean())
    f_["AUC"] = roc_auc_score(zm.L1n == "H", x_)
    sens.append(f_)
sens = pd.DataFrame(sens)
display(sens[["paso", "variable", "corte", "exactitud", "κ de Cohen", "IC95 κ", "AUC", "% H nuestro"]].round(3))
SENS = ("λ de AltScore: " + " · ".join(f"{r.variable} {r.exactitud:.0%}" for r in sens[sens.paso.eq("λ AltScore") & sens.corte.eq("relativo")].itertuples())
        + " (corte relativo). Radio: " + " · ".join(f"{r.variable} {r.exactitud:.0%}" for r in sens[sens.paso.eq("radio del clúster")].itertuples()) + ".")
print(SENS)

# %% [markdown]
# ## 4. Exactitud final de la primera letra
#
# **Qué se hace:** tres números: (1) **el proceso tal como lo usa hoy el 06** (clúster NSE + AltScore λ = 0.25, corte = media de
# nuestros PDV Tradicional); (2) **el mismo proceso con el mejor corte** sin usar información de Nielsen (relativo o por cadena);
# (3) el **techo** (su propio perfil con su referencia). Más la matriz de confusión del proceso del 06.
#
# **Por qué:** es la respuesta directa para el tomador de decisiones: hoy acertamos X; con un cambio de corte acertaríamos Y; lo
# máximo alcanzable con esta regla es Z.

# %%
p06 = pasos[pasos.variable.eq("N_cluster_alt") & pasos.corte.str.startswith("del 06")].iloc[0]
cand = pasos[pasos.variable.isin(["N_cluster", "N_cluster_alt"]) & pasos.corte.str.startswith(("relativo", "por cadena"))]
pmejor = cand.loc[cand.exactitud.idxmax()]
final_l1 = pd.DataFrame([
    {"proceso": "Hoy (06): clúster NSE + AltScore, corte de nuestros PDV", **{k: p06[k] for k in ["n", "exactitud", "IC95 exactitud", "κ de Cohen", "IC95 κ", "lectura κ", "% H nuestro", "% H Nielsen"]}},
    {"proceso": f"Mejor corte: {pmejor.paso.split('· ')[1]} · {pmejor.corte}", **{k: pmejor[k] for k in ["n", "exactitud", "IC95 exactitud", "κ de Cohen", "IC95 κ", "lectura κ", "% H nuestro", "% H Nielsen"]}},
    {"proceso": "Techo: perfil y referencia de Nielsen", **{k: techo[k] for k in ["n", "exactitud", "IC95 exactitud", "κ de Cohen", "IC95 κ", "lectura κ", "% H nuestro", "% H Nielsen"]}},
])
final_l1["azar"] = float(((zm.L1n.value_counts(normalize=True)) ** 2).sum())
display(final_l1.round(3))
let06 = np.where(zm.N_cluster_alt >= CORTE_06["N_cluster_alt"], "H", "L")
display(pd.crosstab(zm.L1n.rename("Nielsen"), pd.Series(let06, name="nuestra (06)"), margins=True))
FINAL_L1 = (f"Primera letra: hoy (proceso del 06) acertamos {p06.exactitud:.0%} (κ {p06['κ de Cohen']:.2f} {p06['IC95 κ']}); con el mejor corte "
            f"({pmejor.corte}) {pmejor.exactitud:.0%} (κ {pmejor['κ de Cohen']:.2f}); el techo con la regla de Nielsen es {techo['exactitud']:.0%}. "
            f"El corte del 06 marca H el {p06['% H nuestro']:.0f}% de las zonas contra {p06['% H Nielsen']:.0f}% de Nielsen: ahí está la diferencia.")
print(FINAL_L1)

# %% [markdown]
# ## 5. Entregable sencillo: el QA en %
#
# **Qué se hace:** una sola hoja (`qa/salidas/QA_en_porcentaje_bepensa_zm_merida.xlsx`) con el % de supermercados de Nielsen en
# los que acertamos su letra, en las dos formas de inferirla:
# **QA 1 · tiendas alrededor** (la letra de la mayoría de nuestras tiendas Tradicional a 500 m) y **QA 2 · punto geográfico**
# (nuestro proceso de la Letra 1 aplicado en la coordenada del supermercado). El detalle técnico queda en los notebooks.

# %%
import excel_kin as X

f1 = pd.read_parquet(OUT / "qa1_exactitud_final.parquet").set_index("comparación")
g1 = f1.loc["Letra 1 · geografía (mayoría de nuestros PDV a 500 m)"]
g2 = f1.loc["Letra 2 · geografía (mayoría de nuestros PDV a 500 m)"]
g12 = f1.loc["Clúster · L1 y L2 geografía (mayoría de nuestros PDV a 500 m)"]
TIENDAS = "Letra de la mayoría de nuestras tiendas Tradicional a 500 m del supermercado"
PUNTO = "Nuestro proceso de la Letra 1 (NSE del clúster + AltScore) en la coordenada del supermercado"
resumen = pd.DataFrame([
    ("QA 1 · Tiendas alrededor", TIENDAS, "Letra 1 (NSE)", g1.exactitud, int(g1.n)),
    ("QA 1 · Tiendas alrededor", TIENDAS, "Letra 2 (venta)", g2.exactitud, int(g2.n)),
    ("QA 1 · Tiendas alrededor", TIENDAS, "Las dos letras", g12.exactitud, int(g12.n)),
    ("QA 2 · Punto geográfico", PUNTO, "Letra 1 · como hoy (corte del 06)", p06.exactitud, int(p06.n)),
    ("QA 2 · Punto geográfico", PUNTO, f"Letra 1 · con el corte {pmejor.corte.split(' (')[0]}", pmejor.exactitud, int(pmejor.n)),
], columns=["QA", "cómo se infiere la letra", "letra", "% de acierto", "supermercados"])
resumen["% de acierto"] = (resumen["% de acierto"] * 100).round(0)
display(resumen)
NOTA = ("% de acierto = % de supermercados de Nielsen (Golden Stores Sueros FY'23, ZM Mérida) con la misma letra que la nuestra. "
        "Nielsen es canal Moderno y nosotros Tradicional: no hay tiendas en común, se compara la zona.")
wb = X.libro()
X.hoja_tabla(wb, "QA en %", resumen, titulo="¿Cuánto le atinamos a las letras de Nielsen?", nota=NOTA, ajustar=True,
             formatos={"% de acierto": r"0\%"}, anchos={"QA": 26, "cómo se infiere la letra": 62, "letra": 34, "% de acierto": 14, "supermercados": 14})
XLSX = OUT / f"QA_en_porcentaje_{C.CLIENTE}_{C.SLUG}.xlsx"
try:
    wb.save(XLSX)
except PermissionError:
    XLSX = XLSX.with_name(XLSX.stem + "_nuevo.xlsx")
    wb.save(XLSX)
    print("AVISO: el Excel anterior está abierto; esta versión quedó en otro archivo.")
print("Guardado:", XLSX.relative_to(BASE))
