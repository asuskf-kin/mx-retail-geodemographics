---
name: golden-stores-kin
description: Replica para un cliente (ventas + Customer Potential) la metodología Golden Stores (NielsenIQ/Spectra) sobre sus puntos de venta de una zona metropolitana de México y genera la presentación con el estilo Kin Analytics — validación de ventas × CP, perfil NSE a 300 m de cada PDV en hexágonos H3, clústeres HH/HL/LH/LL, semáforos, priorización y entregable Excel. Usar cuando pidan "golden stores", "tiendas más valiosas", "presentación / deck / pptx del análisis", "hazlo para otro cliente / otra ciudad / otro canal", "cuadrantes demanda × venta", "semáforos por clúster", o cuando lleguen archivos de ventas y CP de un cliente.
---

# Golden Stores × Kin (cliente con ventas + CP)

Este repo ya tiene todo el proceso. **No lo reescribas**: se configura y se corre. Lee primero `.claude/CLAUDE.md`.
Detalle de cada pieza: [metodologia_golden_stores.md](references/metodologia_golden_stores.md) (la metodología, fija),
[estilo_kin.md](references/estilo_kin.md) (diseño del deck y QA) y [datos_cliente.md](references/datos_cliente.md)
(qué pedir al cliente y cómo validarlo).

## Instalación (una vez por máquina)

```bash
python .claude/skills/golden-stores-kin/scripts/instalar.py     # instala requirements, registra el kernel, verifica LibreOffice y datos
```
Si pip dice que un archivo está en uso, cierra los kernels de Jupyter/VS Code de ese Python y repite (una instalación
interrumpida deja paquetes rotos, p. ej. pyproj sin su DLL: `instalar.py --solo-verificar` los detecta).

## Paso 0 — Datos del cliente (OBLIGATORIO, sin esto no se avanza)

Busca en `data/raw/<cliente>/` los dos insumos:

1. **Ventas por punto de venta** (`ventas/*.csv`): id de PDV, cantidad vendida en el periodo, meses activos, primera y última venta.
2. **Customer Potential** (`cp/*.csv`): id de PDV, **latitud y longitud**, subcanal, tamaño y potencial (cuantitativo, final, cualitativo).

**Si falta cualquiera de los dos: DETENTE y pídelo al usuario** (con la lista de campos de `datos_cliente.md`).
No inventes datos, no uses otra fuente como sustituto y no corras los notebooks 00, 04 ni 05. Todo lo demás (Censo,
ENIGH, Marco Geoestadístico, DENUE, AMAI) se descarga solo.

## Paso 1 — Configurar

En `src/config.py`: `CLIENTE`, `CLIENTE_CIUDAD`, las rutas `CLIENTE_VENTAS` / `CLIENTE_CP` y el bloque de la ciudad en
`CIUDADES` (si la ciudad es nueva, sigue la skill `/nse-tiendas-mx` para ZM, ENIGH y URLs). `RADIO_PDV_M = 300`.

## Paso 2 — Correr (en paralelo, ~2 min para Mérida)

```bash
python src/correr.py --pasos 00,01,02,03,04,05 <ciudad>
```
00 valida ventas × CP (variable 1: venta) · 01 hogares por AGEB · 02 tiendas DENUE · 04 perfil a ≤ 300 m (variable 2:
demanda potencial) · 05 Golden Stores + deck + Excel. Los ejecutados quedan en `notebooks/ejecutados/<ciudad>/`.

## Paso 3 — Revisar antes de entregar

- **00 → hoja Hallazgos:** llave ventas ↔ CP (si el ID no empata directo, inferirla y probarla: ver `datos_cliente.md`),
  cobertura, % de cajas sin ubicar, señales con fuga. Si la llave no se puede probar, **pregunta** antes de seguir.
- **02:** cadenas locales detectadas dentro de abarrotes (falsos positivos) y cadenas nuevas del cliente → `src/cadenas.py`.
- **04 → Robustez:** asociaciones que sobreviven al bootstrap espacial por bloques.
- **05 → sección 2b (QA) y 2c (piloto):** brecha HL vs HH real vs al azar (si son iguales, no es oportunidad), actividad por
  clúster, Spearman demanda vs venta, % frontera, excluidas sin hogares, y MDE del piloto por universo. Los títulos con cifras se
  calculan, no se escriben a mano.
- **Fuentes:** revisar si hay ediciones nuevas (Marco Geoestadístico, DENUE semestral, Intercensal, Regla AMAI) y actualizar `FUENTES`
  / `MG_VERSION` en `src/config.py`. La demanda usa hogares por área de manzana + localidades rurales, actualizados con la Intercensal.

## Paso 4 — Presentación ejecutiva y Excel (QA obligatorio)

El 05 genera `outputs/<ciudad>/05_golden_stores_<canal>_<cliente>_zm_<ciudad>.pptx` y `.xlsx`:
- **Deck**: metodología Golden Stores intacta, contada con la skill `/executive-pitch-presentation-builder` (BLUF: resumen y
  decisión primero; costo de la inacción; solución; evidencia; caso de negocio en cajas; ruta de 90 días con puertas de
  decisión; riesgos; anexo con metodología, datos y objeciones). Titulares de acción con cifras calculadas, **ejemplos con
  tiendas reales** (una por clúster y un recorrido paso a paso) y guion en las notas de cada lámina.
- **Excel corporativo** (`src/excel_kin.py`): Portada con índice · Resumen con fórmulas vivas sobre Tiendas · Tiendas
  (clúster y semáforo con color, P1, barras de datos, filtros) · Perfiles · Accionables · Guion y objeciones · Diccionario.

QA: `python .claude/skills/golden-stores-kin/scripts/qa_deck.py <deck.pptx> [carpeta]` y **mirar cada lámina**; validar el
pptx con la skill pptx; recalcular el Excel con LibreOffice y confirmar que el Resumen coincide con el notebook.

## Decisiones que NO asumas: pregúntalas

- **Canal target** del deck (`CANALES_DECK` en el 05). Bepensa: Tradicional.
- Municipios de la ZM si solo dan la ciudad · radio del área (default 300 m; 500 m se consideró demasiado lejos).
- Clasificación de franquicias y cadenas de farmacias (Bepensa: Six = Tradicional; Modelorama y farmacias de cadena = Moderno).

## Reglas fijas (decididas con el usuario)

- **La metodología Golden Stores no se cambia** (clústeres, índice 100, accionables Atacar/Bloquear/Fortalecer/Mantener,
  semáforos, P1 = HH y LH en verde y amarillo). Solo se sustituyen las fuentes de ventas y demanda.
- **El CP es potencial futuro: variable de clasificación, no decisiva.**
- La unidad es el PDV: no calificar la ZM completa ni por demografía agregada.
- Moderno y Tradicional se analizan y entregan por separado.
