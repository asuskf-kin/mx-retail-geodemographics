"""Mapas de QA del notebook 06: fondo para mapas estáticos (matplotlib) y mapa interactivo en HTML.

El HTML usa Leaflet y h3-js desde CDN y un fondo libre con datos de OpenStreetMap: OpenFreeMap (estilo gris "Positron",
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
import html
import json
import math

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
    pagina = _PLANTILLA.replace("__TITULO__", html.escape(titulo)).replace("__DATOS__", js)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(pagina)
    return ruta


_PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js"></script>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.9.0/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@5.9.0/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js"></script>
<style>
:root{--tinta:#0b0b0b;--tinta2:#52514e;--muted:#898781;--linea:#e1e0d9;--fondo:#fcfcfb;--acento:#e5ff01}
*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:Arial,Helvetica,sans-serif;color:var(--tinta);background:var(--fondo)}
#app{display:flex;height:100%}#panel{width:380px;min-width:300px;overflow-y:auto;border-right:1px solid var(--linea);padding:14px 16px}
#mapa{flex:1}h1{font-size:17px;margin:0 0 2px}.sub{color:var(--tinta2);font-size:12px;margin-bottom:10px}
.pasos button{display:block;width:100%;text-align:left;border:1px solid var(--linea);background:#fff;padding:7px 9px;margin:4px 0;
 border-radius:6px;cursor:pointer;font-size:12.5px}.pasos button.on{background:var(--tinta);color:#fff;border-color:var(--tinta)}
#texto{font-size:12.5px;line-height:1.45;margin-top:10px}#texto h3{font-size:14px;margin:6px 0}#texto .f{background:#f3f3ef;border-left:3px solid var(--acento);
 padding:6px 8px;font-family:Consolas,monospace;font-size:11.5px;white-space:pre-wrap}#leyenda{margin-top:10px;font-size:12px}
.sw{display:inline-block;width:11px;height:11px;border-radius:50%;margin:0 5px -1px 0;border:1px solid #fff;box-shadow:0 0 0 1px #ccc}
.grad{height:10px;border-radius:3px;margin:3px 0}.lab{display:flex;justify-content:space-between;color:var(--tinta2);font-size:11px}
#buscar{width:100%;padding:6px 8px;border:1px solid var(--linea);border-radius:6px;margin:8px 0 2px;font-size:12.5px}
#res div{padding:3px 6px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--linea)}#res div:hover{background:#f3f3ef}
#filtro{font-size:12.5px;margin:8px 0 4px;padding:6px 8px;background:#f3f3ef;border-radius:6px}#filtro label{margin-right:12px;cursor:pointer;white-space:nowrap}
.dist{display:flex;height:10px;width:220px;border-radius:3px;overflow:hidden;margin:5px 0 3px;background:#eee}.dist span{display:block;height:100%}
.dist-lab{font-size:11px;line-height:1.4}.dist-tit{font-size:11.5px;color:var(--tinta2);margin-bottom:1px}
.nota{color:var(--muted);font-size:11px;margin-top:10px}.ficha td{padding:1px 6px 1px 0;font-size:11.5px;vertical-align:top}.ficha td:first-child{color:var(--tinta2)}
@media (max-width:760px){#app{flex-direction:column}#panel{width:100%;height:45%;border-right:0;border-bottom:1px solid var(--linea)}}
</style></head><body><div id="app"><div id="panel">
<h1 id="t"></h1><div class="sub" id="s"></div>
<div id="filtro"></div><input id="buscar" placeholder="Buscar PDV por ID o nombre"><div id="res"></div>
<div class="pasos" id="pasos"></div><div id="texto"></div><div id="leyenda"></div>
<div class="nota">Clic en un punto: su radio, lo que queda dentro y su ficha con las fórmulas. Fondo libre OpenFreeMap (datos © colaboradores de OpenStreetMap): sin API key, funciona abriendo el archivo con doble clic.</div>
</div><div id="mapa"></div></div>
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
function rgb(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
function continuo(v, e) {
  if (v === null || v === undefined || isNaN(v)) return null;
  const t = Math.max(0, Math.min(1, (v - e.min) / (e.max - e.min))) * (e.colores.length - 1);
  const i = Math.min(Math.floor(t), e.colores.length - 2), a = rgb(e.colores[i]), b = rgb(e.colores[i + 1]), f = t - i;
  return 'rgb(' + a.map((x, j) => Math.round(x + (b[j] - x) * f)).join(',') + ')';
}
const color = (v, e) => e.tipo === 'categorica' ? (e.colores[v] || '#c3c2b7') : continuo(v, e);
function pasa(r, filtro) { return !filtro || r[filtro[0]] === filtro[1]; }
const F = D.filtro, activos = new Set(F ? F.valores : []);         // filtro del panel (p. ej. canal)
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
        .bindTooltip(() => c.nombre + ': ' + fmt(v) + je.map(([e, jj]) => '<br>' + e + ': <b>' + fmt(vals[jj]) + '</b>').join('') +
          barra(jd.map(([e, jj, col]) => [e, vals[jj], col])), {sticky: true});
      if (porId && porId[h]) pol.on('click', () => seleccionar(c.seleccion, porId[h]));
      pol.addTo(g);
    }
  } else if (c.tipo === 'poligonos') {
    L.geoJSON(D.poligonos[c.fuente], {renderer: lienzo, style: f => ({color: '#ffffff', weight: 0.7, fillColor: color(f.properties[c.campo], c.escala) || '#e1e0d9',
      fillOpacity: c.opacidad || 0.55}), onEachFeature: (f, l) => l.bindTooltip(() => (c.etiqueta ? f.properties[c.etiqueta] + ' · ' : '') + c.nombre + ': ' + fmt(f.properties[c.campo]) +
      barra((c.distribucion || []).map(([e, k, col]) => [e, f.properties[k], col])), {sticky: true})}).addTo(g);
  } else if (c.tipo === 'puntos') {
    for (const r of DS[c.dataset]) {
      if (!pasa(r, c.filtro) || !visible(c.dataset, r)) continue;
      const rad = c.tamano ? Math.max(3, Math.min(18, Math.sqrt(Math.max(r[c.tamano] || 0, 0)) * (c.escala_tamano || 0.5))) : (c.radio_px || 4);
      L.circleMarker([r.lat, r.lon], {renderer: lienzo, radius: rad, color: '#ffffff', weight: 0.7, fillColor: color(r[c.campo], c.escala) || '#c3c2b7', fillOpacity: 0.9})
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
    notas.push('Clúster NSE (azul): el hexágono y su centro (punto azul); ' + miembros.length +
               ' PDV del hexágono comparten su NSE (Letra 1).');
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
    notas.push('Buffer de ' + D.radio + ' m del punto (negro, sin contarlo): ' + mismo.length + ' PDV con venta ' +
      (r.canal === undefined ? '(negro, referencia)' : 'de su canal (negro, su clúster) y ' + otros.length + ' del otro canal (gris, no cuentan)') +
      ' · ' + rap.length + ' tiendas Rappi (rojo; su venta media es el Rappi del PDV)' + (rap.length ? ': ' + rap.slice(0, 5).map(p => p.nombre + (p.activa ? ' (activa)' : ' (esporádica)')).join(', ') : ''));
  }
  let t = '<table class="ficha">' + (D.popup[ds] || []).map(([e, k]) => '<tr><td>' + e + '</td><td><b>' + fmt(r[k]) + '</b></td></tr>').join('') + '</table>';
  const dp = (D.dist_popup || {})[ds];
  if (dp) t = '<div class="dist-tit">' + dp.titulo + '</div>' + barra(dp.partes.map(([e, k, col]) => [e, r[k], col])) + '<hr style="border:0;border-top:1px solid #e1e0d9">' + t;
  t += '<div class="nota">' + notas.join('<br>') + '</div>';
  L.popup({maxWidth: 380}).setLatLng(donde).setContent(t).openOn(mapa);
}
function leyenda(ids) {
  let h = '';
  for (const id of ids) {
    const c = capaPor[id]; if (!c.escala) continue;
    h += '<div style="margin-top:6px"><b>' + c.nombre + '</b><br>';
    if (c.escala.tipo === 'categorica') h += Object.entries(c.escala.colores).map(([k, v]) => '<span class="sw" style="background:' + v + '"></span>' + (c.escala.etiquetas && c.escala.etiquetas[k] || k)).join('<br>');
    else h += '<div class="grad" style="background:linear-gradient(90deg,' + c.escala.colores.join(',') + ')"></div><div class="lab"><span>' + (c.escala.bajo || fmt(c.escala.min)) + '</span><span>' + (c.escala.alto || fmt(c.escala.max)) + '</span></div>';
    h += '</div>';
  }
  document.getElementById('leyenda').innerHTML = h;
}
function activar(i) {
  const p = D.pasos[i];
  pasoActual = i;
  document.querySelectorAll('.pasos button').forEach((b, j) => b.classList.toggle('on', j === i));
  for (const id in capas) mapa.removeLayer(capas[id]);
  for (const id of p.capas) { if (!capas[id]) capas[id] = construir(capaPor[id]); capas[id].addTo(mapa); }
  document.getElementById('texto').innerHTML = '<h3>' + p.titulo + '</h3><p><b>Qué se hace:</b> ' + p.que + '</p><p><b>Por qué:</b> ' + p.porque + '</p>' +
    (p.formula ? '<div class="f">' + p.formula + '</div>' : '') + (p.cifras ? '<p>' + p.cifras + '</p>' : '');
  leyenda(p.capas);
}
D.capas.filter(c => c.siempre).forEach(c => construir(c).addTo(mapa));      // contexto fijo (p. ej. límite municipal)
D.pasos.forEach((p, i) => { const b = document.createElement('button'); b.textContent = p.titulo; b.onclick = () => activar(i); document.getElementById('pasos').appendChild(b); });
if (F) {
  const box = document.getElementById('filtro');
  box.innerHTML = '<b>' + F.etiqueta + ':</b> ' + F.valores.map(v => '<label><input type="checkbox" value="' + v + '" checked> ' + v + ' (' +
    DS[F.dataset].filter(r => r[F.campo] === v).length.toLocaleString('es-MX') + ')</label>').join('');
  box.querySelectorAll('input').forEach(inp => inp.onchange = () => {
    inp.checked ? activos.add(inp.value) : activos.delete(inp.value);
    for (const id in capas) if (capaPor[id].dataset === F.dataset) { mapa.removeLayer(capas[id]); delete capas[id]; }   // se redibujan con el filtro
    sel.clearLayers(); mapa.closePopup(); activar(pasoActual);
  });
}
document.getElementById('buscar').addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase(), res = document.getElementById('res'); res.innerHTML = '';
  if (q.length < 2) return;
  (DS.pdv || []).filter(r => visible('pdv', r) && (String(r.id).includes(q) || String(r.nombre).toLowerCase().includes(q))).slice(0, 8).forEach(r => {
    const d = document.createElement('div'); d.textContent = r.id + ' · ' + r.nombre;
    d.onclick = () => { mapa.setView([r.lat, r.lon], 17); seleccionar('pdv', r); }; res.appendChild(d);
  });
});
activar(0);
</script></body></html>
"""
