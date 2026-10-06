"""Corre los QA contra Nielsen de una ciudad y guarda los notebooks ejecutados en su carpeta de qa/.

    uv run python qa/correr_qa.py guadalajara            # qa_linea_base_nielsen → qa2_primera_letra → qa (consistencia interna)
    uv run python qa/correr_qa.py merida --pasos qa1

Regenera qa/*.ipynb desde qa/_src/*.py (qa.ipynb no tiene _src) y deja los ejecutados en qa/<carpeta>/ejecutados/.
El QA 2 lee los resultados del QA 1, por eso van en orden.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

QA = Path(__file__).resolve().parent
sys.path.insert(0, str(QA.parent / "src"))
from py2nb import convertir  # noqa: E402

CARPETA = {"merida": "Bepensa", "guadalajara": "Guadalajara"}
PASOS = {"qa1": "qa_linea_base_nielsen", "qa2": "qa2_primera_letra", "interno": "qa"}

ap = argparse.ArgumentParser()
ap.add_argument("ciudad", choices=CARPETA)
ap.add_argument("--pasos", default="qa1,qa2,interno")
a = ap.parse_args()
fallos = 0
for p in a.pasos.split(","):
    n = PASOS[p]
    if (QA / "_src" / f"{n}.py").exists():
        convertir(QA / "_src" / f"{n}.py", QA / f"{n}.ipynb")
    t, nb = time.time(), nbformat.read(QA / f"{n}.ipynb", 4)
    try:
        NotebookClient(nb, timeout=5400, kernel_name="python3", resources={"metadata": {"path": str(QA)}}).execute(
            env={**os.environ, "CIUDAD": a.ciudad, "PYTHONIOENCODING": "utf-8"})
        estado = "OK"
    except Exception as e:                                  # se guarda igual, con la celda que falló
        estado, fallos = f"FALLO: {type(e).__name__}: {str(e)[-1500:]}", fallos + 1
    destino = QA / CARPETA[a.ciudad] / "ejecutados" / f"{n}.ipynb"
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, destino)
    print(f"[{a.ciudad}] {n}: {estado} ({time.time() - t:.0f}s) -> {destino.relative_to(QA.parent)}", flush=True)
sys.exit(fallos)
