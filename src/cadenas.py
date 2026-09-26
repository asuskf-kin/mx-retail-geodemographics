"""Cadenas comerciales y canal (Moderno / Tradicional): UNICA fuente, la usan el notebook 02 (tiendas DENUE)
y los notebooks 00 y 04 (puntos de venta de Bepensa).

Regla: Moderno = cadena identificada por nombre o razon social; Tradicional = independientes y las cadenas de
CADENAS_TRADICIONALES (Six: abarrotes independientes afiliados a Grupo Modelo). Decisiones del usuario:
Six = Tradicional; Modelorama y cadenas de farmacias = Moderno.
El orden de CADENAS importa: si un texto coincide con varios patrones, gana el primero de la lista.
Para probar un cambio sin correr notebooks: aplicar `clasificar` a tiendas_denue_*.parquet de otra ciudad.
"""
import numpy as np
import pandas as pd

CADENAS = [
    ("Bara", r"^(?!ABARROTES)[^|]*(?:SUPER BARA|TIENDAS? BARA)\b"),  # FEMSA; comparte razon social con OXXO
    ("OXXO", r"\bOXXO\b|CADENA COMERCIAL OXXO"),
    ("7-Eleven", r"7[\s-]?ELEVEN|SEVEN\s?L?ELEVEN|SIETE ONCE"),
    ("Circle K", r"CIRCLE\s*K\b|CIRCULO K\b"),
    ("Kiosko", r"^(?!ABARROTES).*\bKIOSKO\b"),         # "ABARROTES KIOSKO" = tienda independiente
    ("Super Aki", r"^(?!TIENDA DE ABARROTES AKI).*(?:\bAKI\b|SUPER\s*AKI|GRUPO AKI|DAC\b)"),
    ("Six", r"\bSIX\b"),
    ("Bodega Aurrera", r"AURRERA"),
    ("Walmart", r"\bWAL\s*-?\s*MART\b"),              # no "WALMARTHA"
    ("Sam's Club", r"\bSAM'?S CLUB\b"),                 # no "ABARROTES SAMS"
    ("Soriana", r"SORIANA|MEGA SORIANA|CITY CLUB"),
    ("Chedraui", r"CHEDRAUI"),
    ("La Comer / City Market / Fresko", r"LA COMER|CITY MARKET|FRESKO|SUMESA"),
    ("Costco", r"COSTCO"),
    ("Super San Francisco de Asís", r"SAN FRANCISCO DE ASIS"),
    ("Super Willys", r"WILLYS|SUPER\s*WILLY"),
    ("Tiendas 3B", r"\b3\s?B\b|TIENDAS TRES B|BBB"),
    ("Tiendas Neto", r"^(?!.*EL NETO).*\bNETO\b"),
    ("Merza / Dax", r"\bMERZA\b|\bDAX\b"),
    ("Extra", r"\bEXTRA\b"),
    ("Dunosusa", r"DUNOSUSA|DONOSUSA|\bDUNO\b"),
    ("Go Mart", r"GO\s?MART"),
    ("Super Farahon", r"FARAHON"),
    ("Waldo's", r"\bWALDO"),                           # no "OSWALDO"
    ("La Macarena", r"^(?!.*TENDEJON).*MACARENA"),
    ("Delimart (Pemex)", r"DELIMART|PEME\d"),
    ("Toyo Foods", r"TOYO FOODS"),
    # Guadalajara
    ("Su Super", r"^SU SUPER\b"),
    ("Abarrotes y Bebidas MR", r"ABARROTES Y BEBIDAS MR\b"),
    ("Super Kadis", r"SUPER KADIS"),
    ("Area 24.7", r"AREA 24\.?7"),
    # Farmacias de cadena (aparecen en los PDV de Bepensa, subcanal FARMACIAS)
    ("Farmacias Guadalajara", r"FARMACIAS? GUADALAJARA|FARMACIAS? GUADAJARA"),
    ("Farmacias del Ahorro", r"FARMACIAS? DEL AHORRO"),
    ("Farmacias Yza", r"\bYZA\b"),
    ("Farmacias Bazar", r"FARMACIAS? (?:DEL )?BAZAR"),
    ("Farmacias Emérita", r"EM[EÉ]RITA FARMACIA"),
    ("Farmacias Montejo", r"FARMACIAS? MONTEJO"),
    ("Farmacias Similares", r"FARMACIAS? SIMILARES|DR\.? SIMI\b"),
    ("Farmacias San Pablo", r"FARMACIAS? SAN PABLO"),
    ("Farmacias Benavides", r"FARMACIAS? BENAVIDES"),
    # Franquicia cervecera de Grupo Modelo: Moderno (decisión del usuario); Six queda Tradicional
    ("Modelorama", r"MODELORAMA"),
    ("Tiendas IMSS / ISSSTE", r"TIENDA DEL IMSS|SUPERISSSTE"),
]

CADENAS_TRADICIONALES = {"Independiente", "Six"}


def clasificar(texto: pd.Series) -> pd.DataFrame:
    """texto (nombre y/o razon social) -> DataFrame con columnas `cadena` y `canal`, mismo indice."""
    t = texto.fillna("").str.upper()
    cadena = pd.Series("Independiente", index=t.index)
    for nombre, patron in reversed(CADENAS):
        cadena[t.str.contains(patron, regex=True)] = nombre
    return pd.DataFrame({"cadena": cadena,
                         "canal": np.where(cadena.isin(CADENAS_TRADICIONALES), "Tradicional", "Moderno")}, index=t.index)
