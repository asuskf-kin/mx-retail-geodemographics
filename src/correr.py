"""Corre los notebooks por ciudad, en paralelo cuando sus dependencias lo permiten.

Uso (desde la raiz del repo):
    python src/correr.py merida guadalajara              -> pipeline 01-03 de cada ciudad
    python src/correr.py --pasos 00,01,02,03,04 merida   -> los notebooks indicados (Bepensa)
    python src/correr.py --secuencial --pasos ... merida -> uno por uno (para depurar)

- Regenera notebooks/*.ipynb desde notebooks/_src/*.py (quedan limpios, sin salidas).
- Ejecuta en paralelo todo notebook cuyas dependencias ya terminaron (cada uno en su propio kernel):
      nivel 1: 00 (ventas x CP), 01 (hogares), 02 (DENUE)   nivel 2: 03 (<- 01, 02), 04 (<- 00, 01, 02)   nivel 3: 05 (<- 00, 04)
- Si un notebook falla, no se corre nada que dependa de el; el resto sigue.
- Guarda cada notebook EJECUTADO en notebooks/ejecutados/<ciudad>/ (para revisar y depurar).
- Las descargas se reutilizan desde data/raw (con candado: dos notebooks no bajan el mismo zip a la vez).
- Las ciudades se corren una despues de otra (comparten descargas como la ENIGH).
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
PASOS_CLIENTE = ["00_ventas_cp_validacion", "04_hexagonos_pdv", "05_presentacion_pdv"]
DEPENDE = {                                   # notebook -> notebooks cuyas salidas necesita
    "00_ventas_cp_validacion": [],
    "01_socioeconomico_merida": [],
    "02_tiendas_denue_merida": [],
    "03_union_tiendas_nse": ["01_socioeconomico_merida", "02_tiendas_denue_merida"],
    "04_hexagonos_pdv": ["00_ventas_cp_validacion", "01_socioeconomico_merida", "02_tiendas_denue_merida"],
    "05_presentacion_pdv": ["00_ventas_cp_validacion", "04_hexagonos_pdv"],
}


def ejecutar(n: str, ciudad: str) -> str:
    t = time.time()
    nb = nbformat.read(NB / f"{n}.ipynb", 4)
    env = {**os.environ, "CIUDAD": ciudad}                 # el kernel hereda la variable; config.py la lee
    try:
        NotebookClient(nb, timeout=5400, kernel_name="python3", resources={"metadata": {"path": str(NB)}}).execute(env=env)
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
                deps = [d for d in DEPENDE.get(n, []) if d in pasos]
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
        hechos, fallidos = correr_ciudad(ciudad, pasos, paralelo)
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
