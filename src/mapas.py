"""Mapas de QA del notebook 06: fondo para mapas estáticos (matplotlib) y mapa interactivo en HTML.

El HTML lleva la marca Kin (skill brand-guidelines-kin: tokens, fuentes embebidas y logo desde archivo) y usa Leaflet y h3-js desde CDN y un fondo libre con datos de OpenStreetMap: OpenFreeMap (estilo gris "Positron",
teselas vectoriales dibujadas con MapLibre). No pide API key ni Referer, así que también funciona al abrir el archivo con doble
clic (file://); los servidores de tile.openstreetmap.org bloquean esas peticiones con 403. Se abre en cualquier navegador con
internet, no hay que instalar nada. Tiene un panel con los **pasos del QA**: cada paso enciende sus capas y explica qué
se hace, por qué y con qué fórmula; un **filtro** opcional por campo (p. ej. subcanal) y búsqueda. Clic en un punto de venta:
dibuja su radio de 300 m, marca los PDV y las tiendas Rappi que quedan dentro y muestra su ficha con los valores de las
fórmulas; con `cluster`, también su **clúster NSE** (el hexágono H3 que lo contiene, el buffer de 300 m desde su centro y los PDV
que lo comparten). Clic en un hexágono de clúster: su ficha y sus PDV. Los hexágonos viajan como id H3 (el navegador dibuja el
polígono), así el archivo pesa poco.
El HTML lleva datos del cliente: se guarda en outputs/ (fuera de git) y no se publica.
"""
import base64
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import eda

# escalas de color (paleta de eda / skill dataviz): secuencial para niveles, categórica para letras y clústeres
SECUENCIAL = ["#fbe9d6", "#f6c08f", "#eb8a4f", "#c65a2e", "#7d3a1f"]   # NSE bajo → alto (naranja → café)
AZULES = ["#e7eef8", "#b9cfee", "#7eaae3", "#2a78d6", "#154a8a"]
COLOR_L1 = {"H": "#2a78d6", "L": "#eda100"}                        # NSE alto / bajo
COLOR_L2 = {"H": "#1baf7a", "L": "#e34948"}                        # venta alta / baja
COLOR_CLUSTER = {"HH": "#0a0a0a", "HL": "#2a78d6", "LH": "#1baf7a", "LL": "#b0aea5"}
COLOR_NSE3 = {"bajo": "#eda100", "medio": "#a39e93", "alto": "#2a78d6"}      # NSE bajo / medio / alto (mismos tonos que la Letra 1)


def fondo(ax, municipios, agebs=None):
    """Fondo de mapa estático: AGEB urbanas en gris claro y límite municipal."""
    if agebs is not None:
        agebs.plot(ax=ax, color=eda.GRID, edgecolor=eda.FONDO, lw=0.3)
    municipios.boundary.plot(ax=ax, color=eda.TINTA_2, lw=0.8)
    ax.set_axis_off()


def encuadre(ax, x, y, radio):
    """Acerca el mapa a un círculo de `radio` (unidades del CRS) alrededor de (x, y)."""
    ax.set_xlim(x - radio, x + radio)
    ax.set_ylim(y - radio, y + radio)


def _limpio(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def tabla_js(df: pd.DataFrame) -> dict:
    """DataFrame → {'campos': [...], 'filas': [[...], ...]} con NaN → null (JSON válido y compacto)."""
    return {"campos": [str(c) for c in df.columns], "filas": [[_limpio(v) for v in fila] for fila in df.itertuples(index=False)]}


def mapa_html(ruta, titulo, subtitulo, centro, datasets, capas, pasos, popup, hexagonos=None, poligonos=None, radio_m=300, zoom=12,
              filtro=None, distribucion_popup=None, cluster=None, resoluciones=None, buscar_placeholder=None):
    """Escribe el mapa interactivo.

    datasets = {nombre: DataFrame con columnas lat, lon, ...}; hexagonos = DataFrame indexado por id H3, o {fuente: DataFrame}
    (una capa hex elige la suya con "fuente"; con "borde" dibuja el contorno, con "extra" = [[etiqueta, campo], ...] agrega
    líneas al tooltip y con "seleccion" = dataset, el clic en el hexágono abre la ficha de su fila en ese dataset);
    poligonos = {nombre: GeoDataFrame en EPSG:4326}; capas = lista de dicts (id, nombre, tipo = hex | poligonos | puntos |
    circulos, campo, escala, ...); pasos = lista de dicts (titulo, que, porque, formula, capas); popup = {dataset: [(etiqueta, campo)]};
    filtro = {dataset, campo, valores, etiqueta}: casillas en el panel (p. ej. subcanal) que filtran los puntos.
    cluster = {dataset, campo, miembros}: el campo con el id H3 del clúster NSE de cada fila; al seleccionar una fila se dibujan
    su hexágono, el buffer de radio_m desde su centro y las filas de `miembros` con el mismo id.
    resoluciones = {etiqueta, valores: [{valor, etiqueta, n}], defecto}: chips para elegir la resolución H3; una capa con "res" se ve
    solo en su resolución y su tooltip muestra el id del hexágono, que también se puede buscar (versión KO del 06).
    Una capa hex o poligonos con "distribucion" = [[etiqueta, campo, color], ...] (campos en %) muestra en su tooltip una barra
    apilada con esos %; distribucion_popup = {dataset: {"titulo", "partes": [[etiqueta, campo, color], ...]}} la pone arriba de la
    ficha al hacer clic en un punto.
    """
    datos = {"titulo": titulo, "subtitulo": subtitulo, "centro": list(centro), "zoom": zoom, "radio": radio_m,
             "datasets": {k: tabla_js(v) for k, v in datasets.items()}, "capas": capas, "pasos": pasos, "popup": popup,
             "hex": {}, "poligonos": {}, "filtro": filtro, "dist_popup": distribucion_popup or {}, "cluster": cluster,
             "resoluciones": resoluciones, "buscar_placeholder": buscar_placeholder}
    hexs = {"hex": hexagonos} if isinstance(hexagonos, pd.DataFrame) else (hexagonos or {})
    for k, hx in hexs.items():
        datos["hex"][k] = {"campos": list(hx.columns), "filas": {h: [_limpio(v) for v in fila] for h, fila in
                                                                zip(hx.index, hx.itertuples(index=False))}}
    for k, g in (poligonos or {}).items():
        datos["poligonos"][k] = json.loads(g.to_json(drop_id=True))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(pagina(datos))
    return ruta


def pagina(datos: dict) -> str:
    """HTML del mapa con la plantilla vigente para un dict de datos ya armado (lo reusa version_ko.py con el D de un mapa existente)."""
    js = json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=_limpio).replace("</", "<\\/")
    m = _marca()
    return (_PLANTILLA.replace("__MARCA_CSS__", m["css"]).replace("__LOGO__", m["logo"]).replace("__FAVICON__", m["favicon"])
            .replace("__TITULO__", html.escape(datos["titulo"])).replace("__DATOS__", js))


MARCA = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "brand-guidelines-kin" / "assets"   # skill brand-guidelines-kin


def _marca() -> dict:
    """Marca Kin para el HTML: tokens de color y tipo, Space Grotesk + Albert Sans embebidas (base64) y logo/favicon desde archivo."""
    b64 = lambda f: base64.b64encode((MARCA / f).read_bytes()).decode()
    css = (MARCA / "tokens" / "colors_and_type.css").read_text(encoding="utf-8")
    css += ("\n@font-face{font-family:'Space Grotesk';src:url('data:font/woff2;base64," + b64("fonts/space-grotesk.woff2") +
            "') format('woff2');font-weight:300 700;font-style:normal}"
            "\n@font-face{font-family:'Albert Sans';src:url('data:font/woff2;base64," + b64("fonts/albert-sans.woff2") +
            "') format('woff2');font-weight:100 900;font-style:normal}\n")
    return {"css": css, "logo": "data:image/svg+xml;base64," + b64("logos/informal/Kin_Logo_IV_19.svg"),     # fondo oscuro: blanco + hex amarillo
            "favicon": "data:image/svg+xml;base64," + b64("logos/symbol/Kin_Logo_S_14.svg")}


_PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<link rel="icon" href="__FAVICON__">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js"></script>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.9.0/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@5.9.0/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js"></script>
<style>
__MARCA_CSS__
/* ---- mapa con la marca Kin (tokens de la skill brand-guidelines-kin; los colores de dato vienen de src/mapas.py) ---- */
:root{--esp-1:.25rem;--esp-2:.5rem;--esp-3:.75rem;--esp-4:1rem;--esp-5:1.5rem;--panel:24rem}
*{box-sizing:border-box}
html,body{margin:0;height:100%;font-family:var(--ka-font-body);font-size:var(--ka-size-body);color:var(--ka-color-text-primary);background:var(--ka-color-bg-layout)}
#app{display:flex;height:100%}
#panel{width:var(--panel);min-width:18rem;display:flex;flex-direction:column;background:var(--ka-color-surface);border-right:1px solid var(--ka-color-border)}
#cabeza{background:var(--ka-color-black);color:var(--ka-color-white);padding:var(--esp-4) var(--esp-4) var(--esp-4);border-bottom:3px solid var(--ka-color-yellow)}
#cabeza .logo{height:1.6rem;width:auto;display:block;margin-bottom:var(--esp-3)}
.eyebrow{font-family:var(--ka-font-body);font-weight:var(--ka-weight-semibold);font-size:var(--ka-size-overline);letter-spacing:var(--ka-tracking-eyebrow);text-transform:uppercase;color:var(--ka-color-gray-3)}
#cabeza .eyebrow{color:var(--ka-color-yellow)}
h1{font-family:var(--ka-font-display);font-weight:var(--ka-weight-bold);font-size:var(--ka-size-h3);line-height:var(--ka-lh-tight);margin:var(--esp-1) 0 var(--esp-2)}
.sub{color:var(--ka-color-gray-2);font-size:var(--ka-size-caption);line-height:1.4}
#cuerpo{flex:1;overflow-y:auto;padding:var(--esp-4)}
.bloque{margin-bottom:var(--esp-4)}.bloque>.eyebrow{display:block;margin-bottom:var(--esp-2)}
#filtro,#resol,#vista{display:flex;flex-wrap:wrap;gap:var(--esp-2)}
#filtro label,#resol label,#vista label{display:inline-flex;align-items:center;gap:var(--esp-1);padding:var(--esp-1) var(--esp-3);border:1px solid var(--ka-color-border);border-radius:var(--ka-radius-pill);
 font-size:var(--ka-size-caption);cursor:pointer;user-select:none;background:var(--ka-color-surface)}
#filtro label.on,#resol label.on,#vista label.on{background:var(--ka-color-black);color:var(--ka-color-white);border-color:var(--ka-color-black)}
#filtro input,#resol input,#vista input{display:none}#filtro .n,#resol .n,#vista .n{color:var(--ka-color-gray-3)}
#buscar{width:100%;padding:var(--esp-2) var(--esp-3);border:1px solid var(--ka-color-border);border-radius:var(--ka-radius-box);font:inherit;font-size:var(--ka-size-caption)}
#buscar:focus{outline:2px solid var(--ka-color-black);outline-offset:1px}
#res{margin-top:var(--esp-1)}#res div{padding:var(--esp-2) var(--esp-3);cursor:pointer;font-size:var(--ka-size-caption);border-radius:var(--ka-radius-base)}
#res div:hover,#res div.on{background:var(--ka-color-gray-1)}#res .vacio{color:var(--ka-color-gray-3);cursor:default}
.pasos{display:flex;flex-direction:column;gap:var(--esp-1)}
.pasos button{display:flex;gap:var(--esp-3);align-items:baseline;width:100%;text-align:left;border:1px solid var(--ka-color-border);background:var(--ka-color-surface);
 padding:var(--esp-2) var(--esp-3);border-radius:var(--ka-radius-box);cursor:pointer;font:inherit;font-size:var(--ka-size-caption);color:var(--ka-color-text-primary)}
.pasos button .num{font-family:var(--ka-font-display);font-weight:var(--ka-weight-bold);color:var(--ka-color-gray-3)}
.pasos button:hover{border-color:var(--ka-color-black)}
.pasos button.on{background:var(--ka-color-black);color:var(--ka-color-white);border-color:var(--ka-color-black)}.pasos button.on .num{color:var(--ka-color-yellow)}
#nav{display:flex;justify-content:space-between;align-items:center;margin-top:var(--esp-2);font-size:var(--ka-size-caption);color:var(--ka-color-gray-3)}
#nav button{border:1px solid var(--ka-color-border);background:var(--ka-color-surface);border-radius:var(--ka-radius-pill);padding:var(--esp-1) var(--esp-3);cursor:pointer;font:inherit}
#nav button:disabled{opacity:.35;cursor:default}
#texto{font-size:var(--ka-size-caption);line-height:1.55;background:var(--ka-color-bg-layout);border-radius:var(--ka-radius-box);padding:var(--esp-3) var(--esp-4)}
#texto h3{font-family:var(--ka-font-display);font-weight:var(--ka-weight-bold);font-size:var(--ka-size-body);margin:0 0 var(--esp-2)}
#texto p{margin:var(--esp-2) 0}
#texto .f{background:var(--ka-color-surface);border-left:3px solid var(--ka-color-yellow);padding:var(--esp-2) var(--esp-3);border-radius:var(--ka-radius-base);
 font-family:ui-monospace,Consolas,monospace;font-size:var(--ka-size-overline);white-space:pre-wrap}
#pie{padding:var(--esp-3) var(--esp-4);border-top:1px solid var(--ka-color-border)}
.nota{color:var(--ka-color-gray-3);font-size:var(--ka-size-overline);line-height:1.45}
.ka-site{display:block;margin-top:var(--esp-2)}
#mapa-wrap{flex:1;position:relative}#mapa{position:absolute;inset:0}
#b-capas{position:absolute;right:var(--esp-4);top:var(--esp-3);z-index:600;width:17rem;max-height:52%;overflow-y:auto;background:var(--ka-color-surface);border:1px solid var(--ka-color-border);border-radius:var(--ka-radius-box);box-shadow:0 6px 18px rgba(20,20,23,.14);padding:var(--esp-2) var(--esp-3)}
#leyenda{position:absolute;right:var(--esp-4);bottom:2rem;z-index:500;max-width:16rem;max-height:45%;overflow-y:auto;background:var(--ka-color-surface);
 border-radius:var(--ka-radius-box);padding:var(--esp-3) var(--esp-4);font-size:var(--ka-size-caption);box-shadow:0 1px 4px rgba(20,20,23,.18)}
#leyenda:empty{display:none}#leyenda b{font-family:var(--ka-font-display);font-weight:var(--ka-weight-medium)}
.zip-on{background:var(--ka-color-yellow);color:#141417;border-radius:var(--ka-radius-pill);padding:var(--esp-1) var(--esp-3);font-size:var(--ka-size-caption);font-weight:var(--ka-weight-semibold);margin-top:var(--esp-2);display:inline-block}
.zip-on button{border:0;background:transparent;font:inherit;cursor:pointer;text-decoration:underline;margin-left:var(--esp-2)}
#chip-zip{position:absolute;left:50%;transform:translateX(-50%);top:var(--esp-3);z-index:650;margin:0;box-shadow:0 2px 8px rgba(20,20,23,.2)}
#ayuda{position:absolute;left:3.25rem;top:var(--esp-3);z-index:500;background:var(--ka-color-black);color:var(--ka-color-white);border-radius:var(--ka-radius-pill);
 padding:var(--esp-1) var(--esp-3);font-size:var(--ka-size-overline);pointer-events:none}
#leyenda .it{cursor:pointer;user-select:none}#leyenda .it .n{color:var(--ka-color-gray-3)}#leyenda .it:hover{text-decoration:underline}#leyenda .it.off{opacity:.4;text-decoration:line-through}
.sw{display:inline-block;width:.7rem;height:.7rem;border-radius:50%;margin:0 var(--esp-1) -1px 0;border:1px solid var(--ka-color-white);box-shadow:0 0 0 1px var(--ka-color-gray-2)}
.grad{height:.6rem;border-radius:var(--ka-radius-base);margin:var(--esp-1) 0}.lab{display:flex;justify-content:space-between;color:var(--ka-color-gray-3);font-size:var(--ka-size-overline)}
.dist{display:flex;height:.6rem;width:100%;min-width:13rem;border-radius:var(--ka-radius-base);overflow:hidden;margin:var(--esp-1) 0;background:var(--ka-color-gray-1)}.dist span{display:block;height:100%}
.dist-lab{font-size:var(--ka-size-overline);line-height:1.4}.dist-tit{font-size:var(--ka-size-overline);color:var(--ka-color-gray-3);text-transform:uppercase;letter-spacing:var(--ka-tracking-eyebrow)}
.leaflet-container{font-family:var(--ka-font-body)}
.leaflet-popup-content-wrapper{border-radius:var(--ka-radius-box)}.leaflet-popup-content{margin:var(--esp-3) var(--esp-4);font-size:var(--ka-size-caption)}
.ficha-cab{font-family:var(--ka-font-display);font-weight:var(--ka-weight-bold);font-size:var(--ka-size-body);line-height:1.2}
.ficha-id{color:var(--ka-color-gray-3);font-size:var(--ka-size-overline);margin-bottom:var(--esp-2)}
.etq span{display:inline-block;transform:translate(-50%,-50%);font:600 11px var(--ka-font-body);color:#141417;white-space:nowrap;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 2px #fff;pointer-events:none}
#b-capas summary{cursor:pointer;list-style:none}#b-capas summary::-webkit-details-marker{display:none}
#b-capas summary::after{content:' ▾'}#b-capas details[open] summary::after{content:' ▴'}
#lista-capas{display:flex;flex-direction:column;gap:2px;margin-top:var(--esp-2)}
#lista-capas label{display:flex;gap:var(--esp-2);align-items:flex-start;font-size:var(--ka-size-caption);cursor:pointer;padding:2px 0}
#lista-capas input{margin-top:2px;accent-color:#141417}
.ficha-sec{font-weight:var(--ka-weight-semibold);padding-top:var(--esp-2)!important;color:var(--ka-color-black)}
.chips{display:flex;flex-wrap:wrap;gap:var(--esp-1);margin:var(--esp-1) 0 var(--esp-2)}
.chip{display:inline-block;padding:.1rem var(--esp-2);border-radius:var(--ka-radius-pill);font-size:var(--ka-size-overline);font-weight:var(--ka-weight-semibold);
 background:var(--ka-color-gray-1);color:var(--ka-color-black)}.chip.fuerte{background:var(--ka-color-black);color:var(--ka-color-white)}.chip.acento{background:var(--ka-color-yellow);color:var(--ka-color-black)}
.ficha{border-collapse:collapse;width:100%}.ficha td{padding:2px var(--esp-2) 2px 0;font-size:var(--ka-size-overline);vertical-align:top;border-bottom:1px solid var(--ka-color-gray-1)}
.ficha td:first-child{color:var(--ka-color-gray-3)}.ficha td:last-child{text-align:right;font-weight:var(--ka-weight-semibold)}
.ficha-wrap{max-height:16rem;overflow-y:auto}
hr.sep{border:0;border-top:1px solid var(--ka-color-gray-1);margin:var(--esp-2) 0}
#plegar{display:none}
@media (max-width:760px){#app{flex-direction:column}#panel{width:100%;max-height:55%;border-right:0;border-bottom:1px solid var(--ka-color-border)}
 #panel.cerrado #cuerpo,#panel.cerrado #pie{display:none}
 #plegar{display:inline-block;float:right;border:1px solid var(--ka-color-gray-3);background:transparent;color:var(--ka-color-white);border-radius:var(--ka-radius-pill);padding:0 var(--esp-2);font:inherit;font-size:var(--ka-size-overline)}
 #leyenda{max-width:12rem}#ayuda{display:none}#b-capas{width:13rem;max-height:40%}}
</style></head><body><div id="app"><aside id="panel">
<header id="cabeza"><button id="plegar" type="button">Ocultar panel ◂</button><img class="logo" src="__LOGO__" alt="Kin">
<div class="eyebrow">Mapa interactivo</div><h1 id="t"></h1><div class="sub" id="s"></div></header>
<div id="cuerpo">
<div class="bloque" id="b-vista" style="display:none"><span class="eyebrow" id="vista-tit"></span><div id="vista"></div></div>
<div class="bloque" id="b-res"><span class="eyebrow" id="res-tit"></span><div id="resol"></div></div>
<div class="bloque" id="b-filtro"><span class="eyebrow" id="filtro-tit"></span><div id="filtro"></div></div>
<div class="bloque"><span class="eyebrow">Buscar</span><input id="buscar" placeholder="ID o nombre del PDV · Enter abre el primero" autocomplete="off"><div id="filtro-zip" class="zip-on" style="display:none"></div><div id="res"></div></div>
<div class="bloque"><span class="eyebrow">Pasos</span><div class="pasos" id="pasos"></div>
<div id="nav"><button id="ant" type="button">← anterior</button><span id="pos"></span><button id="sig" type="button">siguiente →</button></div></div>
<div class="bloque"><div id="texto"></div></div>
</div>
<footer id="pie"><div class="nota">Clic en un PDV o en un hexágono: se dibujan su clúster NSE, su buffer de 300 m y su ficha. Teclas ← → cambian de paso.
Fondo OpenFreeMap (datos © colaboradores de OpenStreetMap), sin API key: funciona abriendo el archivo con doble clic.</div>
<span class="ka-site">kinanalytics.com</span></footer>
</aside><div id="mapa-wrap"><div id="mapa"></div><div id="b-capas" style="display:none"><details open><summary class="eyebrow">Resultados · elige qué ver</summary><div id="lista-capas"></div></details></div><div id="leyenda"></div><div id="ayuda">Clic en un punto o hexágono para ver su ficha</div><div id="chip-zip" class="zip-on" style="display:none"></div></div></div>
<script>
const D = __DATOS__;
document.getElementById('t').textContent = D.titulo; document.getElementById('s').textContent = D.subtitulo;
const mapa = L.map('mapa', {preferCanvas: true}).setView(D.centro, D.zoom);
// fondo vectorial libre (OpenFreeMap, datos OSM): sin API key ni Referer; si no hay WebGL queda el límite municipal
if (L.maplibreGL) L.maplibreGL({style: 'https://tiles.openfreemap.org/styles/positron', attribution:
  '<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> &copy; <a href="https://www.openmaptiles.org/" target="_blank">OpenMapTiles</a> ' +
  'datos &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">colaboradores de OpenStreetMap</a>'}).addTo(mapa);
const lienzo = L.canvas({padding: 0.5});
const DS = {};
for (const k in D.datasets) { const c = D.datasets[k].campos; DS[k] = D.datasets[k].filas.map(f => Object.fromEntries(c.map((n, i) => [n, f[i]]))); }
const fmt = v => v === null || v === undefined ? '—' : (typeof v === 'number' ? v.toLocaleString('es-MX', {maximumFractionDigits: 2}) : String(v));
const esc = s => String(s).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
function rgb(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
function continuo(v, e) {
  if (v === null || v === undefined || isNaN(v)) return null;
  const t = Math.max(0, Math.min(1, (v - e.min) / (e.max - e.min))) * (e.colores.length - 1);
  const i = Math.min(Math.floor(t), e.colores.length - 2), a = rgb(e.colores[i]), b = rgb(e.colores[i + 1]), f = t - i;
  return 'rgb(' + a.map((x, j) => Math.round(x + (b[j] - x) * f)).join(',') + ')';
}
const color = (v, e) => e.tipo === 'categorica' ? (e.colores[v] || '#c3c2b7') : continuo(v, e);
function pasa(r, filtro) { return !filtro || r[filtro[0]] === filtro[1]; }
const F = D.filtro, activos = new Set(F ? F.valores : []);         // filtro del panel (p. ej. subcanal)
const visible = (ds, r) => !F || ds !== F.dataset || activos.has(r[F.campo]);
let pasoActual = 0;
const ocultos = {};                       // clic en un valor de la leyenda: lo oculta o lo muestra (usuario, 2026-10-23)
const claveFiltro = c => c.campo + '|' + (c.dataset || String(c.fuente || 'hex').replace(/^r\d+$/, 'r'));
let zipFiltro = null, zona = null, zonaPadres = {};   // búsqueda de un código postal: solo se ve ese código (usuario, 2026-10-23)
function fueraDeZona(h, vals, campos) {   // hexágono fuera del código buscado
  if (zipFiltro === null) return false;
  const r = h3.getResolution(h), jz = campos.indexOf('zip');
  if (jz >= 0 && r >= 7) return vals[jz] !== zipFiltro;                        // hexágonos con código postal: el mismo código
  if (r > 9) return !zona.has(h3.cellToParent(h, 9));                          // hexágonos finos (res 10): dentro de la zona
  return !(zonaPadres[r] || (zonaPadres[r] = new Set([...zona].map(c => h3.cellToParent(c, r))))).has(h);   // res 6 (Whisp): los que la contienen
}
function puntoFuera(r) {
  if (zipFiltro === null) return false;
  if (r.zip !== undefined) return r.zip !== zipFiltro;                         // PDV: su código postal
  return !zona.has(h3.latLngToCell(r.lat, r.lon, 9));                          // Rappi y otros puntos: solo dentro de la zona
}
const oculto = (c, v) => !!(ocultos[claveFiltro(c)] && ocultos[claveFiltro(c)].has(String(v)));
const RS = D.resoluciones || null;        // selector de resolución H3: capas con "res" se ven solo en la resolución elegida
let resActual = RS ? RS.defecto : null;
const VS = D.vistas || null;              // "Ver": un paso con varias capas (p. ej. código postal · letras · prioridad), una a la vez
let vistaActual = VS ? VS.defecto : null;
const enRes = c => (!RS || c.res === undefined || c.res === resActual) && (!VS || c.vista === undefined || c.vista === vistaActual);
const conteos = {};                       // capa → {valor: cuántos se dibujan} (la leyenda solo muestra lo que hay en la vista)
function construir(c) {
  const g = L.layerGroup();
  const cnt = conteos[c.id] = {};
  if (c.tipo === 'hex') {
    const H = D.hex[c.fuente || 'hex'], j = H.campos.indexOf(c.campo);
    const jd = (c.distribucion || []).map(([e, k, col]) => [e, H.campos.indexOf(k), col]);
    const je = (c.extra || []).map(([e, k]) => [e, H.campos.indexOf(k)]);
    const K = D.cluster, porId = c.seleccion && K ? Object.fromEntries(DS[c.seleccion].map(r => [r[K.campo], r])) : null;
    for (const [h, vals] of Object.entries(H.filas)) {
      const v = vals[j]; if (v === null || fueraDeZona(h, vals, H.campos)) continue;
      cnt[v] = (cnt[v] || 0) + 1; if (oculto(c, v)) continue;
      const pol = L.polygon(h3.cellToBoundary(h), c.solo_borde ?        // contorno encima de otras capas, sin tapar ni robar el clic
        {renderer: lienzo, color: color(v, c.escala), weight: c.grosor || 3, fill: false, interactive: false} :
        {renderer: lienzo, stroke: !!c.borde, color: '#ffffff', weight: c.borde ? 1 : 0, fillColor: color(v, c.escala), fillOpacity: c.opacidad || 0.6})
        .bindTooltip(() => (c.res !== undefined ? '<span class="nota">H3 res ' + c.res + ' · ' + h + '</span><br>' : '') + '<b>' + c.nombre + ': ' + fmt(v) + '</b>' + je.map(([e, jj]) => '<br>' + e + ': <b>' + fmt(vals[jj]) + '</b>').join('') +
          barra(jd.map(([e, jj, col]) => [e, vals[jj], col])), {sticky: true});
      if (porId && porId[h]) pol.on('click', () => seleccionar(c.seleccion, porId[h]));
      else if (c.ficha) pol.on('click', () => fichaHex(c, h, vals, H));
      pol.addTo(g);
    }
  } else if (c.tipo === 'poligonos') {
    L.geoJSON(D.poligonos[c.fuente], {renderer: lienzo, style: f => ({color: '#ffffff', weight: 0.7, fillColor: color(f.properties[c.campo], c.escala) || '#e1e0d9',
      fillOpacity: c.opacidad || 0.55}), onEachFeature: (f, l) => l.bindTooltip(() => '<b>' + (c.etiqueta ? f.properties[c.etiqueta] + ' · ' : '') + c.nombre + ': ' + fmt(f.properties[c.campo]) + '</b>' +
      barra((c.distribucion || []).map(([e, k, col]) => [e, f.properties[k], col])), {sticky: true})}).addTo(g);
  } else if (c.tipo === 'puntos') {
    for (const r of DS[c.dataset]) {
      if (!pasa(r, c.filtro) || !visible(c.dataset, r) || puntoFuera(r)) continue;
      cnt[r[c.campo]] = (cnt[r[c.campo]] || 0) + 1; if (oculto(c, r[c.campo])) continue;
      const rad = c.tamano ? Math.max(3, Math.min(18, Math.sqrt(Math.max(r[c.tamano] || 0, 0)) * (c.escala_tamano || 0.5))) : (c.radio_px || 4);
      L.circleMarker([r.lat, r.lon], {renderer: lienzo, radius: rad, color: '#ffffff', weight: 0.7, fillColor: color(r[c.campo], c.escala) || '#c3c2b7', fillOpacity: 0.9})
        .bindTooltip(() => esc(r.nombre || r.id || '') + (c.campo === 'zip' && r.zip ? ' · CP ' + esc(r.zip) : ''), {direction: 'top'})
        .on('click', () => seleccionar(c.dataset, r)).addTo(g);
    }
  } else if (c.tipo === 'contorno') {
    L.geoJSON(D.poligonos[c.fuente], {renderer: lienzo, interactive: false, style: {color: c.color || '#52514e', weight: c.grosor || 1.2, fill: false}}).addTo(g);
  } else if (c.tipo === 'circulos') {
    for (const r of DS[c.dataset]) if (pasa(r, c.filtro))
      L.circle([r.lat, r.lon], {renderer: lienzo, radius: c.radio_m, color: c.color || '#e34948', weight: 1, fillOpacity: 0.04, interactive: false}).addTo(g);
  }
  return g;
}
function barra(partes) {   // [[etiqueta, % de 0 a 100, color], ...] → barra apilada con sus % (vacía si no hay datos)
  const ok = partes.filter(p => p[1] !== null && p[1] !== undefined && !isNaN(p[1]));
  if (!ok.length) return '';
  return '<div class="dist">' + ok.map(p => '<span style="width:' + Math.max(+p[1], 0) + '%;background:' + p[2] + '"></span>').join('') + '</div>' +
    '<div class="dist-lab">' + ok.map(p => '<span style="color:' + p[2] + '">■</span> ' + p[0] + ': <b>' + Math.round(+p[1]) + '%</b>').join('<br>') + '</div>';
}
const capas = {}, capaPor = Object.fromEntries(D.capas.map(c => [c.id, c]));
const sel = L.layerGroup().addTo(mapa);      // selección en el MISMO lienzo: un 2.º canvas encima tapaba los clics a los demás puntos
const dist = (a, b) => mapa.distance([a.lat, a.lon], [b.lat, b.lon]);
function chips(r) {         // etiquetas de la ficha: letras, prioridad y acción (si el dataset las trae)
  const c = [];
  if (r.letras) c.push('<span class="chip fuerte">' + esc(r.letras) + '</span>');
  if (r.prioridad) c.push('<span class="chip acento">' + esc(r.prioridad) + '</span>');
  if (r.accion) c.push('<span class="chip">' + esc(r.accion) + '</span>');
  if (r.segmento) c.push('<span class="chip">' + esc(r.segmento) + '</span>');
  return c.length ? '<div class="chips">' + c.join('') + '</div>' : '';
}
function seleccionar(ds, r) {
  sel.clearLayers();
  const K = D.cluster, cid = K ? r[K.campo] : null, esCluster = !!K && ds === K.dataset;
  const notas = [];
  let donde = [r.lat, r.lon];
  if (cid) {                    // clúster NSE: su hexágono, su centro y los PDV que lo comparten (azul; el buffer de 300 m del NSE no se dibuja)
    const cc = h3.cellToLatLng(cid);
    if (esCluster) donde = cc;
    L.polygon(h3.cellToBoundary(cid), {renderer: lienzo, color: '#2a78d6', weight: 2.4, fill: false, interactive: false}).addTo(sel);
    L.circleMarker(cc, {renderer: lienzo, radius: 3, color: '#2a78d6', weight: 1, fillColor: '#2a78d6', fillOpacity: 1, interactive: false}).addTo(sel);
    const miembros = (DS[K.miembros] || []).filter(p => p[K.campo] === cid && visible(K.miembros, p));
    miembros.forEach(p => L.circleMarker([p.lat, p.lon], {renderer: lienzo, radius: 5, color: '#2a78d6', weight: 2.2, fill: false, interactive: false}).addTo(sel));
    notas.push('<b>Clúster NSE</b> (azul): el hexágono y su centro; ' + miembros.length + ' PDV del hexágono comparten su NSE (Letra 1).');
  }
  if (!esCluster) {             // buffer del PDV: PDV con venta (negro) y las tiendas Rappi (rojo) que dan su variable Rappi
    L.circle([r.lat, r.lon], {renderer: lienzo, radius: D.radio, color: '#0a0a0a', weight: 2, dashArray: '6 4', fill: false, interactive: false}).addTo(sel);
    const dentro = (DS.bepensa || DS.pdv || []).filter(p => p.id !== r.id && dist(p, r) <= D.radio);   // PDV con venta
    const mismo = r.canal === undefined ? dentro : dentro.filter(p => p.canal === r.canal);          // su clúster: mismo canal
    const otros = dentro.filter(p => !mismo.includes(p));
    const rap = (DS.rappi || []).filter(p => p !== r && dist(p, r) <= D.radio);
    mismo.forEach(p => L.circleMarker([p.lat, p.lon], {renderer: lienzo, radius: 7, color: '#0a0a0a', weight: 1.8, fill: false, interactive: false}).addTo(sel));
    otros.forEach(p => L.circleMarker([p.lat, p.lon], {renderer: lienzo, radius: 7, color: '#898781', weight: 1.2, dashArray: '2 2', fill: false, interactive: false}).addTo(sel));
    rap.forEach(p => L.circleMarker([p.lat, p.lon], {renderer: lienzo, radius: 10, color: '#e34948', weight: 2, fill: false, interactive: false}).addTo(sel));
    notas.push('<b>Buffer de ' + D.radio + ' m</b> (negro punteado): ' + mismo.length + ' PDV con venta ' +
      (r.canal === undefined ? '(negro)' : 'de su canal (negro) y ' + otros.length + ' del otro canal (gris, no cuentan)') +
      ' · ' + rap.length + ' tiendas Rappi (rojo)' + (rap.length ? ': ' + rap.slice(0, 5).map(p => esc(p.nombre) + (p.activa ? ' (activa)' : ' (esporádica)')).join(', ') : ''));
  }
  if (!esCluster) {             // el PDV seleccionado: anillo amarillo (acento Kin) con borde negro para ubicarlo en el mapa
    L.circleMarker([r.lat, r.lon], {renderer: lienzo, radius: 13, color: '#141417', weight: 1.5, fill: false, interactive: false}).addTo(sel);
    L.circleMarker([r.lat, r.lon], {renderer: lienzo, radius: 11, color: '#e5ff01', weight: 4, fill: false, interactive: false}).addTo(sel);
    notas.unshift('<b>PDV seleccionado</b> (anillo amarillo).');
  }
  let t = '<div class="ficha-cab">' + esc(r.nombre || (esCluster ? 'Clúster NSE' : 'PDV')) + '</div>' +
          '<div class="ficha-id">' + (r.id !== undefined && r.id !== null ? 'pos_id ' + esc(r.id) : (cid ? 'H3 ' + esc(cid) : '')) + '</div>' + chips(r);
  const dp = (D.dist_popup || {})[ds];
  if (dp) t += '<div class="dist-tit">' + dp.titulo + '</div>' + barra(dp.partes.map(([e, k, col]) => [e, r[k], col])) + '<hr class="sep">';
  t += '<div class="ficha-wrap"><table class="ficha">' + (D.popup[ds] || []).map(([e, k]) => '<tr><td>' + e + '</td><td>' + esc(fmt(r[k])) + '</td></tr>').join('') + '</table></div>';
  t += '<hr class="sep"><div class="nota">' + notas.join('<br>') + '</div>';
  L.popup({maxWidth: 400, minWidth: 280, autoPanPaddingTopLeft: [16, 48], autoPanPaddingBottomRight: [300, 32]}).setLatLng(donde).setContent(t).openOn(mapa);
}
function fichaHex(c, h, vals, H) {   // capa hex con "ficha" = [[etiqueta, campo], ...]: clic → todos los datos del hexágono
  sel.clearLayers();
  const b = h3.cellToBoundary(h), r = Object.fromEntries(H.campos.map((k, i) => [k, vals[i]]));
  L.polygon(b, {renderer: lienzo, color: '#141417', weight: 4, fill: false, interactive: false}).addTo(sel);
  L.polygon(b, {renderer: lienzo, color: '#e5ff01', weight: 2.5, fill: false, interactive: false}).addTo(sel);
  let t = '<div class="ficha-cab">Hexágono' + (c.res !== undefined ? ' res ' + c.res : '') + '</div><div class="ficha-id">H3 ' + esc(h) + '</div>' + chips(r);
  const jd = (c.distribucion_ficha || c.distribucion || []).map(([e, k, col]) => [e, r[k], col]);
  if (jd.length) t += '<div class="dist-tit">' + (c.titulo_distribucion || 'Distribución') + '</div>' + barra(jd) + '<hr class="sep">';
  t += '<div class="ficha-wrap"><table class="ficha">' + c.ficha.map(([e, k]) => e.startsWith('§') ?
    '<tr><td colspan="2" class="ficha-sec">' + esc(e.slice(1)) + '</td></tr>' : '<tr><td>' + e + '</td><td>' + esc(fmt(r[k])) + '</td></tr>').join('') + '</table></div>';
  L.popup({maxWidth: 400, minWidth: 280, autoPanPaddingTopLeft: [16, 48], autoPanPaddingBottomRight: [300, 32]})
    .setLatLng(h3.cellToLatLng(h)).setContent(t).openOn(mapa);
}
const etq = L.layerGroup().addTo(mapa);   // etiquetas fijas (p. ej. el código postal) dentro de los hexágonos visibles al acercarse
function etiquetas() {
  etq.clearLayers();
  const p = D.pasos[pasoActual]; if (!p) return;
  const b = mapa.getBounds();
  for (const id of visibles) {
    const c = capaPor[id];
    if (!c.etiqueta_campo || mapa.getZoom() < (c.etiqueta_zoom || 14)) continue;
    const H = D.hex[c.fuente], j = H.campos.indexOf(c.etiqueta_campo); let n = 0;
    for (const [h, vals] of Object.entries(H.filas)) {
      const v = vals[j]; if (v === null || v === undefined) continue;
      const ll = h3.cellToLatLng(h); if (!b.contains(ll)) continue;
      L.marker(ll, {interactive: false, keyboard: false, icon: L.divIcon({className: 'etq', html: '<span>' + esc(v) + '</span>', iconSize: null})}).addTo(etq);
      if (++n >= 800) break;
    }
  }
}
mapa.on('moveend', etiquetas);
function leyenda(ids) {
  let h = '';
  for (const id of ids) {
    const c = capaPor[id]; if (!c.escala) continue;
    h += '<div style="margin-top:.4rem"><b>' + c.nombre + '</b><br>';
    if (c.escala.leyenda) h += '<span class="nota">' + c.escala.leyenda + '</span>';
    else if (c.escala.tipo === 'categorica') {                   // solo los valores que hay en lo que se ve, con cuántos
      const n = conteos[id] || {}, hay = Object.entries(c.escala.colores).filter(([k]) => n[k]);
      h += hay.length ? hay.map(([k, v]) => '<span class="it' + (oculto(c, k) ? ' off' : '') + '" data-capa="' + esc(id) + '" data-v="' + esc(k) +
        '" title="clic: mostrar u ocultar"><span class="sw" style="background:' + v + '"></span>' + (c.escala.etiquetas && c.escala.etiquetas[k] || k) +
        ' <span class="n">' + n[k].toLocaleString('es-MX') + '</span></span>').join('<br>') : '<span class="nota">nada en esta vista</span>';
    }
    else h += '<div class="grad" style="background:linear-gradient(90deg,' + c.escala.colores.join(',') + ')"></div><div class="lab"><span>' + (c.escala.bajo || fmt(c.escala.min)) + '</span><span>' + (c.escala.alto || fmt(c.escala.max)) + '</span></div>';
    h += '</div>';
  }
  const ley = document.getElementById('leyenda');
  ley.innerHTML = h ? '<span class="eyebrow">Leyenda · clic en un valor para mostrarlo u ocultarlo</span>' + h : '';
  ley.querySelectorAll('.it').forEach(el => el.onclick = () => {
    const c = capaPor[el.dataset.capa], k = claveFiltro(c), s = ocultos[k] = ocultos[k] || new Set();
    s.has(el.dataset.v) ? s.delete(el.dataset.v) : s.add(el.dataset.v);
    for (const id in capas) if (claveFiltro(capaPor[id]) === k) { mapa.removeLayer(capas[id]); delete capas[id]; }   // se redibujan sin esos valores
    sel.clearLayers(); mapa.closePopup(); activar(pasoActual, true);
  });
}
let ajustes = {}, visibles = [];        // grupo de capa → true/false puesto por el usuario · capas que se ven ahora
const grupoDe = c => c.grupo || c.id;
const nombreCapa = c => c.etiqueta_capa || String(c.nombre).replace(/^Res \d+ · /, '');
const GRUPOS = [...new Map(D.capas.filter(c => !c.siempre).map(c => [grupoDe(c), c])).values()];
const rango = c => c.tipo === 'poligonos' ? 0 : c.tipo === 'hex' ? (c.solo_borde ? 2 : 1) : c.tipo === 'circulos' ? 3 : 4;   // puntos arriba
function capaDeGrupo(g) { const cs = D.capas.filter(c => grupoDe(c) === g); return (cs.find(c => c.res === undefined || c.res === resActual) || cs[0]).id; }
const OP = D.opciones || null;           // resultados de cada proceso (código postal, letras, Rappi, Whisp): lo que se elige en la última vista
let opOn = new Set(OP ? OP.filter(o => o.defecto).map(o => o.valor) : []);
function capasOpciones() {               // "solo": la versión que se usa cuando ningún otro resultado pinta hexágonos (p. ej. Whisp relleno y clicable)
  const ons = OP.filter(o => opOn.has(o.valor)), ids = [];
  for (const o of ons) ids.push(...((o.solo && !ons.some(x => x !== o && x.relleno)) ? o.solo : o.capas).map(capaDeGrupo));
  return ids;
}
function listaCapas() {
  if (OP) {
    const box = document.getElementById('lista-capas');
    box.innerHTML = OP.map(o => '<label><input type="checkbox" value="' + esc(o.valor) + '"' + (opOn.has(o.valor) ? ' checked' : '') + '><span><b>' +
      esc(o.etiqueta) + '</b>' + (o.nota ? '<br><span class="nota">' + esc(o.nota) + '</span>' : '') + '</span></label>').join('');
    box.querySelectorAll('input').forEach(inp => inp.onchange = () => { inp.checked ? opOn.add(inp.value) : opOn.delete(inp.value); activar(pasoActual, true); });
    return;
  }
  const on = new Set(visibles.map(id => grupoDe(capaPor[id]))), box = document.getElementById('lista-capas');
  const prim = [...new Set(D.pasos[pasoActual].capas.map(id => grupoDe(capaPor[id])))];      // primero las de esta vista, luego las demás
  const fila = c => '<label><input type="checkbox" value="' + esc(grupoDe(c)) + '"' + (on.has(grupoDe(c)) ? ' checked' : '') + '><span>' + esc(nombreCapa(c)) + '</span></label>';
  const a = prim.map(g => GRUPOS.find(c => grupoDe(c) === g)).filter(Boolean), b = GRUPOS.filter(c => !prim.includes(grupoDe(c)));
  box.innerHTML = a.map(fila).join('') + (b.length ? '<div class="nota" style="margin-top:var(--esp-2)">Más capas (de los otros pasos)</div>' + b.map(fila).join('') : '');
  box.querySelectorAll('input').forEach(inp => inp.onchange = () => { ajustes[inp.value] = inp.checked; activar(pasoActual, true); });
}
function activar(i, conservar) {
  i = Math.max(0, Math.min(D.pasos.length - 1, i));
  const p = D.pasos[i];
  const libre = i === D.pasos.length - 1;   // solo el último paso deja prender o apagar cualquier capa (usuario, 2026-10-23)
  if (!conservar || !libre) ajustes = {};
  if (!conservar && Object.keys(ocultos).length) {          // otro paso: se vuelven a ver todos los valores
    for (const k in ocultos) delete ocultos[k];
    for (const id in capas) { mapa.removeLayer(capas[id]); delete capas[id]; }
  }
  pasoActual = i;
  document.getElementById('b-capas').style.display = libre ? '' : 'none';
  document.querySelectorAll('.pasos button').forEach((b, j) => b.classList.toggle('on', j === i));
  for (const id in capas) mapa.removeLayer(capas[id]);
  const base = p.capas.filter(id => enRes(capaPor[id])), gb = new Set(base.map(id => grupoDe(capaPor[id])));
  let vis = base.filter(id => ajustes[grupoDe(capaPor[id])] !== false);
  for (const [g, on] of Object.entries(ajustes)) if (on && !gb.has(g)) vis.push(capaDeGrupo(g));
  if (libre && OP) vis = capasOpciones();
  vis = vis.map((id, k) => [id, k]).sort((a, b) => rango(capaPor[a[0]]) - rango(capaPor[b[0]]) || a[1] - b[1]).map(x => x[0]);
  visibles = vis;
  if (VS) document.getElementById('b-vista').style.display = !libre && p.capas.some(id => capaPor[id].vista !== undefined) ? '' : 'none';   // en la última vista mandan las casillas
  for (const id of vis) { if (!capas[id]) capas[id] = construir(capaPor[id]); capas[id].addTo(mapa); }
  document.getElementById('texto').innerHTML = '<h3>' + p.titulo + '</h3><p><b>Qué se hace:</b> ' + p.que + '</p><p><b>Por qué:</b> ' + p.porque + '</p>' +
    (p.formula ? '<div class="f">' + p.formula + '</div>' : '') + (p.cifras ? '<p>' + p.cifras + '</p>' : '');
  document.getElementById('pos').textContent = 'Paso ' + (i + 1) + ' de ' + D.pasos.length;
  document.getElementById('ant').disabled = i === 0; document.getElementById('sig').disabled = i === D.pasos.length - 1;
  leyenda(vis);
  etiquetas();
  listaCapas();
}
D.capas.filter(c => c.siempre).forEach(c => construir(c).addTo(mapa));      // contexto fijo (p. ej. límite municipal)
D.pasos.forEach((p, i) => {
  const b = document.createElement('button'); b.type = 'button';
  b.innerHTML = '<span class="num">' + String(i + 1).padStart(2, '0') + '</span><span>' + esc(p.titulo) + '</span>';
  b.onclick = () => activar(i); document.getElementById('pasos').appendChild(b);
});
document.getElementById('ant').onclick = () => activar(pasoActual - 1);
document.getElementById('sig').onclick = () => activar(pasoActual + 1);
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowRight') activar(pasoActual + 1); else if (e.key === 'ArrowLeft') activar(pasoActual - 1);
});
if (F) {
  document.getElementById('filtro-tit').textContent = F.etiqueta;
  const box = document.getElementById('filtro');
  box.innerHTML = F.valores.map(v => '<label class="on"><input type="checkbox" value="' + esc(v) + '" checked>' + esc(v) + ' <span class="n">' +
    DS[F.dataset].filter(r => r[F.campo] === v).length.toLocaleString('es-MX') + '</span></label>').join('');
  box.querySelectorAll('input').forEach(inp => inp.onchange = () => {
    inp.checked ? activos.add(inp.value) : activos.delete(inp.value);
    inp.parentElement.classList.toggle('on', inp.checked);
    for (const id in capas) if (capaPor[id].dataset === F.dataset) { mapa.removeLayer(capas[id]); delete capas[id]; }   // se redibujan con el filtro
    sel.clearLayers(); mapa.closePopup(); activar(pasoActual, true);
  });
} else document.getElementById('b-filtro').style.display = 'none';
if (RS) {
  document.getElementById('res-tit').textContent = RS.etiqueta;
  const box = document.getElementById('resol');
  box.innerHTML = RS.valores.map(o => '<label' + (o.valor === resActual ? ' class="on"' : '') + '><input type="radio" name="resol" value="' + o.valor + '"' +
    (o.valor === resActual ? ' checked' : '') + '>' + esc(o.etiqueta) + (o.n !== undefined ? ' <span class="n">' + o.n.toLocaleString('es-MX') + '</span>' : '') + '</label>').join('');
  box.querySelectorAll('input').forEach(inp => inp.onchange = () => {
    resActual = +inp.value; box.querySelectorAll('label').forEach(l => l.classList.toggle('on', l.firstChild.checked));
    sel.clearLayers(); mapa.closePopup(); activar(pasoActual, true);
  });
} else document.getElementById('b-res').style.display = 'none';
function marcarVista(v) {
  vistaActual = v; document.querySelectorAll('#vista input').forEach(i => { i.checked = i.value === v; i.parentElement.classList.toggle('on', i.checked); });
}
if (VS) {
  document.getElementById('vista-tit').textContent = VS.etiqueta;
  const box = document.getElementById('vista');
  box.innerHTML = VS.valores.map(o => '<label' + (o.valor === vistaActual ? ' class="on"' : '') + '><input type="radio" name="vista" value="' + o.valor + '"' +
    (o.valor === vistaActual ? ' checked' : '') + '>' + esc(o.etiqueta) + '</label>').join('');
  box.querySelectorAll('input').forEach(inp => inp.onchange = () => { marcarVista(inp.value); sel.clearLayers(); mapa.closePopup(); activar(pasoActual, true); });
}
if (D.buscar_placeholder) document.getElementById('buscar').placeholder = D.buscar_placeholder;
const HEXR = D.capas.filter(c => c.tipo === 'hex' && c.res !== undefined);       // hexágonos buscables por id (una fuente por resolución)
function buscarHex(q) {
  const vistos = new Set(), out = [];
  for (const c of HEXR.filter(c => c.buscar_campo && enRes(c))) {          // por valor (código postal): uno por valor
    const H = D.hex[c.fuente], j = H.campos.indexOf(c.buscar_campo), por = {};
    for (const h in H.filas) { const v = H.filas[h][j]; if (v !== null && String(v).startsWith(q)) (por[v] = por[v] || []).push(h); }
    for (const v of Object.keys(por).sort()) { out.push({valor: v, campo: c.buscar_etiqueta || c.buscar_campo, res: c.res, hexes: por[v]}); if (out.length >= 8) return out; }
    break;
  }
  for (const c of HEXR) { if (vistos.has(c.fuente)) continue; vistos.add(c.fuente);
    const H = D.hex[c.fuente], j = H.campos.indexOf(c.campo);
    for (const h in H.filas) if (h.includes(q)) { out.push({hex: h, res: c.res, etiqueta: H.filas[h][j]}); if (out.length >= 8) return out; } }
  return out;
}
function irHex(o) {
  if (RS && o.res !== resActual) { resActual = o.res; document.querySelectorAll('#resol input').forEach(i => { i.checked = +i.value === o.res; i.parentElement.classList.toggle('on', i.checked); }); }
  const quiere = id => capaPor[id].res === o.res && (!o.hexes || capaPor[id].buscar_campo);   // por valor → el paso de ese campo
  if (o.hexes) ponerZip(o.valor);
  if (o.hexes) { const c = D.capas.find(c => quiere(c.id)); if (c && c.vista !== undefined) marcarVista(c.vista); activar(D.pasos.findIndex(p => p.capas.some(quiere))); }
  else if (!D.pasos[pasoActual].capas.some(id => capaPor[id].res === o.res)) activar(D.pasos.findIndex(p => p.capas.some(id => capaPor[id].res === o.res))); else activar(pasoActual);
  sel.clearLayers();
  const todos = [];
  for (const hx of (o.hexes || [o.hex])) { const b = h3.cellToBoundary(hx); todos.push(...b);
    if (o.hexes) continue;                  // código postal: el filtro ya deja solo esos hexágonos; un id: se marca
    L.polygon(b, {renderer: lienzo, color: '#141417', weight: 4, fill: false, interactive: false}).addTo(sel);
    L.polygon(b, {renderer: lienzo, color: '#e5ff01', weight: 2.5, fill: false, interactive: false}).addTo(sel); }
  mapa.fitBounds(L.latLngBounds(todos), {maxZoom: o.hexes ? 15 : 16, padding: [60, 60]});
}
function buscarZip(q) {                // PDV por código postal: un resultado por código con todos sus PDV
  if (!/^\d{2,5}$/.test(q) || !(DS.pdv || []).length || DS.pdv[0].zip === undefined) return [];
  const por = {};
  for (const r of DS.pdv) if (visible('pdv', r) && String(r.zip).startsWith(q)) (por[r.zip] = por[r.zip] || []).push(r);
  return Object.keys(por).sort().slice(0, 4).map(v => ({zipval: v, pdvs: por[v]}));
}
function ponerZip(z) {                    // filtra todo el mapa a un código postal (null = quitar)
  zipFiltro = z; zonaPadres = {};
  if (z !== null) {
    zona = new Set();
    if (D.hex.r9) { const jz = D.hex.r9.campos.indexOf('zip'); for (const h in D.hex.r9.filas) if (D.hex.r9.filas[h][jz] === z) zona.add(h); }
    for (const r of (DS.pdv || [])) if (r.zip === z) zona.add(h3.latLngToCell(r.lat, r.lon, 9));
    if (OP && OP.some(o => o.valor === 'zip')) opOn.add('zip');
  }
  for (const id in capas) { mapa.removeLayer(capas[id]); delete capas[id]; }
  const txt = z === null ? '' : 'Solo CP ' + esc(z) + ' <button type="button" class="quitar-zip">quitar ✕</button>';
  for (const id of ['filtro-zip', 'chip-zip']) { const el = document.getElementById(id); el.innerHTML = txt; el.style.display = z === null ? 'none' : ''; }
  document.querySelectorAll('.quitar-zip').forEach(b => b.onclick = () => { ponerZip(null); sel.clearLayers(); activar(pasoActual, true); });
}
function irZip(o) {
  ponerZip(o.zipval);
  const i = D.pasos.findIndex(p => p.capas.some(id => capaPor[id].campo === 'zip' && capaPor[id].tipo === 'puntos'));
  if (i >= 0) { const c = D.capas.find(c => c.campo === 'zip' && c.tipo === 'puntos'); if (c && c.vista !== undefined) marcarVista(c.vista); activar(i); }
  sel.clearLayers(); mapa.closePopup();
  mapa.fitBounds(L.latLngBounds(o.pdvs.map(p => [p.lat, p.lon])), {maxZoom: 15, padding: [60, 60]});   // el filtro ya deja solo ese código
}
let hallados = [];
const ir = r => r.pdvs ? irZip(r) : (r.hex || r.hexes) ? irHex(r) : (mapa.setView([r.lat, r.lon], 17), seleccionar('pdv', r));
const buscar = document.getElementById('buscar'), res = document.getElementById('res');
buscar.addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase(); res.innerHTML = ''; hallados = [];
  if (q.length < 2) return;
  hallados = [...buscarZip(q), ...(DS.pdv || []).filter(r => visible('pdv', r) && (String(r.id).includes(q) || String(r.nombre).toLowerCase().includes(q)))].slice(0, 8);
  if (!hallados.length && HEXR.length) hallados = buscarHex(q);
  if (!hallados.length) { res.innerHTML = '<div class="vacio">Sin resultados con el filtro actual</div>'; return; }
  hallados.forEach((r, k) => {
    const d = document.createElement('div');
    d.textContent = r.pdvs ? 'CP ' + r.zipval + ' · ' + r.pdvs.length + ' PDV' : r.hexes ? r.campo + ' ' + r.valor + ' · ' + r.hexes.length + ' hexágonos res ' + r.res : r.hex ? 'H3 res ' + r.res + ' · ' + r.hex + (r.etiqueta ? ' · ' + r.etiqueta : '') :
      r.id + ' · ' + r.nombre + (r.letras ? ' · ' + r.letras : '') + (r.prioridad ? ' · ' + r.prioridad : '');
    if (k === 0) d.className = 'on';
    d.onclick = () => ir(r); res.appendChild(d);
  });
});
buscar.addEventListener('keydown', e => {
  if (e.key === 'Enter' && hallados.length) ir(hallados[0]);
  if (e.key === 'Escape') { buscar.value = ''; res.innerHTML = ''; hallados = []; if (zipFiltro !== null) { ponerZip(null); sel.clearLayers(); activar(pasoActual, true); } }
});
document.getElementById('plegar').onclick = e => {
  const p = document.getElementById('panel'); p.classList.toggle('cerrado'); e.target.textContent = p.classList.contains('cerrado') ? 'Mostrar panel ▸' : 'Ocultar panel ◂';
  setTimeout(() => mapa.invalidateSize(), 50);
};
activar(0);
</script></body></html>
"""
