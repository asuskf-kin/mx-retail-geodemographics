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
              filtro=None, distribucion_popup=None, cluster=None):
    """Escribe el mapa interactivo.

    datasets = {nombre: DataFrame con columnas lat, lon, ...}; hexagonos = DataFrame indexado por id H3, o {fuente: DataFrame}
    (una capa hex elige la suya con "fuente"; con "borde" dibuja el contorno, con "extra" = [[etiqueta, campo], ...] agrega
    líneas al tooltip y con "seleccion" = dataset, el clic en el hexágono abre la ficha de su fila en ese dataset);
    poligonos = {nombre: GeoDataFrame en EPSG:4326}; capas = lista de dicts (id, nombre, tipo = hex | poligonos | puntos |
    circulos, campo, escala, ...); pasos = lista de dicts (titulo, que, porque, formula, capas); popup = {dataset: [(etiqueta, campo)]};
    filtro = {dataset, campo, valores, etiqueta}: casillas en el panel (p. ej. subcanal) que filtran los puntos.
    cluster = {dataset, campo, miembros}: el campo con el id H3 del clúster NSE de cada fila; al seleccionar una fila se dibujan
    su hexágono, el buffer de radio_m desde su centro y las filas de `miembros` con el mismo id.
    Una capa hex o poligonos con "distribucion" = [[etiqueta, campo, color], ...] (campos en %) muestra en su tooltip una barra
    apilada con esos %; distribucion_popup = {dataset: {"titulo", "partes": [[etiqueta, campo, color], ...]}} la pone arriba de la
    ficha al hacer clic en un punto.
    """
    datos = {"titulo": titulo, "subtitulo": subtitulo, "centro": list(centro), "zoom": zoom, "radio": radio_m,
             "datasets": {k: tabla_js(v) for k, v in datasets.items()}, "capas": capas, "pasos": pasos, "popup": popup,
             "hex": {}, "poligonos": {}, "filtro": filtro, "dist_popup": distribucion_popup or {}, "cluster": cluster}
    hexs = {"hex": hexagonos} if isinstance(hexagonos, pd.DataFrame) else (hexagonos or {})
    for k, hx in hexs.items():
        datos["hex"][k] = {"campos": list(hx.columns), "filas": {h: [_limpio(v) for v in fila] for h, fila in
                                                                zip(hx.index, hx.itertuples(index=False))}}
    for k, g in (poligonos or {}).items():
        datos["poligonos"][k] = json.loads(g.to_json(drop_id=True))
    js = json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=_limpio).replace("</", "<\\/")
    m = _marca()
    pagina = (_PLANTILLA.replace("__MARCA_CSS__", m["css"]).replace("__LOGO__", m["logo"]).replace("__FAVICON__", m["favicon"])
              .replace("__TITULO__", html.escape(titulo)).replace("__DATOS__", js))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(pagina)
    return ruta


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
#filtro{display:flex;flex-wrap:wrap;gap:var(--esp-2)}
#filtro label{display:inline-flex;align-items:center;gap:var(--esp-1);padding:var(--esp-1) var(--esp-3);border:1px solid var(--ka-color-border);border-radius:var(--ka-radius-pill);
 font-size:var(--ka-size-caption);cursor:pointer;user-select:none;background:var(--ka-color-surface)}
#filtro label.on{background:var(--ka-color-black);color:var(--ka-color-white);border-color:var(--ka-color-black)}
#filtro input{display:none}#filtro .n{color:var(--ka-color-gray-3)}
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
#leyenda{position:absolute;right:var(--esp-4);bottom:2rem;z-index:500;max-width:16rem;max-height:45%;overflow-y:auto;background:var(--ka-color-surface);
 border-radius:var(--ka-radius-box);padding:var(--esp-3) var(--esp-4);font-size:var(--ka-size-caption);box-shadow:0 1px 4px rgba(20,20,23,.18)}
#leyenda:empty{display:none}#leyenda b{font-family:var(--ka-font-display);font-weight:var(--ka-weight-medium)}
#ayuda{position:absolute;left:3.25rem;top:var(--esp-3);z-index:500;background:var(--ka-color-black);color:var(--ka-color-white);border-radius:var(--ka-radius-pill);
 padding:var(--esp-1) var(--esp-3);font-size:var(--ka-size-overline);pointer-events:none}
.sw{display:inline-block;width:.7rem;height:.7rem;border-radius:50%;margin:0 var(--esp-1) -1px 0;border:1px solid var(--ka-color-white);box-shadow:0 0 0 1px var(--ka-color-gray-2)}
.grad{height:.6rem;border-radius:var(--ka-radius-base);margin:var(--esp-1) 0}.lab{display:flex;justify-content:space-between;color:var(--ka-color-gray-3);font-size:var(--ka-size-overline)}
.dist{display:flex;height:.6rem;width:100%;min-width:13rem;border-radius:var(--ka-radius-base);overflow:hidden;margin:var(--esp-1) 0;background:var(--ka-color-gray-1)}.dist span{display:block;height:100%}
.dist-lab{font-size:var(--ka-size-overline);line-height:1.4}.dist-tit{font-size:var(--ka-size-overline);color:var(--ka-color-gray-3);text-transform:uppercase;letter-spacing:var(--ka-tracking-eyebrow)}
.leaflet-container{font-family:var(--ka-font-body)}
.leaflet-popup-content-wrapper{border-radius:var(--ka-radius-box)}.leaflet-popup-content{margin:var(--esp-3) var(--esp-4);font-size:var(--ka-size-caption)}
.ficha-cab{font-family:var(--ka-font-display);font-weight:var(--ka-weight-bold);font-size:var(--ka-size-body);line-height:1.2}
.ficha-id{color:var(--ka-color-gray-3);font-size:var(--ka-size-overline);margin-bottom:var(--esp-2)}
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
 #leyenda{max-width:12rem}#ayuda{display:none}}
</style></head><body><div id="app"><aside id="panel">
<header id="cabeza"><button id="plegar" type="button">ocultar</button><img class="logo" src="__LOGO__" alt="Kin">
<div class="eyebrow">Mapa interactivo</div><h1 id="t"></h1><div class="sub" id="s"></div></header>
<div id="cuerpo">
<div class="bloque" id="b-filtro"><span class="eyebrow" id="filtro-tit"></span><div id="filtro"></div></div>
<div class="bloque"><span class="eyebrow">Buscar</span><input id="buscar" placeholder="ID o nombre del PDV · Enter abre el primero" autocomplete="off"><div id="res"></div></div>
<div class="bloque"><span class="eyebrow">Pasos</span><div class="pasos" id="pasos"></div>
<div id="nav"><button id="ant" type="button">← anterior</button><span id="pos"></span><button id="sig" type="button">siguiente →</button></div></div>
<div class="bloque"><div id="texto"></div></div>
</div>
<footer id="pie"><div class="nota">Clic en un PDV o en un hexágono: se dibujan su clúster NSE, su buffer de 300 m y su ficha. Teclas ← → cambian de paso.
Fondo OpenFreeMap (datos © colaboradores de OpenStreetMap), sin API key: funciona abriendo el archivo con doble clic.</div>
<span class="ka-site">kinanalytics.com</span></footer>
</aside><div id="mapa-wrap"><div id="mapa"></div><div id="leyenda"></div><div id="ayuda">Clic en un punto o hexágono para ver su ficha</div></div></div>
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
function construir(c) {
  const g = L.layerGroup();
  if (c.tipo === 'hex') {
    const H = D.hex[c.fuente || 'hex'], j = H.campos.indexOf(c.campo);
    const jd = (c.distribucion || []).map(([e, k, col]) => [e, H.campos.indexOf(k), col]);
    const je = (c.extra || []).map(([e, k]) => [e, H.campos.indexOf(k)]);
    const K = D.cluster, porId = c.seleccion && K ? Object.fromEntries(DS[c.seleccion].map(r => [r[K.campo], r])) : null;
    for (const [h, vals] of Object.entries(H.filas)) {
      const v = vals[j]; if (v === null) continue;
      const pol = L.polygon(h3.cellToBoundary(h), {renderer: lienzo, stroke: !!c.borde, color: '#ffffff', weight: c.borde ? 1 : 0,
        fillColor: color(v, c.escala), fillOpacity: c.opacidad || 0.6})
        .bindTooltip(() => '<b>' + c.nombre + ': ' + fmt(v) + '</b>' + je.map(([e, jj]) => '<br>' + e + ': <b>' + fmt(vals[jj]) + '</b>').join('') +
          barra(jd.map(([e, jj, col]) => [e, vals[jj], col])), {sticky: true});
      if (porId && porId[h]) pol.on('click', () => seleccionar(c.seleccion, porId[h]));
      pol.addTo(g);
    }
  } else if (c.tipo === 'poligonos') {
    L.geoJSON(D.poligonos[c.fuente], {renderer: lienzo, style: f => ({color: '#ffffff', weight: 0.7, fillColor: color(f.properties[c.campo], c.escala) || '#e1e0d9',
      fillOpacity: c.opacidad || 0.55}), onEachFeature: (f, l) => l.bindTooltip(() => '<b>' + (c.etiqueta ? f.properties[c.etiqueta] + ' · ' : '') + c.nombre + ': ' + fmt(f.properties[c.campo]) + '</b>' +
      barra((c.distribucion || []).map(([e, k, col]) => [e, f.properties[k], col])), {sticky: true})}).addTo(g);
  } else if (c.tipo === 'puntos') {
    for (const r of DS[c.dataset]) {
      if (!pasa(r, c.filtro) || !visible(c.dataset, r)) continue;
      const rad = c.tamano ? Math.max(3, Math.min(18, Math.sqrt(Math.max(r[c.tamano] || 0, 0)) * (c.escala_tamano || 0.5))) : (c.radio_px || 4);
      L.circleMarker([r.lat, r.lon], {renderer: lienzo, radius: rad, color: '#ffffff', weight: 0.7, fillColor: color(r[c.campo], c.escala) || '#c3c2b7', fillOpacity: 0.9})
        .bindTooltip(() => esc(r.nombre || r.id || ''), {direction: 'top'})
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
function leyenda(ids) {
  let h = '';
  for (const id of ids) {
    const c = capaPor[id]; if (!c.escala) continue;
    h += '<div style="margin-top:.4rem"><b>' + c.nombre + '</b><br>';
    if (c.escala.tipo === 'categorica') h += Object.entries(c.escala.colores).map(([k, v]) => '<span class="sw" style="background:' + v + '"></span>' + (c.escala.etiquetas && c.escala.etiquetas[k] || k)).join('<br>');
    else h += '<div class="grad" style="background:linear-gradient(90deg,' + c.escala.colores.join(',') + ')"></div><div class="lab"><span>' + (c.escala.bajo || fmt(c.escala.min)) + '</span><span>' + (c.escala.alto || fmt(c.escala.max)) + '</span></div>';
    h += '</div>';
  }
  document.getElementById('leyenda').innerHTML = h ? '<span class="eyebrow">Leyenda</span>' + h : '';
}
function activar(i) {
  i = Math.max(0, Math.min(D.pasos.length - 1, i));
  const p = D.pasos[i];
  pasoActual = i;
  document.querySelectorAll('.pasos button').forEach((b, j) => b.classList.toggle('on', j === i));
  for (const id in capas) mapa.removeLayer(capas[id]);
  for (const id of p.capas) { if (!capas[id]) capas[id] = construir(capaPor[id]); capas[id].addTo(mapa); }
  document.getElementById('texto').innerHTML = '<h3>' + p.titulo + '</h3><p><b>Qué se hace:</b> ' + p.que + '</p><p><b>Por qué:</b> ' + p.porque + '</p>' +
    (p.formula ? '<div class="f">' + p.formula + '</div>' : '') + (p.cifras ? '<p>' + p.cifras + '</p>' : '');
  document.getElementById('pos').textContent = 'Paso ' + (i + 1) + ' de ' + D.pasos.length;
  document.getElementById('ant').disabled = i === 0; document.getElementById('sig').disabled = i === D.pasos.length - 1;
  leyenda(p.capas);
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
    sel.clearLayers(); mapa.closePopup(); activar(pasoActual);
  });
} else document.getElementById('b-filtro').style.display = 'none';
let hallados = [];
const ir = r => { mapa.setView([r.lat, r.lon], 17); seleccionar('pdv', r); };
const buscar = document.getElementById('buscar'), res = document.getElementById('res');
buscar.addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase(); res.innerHTML = ''; hallados = [];
  if (q.length < 2) return;
  hallados = (DS.pdv || []).filter(r => visible('pdv', r) && (String(r.id).includes(q) || String(r.nombre).toLowerCase().includes(q))).slice(0, 8);
  if (!hallados.length) { res.innerHTML = '<div class="vacio">Sin resultados con el filtro actual</div>'; return; }
  hallados.forEach((r, k) => {
    const d = document.createElement('div'); d.textContent = r.id + ' · ' + r.nombre + (r.letras ? ' · ' + r.letras : '') + (r.prioridad ? ' · ' + r.prioridad : '');
    if (k === 0) d.className = 'on';
    d.onclick = () => ir(r); res.appendChild(d);
  });
});
buscar.addEventListener('keydown', e => {
  if (e.key === 'Enter' && hallados.length) ir(hallados[0]);
  if (e.key === 'Escape') { buscar.value = ''; res.innerHTML = ''; hallados = []; }
});
document.getElementById('plegar').onclick = e => {
  const p = document.getElementById('panel'); p.classList.toggle('cerrado'); e.target.textContent = p.classList.contains('cerrado') ? 'mostrar' : 'ocultar';
  setTimeout(() => mapa.invalidateSize(), 50);
};
activar(0);
</script></body></html>
"""
