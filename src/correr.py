"""Corre los notebooks por ciudad, en paralelo cuando sus dependencias lo permiten.

Uso (desde la raiz del repo):
    python src/correr.py merida guadalajara              -> pipeline 01-03 de cada ciudad
    python src/correr.py --pasos 00,01,02,03,04 merida   -> los notebooks indicados (Bepensa)
    python src/correr.py --pasos 00c,06 merida            -> EDA de Rappi y letras NSE / ventas
    python src/correr.py --secuencial --pasos ... merida -> uno por uno (para depurar)

- Regenera notebooks/*.ipynb desde notebooks/_src/*.py (quedan limpios, sin salidas).
- Ejecuta en paralelo todo notebook cuyas dependencias ya terminaron (cada uno en su propio kernel):
      nivel 1: 00 (CP), 00b (AltScore), 00c (Rappi), 01 (hogares), 02 (DENUE)   nivel 2: 03 (<- 01, 02), 04 (<- 00, 00b, 01, 02)
      nivel 3: 05 (<- 00, 04), 07 (Whisp: share KO por hexagono; <- 00) · nivel 4: 06 (<- 00, 00b, 00c, 01, 04, 07)
- Cliente por ciudad (config.CLIENTES; las ciudades son independientes): el paso "00" es 00_cp_validacion (solo CP; las ventas ya no
  se usan desde 2026-10-05: ventas=None en todas las ciudades; 00_ventas_cp_validacion queda como histórico). Antes de correr pasos del cliente se verifica que existan el CP y AltScore
  (enrichedgeodata): si falta uno, la ciudad NO se corre (se piden al cliente).
- Si un notebook falla, no se corre nada que dependa de el; el resto sigue.
- Guarda cada notebook EJECUTADO en notebooks/ejecutados/<ciudad>/ (para revisar y depurar).
- Las descargas se reutilizan desde data/raw/<ciudad>/fuentes_oficiales (con candado: dos notebooks no bajan el mismo zip a la vez).
- Las ciudades se corren una despues de otra.
- Limite por celda: 5400 s; para un estado grande (QA Region Sur, Oaxaca) subirlo con la variable CELDA_TIMEOUT_S.
"""
import os
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import nbformat
from nbclient import NotebookClient

BASE = Path(__file__).resolve().parents[1]
NB = BASE / "notebooks"
PASOS = ["01_socioeconomico_merida", "02_tiendas_denue_merida", "03_union_tiendas_nse"]
# pasos del cliente (Bepensa, ZM Merida)
PASOS_CLIENTE = ["00_ventas_cp_validacion", "00_cp_validacion", "00b_altscore_eda", "00c_rappi_eda", "04_hexagonos_pdv",
                 "05_presentacion_pdv", "07_whisp_share", "06_letras_nse_ventas"]
DEPENDE = {                                   # notebook -> notebooks cuyas salidas necesita
    "00_ventas_cp_validacion": [],
    "00b_altscore_eda": [],
    "00c_rappi_eda": [],
    "01_socioeconomico_merida": [],
    "02_tiendas_denue_merida": [],
    "03_union_tiendas_nse": ["01_socioeconomico_merida", "02_tiendas_denue_merida"],
    "04_hexagonos_pdv": ["00_ventas_cp_validacion", "00b_altscore_eda", "01_socioeconomico_merida", "02_tiendas_denue_merida"],
    "05_presentacion_pdv": ["00_ventas_cp_validacion", "04_hexagonos_pdv"],
    "07_whisp_share": ["00_ventas_cp_validacion"],
    "06_letras_nse_ventas": ["00_ventas_cp_validacion", "00b_altscore_eda", "00c_rappi_eda", "01_socioeconomico_merida", "04_hexagonos_pdv",
                             "07_whisp_share"],
}


def config_ciudad(ciudad: str) -> dict:
    """Cliente de la ciudad desde src/config.py (sin importar config, que lee CIUDAD al cargarse)."""
    sys.path.insert(0, str(BASE / "src"))
    os.environ["CIUDAD"] = ciudad
    import importlib
    import config as C
    importlib.reload(C)
    return {"cliente": C.CLIENTES.get(ciudad), "cp": C.CLIENTE_CP, "alt": C.CLIENTE_ALTSCORE, "raw": C.CLIENTE_RAW}


def pasos_ciudad(ciudad: str, pasos: list) -> list:
    """El "00" de la ciudad: con ventas declaradas, el de ventas x CP; sin ventas, el de solo CP (alias para las dependencias)."""
    cfg = config_ciudad(ciudad)["cliente"] or {}
    sin = "00_ventas_cp_validacion" if not cfg.get("ventas") else "00_cp_validacion"
    return [n for n in pasos if n != sin]


def datos_cliente_ok(ciudad: str, pasos: list) -> bool:
    """CP y AltScore son obligatorios (usuario): sin ellos no se corre ningun paso del cliente."""
    if not any(n in PASOS_CLIENTE for n in pasos):
        return True
    cfg = config_ciudad(ciudad)
    falta = [f"CP ({cfg['cp']})" for _ in [0] if not Path(cfg["cp"]).exists()]
    falta += [f"AltScore ({cfg['alt']})" for _ in [0] if not (Path(cfg["alt"]).exists() and any(Path(cfg["alt"]).glob("*.parquet")))]
    if cfg["cliente"] is None:
        falta.insert(0, f"cliente de {ciudad} en config.CLIENTES")
    for f in falta:
        print(f"[{ciudad}] DETENIDO: falta {f}. Pedirlo al cliente; no se avanza sin él.", flush=True)
    return not falta


ALIAS, ALIAS_INV = {}, {}


def ejecutar(n: str, ciudad: str) -> str:
    t = time.time()
    nb = nbformat.read(NB / f"{n}.ipynb", 4)
    env = {**os.environ, "CIUDAD": ciudad}                 # el kernel hereda la variable; config.py la lee
    try:
        NotebookClient(nb, timeout=int(os.environ.get("CELDA_TIMEOUT_S", 5400)), kernel_name="python3", resources={"metadata": {"path": str(NB)}}).execute(env=env)
        estado = "OK"
    except Exception as e:                                  # se guarda igual, con la celda que fallo
        estado = f"FALLO: {type(e).__name__}: {str(e)[-800:]}"
    destino = NB / "ejecutados" / ciudad / f"{n}.ipynb"
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, destino)
    print(f"[{ciudad}] {n}: {estado} ({time.time() - t:.0f}s) -> {destino}", flush=True)
    return estado


def correr_ciudad(ciudad: str, pasos: list, paralelo: bool = True):
    """Ejecuta `pasos` respetando DEPENDE (solo entre los pasos pedidos: los demas se asumen ya corridos)."""
    pendientes, hechos, fallidos, en_curso = list(pasos), set(), set(), {}
    with ThreadPoolExecutor(max_workers=len(pasos) if paralelo else 1) as ex:
        while pendientes or en_curso:
            for n in list(pendientes):
                deps = [ALIAS.get(d, d) for d in DEPENDE.get(ALIAS_INV.get(n, n), [])]
                deps = [d for d in deps if d in pasos]
                if any(d in fallidos for d in deps):
                    print(f"[{ciudad}] {n}: OMITIDO (falló una dependencia: {[d for d in deps if d in fallidos]})", flush=True)
                    pendientes.remove(n); fallidos.add(n)
                elif all(d in hechos for d in deps) and (paralelo or not en_curso):
                    en_curso[ex.submit(ejecutar, n, ciudad)] = n
                    pendientes.remove(n)
            if not en_curso:
                break
            listos, _ = wait(en_curso, return_when=FIRST_COMPLETED)
            for f in listos:
                n = en_curso.pop(f)
                (hechos if f.result() == "OK" else fallidos).add(n)
    return hechos, fallidos


def main(ciudades, pasos=None, paralelo=True):
    pasos = pasos or PASOS
    for n in pasos:
        subprocess.run([sys.executable, str(BASE / "src" / "py2nb.py"), f"_src/{n}.py", f"{n}.ipynb"], cwd=NB, check=True)
    for ciudad in ciudades:
        t = time.time()
        p_ciudad = pasos_ciudad(ciudad, pasos)
        if not datos_cliente_ok(ciudad, p_ciudad):
            continue
        ALIAS.clear(); ALIAS_INV.clear()
        if "00_cp_validacion" in p_ciudad:              # las dependencias se escriben con el 00 de ventas
            ALIAS["00_ventas_cp_validacion"] = "00_cp_validacion"; ALIAS_INV["00_cp_validacion"] = "00_ventas_cp_validacion"
        hechos, fallidos = correr_ciudad(ciudad, p_ciudad, paralelo)
        print(f"[{ciudad}] listo en {time.time() - t:.0f}s | OK: {len(hechos)} | con fallo u omitidos: {sorted(fallidos) or 'ninguno'}", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    paralelo = "--secuencial" not in args
    args = [a for a in args if a != "--secuencial"]
    pasos = None
    if args[:1] == ["--pasos"]:
        pref = args[1].split(",")
        pasos = [n for p in pref for n in PASOS + PASOS_CLIENTE if n.split("_")[0] == p]
        args = args[2:]
    main(args or [os.environ.get("CIUDAD", "merida")], pasos, paralelo)
