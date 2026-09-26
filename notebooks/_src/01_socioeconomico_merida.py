# %% [markdown]
# # 01 · Perfil socioeconómico de hogares por AGEB (ciudad según `src/config.py`)
#
# **Salida:** una fila por AGEB urbana con Latitud/Longitud y, para cada categoría, `HHs`, `%` e `Indice`:
#
# | Grupo | Categorías |
# |---|---|
# | Tamaño del hogar | 2 o menos, 3, 4, 5, 6+ personas |
# | Niños (edad del **menor** de 18 en el hogar) | < 6, 6–11, 12–17, sin niños |
# | Edad del jefe(a) de hogar | < 35, 35–44, 45–54, 55–64, 65+ |
# | NSE (Regla **AMAI 2024**, vigente; mismos puntos y cortes que la 2022) | A/B, C+, C, C-, D+, D/E |
#
# **Fuentes oficiales** (todas las URLs viven en `src/config.py` → `FUENTES`; la celda 1 las muestra y
# las verifica con HEAD al correr). Verificadas el 2026-09-24:
#
# | # | Fuente | Edición | Página oficial | Uso |
# |---|---|---|---|---|
# | 1 | INEGI · Censo 2020, Principales resultados por AGEB y manzana urbana | 2020 | https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos | Totales por AGEB (restricciones) y hogares por manzana |
# | 2 | INEGI · Censo 2020, Microdatos del cuestionario ampliado | 2020 | https://www.inegi.org.mx/programas/ccpv/2020/#microdatos | Hogares donantes |
# | 3 | INEGI · Marco Geoestadístico | 2025 (UPC 794551163061) | https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551163061 | Polígonos de AGEB, manzana y localidad |
# | 4 | INEGI · ENIGH 2024, nueva serie (la más reciente) | 2024 | https://www.inegi.org.mx/programas/enigh/nc/2024/#datos_abiertos | Imputar *número* de baños completos y autos |
# | 5 | AMAI · Regla NSE 2024 | vigente desde ene-2024 | https://www.amai.org/NSE/index.php?queVeo=NSE2024 | Puntos y cortes del NSE (`src/nse.py`) |
#
# URL de descarga por estado (`{ENT}` = clave INEGI, `{abrev}` y `{slug}` en `config.py`):
# 1. `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip`
# 2. `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_{abrev}_csv.zip`
# 3. `https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551163061/{ENT}_{slug}.zip`
# 4. `https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/datosabiertos/conjunto_de_datos_enigh2024_ns_csv.zip`
# 5. Nota metodológica: `https://www.amai.org/descargas/NOTA_METODOLOGICA_NSE_AMAI_2024_v6.pdf`
#
# **Por qué Censo 2020 y no la Encuesta Intercensal 2025:** la EIC 2025 (publicada el 2026-09-22) es una muestra
# representativa por estado, municipio y localidades de 50 mil+ habitantes; **no publica resultados por AGEB ni
# manzana**, así que el Censo 2020 sigue siendo la fuente más reciente a ese nivel.
#
# **Marco Geoestadístico 2025 con datos del Censo 2020:** las claves de AGEB coinciden igual que con el MG 2020;
# unas pocas manzanas del Censo ya no existen en el MG 2025 (se reporta cuántas en la sección 8).
#
# **Por qué hace falta modelar:** el Censo por AGEB no publica tamaño de hogar, edad del jefe ni NSE.
# Esas variables sí existen en la muestra censal, pero solo con desagregación municipal / localidad.
# Se usa **microsimulación espacial (IPU)**: para cada AGEB se reponderan los hogares de la muestra
# hasta reproducir exactamente lo que el Censo publica para esa AGEB (hogares, autos, internet,
# computadora, dormitorios, personas por edad, ocupados, escolaridad…). Con esos pesos se estiman las
# distribuciones anteriores.
#
# **Indice** = % de la AGEB / % de la referencia × 100 (referencia configurable en `src/config.py`:
# total de la ZM o total del estado).

# %%
import sys, zipfile
from pathlib import Path

BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())   # raíz del repo
sys.path.insert(0, str(BASE / "src"))
import numpy as np
import pandas as pd
import geopandas as gpd

import config as C
import nse
from descargas import descargar, extraer, registrar_fuentes, verificar_fuentes
from IPython.display import display
from microsim import ipu

pd.set_option("display.width", 200, "display.max_columns", 40)


# reproducibilidad: ciudad, versiones y semilla (no hay pasos aleatorios en este notebook)
import platform
print(f"Repo: {BASE} | ciudad: {C.ZM_NOMBRE} (CIUDAD={C.CIUDAD}) | Python {platform.python_version()} · pandas {pd.__version__} · numpy {np.__version__}")

# %% [markdown]
# ## 1. Fuentes: de dónde se descarga cada archivo (verificación en vivo) y descarga
# Descarga con reanudación: los servidores de INEGI suelen cortar la conexión.

# %%
print("Regla NSE:", C.REGLA_NSE["nombre"], "|", C.REGLA_NSE["pagina"])
print(f"Ciudad: {C.ZM_NOMBRE} · {C.NOM_ENT} ({C.ENT}) · municipios: " + ", ".join(f"{v} ({k})" for k, v in C.ZM_MUNICIPIOS.items()))
display(verificar_fuentes(C.FUENTES, ["ageb", "micro", "mg", "enigh"]))

# %%
for k in ["ageb", "micro", "mg", "enigh"]:
    print(f"{k}: {C.URLS[k]}")
    descargar(C.URLS[k], C.ARCHIVOS[k])



D_AGEB = extraer(C.ARCHIVOS["ageb"], C.RAW / f"ageb_{C.ENT}")
D_MICRO = extraer(C.ARCHIVOS["micro"], C.RAW / f"micro_{C.ENT}")
D_MG = extraer(C.ARCHIVOS["mg"], C.RAW / f"mg{C.MG_VERSION}_{C.ENT}")
D_ENIGH = extraer(C.ARCHIVOS["enigh"], C.RAW / "enigh2024")

# registro de las versiones exactas usadas (para depurar / reproducir): data/processed/<ciudad>/fuentes_usadas_01.csv
registrar_fuentes(C.FUENTES, ["ageb", "micro", "mg", "enigh"], C.PROC / "fuentes_usadas_01.csv")[["fuente", "edicion", "archivo_local", "bytes", "descargado"]]

# %% [markdown]
# ## 2. Imputación de baños completos y autos con ENIGH 2024
#
# El Censo pregunta **si** hay auto y **si** hay regadera + excusado, pero no cuántos. La regla AMAI
# da distintos puntos para 1 vs 2+. Se entrena un logit ponderado en hogares urbanos de la península
# (`C.ENIGH_ESTADOS`: el estado y sus vecinos) con variables que existen en ambas fuentes.
#
# **Validación:** en la propia ENIGH se compara el NSE con conteos reales vs el NSE obtenido tras
# "censalizar" la información (convertir a sí/no e imputar).

# %%
enigh = nse.cargar_enigh(D_ENIGH, C.ENIGH_ESTADOS)
modelos = nse.entrenar_modelos(enigh)

real = nse.nse_real_enigh(enigh)
censal = enigh.assign(banos1=(enigh.n_banos >= 1).astype(int), auto1=(enigh.n_autos >= 1).astype(int),
                      ocup_model=enigh.ocup)
prob_val = nse.distribucion_nse(censal, modelos)

yuc = enigh.ent == C.ENT
val = pd.DataFrame({
    f"ENIGH real ({C.NOM_ENT} urbano)": pd.Series(enigh.factor[yuc].values, index=real[yuc]).groupby(level=0).sum(),
    f"Imputado ({C.NOM_ENT} urbano)": (prob_val[yuc].mul(enigh.factor[yuc], axis=0)).sum(),
}).reindex(nse.NIVELES)
val = (val / val.sum() * 100).round(1)
val["dif pp"] = (val.iloc[:, 1] - val.iloc[:, 0]).round(1)
print(f"Hogares ENIGH usados: {len(enigh):,} ({C.NOM_ENT}: {yuc.sum():,})")
val

# %% [markdown]
# ## 3. Hogares de la muestra censal (estado) → variables de salida y probabilidad NSE

# %%
viv = pd.read_csv(D_MICRO / f"Viviendas{C.ENT}.CSV", dtype=str)
per = pd.read_csv(D_MICRO / f"Personas{C.ENT}.CSV", dtype=str,
                  usecols=["ID_VIV", "EDAD", "PARENTESCO", "NIVACAD", "ESCOLARI", "CONACT", "ESCOACUM"])

viv = viv[viv.NUMPERS.notna() & viv.REFRIGERADOR.notna()].copy()   # viviendas con informacion
for c in ["FACTOR", "NUMPERS", "CUADORM", "TOTCUART", "JEFE_EDAD"]:
    viv[c] = pd.to_numeric(viv[c], errors="coerce")

per["EDAD"] = pd.to_numeric(per.EDAD, errors="coerce").replace(999, np.nan)
per["ESCOACUM"] = pd.to_numeric(per.ESCOACUM, errors="coerce").replace(99, np.nan)
ocupado = per.CONACT.isin(["10", "13", "14", "15", "16", "17", "18", "19", "20"])
e = per.EDAD
nivac = pd.to_numeric(per.NIVACAD, errors="coerce")
per = per.assign(
    n0_5=e.between(0, 5), n6_11=e.between(6, 11), n12_17=e.between(12, 17),
    n18_24=e.between(18, 24), n60=e >= 60, n65=e >= 65,
    ocup12=ocupado & (e >= 12), ocup14=ocupado & (e >= 14),
    p18pb=(e >= 18) & nivac.isin([4, 5, 7, 8, 9, 10, 11, 12, 13, 14]),
    esc15=np.where(e >= 15, per.ESCOACUM, 0),
    edad_menor=np.where(e < 18, e, np.nan),
)
agg = per.groupby("ID_VIV").agg(
    n0_5=("n0_5", "sum"), n6_11=("n6_11", "sum"), n12_17=("n12_17", "sum"), n18_24=("n18_24", "sum"),
    n60=("n60", "sum"), n65=("n65", "sum"), ocup12=("ocup12", "sum"), ocup14=("ocup14", "sum"),
    p18pb=("p18pb", "sum"), esc15=("esc15", "sum"), edad_menor=("edad_menor", "min"))
jefe = per[per.PARENTESCO.str.startswith("1")].drop_duplicates("ID_VIV").set_index("ID_VIV")
agg["pts_edu"] = nse.edu_censo(jefe.NIVACAD, jefe.ESCOLARI).reindex(agg.index)

h = viv.set_index("ID_VIV").join(agg, how="inner")
h["pts_edu"] = h.pts_edu.fillna(h.groupby("MUN").pts_edu.transform("median"))
h["JEFE_EDAD"] = h.JEFE_EDAD.where(h.JEFE_EDAD < 130)
h["JEFE_EDAD"] = h.JEFE_EDAD.fillna(h.JEFE_EDAD.median())

# variables en la misma definicion que el modelo ENIGH
h = h.assign(
    dorm=h.CUADORM.where(h.CUADORM < 99, 1).clip(0, 4), cuartos=h.TOTCUART.where(h.TOTCUART < 99, 2).clip(0, 8),
    internet=(h.INTERNET == "7").astype(int), ocup=h.ocup14, ocup_model=h.ocup12,
    integ=h.NUMPERS.clip(0, 8), pc=(h.COMPUTADORA == "1").astype(int),
    lavadora=(h.LAVADORA == "3").astype(int), micro=(h.HORNO == "5").astype(int),
    banos1=((h.REGADERA == "7") & (h.SERSAN == "1")).astype(int),
    auto1=(h.AUTOPROP == "7").astype(int),
)
P_NSE = nse.distribucion_nse(h, modelos)

# ---- matriz de categorias de salida (hogares x categorias, valores 0-1) ----
cat = pd.DataFrame(index=h.index)
n = h.NUMPERS
cat["2 o Menos Personas"], cat["3 personas"], cat["4 personas"] = n <= 2, n == 3, n == 4
cat["5 personas"], cat["6+ personas"] = n == 5, n >= 6
m = h.edad_menor
cat["Niño < 6"], cat["Niño 6 - 11"], cat["Niño 12+"], cat["Sin Niños"] = m < 6, m.between(6, 11), m >= 12, m.isna()
a = h.JEFE_EDAD
cat["Edad menos de 35"], cat["Edad 35 - 44"], cat["Edad 45 - 54"] = a < 35, a.between(35, 44), a.between(45, 54)
cat["Edad 55 - 64"], cat["Edad 65+"] = a.between(55, 64), a >= 65
for niv in ["A/B", "C+", "C", "C-", "D+"]:
    cat[niv] = P_NSE[niv]
cat["D/E"] = P_NSE["D"] + P_NSE["E"]
cat = cat.astype(float)[C.CATEGORIAS]
print(f"Hogares en la muestra ({C.NOM_ENT}): {len(h):,}  |  representan {h.FACTOR.sum():,.0f} hogares")

# distribucion de referencia estatal (muestra expandida)
REF_ESTADO = cat.mul(h.FACTOR, axis=0).sum() / h.FACTOR.sum() * 100
REF_ESTADO.round(1).to_frame(f"% {C.NOM_ENT}")

# %% [markdown]
# ## 4. Totales por AGEB del Censo 2020 (restricciones de la microsimulación)

# %%
f_ageb = next(D_AGEB.rglob(f"conjunto_de_datos_ageb_urbana_{C.ENT}_cpv2020.csv"))
try:                                                   # Yucatán viene en utf-8-sig, Jalisco en latin-1
    raw = pd.read_csv(f_ageb, dtype=str, encoding="utf-8-sig")
except UnicodeDecodeError:
    raw = pd.read_csv(f_ageb, dtype=str, encoding="latin-1")
# nombres de localidad desde el Marco Geoestadistico (en el CSV AGEB solo dice "Total de la localidad")
loc = gpd.read_file(D_MG / "conjunto_de_datos" / f"{C.ENT}l.shp", columns=["CVEGEO", "NOMGEO"], ignore_geometry=True)
nom_loc = loc.set_index("CVEGEO").NOMGEO
ag = raw[(raw.AGEB != "0000") & (raw.MZA == "000") & raw.MUN.isin(C.ZM_MUNICIPIOS)].copy()
num_cols = ag.columns[8:]
ag[num_cols] = ag[num_cols].apply(pd.to_numeric, errors="coerce")   # '*' y 'N/D' -> NaN
ag = ag.copy()
ag["NOM_LOC"] = (C.ENT + ag.MUN + ag.LOC).map(nom_loc)
ag["CVEGEO"] = C.ENT + ag.MUN + ag.LOC + ag.AGEB
ag = ag[ag.TOTHOG > 0].reset_index(drop=True)

fh = ag.TOTHOG / ag.VIVPARH_CV          # VPH_* estan referidos a viviendas con caracteristicas
fp = ag.POBHOG / ag.POBTOT              # personas -> solo poblacion en hogares
T = pd.DataFrame({
    "hog": ag.TOTHOG,
    "autom": ag.VPH_AUTOM * fh, "inter": ag.VPH_INTER * fh, "pc": ag.VPH_PC * fh,
    "lavad": ag.VPH_LAVAD * fh, "micro": ag.VPH_HMICRO * fh, "stvp": ag.VPH_STVP * fh,
    "spmv": ag.VPH_SPMVPI * fh, "telef": ag.VPH_TELEF * fh, "refri": ag.VPH_REFRI * fh,
    "dor1": ag.VPH_1DOR * fh, "cua1": ag.VPH_1CUART * fh, "cua2": ag.VPH_2CUART * fh,
    "jefe_f": ag.HOGJEF_F,
    "pers": ag.POBHOG, "n0_5": (ag.P_0A2 + ag.P_3A5) * fp, "n6_11": ag.P_6A11 * fp,
    "n12_17": (ag.P_12A14 + ag.P_15A17) * fp, "n18_24": ag.P_18A24 * fp,
    "n60": ag.P_60YMAS * fp, "n65": ag.POB65_MAS * fp, "ocup12": ag.POCUPADA * fp,
    "p18pb": ag.P18YM_PB * fp, "esc15": ag.GRAPROES * ag.P_15YMAS * fp,
})
print(f"AGEB urbanas con hogares en {C.ZM_NOMBRE}: {len(ag):,} | hogares: {ag.TOTHOG.sum():,.0f}")
print("Restricciones faltantes (celdas confidenciales) por variable:")
print(T.isna().sum()[T.isna().sum() > 0].to_dict())

# %% [markdown]
# ## 5. Microsimulación (IPU) por AGEB
#
# Donantes = hogares de la muestra censal de los 5 municipios de la ZM. Peso inicial = factor de
# expansión; los donantes del mismo municipio que la AGEB reciben el doble de peso inicial.

# %%
don = h[h.MUN.isin(C.ZM_MUNICIPIOS)]
cat_don = cat.loc[don.index].values
X = np.column_stack([
    np.ones(len(don)), don.auto1, don.internet, don.pc, don.lavadora, don.micro,
    don.SERV_TV_PAGA == "1", don.SERV_PEL_PAGA == "3", don.TELEFONO == "3", don.REFRIGERADOR == "1",
    don.CUADORM == 1, don.TOTCUART == 1, don.TOTCUART == 2, don.JEFE_SEXO == "3",
    don.NUMPERS, don.n0_5, don.n6_11, don.n12_17, don.n18_24, don.n60, don.n65,
    don.ocup12, don.p18pb, don.esc15.fillna(0),
]).astype(float)
assert X.shape[1] == T.shape[1]

mun_ag, mun_don = ag.MUN.to_numpy(dtype=object), don.MUN.to_numpy(dtype=object)
W0 = don.FACTOR.to_numpy(float)[None, :] * np.where(mun_ag[:, None] == mun_don[None, :], 2.0, 1.0)
W, errores = ipu(X, T.values.astype(float), W0)
HH = W @ cat_don

# error relativo maximo por AGEB (sobre la restriccion peor ajustada, escala min. 5% de hogares)
print(f"Donantes: {len(don):,} | error máx. de calibración por AGEB — mediana {np.median(errores):.3f}, "
      f"p90 {np.quantile(errores, .9):.3f}")
# ajuste agregado por restriccion (qué tan bien se reproduce el Censo AGEB en conjunto)
ajuste = pd.DataFrame({"Censo AGEB": np.nansum(T.values, axis=0), "Microsim": (W @ X).sum(axis=0)}, index=T.columns)
ajuste["dif %"] = ((ajuste.Microsim / ajuste["Censo AGEB"] - 1) * 100).round(2)
ajuste.round(0)

# %% [markdown]
# ## 6. Armar la tabla de salida (HHs, %, Índice) + coordenadas

# %%
geo = gpd.read_file(D_MG / "conjunto_de_datos" / f"{C.ENT}a.shp")
geo = geo[geo.CVEGEO.isin(ag.CVEGEO)]
pt = geo.set_index("CVEGEO").geometry.representative_point().to_crs(4326)

hh = pd.DataFrame(HH, columns=C.CATEGORIAS)
# cada grupo debe sumar el total de hogares de la AGEB: normalizamos por grupo
for g, cols in C.GRUPOS.items():
    hh[cols] = hh[cols].div(hh[cols].sum(axis=1), axis=0).mul(ag.TOTHOG, axis=0)
pct = pd.DataFrame({c: hh[c] / ag.TOTHOG * 100 for c in C.CATEGORIAS})

REF_ZM = hh.sum() / ag.TOTHOG.sum() * 100
REF = REF_ZM if C.REFERENCIA_INDICE == "zm" else REF_ESTADO
idx = pct.div(REF, axis=1) * 100

ids = pd.DataFrame({
    "CVEGEO": ag.CVEGEO,
    "Latitud": ag.CVEGEO.map(pt.y).round(6), "Longitud": ag.CVEGEO.map(pt.x).round(6),
    "Región Nielsen": C.REGION_NIELSEN, "Estado": C.NOM_ENT, "Municipio": ag.NOM_MUN,
    "Localidad": ag.NOM_LOC, "Zonas Metropolitanas": C.ZM_NOMBRE,
    "Total HHs": ag.TOTHOG, "Población": ag.POBTOT,
})
blocks = {}
for c in C.CATEGORIAS:
    blocks[(c, "HHs")] = hh[c].round(0)
    blocks[(c, "%")] = pct[c].round(1)
    blocks[(c, "Indice")] = idx[c].round(0)
tabla = pd.concat([pd.concat({("", k): v for k, v in ids.items()}, axis=1),
                   pd.DataFrame(blocks)], axis=1)
tabla.columns = pd.MultiIndex.from_tuples(tabla.columns)
tabla.head()

# %% [markdown]
# ## 7. Validaciones rápidas

# %%
# (a) ZM agregada vs estimación directa de la muestra (ambas deberían parecerse)
don_ref = cat.loc[don.index].mul(don.FACTOR, axis=0).sum() / don.FACTOR.sum() * 100
chk = pd.DataFrame({"ZM (suma AGEB)": REF_ZM, "ZM (muestra directa)": don_ref, C.NOM_ENT: REF_ESTADO}).round(1)
# (b) comparación NSE con AMAI nacional 2022 (publicado): A/B 7.3, C+ 12.0, C 15.3, C- 16.4, D+ 14.9, D/E 34.1
chk

# %% [markdown]
# ## 8. Guardar resultados
#
# * `outputs/<ciudad>/01_nse_ageb_zm_<ciudad>.xlsx` – formato del entregable (encabezado de 2 niveles).
# * `data/processed/<ciudad>/nse_ageb_zm_<ciudad>.parquet` – tabla plana (para el paso 03).
# * `data/processed/<ciudad>/ageb_zm_<ciudad>.gpkg` – polígonos AGEB con los atributos (para mapas).
# * `data/processed/<ciudad>/manzanas_zm_<ciudad>.parquet` – centroides de manzana con su participación de hogares
#   dentro de la AGEB (para medir áreas de influencia de tiendas en el paso 03).

# %%
out_xlsx = C.OUT / f"01_nse_ageb_{C.SLUG}.xlsx"
with pd.ExcelWriter(out_xlsx, engine="openpyxl") as xw:
    tabla.to_excel(xw, sheet_name="AGEB")
    pd.DataFrame({"Referencia %": REF.round(2)}).to_excel(xw, sheet_name="Referencia indice")
    val.to_excel(xw, sheet_name="Validacion ENIGH")
    chk.to_excel(xw, sheet_name="Validacion ZM")
    ajuste.to_excel(xw, sheet_name="Ajuste microsim")

plana = pd.concat([ids, hh.add_prefix("HHs_")], axis=1)
plana.to_parquet(C.PROC / f"nse_ageb_{C.SLUG}.parquet", index=False)
REF_ESTADO.to_frame("pct").to_parquet(C.PROC / "ref_estado.parquet")
geo.merge(plana, on="CVEGEO").to_file(C.PROC / f"ageb_{C.SLUG}.gpkg", driver="GPKG")

# ---- manzanas: participacion de hogares dentro de su AGEB ----
mz = raw[(raw.MZA != "000") & raw.MUN.isin(C.ZM_MUNICIPIOS)][["MUN", "LOC", "AGEB", "MZA", "TOTHOG", "VIVPAR_HAB"]].copy()
mz["CVEGEO_AGEB"] = C.ENT + mz.MUN + mz.LOC + mz.AGEB
mz["CVEGEO"] = mz.CVEGEO_AGEB + mz.MZA
mz["hog"] = pd.to_numeric(mz.TOTHOG, errors="coerce")
mz = mz[mz.CVEGEO_AGEB.isin(ag.CVEGEO)]
tot = ag.set_index("CVEGEO").TOTHOG
conocido = mz.groupby("CVEGEO_AGEB").hog.sum()
# manzanas confidenciales ('*'): reparten a partes iguales el remanente de hogares de su AGEB
masc = mz.hog.isna() & (pd.to_numeric(mz.VIVPAR_HAB, errors="coerce").fillna(1) > 0)
n_masc = masc.groupby(mz.CVEGEO_AGEB).sum()
resto = (tot - conocido.reindex(tot.index).fillna(0)).clip(lower=0)
mz.loc[masc, "hog"] = (resto / n_masc.reindex(tot.index).replace(0, np.nan)).reindex(mz.loc[masc, "CVEGEO_AGEB"]).values
mz["hog"] = mz.hog.fillna(0)
mz["share"] = mz.hog / mz.groupby("CVEGEO_AGEB").hog.transform("sum")
gmz = gpd.read_file(D_MG / "conjunto_de_datos" / f"{C.ENT}m.shp", columns=["CVEGEO"])
gmz = gmz[gmz.CVEGEO.isin(mz.CVEGEO)]
cm = gmz.set_index("CVEGEO").geometry.representative_point().to_crs(4326)
mz["lat"], mz["lon"] = mz.CVEGEO.map(cm.y), mz.CVEGEO.map(cm.x)
sin_poligono = mz.lat.isna() & (mz.hog > 0)
print(f"Manzanas del Censo sin polígono en el Marco Geoestadístico {C.MG_VERSION}: {sin_poligono.sum():,} "
      f"({mz.hog[sin_poligono].sum():,.0f} hogares, {mz.hog[sin_poligono].sum() / mz.hog.sum():.2%}) → no entran en los radios")
mz = mz.dropna(subset=["lat", "share"])
mz[["CVEGEO", "CVEGEO_AGEB", "hog", "share", "lat", "lon"]].to_parquet(C.PROC / f"manzanas_{C.SLUG}.parquet", index=False)
print("Guardado:", out_xlsx, f"| manzanas: {len(mz):,}")
