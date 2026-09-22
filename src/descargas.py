"""Descarga robusta de archivos de INEGI (reanuda cuando el servidor corta la conexion)."""
from pathlib import Path
import time
import zipfile

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (analisis-geoespacial)"}


def descargar(url: str, destino: Path, intentos: int = 30, chunk: int = 1 << 20) -> Path:
    """Descarga `url` a `destino` usando HTTP Range para reanudar cortes.

    Si el archivo es un .zip, valida que abra correctamente al final.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and _zip_ok(destino):
        print(f"[ok] ya existe {destino.name}")
        return destino

    total = None
    for i in range(intentos):
        ya = destino.stat().st_size if destino.exists() else 0
        h = dict(HEADERS)
        if ya:
            h["Range"] = f"bytes={ya}-"
        try:
            with requests.get(url, headers=h, stream=True, timeout=120) as r:
                if r.status_code == 416:  # ya completo
                    break
                r.raise_for_status()
                if "text/html" in r.headers.get("Content-Type", ""):
                    raise RuntimeError(f"INEGI devolvio HTML (URL invalida?): {url}")
                if ya and r.status_code == 200:  # servidor ignoro Range
                    ya = 0
                modo = "ab" if ya else "wb"
                if "Content-Range" in r.headers:
                    total = int(r.headers["Content-Range"].split("/")[-1])
                elif r.headers.get("Content-Length"):
                    total = ya + int(r.headers["Content-Length"])
                with open(destino, modo) as f:
                    for b in r.iter_content(chunk):
                        f.write(b)
            if total is None or destino.stat().st_size >= total:
                break
        except (requests.RequestException, OSError) as e:
            print(f"  corte ({e.__class__.__name__}), reanudando en {destino.stat().st_size if destino.exists() else 0:,} bytes...")
            time.sleep(min(2 * (i + 1), 15))
    if destino.suffix.lower() == ".zip" and not _zip_ok(destino):
        raise RuntimeError(f"Zip incompleto/corrupto: {destino}")
    print(f"[ok] {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
    return destino


def _zip_ok(p: Path) -> bool:
    if p.suffix.lower() != ".zip":
        return p.stat().st_size > 0
    try:
        with zipfile.ZipFile(p) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False
