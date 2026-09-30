"""Letras de cada punto de venta (notebook 06; canal Tradicional y solo datos del CP): Letra 1 = NSE de su clúster NSE
(hexágono H3 + buffer de 300 m desde su centro, movido por AltScore); Letra 2 = venta + CP + Rappi contra su clúster de venta.

Fórmulas (las mismas de la hoja "Fórmulas" del Excel del 06). i = PDV; s(i) = su subcanal (CP); c(i) = su clúster NSE = la
celda H3 de res 9 que lo contiene (config.NSE_CLUSTER_RES; su centro es el punto NSE); A_c = hexágonos H3 res 10 cuyo centro
está a ≤ 300 m del centro de c; k = nivel NSE AMAI (1 = D/E, 2 = D+, 3 = C−, 4 = C, 5 = C+, 6 = A/B).

  Letra 1 (NSE del clúster: todos los PDV del hexágono comparten su NSE; el PDV no la cambia)
    HH_ck  = Σ_{h ∈ A_c} HH_hk                     hogares del nivel k en el buffer del clúster (manzanas repartidas por área, 2025)
    p_ck   = HH_ck / Σ_k HH_ck                      distribución NSE del clúster
    N_c    = Σ_k k · p_ck                           nivel NSE medio (1 a 6) según INEGI
    a_c    = media del índice NSE AltScore de sus puntos a ≤ 300 m del centro (percentil 0-100, notebook 00b)
    Ñ_c    = Q_N(F_a(a_c))                          AltScore en la escala de N por cuantiles (misma distribución que N)
    N*_c   = (1 − λ) · N_c + λ · Ñ_c                AltScore mueve el NSE (λ = config.ALTSCORE_PESO_NSE); N*_c = N_c si el
                                                    buffer tiene < config.ALTSCORE_MIN_PUNTOS puntos AltScore con índice
    I^N_i  = 100 · N*_c(i) / media_{j ∈ s(i)} N*_c(j)   índice NSE (100 = media del subcanal)
    L1_i   = H si I^N_i ≥ 100, si no L

  Letra 2 (Ventas) — reglas del usuario (2026-09-30): venta media + CP contra la media de su clúster de venta; Rappi premia
  a la locación moviendo su venta
    V_i    = PotentialQuantitative_TotalPortafolio_i   venta media del PDV según el CP (cajas/mes; ya no el archivo de ventas)
    CP_i   = ⌊PQF_i⌋ + 1[PQF_i − ⌊PQF_i⌋ ≥ 0.6]      potencial del CP (PotentialQuantitativeFinal_TotalPortafolio) en cajas
                                                    enteras: hacia abajo si el decimal < 0.6 (config.CP_UMBRAL_REDONDEO)
    W_i    = V_i + CP_i
    C_i    = {j con venta : d(i, j) ≤ 300 m}        clúster de venta: PDV con venta en el buffer del PDV (incluye a i)
    I^V_i  = 100 · W_i / media_{j ∈ C_i} W_j        índice de venta contra su clúster de venta (sin Rappi)
    S_r    = botellas_r / meses de vida_r / b       venta de sueros e hidratación de la tienda Rappi activa r, en cajas/mes
                                                    (b = config.RAPPI_BOTELLAS_CAJA)
    D_r    = {j con venta : d(j, r) ≤ 300 m}        PDV que reciben la venta de r
    R_i    = Σ_{r : i ∈ D_r} S_r / |D_r|            venta Rappi movida al PDV (partes iguales: la misma venta no se cuenta dos veces)
    I^V*_i = 100 · (W_i + R_i) / media_{j ∈ C_i} (W_j + R_j)   índice con la venta Rappi movida (la media también lleva Rappi)
    L2_i   = H si |C_i| ≥ 2 y I^V*_i > 100; si no L   (el PDV que es el único con venta en su buffer queda L)

  La media del clúster de venta también se mueve con Rappi (usuario, 2026-09-30): cada PDV se compara con sus vecinos con la
  misma vara (venta media + CP + Rappi), así que Rappi puede subir o bajar una letra.

La media de la Letra 1 se toma sobre los PDV objetivo del subcanal (con venta y con hogares en su clúster NSE); un PDV sin venta
recibe su Letra 1 contra esa misma media y no tiene Letra 2.
"""
import h3
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

NIVELES = {"D/E": 1, "D+": 2, "C-": 3, "C": 4, "C+": 5, "A/B": 6}
NOMBRE_NIVEL = {v: k for k, v in NIVELES.items()}
ACCION = {"HH": "Atacar", "HL": "Bloquear", "LH": "Fortalecer", "LL": "Mantener"}


def nivel_medio(hh: pd.DataFrame) -> pd.Series:
    """N = Σ_k k · p_k con los hogares por nivel (columnas = NIVELES). NaN si no hay hogares."""
    x = hh[list(NIVELES)].astype(float)
    tot = x.sum(axis=1)
    return (x * pd.Series(NIVELES)).sum(axis=1) / tot.where(tot > 0)


def indice(x: pd.Series, grupo: pd.Series, referencia: pd.Series | None = None) -> pd.Series:
    """100 · x / media del grupo. `referencia` (booleana) = filas con las que se calcula la media (por defecto todas)."""
    ref = x if referencia is None else x.where(referencia)
    return 100 * x / ref.groupby(grupo).transform("mean")


def letra(i: pd.Series, corte: float = 100) -> pd.Series:
    """H si el índice ≥ corte, L si es menor, NaN si no hay índice."""
    return pd.Series(np.where(i.isna(), None, np.where(i >= corte, "H", "L")), index=i.index, dtype=object)


def letra_media(x: pd.Series, grupo: pd.Series, referencia: pd.Series | None = None) -> pd.Series:
    """Misma regla para variables sin cero natural (índices en z o percentil): H si x ≥ media del grupo. Para variables
    positivas es idéntica a índice ≥ 100."""
    ref = x if referencia is None else x.where(referencia)
    return letra(x - ref.groupby(grupo).transform("mean"), corte=0)


def hexagonos_en_radio(lat, lon, radio_m: float, res: int) -> list:
    """Para cada punto, los hexágonos H3 de resolución `res` cuyo centro está a ≤ radio_m (misma regla que el notebook 04)."""
    arista = h3.average_hexagon_edge_length(res, "m")
    k = int(np.ceil((radio_m + arista) / (np.sqrt(3) * arista))) + 1
    areas = []
    for la, lo in zip(np.asarray(lat, float), np.asarray(lon, float)):
        cand = list(h3.grid_disk(h3.latlng_to_cell(la, lo, res), k))
        c = np.radians([h3.cell_to_latlng(x) for x in cand])
        a, b = np.radians(la), np.radians(lo)
        d = 2 * 6_371_000 * np.arcsin(np.sqrt(np.sin((c[:, 0] - a) / 2) ** 2 + np.cos(a) * np.cos(c[:, 0]) * np.sin((c[:, 1] - b) / 2) ** 2))
        areas.append([x for x, di in zip(cand, d) if di <= radio_m])
    return areas


def suma_area(tabla: pd.DataFrame, areas: list) -> pd.DataFrame:
    """Suma, para cada área (lista de hexágonos), las filas de `tabla` (indexada por hexágono) que caen en ella."""
    M = tabla.to_numpy(float)
    pos = pd.Series(np.arange(len(tabla)), index=tabla.index)
    out = np.zeros((len(areas), M.shape[1]))
    for i, v in enumerate(areas):
        idx = pos.reindex(v).dropna().to_numpy(int)
        if idx.size:
            out[i] = np.nansum(M[idx], axis=0)
    return pd.DataFrame(out, columns=tabla.columns)


def redondeo_cp(x, umbral: float = 0.6):
    """Cajas enteras con umbral: hacia abajo si el decimal es menor a `umbral`, hacia arriba si no (0.59 → 0, 0.6 → 1,
    1.55 → 1, 1.6 → 2). NaN se queda NaN."""
    x = pd.Series(x, dtype=float)
    piso = np.floor(x)
    return piso + ((x - piso).round(9) >= umbral).astype(float).where(x.notna())    # round(9): 4.6 − 4 = 0.5999999999999996


def mover_venta(venta, lat_o, lon_o, lat_d, lon_d, radio_m: float, destino):
    """Mueve la venta de cada origen (p. ej. una tienda Rappi) a los destinos con `destino` = True a ≤ radio_m, en partes
    iguales. Devuelve (venta recibida por cada destino, número de destinos de cada origen) como arreglos; la suma recibida es la
    venta de los orígenes con al menos un destino (lo que no tiene destino no se mueve)."""
    destino = np.asarray(destino, bool)
    idx = np.flatnonzero(destino)
    recibida = np.zeros(destino.size)
    n = np.zeros(len(np.asarray(venta)), int)
    if idx.size:
        arbol = BallTree(np.radians(np.column_stack([np.asarray(lat_d, float)[idx], np.asarray(lon_d, float)[idx]])), metric="haversine")
        vec = arbol.query_radius(np.radians(np.column_stack([np.asarray(lat_o, float), np.asarray(lon_o, float)])), r=radio_m / 6_371_000)
        for k, (v, x) in enumerate(zip(np.asarray(venta, float), vec)):
            n[k] = x.size
            if x.size:
                np.add.at(recibida, idx[x], v / x.size)
    return recibida, n


def centros(celdas):
    """Latitud y longitud del centro de cada celda H3 (el punto NSE de cada clúster)."""
    c = np.array([h3.cell_to_latlng(h) for h in celdas], float).reshape(-1, 2)
    return c[:, 0], c[:, 1]


def a_escala(x, referencia, x_base=None) -> pd.Series:
    """Lleva `x` a la escala de `referencia` por cuantiles: cada valor toma el de su mismo percentil (rango medio dentro de
    `x_base`, por defecto `x`) en la distribución de `referencia`; en la base el resultado tiene la distribución de
    `referencia` y el orden de `x` (AltScore 0-100 → N de 1 a 6). NaN se queda NaN."""
    x = pd.Series(x, dtype=float)
    xs = np.sort(pd.Series(x if x_base is None else x_base, dtype=float).dropna().to_numpy())
    ref = pd.Series(referencia, dtype=float).dropna().to_numpy()
    v = x.to_numpy()
    p = (np.searchsorted(xs, v, side="left") + np.searchsorted(xs, v, side="right")) / 2 / max(len(xs), 1)
    return pd.Series(np.where(np.isnan(v), np.nan, np.quantile(ref, np.clip(np.nan_to_num(p, nan=0.5), 0, 1))), index=x.index)


def mover_nse(N, N_alt, peso: float) -> pd.Series:
    """N* = (1 − peso) · N + peso · N_alt donde hay N_alt; N donde no (AltScore mueve el NSE, config.ALTSCORE_PESO_NSE)."""
    N = pd.Series(N, dtype=float)
    a = np.asarray(N_alt, float)
    return pd.Series(np.where(np.isnan(a), N.to_numpy(), (1 - peso) * N.to_numpy() + peso * a), index=N.index)


def cluster_local(valor, grupo, lat, lon, radio_m: float, miembro):
    """Clúster de cada punto: los puntos del mismo `grupo` (p. ej. canal) con `miembro` = True a ≤ radio_m, incluido él si es
    miembro. Devuelve (tamaño del clúster, media de `valor` en el clúster) como arreglos."""
    valor, grupo, miembro = np.asarray(valor, float), np.asarray(grupo, object), np.asarray(miembro, bool)
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    n, media = np.zeros(valor.size, int), np.full(valor.size, np.nan)
    for g in pd.unique(grupo):
        m = (grupo == g) & miembro
        if not m.any():
            continue
        arbol = BallTree(np.radians(np.column_stack([lat[m], lon[m]])), metric="haversine")
        q = np.flatnonzero(grupo == g)
        vec = arbol.query_radius(np.radians(np.column_stack([lat[q], lon[q]])), r=radio_m / 6_371_000)
        v = valor[m]
        for k, idx in zip(q, vec):
            n[k] = idx.size
            media[k] = v[idx].mean() if idx.size else np.nan
    return n, media
