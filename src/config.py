"""Configuracion del pipeline Merida (NSE + tiendas DENUE)."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
OUT = BASE / "outputs"
for _p in (RAW, PROC, OUT):
    _p.mkdir(parents=True, exist_ok=True)

# ---- Estado / ciudad: para replicar en otra ciudad solo se cambia este bloque ----
ENT = "31"                    # clave INEGI de entidad (2 digitos)
NOM_ENT = "Yucatán"
ABREV_MICRO = "yuc"           # abreviatura en Censo2020_CA_<abrev>_csv.zip (ags, bc, ..., yuc, zac)
MG_SLUG = "yucatan"           # nombre en el zip del Marco Geoestadistico: <ENT>_<slug>.zip
REGION_NIELSEN = "Sureste"  # Nielsen Mexico, Area 6 Sureste

# Zona Metropolitana de Merida (SEDATU-CONAPO-INEGI, Metropolis de Mexico 2020)
ZM_NOMBRE = "ZM Mérida"
ZM_MUNICIPIOS = {"013": "Conkal", "041": "Kanasín", "050": "Mérida", "100": "Ucú", "101": "Umán"}

# Referencia del indice: "zm" (total ZM Merida) o "estado" (total Yucatan, desde microdatos)
REFERENCIA_INDICE = "zm"

# Estados usados para entrenar la imputacion ENIGH (peninsula + Tabasco, urbano)
ENIGH_ESTADOS = ["04", "23", "27", "31"]

URLS = {
    # Censo 2020 - resultados por AGEB y manzana urbana (Yucatan)
    "ageb": f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip",
    # Censo 2020 - microdatos del cuestionario ampliado (muestra), Yucatan
    "micro": f"https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_{ABREV_MICRO}_csv.zip",
    # Marco Geoestadistico 2020 - Yucatan (AGEB, manzanas, localidades)
    "mg": f"https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/{ENT}_{MG_SLUG}.zip",
    # ENIGH 2024 (nueva serie) - para imputar # banos completos y # autos
    "enigh": "https://www.inegi.org.mx/contenidos/programas/enigh/nc/2024/datosabiertos/conjunto_de_datos_enigh2024_ns_csv.zip",
    # DENUE - descarga masiva Yucatan (edicion vigente)
    "denue": f"https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip",
}

ARCHIVOS = {
    "ageb": RAW / f"ageb_mza_urbana_{ENT}_cpv2020_csv.zip",
    "micro": RAW / f"Censo2020_CA_{ABREV_MICRO}_csv.zip",
    "mg": RAW / f"mg2020_{ENT}_{MG_SLUG}.zip",
    "enigh": RAW / "enigh2024_ns_csv.zip",
    "denue": RAW / f"denue_{ENT}_csv.zip",
}

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
    "NSE AMAI 2022": ["A/B", "C+", "C", "C-", "D+", "D/E"],
}
CATEGORIAS = [c for g in GRUPOS.values() for c in g]
ID_COLS = ["Latitud", "Longitud", "Región Nielsen", "Estado", "Municipio", "Localidad", "Zonas Metropolitanas"]
