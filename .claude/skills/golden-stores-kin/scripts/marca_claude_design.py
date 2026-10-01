"""Aplica los lineamientos de la skill brand-guidelines-kin (canon: Kin Design System, template "Kin Presentation")
a un deck de Claude Design (artifact tipo Slides) descargado con `Artifact` → `read` (carpeta con `project/slides/*.html`).

Uso:
    python .claude/skills/golden-stores-kin/scripts/marca_claude_design.py <carpeta_deck> [<carpeta_deck> ...]
      → normaliza las láminas de CONTENIDO: eyebrow gris (sin píldora), pie logo + kinanalytics.com (Albert Sans 500, Gray 3),
        fondo Gray 1 (#EFEFEE) en lugar de #F2F2F2, grises fuera de paleta → Gray 4 / Gray 2.
    Portada, divisores y cierre se escriben con portada(), divisor() y cierre() (importar este módulo; ver
    references/claude_design_marca.md). Sus ids van en ESPECIALES para que la pasada de contenido no los toque.
Los assets (cover-duotone.jpg, kin-mark-yellow-hex.png, …) se copian del DS al publicar (ver la referencia).
"""
import pathlib, re, sys
SG = "'Space Grotesk', Arial, sans-serif"; AS = "'Albert Sans', Arial, sans-serif"
A = "project/ds/kin/templates/kin-presentation/assets/"
FOTO = A + "cover-duotone.jpg"
ESPECIALES = {"cover", "cierre_foto", "9f34f8c6"}   # + todo id que empiece con "div-"
PILL = f"<p style=\"align-self:start;font-family:{SG};font-size:24px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:#e5ff01;background:#141417;padding:8px 20px;border-radius:999px\">"
EYEBROW = f"<p style=\"font-family:{AS};font-size:24px;font-weight:600;letter-spacing:6px;text-transform:uppercase;color:#999ea6\">"
LOGO_OLD = 'style="position:absolute;left:96px;bottom:52px;width:240px;height:48px;object-fit:contain"'
LOGO_NEW = 'style="position:absolute;left:56px;bottom:40px;width:300px;height:60px;object-fit:contain"'
URL_OLD = '<p style="position:absolute;right:96px;bottom:60px;width:400px;font-size:26px;text-align:right;color:#444444">'
URL_NEW = f'<p style="position:absolute;right:56px;bottom:48px;width:400px;font-family:{AS};font-size:28px;font-weight:500;text-align:right;color:#999ea6">'

def fondo(variante, velo):
    if variante == "C": return ""
    if variante == "B": return ""
    return (f'<img src="{FOTO}" alt="" style="position:absolute;left:0px;top:0px;width:1920px;height:1080px;object-fit:cover">\n'
            f'<div style="position:absolute;left:0px;top:0px;width:1920px;height:1080px;background:#141417;opacity:{velo}"></div>\n')
def portada(eyebrow, titulo, subtitulo, meta, notas):
    m = "".join(f'<div style="display:flex;flex-direction:column;gap:8px"><p style="font-family:{AS};font-size:24px;font-weight:600;letter-spacing:4px;text-transform:uppercase;color:#999ea6">{k}</p>'
                f'<p style="font-family:{SG};font-size:28px;font-weight:600;color:#ffffff">{v}</p></div>' for k, v in meta)
    return f'''<section id="cover" data-transition="fade" style="background:#222326;color:#ffffff;font-family:{AS};padding:0px;display:flex;flex-direction:column">
{fondo("A", 0.12)}<img src="{A}kin-mark-yellow-hex.png" alt="Kin" style="position:absolute;left:40px;top:24px;width:240px;height:150px;object-fit:contain">
<div style="position:absolute;left:72px;top:540px;transform:translateY(-50%);width:1100px;display:flex;flex-direction:column;gap:24px;background:#141417;padding:80px 92px 84px;border-radius:12px">
<p style="font-family:{AS};font-size:24px;font-weight:600;letter-spacing:6px;text-transform:uppercase;color:#e5ff01">{eyebrow}</p>
<h1 style="font-family:{SG};font-size:104px;font-weight:600;line-height:1;letter-spacing:-3px;color:#e5ff01">{titulo}</h1>
<p style="font-family:{SG};font-size:40px;font-weight:400;line-height:1.2;letter-spacing:-1px;color:#ffffff">{subtitulo}</p>
<div style="display:flex;gap:64px;padding:26px 0px 0px 0px">{m}</div>
</div>
<div style="position:absolute;right:72px;bottom:54px;width:520px;display:flex;flex-direction:column;align-items:flex-end;gap:6px">
<p style="font-family:{SG};font-size:24px;font-weight:600;text-align:right;color:#ffffff">Kin Analytics© 2026</p>
<p style="font-family:{AS};font-size:24px;font-weight:600;letter-spacing:4px;text-transform:uppercase;text-align:right;color:#e5ff01">Confidential</p>
</div>
<aside>{notas}</aside>
</section>
'''
def divisor(sid, variante, num, titulo, linea, notas):
    claro = variante == "C"
    bg = "#d4d5d6" if claro else ("#222326" if variante == "A" else "#141417")
    tinta = "#141417" if claro else "#ffffff"; numc = "#141417" if claro else "#e5ff01"
    return f'''<section id="{sid}" data-transition="fade" style="background:{bg};color:{tinta};font-family:{AS};padding:0px;display:flex;flex-direction:column">
{fondo(variante, 0.45)}<svg aria-label="Panel amarillo con punta de hexágono" viewBox="0 0 730 1080" width="730" height="1080" style="position:absolute;left:1190px;top:0px;width:730px;height:1080px"><polygon points="190,0 0,540 190,1080 730,1080 730,0" fill="#E5FF01"/></svg>
<p style="position:absolute;left:72px;top:48px;width:600px;font-family:{SG};font-size:132px;font-weight:700;line-height:0.9;letter-spacing:-5px;color:{numc}">{num}.</p>
<div style="position:absolute;left:72px;top:430px;width:1100px;display:flex;flex-direction:column;align-items:flex-start;gap:14px">
<h2 style="font-family:{SG};font-size:88px;font-weight:700;line-height:1.05;letter-spacing:-2.5px;color:{tinta}">{titulo}</h2>
<p style="font-family:{SG};font-size:88px;font-weight:700;line-height:1.1;letter-spacing:-2.5px;color:#141417;background:#e5ff01;padding:2px 18px">{linea}</p>
</div>
<img src="{A}kin-mark-black-hex.png" alt="Kin" style="position:absolute;right:40px;bottom:24px;width:240px;height:150px;object-fit:contain">
<aside>{notas}</aside>
</section>
'''

def cierre(sid, titulo, linea, notas="Cierre."):
    return f'''<section id="{sid}" data-transition="fade" style="background:#222326;color:#ffffff;font-family:{AS};padding:128px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:40px">
{fondo("A", 0.5)}<h2 style="font-family:{SG};font-size:120px;font-weight:600;line-height:1.05;letter-spacing:-2px;text-align:center;color:#ffffff">{titulo}</h2>
<p style="font-size:34px;line-height:1.4;text-align:center;color:#e5ff01">{linea}</p>
<img src="{A}kin-analytics-logo-dark.png" alt="Kin Analytics" style="width:360px;height:72px;object-fit:contain">
<aside>{notas}</aside>
</section>
'''

def contenido(raices, especiales=ESPECIALES):
  for raiz in raices:
    for f in sorted(pathlib.Path(raiz, "project/slides").glob("*.html")):
        if f.stem in especiales or f.stem.startswith('div-'): continue
        t = f.read_text(encoding="utf-8"); o = t
        t = t.replace(PILL, EYEBROW).replace(LOGO_OLD, LOGO_NEW).replace(URL_OLD, URL_NEW)
        t = re.sub(r'(<section [^>]*?)background:#f2f2f2', r'\1background:#efefee', t, count=1)
        t = t.replace("#1e1e1e", "#222326").replace("#b3b3b3", "#d4d5d6")
        t = t.replace("letter-spacing:-1px;color:#141417", "letter-spacing:-1.6px;color:#141417")
        if f.stem == "cierre" and "Siguientes pasos" in t:   # Letras: lámina de contenido oscura
            t = t.replace(f"<p style=\"align-self:start;font-family:{SG};font-size:28px;font-weight:600;letter-spacing:4px;text-transform:uppercase;color:#e5ff01\">",
                          f"<p style=\"font-family:{AS};font-size:24px;font-weight:600;letter-spacing:6px;text-transform:uppercase;color:#e5ff01\">")
            t = t.replace('style="position:absolute;left:128px;bottom:72px;width:300px;height:60px;object-fit:contain">',
                          LOGO_NEW + '>\n' + URL_NEW + 'kinanalytics.com</p>')
        if t != o: f.write_text(t, encoding="utf-8"); print("ok", f.parent.parent.parent.name[:8], f.stem)

if __name__ == "__main__":
    contenido(sys.argv[1:])
