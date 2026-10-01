"""Configuracion del pipeline NSE + tiendas DENUE (una entrada por ciudad en CIUDADES)."""
from pathlib import Path

import os

BASE = Path(__file__).resolve().parents[1]

# ---- Ciudad a correr: cambia esta linea (o define la variable de entorno CIUDAD) ----
CIUDAD = os.environ.get("CIUDAD", "merida")

# ---- Estado / ciudad: para agregar otra ciudad solo se agrega un bloque aqui ----
# ZM = delimitacion SEDATU-CONAPO-INEGI, Metropolis de Mexico 2020.
# ENIGH_ESTADOS = estado + vecinos (la ENIGH es chica por estado; conviene 5k+ hogares urbanos).
CIUDADES = {
    "merida": dict(
        ENT="31", NOM_ENT="Yucatán", ABREV_MICRO="yuc", MG_SLUG="yucatan",
        REGION_NIELSEN="Sureste",                       # Nielsen Mexico, Area 6 Sureste
        ZM_NOMBRE="ZM Mérida",
        ZM_MUNICIPIOS={"013": "Conkal", "041": "Kanasín", "050": "Mérida", "100": "Ucú", "101": "Umán"},
        ENIGH_ESTADOS=["04", "23", "27", "31"],         # peninsula + Tabasco
        RAPPI_CIUDAD=["MERIDA"],                         # etiqueta `city` de Rappi (normalizada: "Mérida" y "Merida")
    ),
    "guadalajara": dict(
        ENT="14", NOM_ENT="Jalisco", ABREV_MICRO="jal", MG_SLUG="jalisco",
        REGION_NIELSEN="Pacífico",
        ZM_NOMBRE="ZM Guadalajara",
        ZM_MUNICIPIOS={"002": "Acatlán de Juárez", "039": "Guadalajara", "044": "Ixtlahuacán de los Membrillos",
                       "051": "Juanacatlán", "070": "El Salto", "097": "Tlajomulco de Zúñiga",
                       "098": "San Pedro Tlaquepaque", "101": "Tonalá", "120": "Zapopan", "124": "Zapotlanejo"},
        ENIGH_ESTADOS=["01", "06", "14", "16", "18"],   # Jalisco + Ags, Colima, Michoacan, Nayarit
        RAPPI_CIUDAD=["GUADALAJARA"],
    ),
}
_c = CIUDADES[CIUDAD]
ENT, NOM_ENT, ABREV_MICRO, MG_SLUG = _c["ENT"], _c["NOM_ENT"], _c["ABREV_MICRO"], _c["MG_SLUG"]
REGION_NIELSEN, ZM_NOMBRE, ZM_MUNICIPIOS = _c["REGION_NIELSEN"], _c["ZM_NOMBRE"], _c["ZM_MUNICIPIOS"]
ENIGH_ESTADOS, RAPPI_CIUDAD = _c["ENIGH_ESTADOS"], _c["RAPPI_CIUDAD"]
SLUG = f"zm_{CIUDAD}"          # sufijo de archivos intermedios y entregables

RAW = BASE / "data" / "raw"
CLIENTE = "bepensa"
CLIENTE_CIUDAD = "merida"          # los datos de Bepensa se analizan para la ZM Mérida (notebooks 00 y 04)
# todo lo de la ciudad va en data/raw/<ciudad>/<cliente>/ (ciudad sin cliente: data/raw/<ciudad>/)
RAW_CIUDAD = RAW / CIUDAD / (CLIENTE if CIUDAD == CLIENTE_CIUDAD else "")
# descargas de organismos oficiales: <institucion>/<fuente>/ con el zip, lo extraido y descarga.json
# (url, pagina, edicion, fecha de descarga, sha256); fuentes.csv en la raiz es el indice de todas
RAW_OFICIAL = RAW_CIUDAD / "fuentes_oficiales"
# intermedios y entregables con la misma estructura ciudad -> bottler que data/raw (ciudad sin cliente: sin subcarpeta)
PROC = BASE / "data" / "processed" / CIUDAD / (CLIENTE if CIUDAD == CLIENTE_CIUDAD else "")
OUT = BASE / "outputs" / CIUDAD / (CLIENTE if CIUDAD == CLIENTE_CIUDAD else "")     # Excel de analisis y QA (00-04, 06)
OUT_CLIENTE = OUT / "cliente"          # solo lo que se entrega al cliente: presentacion y Excel final (notebook 05)
for _p in (RAW, PROC, OUT):
    _p.mkdir(parents=True, exist_ok=True)

# Referencia del indice: "zm" (total de la ZM) o "estado" (total del estado, desde microdatos)
REFERENCIA_INDICE = "zm"

ESTADOS = {"01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur", "04": "Campeche",
           "05": "Coahuila", "06": "Colima", "07": "Chiapas", "08": "Chihuahua", "09": "Ciudad de México",
           "10": "Durango", "11": "Guanajuato", "12": "Guerrero", "13": "Hidalgo", "14": "Jalisco", "15": "México",
           "16": "Michoacán", "17": "Morelos", "18": "Nayarit", "19": "Nuevo León", "20": "Oaxaca", "21": "Puebla",
           "22": "Querétaro", "23": "Quintana Roo", "24": "San Luis Potosí", "25": "Sinaloa", "26": "Sonora",
           "27": "Tabasco", "28": "Tamaulipas", "29": "Tlaxcala", "30": "Veracruz", "31": "Yucatán", "32": "Zacatecas"}
_COB_ESTADO = f"{NOM_ENT} ({ENT}) → se filtran los {len(ZM_MUNICIPIOS)} municipios de la {ZM_NOMBRE}"

# ---- Fuentes oficiales: UNICO lugar con las URLs (los notebooks las muestran y verifican con HEAD) ----
# Verificadas el 2026-09-24. Cada entrada: nombre, edicion, pagina oficial y URL de descarga del estado.
# Marco Geoestadistico: "2025eic" (el mas reciente: edicion 2026 de la Encuesta Intercensal 2025, datos a nov-2025,
# publicado 2026-08-27), "2025" (UPC 794551163061, datos a jul-2025) o "2020" (el ligado al Censo 2020)
MG_VERSION = "2025eic"
_MG_UPC = {"2020": "889463807469", "2025": "794551163061", "2025eic": "794551196649"}   # carpeta / UPC del producto en INEGI
_MG_NOMBRE = {"2020": "2020", "2025": "2025", "2025eic": "Encuesta Intercensal 2025 (edición 2026)"}

FUENTES = {
    "ageb": dict(
        cobertura=_COB_ESTADO,
        nombre="Censo de Población y Vivienda 2020 · Principales resultados por AGEB y manzana urbana",
        edicion="2020 (datos abiertos, CSV)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos",
        url=f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "censo2020_ageb_manzana" / f"ageb_mza_urbana_{ENT}_cpv2020_csv.zip"),
    "iter": dict(
        cobertura=_COB_ESTADO,
        nombre="Censo de Población y Vivienda 2020 · Principales resultados por localidad (ITER)",
        edicion="2020 (datos abiertos, CSV)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos",
        url=f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_{ENT}_cpv2020_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "censo2020_iter_localidades" / f"iter_{ENT}_cpv2020_csv.zip"),
    "micro": dict(
        cobertura=_COB_ESTADO,
        nombre="Censo de Población y Vivienda 2020 · Microdatos del cuestionario ampliado (muestra)",
        edicion="2020 (CSV por entidad)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/ccpv/2020/#microdatos",
        url=f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_{ABREV_MICRO}_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "censo2020_muestra_microdatos" / f"Censo2020_CA_{ABREV_MICRO}_csv.zip"),
    "mg": dict(
        cobertura=_COB_ESTADO,
        nombre=f"Marco Geoestadístico {_MG_NOMBRE[MG_VERSION]} · AGEB, manzanas y localidades del estado",
        edicion=f"{_MG_NOMBRE[MG_VERSION]} (UPC {_MG_UPC[MG_VERSION]}, shapefile)", institucion="INEGI",
        pagina=f"https://www.inegi.org.mx/app/biblioteca/ficha.html?upc={_MG_UPC[MG_VERSION]}",
        url=("https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/"
             f"geografia/marcogeo/{_MG_UPC[MG_VERSION]}/{ENT}_{MG_SLUG}.zip"),
        archivo=RAW_OFICIAL / "INEGI" / f"marco_geoestadistico_{MG_VERSION}" / f"mg{MG_VERSION}_{ENT}_{MG_SLUG}.zip"),
    "eic": dict(
        cobertura="Nacional → hogares y viviendas por municipio de " + ", ".join(ZM_MUNICIPIOS.values()),
        nombre="Encuesta Intercensal 2025 · Principales resultados por municipio y localidad de 50 000 y más",
        edicion="2025 (publicada 2026-09-22; estimaciones con CV)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/eic/2025/",
        url="https://www.inegi.org.mx/contenidos/programas/eic/2025/datosabiertos/conjunto_de_datos_eic2025_105_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "encuesta_intercensal_2025" / "conjunto_de_datos_eic2025_105_csv.zip"),
    "enigh": dict(
        cobertura="Nacional → se usan hogares urbanos de " + ", ".join(f"{ESTADOS[e]} ({e})" for e in ENIGH_ESTADOS),
        nombre="Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH) 2024 · nueva serie",
        edicion="2024 (publicada 2025-07-30; la más reciente)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/enigh/nc/2024/#datos_abiertos",
        url="https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/datosabiertos/conjunto_de_datos_enigh2024_ns_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "enigh2024" / "enigh2024_ns_csv.zip"),
    "denue": dict(
        cobertura=_COB_ESTADO,
        nombre="Directorio Estadístico Nacional de Unidades Económicas (DENUE) · descarga masiva por entidad",
        edicion="vigente (la edición exacta se lee de metadatos_denue.txt)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/app/descarga/?ti=6",
        url=f"https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip",
        archivo=RAW_OFICIAL / "INEGI" / "denue" / f"denue_{ENT}_csv.zip"),
}
# Referencias sin descarga automatica
REGLA_NSE = dict(
    nombre="Regla NSE AMAI 2024 (vigente desde enero 2024; mismos puntos y cortes que la Regla 2022)",
    institucion="AMAI",
    pagina="https://www.amai.org/NSE/index.php?queVeo=NSE2024",
    documentos=["https://www.amai.org/descargas/NOTA_METODOLOGICA_NSE_AMAI_2024_v6.pdf",
                "https://www.amai.org/descargas/CUESTIONARIO_AMAI_2022.pdf"],
)
OSM = dict(nombre="OpenStreetMap vía Overpass API (opcional, solo alerta de tiendas faltantes)",
           pagina="https://overpass-api.de/", url="https://overpass-api.de/api/interpreter")

for _k, _f in FUENTES.items():
    _f["clave"] = _k
URLS = {k: v["url"] for k, v in FUENTES.items()}
ARCHIVOS = {k: v["archivo"] for k, v in FUENTES.items()}

# ---- Datos del cliente (Bepensa): ventas y customer potential por punto de venta (no se suben a git) ----
CLIENTE_RAW = RAW / CLIENTE_CIUDAD / CLIENTE      # data/raw/merida/bepensa/{ventas,cp}
# el CP cubre toda la peninsula: los notebooks 00 y 04 filtran a la ZM activa y escriben en PROC / OUT de la ciudad
CLIENTE_VENTAS = sorted((CLIENTE_RAW / "ventas").glob("part-*.csv"))
CLIENTE_CP = CLIENTE_RAW / "cp" / "conservative_scenario.csv"
# señales AltScore (geohex_geodig.parquet, con location.lat/lng): variable socioeconómica adicional (notebook 00b; se une en el 04 y el 06 por ubicación)
CLIENTE_ALTSCORE = CLIENTE_RAW / "enrichedgeodata"
ALTSCORE_RES = 8           # celda H3 a la que se proyecta AltScore (res 8 = escala de sus señales OSM; lo digital es de ~1 km)
# Area de influencia de cada punto de venta: hexagonos H3 cuyo centro esta a <= RADIO_PDV_M del punto.
# res 10: arista ~76 m, area ~0.015 km2 (del tamano de una manzana) -> 300 m ~ 19 hexagonos (~0.28 km2).
AJUSTE_HOGARES = "eic2025"      # 04: hogares 2020 × crecimiento de población 2020→2025 por municipio (EIC 2025); None = Censo 2020
H3_RES = 10
RADIO_PDV_M = 300          # definido con el usuario: el area llega hasta 300 m (500 m es demasiado lejos)

# ---- Rappi: panel nacional de venta en linea (data/raw/rappi/, no se sube a git; notebook 00c) ----
# Decision del usuario: el proyecto es SUEROS E HIDRATACION de la ciudad activa; si una linea viene con otros productos, lo que
# importa es que tenga sueros o sus derivados (regla "sueros primero" en src/rappi.py: subcategoria de Rappi, marca, nombre del
# producto; solo sale lo que tiene evidencia de NO ser suero, p. ej. Vitamin Water = agua funcional). La ZM se toma por poligono
# municipal (la etiqueta `city` solo se verifica). Ventana: termina con las ventas del cliente (ago-2026) y empieza en ene-2025
# porque en oct-dic 2024 el archivo no trae cadena, vertical ni la 2a marca competidora en todo el pais (notebook 00c, 1.3).
RAPPI_CSV = RAW / "rappi" / "rappi.csv"
RAPPI_CATEGORIA = "Bebidas Hidratantes"                               # Product_Category_2 de Rappi
RAPPI_SUBCATEGORIAS = {"Hidratantes Líquidos": "Sueros (hidratantes)",  # Product_Category_3 de Rappi -> subcategoria del proyecto
                       "Isotónicos Líquidos": "Isotónicos (derivados)"}
RAPPI_VENTANA = ("2025-01-01", "2026-09-01")                          # [inicio, fin): 20 meses con cobertura completa
RAPPI_MIN_PEDIDOS = 12     # tienda Rappi "activa" en hidratacion: >= 12 pedidos en la ventana (uno cada ~2 meses)

# ---- Letras por PDV (notebook 06, solo canal Tradicional y solo datos del CP; usuario, 2026-09-30) ----
# Letra 1 = NSE de su CLUSTER NSE: el hexagono H3 de res NSE_CLUSTER_RES que contiene al PDV; su centro es el punto NSE y el
# buffer de RADIO_PDV_M alrededor del centro da el NSE (res 9: arista ~174 m, todo PDV queda a <= ~210 m del centro, dentro del
# buffer). Todos los PDV del hexagono comparten su NSE. Letra 2 = score de rangos de venta, CP y Rappi (abajo).
NSE_CLUSTER_RES = 9
# AltScore MUEVE EL NSE del cluster (usuario, 2026-09-30): su indice alrededor del centro se lleva a la escala de N (1-6) por
# cuantiles y N* = (1 - peso) * N_INEGI + peso * N_AltScore, solo donde el buffer tiene >= ALTSCORE_MIN_PUNTOS puntos con indice.
ALTSCORE_PESO_NSE = 0.25   # INEGI pesa 3 veces lo que AltScore (el Censo por manzana confirma a INEGI; a validar con el usuario)
ALTSCORE_MIN_PUNTOS = 5
# Letra 2 (usuario, 2026-09-30): vector del PDV = venta media, CP y Rappi (venta media de las tiendas Rappi de su buffer de
# RADIO_PDV_M); cada variable pasa a su pct_rank descendente entre los PDV con venta (0 = el que mas vende) y el score es su
# media ponderada; H si score < LETRA2_CORTE. Los rangos evitan convertir Rappi (pesos) a cajas. El PDV sin venta es L.
LETRA2_PESOS = {"venta": 2, "cp": 2, "rappi": 1}   # Rappi pesa la mitad: no castigar tanto al PDV sin Rappi cerca
LETRA2_CORTE = 0.4
FRONTERA = 10              # |indice - 100| <= FRONTERA: la letra cambia con poco ruido (se marca, igual que en el 05)
# Letra 2: venta (PotentialQuantitative_TotalPortafolio) y potencial (PotentialQuantitativeFinal_TotalPortafolio) salen del CP;
# el potencial va con decimales (usuario, 2026-09-30). El redondeo anterior queda solo como comparacion en el QA:
CP_UMBRAL_REDONDEO = 0.6   # decimal < 0.6 -> hacia abajo (0.59 -> 0, 1.55 -> 1); >= 0.6 -> hacia arriba (0.6 -> 1, 1.6 -> 2)

SCIAN_TIENDAS = {
    "462111": "Supermercado",
    "462112": "Minisuper",
    "461110": "Abarrotes",   # tiendas de abarrotes, ultramarinos y miscelaneas (canal tradicional)
}
# Canal: "Moderno" = tienda de cadena identificada; "Tradicional" = independientes (incluye abarrotes)
CANALES = ["Moderno", "Tradicional"]

# Categorias de salida (orden = orden de columnas del entregable)
GRUPOS = {
    "Tamaño hogar": ["2 o Menos Personas", "3 personas", "4 personas", "5 personas", "6+ personas"],
    "Niños": ["Niño < 6", "Niño 6 - 11", "Niño 12+", "Sin Niños"],
    "Edad jefe": ["Edad menos de 35", "Edad 35 - 44", "Edad 45 - 54", "Edad 55 - 64", "Edad 65+"],
    "NSE AMAI 2024": ["A/B", "C+", "C", "C-", "D+", "D/E"],
}
CATEGORIAS = [c for g in GRUPOS.values() for c in g]
ID_COLS = ["Latitud", "Longitud", "Región Nielsen", "Estado", "Municipio", "Localidad", "Zonas Metropolitanas"]
