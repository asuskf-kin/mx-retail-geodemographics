"""Instala y verifica todo lo necesario para replicar el proceso (Python + LibreOffice + datos del cliente).

Uso (desde la raíz del repo, con el Python que se va a usar como kernel):
    python .claude/skills/golden-stores-kin/scripts/instalar.py            # verifica e instala lo que falte
    python .claude/skills/golden-stores-kin/scripts/instalar.py --solo-verificar

- Instala requirements.txt en ESTE intérprete (pip). Si un kernel de Jupyter/VS Code con ese mismo Python está
  abierto, Windows bloquea archivos (p. ej. pyproj/proj.db): cierra el kernel antes de instalar.
- Registra el kernel "mx-retail-geodemographics" para elegirlo en VS Code / Jupyter.
- Verifica LibreOffice (QA visual del deck) y que existan los datos del cliente (ventas + CP).
"""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "config.py").exists())
MODULOS = {"pandas": "pandas", "numpy": "numpy", "scipy": "scipy", "sklearn": "scikit-learn", "geopandas": "geopandas",
           "pyogrio": "pyogrio", "pyproj": "pyproj", "shapely": "shapely", "h3": "h3", "pyarrow": "pyarrow", "openpyxl": "openpyxl",
           "matplotlib": "matplotlib", "requests": "requests", "pptx": "python-pptx", "fitz": "pymupdf", "nbformat": "nbformat",
           "nbclient": "nbclient", "ipykernel": "ipykernel"}


def faltantes():
    malos = []
    for mod, pkg in MODULOS.items():
        try:
            importlib.import_module(mod)
        except Exception as e:               # ImportError o DLL rota (instalación interrumpida)
            malos.append((pkg, f"{type(e).__name__}: {e}"[:120]))
    return malos


def soffice():
    for c in [shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        if c and Path(c).exists():
            return c
    return None


def main():
    solo = "--solo-verificar" in sys.argv
    print(f"Python: {sys.executable} ({sys.version.split()[0]}) | repo: {RAIZ}")
    malos = faltantes()
    if malos and not solo:
        print("Instalando requirements.txt ...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(RAIZ / "requirements.txt")])
        if r.returncode != 0:
            print("pip falló. Si el error menciona un archivo en uso, cierra los kernels de Jupyter/VS Code de este Python y repite.")
        malos = faltantes()
    for pkg, err in malos:
        print(f"  FALTA/ROTO {pkg}: {err}  -> python -m pip install --force-reinstall {pkg}")
    if not malos:
        print("Paquetes: OK")
        if not solo:
            subprocess.run([sys.executable, "-m", "ipykernel", "install", "--user", "--name", "mx-retail-geodemographics",
                            "--display-name", "Python (mx-retail-geodemographics)"], check=False)
    s = soffice()
    print(f"LibreOffice: {'OK ' + s if s else 'NO encontrado (solo se usa para el QA visual del deck: https://www.libreoffice.org/)'}")
    sys.path.insert(0, str(RAIZ / "src"))
    try:
        import config as C
        ok_v, ok_cp = bool(C.CLIENTE_VENTAS), C.CLIENTE_CP.exists()
        print(f"Datos del cliente ({C.CLIENTE}): ventas {'OK' if ok_v else 'FALTAN'} · CP {'OK' if ok_cp else 'FALTA'}")
        if not (ok_v and ok_cp):
            print(f"  -> Sin ventas y CP no se puede avanzar: pedirlos al cliente y copiarlos a {C.CLIENTE_RAW}")
    except Exception as e:
        print("No se pudo leer src/config.py:", e)
    print("Siguiente: python src/correr.py --pasos 00,01,02,03,04,05 <ciudad>")
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
