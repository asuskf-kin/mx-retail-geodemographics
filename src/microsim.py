"""Microsimulacion espacial por AGEB (Iterative Proportional Updating, Ye et al. 2009).

Cada AGEB recibe pesos sobre los hogares donantes de la muestra censal, de modo que
los totales ponderados reproduzcan lo que el Censo 2020 publica para esa AGEB
(hogares, autos, internet, personas por edad, ocupados, escolaridad, etc.).
Con esos pesos se estiman distribuciones que el Censo NO publica por AGEB
(tamano de hogar, edad del menor, edad del jefe, NSE AMAI).
"""
import numpy as np


def ipu(X: np.ndarray, T: np.ndarray, W0: np.ndarray, max_iter: int = 200, tol: float = 5e-3):
    """IPU vectorizado para todas las areas a la vez.

    X  : donantes x restricciones (conteos >= 0). La columna 0 = 1 (total de hogares).
    T  : areas x restricciones (totales objetivo; NaN = restriccion no disponible en esa area).
    W0 : areas x donantes (pesos iniciales).
    Devuelve (W, err) con err = error relativo maximo por area.
    """
    W = W0 * (T[:, [0]] / W0.sum(axis=1, keepdims=True))
    disponible = ~np.isnan(T)
    Tz = np.nan_to_num(T)
    piso = np.maximum(0.05 * T[:, [0]], 1.0)          # escala minima: 5% de los hogares del area
    for it in range(max_iter):
        for j in range(X.shape[1]):
            nz = X[:, j] > 0
            s = W[:, nz] @ X[nz, j]
            ratio = np.where(Tz[:, j] <= 0, 1e-6, Tz[:, j] / np.where(s > 0, s, 1))
            ratio = np.where(disponible[:, j] & ((s > 0) | (Tz[:, j] <= 0)), ratio, 1.0)
            W[:, nz] *= ratio[:, None]
        if it % 10 == 9 or it == max_iter - 1:
            err = np.where(disponible, np.abs(W @ X - Tz) / np.maximum(Tz, piso), 0).max(axis=1)
            if err.max() < tol:
                break
    return W, err
