# Datos del cliente: qué pedir y cómo validarlos (notebook 00)

## Qué pedir (si falta, no se avanza)

| Archivo | Campos mínimos | Nota |
|---|---|---|
| Ventas por PDV | id de PDV · categoría · cantidad vendida en el periodo · meses con venta · primera y última fecha de venta | Bepensa: `pos_id, custom_category, total_boxes_sold, n_active_months, min_sale_date, max_sale_date, avg_monthly_boxes` |
| Customer Potential | id de PDV · nombre · **latitud, longitud** · ciudad/municipio · subcanal · tamaño · potencial cuantitativo, final y cualitativo · id comparativo | Bepensa: `conservative_scenario.csv` |
| Ideal (pedir aunque sea opcional) | tabla de equivalencias entre el id de ventas y el id del CP; coordenadas de las cuentas clave | Sin eso, parte de la venta queda fuera del mapa |

## Validaciones del 00 (método retail-math-eda)

1. **Grano y llaves** únicas; sin negativos; `avg = total / meses` verificado.
2. **Llave ventas ↔ CP.** Si no empata directo, buscar el id del CP embebido en el de ventas (sufijo, prefijo, segmento).
   Bepensa: id de ventas = **prefijo de 4 dígitos (centro de distribución) + pos_id del CP a 6 dígitos**. Probarla con
   (a) binomial del empate vs azar (73% vs 3.7%) y (b) pureza geográfica por prefijo vs 200 permutaciones (0.71 vs 0.16).
   Siempre marcarla como "inferida: confirmar con el cliente".
3. **Nulos MNAR**: el potencial del CP falta exactamente en PDV sin venta (V de Cramér = 1).
4. **Coordenadas**: escala perdida, lat/lon invertidas, signo; caja de la región; municipio por polígono del Marco
   Geoestadístico (no confiar en `pos_city`).
5. **Filtro a la ZM** por polígono municipal. Ventas de la ZM sin empate = "no ubicables": cuantificar su % de cajas y su
   sesgo (δ de Cliff para el PDV típico + concentración en pocas cuentas grandes).
6. **Métricas**: `cajas_mes_vida` (señal principal), tasa de actividad, recencia, estado (activo / en riesgo / inactivo),
   Kaplan-Meier de permanencia, cola pesada (Hill, AIC), Gini.
7. **Señales del CP**: prueba de fuga (árbol de 1 variable con CV: `size_class` 97.5% → fuga), identidades
   (`Final = Quantitative × Cover`; `Quantitative` ≈ venta actual → fuga), Spearman con IC y MI (q de BH), chequeo de
   Simpson por subcanal, Kruskal-Wallis con ε² e IC.
8. **Canal**: `src/cadenas.py` (misma regla que DENUE) sobre el nombre del PDV.

Todo con semilla fija (`eda.SEMILLA`) y resultados en la hoja **Hallazgos** del Excel del 00.
