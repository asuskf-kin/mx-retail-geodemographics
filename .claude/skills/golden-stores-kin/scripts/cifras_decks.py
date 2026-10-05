"""Cifras para escribir a mano los decks de Claude Design (Golden Stores y Letras) desde los resultados ya corridos.

Uso:  uv run python .claude/skills/golden-stores-kin/scripts/cifras_decks.py <ciudad> <cliente> [--ejemplos "NOMBRE 1|NOMBRE 2"]

Deck Golden Stores (lo armó el usuario sobre las letras del 06): base = PDV Tradicional CON VENTA del CP (venta media > 0),
segmento = letras finales del 06 ("sin NSE" aparte), venta = venta media de la categoría del CP, potencial =
PotentialQuantitativeFinal y semáforo = PotentialQualitative (Very High/High verde · Moderate amarillo · Low rojo). El perfil del
hogar de las HH sale de la hoja "Perfil %" del Excel del 05 (redondeo: 0.5 hacia arriba; barra = % × 6.85 px).
Deck Letras: hojas Resumen y Sensibilidad Letra 2 del Excel del 06, parquet de letras y textos del notebook 06 ejecutado.
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[4]
ap = argparse.ArgumentParser()
ap.add_argument("ciudad"); ap.add_argument("cliente"); ap.add_argument("--ejemplos", default="")
a = ap.parse_args()
slug = f"zm_{a.ciudad}"
P = BASE / "data" / "processed" / a.ciudad / a.cliente
CL = BASE / "outputs" / a.ciudad / a.cliente / "cliente"
pd.set_option("display.width", 250)

# ---------------- Golden Stores ----------------
l = pd.read_parquet(P / f"letras_pdv_{a.cliente}_{slug}.parquet")
d = pd.read_parquet(P / f"pdv_{a.cliente}_{slug}.parquet").drop_duplicates("pos_id_cp").set_index("pos_id_cp")
cat = [c.split("PotentialQualitative_")[1] for c in d.columns if c.startswith("PotentialQualitative_Custom")][0]
l = l.join(d[[f"PotentialQualitative_{cat}", f"PotentialQuantitativeFinal_{cat}", "pos_name", "pos_subchannel"]], on="pos_id_cp")
b = l[l.V.fillna(0) > 0].copy()
b["seg"] = b.letras.fillna("sin NSE")
POT = f"PotentialQuantitativeFinal_{cat}"
n, V, G = len(b), b.V.sum(), b[POT].fillna(0).sum()
print(f"== GOLDEN STORES · base con venta {n:,} (sin NSE {int((b.seg == 'sin NSE').sum())}) · venta {V:,.0f} · potencial {G:,.0f}")
g = b.groupby("seg")
print(pd.DataFrame({"tiendas": g.size(), "% tiendas": g.size() / n * 100, "% venta": g.V.sum() / V * 100,
                    "% potencial": g[POT].sum() / G * 100, "venta media": g.V.mean()}).round(2))
print(f"venta media del canal {b.V.mean():.2f} · HH vende {b.V[b.seg.eq('HH')].mean() / b.V.mean() - 1:+.0%} vs el canal")
sem = b[f"PotentialQualitative_{cat}"].map({"Very High": "verde", "High": "verde", "Moderate": "amarillo", "Low": "rojo"})
print(b[f"PotentialQualitative_{cat}"].value_counts().to_dict())
print(pd.crosstab(b.seg, sem, margins=True))
ver, hh = sem.eq("verde"), b.seg.eq("HH")
print(f"verde: {ver.mean():.0%} del canal, {b.V[ver].sum() / V:.0%} de la venta, {b[POT][ver].sum() / G:.0%} del potencial · "
      f"HH verde {(hh & ver).sum():,} ({(hh & ver).sum() / hh.sum():.0%}), {b.V[hh & ver].sum() / V:.0%} venta, {b[POT][hh & ver].sum() / G:.0%} potencial")
print((pd.crosstab(b.pos_subchannel, b.seg, normalize="columns") * 100).round(1))
pf = pd.read_excel(CL / f"05_golden_stores_tradicional_{a.cliente}_{slug}.xlsx", sheet_name="Perfil %", header=3)
print("perfil HH (05):", pf[pf.iloc[:, 0].eq("HH")].iloc[0, 1:].to_dict())
ej = b[hh & b.rappi_n.ge(1) & b.n_cluster_nse.between(3, 6) & b.pos_name.str.contains("ABARROTES|TIENDA|MINI|SUPER|CREMERIA", na=False)]
print("ejemplos HH con Rappi y clúster de 3-6 PDV (para mapa/ficha):")
print(ej[["pos_id_cp", "pos_name", "prioridad", "V", f"PotentialQualitative_{cat}"]].sort_values("V", ascending=False).head(5).to_string())

# ---------------- Letras ----------------
X = CL / f"06_letras_nse_ventas_tradicional_{a.cliente}_{slug}.xlsx"


def hoja(nombre, clave):
    t = pd.read_excel(X, sheet_name=nombre, header=None)
    i = t.index[t.apply(lambda r: clave in r.astype(str).tolist(), axis=1)][0]
    u = t.loc[i + 1:].copy(); u.columns = t.loc[i]; return u.dropna(how="all")


print("\n== LETRAS")
print(hoja("Resumen", "Letras").to_string())
print(hoja("Sensibilidad Letra 2", "variante").to_string())
ob = l[l.objetivo]
print(f"objetivo {len(ob):,} de {len(l):,} · con Rappi a 300 m {int((ob.rappi_n > 0).sum()):,} ({(ob.rappi_n > 0).mean():.1%}) · "
      f"Rappi sube {int(ob.sube_por_rappi.sum())} / baja {int(ob.baja_por_rappi.sum())} · L1 H {(ob.L1 == 'H').mean():.0%} · "
      f"L2 H {(ob.L2 == 'H').mean():.1%} · AltScore cambia {int(ob.cambia_por_alt.sum())} ({int(ob.sube_por_alt.sum())}↑ {int(ob.baja_por_alt.sum())}↓)")
print("prioridad", l.prioridad.value_counts().to_dict(), "|", l.fuente_prioridad.value_counts().to_dict())
nb = json.loads((BASE / "notebooks" / "ejecutados" / a.ciudad / "06_letras_nse_ventas.ipynb").read_text(encoding="utf-8"))
txt = "".join("".join(o.get("text", "")) for c in nb["cells"] for o in c.get("outputs", []))
for k in ["clústeres NSE (hexágonos H3 res 9) tienen PDV objetivo", "confirmada por el Censo", "NSE AMAI vs índice del Censo",
          "tiendas físicas Rappi", "con λ = 0.5", "Prioridad:"]:
    m = re.search(re.escape(k), txt)
    if m:
        print(">>", txt[max(0, m.start() - 150):m.start() + 300].replace("\n", " "))
if a.ejemplos:
    v = pd.read_parquet(P / f"letra2_vector_{a.cliente}_{slug}.parquet")
    for nom in a.ejemplos.split("|"):
        print(v[v.Nombre.str.upper().eq(nom.upper())][["pos_id", "Nombre", "venta_media", "cp", "rappi", "score", "score_sin_rappi"]].to_string())
