# %% [markdown]
# # 07 · Share de Coca-Cola con Whisp (opcional) → prioridad
#
# **Regla del usuario (2026-10-05):** la prioridad de cada PDV sale de su **Letra 1** (demanda) y del **share** de Coca-Cola de su zona:
#
# | Letra 1 | Share | Prioridad |
# |---|---|---|
# | H | bajo | **P1** |
# | H | alto | **P2** |
# | L | bajo | **P3** |
# | L | alto | **P4** |
#
# El share sale de **Whisp** (`data/raw/whisp/Whisp.csv`, ventas por hexágono H3 **res 6**, fabricante y mes): por hexágono,
# share = cajas unidad de `COCA-COLA COMPANY` / cajas unidad de todos los fabricantes (sueros + isotónicos), en la ventana
# `config.WHISP_VENTANA` (ago-2025 → ago-2026). **Alto** si el share del hexágono ≥ share de toda el área de estudio (índice 100,
# la misma lógica que Golden Stores). También se reporta el share en revenue.
#
# **Whisp es opcional:** solo cubre algunas regiones (hoy Occidente y CD.MX). Si no tiene datos para el área (p. ej. Mérida), este
# paso lo registra y el 06 deja la prioridad por letras (HH P1 · HL P2 · LH P3 · LL P4). Un PDV cuyo hexágono no tiene ventas en
# Whisp también toma la prioridad por letras (y se marca la fuente). El 06 lee la salida de este paso.

# %%
import os
import sys
from pathlib import Path

os.environ.setdefault("CIUDAD", "merida")
BASE = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(BASE / "src"))

import h3
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from IPython.display import display
from shapely.geometry import Polygon

import config as C
import eda
from descargas import requisitos, descargar_fuente, extraer

assert C.CIUDAD == C.CLIENTE_CIUDAD, f"No hay cliente configurado para {C.CIUDAD}"
eda.estilo()
F_PDV = C.PROC / f"pdv_{C.CLIENTE}_{C.SLUG}.parquet"
requisitos({F_PDV: "00_cp_validacion / 00_ventas_cp_validacion"})
SALIDA = C.PROC / f"whisp_share_{C.CLIENTE}_{C.SLUG}.parquet"
print(f"{C.CLIENTE_NOMBRE} · {C.ZM_NOMBRE} · Whisp: {C.WHISP_CSV.relative_to(BASE)} · ventana {C.WHISP_VENTANA}")

# %% [markdown]
# ## 1. Área de estudio en hexágonos H3 res 6
#
# Hexágonos cuyo centro cae en un municipio de la ZM, más los que contienen algún PDV del cliente (por si un PDV queda en un
# hexágono de borde).

# %%
descargar_fuente(C.FUENTES["mg"])
mun = gpd.read_file(next(extraer(C.ARCHIVOS["mg"]).rglob(f"{C.ENT}mun.shp")))
zm = mun[mun.CVE_MUN.isin(C.ZM_MUNICIPIOS)].to_crs(4326)
area = set()
for g in zm.geometry:
    for parte in getattr(g, "geoms", [g]):
        area |= set(h3.geo_to_cells(parte.__geo_interface__, C.WHISP_RES))
pdv = pd.read_parquet(F_PDV)
pdv = pdv[pdv.lat.notna()].copy()
pdv["hex6"] = [h3.latlng_to_cell(a, b, C.WHISP_RES) for a, b in zip(pdv.lat, pdv.lon)]
area |= set(pdv.hex6)
print(f"Área de estudio: {len(area):,} hexágonos res 6 (≈ 36 km² cada uno) · {len(pdv):,} PDV del cliente")

# %% [markdown]
# ## 2. Whisp en el área y la ventana

# %%
DISPONIBLE = C.WHISP_CSV.exists()
if DISPONIBLE:
    whisp = (pd.read_csv(C.WHISP_CSV, usecols=["Year-Month", "Categoria", "Segmento", "Fabricante", "Región", "SubTerritorio",
                                          "Hexágono (Res. 6)", "Cajas Unidad", "Revenue"])
             .rename(columns={"Year-Month": "aniomes", "Hexágono (Res. 6)": "hex_res_6", "Cajas Unidad": "unit_cases", "Revenue": "revenue"}))
    print(f"Whisp: {len(whisp):,} filas · regiones {sorted(whisp['Región'].dropna().unique())} · meses {whisp.aniomes.min()}–{whisp.aniomes.max()}")
    whisp = whisp[whisp.aniomes.between(*C.WHISP_VENTANA) & whisp.hex_res_6.isin(area)].copy()
    DISPONIBLE = len(whisp) > 0
else:
    whisp = pd.DataFrame()
if not DISPONIBLE:
    print(f"Whisp NO tiene datos para {C.ZM_NOMBRE} en la ventana {C.WHISP_VENTANA}: la prioridad sale de las letras (HH P1 · HL P2 · "
          "LH P3 · LL P4).")
else:
    whisp["industry"] = np.where(whisp.Fabricante == C.WHISP_KO, "ko", "noko")
    for c_ in ["Región", "SubTerritorio", "Segmento", "Categoria"]:
        whisp[c_] = whisp[c_].fillna("sin dato en Whisp")
    print(f"Whisp en el área: {len(whisp):,} filas · {whisp.hex_res_6.nunique():,} hexágonos con venta de {len(area):,} · "
          f"{whisp.aniomes.nunique()} meses · categorías {whisp.Categoria.value_counts().to_dict()}")

# %% [markdown]
# ## 3. Share KO por hexágono (código del usuario) y corte por índice 100

# %%
if DISPONIBLE:
    whisp_agg = whisp.groupby(["hex_res_6", "industry"])[["unit_cases", "revenue"]].sum().reset_index()
    piv = whisp_agg.pivot_table(index="hex_res_6", columns="industry", values=["unit_cases", "revenue"], aggfunc="sum").fillna(0)
    piv.columns = [f"{v}_{i}" for v, i in piv.columns]
    for c_ in ["unit_cases_ko", "unit_cases_noko", "revenue_ko", "revenue_noko"]:
        if c_ not in piv:
            piv[c_] = 0.0
    sh = piv.copy()
    sh["share_cajas"] = sh.unit_cases_ko / (sh.unit_cases_ko + sh.unit_cases_noko)
    sh["share_revenue"] = sh.revenue_ko / (sh.revenue_ko + sh.revenue_noko)
    SHARE_AREA = sh.unit_cases_ko.sum() / (sh.unit_cases_ko.sum() + sh.unit_cases_noko.sum())
    sh["indice_share"] = sh.share_cajas / SHARE_AREA * 100
    sh["share_clase"] = np.where(sh.share_cajas >= SHARE_AREA, "alto", "bajo")
    sh["cajas_total"] = sh.unit_cases_ko + sh.unit_cases_noko
    print(f"Share KO del área (cajas unidad): {SHARE_AREA:.1%} · revenue: {sh.revenue_ko.sum() / (sh.revenue_ko.sum() + sh.revenue_noko.sum()):.1%}")
    print(f"Hexágonos con share alto: {(sh.share_clase == 'alto').sum()} de {len(sh)}")
    display(sh.sort_values("cajas_total", ascending=False).round(3).head(15))

    # Región, SubTerritorio y Segmento de cada hexágono (usuario, 2026-10-05): todos los valores, el de más cajas primero
    def valores(col):
        g = whisp.groupby(["hex_res_6", col]).unit_cases.sum().reset_index().sort_values(["hex_res_6", "unit_cases"], ascending=[True, False])
        return g.groupby("hex_res_6")[col].agg(" · ".join)
    geo = pd.DataFrame({c_: valores(c_) for c_ in ["Región", "SubTerritorio", "Segmento"]})
    geo["SubTerritorio principal"] = geo.SubTerritorio.str.split(" · ").str[0]
    # share KO por categoría dentro del hexágono (sueros / isotónicos)
    cat = whisp.pivot_table(index="hex_res_6", columns=["Categoria", "industry"], values="unit_cases", aggfunc="sum").fillna(0)
    por_cat = pd.DataFrame(index=sh.index)
    for k in sorted(whisp.Categoria.unique()):
        ko_, no_ = (cat[(k, i)] if (k, i) in cat else 0 for i in ["ko", "noko"])
        tot = ko_ + no_
        por_cat[f"cajas {k.lower()}"] = tot
        por_cat[f"share KO {k.lower()}"] = (ko_ / tot).where(tot > 0)
    sh = sh.join(geo).join(por_cat)

    # Fabricantes por categoría: cajas, revenue y participación dentro de la categoría
    fab = (whisp.groupby(["Categoria", "Fabricante"])[["unit_cases", "revenue"]].sum().reset_index()
              .sort_values(["Categoria", "unit_cases"], ascending=[True, False]))
    tot_cat = fab.groupby("Categoria")[["unit_cases", "revenue"]].transform("sum")
    fab["% cajas en la categoría"] = fab.unit_cases / tot_cat.unit_cases * 100
    fab["% revenue en la categoría"] = fab.revenue / tot_cat.revenue * 100
    fab["% cajas del área"] = fab.unit_cases / fab.unit_cases.sum() * 100
    fab["lugar en la categoría"] = fab.groupby("Categoria").unit_cases.rank(ascending=False, method="min").astype(int)
    fab["es Coca-Cola"] = np.where(fab.Fabricante == C.WHISP_KO, "sí", "no")
    fab["hexágonos con venta"] = fab.apply(lambda r: whisp[(whisp.Categoria == r.Categoria) & (whisp.Fabricante == r.Fabricante)].hex_res_6.nunique(), axis=1)
    display(fab.groupby("Categoria").head(5).round(1))

    # Categorías y segmentos: tamaño y share KO
    def resumen_grupo(cols):
        g = whisp.groupby(cols + ["industry"])[["unit_cases", "revenue"]].sum().unstack("industry", fill_value=0)
        t = pd.DataFrame({"cajas": g.unit_cases.sum(axis=1), "revenue": g.revenue.sum(axis=1)})
        t["% cajas del área"] = t.cajas / t.cajas.sum() * 100
        t["share KO cajas"] = g.unit_cases.get("ko", 0) / t.cajas * 100
        t["share KO revenue"] = g.revenue.get("ko", 0) / t.revenue * 100
        t["fabricantes"] = whisp.groupby(cols).Fabricante.nunique()
        t["hexágonos con venta"] = whisp.groupby(cols).hex_res_6.nunique()
        return t.reset_index()
    cats = pd.concat([resumen_grupo(["Categoria"]).assign(Segmento="todos"), resumen_grupo(["Categoria", "Segmento"])])
    cats = cats[["Categoria", "Segmento"] + [c_ for c_ in cats if c_ not in ("Categoria", "Segmento")]].sort_values(["Categoria", "Segmento"], key=lambda x: x.replace("todos", "0"))
    display(cats.round(1))
else:
    sh = pd.DataFrame(columns=["unit_cases_ko", "unit_cases_noko", "revenue_ko", "revenue_noko", "share_cajas", "share_revenue",
                               "indice_share", "share_clase", "cajas_total"])
    SHARE_AREA = np.nan
    fab = cats = pd.DataFrame()

# %% [markdown]
# ## 4. Share de cada PDV (su hexágono res 6) y QA en mapa

# %%
pdv_sh = pdv[["pos_id_cp", "hex6", "canal"]].join(sh, on="hex6")
pdv_sh["whisp_disponible"] = DISPONIBLE
pdv_sh["share_area"] = SHARE_AREA                     # share de Coca-Cola de toda el área (corte alto / bajo; lo usa el mapa del 06)
pdv_sh["fuente_share"] = np.where(pdv_sh.share_cajas.notna(), "Whisp (hexágono res 6)",
                                  "sin ventas en Whisp en su hexágono" if DISPONIBLE else "Whisp sin datos para el área")
print(pdv_sh.fuente_share.value_counts().to_string())
if DISPONIBLE:
    poly = gpd.GeoDataFrame(sh.reset_index(), geometry=[Polygon([(b, a) for a, b in h3.cell_to_boundary(h)]) for h in sh.index], crs=4326)
    fig, ax = plt.subplots(1, 2, figsize=(15, 7))
    zm.boundary.plot(ax=ax[0], color="#999ea6", linewidth=0.6)
    poly.plot(ax=ax[0], column="share_cajas", cmap="RdYlGn", legend=True, alpha=0.8, edgecolor="white")
    ax[0].set_title(f"Share KO (cajas) por hexágono res 6 · área {SHARE_AREA:.0%}")
    zm.boundary.plot(ax=ax[1], color="#999ea6", linewidth=0.6)
    poly.plot(ax=ax[1], color=poly.share_clase.map({"alto": "#1baf7a", "bajo": "#e34948"}), alpha=0.7, edgecolor="white")
    t_ = pdv[pdv.canal == "Tradicional"]
    ax[1].scatter(t_.lon, t_.lat, s=0.3, c="#141417", alpha=0.3)
    ax[1].set_title("Share alto (verde) / bajo (rojo) y PDV Tradicional (negro)")
    for a_ in ax:
        a_.set_axis_off()
    plt.tight_layout(); plt.show()

# %% [markdown]
# ## 5. Guardar (lo lee el 06)

# %%
pdv_sh.to_parquet(SALIDA, index=False)
resumen = pd.DataFrame([("Whisp disponible para el área", "sí" if DISPONIBLE else "no"),
                        ("Ventana", f"{C.WHISP_VENTANA[0]} → {C.WHISP_VENTANA[1]}"),
                        ("Hexágonos res 6 del área", len(area)), ("Hexágonos con ventas en Whisp", len(sh)),
                        ("Share KO del área (cajas)", f"{SHARE_AREA:.1%}" if DISPONIBLE else "no aplica · sin Whisp"),
                        ("Hexágonos con share alto", int((sh.share_clase == "alto").sum()) if DISPONIBLE else "no aplica · sin Whisp"),
                        ("PDV con share de Whisp", int(pdv_sh.share_cajas.notna().sum())),
                        ("Regla", "Prioridad = Letra 1 × share: H bajo P1 · H alto P2 · L bajo P3 · L alto P4; sin share, por letras")],
                       columns=["concepto", "valor"])
out = C.OUT / f"07_whisp_share_{C.CLIENTE}_{C.SLUG}.xlsx"
with pd.ExcelWriter(out) as xw:
    resumen.to_excel(xw, sheet_name="Resumen", index=False)
    hx = sh.round(4).reset_index().rename(columns={"index": "hex_res_6"})
    pri = ["hex_res_6", "Región", "SubTerritorio principal", "SubTerritorio", "Segmento"]
    hx = hx[[c_ for c_ in pri if c_ in hx] + [c_ for c_ in hx if c_ not in pri]]
    for c_ in [c_ for c_ in hx if c_.startswith("share KO ")]:   # sin celdas vacías sin motivo
        hx[c_] = hx[c_].astype(object).where(hx[c_].notna(), "sin venta de la categoría en el hexágono")
    hx.to_excel(xw, sheet_name="Share por hexágono", index=False)
    (fab.rename(columns={"unit_cases": "cajas unidad"}).round(2) if len(fab) else pd.DataFrame({"nota": ["no aplica · sin Whisp para el área"]})
     ).to_excel(xw, sheet_name="Fabricantes", index=False)
    (cats.round(2) if len(cats) else pd.DataFrame({"nota": ["no aplica · sin Whisp para el área"]})).to_excel(xw, sheet_name="Categorías", index=False)
display(resumen)
print(f"Guardado: {SALIDA.name} ({len(pdv_sh):,} PDV, {int(pdv_sh.share_cajas.notna().sum()):,} con share) | {out.name}")
