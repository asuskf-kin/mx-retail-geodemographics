# Estilo Kin Analytics para presentaciones

Referencia visual: deck de Kin "Ultra segmentación · Customer Potential Model" (Femsa Guatemala, 2026). Implementación:
`src/deck_kin.py` (python-pptx). **Cambia el estilo solo ahí**; los notebooks llaman a sus funciones.

## Identidad

- 16:9 de **10 × 5.625 in**. Portadas, separadores y cierre en **negro 0A0A0A** con título blanco grande, subtítulo en
  **lima E5FF01** y un corte lima en la esquina superior derecha. Contenido en blanco.
- Paleta: negro 0A0A0A / 222326 · grises 666666, 999EA6, E0E0E0 · tarjetas F4F4F4 · acento único **lima E5FF01** · verde 22C55E.
  Semáforos: verde 22C55E, amarillo EDA100, rojo E34948 (solo para semáforos).
- Tipografía de marca: Albert Sans (texto) y Space Grotesk (títulos). **No están instaladas en todas las máquinas** y
  PowerPoint las sustituye: por defecto se usa Arial (`FUENTE_TITULO`, `FUENTE_TEXTO` en `deck_kin.py`).
- Pie en cada lámina: "Kin Analytics®" · "Let knowledge in." · "KinAnalytics.com" sobre franja gris clara.
- Etiqueta (kicker) gris en mayúsculas sobre el título; título 21 pt negrita (una idea, con la cifra calculada);
  subtítulo gris 9.5 pt; mensaje clave en barra negra con texto lima (o lima con texto negro).

## Piezas (`deck_kin`)

`portada`, `separador`, `lamina` (devuelve la y donde empieza el contenido), `tarjeta` (número en círculo lima, oscura,
acento, compacta), `cifra` (número grande), `mensaje`, `tabla` (encabezado negro, filas alternas, `resaltar` en lima),
`barras` (gráfico nativo editable), `cierre`.

## QA obligatorio (renderizar y mirar)

```bash
soffice --headless --convert-to pdf deck.pptx           # en Windows: "C:/Program Files/LibreOffice/program/soffice.exe"
python -c "import fitz; d=fitz.open('deck.pdf'); [p.get_pixmap(dpi=100).save(f'l{i+1:02d}.png') for i,p in enumerate(d)]"
python <skill pptx>/scripts/office/validate.py deck.pptx
```
Revisar: texto desbordado o encimado (títulos de 2 líneas empujan el subtítulo: `lamina` asume ~56 caracteres por línea),
tarjetas con texto que sale del borde (usar `compacta=True` en tarjetas bajas), huecos grandes, cifras que no cuadran con
los datos.

## Trampas aprendidas

- **Barras negativas**: LibreOffice (y algunos visores) las dibujan mal. Usar |valor| con color por signo (lima = +,
  gris = −) y el signo en la etiqueta.
- **Saltos de línea**: en `texto()` un "\n" crea párrafo nuevo; o pasar una lista de líneas.
- Al editar código con escapes (`\n`, `\b`) desde un heredoc de bash, pueden terminar como caracteres reales: usar el
  editor de archivos y verificar con `ast.parse` / probando el regex.
- Títulos y cifras **siempre calculados** desde los datos (nunca "~8×" escrito a mano): cambian con cada corte del cliente.
- Nombres del cliente con errores de captura ("ABARRROTES") se normalizan solo para mostrar.
- Barras apiladas: los segmentos < 3% de la barra más larga no llevan etiqueta (`deck_kin.barras` borra el dLbl por punto). No usar formatos
  condicionales tipo `[<3]""` en etiquetas: LibreOffice los aplica a todas y el QA sale sin números.
- Excel corporativo (`src/excel_kin.py`): `libro()` (Arial 9 por defecto), `portada`, `hoja_tabla` (con `ajustar` para textos
  largos y `escala` divergente para correlaciones) y `hoja_tabla_2niveles` para el layout acordado de 2 niveles (bloques del PDV
  y categoría | HHs · % · Indice; índice ≥ 105 lima, ≤ 95 gris; filas alternadas). Lo usan los Excel del 04 y del 05.
  Booleanos como Sí/No y "ABARRROTES" corregido solo al mostrar. El 05 lee la robustez del parquet del 04, no de su Excel.

