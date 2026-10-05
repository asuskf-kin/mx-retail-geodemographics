"""Verificación previa de datos para un bottler y una ciudad (paso 0 de la skill golden-stores-kin). No corre el pipeline.

Uso:
    uv run python .claude/skills/golden-stores-kin/scripts/verificar_datos.py <ciudad> <cliente> [--cp RUTA] [--altscore CARPETA]
        [--etiquetas "CIUDAD DE MEXICO|CDMX"]      # cómo escribe el CP (pos_city) y Rappi (city) a la ciudad, si no está en config

Revisa, sin descargar nada:
  OBLIGATORIOS (si falla uno: DETENERSE y pedirlo al usuario)
    · Customer Potential: archivo, columnas, pos_id único, categoría (config.CP_CATEGORIA) y cuántos PDV caen en la ciudad.
    · AltScore: parquet con ubicación (location.lat + location.lng/lon) y cobertura sobre los PDV de la ciudad (H3 res 8 ± 1 anillo).
  OPCIONALES (si vienen, van en TODO: Excel, mapa y las dos presentaciones)
    · Rappi (líneas de la ciudad sin BRAND_x, marcas Coca-Cola de la Letra 2) · Whisp (hexágonos res 6 de la
      ciudad con venta en la ventana).
  CONFIGURACIÓN: bloque de la ciudad en config.CIUDADES (si no existe: skill /nse-tiendas-mx) y su cliente en config.CLIENTES.
Sale con código 1 si falta algo obligatorio.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

import h3
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BASE / "src"))
import config as C  # noqa: E402  (CIUDAD por defecto; aquí solo se leen constantes generales)

ap = argparse.ArgumentParser()
ap.add_argument("ciudad"); ap.add_argument("cliente")
ap.add_argument("--cp"); ap.add_argument("--altscore"); ap.add_argument("--etiquetas", default="")
a = ap.parse_args()
RAW = BASE / "data" / "raw" / a.ciudad / a.cliente
filas = []


def nota(dato, tipo, estado, detalle):
    filas.append((dato, tipo, estado, detalle))
    print(f"[{estado:^10}] {dato} ({tipo}): {detalle}", flush=True)


def norm(s):
    return " ".join(unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().split())


# ---------------- configuración ----------------
cfg = C.CIUDADES.get(a.ciudad)
cli = C.CLIENTES.get(a.ciudad)
if cfg is None:
    nota("Ciudad en config.CIUDADES", "config", "FALTA", f"'{a.ciudad}' no está configurada: agregar su bloque con la skill /nse-tiendas-mx "
         "(ENT, municipios de la ZM, ENIGH, etiqueta Rappi). Ojo: una ZM de varios estados (p. ej. Valle de México = CDMX + Edo. Méx. + "
         "Hidalgo) NO cabe en un bloque de un solo ENT: preguntar el alcance antes de tocar código.")
else:
    nota("Ciudad en config.CIUDADES", "config", "OK", f"{cfg['ZM_NOMBRE']} · ENT {cfg['ENT']} · {len(cfg['ZM_MUNICIPIOS'])} municipios")
if cli is None or cli.get("cliente") != a.cliente:
    nota("Cliente en config.CLIENTES", "config", "FALTA", f"agregar \"{a.ciudad}\": dict(cliente=\"{a.cliente}\", nombre=..., cp=\"cp/<archivo>.csv\", "
         "ventas=None) cuando el CP esté en su carpeta (las ventas ya no se usan)")
else:
    nota("Cliente en config.CLIENTES", "config", "OK", f"{cli['nombre']} · cp={cli['cp']} · ventas={cli['ventas']}")

etq = [norm(e) for e in a.etiquetas.split("|") if e] or ([norm(cfg["ZM_NOMBRE"].replace("ZM ", ""))] + [norm(m) for m in cfg["ZM_MUNICIPIOS"].values()]
                                                        if cfg else [norm(a.ciudad)])

# ---------------- CP (obligatorio) ----------------
cp_path = Path(a.cp) if a.cp else (RAW / cli["cp"] if cli and cli.get("cliente") == a.cliente else None)
if cp_path is None or not cp_path.exists():
    cands = sorted((RAW / "cp").glob("*.csv")) if (RAW / "cp").exists() else []
    cp_path = cands[0] if cands else None
pdv = pd.DataFrame()
if cp_path is None or not cp_path.exists():
    nota("Customer Potential", "OBLIGATORIO", "FALTA", f"no hay CSV en {RAW / 'cp'}: pedirlo al usuario")
else:
    cp = pd.read_csv(cp_path, low_memory=False)
    cat = C.CP_CATEGORIA
    req = ["pos_id", "pos_name", "pos_latitude", "pos_longitude", "pos_subchannel", "pos_city",
           f"PotentialQuantitative_{cat}", f"PotentialQuantitativeFinal_{cat}", f"PotentialQualitative_{cat}"]
    falt = [c for c in req if c not in cp.columns]
    ciudad_cp = cp.pos_city.map(norm) if "pos_city" in cp else pd.Series("", index=cp.index)
    en = ciudad_cp.apply(lambda c: any(e and (e in c or c in e) for e in etq) if c else False)
    top = ", ".join(f"{k} {v:,}" for k, v in cp.pos_city.value_counts().head(8).items()) if "pos_city" in cp else "sin pos_city"
    if falt:
        nota("Customer Potential", "OBLIGATORIO", "INCOMPLETO", f"{cp_path.name}: faltan columnas {falt}")
    elif not cp.pos_id.is_unique:
        nota("Customer Potential", "OBLIGATORIO", "INCOMPLETO", f"{cp_path.name}: pos_id repetido")
    elif en.sum() == 0:
        nota("Customer Potential", "OBLIGATORIO", "NO CUBRE", f"{cp_path.name}: {len(cp):,} PDV pero ninguno con pos_city de {etq[:3]}. "
             f"Ciudades del CP: {top}. Pedir el CP correcto (o pasar --etiquetas)")
    else:
        pdv = cp[en].copy()
        v = pdv[f"PotentialQuantitative_{cat}"]
        nota("Customer Potential", "OBLIGATORIO", "OK", f"{cp_path.name}: {len(pdv):,} PDV de la ciudad (de {len(cp):,}); {int(v.gt(0).sum()):,} con "
             f"venta de {cat}. La ZM exacta la recorta el 00 por polígono municipal")
    if len(pdv):
        lat, lon = pdv.pos_latitude.astype(float).abs(), -pdv.pos_longitude.astype(float).abs()
        ok = lat.between(14, 33) & lon.between(-118, -86)
        pdv["lat"], pdv["lon"] = lat.where(ok), lon.where(ok)
        if (~ok).mean() > 0.05:
            nota("Coordenadas del CP", "OBLIGATORIO", "REVISAR", f"{(~ok).mean():.0%} fuera de México tal como vienen (el 00 corrige escala e inversión)")

# ---------------- AltScore (obligatorio) ----------------
alt_dir = Path(a.altscore) if a.altscore else RAW / "enrichedgeodata"
alts = sorted(alt_dir.glob("*.parquet")) if alt_dir.exists() else []
if not alts:
    nota("AltScore", "OBLIGATORIO", "FALTA", f"no hay parquet en {alt_dir}: pedirlo al usuario (geohex_geodig.parquet)")
else:
    import pyarrow.parquet as pq
    cols = pq.read_schema(alts[0]).names
    clat = "location.lat" if "location.lat" in cols else None
    clon = next((c for c in ("location.lng", "location.lon") if c in cols), None)
    if not (clat and clon):
        nota("AltScore", "OBLIGATORIO", "INCOMPLETO", f"{alts[0].name}: sin location.lat + location.lng/lon (la unión es solo por ubicación)")
    else:
        al = pd.read_parquet(alts[0], columns=[clat, clon]).replace([-999999, -999998, -999997], np.nan).dropna()
        if len(pdv) and pdv.lat.notna().any():
            p = pdv.dropna(subset=["lat"])
            celdas = {h3.latlng_to_cell(y, x, 8) for y, x in zip(al[clat], al[clon])}
            cub = np.mean([any(c in celdas for c in h3.grid_disk(h3.latlng_to_cell(y, x, 8), 1)) for y, x in zip(p.lat, p.lon)])
            est = "OK" if cub >= 0.5 else "NO CUBRE"
            nota("AltScore", "OBLIGATORIO", est, f"{alts[0].name}: {len(al):,} puntos; {cub:.0%} de los PDV del CP tienen AltScore a ≤ 1 anillo H3 res 8"
                 + ("" if est == "OK" else ": pedir la exportación de esta ciudad"))
        else:
            nota("AltScore", "OBLIGATORIO", "SIN VERIFICAR", f"{alts[0].name}: {len(al):,} puntos con ubicación; cobertura pendiente (no hay PDV del CP)")

# ---------------- opcionales ----------------
if (RAW / "ventas").exists() or (cli and cli.get("ventas")):
    nota("Ventas del cliente", "no se usa", "IGNORADO", "las ventas ya no se usan (usuario, 2026-10-05): poner ventas=None en config.CLIENTES")
if C.RAPPI_CSV.exists():
    rp = pd.read_csv(C.RAPPI_CSV, usecols=["city", "store_lat", "store_lng", "Product_Brand", "Product_Maker_Standard"], engine="pyarrow")
    rp = rp[~rp.Product_Brand.fillna("").str.match(C.RAPPI_EXCLUIR_MARCA)]
    eti = (cfg or {}).get("RAPPI_CIUDAD") or etq
    c_rp = rp.city.map(norm)
    en_rp = c_rp.isin([norm(e) for e in eti]) | c_rp.apply(lambda c: any(e in c for e in eti if e))
    ko = en_rp & rp.Product_Maker_Standard.eq(C.RAPPI_FABRICANTE) & rp.Product_Brand.isin(C.RAPPI_MARCAS_L2)
    nota("Rappi", "opcional (compartido)", "VIENE" if en_rp.any() else "NO VIENE",
         f"{int(en_rp.sum()):,} líneas de la ciudad sin BRAND_x; {int(ko.sum()):,} de hidratación Coca-Cola ({', '.join(C.RAPPI_MARCAS_L2)}). "
         f"Etiquetas usadas: {eti[:3]}" + ("" if en_rp.any() else f" · city en Rappi: {', '.join(rp.city.value_counts().head(6).index)}"))
else:
    nota("Rappi", "opcional (compartido)", "NO VIENE", f"falta {C.RAPPI_CSV}")

if C.WHISP_CSV.exists():
    if len(pdv) and pdv.lat.notna().any():
        hx = {h3.latlng_to_cell(y, x, C.WHISP_RES) for y, x in zip(pdv.lat.dropna(), pdv.lon.dropna())}
        w = pd.read_csv(C.WHISP_CSV, usecols=["Year-Month", "Hexágono (Res. 6)", "Región"])
        w = w[w["Year-Month"].between(*C.WHISP_VENTANA)]
        dentro = w[w["Hexágono (Res. 6)"].isin(hx)]
        nota("Whisp", "opcional (compartido)", "VIENE" if len(dentro) else "NO VIENE",
             f"{dentro['Hexágono (Res. 6)'].nunique()} de {len(hx)} hexágonos res 6 de los PDV del CP tienen venta Whisp en {C.WHISP_VENTANA}"
             + (f" (región {', '.join(dentro['Región'].dropna().unique())})" if len(dentro) else "; la prioridad quedará por letras"))
    else:
        nota("Whisp", "opcional (compartido)", "SIN VERIFICAR", "no hay PDV del CP para ubicar sus hexágonos")
else:
    nota("Whisp", "opcional (compartido)", "NO VIENE", f"falta {C.WHISP_CSV}")

# ---------------- veredicto ----------------
mal = [f for f in filas if f[1] in ("OBLIGATORIO", "config") and f[2] not in ("OK",)]
print("\nRESUMEN")
print(pd.DataFrame(filas, columns=["dato", "tipo", "estado", "detalle"])[["dato", "tipo", "estado"]].to_string(index=False))
if mal:
    print("\nDETENER: " + " · ".join(f"{f[0]} ({f[2]})" for f in mal) + ". Pedir/configurar antes de correr el pipeline.")
    sys.exit(1)
print("\nListo para correr: uv run python src/correr.py --pasos 00,00b,00c,01,02,03,04,05,07,06 " + a.ciudad)
