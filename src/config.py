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
    ),
    "guadalajara": dict(
        ENT="14", NOM_ENT="Jalisco", ABREV_MICRO="jal", MG_SLUG="jalisco",
        REGION_NIELSEN="Pacífico",
        ZM_NOMBRE="ZM Guadalajara",
        ZM_MUNICIPIOS={"002": "Acatlán de Juárez", "039": "Guadalajara", "044": "Ixtlahuacán de los Membrillos",
                       "051": "Juanacatlán", "070": "El Salto", "097": "Tlajomulco de Zúñiga",
                       "098": "San Pedro Tlaquepaque", "101": "Tonalá", "120": "Zapopan", "124": "Zapotlanejo"},
        ENIGH_ESTADOS=["01", "06", "14", "16", "18"],   # Jalisco + Ags, Colima, Michoacan, Nayarit
    ),
}
_c = CIUDADES[CIUDAD]
ENT, NOM_ENT, ABREV_MICRO, MG_SLUG = _c["ENT"], _c["NOM_ENT"], _c["ABREV_MICRO"], _c["MG_SLUG"]
REGION_NIELSEN, ZM_NOMBRE, ZM_MUNICIPIOS = _c["REGION_NIELSEN"], _c["ZM_NOMBRE"], _c["ZM_MUNICIPIOS"]
ENIGH_ESTADOS = _c["ENIGH_ESTADOS"]
SLUG = f"zm_{CIUDAD}"          # sufijo de archivos intermedios y entregables

RAW = BASE / "data" / "raw"                       # compartido: los nombres ya llevan la clave de estado
PROC = BASE / "data" / "processed" / CIUDAD
OUT = BASE / "outputs" / CIUDAD
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
MG_VERSION = "2025"                 # Marco Geoestadistico: "2025" (vigente) o "2020" (el ligado al Censo 2020)
_MG_UPC = {"2020": "889463807469", "2025": "794551163061"}   # carpeta / UPC del producto en INEGI

FUENTES = {
    "ageb": dict(
        cobertura=_COB_ESTADO,
        nombre="Censo de Población y Vivienda 2020 · Principales resultados por AGEB y manzana urbana",
        edicion="2020 (datos abiertos, CSV)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/ccpv/2020/#datos_abiertos",
        url=f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip",
        archivo=RAW / f"ageb_mza_urbana_{ENT}_cpv2020_csv.zip"),
    "micro": dict(
        cobertura=_COB_ESTADO,
        nombre="Censo de Población y Vivienda 2020 · Microdatos del cuestionario ampliado (muestra)",
        edicion="2020 (CSV por entidad)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/ccpv/2020/#microdatos",
        url=f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_{ABREV_MICRO}_csv.zip",
        archivo=RAW / f"Censo2020_CA_{ABREV_MICRO}_csv.zip"),
    "mg": dict(
        cobertura=_COB_ESTADO,
        nombre=f"Marco Geoestadístico {MG_VERSION} · AGEB, manzanas y localidades del estado",
        edicion=f"{MG_VERSION} (UPC {_MG_UPC[MG_VERSION]}, shapefile)", institucion="INEGI",
        pagina=f"https://www.inegi.org.mx/app/biblioteca/ficha.html?upc={_MG_UPC[MG_VERSION]}",
        url=("https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/"
             f"geografia/marcogeo/{_MG_UPC[MG_VERSION]}/{ENT}_{MG_SLUG}.zip"),
        archivo=RAW / f"mg{MG_VERSION}_{ENT}_{MG_SLUG}.zip"),
    "enigh": dict(
        cobertura="Nacional → se usan hogares urbanos de " + ", ".join(f"{ESTADOS[e]} ({e})" for e in ENIGH_ESTADOS),
        nombre="Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH) 2024 · nueva serie",
        edicion="2024 (publicada 2025-07-30; la más reciente)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/programas/enigh/nc/2024/#datos_abiertos",
        url="https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/datosabiertos/conjunto_de_datos_enigh2024_ns_csv.zip",
        archivo=RAW / "enigh2024_ns_csv.zip"),
    "denue": dict(
        cobertura=_COB_ESTADO,
        nombre="Directorio Estadístico Nacional de Unidades Económicas (DENUE) · descarga masiva por entidad",
        edicion="vigente (la edición exacta se lee de metadatos_denue.txt)", institucion="INEGI",
        pagina="https://www.inegi.org.mx/app/descarga/?ti=6",
        url=f"https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip",
        archivo=RAW / f"denue_{ENT}_csv.zip"),
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

URLS = {k: v["url"] for k, v in FUENTES.items()}
ARCHIVOS = {k: v["archivo"] for k, v in FUENTES.items()}

# ---- Datos del cliente (Bepensa): ventas y customer potential por punto de venta (no se suben a git) ----
CLIENTE = "bepensa"
CLIENTE_CIUDAD = "merida"          # los datos de Bepensa se analizan para la ZM Mérida (notebooks 00 y 04)
CLIENTE_RAW = RAW / CLIENTE
# el CP cubre toda la peninsula: los notebooks 00 y 04 filtran a la ZM activa y escriben en PROC / OUT de la ciudad
CLIENTE_VENTAS = sorted((CLIENTE_RAW / "ventas").glob("part-*.csv"))
CLIENTE_CP = CLIENTE_RAW / "cp" / "conservative_scenario.csv"
# Area de influencia de cada punto de venta: hexagonos H3 cuyo centro esta a <= RADIO_PDV_M del punto.
# res 10: arista ~76 m, area ~0.015 km2 (del tamano de una manzana) -> 300 m ~ 19 hexagonos (~0.28 km2).
H3_RES = 10
RADIO_PDV_M = 300          # definido con el usuario: el area llega hasta 300 m (500 m es demasiado lejos)

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
