"""Convierte un script con celdas '# %%' / '# %% [markdown]' a .ipynb (sin dependencias extra)."""
import sys
from pathlib import Path

import nbformat


def convertir(py_path, ipynb_path):
    celdas, tipo, buf = [], None, []

    def cerrar():
        if tipo is None:
            return
        texto = "\n".join(buf).strip("\n")
        if tipo == "md":
            texto = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in texto.splitlines())
            celdas.append(nbformat.v4.new_markdown_cell(texto))
        elif texto:
            celdas.append(nbformat.v4.new_code_cell(texto))

    for linea in Path(py_path).read_text(encoding="utf-8").splitlines():
        if linea.startswith("# %%"):
            cerrar()
            tipo, buf = ("md" if "[markdown]" in linea else "code"), []
        else:
            buf.append(linea)
    cerrar()
    nb = nbformat.v4.new_notebook(cells=celdas)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbformat.write(nb, ipynb_path)


if __name__ == "__main__":
    convertir(sys.argv[1], sys.argv[2])
