"""Rappi (panel nacional de venta en línea): lectura, etiquetas de ciudad, clasificación de sueros e hidratación y tiendas físicas.

Lo usan el notebook 00c (EDA y selección) y el 06 (Rappi mueve su venta a los PDV de la Letra 2). Reglas (decisión del usuario): el
proyecto es **sueros e hidratación** de la ZM activa; si una línea viene con otros productos, lo que importa es que tenga
**sueros o sus derivados**. La ZM se define por polígono municipal del Marco Geoestadístico; la etiqueta `city` solo se verifica.

Hallazgos del archivo que explican el código (notebook 00c, secciones 1-2):
- `datetime` trae sufijo "Z" pero el perfil por hora es de hora local (pico 19-21 h, casi nada de 1-6 h): no se convierte.
- Los competidores de Coca-Cola vienen anonimizados a nivel marca (sin SKU, nombre ni usuario): dos sabores de la misma
  marca al mismo precio en un pedido quedan como filas idénticas. Por eso las filas duplicadas no se borran.
- `Product_Category_3` = "Bebidas Hidratantes" es un nodo genérico y "No disponible" no dice nada; además hay sueros
  (p. ej. "Electrolit Suero Oral") y combos con Powerade fuera de la categoría. Ver `clasificar`.
- Una tienda física tiene varios `store_id` (…_Express, …_Super, …_Pharma): se agrupan por cercanía de coordenadas.
"""
import unicodedata

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.neighbors import BallTree

GENERICA = "Bebidas Hidratantes"                 # Product_Category_3 sin detalle (mismo nombre que la categoría)
SIN_SUB = "Hidratación sin subcategoría"
RADIO_TIERRA_M = 6_371_000
# nombre del producto (solo lo traen Coca-Cola y algunas filas sin marca): primero isotónico (Powerade también se llama
# "bebida hidratante"), luego suero. Vitamin Water es agua funcional (así la clasifica Rappi): no es suero ni derivado.
NOMBRE_ISOTONICO = r"POWERADE|GATORADE|ISOT[OÓ]NIC|DEPORTIV|PARA DEPORTISTAS"
NOMBRE_SUERO = r"SUERO|ELECTROL|REHIDRAT|HIDRATANTE|FLASHLYTE|PEDIALYTE|\bLYTE\b"
NO_ES_SUERO = r"VITAMIN\s*WATER"
COLUMNAS = ["datetime", "Source_Platform_Type", "Source_Ship_From_Code", "State", "city", "store_id", "store_name",
            "store_lat", "store_lng", "store_group_name", "vertical", "Source_Product_Code", "Product_Code", "Product_name",
            "Product_Brand", "Product_Category_2", "Product_Category_3", "Product_Maker_Standard", "beverage_sales",
            "beverage_units", "order_code", "user_code", "age", "gender", "User_Attribute_1"]


def normalizar(s: pd.Series) -> pd.Series:
    """Mayúsculas, sin acentos ni espacios repetidos: 'Mérida' y 'Merida' → 'MERIDA'."""
    return s.fillna("").map(lambda t: " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper().split()))


def subcategoria_por_marca(df: pd.DataFrame, categoria: str, subcategorias) -> pd.DataFrame:
    """Subcategoría específica de cada marca en todo el archivo: la moda, su pureza (% de filas específicas de la marca
    que caen en la moda) y el número de filas específicas en que se basa. "No disponible" no es una marca."""
    esp = df[df.Product_Category_2.eq(categoria) & df.Product_Category_3.isin(subcategorias) & ~df.Product_Brand.eq("No disponible")]
    g = esp.groupby("Product_Brand").Product_Category_3
    return pd.DataFrame({"subcategoria": g.agg(lambda s: s.value_counts().index[0]),
                         "pureza": g.agg(lambda s: s.value_counts(normalize=True).iloc[0]), "filas_especificas": g.size()})


def clasificar(df: pd.DataFrame, marcas: pd.DataFrame, categoria: str, subcategorias: dict, pureza_min=0.95):
    """Subcategoría del proyecto y regla que la decide, por línea. La primera regla que aplica gana:

    1. subcategoría específica de Rappi (`subcategorias`: Hidratantes → sueros, Isotónicos → derivados);
    2. la subcategoría de su marca en todo el país, si la marca es pura (≥ pureza_min de sus filas específicas);
    3. el nombre del producto (suero / electrolito / rehidratante, o Powerade / Gatorade / isotónico), en cualquier categoría:
       así entran los sueros mal clasificados y los combos que traen un suero o un isotónico;
    4. si sigue en la categoría de hidratación: "Hidratación sin subcategoría" (entra: puede ser suero).
    Sale solo lo que tiene evidencia de no ser suero ni derivado (Vitamin Water, agua funcional) y lo que no es hidratación.
    Devuelve (subcategoria, regla) como Series (subcategoria NaN = no entra)."""
    en_cat = df.Product_Category_2.eq(categoria)
    nombre = normalizar(df.Product_name)
    marca = df.Product_Brand.fillna("")
    de_marca = marca.map(marcas.subcategoria.where(marcas.pureza >= pureza_min)).map(subcategorias)
    por_nombre = pd.Series(np.select([nombre.str.contains(NOMBRE_ISOTONICO), nombre.str.contains(NOMBRE_SUERO)],
                                     [subcategorias["Isotónicos Líquidos"], subcategorias["Hidratantes Líquidos"]], ""),
                           index=df.index).replace("", np.nan)
    reglas = [(en_cat & df.Product_Category_3.isin(subcategorias), df.Product_Category_3.map(subcategorias), "1 · subcategoría de Rappi"),
              (de_marca.notna(), de_marca, "2 · subcategoría de su marca en el país"),
              (por_nombre.notna(), por_nombre, "3 · nombre del producto"),
              (en_cat, pd.Series(SIN_SUB, index=df.index), "4 · categoría de hidratación sin subcategoría")]
    sub = pd.Series(np.nan, index=df.index, dtype=object)
    regla = pd.Series("no es hidratación (otra categoría)", index=df.index, dtype=object)
    for cond, valor, nombre_regla in reversed(reglas):             # se aplican al revés: la primera de la lista queda encima
        sub = sub.mask(cond, valor)
        regla = regla.mask(cond, nombre_regla)
    no_suero = normalizar(marca).str.contains(NO_ES_SUERO) | nombre.str.contains(NO_ES_SUERO)
    sub[no_suero] = np.nan
    regla[no_suero] = "no es suero ni derivado (Vitamin Water: agua funcional)"
    return sub, regla


def tiendas_fisicas(lat, lon, radio_m=25) -> np.ndarray:
    """Etiqueta de tienda física para cada coordenada: componentes conexas de puntos a ≤ radio_m (haversine)."""
    X = np.radians(np.column_stack([lat, lon]))
    vec = BallTree(X, metric="haversine").query_radius(X, r=radio_m / RADIO_TIERRA_M)
    filas = np.repeat(np.arange(len(vec)), [len(v) for v in vec])
    G = csr_matrix((np.ones(filas.size), (filas, np.concatenate(vec))), shape=(len(X), len(X)))
    return connected_components(G, directed=False)[1]


def botellas(lineas: pd.DataFrame, precio_max=150) -> pd.Series:
    """Botellas de cada línea: sus unidades; en un empaque múltiple (precio por unidad > `precio_max` MXN; un suero o isotónico
    individual cuesta 20-50), el importe entre el precio mediano de una botella de su subcategoría."""
    multi = lineas.beverage_sales / lineas.beverage_units > precio_max
    precio = (lineas.beverage_sales / lineas.beverage_units)[~multi].groupby(lineas.subcategoria[~multi]).median()
    precio_linea = lineas.subcategoria.map(precio).fillna(precio.median())
    return pd.Series(np.where(multi, lineas.beverage_sales / precio_linea, lineas.beverage_units), index=lineas.index)


def en_radio(lat_a, lon_a, lat_b, lon_b, radio_m) -> list:
    """Para cada punto A, índices de los puntos B a ≤ radio_m (haversine)."""
    arbol = BallTree(np.radians(np.column_stack([lat_b, lon_b])), metric="haversine")
    return arbol.query_radius(np.radians(np.column_stack([lat_a, lon_a])), r=radio_m / RADIO_TIERRA_M)
