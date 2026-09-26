# %% [markdown]
# # 00 · Validación y cruce: ventas Bepensa × Customer Potential (CP) — ZM Mérida
#
# **Objetivo:** dejar una tabla limpia, **una fila por punto de venta (PDV) con coordenadas**, con sus ventas y su
# potencial, y decidir con **evidencia estadística** (prueba, tamaño de efecto e intervalo de confianza) qué señales
# sirven y cuáles no. Esa tabla alimenta el notebook 04 (perfil NSE e indicadores en hexágonos a ≤ 300 m de cada PDV).
#
# **Alcance:** el CP y las ventas cubren toda la península. La llave se infiere con toda la base (más evidencia) y
# después **todo el análisis se hace solo con los PDV de la ZM Mérida** (cruce espacial con los polígonos municipales
# del Marco Geoestadístico 2025).
#
# **Fuentes (del cliente, en `data/raw/bepensa/`, no se suben a git):**
#
# | Archivo | Qué trae | Grano |
# |---|---|---|
# | `ventas/part-*.csv` | cajas vendidas por PDV y categoría, meses activos, primera y última venta | PDV × categoría (solo `sueros`) |
# | `cp/conservative_scenario.csv` | coordenadas, subcanal, tamaño, cluster y potencial (escenario conservador) | PDV |
#
# **Convenciones (método retail-math-eda):**
# * **Grano:** ventas = `pos_id` × `custom_category`; CP = `pos_id`. Se verifica que ambas llaves sean únicas.
# * **Ventana:** oct-2024 → ago-2026 (23 meses). Las ventas vienen agregadas por PDV: no hay transacciones, precios
#   ni canasta, así que market basket, RFM transaccional y elasticidad **no aplican**.
# * **Unidad:** cajas (sin importes). Sin devoluciones (se verifica que no haya negativos).
# * **Inferencia:** toda p se corrige por comparaciones múltiples con Benjamini-Hochberg (q). Con n ≈ 6,000 casi todo
#   es "significativo", así que se decide por **tamaño de efecto** (ρ, ε², δ de Cliff, V de Cramér) y su IC95.
#
# **Reproducir:** es el **primer** notebook: no depende de 01–03 (orden completo 00 → 01 → 02 → 03 → 04). Ábrelo desde
# `notebooks/` o corre `python src/correr.py --pasos 00 merida`. Necesita los datos del cliente en `data/raw/bepensa/`
# (el Marco Geoestadístico se descarga solo si falta) y los paquetes de `requirements.txt`.
# Todo lo aleatorio usa la semilla fija `eda.SEMILLA`.

# %%
# --- parámetros y entorno (lo único que se cambiaría a mano) ---
import os
import sys
import platform
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")       # Bepensa se analiza para la ZM Mérida; cambiar antes de importar config
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import scipy
import sklearn
from scipy import stats
from sklearn.model_selection import cross_val_score
from sklearn.tree import DecisionTreeClassifier
from IPython.display import display

import config as C
import eda
from descargas import descargar, extraer

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"Los datos de {C.CLIENTE} son de {C.CLIENTE_CIUDAD}; CIUDAD={C.CIUDAD}"
eda.estilo()
pd.set_option("display.width", 220, "display.max_columns", 40, "display.float_format", "{:,.3f}".format)
print(f"Repo: {BASE} | ciudad: {C.ZM_NOMBRE} | semilla: {eda.SEMILLA}")
print(f"Python {platform.python_version()} · pandas {pd.__version__} · numpy {np.__version__} · scipy {scipy.__version__} · "
      f"scikit-learn {sklearn.__version__} · geopandas {gpd.__version__}")

# --- requisitos: datos del cliente y polígonos municipales del Marco Geoestadístico ---
for f in [C.CLIENTE_CP, *C.CLIENTE_VENTAS]:
    assert Path(f).exists(), f"Falta el archivo del cliente: {f}"
assert C.CLIENTE_VENTAS, f"No hay archivos part-*.csv en {C.CLIENTE_RAW / 'ventas'}"
descargar(C.URLS["mg"], C.ARCHIVOS["mg"])       # no vuelve a bajar si el zip ya existe y abre bien
D_MG = extraer(C.ARCHIVOS["mg"], C.RAW / f"mg{C.MG_VERSION}_{C.ENT}")

# %% [markdown]
# ## 1. Carga e integridad

# %%
ventas = pd.concat([pd.read_csv(f) for f in C.CLIENTE_VENTAS], ignore_index=True)
cp = pd.read_csv(C.CLIENTE_CP)
print("Archivos:", [f.name for f in C.CLIENTE_VENTAS], "|", C.CLIENTE_CP.name)
print(f"Ventas: {ventas.shape} | CP: {cp.shape}")
print("Llave ventas (pos_id, custom_category) única:", not ventas.duplicated(["pos_id", "custom_category"]).any(),
      "| categorías:", ventas.custom_category.value_counts().to_dict())
print("Llave CP (pos_id) única:", cp.pos_id.is_unique)
print("Negativos en ventas:", int((ventas.select_dtypes("number") < 0).sum().sum()))
print("avg_monthly_boxes = total_boxes_sold / n_active_months:",
      bool(np.allclose(ventas.avg_monthly_boxes, (ventas.total_boxes_sold / ventas.n_active_months).round(2), atol=0.011)))
nulos = cp.isna().mean().mul(100).round(1)
display(nulos[nulos > 0].to_frame("% nulos CP"))
print("Columnas de potencial nulas en bloque (mismo patrón en las 10):",
      bool(cp.filter(like="Potential").drop(columns=cp.filter(like="PotentialRange").columns).isna().nunique(axis=1).eq(1).all()))

# %% [markdown]
# ## 2. Llave entre ventas y CP
#
# Los `pos_id` no coinciden directamente (ventas: 10 dígitos; CP: 1–480,475). Hipótesis H1:
# **`pos_id` de ventas = prefijo de 4 dígitos (centro de distribución) + `pos_id` del CP a 6 dígitos**.
#
# * **Prueba (a), empate vs azar.** Bajo H0 (sufijo sin relación con el CP) un sufijo de 6 dígitos cae en el CP con
#   probabilidad p₀ = (#pos_id del CP) / 10⁶. Prueba binomial unilateral del número de empates.
# * **Prueba (b), coherencia geográfica.** Si el prefijo es un centro de distribución, sus PDV se concentran en pocas
#   ciudades. Estadístico: pureza = proporción ponderada de la ciudad dominante por prefijo. Se compara con su
#   distribución bajo H0 permutando las ciudades (200 permutaciones, p = (#{T* ≥ T} + 1) / (B + 1)).

# %%
sid = ventas.pos_id.astype(str)
assert sid.str.len().eq(10).all()
ventas["prefijo"] = sid.str[:4]
ventas["pos_id_cp"] = sid.str[4:].astype(int)
ventas["en_cp"] = ventas.pos_id_cp.isin(cp.pos_id)

densidad = cp.pos_id.nunique() / 1_000_000
k, n = int(ventas.en_cp.sum()), len(ventas)
binom = stats.binomtest(k, n, densidad, alternative="greater")
ic = stats.binomtest(k, n).proportion_ci(0.95, method="wilson")      # IC bilateral (el de la prueba unilateral llega a 100%)
print(f"(a) Empate: {k:,}/{n:,} = {k / n:.1%} (IC95 Wilson {ic.low:.1%}–{ic.high:.1%}) vs p₀ = {densidad:.1%} | "
      f"binomial p = {binom.pvalue:.1e} | razón vs azar = {k / n / densidad:.0f}×")
print(f"    cajas cubiertas por el empate: {ventas.total_boxes_sold[ventas.en_cp].sum() / ventas.total_boxes_sold.sum():.1%}")

m = ventas[ventas.en_cp].merge(cp[["pos_id", "pos_city"]].rename(columns={"pos_id": "pos_id_cp"}), on="pos_id_cp")
def pureza(prefijo, ciudad):
    t = pd.crosstab(prefijo, ciudad)
    return float(t.max(axis=1).sum() / t.values.sum())
real = pureza(m.prefijo, m.pos_city)
rng = np.random.default_rng(eda.SEMILLA)
perm_dist = np.array([pureza(m.prefijo, rng.permutation(m.pos_city.values)) for _ in range(200)])
p_perm = (np.sum(perm_dist >= real) + 1) / (perm_dist.size + 1)
perm = perm_dist.mean()
print(f"(b) Pureza de ciudad por prefijo: real {real:.3f} vs permutada {perm:.3f} (máx. de 200: {perm_dist.max():.3f}) | "
      f"p de permutación = {p_perm:.4f} (el mínimo posible con 200)")
print(f"    V de Cramér prefijo × ciudad = {eda.cramer_v(pd.crosstab(m.prefijo, m.pos_city)):.2f}")

llave = (ventas.groupby("prefijo").agg(registros=("pos_id", "size"), empate=("en_cp", "mean"),
                                        cajas=("total_boxes_sold", "sum"))
         .join(m.groupby("prefijo").pos_city.agg(lambda x: x.value_counts().index[0]).rename("ciudad_principal"))
         .sort_values("registros", ascending=False))
display(llave.head(30))
print("Prefijos sin ningún empate:", llave.index[llave.empate == 0].tolist(),
      f"({llave.registros[llave.empate == 0].sum():,} registros)")
multi = ventas[ventas.en_cp].pos_id_cp.duplicated(keep=False)
print(f"PDV del CP atendidos por más de un prefijo: {ventas[ventas.en_cp & multi].pos_id_cp.nunique():,} (se suman al consolidar)")

# nulos del CP ⇔ PDV sin venta (MNAR): tabla 2×2 y V de Cramér
t_mnar = pd.crosstab(cp.PotentialQuantitative_TotalPortafolio.isna().rename("potencial nulo"),
                     cp.pos_id.isin(ventas.pos_id_cp[ventas.en_cp]).rename("con venta"))
display(t_mnar)
print(f"V de Cramér (potencial nulo × con venta) = {eda.cramer_v(t_mnar):.3f} → 1 = el CP solo tiene potencial para PDV que compran")

# %% [markdown]
# **Supuesto a confirmar con Bepensa:** la llave se infirió de los datos. Las dos pruebas rechazan H0 con mucho margen,
# pero una tabla oficial de equivalencias es mejor evidencia que cualquier prueba.

# %% [markdown]
# ## 3. Limpieza de coordenadas del CP
#
# Errores encontrados: lat/lon invertidas, punto decimal perdido (`21034767` → `21.034767`), signo de longitud perdido
# y basura (lat = −lon). Reglas, en orden: (1) escala: si |valor| > 1000 se divide hasta quedar con dos dígitos enteros;
# (2) si |lat| > 80 y |lon| < 30 se intercambian; (3) lat positiva, lon negativa; (4) caja de la península
# (17.5–22.0 N, 86.5–92.5 O). La consistencia con el municipio se revisa en 3b con el polígono municipal.

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
valida = lat.between(17.5, 22.0) & lon.between(-92.5, -86.5)
original_ok = cp.pos_latitude.between(17.5, 22.0) & cp.pos_longitude.between(-92.5, -86.5)
cp["lat"], cp["lon"] = lat.where(valida), lon.where(valida)
cp["coord_estado"] = np.select([original_ok & valida, valida], ["original", "corregida"], "descartada (fuera de la península)")
cp_total_estado = cp.coord_estado.copy()        # base completa, antes de filtrar a la ZM
display(cp.coord_estado.value_counts().to_frame("PDV"))
display(cp.loc[cp.coord_estado != "original", ["pos_id", "pos_city", "pos_latitude", "pos_longitude", "lat", "lon", "coord_estado"]].head(20))

# %% [markdown]
# ## 3b. Filtro a la ZM y sesgo de selección de las ventas que no se pueden ubicar

# %%
mun = gpd.read_file(next(D_MG.rglob(f"{C.ENT}mun.shp")))[["CVE_MUN", "NOMGEO", "geometry"]]
pts = gpd.GeoDataFrame(cp[["pos_id"]], geometry=gpd.points_from_xy(cp.lon, cp.lat), crs=4326).to_crs(mun.crs)
j = gpd.sjoin(pts[cp.lat.notna().values], mun, how="left", predicate="within")
cp["cve_mun"] = j.CVE_MUN.reindex(cp.index)
cp["municipio_mg"] = j.NOMGEO.reindex(cp.index)
cp["en_zm"] = cp.cve_mun.isin(C.ZM_MUNICIPIOS)
print(f"PDV del CP en {C.ZM_NOMBRE}: {cp.en_zm.sum():,} de {len(cp):,} (municipios: {C.ZM_MUNICIPIOS})")
display(pd.crosstab(cp.loc[cp.en_zm, "municipio_mg"], cp.loc[cp.en_zm, "pos_city"]))
dup = cp[cp.en_zm].duplicated(["lat", "lon"], keep=False)
print(f"PDV de la ZM con coordenadas idénticas a otro PDV: {dup.sum():,} (posibles dobles registros o geocodificación a nivel calle)")

zm_ids = set(cp.pos_id[cp.en_zm])
pref_zm = ventas[ventas.en_cp].assign(zm=lambda d: d.pos_id_cp.isin(zm_ids)).groupby("prefijo").zm.mean()
pref_zm = pref_zm[pref_zm >= 0.5].index.tolist()
vz = ventas[ventas.prefijo.isin(pref_zm)].copy()
vz["cajas_mes"] = vz.total_boxes_sold / vz.n_active_months
a, b = vz.loc[~vz.en_cp, "cajas_mes"], vz.loc[vz.en_cp, "cajas_mes"]
mw = stats.mannwhitneyu(a, b)
sesgo = pd.DataFrame({
    "grupo": ["sin empate (no ubicables)", "con empate (analizados)"],
    "registros": [len(a), len(b)],
    "% de las cajas": [vz.total_boxes_sold[~vz.en_cp].sum() / vz.total_boxes_sold.sum() * 100,
                       vz.total_boxes_sold[vz.en_cp].sum() / vz.total_boxes_sold.sum() * 100],
    "mediana cajas/mes activo": [eda.ic_bootstrap(a)[0], eda.ic_bootstrap(b)[0]],
    "IC95 mediana": [f"[{eda.ic_bootstrap(a)[1]:.2f}, {eda.ic_bootstrap(a)[2]:.2f}]", f"[{eda.ic_bootstrap(b)[1]:.2f}, {eda.ic_bootstrap(b)[2]:.2f}]"],
    "% prefijo 3xxx": [a.index.map(vz.prefijo).str.startswith("3").mean() * 100, b.index.map(vz.prefijo).str.startswith("3").mean() * 100],
})
display(sesgo)
d_sesgo = eda.cliff_delta(a, b)
cajas_sin = np.sort(vz.loc[~vz.en_cp, "total_boxes_sold"].to_numpy())[::-1]
top10_sin = cajas_sin[: max(1, cajas_sin.size // 10)].sum() / cajas_sin.sum()
print(f"El 10% más grande de los registros no ubicables concentra {top10_sin:.0%} de sus cajas")
print(f"Prefijos de la ZM: {pref_zm} | Mann-Whitney p = {mw.pvalue:.1e} | δ de Cliff (sin empate vs con empate) = {d_sesgo:+.2f}")
display(vz[~vz.en_cp].nlargest(10, "total_boxes_sold")[["pos_id", "prefijo", "total_boxes_sold", "n_active_months", "max_sale_date"]])

# %% [markdown]
# **Lectura:** δ de Cliff mide el PDV *típico* (|δ| < 0.147 = despreciable) y la cuota de cajas mide el *volumen*.
# Si δ es chico pero la cuota es grande, los no ubicables son PDV comunes más **unas pocas cuentas muy grandes**: el 04
# describe bien al PDV típico, pero el volumen total de la ZM queda subrepresentado.

# %% [markdown]
# ## 4. Métricas de venta por PDV (consolidadas al `pos_id` del CP)
#
# `avg_monthly_boxes` divide entre meses **activos**: premia a quien compró pocos meses y dejó de comprar. Se usa la
# intensidad sobre toda la vida del PDV en la ventana (`cajas_mes_vida` = cajas / meses desde su primera venta hasta el
# cierre) y el estado de actividad al cierre.

# %%
fin = pd.to_datetime(ventas.max_sale_date).max()
def meses(a, b):
    return (b.dt.year - a.dt.year) * 12 + (b.dt.month - a.dt.month)

v = ventas[ventas.en_cp & ventas.pos_id_cp.isin(zm_ids)].copy()
v["min_d"], v["max_d"] = pd.to_datetime(v.min_sale_date), pd.to_datetime(v.max_sale_date)
pdv = v.groupby("pos_id_cp").agg(
    prefijos=("prefijo", lambda x: ",".join(sorted(set(x)))), n_prefijos=("prefijo", "nunique"),
    cajas_total=("total_boxes_sold", "sum"), meses_activos=("n_active_months", "max"),
    primera_venta=("min_d", "min"), ultima_venta=("max_d", "max"))
cierre = pd.Series(fin, index=pdv.index)
pdv["meses_vida"] = meses(pdv.primera_venta, cierre) + 1
pdv["meses_span"] = meses(pdv.primera_venta, pdv.ultima_venta) + 1
pdv["cajas_mes_activo"] = pdv.cajas_total / pdv.meses_activos
pdv["cajas_mes_vida"] = pdv.cajas_total / pdv.meses_vida
pdv["tasa_actividad"] = (pdv.meses_activos / pdv.meses_vida).clip(upper=1)
pdv["recencia_meses"] = meses(pdv.ultima_venta, cierre)
pdv["estado_actividad"] = pd.cut(pdv.recencia_meses, [-1, 0, 2, 99], labels=["activo", "en riesgo (1-2 m)", "inactivo (3+ m)"])
pdv["alta_reciente"] = pdv.primera_venta > fin - pd.DateOffset(months=6)
pdv = pdv.join(cp.set_index("pos_id")[["pos_name", "pos_subchannel", "pos_size_classification"]])
print(f"Cierre de la ventana: {fin.date()} | PDV con venta, en CP y en {C.ZM_NOMBRE}: {len(pdv):,}")
display(pdv.estado_actividad.value_counts().to_frame("PDV"))

# %% [markdown]
# ### 4.1 Distribución univariada: momentos robustos, concentración y cola

# %%
metricas = ["cajas_total", "cajas_mes_vida", "cajas_mes_activo", "meses_activos", "tasa_actividad"]
uni = eda.univariado(pdv, metricas)
display(uni)

# %% [markdown]
# ### 4.2 ¿Qué distribución siguen las ventas? (máxima verosimilitud + AIC) y estabilidad del índice de cola
#
# El KS rechaza casi cualquier ajuste con n ≈ 6,000, así que se compara por AIC (ΔAIC > 10 = evidencia fuerte contra
# la familia) y se reporta la D de KS como distancia. El índice de Hill se lee en la meseta de la curva α(k), no en
# un k aislado: α > 2 implica varianza finita; 2 < α < 4, curtosis inestable (no confiar en la desviación estándar).

# %%
x_vida = pdv.cajas_mes_vida.to_numpy()
ajuste = eda.ajuste_distribuciones(x_vida)
display(ajuste)
lam = stats.boxcox(x_vida)[1]
print(f"Box-Cox λ (máx. verosimilitud) = {lam:.3f} → {'≈ log (λ ≈ 0): log1p es la transformación adecuada' if abs(lam) < 0.25 else 'usar Box-Cox'}")
curva_hill = eda.hill_curva(x_vida)
meseta = curva_hill[(curva_hill.index >= 50) & (curva_hill.index <= 400)]
print(f"Hill α para k = 50–400: mediana {meseta.median():.2f}, rango {meseta.min():.2f}–{meseta.max():.2f} | "
      f"para todo k: {curva_hill.min():.2f}–{curva_hill.max():.2f} (sin meseta limpia: la cola está en el límite α ≈ 2)")

fx, fy = eda.lorenz(x_vida)
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
ax[0].plot(fx, fy, color=eda.PALETA[0])
ax[0].plot([0, 1], [0, 1], color=eda.MUTED, lw=1, ls="--")
top20 = 1 - np.interp(0.8, fx, fy)
ax[0].plot([0.8], [np.interp(0.8, fx, fy)], "o", color=eda.PALETA[0], ms=8, mec=eda.FONDO, mew=2)
ax[0].text(0.78, np.interp(0.8, fx, fy) + 0.04, f"el 20% de PDV con más venta\nhace {top20:.0%} del volumen", ha="right", color=eda.TINTA_2)
ax[0].set(title=f"Curva de Lorenz de cajas/mes · Gini = {eda.gini(x_vida):.2f}", xlabel="fracción acumulada de PDV",
          ylabel="fracción acumulada de cajas")
ax[1].plot(curva_hill.index, curva_hill.values, color=eda.PALETA[1], marker="o", ms=3)
ax[1].axhline(2, color=eda.MUTED, lw=1, ls="--")
ax[1].text(curva_hill.index.min(), 1.85, "α = 2: debajo, varianza infinita", ha="left", color=eda.TINTA_2)
ax[1].set(title="Estimador de Hill α(k)", xlabel="k (mayores observaciones usadas)", ylabel="α", xscale="log")
plt.tight_layout(); plt.show()

# %% [markdown]
# ### 4.3 Atípicos de volumen (z robusto sobre log1p)
#
# Mahalanobis no sirve aquí: `meses_activos` y `tasa_actividad` están acotadas (1–23, 0–1) y son discretas, y la
# covarianza robusta sale degenerada (marca a la mitad de la base). Se usa el z modificado de Iglewicz-Hoaglin sobre
# `log1p(cajas_mes_vida)`, la escala donde la distribución es aproximadamente simétrica (Box-Cox λ ≈ 0): |z| > 3.5.

# %%
pdv["z_robusto"] = eda.z_robusto(np.log1p(pdv.cajas_mes_vida))
pdv["atipico_volumen"] = pdv.z_robusto.abs() > 3.5
top = pdv[pdv.atipico_volumen].sort_values("cajas_mes_vida", ascending=False)
print(f"Atípicos de volumen: {pdv.atipico_volumen.sum():,} ({pdv.atipico_volumen.mean():.1%})")
display(top[["pos_name", "pos_subchannel", "cajas_mes_vida", "meses_activos", "z_robusto"]].head(15))

# %% [markdown]
# **Lectura:** los atípicos son sucursales de cadenas de farmacias y PDV de alto tráfico, no errores: se **marcan** y se
# conservan. En el 04 se reporta la mediana por área además de la suma, porque uno de ellos domina la suma de su zona.

# %% [markdown]
# ### 4.4 Permanencia de los PDV (Kaplan-Meier)
#
# Evento = el PDV deja de comprar (recencia ≥ 3 meses al cierre). Duración = meses entre su primera y su última venta si
# ocurrió el evento; si sigue comprando (o lleva 1–2 meses sin comprar) la observación está **censurada** en su vida
# hasta el cierre. S(t) = probabilidad de seguir comprando t meses después de la primera venta. IC95 de Greenwood.

# %%
evento = pdv.recencia_meses >= 3
duracion = np.where(evento, pdv.meses_span, pdv.meses_vida)
km = eda.kaplan_meier(duracion, evento)
fig, ax = plt.subplots(figsize=(7.5, 3.8))
supervivencia = {}
for i, (sc, g) in enumerate(pdv.groupby("pos_subchannel")):
    e = g.recencia_meses >= 3
    k_ = eda.kaplan_meier(np.where(e, g.meses_span, g.meses_vida), e)
    supervivencia[sc] = k_.S
    ax.step(k_.index, k_.S, where="post", color=eda.PALETA[i], label=f"{sc.title()} (n={len(g):,})")
    ax.text(k_.index.max() + 0.3, k_.S.iloc[-1], sc.title(), color=eda.TINTA_2, va="center", fontsize=8)
ax.set(title="Probabilidad de seguir comprando por subcanal (Kaplan-Meier)", xlabel="meses desde la primera venta",
       ylabel="S(t)", ylim=(0, 1.02), xlim=(0, 27))
ax.legend(loc="lower left", fontsize=8)
plt.tight_layout(); plt.show()
hitos = km.S.reindex(range(1, 24)).ffill().loc[[6, 12, 18, 23]]
display(pd.DataFrame({"S(t) total": hitos, **{k: v.reindex(range(1, 24)).ffill().loc[[6, 12, 18, 23]] for k, v in supervivencia.items()}}).T.round(3))

# %% [markdown]
# ## 5. Señales del CP: ¿cuáles aportan información?
#
# Tres tipos de problema a descartar antes de usar una columna: **redundancia** (duplica otra), **fuga** (es una función
# de la propia venta) y **ruido** (no se asocia con nada).

# %%
pot = ["PotentialQuantitative", "PotentialEstimatedToCover", "PotentialQuantitativeFinal"]
red = pd.DataFrame([{"señal": p, "TotalPortafolio = sueros (%)": np.isclose(cp[f"{p}_TotalPortafolio"], cp[f"{p}_CustomCat_sueros"]).mean() * 100,
                     "spearman": stats.spearmanr(cp[f"{p}_TotalPortafolio"], cp[f"{p}_CustomCat_sueros"], nan_policy="omit")[0]} for p in pot])
display(red)
x = cp.set_index("pos_id")
print("Identidad PotentialQuantitativeFinal = Quantitative × EstimatedToCover:",
      bool(np.allclose(x.PotentialQuantitativeFinal_TotalPortafolio, x.PotentialQuantitative_TotalPortafolio * x.PotentialEstimatedToCover_TotalPortafolio, equal_nan=True)))
cruce = pdv.join(x.drop(columns=["pos_name", "pos_subchannel", "pos_size_classification"]), how="left")
rel = (cruce.PotentialQuantitative_TotalPortafolio / cruce.cajas_mes_activo - 1).abs()
print(f"PotentialQuantitative vs cajas_mes_activo: |diferencia relativa| mediana {rel.median():.4f}, p95 {rel.quantile(.95):.4f}; "
      f"idénticas (±0.01 cajas) en {np.isclose(cruce.PotentialQuantitative_TotalPortafolio, cruce.cajas_mes_activo, atol=0.011).mean():.1%}")
print("Comparative_Client_ID apunta a otro PDV del CP:", f"{cruce.Comparative_Client_ID_TotalPortafolio.isin(cp.pos_id).mean():.1%}",
      f"| es el mismo PDV: {(cruce.Comparative_Client_ID_TotalPortafolio == cruce.index).mean():.1%}")
cp = cp[cp.en_zm].copy()                        # desde aquí, universo = CP de la ZM

# %% [markdown]
# ### 5.1 Prueba de fuga: ¿se puede reconstruir la columna solo con la venta?
#
# Un árbol de decisión con **una sola variable** (cajas/mes activo) predice cada columna categórica; exactitud por
# validación cruzada de 5 pliegues. Exactitud ≈ 100% = la columna es una función de la venta (fuga). Referencia: la
# exactitud de adivinar siempre la clase más frecuente.

# %%
fuga = []
for c in ["size_class", "pos_size_classification", "PotentialQualitative_TotalPortafolio", "pos_subchannel", "cluster"]:
    d = cruce[[c, "cajas_mes_activo"]].dropna()
    acc = cross_val_score(DecisionTreeClassifier(max_depth=4, random_state=eda.SEMILLA), d[["cajas_mes_activo"]], d[c].astype(str), cv=5)
    fuga.append({"columna": c, "clases": d[c].nunique(), "exactitud_CV": acc.mean(), "±": acc.std(),
                 "línea base (clase mayoritaria)": d[c].astype(str).value_counts(normalize=True).iloc[0]})
fuga = pd.DataFrame(fuga)
fuga["veredicto"] = np.where(fuga.exactitud_CV > 0.95, "FUGA: función de la venta",
                    np.where(fuga.exactitud_CV - fuga["línea base (clase mayoritaria)"] > 0.1, "asociada a la venta", "poco asociada"))
display(fuga)
display(cruce.groupby("size_class").cajas_mes_activo.agg(["count", "min", "max"]).sort_values("min"))

# %% [markdown]
# ### 5.2 Dependencia con la venta: Spearman con IC95, Pearson sobre log1p e información mutua (q de BH)

# %%
num = ["PotentialQuantitative_TotalPortafolio", "PotentialEstimatedToCover_TotalPortafolio",
       "PotentialQuantitativeFinal_TotalPortafolio", "area", "cluster"]
dep = eda.dependencias(cruce, num, ["cajas_mes_vida", "cajas_mes_activo", "tasa_actividad"])
display(dep)

# %% [markdown]
# ### 5.3 ¿La asociación se sostiene dentro de cada subcanal? (control de la paradoja de Simpson)
#
# Si una señal solo "funciona" en el agregado porque los subcanales tienen niveles distintos de venta y de potencial,
# no sirve para comparar PDV. Se repite el Spearman dentro de cada subcanal con IC95.

# %%
estr = []
for sc, g in cruce.groupby("pos_subchannel"):
    for s in ["PotentialQuantitativeFinal_TotalPortafolio", "PotentialEstimatedToCover_TotalPortafolio", "area"]:
        d = g[[s, "cajas_mes_vida"]].dropna()
        r, p = stats.spearmanr(d[s], d.cajas_mes_vida)
        lo, hi = eda.spearman_ic(r, len(d))
        estr.append({"subcanal": sc, "señal": s, "n": len(d), "spearman": r, "IC95": f"[{lo:+.2f}, {hi:+.2f}]", "p": p})
estr = pd.DataFrame(estr)
estr["q_BH"] = stats.false_discovery_control(estr.p, method="bh")
display(estr.pivot_table(index="señal", columns="subcanal", values="spearman").round(2))
display(estr)

# %% [markdown]
# ### 5.4 Variables categóricas: Kruskal-Wallis con ε² (IC95 bootstrap) y comparaciones por pares (δ de Cliff)

# %%
cats = ["pos_subchannel", "size_class", "pos_size_classification", "cluster", "PotentialQualitative_TotalPortafolio"]
cat = eda.efecto_categorico(cruce, cats, "cajas_mes_vida")
display(cat)
pares = eda.comparaciones_pares(cruce, "pos_subchannel", "cajas_mes_vida")
display(pares)

orden = cruce.groupby("pos_subchannel").cajas_mes_vida.median().sort_values().index
fig, ax = plt.subplots(figsize=(8, 3.6))
datos = [np.log10(cruce.loc[cruce.pos_subchannel == s, "cajas_mes_vida"]) for s in orden]
bp = ax.boxplot(datos, orientation="horizontal", widths=0.5, patch_artist=True, showfliers=False,
                medianprops=dict(color=eda.TINTA, lw=2), whiskerprops=dict(color=eda.MUTED), capprops=dict(color=eda.MUTED))
for patch in bp["boxes"]:
    patch.set(facecolor=eda.PALETA[0], alpha=0.35, edgecolor=eda.PALETA[0])
ax.set_yticks(range(1, len(orden) + 1), [f"{s.title()} · mediana {10 ** np.median(d):.1f}" for s, d in zip(orden, datos)])
ticks = [0.1, 0.3, 1, 3, 10, 30, 100]
ax.set_xticks(np.log10(ticks), [str(t) for t in ticks])
ax.set(title=f"Cajas/mes por subcanal (escala log) · ε² = {cat.set_index('variable').loc['pos_subchannel', 'epsilon2']:.2f}",
       xlabel="cajas por mes de vida del PDV")
ax.grid(axis="x", color=eda.GRID); ax.grid(axis="y", visible=False)
plt.tight_layout(); plt.show()

# %% [markdown]
# ## 6. Veredicto: qué señales sirven
#
# Tabla de decisión con la estadística que la respalda (se usa en el notebook 04).

# %%
def rho(xc, yc="cajas_mes_vida"):
    r = dep[(dep.x == xc) & (dep.y == yc)]
    return f"ρ={r.spearman.iloc[0]:+.2f} {r.IC95.iloc[0]}" if len(r) else "—"
def eps(c):
    r = cat[cat.variable == c]
    return f"ε²={r.epsilon2.iloc[0]:.3f} {r.IC95.iloc[0]}" if len(r) else "—"
def acc(c):
    r = fuga[fuga.columna == c]
    return f"exactitud con solo la venta {r.exactitud_CV.iloc[0]:.1%}" if len(r) else "—"
def rng_estr(s):
    g = estr[estr.señal == s]
    si, no = g[g.q_BH < 0.05], g[g.q_BH >= 0.05]
    txt = "significativo en " + ", ".join(f"{r.subcanal.title()} {r.spearman:+.2f}" for r in si.itertuples()) if len(si) else "no significativo en ningún subcanal"
    return txt + ("; nulo en " + ", ".join(r.subcanal.title() for r in no.itertuples()) if len(no) else "")

senales = pd.DataFrame([
    ("cajas_mes_vida (ventas)", "USAR · variable objetivo", f"intensidad sobre la vida del PDV; Box-Cox λ = {lam:.2f} → analizar en log1p"),
    ("estado_actividad / recencia", "USAR", f"{(pdv.recencia_meses > 0).mean():.0%} no compró en el último mes; S(12 m) = {hitos.loc[12]:.2f}"),
    ("tasa_actividad", "USAR", "regularidad de compra (meses activos / meses de vida)"),
    ("cajas_mes_activo (= avg_monthly_boxes)", "USAR CON CUIDADO", "sesgado al alza en PDV intermitentes o inactivos"),
    ("PotentialQuantitative_*", "NO USAR · fuga", f"es la venta mensual actual: |dif. relativa| mediana {rel.median():.4f}"),
    ("PotentialQuantitativeFinal_*", "USAR · potencial incremental", f"Quantitative × EstimatedToCover; {rho('PotentialQuantitativeFinal_TotalPortafolio')}; dentro de subcanal {rng_estr('PotentialQuantitativeFinal_TotalPortafolio')}"),
    ("PotentialEstimatedToCover_*", "USAR", f"brecha vs PDV comparable; {rho('PotentialEstimatedToCover_TotalPortafolio')}"),
    ("PotentialRange / PotentialQualitative", "REDUNDANTE · fuga parcial", f"discretización del potencial; {acc('PotentialQualitative_TotalPortafolio')}"),
    ("columnas *_CustomCat_sueros", "REDUNDANTE", "≈ *_TotalPortafolio (ρ ≈ 1): la venta solo trae la categoría sueros"),
    ("Comparative_Client_ID_*", "SOLO TRAZABILIDAD", "PDV de referencia usado para el potencial; no es predictor"),
    ("pos_subchannel", "USAR · segmentar", f"{eps('pos_subchannel')}; comparar PDV dentro de su subcanal"),
    ("size_class", "NO USAR · fuga", f"{eps('size_class')}; {acc('size_class')}: son cortes de la propia venta"),
    ("pos_size_classification", "USAR", f"{eps('pos_size_classification')}; {acc('pos_size_classification')}; existe para todo el CP"),
    ("cluster", "RUIDO", f"{eps('cluster')}; {rho('cluster')}; sin diccionario"),
    ("area", "SEÑAL DÉBIL", f"{rho('area')}; dentro de subcanal {rng_estr('area')}; unidad desconocida (máx {cp.area.max():,.0f})"),
    ("lat / lon", "USAR (limpias)", f"{(cp.coord_estado == 'corregida').sum()} corregidas en la ZM; municipio asignado por polígono"),
], columns=["señal", "veredicto", "evidencia"])
with pd.option_context("display.max_colwidth", None):
    display(senales)

# %% [markdown]
# ## 7. Hallazgos
#
# Resumen de todo lo encontrado, con el número que lo respalda (se recalcula en cada corrida) y qué implica para el 04.

# %%
act = pdv.estado_actividad.value_counts(normalize=True)
sub = cruce.groupby("pos_subchannel").cajas_mes_vida.median().sort_values()
n_cp_zm, n_venta_zm = len(cp), int(cp.pos_id.isin(pdv.index).sum())
mejor = ajuste.iloc[0]
par_top = pares.iloc[0]
hallazgos = pd.DataFrame([
    ("Llave", f"ID de ventas = prefijo de 4 dígitos (centro de distribución) + pos_id del CP. Empata {k / n:.1%} (IC95 {ic.low:.1%}–{ic.high:.1%}) "
              f"vs {densidad:.1%} por azar (binomial p = {binom.pvalue:.0e}); pureza geográfica {real:.2f} vs {perm:.2f} permutada (p = {p_perm:.3f}).",
     "Inferida de los datos: confirmar con Bepensa."),
    ("Cobertura ZM", f"{n_cp_zm:,} PDV del CP en {C.ZM_NOMBRE}; {n_venta_zm:,} con venta ({n_venta_zm / n_cp_zm:.0%}) y "
                     f"{n_cp_zm - n_venta_zm:,} sin venta (prospectos, sin potencial calculado: V de Cramér = {eda.cramer_v(t_mnar):.2f}).",
     "Los PDV sin venta sirven para medir penetración en el área."),
    ("Ventas sin ubicar (sesgo)", f"En los prefijos de la ZM {len(a):,} registros no empatan y concentran {sesgo['% de las cajas'].iloc[0]:.1f}% de las cajas. "
                                  f"El registro típico casi no difiere del analizado (δ de Cliff = {d_sesgo:+.2f}; mediana {sesgo['mediana cajas/mes activo'].iloc[0]:.1f} vs "
                                  f"{sesgo['mediana cajas/mes activo'].iloc[1]:.1f} cajas/mes), pero el 10% más grande de ellos hace {top10_sin:.0%} de sus cajas: "
                                  f"son pocas cuentas muy grandes ({sesgo['% prefijo 3xxx'].iloc[0]:.0f}% con prefijo 3xxx).",
     "El 04 describe bien al PDV típico, pero no el volumen total: pedir a Bepensa la tabla de equivalencias o coordenadas de esas cuentas."),
    ("PotentialQuantitative = venta actual", f"|dif. relativa| con cajas_mes_activo: mediana {rel.median():.4f}; idénticas en "
                                             f"{np.isclose(cruce.PotentialQuantitative_TotalPortafolio, cruce.cajas_mes_activo, atol=0.011).mean():.1%}.",
     "Fuga: no usar como potencial ni como predictor."),
    ("Potencial incremental", f"PotentialQuantitativeFinal = Quantitative × EstimatedToCover; {rho('PotentialQuantitativeFinal_TotalPortafolio')} con la venta y "
                              f"dentro de subcanal: {rng_estr('PotentialQuantitativeFinal_TotalPortafolio')}.",
     "Aporta información distinta a la venta; usarlo por subcanal (no es comparable entre subcanales)."),
    ("size_class", f"{acc('size_class')} (línea base {fuga.set_index('columna').loc['size_class', 'línea base (clase mayoritaria)']:.0%}); {eps('size_class')}.",
     "Fuga: son cortes de la propia venta. No usar."),
    ("Tamaño del PDV", f"pos_size_classification {eps('pos_size_classification')}; {acc('pos_size_classification')}; existe para todo el CP.", "Usar para segmentar."),
    ("Subcanal", f"{eps('pos_subchannel')}. Mediana de cajas/mes: " + " · ".join(f"{k_.title()} {v_:.1f}" for k_, v_ in sub.items()) +
                 f". Mayor diferencia: {par_top.A.title()} vs {par_top.B.title()} (δ = {par_top.cliff_delta:+.2f}, {par_top.efecto}).",
     "Comparar PDV siempre dentro de su subcanal."),
    ("Actividad", f"Al cierre ({fin:%b-%Y}): activos {act.get('activo', 0):.0%} · en riesgo {act.get('en riesgo (1-2 m)', 0):.0%} · "
                  f"inactivos {act.get('inactivo (3+ m)', 0):.0%}. Kaplan-Meier: S(6 m) = {hitos.loc[6]:.2f}, S(12 m) = {hitos.loc[12]:.2f}, S(23 m) = {hitos.loc[23]:.2f}.",
     "avg_monthly_boxes sobreestima a los inactivos: usar cajas_mes_vida."),
    ("Distribución", f"Mejor ajuste por AIC: {mejor.familia} (siguiente a ΔAIC = {ajuste.ΔAIC.iloc[1]:.0f}); Box-Cox λ = {lam:.2f} (≈ log). "
                     f"Hill α ≈ {meseta.median():.2f} (entre {curva_hill.min():.2f} y {curva_hill.max():.2f} según k): cola en el límite de varianza infinita.",
     "Trabajar en log1p; reportar medianas con IC, no medias ± sd."),
    ("Concentración", f"Gini = {uni.loc['cajas_mes_vida', 'gini']:.2f}; el 20% de PDV con más venta hace {uni.loc['cajas_mes_vida', 'cuota_top20%']:.0f}% del volumen; "
                      f"mediana {uni.loc['cajas_mes_vida', 'mediana']:.2f} cajas/mes (IC95 {uni.loc['cajas_mes_vida', 'mediana_IC95']}).",
     "Por área, reportar suma y mediana."),
    ("Atípicos", f"{int(pdv.atipico_volumen.sum())} PDV con |z robusto| > 3.5 (sucursales de cadenas de farmacias): reales, se conservan marcados.",
     "Pueden dominar la venta de su área."),
    ("Coordenadas", f"Base completa: {(cp_total_estado == 'corregida').sum()} corregidas y {(cp_total_estado != 'original').sum() - (cp_total_estado == 'corregida').sum()} descartadas. "
                    f"En la ZM, {int((cp.municipio_mg.str.upper() != cp.pos_city.str.upper().str.replace('MERIDA', 'MÉRIDA')).sum()):,} PDV tienen pos_city distinto al municipio real "
                    f"y {int(dup.sum()):,} comparten coordenadas exactas con otro PDV.",
     "Usar el municipio del polígono, no pos_city."),
    ("Ruido", f"cluster {eps('cluster')}; area {rho('area')}.", "No usar sin su diccionario."),
], columns=["tema", "hallazgo", "implicación"])
with pd.option_context("display.max_colwidth", None):
    display(hallazgos)

# %% [markdown]
# ## 8. Guardar

# %%
salida = (cp.set_index("pos_id")
          .drop(columns=[c for c in cp.columns if c.endswith("_CustomCat_sueros")] + ["pos_latitude", "pos_longitude"])
          .join(pdv.drop(columns=["pos_name", "pos_subchannel", "pos_size_classification"]), how="left"))
salida["con_venta"] = salida.cajas_total.notna()
salida.index.name = "pos_id_cp"
salida.reset_index().to_parquet(C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet", index=False)
vz[~vz.en_cp].to_parquet(C.PROC / f"ventas_sin_cp_{C.CLIENTE}_{C.SLUG}.parquet", index=False)

out = C.OUT / f"00_validacion_ventas_cp_{C.CLIENTE}_{C.SLUG}.xlsx"
with pd.ExcelWriter(out) as xw:
    hallazgos.to_excel(xw, sheet_name="Hallazgos", index=False)
    senales.to_excel(xw, sheet_name="Señales", index=False)
    llave.to_excel(xw, sheet_name="Llave por prefijo")
    sesgo.to_excel(xw, sheet_name="Sesgo ventas sin ubicar", index=False)
    cp.coord_estado.value_counts().to_frame("PDV").to_excel(xw, sheet_name="Coordenadas")
    uni.to_excel(xw, sheet_name="Univariado")
    ajuste.to_excel(xw, sheet_name="Ajuste distribuciones", index=False)
    km.to_excel(xw, sheet_name="Kaplan-Meier")
    fuga.to_excel(xw, sheet_name="Prueba de fuga", index=False)
    dep.to_excel(xw, sheet_name="Dependencias", index=False)
    estr.to_excel(xw, sheet_name="Por subcanal", index=False)
    cat.to_excel(xw, sheet_name="Categoricas", index=False)
    pares.to_excel(xw, sheet_name="Pares subcanal", index=False)
    top.to_excel(xw, sheet_name="Atipicos")
    vz[~vz.en_cp].sort_values("total_boxes_sold", ascending=False).to_excel(xw, sheet_name="Ventas sin ubicar", index=False)
print(f"Guardado: {C.PROC / f'pdv_{C.CLIENTE}_{C.SLUG}.parquet'} ({len(salida):,} PDV, {salida.con_venta.sum():,} con venta, "
      f"{salida.lat.notna().sum():,} con coordenadas) | {out}")
