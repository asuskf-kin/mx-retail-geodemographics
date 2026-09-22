# Mérida: perfil socioeconómico de hogares y tiendas (DENUE 462111 / 462112)

Corre los notebooks en orden desde la carpeta `notebooks/`:

| Paso | Notebook | Qué hace | Salida principal |
|---|---|---|---|
| 01 | `01_socioeconomico_merida.ipynb` | Descarga Censo 2020 (AGEB + muestra), Marco Geoestadístico y ENIGH 2024; estima por AGEB el tamaño de hogar, la edad del menor, la edad del jefe y el NSE AMAI 2022 | `outputs/01_nse_ageb_zm_merida.xlsx` |
| 02 | `02_tiendas_denue_merida.ipynb` | Descarga el DENUE vigente y filtra supermercados, minisupers (462111/462112) y abarrotes (461110) de la ZM; identifica la cadena, el canal Moderno/Tradicional y las altas recientes; cruza con OpenStreetMap | `outputs/02_tiendas_moderno_zm_merida.xlsx`, `outputs/02_tiendas_tradicional_zm_merida.xlsx` |
| 03 | `03_union_tiendas_nse.ipynb` | Une tiendas y hogares: la AGEB de cada tienda, sus áreas de influencia de 500 m y 1 km (dasimétrico por manzana) y la competencia | `outputs/03_moderno_x_nse_zm_merida.xlsx`, `outputs/03_tradicional_x_nse_zm_merida.xlsx` |

La configuración está en `src/config.py`: municipios de la ZM, la referencia del índice (`zm` o `estado`), los códigos SCIAN y las URLs.
Los `.ipynb` se generan desde `notebooks/_src/*.py` con este comando:
`python src/py2nb.py notebooks/_src/01_socioeconomico_merida.py notebooks/01_socioeconomico_merida.ipynb`

## Supuestos metodológicos
- **Año base.** Los datos de hogares son del Censo 2020. El DENUE es la edición vigente (05/2026). La ENIGH 2024 solo se usa para imputar dos variables.
- **NSE AMAI 2022.** Puntos y cortes tomados del cuestionario oficial de AMAI. El Censo no pregunta *cuántos* baños completos ni *cuántos* autos hay, solo si existen. Para distinguir 1 de 2 o más se usa un logit entrenado con ENIGH 2024 (sureste urbano). Cada hogar se reparte en probabilidades entre niveles. El Censo pregunta por el trabajo de la "semana pasada"; AMAI pregunta por el "último mes".
- **Baño completo.** Se cuenta cuando la vivienda tiene regadera y taza de baño (excusado).
- **Niños.** La clasificación usa la edad del integrante *más joven* menor de 18. "Niño 12+" significa 12 a 17 años.
- **AGEB.** Microsimulación espacial IPU. Se calibra a 24 totales publicados por AGEB, usando como donantes los hogares de la muestra censal de la ZM.
- **Índice.** Se calcula como % de la unidad / % de la referencia × 100.
- **Canal.** Moderno = tienda de una cadena identificada por nombre o razón social. Tradicional = abarrotes, misceláneas y minisupers independientes. Los abarrotes afiliados a Six (Grupo Modelo) cuentan como Tradicional.
- **ZM Mérida.** Incluye Conkal, Kanasín, Mérida, Ucú y Umán (delimitación 2020).
