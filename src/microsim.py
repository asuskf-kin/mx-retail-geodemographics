"""Microsimulacion espacial por AGEB (Iterative Proportional Updating, Ye et al. 2009).

Cada AGEB recibe pesos sobre los hogares donantes de la muestra censal, de modo que
los totales ponderados reproduzcan lo que el Censo 2020 publica para esa AGEB
(hogares, autos, internet, personas por edad, ocupados, escolaridad, etc.).
Con esos pesos se estiman distribuciones que el Censo NO publica por AGEB
(tamano de hogar, edad del menor, edad del jefe, NSE AMAI).

Implementacion comprimida (mismo resultado que el IPU directo, hasta error de redondeo):
- El IPU multiplica, en cada area, a todos los donantes con X[:, j] > 0 por el mismo factor, asi que
  donantes con el mismo patron de ceros reciben siempre los mismos factores:
  W[a, d] = W0[a, d] * c[a] * g[a, patron(d)].
- W0 tiene pocas filas distintas (depende solo del municipio del area), asi que las sumas
  sum_d W0[a, d] * X[d, j] por patron se precalculan una vez por fila distinta.
Con esto la iteracion trabaja sobre g (areas x patrones) y no sobre W (areas x donantes):
ZM Guadalajara (2,000 AGEB x 40,799 donantes, 15k patrones) pasa de >90 min a unos minutos.
"""
import numpy as np
from scipy import sparse


def ipu(X: np.ndarray, T: np.ndarray, W0: np.ndarray, max_iter: int = 200, tol: float = 5e-3):
    """IPU vectorizado para todas las areas a la vez.

    X  : donantes x restricciones (conteos >= 0). La columna 0 = 1 (total de hogares).
    T  : areas x restricciones (totales objetivo; NaN = restriccion no disponible en esa area).
    W0 : areas x donantes (pesos iniciales).
    Devuelve (W, err) con err = error relativo maximo por area.
    """
    D, K = X.shape
    _, patron = np.unique(X > 0, axis=0, return_inverse=True)
    patron = patron.ravel()
    P = patron.max() + 1
    nzp = np.zeros((P, K), bool)
    nzp[patron] = X > 0                                  # el patron p tiene X[:, j] > 0

    # filas distintas de W0 (hash de fila; np.unique(axis=0) sobre areas x donantes es lento)
    h = W0 @ np.random.default_rng(0).random(D)
    _, primera, fila = np.unique(h, return_index=True, return_inverse=True)
    fila = fila.ravel()
    U = W0[primera]
    # ordenar areas por fila de W0 para que cada grupo sea un bloque contiguo
    orden = np.argsort(fila, kind="stable")
    T, W0, fila = T[orden], W0[orden], fila[orden]
    cortes = np.flatnonzero(np.diff(fila)) + 1
    bloques = [slice(i, k) for i, k in zip(np.r_[0, cortes], np.r_[cortes, len(fila)])]
    c = T[:, 0] / W0.sum(axis=1)                         # escala inicial: sum W = hogares del area
    # C[j][u, p] = sum_{d en p} U[u, d] * X[d, j]
    C = [np.ascontiguousarray((sparse.csr_matrix((X[:, j], (patron, np.arange(D))), shape=(P, D)) @ U.T).T)
         for j in range(K)]

    def suma(j):                                         # sum_d W[a, d] X[d, j] para todas las areas
        s = np.empty(len(T))
        for b in bloques:                                # un producto matriz-vector por grupo de W0
            s[b] = C[j][fila[b.start]] @ gT[:, b]
        return s * c

    gT = np.ones((P, len(T)))                            # g transpuesta: actualizar patrones = filas contiguas
    disponible = ~np.isnan(T)
    Tz = np.nan_to_num(T)
    piso = np.maximum(0.05 * T[:, [0]], 1.0)            # escala minima: 5% de los hogares del area
    for it in range(max_iter):
        for j in range(K):
            s = suma(j)
            ratio = np.where(Tz[:, j] <= 0, 1e-6, Tz[:, j] / np.where(s > 0, s, 1))
            ratio = np.where(disponible[:, j] & ((s > 0) | (Tz[:, j] <= 0)), ratio, 1.0)
            np.multiply(gT, ratio, out=gT, where=nzp[:, [j]])   # in-place, sin copiar filas
        if it % 10 == 9 or it == max_iter - 1:
            WX = np.column_stack([suma(j) for j in range(K)])
            err = np.where(disponible, np.abs(WX - Tz) / np.maximum(Tz, piso), 0).max(axis=1)
            if err.max() < tol:
                break
    inv = np.argsort(orden)                              # regresar al orden original de las areas
    return (W0 * c[:, None] * gT[patron].T)[inv], err[inv]
