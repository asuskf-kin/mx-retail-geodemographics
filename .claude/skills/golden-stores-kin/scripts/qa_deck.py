"""QA visual de un deck: pptx → PDF (LibreOffice) → PNG por lámina + hojas de contacto de 6 láminas.

Uso:  python .claude/skills/golden-stores-kin/scripts/qa_deck.py outputs/merida/05_golden_stores_tradicional_bepensa_zm_merida.pptx [carpeta]
Luego se miran las imágenes (una por lámina y `hoja_N.png`) buscando texto desbordado, encimado o huecos.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz                      # pymupdf
from PIL import Image


def soffice():
    for c in [shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe", "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        if c and Path(c).exists():
            return c
    sys.exit("No se encontró LibreOffice (soffice).")


def main(pptx, destino=None):
    pptx = Path(pptx).resolve()
    destino = Path(destino or tempfile.mkdtemp(prefix="qa_deck_"))
    destino.mkdir(parents=True, exist_ok=True)
    copia = destino / "deck.pptx"
    shutil.copy(pptx, copia)                            # no toca el original (puede estar abierto en PowerPoint)
    subprocess.run([soffice(), "--headless", "--convert-to", "pdf", "--outdir", str(destino), str(copia)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    doc = fitz.open(destino / "deck.pdf")
    imgs = []
    for i, pag in enumerate(doc, 1):
        p = destino / f"lamina_{i:02d}.png"
        pag.get_pixmap(dpi=100).save(p)
        imgs.append(Image.open(p))
    w, h = imgs[0].size
    for k in range(0, len(imgs), 6):
        hoja = Image.new("RGB", (w * 2, h * 3), "white")
        for j, im in enumerate(imgs[k:k + 6]):
            hoja.paste(im, ((j % 2) * w, (j // 2) * h))
        hoja.save(destino / f"hoja_{k // 6 + 1}.png")
    print(f"{len(imgs)} laminas -> {destino}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
