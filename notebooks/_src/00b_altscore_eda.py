# %% [markdown]
# # 00b · EDA matemático-estadístico y selección de señales AltScore (enrichedgeodata) — Bepensa, ZM Mérida
#
# **Papel en el flujo:** AltScore es **una variable socioeconómica más**, que complementa al NSE AMAI que se construye
# con INEGI (notebooks 01 y 04). Este notebook (1) revisa con pruebas formales la calidad, la estructura y las
# correlaciones de sus señales, (2) construye el **índice NSE AltScore** y (3) **decide qué señales pasan al resto
# del flujo** con reglas explícitas (sección 8). El notebook 04 proyecta el índice y las señales seleccionadas al área de
# 300 m de cada PDV **por hexágono H3** y las compara con el NSE de INEGI.
#
# **Fuente (del cliente, en `data/raw/merida/bepensa/enrichedgeodata/`, no se sube a git):** exportación
# `geohex_geodig.parquet` de AltScore (actualizada el 2026-09-30; fecha de análisis 2024-07-16), una fila por `foreignKey`
# (UUID, aquí `pos_id`) con su ubicación (`location.lat/lng`) y sus celdas H3 (`geoHexData_hexIdx_res7/8/9`). Diccionario:
# *AltScore Data Dictionary 21/12/2022* — Geo Digital Track (tráfico web por categoría, dispositivo, sistema operativo e
# idioma, en una malla de ~1 km) y Geo Hex Data (amenidades, edificios —conteo, área y altura—, vías, comercios y parques
# OSM por celda H3 res 7/8/9; índices de costo de vida y conectividad del municipio). La exportación cubre la península:
# **solo entra la ZM**, por ubicación dentro de sus municipios (igual que Rappi).
#
# **Limpieza:** los códigos −999999, −999998 y −999997 son "sin dato" o error y se vuelven NaN (también en `hexIdx`). Los
# idiomas vienen por idioma y se arman los 3 agregados de la exportación anterior (% español, % portugués y % de los demás).
# Entran al EDA los % digitales, las métricas OSM en res 8 y res 9 y los índices del municipio; quedan fuera res 7 (≈ 5 km²,
# mucho más grande que el área de 300 m), las reescalas `*PctOfMax`, los índices adm0/adm1 (constantes en la ZM) y los
# conteos digitales crudos (`altscore.senales`).
#
# **Regla de cruce: por ubicación, nunca por `pos_id`.** El UUID de AltScore no coincide con el `pos_id` del CP ni con el
# de ventas: la unión con los PDV la hace el 04 por el hexágono H3 de cada registro.
#
# **Convenciones (método retail-math-eda):**
# * **Grano:** `pos_id` de AltScore. Si muchos PDV comparten exactamente las mismas señales (misma zona), la muestra
#   efectiva es de **contextos únicos**: toda la estadística se hace sobre ellos y las p de las correlaciones usan el
#   número de pares de valores **distintos** (si no, salen optimistas por pseudo-replicación).
# * **Pruebas:** Spearman (principal), Pearson sobre log1p y τ de Kendall (robustez), IC95 de Fisher, p de permutación,
#   información mutua (no linealidad), q de Benjamini-Hochberg sobre todas las pruebas, correlación parcial, prueba de
#   Meng para correlaciones dependientes, KMO y Bartlett, análisis paralelo de Horn, α de Cronbach, MCD y bootstrap.
# * **No aplica** market basket, RFM, elasticidad, ABC-XYZ ni series de tiempo: no hay transacciones, precios ni fechas.
#
# **Reproducir:** no depende de ningún otro notebook (`python src/correr.py --pasos 00b merida`). El 04 lee sus salidas.
# Todo lo aleatorio usa la semilla fija `eda.SEMILLA`.

# %%
import os
import sys
import platform
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")       # Bepensa se analiza para la ZM Mérida; cambiar antes de importar config
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import scipy
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster, leaves_list
from scipy.spatial.distance import squareform
from sklearn.covariance import MinCovDet
from IPython.display import display

import geopandas as gpd
import pyarrow.parquet as pq

import config as C
import altscore as A
import eda
from descargas import descargar_fuente, extraer

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"Los datos de {C.CLIENTE} son de {C.CLIENTE_CIUDAD}; CIUDAD={C.CIUDAD}"
eda.estilo()
rng = np.random.default_rng(eda.SEMILLA)
AZUL, NARANJA, VERDE, AMBAR = eda.PALETA[:4]
DIVERGENTE = LinearSegmentedColormap.from_list("div", [AZUL, eda.FONDO, NARANJA])
pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.3f}".format)
print(f"Repo: {BASE} | ciudad: {C.ZM_NOMBRE} | semilla: {eda.SEMILLA} | Python {platform.python_version()} · "
      f"pandas {pd.__version__} · numpy {np.__version__} · scipy {scipy.__version__}")

# procedencia de los archivos del cliente (igual que el notebook 00): archivo, filas, fecha y SHA-256
partes = A.archivos(C.CLIENTE_ALTSCORE)
FUENTES_ALTSCORE = pd.DataFrame([{
    "insumo": "AltScore enrichedgeodata", "archivo": p.name, "ruta": str(p.relative_to(BASE)), "bytes": p.stat().st_size,
    "filas": pq.ParquetFile(p).metadata.num_rows,
    "modificado": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in partes])
FUENTES_ALTSCORE.to_csv(C.PROC / f"fuentes_cliente_{C.CLIENTE}_00b.csv", index=False)
print(f"{len(partes)} archivos · {FUENTES_ALTSCORE.bytes.sum() / 1e6:.1f} MB · {FUENTES_ALTSCORE.filas.sum():,} filas")

# %% [markdown]
# ## 1. Grano, llave, ubicación y composiciones

# %%
d = A.cargar(C.CLIENTE_ALTSCORE)
loc = A.ubicacion(d)
tiene_loc = bool(loc["hex"] or (loc["lat"] and loc["lon"]))
N_TOTAL, N_COLS = len(d), d.shape[1]
print(f"Exportación: {N_TOTAL:,} filas · {N_COLS} columnas · {d.attrs.get('centinelas', 0):,} celdas con código de 'sin dato' "
      f"(−999999/−999998/−999997) → NaN")
UNIVERSO = pd.Series(dtype=int)
if loc["lat"] and loc["lon"]:                                   # universo: solo la ZM, por ubicación dentro de sus municipios
    descargar_fuente(C.FUENTES["mg"])
    D_MG = extraer(C.ARCHIVOS["mg"])
    mun = gpd.read_file(next(D_MG.rglob(f"{C.ENT}mun.shp")))
    mun = mun[mun.CVE_MUN.isin(C.ZM_MUNICIPIOS)].to_crs(4326)
    pts_a = gpd.GeoDataFrame(d[["pos_id"]], geometry=gpd.points_from_xy(d[loc["lon"]], d[loc["lat"]]), crs=4326)
    en_mun = gpd.sjoin(pts_a, mun[["NOMGEO", "geometry"]], predicate="within", how="left")
    d["municipio"] = en_mun[~en_mun.index.duplicated()].NOMGEO.reindex(d.index).to_numpy()
    UNIVERSO = d.municipio.value_counts()
    print(f"En la {C.ZM_NOMBRE}: {d.municipio.notna().sum():,} filas ({d.municipio.notna().mean():.1%}): "
          + ", ".join(f"{k} {v:,}" for k, v in UNIVERSO.items()) + f" · fuera (resto de la península): {d.municipio.isna().sum():,}")
    dig_pen = [c for c in A.senales(d) if A.familia(c) == "digital"]      # referencia: la escala anterior en toda la península
    b_pen = d[dig_pen].dropna(subset=A.PROXIES_NSE).drop_duplicates()
    ALFA_PENINSULA = A.alfa_cronbach(np.column_stack([A.rango_normal(b_pen[c]) for c in A.PROXIES_NSE]))
    print(f"Referencia: los 4 proxies de la exportación anterior (iOS, macOS, viajes, idiomas no españoles) dan α = {ALFA_PENINSULA:.2f} "
          f"en la península ({len(b_pen):,} vectores digitales)")
    d = d[d.municipio.notna()].reset_index(drop=True)
else:
    ALFA_PENINSULA = np.nan
S = d[A.senales(d)]
FAM = pd.Series({c: A.familia(c) for c in S.columns})
print(f"Filas: {len(d):,} · señales: {S.shape[1]} ({FAM.value_counts().to_dict()})")
print(f"pos_id único: {d.pos_id.is_unique} · formato: UUID v{d.pos_id.str[14].mode()[0]} (aleatorio: no se deriva de otro id)")
print("Ubicación en la exportación:", {k: v for k, v in loc.items() if v} or "NINGUNA (sin lat/lon ni hexIdx)")

u = S.drop_duplicates().reset_index(drop=True)                 # contextos únicos
FAMS = [f for f in ["digital", "entorno", "contexto", "visitas"] if (FAM == f).any()]
grano = pd.DataFrame({f: {"señales": int((FAM == f).sum()),
                          "vectores distintos": S.loc[:, FAM == f].dropna(how="all").drop_duplicates().shape[0]} for f in FAMS}).T
grano["filas por vector (mediana)"] = [S.loc[:, FAM == f].dropna(how="all").value_counts().median() for f in grano.index]
print(f"Contextos únicos (las {S.shape[1]} señales iguales): {len(u):,} de {len(d):,} filas "
      f"({(1 - len(u) / len(d)):.0%} de las filas repite el contexto de otra)")
display(grano)

composiciones = {"sistema operativo": [c for c in S if c.startswith("geoDigTrack_os_") and c.endswith("Pct")],
                 "dispositivo": [c for c in S if c.startswith("geoDigTrack_device_")],
                 "categoría web": [c for c in S if c.startswith("geoDigTrack_cat1_")],
                 "idioma": ["not_sp_pt_lang_Pct", "sp_lang_Pct", "pt_lang_Pct"],
                 "franja de visitas": [c for c in S if c.startswith("visit_index_")]}
composiciones = {k: v for k, v in composiciones.items() if v}                # solo las que vienen en la exportación
cierre = pd.DataFrame({k: S[v].dropna().sum(axis=1).agg(["min", "max"]) for k, v in composiciones.items()}).T.round(3)
cierre["complemento que se excluye"] = [A.corto(next(c for c in A.COMPLEMENTOS if c in v)) for v in composiciones.values()]
display(cierre)
constantes = [c for c in S if S[c].nunique(dropna=True) <= 1]
print("Señales constantes:", constantes)

# zona de medición de cada señal = vector de su familia (filas con el mismo vector = misma medición repetida)
ZONA = {f: pd.util.hash_pandas_object(u[[c for c in S if FAM[c] == f]].fillna(-9e9), index=False).factorize()[0] for f in FAMS}
zonas_x_digital = pd.DataFrame({"dig": ZONA["digital"], "ent": ZONA["entorno"]}).groupby("dig").ent.nunique()
print(f"Grano digital: cada vector digital cubre en mediana {zonas_x_digital.median():.0f} zonas de entorno "
      f"(p90 {zonas_x_digital.quantile(0.9):.0f}, máximo {zonas_x_digital.max():,}): el bloque digital es más grueso que el OSM.")

fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
ax[0].barh(grano.index, grano["vectores distintos"], color=AZUL)
ax[0].set_title("Vectores distintos por familia de señales")
ax[0].set_xscale("log")
ax[1].hist(S.value_counts().to_numpy(), bins=np.logspace(0, 3.5, 40), color=AZUL)
ax[1].set_xscale("log")
ax[1].set_title("PDV que comparten el mismo contexto")
ax[1].set_xlabel("filas por contexto (log)")
ax[1].hist(zonas_x_digital.to_numpy(), bins=np.logspace(0, 3.2, 40), color=NARANJA, alpha=0.6, label="zonas de entorno por vector digital")
ax[1].legend(fontsize=7)
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** el grano real de las señales **no es el PDV**. El bloque digital tiene ~1,070 vectores distintos para
# ~83 mil filas: es una medición por zona, repetida en todos los PDV de la zona. Los % de sistema operativo, dispositivo,
# categoría web, idioma y franja de visitas son **composiciones** (suman 1 o 100). Entre sus partes hay correlación
# negativa por construcción, así que de cada una se excluye una parte, el complemento (sección 4.3).

# %% [markdown]
# ## 2. Faltantes: cobertura, patrones y mecanismo

# %%
bloques = {
    "digital (web por zona)": [c for c in S if FAM[c] == "digital"],
    "visitas": [c for c in S if FAM[c] == "visitas"],
    "costo de vida (adm2)": ["geoHexData_idx_costOfLiving_v1_adm2"],
    "conectividad (adm2)": ["geoHexData_idx_techAndConnectivity_v1_adm2"],
    **{f"{f} res {r}": [c for c in S if f"_{f}_res{r}" in c] for f in ["amenity", "building", "shop"] for r in (8, 9)},
    **{f"vías res {r}": [c for c in S if f"_road_res{r}" in c] for r in (8, 9)},
    **{f"parques res {r}": [c for c in S if f"_leisure_res{r}" in c] for r in (8, 9)},
}
bloques = {k: v for k, v in bloques.items() if v}                            # solo los bloques que trae la exportación
BLOQUE_DE = {c: k for k, v in bloques.items() for c in v}
M = pd.DataFrame({k: S[v].isna().all(axis=1) for k, v in bloques.items()})
parcial = {k: int((S[v].isna().any(axis=1) & ~S[v].isna().all(axis=1)).sum()) for k, v in bloques.items()}
faltantes = pd.DataFrame({"señales": {k: len(v) for k, v in bloques.items()}, "% filas sin el bloque": M.mean() * 100,
                          "filas con nulos parciales": parcial}).sort_values("% filas sin el bloque")
display(faltantes.round(1))
print("Anidamiento res 9 ⊂ res 8 (amenidades): sin res 8 pero con res 9 =",
      int((M["amenity res 8"] & ~M["amenity res 9"]).sum()), "| sin res 9 pero con res 8 =", int((~M["amenity res 8"] & M["amenity res 9"]).sum()))

# índice NSE AltScore: un solo ajuste (en contextos digitales únicos) para todo el notebook; detalle en la sección 6
base_items = u.dropna(subset=A.CANDIDATOS_NSE[:-1]).drop_duplicates(subset=[c for c in S if FAM[c] == "digital"])
CAND = [c for c in A.CANDIDATOS_NSE if "_adm" not in c and base_items[c].nunique() > 5]   # a priori y locales: los índices del
                                                                              # municipio (adm2) miden diferencias entre municipios
PROXIES, traza_items = A.seleccionar_proxies(base_items, CAND)               # análisis de ítems en la ZM (detalle en la sección 6)
iu = A.indice_nse(u, cols=PROXIES, ajuste=base_items)[0]


def boot_zona(fn, df, B=300):
    """IC95 de fn(df) remuestreando zonas digitales completas (df trae la columna 'zona'): respeta que las filas de una
    misma zona repiten la medición digital, cosa que un IC por filas ignora."""
    idx_z = df.groupby("zona").indices
    llaves = np.array(list(idx_z))
    bs = [fn(df.iloc[np.concatenate([idx_z[k] for k in rng.choice(llaves, llaves.size)])]) for _ in range(B)]
    return np.nanquantile(bs, [0.025, 0.975])


# ¿MCAR? Si falta un bloque, ¿cambia el perfil socioeconómico digital de la zona? (contextos únicos)
mcar = []
for k, v in bloques.items():
    if k.startswith("digital"):
        continue                                               # el índice se calcula con este bloque
    falta = u[v].isna().all(axis=1)
    a, b = iu[falta].dropna(), iu[~falta].dropna()
    if len(a) < 30 or len(b) < 30:
        continue
    dz = pd.DataFrame({"i": iu, "f": falta, "zona": ZONA["digital"]}).dropna(subset=["i"])
    lo_d, hi_d = boot_zona(lambda t: eda.cliff_delta(t.i[t.f], t.i[~t.f]) if t.f.any() and (~t.f).any() else np.nan, dz, B=200)
    mcar.append({"bloque": k, "contextos sin bloque": int(falta.sum()), "mediana índice sin": a.median(), "mediana índice con": b.median(),
                 "delta de Cliff": eda.cliff_delta(a, b), "IC95 δ (bootstrap por zona)": f"[{lo_d:+.2f}, {hi_d:+.2f}]",
                 "δ excluye 0": bool(lo_d > 0 or hi_d < 0), "p (Mann-Whitney)": stats.mannwhitneyu(a, b).pvalue})
mcar = pd.DataFrame(mcar)
mcar["q_BH"] = stats.false_discovery_control(mcar["p (Mann-Whitney)"], method="bh")
mcar["lectura"] = np.where((mcar["delta de Cliff"].abs() < 0.147) | ~mcar["δ excluye 0"],
                           "compatible con MCAR (efecto despreciable o IC incluye 0)", "no MCAR: el faltante depende del tipo de zona")
display(mcar.sort_values("delta de Cliff").round(3))

patrones = M.value_counts().head(12)
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), gridspec_kw={"width_ratios": [2.2, 1, 1.4]})
ax[0].imshow(np.array(patrones.index.tolist(), float), aspect="auto", cmap=LinearSegmentedColormap.from_list("m", [eda.FONDO, eda.TINTA_2]))
ax[0].set_xticks(range(M.shape[1]), M.columns, rotation=60, ha="right", fontsize=7)
ax[0].set_yticks(range(len(patrones)), [f"{n:,}" for n in patrones.to_numpy()], fontsize=7)
ax[0].set_ylabel("filas con el patrón")
ax[0].set_title("12 patrones de faltantes más frecuentes (oscuro = falta)")
ax[0].grid(False)
f_ = faltantes["% filas sin el bloque"]
ax[1].barh(f_.index, 100 - f_, color=[VERDE if 100 - x >= 40 else AMBAR for x in f_])
ax[1].axvline(40, color=eda.MUTED, ls="--", lw=1)
ax[1].set_title("Cobertura por bloque (% filas)")
ax[1].tick_params(axis="y", labelsize=7)
orden = mcar.sort_values("delta de Cliff")
ax[2].barh(orden.bloque, orden["delta de Cliff"], color=[NARANJA if abs(x) >= 0.147 else eda.MUTED for x in orden["delta de Cliff"]])
ax[2].axvline(-0.147, color=eda.MUTED, ls=":", lw=1)
ax[2].axvline(0.147, color=eda.MUTED, ls=":", lw=1)
ax[2].set_title("¿MCAR? δ de Cliff del índice NSE (sin vs con bloque)")
ax[2].tick_params(axis="y", labelsize=7)
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** los faltantes son **por bloque completo** (casi no hay nulos parciales) y **anidados** por resolución:
# res 9 falta mucho más que res 8. En los conteos OSM, "sin bloque" es "no hay objetos mapeados en la celda", una mezcla
# de cero estructural y falta de cobertura OSM, y **se concentra en zonas de índice NSE más bajo** (δ < 0: no MCAR).
# El costo de vida solo existe en zonas de índice alto. Consecuencias: **no se imputa con la media**; el índice NSE se
# arma solo con el bloque digital (cobertura ≈ 90%); una señal necesita cobertura suficiente para pasar al flujo
# (regla R2 de la sección 9).

# %% [markdown]
# ## 3. Univariado, colas y concentración (contextos únicos)

# %%
clave = [c for c in A.CANDIDATOS_NSE] + ["geoHexData_idx_costOfLiving_v1_adm2", "geoHexData_building_res8_count", "geoHexData_building_res8_meanArea",
                                         "geoHexData_amenity_res8_count_sustenance", "geoHexData_amenity_res8_count_bank",
                                         "geoHexData_road_res8_count_residential", "geoHexData_shop_res8_count_foodAndDrink",
                                         "visits_percofmax", "weekend_visits_Pct"]
clave = [c for c in clave if c in S.columns]
uni = eda.univariado(u, clave)
display(uni[["n", "ceros_%", "mediana", "mediana_IC95", "MAD_n", "p99", "asimetria", "curtosis_exc", "gini", "hill_alpha", "lectura"]].round(3))
colas = {A.corto(c): eda.ajuste_distribuciones(u[c].dropna().to_numpy())[["familia", "AIC", "ΔAIC", "KS_D"]].iloc[0]
         for c in ["geoHexData_building_res8_meanArea", "geoHexData_amenity_res8_count_sustenance", "geoDigTrack_os_iosPct", "visits_percofmax"]
         if c in S.columns}
display(pd.DataFrame(colas).T.rename_axis("mejor ajuste por AIC (lognormal, gamma, Weibull, exponencial)"))

fig, axs = plt.subplots(3, 4, figsize=(14, 7.5))
for ax, c in zip(axs.flat, clave[:12]):
    x = u[c].dropna()
    pesada = uni.loc[c, "asimetria"] > 2
    ax.hist(np.log1p(x) if pesada else x, bins=40, color=AZUL if FAM[c] == "digital" else VERDE if FAM[c] == "entorno" else AMBAR)
    ax.axvline(np.log1p(x.median()) if pesada else x.median(), color=eda.TINTA, lw=1)
    ax.set_title(("log1p · " if pesada else "") + A.corto(c), fontsize=8)
    ax.tick_params(labelsize=7)
plt.suptitle("Distribución por contexto único (línea = mediana; azul digital, verde entorno, ámbar contexto)", x=0.01, ha="left", fontsize=10)
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** las proporciones digitales tienen asimetría moderada, pero los conteos OSM y el área de edificios tienen
# **colas pesadas** (asimetría > 2, Hill bajo, mejor ajuste lognormal): una media o una correlación de Pearson las
# dominarían unas pocas celdas comerciales. Por eso las dependencias se miden con **rangos** y todo se transforma a
# normal por rangos antes de analizar la estructura.

# %% [markdown]
# ## 4. Correlaciones y sus pruebas
# ### 4.1 Matriz completa (Spearman, n efectivo por zonas, BH) y grupos de señales redundantes
# La p de cada par usa el número de **combinaciones de zonas distintas** en que se midieron las dos señales, no el número
# de filas: dos señales digitales de una zona repetida 50 veces aportan una observación, no 50.

# %%
SIN_INFO = set(constantes) | set(A.COMPLEMENTOS) | set(A.DERIVADAS)
cand = [c for c in S if c not in SIN_INFO]
rho, n_ef, p_ef, q_ef = eda.matriz_spearman(u, cand, zonas={c: ZONA[FAM[c]] for c in cand})
iu_ = np.triu_indices(len(cand), 1)
pares = pd.DataFrame({"x": np.array(cand)[iu_[0]], "y": np.array(cand)[iu_[1]], "spearman": rho.to_numpy()[iu_],
                      "n efectivo": n_ef.to_numpy()[iu_], "p": p_ef.to_numpy()[iu_], "q_BH": q_ef.to_numpy()[iu_]}).dropna(subset=["spearman"])
pares["n filas"] = [int(u[[a, b]].dropna().shape[0]) for a, b in zip(pares.x, pares.y)]
pares = pares.reindex(pares.spearman.abs().sort_values(ascending=False).index)
print(f"{len(cand)} señales con información · {len(pares):,} pares · q < 0.05 con n efectivo: {(pares.q_BH < 0.05).sum():,} "
      f"· |ρ| ≥ 0.3: {(pares.spearman.abs() >= 0.3).sum()} · |ρ| ≥ 0.7: {(pares.spearman.abs() >= 0.7).sum()}")

# grupos redundantes: enlace promedio sobre 1 - |ρ|; corte en |ρ| = 0.7
Dm = 1 - rho.abs().fillna(0).to_numpy()
np.fill_diagonal(Dm, 0)
enlace = linkage(squareform(Dm, checks=False), "average")
grupo = pd.Series(fcluster(enlace, 0.3, "distance"), index=cand)
redundantes = grupo[grupo.duplicated(keep=False)].sort_values()
display(pd.DataFrame({"grupo": redundantes, "señal": [A.corto(c) for c in redundantes.index]}).reset_index(drop=True))
display(pares.head(15).assign(x=lambda t: t.x.map(A.corto), y=lambda t: t.y.map(A.corto)).round(3))

orden = leaves_list(enlace)
fig, ax = plt.subplots(figsize=(13, 11.5))
im = ax.imshow(rho.to_numpy()[np.ix_(orden, orden)], cmap=DIVERGENTE, vmin=-1, vmax=1)
et = [A.corto(cand[i]) for i in orden]
ax.set_xticks(range(len(et)), et, rotation=90, fontsize=5.5)
ax.set_yticks(range(len(et)), et, fontsize=5.5)
for i, c in enumerate(np.array(cand)[orden]):
    col = {"digital": AZUL, "entorno": VERDE, "contexto": AMBAR, "visitas": NARANJA}[FAM[c]]
    ax.get_yticklabels()[i].set_color(col)
    ax.get_xticklabels()[i].set_color(col)
ax.grid(False)
plt.colorbar(im, ax=ax, shrink=0.6, label="ρ de Spearman")
ax.set_title("Correlación de Spearman entre señales, ordenada por agrupamiento jerárquico (etiqueta: azul digital, verde entorno, ámbar contexto, naranja visitas)")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** la matriz se ordena en **bloques por familia**: las señales digitales casi no correlacionan con las de
# entorno OSM. Eso indica que miden cosas distintas (perfil de la gente contra infraestructura), no que una sobre. La
# redundancia fuerte (|ρ| ≥ 0.7) es poca y previsible: cada señal res 8 con su versión res 9, bancos con instituciones
# financieras y PC con Windows. De cada grupo queda **una representante** (regla R4).

# %% [markdown]
# ### 4.2 Robustez de las correlaciones más fuertes: Pearson, Spearman, Kendall y permutación

# %%
rob_corr = []
for _, r in pares.head(12).iterrows():
    m = u[[r.x, r.y]].dropna()
    rx_, ry_ = stats.rankdata(m[r.x]), stats.rankdata(m[r.y])
    perm = np.array([np.corrcoef(rx_, rng.permutation(ry_))[0, 1] for _ in range(1000)])
    lo, hi = eda.spearman_ic(r.spearman, r["n efectivo"])
    rob_corr.append({"x": A.corto(r.x), "y": A.corto(r.y), "n efectivo": int(r["n efectivo"]), "spearman": r.spearman, "IC95 Fisher": f"[{lo:+.2f}, {hi:+.2f}]",
                     "pearson log1p": np.corrcoef(np.log1p(m[r.x].clip(lower=0)), np.log1p(m[r.y].clip(lower=0)))[0, 1],
                     "kendall τ": stats.kendalltau(m[r.x], m[r.y])[0],
                     "p permutación": (np.sum(np.abs(perm) >= abs(r.spearman)) + 1) / 1001})
rob_corr = pd.DataFrame(rob_corr)
rob_corr["mismo signo en los 3"] = np.sign(rob_corr.spearman).eq(np.sign(rob_corr["pearson log1p"])) & np.sign(rob_corr.spearman).eq(np.sign(rob_corr["kendall τ"]))
display(rob_corr.round(3))

fig, ax = plt.subplots(figsize=(9, 4))
yy = np.arange(len(rob_corr))
for col, mk, cc in [("spearman", "o", AZUL), ("pearson log1p", "s", NARANJA), ("kendall τ", "D", VERDE)]:
    ax.scatter(rob_corr[col], yy, marker=mk, color=cc, label=col, zorder=3)
ax.set_yticks(yy, rob_corr.x + "  ×  " + rob_corr.y, fontsize=7)
ax.axvline(0, color=eda.EJE, lw=1)
ax.invert_yaxis()
ax.legend(loc="lower right")
ax.set_title("Los pares más correlacionados, con tres estimadores")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** los tres estimadores coinciden en el signo y la magnitud relativa, y la p de permutación descarta el azar
# (permuta filas, así que ignora que varias filas comparten zona; la prueba exigente es el IC por zona de la sección 7).
# τ de Kendall sale menor que ρ por definición (τ ≈ 2/3 ρ), no porque la asociación sea más débil. Pearson sobre log1p
# se aleja de Spearman justo en los conteos con muchos ceros: por eso la decisión se toma con Spearman.

# %% [markdown]
# ### 4.3 Composiciones: la correlación negativa entre partes es en parte artificial

# %%
os_parts = composiciones["sistema operativo"]
m = u[os_parts].dropna()
m = m[(m > 0).all(axis=1)]
clr = np.log(m).sub(np.log(m).mean(axis=1), axis=0)          # transformación log-cociente centrada (Aitchison)
os_ = lambda k: f"geoDigTrack_os_{k}Pct"
pares_os = [(os_("android"), os_("ios")), (os_("ios"), os_("windows")), (os_("macOs"), os_("windows")), (os_("android"), os_("windows"))]
comp = pd.DataFrame({"par": [f"{A.corto(a)} × {A.corto(b)}" for a, b in pares_os],
                     "ρ en %": [stats.spearmanr(m[a], m[b])[0] for a, b in pares_os],
                     "ρ en CLR": [stats.spearmanr(clr[a], clr[b])[0] for a, b in pares_os]})
print(f"Contextos con todas las partes > 0: {len(m):,}")
display(comp.round(3))

# %% [markdown]
# **Lectura:** en una composición, si una parte sube, las otras bajan aunque no haya relación de fondo. Por eso se
# excluye la parte dominante de cada composición (Android, smartphone, español, "otro" contenido y visitas de noche)
# y se trabaja con las partes minoritarias, que son las informativas.

# %% [markdown]
# ### 4.4 ¿Resolución H3 8 o 9? Prueba de Meng para correlaciones dependientes
# Para cada señal que existe en las dos resoluciones: ¿se asocia distinto con el índice NSE AltScore? Las dos
# correlaciones comparten el índice, así que no son independientes: la prueba de Meng, Rosenthal y Rubin (1992) lo
# corrige usando la correlación entre las dos versiones.

# %%
meng = []
for c8 in [c for c in cand if "_res8" in c and c.replace("_res8", "_res9") in S.columns]:
    c9 = c8.replace("_res8", "_res9")
    m = pd.DataFrame({"y": iu, "a": u[c8], "b": u[c9]}).dropna()
    if len(m) < 50:
        continue
    r = m.corr("spearman")
    z, p = eda.meng_z(r.loc["y", "a"], r.loc["y", "b"], r.loc["a", "b"], len(m))
    meng.append({"señal": A.corto(c8).replace("r8 ", ""), "n": len(m), "ρ índice · res 8": r.loc["y", "a"], "ρ índice · res 9": r.loc["y", "b"],
                 "ρ res 8 · res 9": r.loc["a", "b"], "z de Meng": z, "p": p,
                 "cobertura res 8 %": S[c8].notna().mean() * 100, "cobertura res 9 %": S[c9].notna().mean() * 100})
meng = pd.DataFrame(meng)
meng["q_BH"] = stats.false_discovery_control(meng.p, method="bh")
meng["preferir"] = np.where((meng.q_BH < 0.05) & (meng["ρ índice · res 9"].abs() > meng["ρ índice · res 8"].abs()), "res 9", "res 8")
display(meng.round(3))

fig, ax = plt.subplots(figsize=(8, 4))
yy = np.arange(len(meng))
ax.hlines(yy, meng["ρ índice · res 8"], meng["ρ índice · res 9"], color=eda.EJE, lw=2)
ax.scatter(meng["ρ índice · res 8"], yy, color=AZUL, label="res 8", zorder=3)
ax.scatter(meng["ρ índice · res 9"], yy, color=NARANJA, label="res 9", zorder=3)
for k, r in meng.iterrows():
    if r.q_BH < 0.05:
        ax.annotate("q < 0.05", (max(r["ρ índice · res 8"], r["ρ índice · res 9"]) + 0.01, k), fontsize=7, va="center", color=eda.TINTA_2)
ax.set_yticks(yy, meng.señal, fontsize=7)
ax.axvline(0, color=eda.EJE, lw=1)
ax.legend()
ax.set_title("Correlación con el índice NSE AltScore: res 8 vs res 9")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** en casi todas las señales las dos resoluciones dicen lo mismo (q ≥ 0.05) y res 8 tiene casi el doble de
# cobertura. Se usa **res 8**, salvo donde la prueba diga lo contrario.

# %% [markdown]
# ### 4.5 No linealidad: información mutua contra ρ²
# Si la información mutua (MI) es alta pero ρ² es bajo, la relación con el índice NSE existe pero no es monótona, y
# Spearman la subestimaría.

# %%
u_idx = u.assign(indice_nse_altscore=iu, zona=ZONA["digital"])
no_indice = [c for c in cand if c not in PROXIES]
dep_idx = eda.dependencias(u_idx, no_indice, ["indice_nse_altscore"])
dep_idx["ρ²"] = dep_idx.spearman ** 2
fig, ax = plt.subplots(figsize=(8, 4.5))
col = [{"digital": AZUL, "entorno": VERDE, "contexto": AMBAR, "visitas": NARANJA}[FAM[c]] for c in dep_idx.x]
ax.scatter(dep_idx["ρ²"], dep_idx.MI, c=col, s=22)
for _, r in dep_idx.nlargest(8, "MI").iterrows():
    ax.annotate(A.corto(r.x), (r["ρ²"], r.MI), fontsize=6.5, xytext=(3, 2), textcoords="offset points")
ax.set_xlabel("ρ² de Spearman con el índice")
ax.set_ylabel("información mutua (nats)")
ax.set_title("Dependencia con el índice NSE AltScore: monótona (ρ²) vs general (MI)")
plt.tight_layout()
plt.show()
display(dep_idx.sort_values("MI", ascending=False).head(12).assign(x=lambda t: t.x.map(A.corto)).drop(columns="y").round(3))

# %% [markdown]
# **Lectura:** la MI más alta aparece en las **señales digitales**, aunque su ρ² sea bajo. No es una relación no lineal
# fuerte: el índice se calcula con esos mismos vectores de zona, que tienen pocos valores distintos (~1,070), y el
# estimador de MI por vecinos cercanos se infla con valores repetidos. Por eso **la MI no decide por sí sola**: sirve
# para marcar señales que requieren revisión (la sección 7 las mira por decil) y la selección usa ρ, cobertura y cargas.

# %% [markdown]
# ## 5. Estructura común: factorabilidad, número de dimensiones y cargas rotadas

# %%
kmo = []
for nombre, cols, base in [("digital", [c for c in cand if FAM[c] == "digital"], S[[c for c in S if FAM[c] == "digital"]].dropna().drop_duplicates()),
                           ("entorno res 8", [c for c in cand if "_res8" in c], u), ("visitas", [c for c in cand if FAM[c] == "visitas"], u)]:
    if len(cols) < 3:                                              # bloque ausente en la exportación (p. ej. visitas)
        continue
    Bz = pd.DataFrame({c: A.rango_normal(base[c]) for c in cols}).dropna()
    Bz = Bz.loc[:, Bz.std() > 0]
    kb = eda.kmo_bartlett(np.corrcoef(Bz.to_numpy(), rowvar=False), len(Bz))
    kmo.append({"bloque": nombre, "señales": Bz.shape[1], "casos completos": len(Bz), "KMO": kb["KMO"],
                "Bartlett χ²": kb["bartlett_chi2"], "gl": kb["gl"], "p": kb["p"],
                "lectura": "bueno" if kb["KMO"] >= 0.7 else "aceptable" if kb["KMO"] >= 0.6 else "regular" if kb["KMO"] >= 0.5 else "insuficiente"})
kmo = pd.DataFrame(kmo)
display(kmo.round(3))

# PCA sobre la matriz de Spearman por pares (cada par usa sus casos completos), proyectada a semidefinida positiva
Rm = eda.psd(rho.fillna(0).to_numpy())
n_med = int(np.median(n_ef.to_numpy()[iu_]))
val, vec = np.linalg.eigh(Rm)
val, vec = val[::-1], vec[:, ::-1]
umbral = eda.analisis_paralelo(n_med, len(cand), B=200)
K = int(np.argmax(val <= umbral)) if (val <= umbral).any() else len(val)
L = pd.DataFrame(eda.varimax(vec[:, :K] * np.sqrt(val[:K])), index=cand, columns=[f"D{k + 1}" for k in range(K)])
L = L * np.sign(L.sum())                                          # signo: carga total positiva
dim_de = L.abs().idxmax(axis=1)
carga_max = L.abs().max(axis=1)
nombres_dim = {k: " / ".join(A.corto(c) for c in L[k].abs().sort_values(ascending=False).index[:2]) for k in L.columns}
print(f"n efectivo mediano por par: {n_med:,} · Kaiser (λ > 1): {(val > 1).sum()} dimensiones · "
      f"análisis paralelo de Horn (λ > percentil 95 del azar): {K} dimensiones · varianza de las {K}: {val[:K].sum() / val.sum():.0%}")
display(pd.DataFrame({"dimensión": list(nombres_dim), "señales que la definen": list(nombres_dim.values()),
                      "señales con carga máx. aquí": [int((dim_de == k).sum()) for k in nombres_dim]}))

fig, ax = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1, 1.6]})
kk = np.arange(1, 31)
ax[0].plot(kk, val[:30], "o-", color=AZUL, label="observado", ms=4)
ax[0].plot(kk, umbral[:30], "s--", color=NARANJA, label="percentil 95 con datos al azar", ms=3)
ax[0].axvline(K + 0.5, color=eda.MUTED, ls=":")
ax[0].set_title(f"Sedimentación y análisis paralelo: se retienen {K} dimensiones")
ax[0].set_xlabel("componente")
ax[0].set_ylabel("autovalor")
ax[0].legend()
top = L.abs().max(axis=1).sort_values(ascending=False).index[:40]
top = sorted(top, key=lambda c: (dim_de[c], -carga_max[c]))
ax[1].imshow(L.loc[top].to_numpy(), aspect="auto", cmap=DIVERGENTE, vmin=-1, vmax=1)
ax[1].set_yticks(range(len(top)), [A.corto(c) for c in top], fontsize=6)
ax[1].set_xticks(range(K), L.columns, fontsize=7)
ax[1].grid(False)
ax[1].set_title("Cargas varimax (40 señales con mayor carga)")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** Bartlett rechaza la esfericidad en todos los bloques: hay estructura común. El KMO es **bueno en el entorno
# OSM**, regular en lo digital y aceptable en visitas (con el complemento de la composición ya excluido). El análisis
# paralelo, más estricto que Kaiser, retiene varias dimensiones con **comunalidades modestas**: las señales AltScore no
# se resumen en un solo factor. Por eso se elige una representante por dimensión (sección 8) en lugar de usar todo.

# %% [markdown]
# ## 6. Índice NSE AltScore: análisis de ítems, estabilidad y atípicos

# %%
def items(cols, base):
    Z = np.column_stack([A.rango_normal(base[c]) for c in cols])
    Z = Z[~np.isnan(Z).any(axis=1)]
    tot = Z.sum(axis=1)
    r_ir = [stats.spearmanr(Z[:, k], tot - Z[:, k])[0] for k in range(len(cols))]
    return A.alfa_cronbach(Z), pd.Series(r_ir, index=cols)

alfa_7, r_7 = items(CAND, base_items.dropna(subset=CAND))
alfa_4, r_4 = items(PROXIES, base_items)
NOMBRES_PROXIES = ", ".join(A.corto(c) for c in PROXIES)
analisis_items = pd.DataFrame({f"correlación ítem-resto ({len(CAND)} a priori)": r_7, f"correlación ítem-resto ({len(PROXIES)} finales)": r_4})
analisis_items["se queda"] = analisis_items.index.isin(PROXIES)
print(f"α de Cronbach en la ZM: {len(CAND)} proxies a priori = {alfa_7:.2f} · {len(PROXIES)} finales ({NOMBRES_PROXIES}) = {alfa_4:.2f} "
      f"(≥ 0.7 aceptable; con 2 ítems el α tiene techo bajo) · los 4 de la exportación anterior daban {ALFA_PENINSULA:.2f} en la península")
display(traza_items.round(2))
display(analisis_items.rename(index=A.corto).round(2))

idx, cargas, var_pc1 = A.indice_nse(S, cols=PROXIES, ajuste=base_items)          # mismo ajuste, aplicado a cada fila
print(f"PC1 de los {len(PROXIES)} proxies explica {var_pc1:.0%} de su varianza · cobertura del índice: {idx.notna().mean():.1%} de las filas")

boot = []
for _ in range(300):
    m = base_items.sample(len(base_items), replace=True, random_state=rng.integers(1 << 31))
    _, w_b, _ = A.indice_nse(m.head(1), cols=PROXIES, ajuste=m)
    boot.append([*w_b.values, items(PROXIES, m)[0]])
boot = pd.DataFrame(boot, columns=[*PROXIES, "alfa"])
estab = pd.DataFrame({"carga": [*cargas.values, alfa_4], "IC95 inferior": boot.quantile(0.025), "IC95 superior": boot.quantile(0.975)},
                     index=boot.columns)
display(estab.rename(index=A.corto).round(3))

Z4 = np.column_stack([A.rango_normal(base_items[c]) for c in PROXIES])
ok4 = ~np.isnan(Z4).any(axis=1)                                          # MCD solo con filas completas
mcd = MinCovDet(random_state=eda.SEMILLA).fit(Z4[ok4])
d2 = np.full(len(Z4), np.nan)
d2[ok4] = mcd.mahalanobis(Z4[ok4])
corte = stats.chi2.ppf(0.999, len(PROXIES))
atip = base_items.assign(d2=d2)[d2 > corte]
print(f"Contextos atípicos (d² robusta > χ²₀.₉₉₉ = {corte:.1f}): {len(atip):,} de {int(ok4.sum()):,} ({len(atip) / max(ok4.sum(), 1):.1%}). "
      "No se eliminan: el índice es por rangos y no los amplifica.")

fig, ax = plt.subplots(1, 3, figsize=(15, 3.6))
ax[0].boxplot([boot[c] for c in PROXIES], orientation="horizontal", widths=0.5, patch_artist=True, boxprops={"facecolor": AZUL, "alpha": 0.5})
ax[0].set_yticks(range(1, len(PROXIES) + 1), [A.corto(c) for c in PROXIES], fontsize=7)
ax[0].set_title("Cargas del índice en 300 remuestreos")
d2_ok = np.sort(d2[ok4])
qq = stats.chi2.ppf((np.arange(1, len(d2_ok) + 1) - 0.5) / len(d2_ok), len(PROXIES))
ax[1].scatter(qq, d2_ok, s=6, color=AZUL)
ax[1].plot([0, qq.max()], [0, qq.max()], color=eda.MUTED, lw=1)
ax[1].axhline(corte, color=NARANJA, ls="--", lw=1)
ax[1].set_title(f"QQ de d² robusta vs χ²({len(PROXIES)})")
ax[1].set_xlabel("cuantil teórico")
ax[1].set_ylabel("d² observada")
ax[2].hist(idx.dropna(), bins=40, color=eda.TINTA_2)
ax[2].set_title("Índice NSE AltScore (percentil, filas)")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** de los 7 proxies definidos a priori, % PC y finanzas **cargan en contra** y la conectividad del
# hexágono **no correlaciona** con el resto (es otra dimensión, más de infraestructura). Los 4 que quedan forman una
# escala consistente, con cargas estrechas en el bootstrap. La cola del QQ muestra pocos contextos extremos, típicos de
# zonas muy pequeñas. Se eligieron por coherencia interna y **nunca se ajustaron a la venta**: el índice puede
# explicar la venta después sin circularidad.

# %% [markdown]
# ## 7. Validez convergente: correlación simple, parcial y por decil
# Contra señales que **no** entraron al índice. La correlación **parcial** controla la densidad urbana (edificios res 8
# y vías residenciales res 8): así se ve si el índice se asocia con el comercio o con el costo de vida **más allá** de
# que la zona sea más densa.

# %%
externas = ["geoHexData_idx_costOfLiving_v1_adm2", "visits_percofmax", "geoHexData_building_res8_meanArea", "geoHexData_amenity_res8_count_bank",
            "geoHexData_shop_res8_count_clothing", "geoHexData_amenity_res8_count_sustenance", "geoHexData_road_res8_count_residential",
            "geoHexData_idx_techAndConnectivity_v1_adm2", "weekend_visits_Pct"]
externas = [c for c in externas if c in S.columns]
control = ["geoHexData_building_res8_count", "geoHexData_road_res8_count_residential"]
validez = eda.dependencias(u_idx, externas, ["indice_nse_altscore"])
parc = [eda.correlacion_parcial(u_idx.indice_nse_altscore, u_idx[x], u_idx[[c for c in control if c != x]]) for x in validez.x]
validez["spearman parcial (densidad)"] = [p_[0] for p_ in parc]
validez["p parcial"] = [p_[1] for p_ in parc]
validez["q parcial"] = stats.false_discovery_control(validez["p parcial"], method="bh")
perm_p = []
for x in validez.x:
    m = u_idx[["indice_nse_altscore", x]].dropna()
    ra, rb = stats.rankdata(m.iloc[:, 0]), stats.rankdata(m.iloc[:, 1])
    obs = np.corrcoef(ra, rb)[0, 1]
    perm_p.append((np.sum(np.abs([np.corrcoef(ra, rng.permutation(rb))[0, 1] for _ in range(1000)]) >= abs(obs)) + 1) / 1001)
validez["p permutación"] = perm_p
ic_z = [boot_zona(lambda t, x=x: stats.spearmanr(t.indice_nse_altscore, t[x])[0], u_idx[["indice_nse_altscore", x, "zona"]].dropna())
        for x in validez.x]
validez["IC95 bootstrap por zona"] = [f"[{a:+.2f}, {b:+.2f}]" for a, b in ic_z]
validez["IC por zona excluye 0"] = [bool(a > 0 or b < 0) for a, b in ic_z]
validez["zonas digitales"] = [u_idx[["indice_nse_altscore", x, "zona"]].dropna().zona.nunique() for x in validez.x]
display(validez.assign(x=validez.x.map(A.corto)).drop(columns=["y", "pearson_log1p"]).round(3))

fig, ax = plt.subplots(1, 2, figsize=(14, 4))
v = validez.sort_values("spearman")
yy = np.arange(len(v))
ax[0].hlines(yy, v.spearman, v["spearman parcial (densidad)"], color=eda.EJE, lw=2)
ax[0].scatter(v.spearman, yy, color=AZUL, label="ρ simple", zorder=3)
ax[0].scatter(v["spearman parcial (densidad)"], yy, color=NARANJA, label="ρ parcial (sin densidad)", zorder=3)
ax[0].set_yticks(yy, v.x.map(A.corto), fontsize=7)
ax[0].axvline(0, color=eda.EJE, lw=1)
ax[0].legend(loc="lower right")
ax[0].set_title("Índice NSE AltScore vs señales externas")
dec = pd.qcut(u_idx.indice_nse_altscore, 10, labels=False) + 1
for x, cc in [(x, cc) for x, cc in zip(["geoHexData_idx_costOfLiving_v1_adm2", "visits_percofmax", "geoHexData_building_res8_meanArea",
                                          "geoHexData_amenity_res8_count_bank"], [NARANJA, AZUL, VERDE, AMBAR]) if x in S.columns]:
    pr = u_idx[x].rank(pct=True) * 100
    g = pd.DataFrame({"d": dec, "p": pr}).dropna().groupby("d").p
    mu, se = g.mean(), g.std() / np.sqrt(g.size())
    ax[1].plot(mu.index, mu, "o-", color=cc, label=A.corto(x), ms=4)
    ax[1].fill_between(mu.index, mu - 1.96 * se, mu + 1.96 * se, color=cc, alpha=0.15)
ax[1].axhline(50, color=eda.MUTED, ls=":")
ax[1].set_xlabel("decil del índice NSE AltScore")
ax[1].set_ylabel("percentil medio de la señal (IC95)")
ax[1].set_xticks(range(1, 11))
ax[1].legend(fontsize=7)
ax[1].set_title("Perfil por decil del índice")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Cómo leer los IC:** el IC de Fisher y la p de permutación tratan cada contexto como independiente. El **IC por
# bootstrap de zonas digitales** remuestrea zonas completas y es el que manda: sale 2 a 3 veces más ancho.
#
# **Lectura:** el índice sube con los **restaurantes y comercio de alimentos** (sustenance), con las **visitas** (más aún
# al quitar la densidad) y con el **costo de vida**, aunque este se reduce a la mitad al controlar densidad: parte de
# esa relación es "zona más urbana". Bancos, ropa y área de edificios apenas se mueven con el índice: miden **oferta
# comercial e infraestructura**, otras dimensiones. Son complementos, no sustitutos. La validación decisiva, contra el
# NSE AMAI de INEGI, necesita ubicación y se hace en el 04.

# %% [markdown]
# ## 8. Reglas de selección de señales para el resto del flujo
# Se fijan **antes** de mirar la venta y no dependen de ella (el cruce con la venta es del 04, con sus propias pruebas):
#
# | Regla | Criterio | Si no se cumple |
# |---|---|---|
# | R1 información | no constante, no complemento de composición, no razón derivada, moda < 95% de los contextos | descartar |
# | R2 cobertura | ≥ 40% de las filas con dato (al promediar ~19 hexágonos en 300 m, casi toda área tendrá dato) | reserva (solo validación) |
# | R3 índice | los 4 proxies del índice entran **a través del índice**, no sueltos | — |
# | R4 redundancia | en cada grupo con \|ρ\| ≥ 0.7 queda la de mayor cobertura (y res 8 si la prueba de Meng no dice lo contrario) | descartar |
# | R5 estructura | carga varimax máxima ≥ 0.4 en alguna de las dimensiones retenidas por el análisis paralelo | reserva (sin estructura común) |
# | R6 parsimonia | una señal por dimensión, la de mayor carga; la dimensión donde cargan los proxies del índice entra **vía el índice** | reserva (la dimensión ya está representada) |

# %%
moda = u.apply(lambda s: s.value_counts(normalize=True).iloc[0] if s.notna().any() else 1.0)
delta_bloque = mcar.set_index("bloque")["delta de Cliff"]
res9_pref = set(meng.loc[meng.preferir == "res 9", "señal"])          # señales donde la prueba de Meng prefiere res 9
DIM_INDICE = dim_de[PROXIES].mode()[0]                          # dimensión donde cargan los proxies del índice
BASE_SEL = pd.DataFrame(index=list(S.columns))
BASE_SEL["familia"] = FAM
BASE_SEL["bloque"] = BASE_SEL.index.map(BLOQUE_DE)
BASE_SEL["cobertura %"] = S.notna().mean() * 100
BASE_SEL["cobertura % (contextos)"] = u.notna().mean() * 100
BASE_SEL["valores distintos (contextos)"] = u.nunique()
BASE_SEL["moda % (contextos)"] = moda * 100
BASE_SEL["δ MCAR del bloque"] = BASE_SEL.bloque.map(delta_bloque)
BASE_SEL["dimensión"] = dim_de
BASE_SEL["carga máx"] = carga_max
BASE_SEL = BASE_SEL.join(dep_idx.set_index("x")[["spearman", "MI"]].rename(columns={"spearman": "ρ con índice NSE", "MI": "MI con índice"}))


def resolucion_preferida(c):
    base = A.corto(c).replace("r8 ", "").replace("r9 ", "")
    return ("_res9" in c) == (base in res9_pref) if ("_res8" in c or "_res9" in c) else True


def seleccionar(cob_min=40, carga_min=0.4, corte_rho=0.7, cobertura="cobertura %"):
    """Aplica R1-R6 con los umbrales dados. Devuelve la tabla con grupo de redundancia, decisión y motivo."""
    sel = BASE_SEL.copy()
    sel["grupo redundancia"] = pd.Series(fcluster(enlace, 1 - corte_rho, "distance"), index=cand)
    tam = sel["grupo redundancia"].value_counts()

    def representante(g):
        miembros = sel.index[sel["grupo redundancia"] == g]
        return min(miembros, key=lambda c: (not resolucion_preferida(c), -sel.at[c, cobertura], -sel.at[c, "carga máx"]))

    decision, motivo = [], []
    for c, r in sel.iterrows():
        g = r["grupo redundancia"]
        if c in constantes:
            dcs, mot = "descartar", "R1: constante"
        elif c in A.COMPLEMENTOS:
            dcs, mot = "descartar", "R1: complemento de una composición (suma 1 o 100)"
        elif c in A.DERIVADAS:
            dcs, mot = "descartar", "R1: razón derivada de dos % que ya están"
        elif r["moda % (contextos)"] >= 95:
            dcs, mot = "descartar", f"R1: casi constante (moda {r['moda % (contextos)']:.0f}%)"
        elif c in PROXIES:
            dcs, mot = "índice NSE", "R3: entra al índice NSE AltScore"
        elif r[cobertura] < cob_min:
            dcs, mot = "reserva", f"R2: cobertura {r[cobertura]:.0f}% < {cob_min}% (solo validación)"
        elif tam.get(g, 1) > 1 and (rep := representante(g)) != c:
            dcs, mot = "descartar", f"R4: redundante con {A.corto(rep)} (|ρ| ≥ {corte_rho})"
        elif r["carga máx"] < carga_min:
            dcs, mot = "reserva", f"R5: sin estructura común (carga máx {r['carga máx']:.2f})"
        else:
            dcs, mot = "usar", f"{r['dimensión']}: {nombres_dim[r['dimensión']]}"
        decision.append(dcs)
        motivo.append(mot)
    sel["decisión"], sel["motivo"] = decision, motivo
    # R6 parsimonia: una representante por dimensión (la de mayor carga); la dimensión del índice entra vía el índice
    for dim, g in sel[sel.decisión == "usar"].groupby("dimensión"):
        rep_dim = g["carga máx"].idxmax()
        for c in g.index:
            if dim == DIM_INDICE:
                sel.loc[c, ["decisión", "motivo"]] = ["reserva", f"R6: su dimensión ({dim}) ya entra con el índice NSE AltScore"]
            elif c != rep_dim:
                sel.loc[c, ["decisión", "motivo"]] = ["reserva", f"R6: misma dimensión ({dim}) que {A.corto(rep_dim)}, que la representa"]
    return sel


sel = seleccionar()
SENALES_USAR = sel.index[sel.decisión == "usar"].tolist()
resumen_sel = sel.groupby(["decisión", "familia"]).size().unstack(fill_value=0)
display(resumen_sel)
cols_ver = ["familia", "cobertura %", "cobertura % (contextos)", "moda % (contextos)", "dimensión", "carga máx", "ρ con índice NSE", "decisión", "motivo"]
with pd.option_context("display.max_rows", 100, "display.max_colwidth", 70):
    display(sel.loc[SENALES_USAR, cols_ver].rename(index=A.corto).sort_values(["dimensión", "carga máx"], ascending=[True, False]).round(3))
print(f"Pasan al flujo: índice NSE AltScore ({len(PROXIES)} proxies: {NOMBRES_PROXIES}; dimensión {DIM_INDICE}) + {len(SENALES_USAR)} señales representantes; "
      f"con el índice cubren {sel.loc[SENALES_USAR, 'dimensión'].nunique() + 1} de las {K} dimensiones retenidas.")

fig, ax = plt.subplots(figsize=(9, 5))
colores = {"usar": VERDE, "índice NSE": AZUL, "reserva": AMBAR, "descartar": eda.MUTED}
for dcs, g in sel.groupby("decisión"):
    ax.scatter(g["cobertura %"], g["carga máx"].fillna(0), s=26, color=colores[dcs], label=f"{dcs} ({len(g)})", zorder=3)
ax.axvline(40, color=eda.MUTED, ls="--", lw=1)
ax.axhline(0.4, color=eda.MUTED, ls="--", lw=1)
for c in SENALES_USAR:
    ax.annotate(A.corto(c), (sel.at[c, "cobertura %"], sel.at[c, "carga máx"]), fontsize=5.5, xytext=(2, 2), textcoords="offset points")
ax.set_xlabel("cobertura (% filas)")
ax.set_ylabel("carga varimax máxima")
ax.legend(loc="lower left")
ax.set_title("Selección de señales: cobertura (R2) × estructura común (R5)")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** pasan al flujo el **índice NSE AltScore** y una señal representante por cada dimensión con estructura y
# cobertura suficientes. Las de res 9, el costo de vida, las que repiten una dimensión ya representada y los comercios
# poco frecuentes quedan en **reserva**: sirven para validar o para sustituir a una representante, no para modelar. En el 04 cada señal entra promediada en el área de 300 m, a las pruebas de asociación con
# la venta (Spearman por subcanal, BH, bootstrap de bloques espaciales), igual que las variables de INEGI.

# %% [markdown]
# ## 9. QA de las decisiones: validación cruzada del índice, sensibilidad de la selección y grano
# Un tomador de decisiones necesita saber si el resultado depende de umbrales elegidos a mano o de haber elegido y medido
# con los mismos datos. Tres pruebas:
# 1. **Índice fuera de muestra:** se parten los contextos digitales en dos mitades (100 veces); en la mitad A se eligen
#    los proxies (correlación ítem-resto > 0.2 entre los 7 a priori) y en la mitad B se mide el α. Si el α de B se
#    parece al reportado, no hay sesgo por elegir y medir en la misma muestra.
# 2. **Sensibilidad de la selección** a los umbrales de R2 (cobertura 30-50%, por filas o por contextos), R4 (|ρ| de
#    redundancia 0.6-0.8) y R5 (carga 0.35-0.5): 90 combinaciones. Cada señal recibe su **frecuencia de selección**.
# 3. **Grano:** qué parte de los PDV tiene un índice que viene de un vector digital compartido por muchas zonas (índice
#    "grueso": no distingue dentro de un área grande).

# %%
res_cv = []
b7 = base_items.dropna(subset=CAND)
for _ in range(100):
    msk = rng.random(len(b7)) < 0.5
    elegidas = A.seleccionar_proxies(b7[msk], CAND)[0]                     # la misma regla, solo con la mitad A
    res_cv.append({"reproduce los proxies": set(elegidas) == set(PROXIES), "α en la otra mitad": items(PROXIES, b7[~msk])[0]})
res_cv = pd.DataFrame(res_cv)
alfa_fuera = res_cv["α en la otra mitad"]
print(f"1) La selección en una mitad reproduce los {len(PROXIES)} proxies en {res_cv['reproduce los proxies'].mean():.0%} de las particiones; "
      f"α fuera de muestra: mediana {alfa_fuera.median():.2f} (IC95 {alfa_fuera.quantile(0.025):.2f}–{alfa_fuera.quantile(0.975):.2f}) "
      f"vs {alfa_4:.2f} en muestra.")

grid = []
for cob in (30, 35, 40, 45, 50):
    for base_cob in ("cobertura %", "cobertura % (contextos)"):
        for corte_rho in (0.6, 0.7, 0.8):
            for carga_min in (0.35, 0.4, 0.5):
                usa = set(seleccionar(cob, carga_min, corte_rho, base_cob).query("decisión == 'usar'").index)
                grid.append({"cobertura mín": cob, "base": base_cob, "|ρ| redundancia": corte_rho, "carga mín": carga_min,
                             "n señales": len(usa), "jaccard vs base": len(usa & set(SENALES_USAR)) / len(usa | set(SENALES_USAR)),
                             "señales": usa})
grid = pd.DataFrame(grid)
frecuencia = pd.Series([c for g in grid.señales for c in g]).value_counts() / len(grid) * 100
estab_sel = pd.DataFrame({"frecuencia de selección %": frecuencia}).rename_axis("señal")
estab_sel["en la selección base"] = estab_sel.index.isin(SENALES_USAR)
estab_sel["lectura"] = np.where(estab_sel["frecuencia de selección %"] >= 80, "estable",
                                np.where(estab_sel["frecuencia de selección %"] >= 50, "depende del umbral", "frágil"))
print(f"2) {len(grid)} combinaciones de umbrales: {grid['n señales'].min()}–{grid['n señales'].max()} señales (base {len(SENALES_USAR)}); "
      f"Jaccard mediano vs la selección base {grid['jaccard vs base'].median():.2f}.")
display(estab_sel.rename(index=A.corto).round(0).sort_values("frecuencia de selección %", ascending=False).head(25))
fragiles_base = estab_sel[estab_sel["en la selección base"] & (estab_sel["frecuencia de selección %"] < 80)]
print("   Señales de la selección base que dependen de los umbrales:",
      ", ".join(f"{A.corto(c)} ({v:.0f}%)" for c, v in fragiles_base["frecuencia de selección %"].items()) or "ninguna")

zxd_ctx = pd.Series(zonas_x_digital.reindex(ZONA["digital"]).to_numpy(), index=u.index)
filas_zona = S.merge(u.assign(_z=zxd_ctx), how="left")["_z"]
p90_grano = zonas_x_digital.quantile(0.9)
print(f"3) Índice 'grueso' (vector digital compartido por > {p90_grano:.0f} zonas de entorno, p90): "
      f"{(filas_zona > p90_grano).mean():.0%} de las filas; el vector más compartido cubre {zonas_x_digital.max():,} zonas.")

fig, ax = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={"width_ratios": [1, 1.4]})
ax[0].hist(alfa_fuera, bins=20, color=AZUL)
ax[0].axvline(alfa_4, color=NARANJA, lw=2, label=f"α en muestra {alfa_4:.2f}")
ax[0].axvline(0.7, color=eda.MUTED, ls=":", label="0.70 aceptable")
ax[0].legend(fontsize=7)
ax[0].set_title("α del índice fuera de muestra (100 particiones)")
top_f = estab_sel.sort_values("frecuencia de selección %", ascending=True).tail(22)
ax[1].barh([A.corto(c) for c in top_f.index], top_f["frecuencia de selección %"],
           color=[VERDE if b else eda.MUTED for b in top_f["en la selección base"]])
ax[1].axvline(80, color=eda.MUTED, ls="--", lw=1)
ax[1].tick_params(axis="y", labelsize=7)
ax[1].set_title("Frecuencia de selección en 90 combinaciones de umbrales (verde = selección base)")
plt.tight_layout()
plt.show()

# %% [markdown]
# **Lectura:** si el α fuera de muestra coincide con el de muestra, el índice no está sobreajustado. Las señales con
# frecuencia ≥ 80% son **decisiones robustas**: salen con casi cualquier umbral razonable. Las que dependen del umbral
# conviene tratarlas como **intercambiables** con sus sustitutas de la misma dimensión (hoja Selección, motivo R6). En el
# 04, el índice de un vector digital "grueso" no distingue dentro de su área: ahí pesa más la parte OSM.

# %% [markdown]
# ## 10. Salidas para el flujo y hallazgos

# %%
salida = d[["pos_id"] + [v for v in loc.values() if v]].assign(indice_nse_altscore=idx.round(2))
salida = pd.concat([salida, S[SENALES_USAR]], axis=1)
salida["zonas_por_vector_digital"] = filas_zona.to_numpy()          # grano del índice (el 04 lo informa, no entra a pruebas)
salida.to_parquet(C.PROC / f"altscore_{C.CLIENTE}_{C.SLUG}.parquet", index=False)
sel.rename_axis("señal").reset_index().assign(nombre=lambda t: t["señal"].map(A.corto)).to_csv(
    C.PROC / f"altscore_senales_{C.CLIENTE}_{C.SLUG}.csv", index=False, encoding="utf-8-sig")
if tiene_loc:
    print(f"Con ubicación ({loc}): el notebook 04 agrega el índice y las {len(SENALES_USAR)} señales al área de 300 m de cada PDV.")
else:
    print("SIN UBICACIÓN: el índice y las señales quedan por pos_id de AltScore, pero no se pueden unir a ningún PDV ni hexágono.\n"
          "  → Pedir a AltScore la misma exportación con lat, lon y hexIdx_res8 / hexIdx_res9 (vienen en su diccionario de datos). "
          "Al copiarla a enrichedgeodata/, el 04 la usa sin cambiar código.")

hallazgos00b = pd.DataFrame([
    ("Universo", f"La exportación trae {N_TOTAL:,} filas de la península; {len(d):,} caen en la {C.ZM_NOMBRE} por ubicación ("
                 + ", ".join(f"{k} {v:,}" for k, v in UNIVERSO.items()) + ").",
     "Solo la ZM entra al EDA y al flujo (misma regla que Rappi)."),
    ("Grano", f"{len(d):,} filas con pos_id único, pero solo {len(u):,} contextos distintos ({1 - len(u) / len(d):.0%} de filas repetidas); "
              f"el bloque digital tiene {grano.loc['digital', 'vectores distintos']:,} vectores.",
     "Las señales son de zona, no de PDV: estadística por contexto único y p con n efectivo."),
    ("Ubicación", "La exportación trae " + (", ".join(v for v in loc.values() if v) if tiene_loc else "solo pos_id (UUID v4) y las señales; sin lat/lon ni hexIdx"),
     "Se une por ubicación en el 04." if tiene_loc else "No se une a PDV (no se infiere el cruce): pedir la exportación con lat, lon y hexIdx."),
    ("Composiciones", f"{len(composiciones)} grupos de % suman 1 o 100 ({', '.join(composiciones)}).",
     "Se excluye un complemento por grupo; la correlación negativa entre partes es en parte artificial."),
    ("Faltantes", f"Por bloque completo y anidados por resolución: digital {M['digital (web por zona)'].mean():.0%}, edificios res 8 "
                  f"{M['building res 8'].mean():.0%}, comercios res 8 {M['shop res 8'].mean():.0%}, costo de vida {M['costo de vida (adm2)'].mean():.0%}.",
     "No MCAR en los bloques OSM (δ < 0: faltan más en zonas de índice bajo); no se imputan con la media."),
    ("Colas", f"{(uni.asimetria > 2).sum()} de {len(uni)} señales clave muy asimétricas; mejor ajuste lognormal.", "Rangos (Spearman) y no medias."),
    ("Correlaciones", f"{len(pares):,} pares; |ρ| ≥ 0.7 solo en {(pares.spearman.abs() >= 0.7).sum()} (res 8 ↔ res 9, bancos ↔ financieras, PC ↔ Windows). "
                      "Spearman, Pearson log1p y Kendall coinciden en signo; p de permutación = 0.001 (el mínimo con 1,000 permutaciones) en los pares fuertes.",
     "Poca redundancia: las familias digital y OSM miden cosas distintas."),
    ("Resolución", f"Meng res 8 vs res 9: {(meng.q_BH < 0.05).sum()} de {len(meng)} con diferencia significativa; res 8 con ~2× cobertura.",
     "Se usa res 8."),
    ("Estructura", f"KMO: " + ", ".join(f"{r.bloque} {r.KMO:.2f}" for r in kmo.itertuples()) + f"; Bartlett p < 0.001; análisis paralelo retiene {K} dimensiones.",
     "Las señales no se resumen en un factor: se elige una representante por dimensión."),
    ("Índice NSE AltScore", f"{len(PROXIES)} proxies en la ZM ({NOMBRES_PROXIES}), α = {alfa_4:.2f} (los {len(CAND)} a priori daban {alfa_7:.2f}; los 4 de la "
                            f"exportación anterior, {ALFA_PENINSULA:.2f} en la península); PC1 explica {var_pc1:.0%}; cobertura {idx.notna().mean():.0%} de las filas.",
     "Variable socioeconómica adicional al NSE AMAI; no ajustada a la venta."),
    ("Validez convergente", "; ".join(f"{A.corto(x)}: ρ = {r:+.2f} IC zona {ic} (parcial {rp:+.2f})" for x, r, ic, rp in
                                      zip(validez.x, validez.spearman, validez["IC95 bootstrap por zona"], validez["spearman parcial (densidad)"]) if abs(r) >= 0.05),
     "Solo cuentan las asociaciones cuyo IC por zona excluye 0. La validación decisiva, contra el NSE AMAI de INEGI, se hace en el 04 "
     "(ahora hay ubicación)."),
    ("QA: índice fuera de muestra", f"La elección de los {len(PROXIES)} proxies se repite en {res_cv['reproduce los proxies'].mean():.0%} de 100 particiones; "
                                    f"α fuera de muestra {alfa_fuera.median():.2f} ({alfa_fuera.quantile(0.025):.2f}–{alfa_fuera.quantile(0.975):.2f}).",
     "Sin sesgo por elegir y medir con los mismos datos."),
    ("QA: sensibilidad de la selección", f"En {len(grid)} combinaciones de umbrales: {grid['n señales'].min()}–{grid['n señales'].max()} señales; "
                                         f"Jaccard mediano vs base {grid['jaccard vs base'].median():.2f}. Dependen del umbral: "
                                         + (", ".join(A.corto(c) for c in fragiles_base.index) or "ninguna") + ".",
     "Las estables (≥ 80%) son decisión firme; las demás son intercambiables con su sustituta de la misma dimensión."),
    ("QA: riesgo de validez (turismo)", f"En la península viajes e idiomas no españoles se mueven con iOS y macOS (α {ALFA_PENINSULA:.2f}) porque marcan "
                                        "ciudades turísticas; dentro de la ZM no forman escala y el análisis de ítems los deja fuera"
                                        + (f"; los {int(mcar.loc[mcar.bloque == 'vías res 8', 'contextos sin bloque'].iloc[0]):,} contextos sin vías res 8 "
                                           f"tienen índice mediano {mcar.loc[mcar.bloque == 'vías res 8', 'mediana índice sin'].iloc[0]:.0f}."
                                           if (mcar.bloque == "vías res 8").any() else "."),
     "Validar contra INEGI con ubicación y marcar zonas turísticas (p. ej. hoteles DENUE 721) antes de usar el índice como NSE de residentes."),
    ("QA: grano del índice", f"Cada vector digital cubre en mediana {zonas_x_digital.median():.0f} zonas OSM (máx. {zonas_x_digital.max():,}); "
                             f"{(filas_zona > p90_grano).mean():.0%} de las filas con índice 'grueso'.",
     "En esas zonas el índice no distingue dentro del área: el 04 informa el grano por PDV."),
    ("Selección", f"Usar: índice NSE + {len(SENALES_USAR)} señales representantes ({', '.join(A.corto(c) for c in SENALES_USAR)}); "
                  f"reserva {int((sel.decisión == 'reserva').sum())}; descartadas {int((sel.decisión == 'descartar').sum())}.",
     "El 04 las usa en el área de 300 m de cada PDV cuando haya ubicación."),
], columns=["tema", "hallazgo", "implicación"])
with pd.option_context("display.max_colwidth", None):
    display(hallazgos00b)

# ---- entregable Excel con formato Kin ----
import excel_kin as X
wb = X.libro()
X.hoja_tabla(wb, "Hallazgos", hallazgos00b.rename(columns=str.capitalize), titulo="Hallazgos del EDA de AltScore", ajustar=True,
             anchos={"Tema": 22, "Hallazgo": 105, "Implicación": 60})
X.hoja_tabla(wb, "Selección", sel.rename_axis("señal").reset_index().assign(nombre=lambda t: t["señal"].map(A.corto)).round(3),
             titulo="Decisión por señal (reglas R1-R6)", nota="usar = pasa al notebook 04; índice NSE = entra vía el índice; reserva = solo validación.",
             anchos={"señal": 44, "motivo": 50, "nombre": 30})
X.hoja_tabla(wb, "Faltantes", faltantes.round(1).rename_axis("Bloque"), indice=True, titulo="Faltantes por bloque de señales",
             nota="Los faltantes son por bloque completo; res 9 está anidado en res 8.", anchos={"Bloque": 28})
X.hoja_tabla(wb, "MCAR", mcar.round(3), titulo="¿El faltante depende del tipo de zona? (índice NSE AltScore con y sin el bloque)",
             nota="δ de Cliff: |δ| < 0.147 despreciable. Unidad: contexto único.", anchos={"bloque": 26, "lectura": 44})
X.hoja_tabla(wb, "Univariado", uni.round(3).reset_index(), titulo="Univariado por señal (contextos únicos)", anchos={"variable": 44, "lectura": 40})
X.hoja_tabla(wb, "Correlaciones", pares.head(200).assign(x=lambda t: t.x.map(A.corto), y=lambda t: t.y.map(A.corto)).round(4),
             titulo="200 pares de señales con mayor |ρ| de Spearman", nota="p con n efectivo (pares distintos); q de Benjamini-Hochberg sobre todos los pares.",
             anchos={"x": 32, "y": 32})
X.hoja_tabla(wb, "Robustez corr.", rob_corr.round(3), titulo="Pares más fuertes: Spearman, Pearson log1p, Kendall y permutación", anchos={"x": 30, "y": 30})
X.hoja_tabla(wb, "Res 8 vs 9", meng.round(4), titulo="Prueba de Meng: correlación con el índice en res 8 vs res 9", anchos={"señal": 28})
X.hoja_tabla(wb, "Estructura", kmo.round(3), titulo="Factorabilidad por bloque (KMO y Bartlett)", anchos={"bloque": 16})
X.hoja_tabla(wb, "Cargas varimax", L.round(3).rename(index=A.corto).rename_axis("Señal").reset_index(),
             titulo=f"Cargas rotadas (varimax) de las {K} dimensiones retenidas por análisis paralelo", anchos={"Señal": 32})
X.hoja_tabla(wb, "Índice NSE", estab.round(3).rename(index=A.corto).rename_axis("Proxy").reset_index(),
             titulo="Índice NSE AltScore: cargas y α con IC95 (bootstrap B = 300)",
             nota=f"Índice = percentil del 1.er componente de {NOMBRES_PROXIES} (normalizados por rangos), elegidos por análisis de ítems en la ZM.",
             anchos={"Proxy": 30})
X.hoja_tabla(wb, "Ítems", analisis_items.round(2).rename(index=A.corto).rename_axis("Proxy").reset_index(), titulo=f"Análisis de ítems en la ZM: {len(CAND)} proxies a priori → {len(PROXIES)} finales",
             anchos={"Proxy": 34})
X.hoja_tabla(wb, "Validez", validez.assign(x=validez.x.map(A.corto)).round(4), titulo="Validez convergente: Spearman simple, parcial (sin densidad) y permutación",
             anchos={"x": 32, "y": 22})
X.hoja_tabla(wb, "QA sensibilidad", estab_sel.rename(index=A.corto).round(1).reset_index(),
             titulo="Frecuencia de selección de cada señal en 90 combinaciones de umbrales (R2, R4, R5)",
             nota="estable ≥ 80% · depende del umbral 50-80% · frágil < 50%.", anchos={"señal": 32, "lectura": 22})
X.hoja_tabla(wb, "QA umbrales", grid.drop(columns="señales").round(3), titulo="Tamaño de la selección y Jaccard vs la base por combinación de umbrales",
             anchos={"base": 24})
X.hoja_tabla(wb, "Datos del cliente", FUENTES_ALTSCORE, titulo="Archivos AltScore usados", anchos={"archivo": 60, "ruta": 90, "sha256": 66})
X.portada(wb, "EDA y selección de señales AltScore", f"{C.CLIENTE.title()} · {C.ZM_NOMBRE} · enrichedgeodata",
          [("Universo", f"{N_TOTAL:,} filas en la exportación (península); {len(d):,} en la {C.ZM_NOMBRE} por ubicación; "
                        f"{len(u):,} contextos únicos, {S.shape[1]} señales."),
           ("Ubicación", "Con ubicación: se une en el notebook 04." if tiene_loc else "Sin lat/lon ni hexIdx: no se une a PDV; pedir la exportación con ubicación."),
           ("Método", "retail-math-eda: integridad, faltantes (MCAR), colas, Spearman con n efectivo + BH, Kendall, permutación, Meng, "
                      "correlación parcial, KMO/Bartlett, análisis paralelo, varimax, α de Cronbach, MCD, bootstrap."),
           ("Selección", f"Índice NSE AltScore + {len(SENALES_USAR)} señales pasan al notebook 04 (reglas R1-R6, hoja Selección)."),
           ("Elaboró", "Kin Analytics · notebooks/_src/00b_altscore_eda.py")],
          [("Hallazgos", "Qué se encontró y qué implica."), ("Selección", "Decisión por señal."), ("Faltantes", "Faltantes por bloque."),
           ("MCAR", "Mecanismo del faltante."), ("Univariado", "Momentos, robustos y colas."), ("Correlaciones", "Pares de señales."),
           ("Robustez corr.", "Tres estimadores y permutación."), ("Res 8 vs 9", "Prueba de Meng."), ("Estructura", "KMO y Bartlett."),
           ("Cargas varimax", "Dimensiones retenidas."), ("Índice NSE", "Cargas y estabilidad."), ("Ítems", "Análisis de ítems."),
           ("Validez", "Validez convergente."), ("QA sensibilidad", "Estabilidad de cada señal ante los umbrales."),
           ("QA umbrales", "Selección por combinación de umbrales."), ("Datos del cliente", "Procedencia de los archivos.")])
out = C.OUT / f"00b_altscore_eda_{C.CLIENTE}_{C.SLUG}.xlsx"
wb.save(out)
print("Guardado:", out.name, "|", f"altscore_{C.CLIENTE}_{C.SLUG}.parquet", "|", f"altscore_senales_{C.CLIENTE}_{C.SLUG}.csv")
