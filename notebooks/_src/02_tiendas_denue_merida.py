# %% [markdown]
# # 02 · Tiendas DENUE — canal Moderno vs Tradicional (ciudad según `src/config.py`)
#
# * **462111** – Comercio al por menor en supermercados
# * **462112** – Comercio al por menor en minisupers
# * **461110** – Comercio al por menor en tiendas de abarrotes, ultramarinos y misceláneas
#
# **Canal:** *Moderno* = tienda de una cadena identificada (OXXO, Dunosusa, Willys, Aki, Walmart…).
# *Tradicional* = establecimientos independientes (abarrotes, misceláneas y minisupers sin cadena).
# Se entregan en **dos archivos xlsx** separados.
#
# **Fuente oficial:** INEGI, DENUE – descarga masiva por entidad (edición vigente, se lee del
# archivo de metadatos; verificada el 2026-09-24: edición 05_2026, publicada 2026-05-20).
# * Página oficial: https://www.inegi.org.mx/app/descarga/?ti=6
# * URL de descarga: `https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip` (en `src/config.py` → `FUENTES`)
#
# Se identifica la **cadena** por nombre / razón social y se marcan las
# tiendas **nuevas** (dadas de alta en el DENUE en los últimos 24 meses).
#
# **Fuente complementaria (opcional):** OpenStreetMap (Overpass API) para detectar tiendas que aún no
# aparecen en DENUE (p. ej. aperturas recientes). Solo se usa como alerta, no se mezcla con DENUE.
# * Overpass API: https://overpass-api.de/api/interpreter (respaldo: https://overpass.kumi.systems/api/interpreter)

# %%
import re, sys, zipfile, io
from pathlib import Path

BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())   # raíz del repo
sys.path.insert(0, str(BASE / "src"))
import numpy as np
import pandas as pd
import requests

import config as C
from descargas import descargar, registrar_fuentes, verificar_fuentes
from IPython.display import display

pd.set_option("display.width", 200, "display.max_columns", 30)


# reproducibilidad: ciudad, versiones y semilla (no hay pasos aleatorios en este notebook)
import platform
print(f"Repo: {BASE} | ciudad: {C.ZM_NOMBRE} (CIUDAD={C.CIUDAD}) | Python {platform.python_version()} · pandas {pd.__version__} · numpy {np.__version__}")
print("Nota: el cruce con OpenStreetMap (sección 3) consulta un servicio externo que cambia con el tiempo; "
      "solo genera alertas y no altera las tiendas DENUE ni los entregables.")

# %% [markdown]
# ## 1. Descarga DENUE del estado

# %%
print(f"Ciudad: {C.ZM_NOMBRE} · {C.NOM_ENT} ({C.ENT}) · municipios: " + ", ".join(f"{v} ({k})" for k, v in C.ZM_MUNICIPIOS.items()))
display(verificar_fuentes(C.FUENTES, ["denue"]))
print("denue:", C.URLS["denue"])
descargar(C.URLS["denue"], C.ARCHIVOS["denue"])
with zipfile.ZipFile(C.ARCHIVOS["denue"]) as z:
    meta = z.read(next(n for n in z.namelist() if n.startswith("metadatos"))).decode("utf-8-sig", "replace")
    f_csv = next(n for n in z.namelist() if n.startswith("conjunto_de_datos") and n.endswith(".csv"))
    denue = pd.read_csv(z.open(f_csv), dtype=str, encoding="latin-1")
EDICION = re.search(r"Title:.*\(DENUE\)\s*(\S+)", meta).group(1)
print("Edición DENUE:", EDICION, f"| establecimientos en {C.NOM_ENT}:", f"{len(denue):,}")
registrar_fuentes(C.FUENTES, ["denue"], C.PROC / "fuentes_usadas_02.csv", extra={"denue": {"edicion_leida": EDICION}})

# %% [markdown]
# ## 2. Filtro SCIAN + ZM y limpieza

# %%
t = denue[denue.codigo_act.isin(C.SCIAN_TIENDAS) & denue.cve_mun.isin(C.ZM_MUNICIPIOS)].copy()
for c in ["nom_estab", "raz_social", "localidad", "municipio", "nomb_asent", "nom_vial"]:
    t[c] = t[c].fillna("").str.strip()
t["latitud"] = pd.to_numeric(t.latitud, errors="coerce")
t["longitud"] = pd.to_numeric(t.longitud, errors="coerce")
t = t.dropna(subset=["latitud", "longitud"])
t["formato"] = t.codigo_act.map(C.SCIAN_TIENDAS)

# cadenas: patron sobre nombre + razon social (orden importa: el primero que coincide)
CADENAS = [
    ("Bara", r"^(?!ABARROTES)[^|]*(?:SUPER BARA|TIENDAS? BARA)\b"),  # FEMSA; comparte razon social con OXXO
    ("OXXO", r"\bOXXO\b|CADENA COMERCIAL OXXO"),
    ("7-Eleven", r"7[\s-]?ELEVEN|SEVEN\s?L?ELEVEN|SIETE ONCE"),
    ("Circle K", r"CIRCLE\s*K\b|CIRCULO K\b"),
    ("Kiosko", r"^(?!ABARROTES).*\bKIOSKO\b"),         # "ABARROTES KIOSKO" = tienda independiente
    ("Super Aki", r"^(?!TIENDA DE ABARROTES AKI).*(?:\bAKI\b|SUPER\s*AKI|GRUPO AKI|DAC\b)"),
    ("Six", r"\bSIX\b"),
    ("Bodega Aurrera", r"AURRERA"),
    ("Walmart", r"\bWAL\s*-?\s*MART\b"),              # no "WALMARTHA"
    ("Sam's Club", r"\bSAM'?S CLUB\b"),                 # no "ABARROTES SAMS"
    ("Soriana", r"SORIANA|MEGA SORIANA|CITY CLUB"),
    ("Chedraui", r"CHEDRAUI"),
    ("La Comer / City Market / Fresko", r"LA COMER|CITY MARKET|FRESKO|SUMESA"),
    ("Costco", r"COSTCO"),
    ("Super San Francisco de Asís", r"SAN FRANCISCO DE ASIS"),
    ("Super Willys", r"WILLYS|SUPER\s*WILLY"),
    ("Tiendas 3B", r"\b3\s?B\b|TIENDAS TRES B|BBB"),
    ("Tiendas Neto", r"^(?!.*EL NETO).*\bNETO\b"),
    ("Merza / Dax", r"\bMERZA\b|\bDAX\b"),
    ("Extra", r"\bEXTRA\b"),
    ("Dunosusa", r"DUNOSUSA|DONOSUSA|\bDUNO\b"),
    ("Go Mart", r"GO\s?MART"),
    ("Super Farahon", r"FARAHON"),
    ("Waldo's", r"\bWALDO"),                           # no "OSWALDO"
    ("La Macarena", r"^(?!.*TENDEJON).*MACARENA"),
    ("Delimart (Pemex)", r"DELIMART|PEME\d"),
    ("Toyo Foods", r"TOYO FOODS"),
    # Guadalajara
    ("Su Super", r"^SU SUPER\b"),
    ("Abarrotes y Bebidas MR", r"ABARROTES Y BEBIDAS MR\b"),
    ("Super Kadis", r"SUPER KADIS"),
    ("Area 24.7", r"AREA 24\.?7"),
    ("Tiendas IMSS / ISSSTE", r"TIENDA DEL IMSS|SUPERISSSTE"),
]
texto = (t.nom_estab + " | " + t.raz_social).str.upper()
t["cadena"] = "Independiente"
for nombre, patron in reversed(CADENAS):
    t.loc[texto.str.contains(patron, regex=True), "cadena"] = nombre
# Six (Grupo Modelo) son abarrotes independientes afiliados -> canal tradicional
CADENAS_TRADICIONALES = {"Independiente", "Six"}
t["canal"] = np.where(t.cadena.isin(CADENAS_TRADICIONALES), "Tradicional", "Moderno")

# tamaño de establecimiento y antiguedad en DENUE
t["fecha_alta"] = pd.to_datetime(t.fecha_alta, format="%Y-%m", errors="coerce")
corte = t.fecha_alta.max() - pd.DateOffset(months=24)
t["nueva_24m"] = t.fecha_alta >= corte

tiendas = t[["id", "clee", "nom_estab", "raz_social", "codigo_act", "formato", "canal", "cadena", "per_ocu",
             "tipo_vial", "nom_vial", "numero_ext", "nomb_asent", "cod_postal", "cve_mun", "municipio",
             "cve_loc", "localidad", "ageb", "manzana", "latitud", "longitud", "fecha_alta", "nueva_24m"]].reset_index(drop=True)
tiendas["edicion_denue"] = EDICION
print(f"Tiendas {C.ZM_NOMBRE}: {len(tiendas):,}")
print(pd.crosstab(tiendas.canal, tiendas.formato, margins=True), "\n")
pd.crosstab(tiendas.cadena, tiendas.formato, margins=True).sort_values("All", ascending=False)

# %% [markdown]
# Revisión: cadenas detectadas dentro de abarrotes (461110) — verificar que no sean falsos positivos.

# %%
tiendas[(tiendas.formato == "Abarrotes") & (tiendas.canal == "Moderno")].groupby("cadena").nom_estab.agg(["count", "first"])

# %%
pd.crosstab(tiendas.municipio, [tiendas.canal, tiendas.formato], margins=True)

# %% [markdown]
# ## 3. (Opcional) Cruce con OpenStreetMap para detectar tiendas no registradas en DENUE
#
# Se consultan `shop=supermarket` y `shop=convenience` en la ZM. Una tienda OSM a más de 100 m de
# cualquier tienda DENUE se marca como *posible tienda no registrada*. Si Overpass no responde, se omite.

# %%
USAR_OSM = True
osm_nuevas = pd.DataFrame()
if USAR_OSM:
    s, w, n, e = tiendas.latitud.min() - .02, tiendas.longitud.min() - .02, tiendas.latitud.max() + .02, tiendas.longitud.max() + .02
    q = f"""[out:json][timeout:120];
    (nwr["shop"~"^(supermarket|convenience)$"]({s},{w},{n},{e}););
    out center tags;"""
    for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        try:
            r = requests.post(url, data={"data": q}, timeout=180,
                              headers={"User-Agent": "analisis-retail-mx/1.0"})  # Overpass exige User-Agent
            r.raise_for_status()
            el = r.json()["elements"]
            break
        except Exception as ex:
            print("Overpass falló en", url, "->", ex.__class__.__name__)
            el = None
    if el:
        osm = pd.DataFrame([{
            "osm_id": f"{x['type']}/{x['id']}", "nombre": x.get("tags", {}).get("name", ""),
            "marca": x.get("tags", {}).get("brand", ""), "shop": x["tags"]["shop"],
            "lat": x.get("lat", x.get("center", {}).get("lat")), "lon": x.get("lon", x.get("center", {}).get("lon")),
        } for x in el])
        from sklearn.neighbors import BallTree
        bt = BallTree(np.radians(tiendas[["latitud", "longitud"]].values), metric="haversine")
        d, _ = bt.query(np.radians(osm[["lat", "lon"]].values), k=1)
        osm["dist_denue_m"] = (d[:, 0] * 6_371_000).round(0)
        osm_nuevas = osm[osm.dist_denue_m > 100].sort_values("dist_denue_m", ascending=False)
        print(f"OSM: {len(osm):,} tiendas | a >100 m de DENUE: {len(osm_nuevas):,}")
osm_nuevas.head(15)

# %% [markdown]
# ## 4. Guardar

# %%
tiendas.to_parquet(C.PROC / f"tiendas_denue_{C.SLUG}.parquet", index=False)
for canal in C.CANALES:
    sub = tiendas[tiendas.canal == canal]
    out = C.OUT / f"02_tiendas_{canal.lower()}_{C.SLUG}.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        sub.to_excel(xw, sheet_name=f"Tiendas {canal}", index=False)
        if canal == "Moderno":
            pd.crosstab(sub.cadena, sub.formato, margins=True).to_excel(xw, sheet_name="Resumen cadenas")
        pd.crosstab(sub.municipio, sub.formato, margins=True).to_excel(xw, sheet_name="Resumen municipio")
        if len(osm_nuevas):
            osm_nuevas.to_excel(xw, sheet_name="OSM no en DENUE", index=False)
    print(f"Guardado: {out.name} ({len(sub):,} tiendas)")
