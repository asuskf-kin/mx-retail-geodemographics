"""Prepara los 15 estados de la Region Sur para el QA 2 (estimar la 1.a letra de las 1,420 tiendas de Nielsen).

Por estado: (1) copia de la carpeta de Merida las fuentes NACIONALES (ENIGH 2024 y Encuesta Intercensal 2025, con su
descarga.json) para no bajarlas 15 veces; (2) descarga el ITER del estado y escribe qa/estados/municipios_<ENT>.json con
todos sus municipios (el notebook 01 los trata como la "ZM" del estado). Despues se corre el 01 por estado:

    uv run python qa/preparar_estados.py
    uv run python src/correr.py --pasos 01 qasur_04 qasur_07 ...
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ESTADOS = ["04", "07", "09", "12", "13", "15", "17", "20", "21", "22", "23", "27", "29", "30", "31"]
MERIDA = BASE / "data" / "raw" / "merida" / "bepensa" / "fuentes_oficiales" / "INEGI"
NACIONALES = ["enigh2024", "encuesta_intercensal_2025"]

HIJO = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/src")
import pandas as pd
import config as C
from descargas import descargar_fuente, extraer
descargar_fuente(C.FUENTES["iter"])
d = extraer(C.ARCHIVOS["iter"])
f = next(d.rglob("conjunto_de_datos_iter_*.csv"))
try:
    it = pd.read_csv(f, dtype=str, usecols=["MUN", "NOM_MUN", "LOC"], encoding="utf-8-sig")
except UnicodeDecodeError:
    it = pd.read_csv(f, dtype=str, usecols=["MUN", "NOM_MUN", "LOC"], encoding="latin-1")
it = it[(it.MUN != "000") & (it.LOC == "0000")].drop_duplicates("MUN").sort_values("MUN")
out = Path(sys.argv[1]) / "qa" / "estados" / f"municipios_{C.ENT}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(dict(zip(it.MUN, it.NOM_MUN)), ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{C.NOM_ENT}: {len(it)} municipios -> {out.name}")
"""

for e in ESTADOS:
    destino = BASE / "data" / "raw" / f"qasur_{e}" / "fuentes_oficiales" / "INEGI"
    for carpeta in NACIONALES:
        src_, dst_ = MERIDA / carpeta, destino / carpeta
        if src_.exists():
            dst_.mkdir(parents=True, exist_ok=True)
            for f in src_.iterdir():
                if (dst_ / f.name).exists():
                    continue                     # el zip, su descarga.json y lo ya extraido (no se descomprime 15 veces)
                if f.is_file():
                    shutil.copy2(f, dst_ / f.name)
                elif f.is_dir() and ".tmp" not in f.name:
                    shutil.copytree(f, dst_ / f.name, dirs_exist_ok=True)
    env = {**os.environ, "CIUDAD": f"qasur_{e}", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", HIJO, str(BASE)], env=env, capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else f"{e}: FALLO\n{r.stderr[-1500:]}", flush=True)
