"""Descarga robusta de archivos de INEGI (reanuda cuando el servidor corta la conexion)."""
from contextlib import contextmanager
from pathlib import Path
import os
import shutil
import time
import zipfile

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (analisis-geoespacial)"}


@contextmanager
def _candado(ruta: Path, espera_max_s: int = 3 * 3600):
    """Candado entre procesos (archivo <ruta>.lock creado de forma atomica): notebooks en paralelo no bajan ni
    descomprimen el mismo archivo a la vez. Un candado de mas de `espera_max_s` se considera huerfano y se borra."""
    lock = Path(f"{ruta}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode()); os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > espera_max_s:
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            time.sleep(2)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def descargar(url: str, destino: Path, intentos: int = 30, chunk: int = 1 << 20) -> Path:
    """Descarga `url` a `destino` usando HTTP Range para reanudar cortes (con candado entre procesos).

    Si el archivo es un .zip, valida que abra correctamente al final.
    """
    with _candado(destino):
        return _descargar(url, Path(destino), intentos, chunk)


def _descargar(url: str, destino: Path, intentos: int, chunk: int) -> Path:
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


def extraer(zip_path: Path, destino: Path) -> Path:
    """Descomprime `zip_path` en `destino` una sola vez (si la carpeta ya existe, la reutiliza).

    Descomprime en una carpeta temporal y la renombra al final: nunca queda una carpeta a medias, y con el candado
    dos notebooks en paralelo no descomprimen lo mismo a la vez.
    """
    destino = Path(destino)
    with _candado(destino):
        if not destino.exists():
            tmp = destino.with_name(destino.name + f".tmp{os.getpid()}")
            shutil.rmtree(tmp, ignore_errors=True)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(tmp)
            os.replace(tmp, destino)
    return destino


def requisitos(archivos: dict):
    """Falla con un mensaje claro si falta algun archivo previo. `archivos` = {ruta: notebook que la genera}."""
    faltan = {str(p): nb for p, nb in archivos.items() if not Path(p).exists()}
    if faltan:
        detalle = "\n".join(f"  - {p}  → corre primero {nb}" for p, nb in faltan.items())
        raise FileNotFoundError(f"Faltan archivos previos:\n{detalle}")
    print(f"Requisitos OK ({len(archivos)} archivos).")


def _ciudad():
    """ZM activa segun config (CIUDAD / env var CIUDAD)."""
    try:
        import config
        return config.ZM_NOMBRE
    except ImportError:
        return ""


def verificar_fuentes(fuentes: dict, claves=None):
    """HEAD a cada URL de `fuentes` (dict de config.FUENTES). Devuelve un DataFrame con lo que responde INEGI."""
    import pandas as pd
    filas = []
    for k in claves or fuentes:
        f = fuentes[k]
        try:
            r = requests.head(f["url"], headers=HEADERS, timeout=60, allow_redirects=True)
            tipo, mb = r.headers.get("Content-Type", ""), int(r.headers.get("Content-Length", 0)) / 1e6
            estado = "OK" if r.ok and "html" not in tipo else f"REVISAR ({r.status_code}, {tipo})"
            modif = r.headers.get("Last-Modified", "")
        except requests.RequestException as e:
            estado, tipo, mb, modif = f"ERROR {type(e).__name__}", "", 0, ""
        filas.append({"fuente": k, "ciudad": _ciudad(), "cobertura": f.get("cobertura", ""),
                      "nombre": f["nombre"], "edición": f["edicion"], "estado": estado,
                      "MB": round(mb, 1), "última modificación (servidor)": modif,
                      "página oficial": f["pagina"], "url de descarga": f["url"]})
    return pd.DataFrame(filas).set_index("fuente")


def registrar_fuentes(fuentes: dict, claves, destino: Path, extra: dict | None = None):
    """Guarda en `destino` (csv) que archivo local se uso de cada fuente: url, edicion, tamano, fecha y sha256.

    Sirve para depurar: los zips de data/raw no se vuelven a descargar, y este registro dice exactamente
    con cual version de cada fuente se genero cada salida.
    """
    import datetime as dt
    import hashlib
    import pandas as pd
    filas = []
    for k in claves:
        f = fuentes[k]
        p = Path(f["archivo"])
        sha = hashlib.sha256()
        with open(p, "rb") as fh:
            for bloque in iter(lambda: fh.read(1 << 20), b""):
                sha.update(bloque)
        filas.append({"fuente": k, "ciudad": _ciudad(), "cobertura": f.get("cobertura", ""),
                      "nombre": f["nombre"], "edicion": f["edicion"], "url": f["url"],
                      "pagina_oficial": f["pagina"], "archivo_local": str(p), "bytes": p.stat().st_size,
                      "descargado": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                      "sha256": sha.hexdigest(), **(extra or {}).get(k, {})})
    df = pd.DataFrame(filas)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, encoding="utf-8-sig")
    return df
