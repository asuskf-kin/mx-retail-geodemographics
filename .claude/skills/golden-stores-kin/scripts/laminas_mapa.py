"""Láminas 1920×1080 (marca Kin) que explican el mapa interactivo del 06 y el diccionario de datos, para pegar en un deck.

Uso (desde la raíz del repo):
    uv run python .claude/skills/golden-stores-kin/scripts/laminas_mapa.py [--pos 2720] [--ciudad merida] [--cliente bepensa]

Lee el mapa `outputs/<ciudad>/<cliente>/06_mapa_qa_letras_<cliente>_zm_<ciudad>.html` y el diccionario
`cliente/06_diccionario_letras_<cliente>_zm_<ciudad>.xlsx` (los escribe el 06) y deja en `cliente/laminas/`:
  01_como_leer_el_mapa.png · 02_ficha_del_pdv.png · 03-05_diccionario_<i>_de_3.png   (láminas completas)
  figuras/mapa_numerado.png · figuras/ficha_numerada.png · figuras/diccionario_<i>.png  (solo la figura, para Claude Design)
Captura con Chrome sin interfaz: los números se dibujan DENTRO del mapa (Leaflet), así no hay coordenadas a mano. El fondo de calles
(OpenFreeMap, WebGL) no se dibuja sin interfaz: las figuras salen sobre fondo liso.
--pos: PDV de ejemplo (conviene uno con tienda Rappi a 300 m y varios PDV en su clúster: Bepensa 2720 El Buen Trato, HH · P1).
"""
import argparse
import base64
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from PIL import Image

RAIZ = next(p for p in [Path.cwd(), *Path(__file__).resolve().parents] if (p / "src" / "config.py").exists())
sys.path.insert(0, str(RAIZ / "src"))
import mapas as MP  # noqa: E402  (tokens, fuentes y colores de dato del mapa)

CHROMES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
           "/usr/bin/google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]

ANOTA_MAPA = r"""<style>#panel,#leyenda,#ayuda,.leaflet-control-container{display:none!important}
.kn{width:34px;height:34px;border-radius:50%;background:#141417;color:#e5ff01;font:700 19px 'Space Grotesk',sans-serif;
 display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 2px #fff}</style><script>
setTimeout(() => {
  const i = D.pasos.findIndex(p => p.titulo.startsWith('3. Letras finales')); activar(i >= 0 ? i : 0);
  const r = DS.pdv.find(p => String(p.id) === '__POS__'); const cc = h3.cellToLatLng(r.cl);
  mapa.invalidateSize(); seleccionar('pdv', r); mapa.closePopup();      // la ficha mueve el mapa (autopan): se centra después
  mapa.setView([(r.lat + cc[0]) / 2, (r.lon + cc[1]) / 2], 17, {animate: false});
  const d = p => mapa.distance([p.lat, p.lon], [r.lat, r.lon]);
  const ven = (DS.bepensa || DS.pdv).filter(p => p.id !== r.id && h3.latLngToCell(p.lat, p.lon, 9) !== r.cl && d(p) <= D.radio);
  const rap = (DS.rappi || []).filter(p => d(p) <= D.radio);
  const fuera = DS.pdv.filter(p => d(p) > D.radio * 1.15 && d(p) < D.radio * 1.8);
  const mie = DS.pdv.filter(p => p.cl === r.cl && p.id !== r.id);
  const oeste = [r.lat + D.radio / 111320, r.lon];   // borde norte del buffer (zona despejada)
  const puntos = [[1, [r.lat, r.lon]], [2, h3.cellToBoundary(r.cl)[1]], [3, cc], [4, mie[0] && [mie[0].lat, mie[0].lon]],
                  [5, oeste], [6, ven[0] && [ven[0].lat, ven[0].lon]], [7, rap[0] && [rap[0].lat, rap[0].lon]], [8, fuera[0] && [fuera[0].lat, fuera[0].lon]]];
  puntos.filter(p => p[1]).forEach(([n, ll]) => L.marker(ll, {interactive: false, icon: L.divIcon({className: '', html: '<div class="kn">' + n + '</div>',
    iconSize: [34, 34], iconAnchor: [-8, 42]})}).addTo(sel));
  document.body.dataset.sinRappi = rap.length ? '' : '1';
}, 800);
</script></body>"""

ANOTA_FICHA = r"""<style>#solo{position:fixed;left:0;top:0;width:620px;bottom:0;box-sizing:border-box;background:#fff;padding:16px 80px 16px 20px;z-index:99999;
 font-size:var(--ka-size-caption)} #solo .ficha-wrap{max-height:none;overflow:visible} #solo .dist-tit{white-space:normal}
.llave{position:absolute;right:46px;width:16px;border:3px solid #141417;border-left:0;border-radius:0 7px 7px 0}
.llave b{position:absolute;left:24px;top:50%;transform:translateY(-50%);width:30px;height:30px;border-radius:50%;background:#141417;color:#e5ff01;
 font:700 17px 'Space Grotesk',sans-serif;display:flex;align-items:center;justify-content:center}</style><script>
setTimeout(() => {
  const r = DS.pdv.find(p => String(p.id) === '__POS__'); seleccionar('pdv', r);
  const s = document.createElement('div'); s.id = 'solo'; s.innerHTML = document.querySelector('.leaflet-popup-content').innerHTML;
  document.body.appendChild(s); mapa.closePopup();
  const filas = [...s.querySelectorAll('.ficha tr')], y = el => el.getBoundingClientRect();
  const fila = t => filas.find(f => f.firstChild.textContent.startsWith(t));
  const tramos = [[s.querySelector('.ficha-cab'), s.querySelector('.chips')], [s.querySelector('.dist-tit'), s.querySelector('.dist-lab')],
    [filas[0], fila('Hogares del clúster')], [fila('NSE del punto'), fila('NSE confirmado')], [fila('V venta media'), fila('Letra 2 con Rappi')],
    [fila('Letras base'), filas[filas.length - 1]], [s.querySelector('.nota'), s.querySelector('.nota')]];
  tramos.forEach(([a, b], k) => { if (!a || !b) return; const t = y(a).top - 2, h = y(b).bottom + 2 - t;
    const l = document.createElement('div'); l.className = 'llave'; l.style.top = t + 'px'; l.style.height = h + 'px'; l.innerHTML = '<b>' + (k + 1) + '</b>'; s.appendChild(l); });
}, 800);
</script></body>"""


def chrome():
    for c in CHROMES:
        if Path(c).exists():
            return c
    raise SystemExit("No encontré Chrome ni Edge: instala uno o ajusta CHROMES.")


def captura(html, png, ancho, alto, tmp):
    f = tmp / (png.stem + ".html"); f.write_text(html, encoding="utf-8")
    subprocess.run([chrome(), "--headless=new", "--hide-scrollbars", f"--window-size={ancho},{alto}", "--virtual-time-budget=20000",
                    f"--screenshot={png}", f.as_uri()], capture_output=True)
    return Image.open(png)


def recorta_blanco(img, margen=6):
    g = img.convert("L").point(lambda v: 0 if v > 245 else 255); caja = g.getbbox()
    return img.crop((max(caja[0] - margen, 0), max(caja[1] - margen, 0), min(caja[2] + margen, img.width), min(caja[3] + margen, img.height))) if caja else img


def uri(img):
    b = io.BytesIO(); img.save(b, "PNG"); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pos", default="2720"); ap.add_argument("--ciudad", default="merida"); ap.add_argument("--cliente", default="bepensa")
    a = ap.parse_args()
    base = RAIZ / "outputs" / a.ciudad / a.cliente
    mapa = base / f"06_mapa_qa_letras_{a.cliente}_zm_{a.ciudad}.html"
    dicc = base / "cliente" / f"06_diccionario_letras_{a.cliente}_zm_{a.ciudad}.xlsx"
    for f in (mapa, dicc):
        if not f.exists():
            raise SystemExit(f"Falta {f}: corre el notebook 06.")
    out = base / "cliente" / "laminas"; fig = out / "figuras"; tmp = out / "_tmp"
    for d in (out, fig, tmp):
        d.mkdir(parents=True, exist_ok=True)
    h = mapa.read_text(encoding="utf-8")
    # figuras numeradas (dibujadas por el propio mapa)
    m = captura(h.replace("</body>", ANOTA_MAPA.replace("__POS__", a.pos), 1), tmp / "mapa.png", 1100, 820, tmp)
    m.save(fig / "mapa_numerado.png")
    f_ = recorta_blanco(captura(h.replace("</body>", ANOTA_FICHA.replace("__POS__", a.pos), 1), tmp / "ficha.png", 620, 1100, tmp))
    f_.save(fig / "ficha_numerada.png")

    M = MP._marca()
    logo = "data:image/svg+xml;base64," + base64.b64encode((MP.MARCA / "logos/formal/Kin_Logo_FV_13.svg").read_bytes()).decode()
    css = M["css"] + """*{box-sizing:border-box;margin:0;padding:0}body{width:1920px;height:1080px;overflow:hidden;background:var(--ka-color-white);
 color:var(--ka-color-black);font-family:var(--ka-font-body)}.lam{position:relative;width:1920px;height:1080px;padding:96px 112px 140px}
.eyebrow{font-weight:600;font-size:22px;letter-spacing:.12em;text-transform:uppercase;color:var(--ka-color-gray-3)}
h1{font-family:var(--ka-font-display);font-weight:700;font-size:48px;line-height:1.08;letter-spacing:-.02em;margin:10px 0 26px}
.pie{position:absolute;left:56px;right:56px;bottom:36px;display:flex;justify-content:space-between;align-items:center}.pie img{height:46px}
.pie span{font-weight:500;font-size:24px;color:var(--ka-color-gray-3)}.cols{display:flex;gap:44px}.lista{display:flex;flex-direction:column;gap:16px;flex:1}
.it{display:flex;gap:14px}.num{width:40px;height:40px;border-radius:50%;background:var(--ka-color-black);color:var(--ka-color-yellow);flex:none;
 font-family:var(--ka-font-display);font-weight:700;font-size:21px;display:flex;align-items:center;justify-content:center}
.it b{font-family:var(--ka-font-display);font-size:24px;display:block}.it p{font-size:19px;line-height:1.35;color:var(--ka-color-gray-4)}
.fig{border-radius:12px;box-shadow:0 0 0 1px var(--ka-color-gray-2);object-fit:contain}
table{width:100%;border-collapse:collapse;font-size:18px}th{text-align:left;font-family:var(--ka-font-display);font-size:19px;background:var(--ka-color-black);
 color:var(--ka-color-white);padding:10px 14px}td{padding:8px 14px;border-bottom:1px solid var(--ka-color-gray-1);vertical-align:top;line-height:1.3}
td.n{color:var(--ka-color-gray-3);width:46px}td.c{font-weight:600;width:460px}td.u{width:130px;color:var(--ka-color-gray-4)}"""

    def lamina(nombre, cuerpo):
        html = f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{css}</style></head><body><div class='lam'>{cuerpo}" \
               f"<div class='pie'><img src='{logo}' alt='Kin Analytics'><span>kinanalytics.com</span></div></div></body></html>"
        captura(html, out / f"{nombre}.png", 1920, 1080, tmp)
        print("lámina:", out / f"{nombre}.png")

    C = MP.COLOR_CLUSTER
    letras = " ".join(f"<span style='color:{C[k]}'>●</span> {k} · {p} · {ac}" for k, p, ac in
                      [("HH", "P1", "Atacar"), ("HL", "P2", "Bloquear"), ("LH", "P3", "Fortalecer"), ("LL", "P4", "Mantener")])
    it = lambda n, t, d: f"<div class='it'><div class='num'>{n}</div><div><b>{t}</b><p>{d}</p></div></div>"
    items1 = [("PDV seleccionado", "Anillo amarillo: la tienda que se consulta."),
              ("Clúster NSE (hexágono H3 res 9)", "Sus tiendas comparten la Letra 1 (demanda)."),
              ("Centro del clúster", "Los hogares a 300 m de este punto dan el NSE del clúster."),
              ("PDV del mismo clúster", "Anillo azul: misma Letra 1 que la tienda seleccionada."),
              ("Buffer de 300 m de la tienda", "Círculo punteado: de aquí sale su variable Rappi."),
              ("PDV con venta en el buffer", "Anillo negro: vecinos de la red (referencia)."),
              ("Tienda Rappi en el buffer", "Anillo rojo: sus pedidos de sueros alimentan la Letra 2."),
              ("Punto de color = un PDV Tradicional", "El color son sus letras finales: " + letras)]
    w1 = round(m.width * 680 / m.height)
    lamina("01_como_leer_el_mapa", "<div class='eyebrow'>Mapa · cómo leerlo</div><h1>Cada punto es una tienda; al elegir una se dibujan su clúster NSE y su buffer de 300 m</h1>"
           f"<div class='cols'><img class='fig' src='{uri(m)}' style='width:{w1}px;height:680px'><div class='lista'>"
           + "".join(it(i + 1, t, d) for i, (t, d) in enumerate(items1)) + "</div></div>")
    items2 = [("Encabezado", "Nombre, pos_id y etiquetas: letras finales, prioridad, acción Golden Stores y subcanal."),
              ("Hogares por NSE del clúster", "Reparto de los hogares a 300 m del centro: bajo (D+, D/E) · medio (C, C−) · alto (C+, A/B)."),
              ("Punto de venta y clúster", "Identificación, hexágono H3 res 9, tiendas que lo comparten, distancia al centro y hogares."),
              ("Demanda · Letra 1", "NSE de INEGI, validación con el Censo, AltScore y nivel final → Letra 1."),
              ("Venta · Letra 2", "Venta media y potencial del CP, Rappi del buffer, rangos y score 2·2·1 → H si < 0.4."),
              ("Resultado", "Letras base (INEGI + CP), letras finales, prioridad P1–P4, acción y clase CP."),
              ("Qué se dibuja", "Notas del mapa: el clúster, el buffer y las tiendas Rappi.")]
    w2 = round(f_.width * 740 / f_.height)
    lamina("02_ficha_del_pdv", "<div class='eyebrow'>Mapa · la ficha de cada tienda</div><h1>La ficha cuenta la historia completa: demanda, venta, letras y prioridad</h1>"
           f"<div class='cols'><img class='fig' src='{uri(f_)}' style='width:{w2}px;height:740px'><div class='lista' style='gap:22px'>"
           + "".join(it(i + 1, t, d) for i, (t, d) in enumerate(items2)) + "</div></div>")
    d = pd.read_excel(dicc, header=3)[["#", "columna", "definición", "unidad o valores"]].dropna(subset=["columna"])
    n3 = -(-len(d) // 3)
    for i, k in enumerate(range(0, len(d), n3), 1):
        filas = "".join(f"<tr><td class='n'>{int(r['#'])}</td><td class='c'>{r['columna']}</td><td>{r['definición']}</td><td class='u'>{r['unidad o valores']}</td></tr>"
                        for _, r in d.iloc[k:k + n3].iterrows())
        nombre = f"0{2 + i}_diccionario_{i}_de_3"
        lamina(nombre, f"<div class='eyebrow'>Diccionario de datos · {i} de 3</div><h1>Qué significa cada columna del Excel de letras y de la ficha del mapa</h1>"
               f"<table><tr><th>#</th><th>Columna</th><th>Definición</th><th>Unidad</th></tr>{filas}</table>")
        recorta_blanco(Image.open(out / f"{nombre}.png").crop((100, 190, 1820, 960))).save(fig / f"diccionario_{i}.png")
    shutil.rmtree(tmp, ignore_errors=True)
    print("figuras para Claude Design:", fig)


if __name__ == "__main__":
    main()
