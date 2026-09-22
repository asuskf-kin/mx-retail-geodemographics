# Referencia técnica: NSE × tiendas (México)

## Fuentes y URLs (patrón por estado, `{ENT}` = 2 dígitos)
| Dato | URL | Nota |
|---|---|---|
| Censo 2020 AGEB y manzana | `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip` | utf-8-sig. Los valores `*` y `N/D` son confidenciales y se leen como NaN |
| Censo 2020 muestra (cuestionario ampliado) | `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_{abrev}_csv.zip` | trae `Viviendas{ENT}.CSV` y `Personas{ENT}.CSV` |
| Marco Geoestadístico 2020 | `https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/{ENT}_{slug}.zip` | capas `{ENT}a.shp` (AGEB urbana), `{ENT}m.shp` (manzana) y `{ENT}l.shp` (localidad urbana, campo NOMGEO) |
| ENIGH 2024 (nueva serie) | `https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/datosabiertos/conjunto_de_datos_enigh2024_ns_csv.zip` | nacional, ~100 MB |
| DENUE (vigente) | `https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip` | latin-1. La edición se lee en `metadatos/metadatos_denue.txt` |
| Regla AMAI 2022 | `https://www.amai.org/descargas/CUESTIONARIO_AMAI_2022.pdf` | la regla sigue vigente en 2024 |
| OSM (opcional) | Overpass `https://overpass-api.de/api/interpreter` | sin header User-Agent responde HTTPError; con él responde 200 |

No uses el zip del Marco Geoestadístico **nacional** (`794551132173_s.zip`): es el de todo el país. Usa el estatal (~50 MB para Yucatán).
Los servidores de INEGI cortan la conexión a media descarga (`ChunkedEncodingError` o `curl: (56)`), así que
usa siempre `src/descargas.py`, que reanuda con Range y valida el zip.

### Abreviaturas de microdatos (`ABREV_MICRO`) y regiones Nielsen
Abreviaturas en orden de clave: 01 ags · 02 bc · 03 bcs · 04 cam · 05 coa · 06 col · 07 chs · 08 chh · 09 cdmx · 10 dgo · 11 gto · 12 gro ·
13 hgo · 14 jal · 15 mex · 16 mich · 17 mor · 18 nay · 19 nl · 20 oax · 21 pue · 22 qro · 23 qroo ·
24 slp · 25 sin · 26 son · 27 tab · 28 tam · 29 tla · 30 ver · 31 yuc · 32 zac.
Las 32 fueron verificadas con HEAD el 2026-09-22; todas responden ZIP. Ojo: no son uniformes (`cam` pero `mich`; `tam` pero `tamps` no existe).

Las áreas Nielsen México son aproximadas. **Confírmalas con el usuario o con su catálogo Nielsen**:
Pacífico, Norte, Bajío, Centro, Valle de México (Metro) y Sureste (Yuc, Camp, QRoo, Tab, Chis y parte de Ver).

## Regla NSE AMAI 2022 (oficial)
| Variable | Puntos |
|---|---|
| Escolaridad del jefe | No estudió 0 · Prim inc 6 · Prim comp 11 · Sec inc 12 · Sec comp 18 · Técnica o comercial 23 · Prepa inc 23 · Prepa comp 27 · Lic inc 36 · Lic comp 59 · Maestría o doctorado 85 |
| Baños completos (regadera + WC) | 0 → 0 · 1 → 24 · 2+ → 47 |
| Autos (incluye camionetas y pickups) | 0 → 0 · 1 → 22 · 2+ → 43 |
| Internet fijo | No 0 · Sí 32 |
| Ocupados de 14+ años | 0 → 0 · 1 → 15 · 2 → 31 · 3 → 46 · 4+ → 61 |
| Cuartos para dormir | 0 → 0 · 1 → 8 · 2 → 16 · 3 → 24 · 4+ → 32 |

Cortes por puntaje: A/B ≥202 · C+ 168–201 · C 141–167 · C- 116–140 · D+ 95–115 · D 48–94 · E 0–47.
La regla 2018 tiene **otros** puntos y cortes; no la mezcles con la 2022.
Distribución nacional AMAI 2022 (ENIGH 2022): A/B 7.3 · C+ 12.0 · C 15.3 · C- 16.4 · D+ 14.9 · D 25.4 · E 8.7.

## Códigos de la muestra censal 2020 (verificados en los datos)
Cada variable tiene sus propios códigos de sí/no:
- REFRIGERADOR 1/2 · LAVADORA 3/4 · HORNO 5/6 · AUTOPROP 7/8 · COMPUTADORA 1/2 · TELEFONO 3/4 · INTERNET 7/8
- SERV_TV_PAGA 1/2 · SERV_PEL_PAGA 3/4 · REGADERA 7/8 · AIRE_ACON 5/6
- En todas, 9 significa "no especificado".
- SERSAN: 1 taza de baño · 2 letrina · 3 ninguno. JEFE_SEXO: 1 hombre · 3 mujer.
- CUADORM y TOTCUART: conteos, con 99 como "no especificado". JEFE_EDAD: 999 es "no especificado".
- **AUTOPROP y REGADERA son solo sí/no**: el Censo no da el número de autos ni de baños, por eso se imputan con ENIGH.
- PARENTESCO viene en **3 dígitos**: el jefe es `101` (empieza con "1"). La documentación dice "01"; no la sigas.
- NIVACAD: 00 ninguno · 01 preescolar · 02 primaria · 03 secundaria · 04 prepa · 05 bachillerato tecnológico ·
  06 y 07 técnica con primaria o secundaria · 08 técnica con prepa · 09 normal básica · 10 normal licenciatura ·
  11 licenciatura · 12 especialidad · 13 maestría · 14 doctorado · 99 no especificado. ESCOLARI es el grado dentro del nivel.
- CONACT (ocupado): 10, 13–19 (rescatados como ocupados) y 20 (tenía trabajo pero no trabajó).
  El universo son personas de 12+ años; para la regla AMAI se filtra EDAD ≥ 14.
- Se descartan las viviendas con `REFRIGERADOR` NaN, que son viviendas sin información de características.
- La variable `LOC50K` identifica localidades de 50k+ habitantes. Los donantes del IPU se toman de todos los municipios de la ZM.

ENIGH 2024 (ns): `viviendas.bano_comp`, `cuart_dorm` y `num_cuarto`; `hogares.num_auto + num_van + num_pick`,
`conex_inte` (1 = sí), `num_compu`, `num_lap`, `num_lavad` y `num_micro`; `concentradohogar.educa_jefe` (01–11), `ocupados`,
`tot_integ`, `tam_loc` (1–3 = 2,500+ habitantes), `factor` y `ubica_geo` (los primeros 2 dígitos son el estado).

## Método (resumen)
1. **Imputación ENIGH.** Un logit ponderado estima P(2+ baños | ≥1) y P(2+ autos | ≥1) con las mismas features en ENIGH y en el Censo.
   Cada hogar censal se reparte entre 4 escenarios (1 o 2+ baños × 1 o 2+ autos), lo que da una probabilidad por nivel de NSE.
2. **Microsimulación IPU por AGEB** (`src/microsim.py`). Calibra a 24 restricciones:
   - A nivel hogar: hogares, autos, internet, PC, lavadora, microondas, TV de paga, streaming, teléfono fijo, refrigerador, 1 dormitorio, 1 y 2 cuartos, jefa mujer.
   - A nivel persona: población en hogares, 0–5, 6–11, 12–17, 18–24, 60+, 65+, ocupados, 18+ con posbásica y años de escolaridad de 15+ (GRAPROES × P_15YMAS).
   - Los totales `VPH_*` se reescalan por TOTHOG/VIVPARH_CV y los de personas por POBHOG/POBTOT.
   - El peso inicial es el FACTOR de la muestra; los donantes del mismo municipio que la AGEB llevan peso ×2.
   - Al final, cada grupo de categorías se renormaliza para que sume TOTHOG.
3. **Áreas de influencia** (notebook 03).
   - Cada manzana recibe los HHs por categoría de su AGEB, en proporción a su TOTHOG. Las manzanas confidenciales se reparten el remanente.
   - Se suman las manzanas cuyo centroide cae dentro del radio (BallTree haversine).
   - La competencia se cuenta en el mismo radio, excluyendo la propia tienda.
4. **Índice** = % de la unidad / % de la referencia × 100.

## Supuestos a declarar en el entregable
- Los datos de hogares son del Censo 2020 (no están proyectados). El DENUE es la edición vigente.
- Baño completo = regadera y taza de baño. El Censo pregunta por el trabajo de la "semana pasada"; AMAI, por el "último mes".
- "Niño < 6 / 6–11 / 12+" se basa en la edad del **menor** de 18 del hogar ("12+" = 12–17). "Sin niños" = ningún menor de 18.
- La edad es la del jefe de hogar según el Censo.
- Canal Moderno = cadena identificada por regex sobre `nom_estab` y `raz_social`. Tradicional = el resto.

## Trampas encontradas
- En el CSV AGEB, `NOM_LOC` de las filas AGEB dice "Total AGEB urbana" y el de la fila total de localidad dice "Total de la localidad urbana".
  El nombre real se toma de `{ENT}l.shp` (NOMGEO).
- Las filas de total AGEB son las que tienen `AGEB != "0000"` y `MZA == "000"`. Las filas de manzana son `MZA != "000"`.
- El IPU por AGEB en loop tardaba 17 minutos; vectorizado (todas las AGEB a la vez) tarda unos 2 minutos.
- Hay regex de cadenas con falsos positivos: "SUPERCITO" no es Chedraui y "TENDEJON WILLY" no es Willys.
  Los abarrotes "Six" son tienditas afiliadas, no tiendas propias de una cadena.
- `pandas 3`: las columnas de texto son Arrow y no admiten indexación 2D numpy.
