# Metodología Golden Stores (fija: no modificar)

Fuente: NielsenIQ | Spectra, "Golden Stores Sueros Nacional Pharma – KO FY'23" (y "Golden Stores Hidratación R. Norte").
Implementación: `notebooks/_src/05_presentacion_pdv.py`. Lo único que cambia son las fuentes de las dos variables.

## Las dos variables de cada tienda

| Golden Stores (NIQ) | Implementación Kin |
|---|---|
| **Ventas de la tienda**: valor / volumen del periodo (Scantrack) | Cajas por mes de vida del PDV (`cajas_mes_vida`, notebook 00). No `avg_monthly_boxes`: sobreestima a inactivos |
| **Demanda potencial** con base en el área transaccional (tiempo de manejo, sociodemográficos, compras del hogar, competidores, m²) | Hogares a ≤ 300 m del PDV (hexágonos H3 res 10, notebook 04) con su perfil (tamaño, niños, edad del jefe, NSE AMAI 2024) y competidores DENUE |

## Clústeres (índice 100 = promedio del mercado)

- Índice de venta = venta del PDV / promedio × 100; índice de demanda = hogares del área / promedio × 100.
- El promedio se toma **dentro de cada subcanal** del canal target (el subcanal cambia la escala de venta: Farmacias
  vende ~8× lo de Hogar con venta). Alta = índice ≥ 100. Por eso los clústeres salen desiguales (p. ej. 14/33/20/32%).

| Clúster | Demanda | Venta | Acción | Accionables (textuales) |
|---|---|---|---|---|
| **HH = Golden Stores** (alto impacto) | alta | alta | **Atacar** | Más SOS · Exhibiciones · Special packs · Ítems exclusivos · Reducciones de precio · Comunicación · Promoción |
| **HL** | alta | baja | **Bloquear** | Evitar desarrollo de competencia · Estrategia reactiva · Seguir estrategias de precio · Cuidar anaquel (SOS) |
| **LH** | baja | alta | **Fortalecer** | Incrementar exhibiciones · Cuidar anaquel (SOS) · Considerar special packs |
| **LL** | baja | baja | **Mantener** | Mantener distribución · Mantener anaquel |

Matriz: demanda en el eje vertical, ventas en el horizontal → HL arriba-izquierda, HH arriba-derecha, LL abajo-izquierda,
LH abajo-derecha. (Lámina conceptual NIQ: Hogares × Tráfico → Alto impacto / Residencial / Tráfico / Bajo impacto.)

## Panorama por clúster

- Título tipo NIQ, calculado: "El X% de las tiendas HH hacen el Y% de las ventas de <categoría> en <canal>".
- Banda "Target: <categoría> · N tiendas". Por clúster: **# Tiendas (%) · % Mix ventas · Index ventas** (promedio del
  clúster / promedio total × 100).
- **Perfil de hogares** por clúster (4 columnas HH, HL, LH, LL): barra con el % de cada categoría (tamaño hogar,
  presencia de niños, edad del jefe, NSE; cada grupo suma 100) e índice vs total de la ZM; resaltar índices ≥ 105.
- Mix de tiendas por región → aquí por municipio y subcanal. Cadenas principales en los clústeres de alta venta
  (si el canal tiene cadenas).
- **Mensajes clave** (3): peso de las Golden Stores en ventas y su índice vs promedio; dónde se ubican y qué hogares
  alcanzan; el segundo clúster en ventas (normalmente LH) o la cadena líder.

## Semáforos por clúster (priorización)

Individualizados por clúster, con desviación estándar dentro del clúster (z de la venta en log por la cola pesada; z de la demanda):
- **Verde**: venta y demanda sobre el promedio del clúster (z > 0 en ambas).
- **Rojo**: ambas bajo el promedio (z < 0 en ambas).
- **Amarillo**: alrededor de los promedios (|z| ≤ 0.5 en ambas, "#2") o subdesarrollo en una: "#1" alta venta / demanda
  baja, "#3" demanda alta / venta menor.
- **P1**: capitalizar con los clústeres de alta venta **HH y LH** en semáforo **verde y amarillo** (tabla clúster × semáforo).
- P2 de NIQ (clústeres de alta venta de la competencia) requiere ventas de competidores: solo si el cliente las da.

## Customer Potential (CP)

Potencial **futuro** de cada cliente frente a su comparable. Se muestra como **clase (Very High → Low) dentro de cada
clúster** y en el entregable: clasifica, **no decide** el orden ni reemplaza a los clústeres.
Ojo: `PotentialQuantitative` = venta actual (fuga) y `size_class` = quintiles de la venta (fuga). El potencial útil es
`PotentialQuantitativeFinal` (= Quantitative × EstimatedToCover) y su clase `PotentialQualitative`.

## Orden del deck (22 láminas)

Portada → Agenda (Metodología · Panorama general · Perfil por clúster · Priorización por tienda) → ¿Dónde se encuentran
las tiendas más valiosas? (6 pasos) → 2 variables clave → 4 segmentos → accionables → Set up (mercado, periodo, target,
líneas de reporte, semáforos, clasificación CP) → separador Panorama → panorama por clúster → perfil de hogares → mix por
municipio y subcanal → clasificación CP → mensajes clave → separador ¿Cómo priorizo acciones? → semáforos → tiendas de
mayor oportunidad (P1) → Golden Stores en verde (lista) → entregable Excel → anexo (calidad de datos 00, robustez 04) → cierre.

Limitaciones a declarar en el Set up: sin SKU/marca no hay share, distribución ni precio por clúster; hogares del Censo
2020 (no proyectados); ventas del cliente sin llave con el CP quedan fuera del mapa.

## Controles de calidad (QA metodológico, decididos 2026-09-25)

La metodología no cambia; estos controles evitan conclusiones falsas al contarla:

| Control | Por qué | Dónde |
|---|---|---|
| Brecha HL vs HH con venta al azar | El clúster se define cortando por venta: la brecha sale ~igual con venta aleatoria (79% vs 81% en Mérida). No es oportunidad. | 05 · 2b |
| Actividad por clúster | En Mérida 56% de las HL dejó de comprar o está en riesgo: primero reactivar, después Bloquear. | 05 · 2b, lámina "Por qué ahora" |
| Demanda vs venta (Spearman) | Hogares a 300 m no predicen la venta (ρ ≈ −0.1): la demanda clasifica el área, no pronostica. | 05 · 2b, riesgos |
| Semáforo en log en ambos ejes | La demanda tiene cola derecha como la venta; misma escala para los z. | 05 · golden_stores |
| Frontera ±10 y alta reciente | ~23% de las tiendas cambia de clúster con poco ruido; tiendas de ≤ 3 meses son ruidosas. | Excel · Tiendas |
| Excluidas sin hogares | No desaparecen: hoja aparte (zonas comerciales). | Excel · Sin hogares 300 m |
| Piloto por zonas + MDE | Las áreas de 300 m se traslapan (contaminación) y 139 tiendas no detectan +10%. Sorteo de zonas H3 r7 emparejadas; MDE con efecto de diseño; se elige el universo con menor MDE. Pedir venta mensual (línea base). | 05 · 2c, Excel · Piloto |
| Clase CP y tamaño | La clase es potencial absoluto (venta × brecha): Very High no existe en la mitad inferior de venta. Leer con la brecha relativa. | 00 · 5.1b |

