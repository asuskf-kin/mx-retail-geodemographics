"""EDA estadistico para ventas por punto de venta (pandas + SciPy + scikit-learn).

Port de la skill retail-math-eda (su scripts/retail_eda.py usa polars, que no esta instalado aqui).
Todo lo aleatorio (bootstrap, permutaciones, MI) usa una semilla fija: SEMILLA.

Contenido:
- distribucion: univariado (momentos robustos, concentracion, Hill), hill_curva, ajuste_distribuciones, gini/lorenz
- dependencia: dependencias (Spearman con IC de Fisher, Pearson sobre log1p, informacion mutua, q de BH)
- grupos: efecto_categorico (Kruskal-Wallis + epsilon^2 con IC bootstrap), comparaciones_pares (Mann-Whitney + delta de Cliff)
- espacial: vecinos_radio, moran_i (autocorrelacion), spearman_bloques (IC por bootstrap de bloques)
- multivariado: matriz_spearman (n efectivo + BH), psd, kmo_bartlett, analisis_paralelo (Horn), varimax,
  correlacion_parcial, meng_z (correlaciones dependientes)
- otros: z_robusto, ic_bootstrap, cramer_v, kappa_cohen (concordancia de clasificaciones), cliff_bloques, kaplan_meier
- graficos: estilo() con la paleta validada de la skill dataviz
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_regression

SEMILLA = 2026


# ─────────────────────────────── utilidades ───────────────────────────────
def ic_bootstrap(x, fn=np.median, B=2000, nivel=0.95, seed=SEMILLA):
    """IC percentil bootstrap de fn(x). Devuelve (estimado, inferior, superior)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    rng = np.random.default_rng(seed)
    bs = np.array([fn(x[rng.integers(0, x.size, x.size)]) for _ in range(B)])
    a = (1 - nivel) / 2
    return fn(x), *np.quantile(bs, [a, 1 - a])


def spearman_ic(rho, n, nivel=0.95):
    """IC de Spearman por transformacion z de Fisher con SE = 1.06 / sqrt(n - 3) (Fieller-Hartley-Pearson)."""
    z, se = np.arctanh(np.clip(rho, -0.999999, 0.999999)), 1.06 / np.sqrt(max(n - 3, 1))
    zc = stats.norm.ppf(1 - (1 - nivel) / 2)
    return np.tanh(z - zc * se), np.tanh(z + zc * se)


def z_robusto(x) -> np.ndarray:
    """z modificado de Iglewicz-Hoaglin: 0.6745 (x - mediana) / MAD. |z| > 3.5 = atipico."""
    x = np.asarray(x, float)
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return 0.6745 * (x - med) / mad if mad > 0 else np.zeros_like(x)


def cliff_delta(a, b):
    """delta de Cliff = P(A > B) - P(A < B) via U de Mann-Whitney. |d|: 0.147 chico, 0.33 medio, 0.474 grande."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * u / (a.size * b.size) - 1


def cramer_v(tabla) -> float:
    """V de Cramer de una tabla de contingencia (0 = independencia, 1 = asociacion perfecta)."""
    t = np.asarray(tabla, float)
    chi2 = stats.chi2_contingency(t, correction=False)[0]
    return float(np.sqrt(chi2 / (t.sum() * (min(t.shape) - 1))))


def kappa_cohen(a, b) -> float:
    """kappa de Cohen entre dos clasificaciones de los mismos casos (1 = acuerdo total, 0 = el acuerdo del azar).
    Lectura de Landis-Koch: < 0.2 pobre, 0.2-0.4 regular, 0.4-0.6 moderado, 0.6-0.8 bueno, > 0.8 casi perfecto."""
    d = pd.DataFrame({"a": np.asarray(a, object), "b": np.asarray(b, object)}).dropna()
    niveles = sorted(set(d.a) | set(d.b))
    t = pd.crosstab(d.a, d.b).reindex(index=niveles, columns=niveles, fill_value=0).to_numpy(float)
    n = t.sum()
    po, pe = np.trace(t) / n, (t.sum(0) @ t.sum(1)) / n ** 2
    return float((po - pe) / (1 - pe)) if pe < 1 else np.nan


def cliff_bloques(grupo_a, y, bloques, B=500, nivel=0.95, seed=SEMILLA):
    """delta de Cliff de y entre grupo_a (booleano) y el resto, con IC por bootstrap de BLOQUES espaciales (se remuestrean
    bloques completos, como spearman_bloques). Devuelve (delta, inferior, superior)."""
    d = pd.DataFrame({"a": np.asarray(grupo_a, bool), "y": np.asarray(y, float), "g": np.asarray(bloques)}).dropna()
    idx = d.groupby("g").indices
    llaves = np.array(list(idx))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        s = d.iloc[np.concatenate([idx[k] for k in rng.choice(llaves, llaves.size)])]
        if s.a.any() and (~s.a).any():
            bs.append(cliff_delta(s.y[s.a], s.y[~s.a]))
    a = (1 - nivel) / 2
    return cliff_delta(d.y[d.a], d.y[~d.a]), *np.quantile(bs, [a, 1 - a])


# ─────────────────────────────── distribucion ───────────────────────────────
def hill(x, k=None):
    """Indice de cola de Hill sobre los k mayores. alpha < 2 -> varianza infinita (no reportar sd)."""
    x = np.sort(np.asarray(x, float)[np.asarray(x, float) > 0])[::-1]
    if x.size < 50:
        return np.nan
    k = min(k or max(int(round(x.size ** 0.5)), 10), x.size - 1)
    suma = np.sum(np.log(x[:k]) - np.log(x[k]))
    return k / suma if suma > 0 else np.inf


def hill_curva(x, ks=None) -> pd.Series:
    """alpha de Hill para varios k (Hill plot): el valor confiable es la meseta, no un k aislado."""
    x = np.asarray(x, float)
    n = int(np.sum(x > 0))
    ks = ks if ks is not None else np.unique(np.geomspace(10, max(11, n // 5), 30).astype(int))
    return pd.Series({int(k): hill(x, int(k)) for k in ks}, name="alpha")


def gini(x) -> float:
    """Coeficiente de Gini (0 = todos venden igual, 1 = uno vende todo)."""
    x = np.sort(np.asarray(x, float))
    n = x.size
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def lorenz(x):
    """Curva de Lorenz: (fraccion acumulada de PDV, fraccion acumulada del volumen), de menor a mayor."""
    x = np.sort(np.asarray(x, float))
    return np.r_[0, np.arange(1, x.size + 1) / x.size], np.r_[0, np.cumsum(x) / x.sum()]


def ajuste_distribuciones(x, familias=("lognorm", "gamma", "weibull_min", "expon")) -> pd.DataFrame:
    """Ajuste por maxima verosimilitud (loc = 0) y comparacion por AIC; KS como bondad de ajuste descriptiva.

    Con n grande el KS rechaza casi siempre: se lee el AIC (menor = mejor) y la D de KS como distancia.
    """
    x = np.asarray(x, float)
    x = x[x > 0]
    filas = []
    for f in familias:
        dist = getattr(stats, f)
        par = dist.fit(x, floc=0)
        ll = np.sum(dist.logpdf(x, *par))
        k = len(par) - 1                                  # loc fijo
        d = stats.kstest(x, f, args=par).statistic
        filas.append({"familia": f, "parametros": np.round(par, 4).tolist(), "logL": ll, "AIC": 2 * k - 2 * ll, "KS_D": d})
    out = pd.DataFrame(filas).sort_values("AIC").reset_index(drop=True)
    out["ΔAIC"] = out.AIC - out.AIC.min()
    return out


def univariado(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Momentos, estadisticos robustos (con IC bootstrap de la mediana), concentracion, Gini y cola por columna."""
    filas = []
    for c in cols:
        x = df[c].dropna().to_numpy(float)
        pos = np.sort(x[x > 0])[::-1]
        med, lo, hi = ic_bootstrap(x)
        filas.append({
            "variable": c, "n": x.size, "ceros_%": np.mean(x == 0) * 100, "negativos": int(np.sum(x < 0)),
            "media": x.mean(), "mediana": med, "mediana_IC95": f"[{lo:.2f}, {hi:.2f}]",
            "MAD_n": 1.4826 * np.median(np.abs(x - np.median(x))),
            "p99": np.percentile(x, 99), "max": x.max(), "asimetria": stats.skew(x), "curtosis_exc": stats.kurtosis(x),
            "cuota_top1%": pos[: max(1, pos.size // 100)].sum() / pos.sum() * 100 if pos.size else np.nan,
            "cuota_top20%": pos[: max(1, pos.size // 5)].sum() / pos.sum() * 100 if pos.size else np.nan,
            "gini": gini(x) if x.sum() > 0 else np.nan, "hill_alpha": hill(pos),
        })
    out = pd.DataFrame(filas).set_index("variable")
    out["lectura"] = np.where(out.hill_alpha < 2, "cola muy pesada: usar mediana/MAD y log1p",
                     np.where(out.asimetria > 2, "asimetrica: usar log1p", "aprox. simetrica"))
    return out


# ─────────────────────────────── dependencia ───────────────────────────────
def dependencias(df: pd.DataFrame, x_cols, y_cols, q=0.05, con_mi=True) -> pd.DataFrame:
    """Spearman (IC95 de Fisher), Pearson sobre log1p e informacion mutua (nats) de cada x contra cada y.

    Las p se corrigen por comparaciones multiples con Benjamini-Hochberg (q_BH).
    MI alta con |rho| baja = relacion no monotona (la marca `no_monotona`).
    """
    filas = []
    for xc in x_cols:
        for yc in y_cols:
            d = df[[xc, yc]].dropna()
            if len(d) < 30 or d[xc].nunique() < 2:
                continue
            rho, p = stats.spearmanr(d[xc], d[yc])
            lo, hi = spearman_ic(rho, len(d))
            fila = {"x": xc, "y": yc, "n": len(d), "spearman": rho, "IC95": f"[{lo:+.2f}, {hi:+.2f}]",
                    "pearson_log1p": np.corrcoef(np.log1p(d[xc].clip(lower=0)), np.log1p(d[yc].clip(lower=0)))[0, 1], "p": p}
            if con_mi:
                fila["MI"] = float(mutual_info_regression(d[[xc]].to_numpy(float), d[yc].to_numpy(float),
                                                          n_neighbors=3, random_state=SEMILLA)[0])
            filas.append(fila)
    out = pd.DataFrame(filas)
    out["q_BH"] = stats.false_discovery_control(out.p.to_numpy(), method="bh")
    out["significativa"] = out.q_BH < q
    if con_mi:
        out["no_monotona"] = (out.MI > 0.05) & (out.spearman.abs() < 0.15)
    return out.sort_values("spearman", key=np.abs, ascending=False).reset_index(drop=True)


# ─────────────────────────────── grupos ───────────────────────────────
def _epsilon2(grupos):
    h = stats.kruskal(*grupos).statistic
    n, k = sum(len(g) for g in grupos), len(grupos)
    return (h - k + 1) / (n - k)


def efecto_categorico(df: pd.DataFrame, cat_cols, y: str, B=300, seed=SEMILLA) -> pd.DataFrame:
    """Kruskal-Wallis con epsilon^2 (0.01 chico, 0.08 medio, 0.26 grande) e IC95 bootstrap estratificado por nivel."""
    rng = np.random.default_rng(seed)
    filas = []
    for c in cat_cols:
        d = df[[c, y]].dropna()
        grupos = [g[y].to_numpy() for _, g in d.groupby(c) if len(g) >= 20]
        if len(grupos) < 2:
            continue
        h, p = stats.kruskal(*grupos)
        bs = [_epsilon2([g[rng.integers(0, g.size, g.size)] for g in grupos]) for _ in range(B)]
        filas.append({"variable": c, "niveles": len(grupos), "n": sum(len(g) for g in grupos), "H": h, "p": p,
                      "epsilon2": _epsilon2(grupos), "IC95": f"[{np.quantile(bs, .025):.3f}, {np.quantile(bs, .975):.3f}]"})
    out = pd.DataFrame(filas)
    out["q_BH"] = stats.false_discovery_control(out.p.to_numpy(), method="bh")
    return out.sort_values("epsilon2", ascending=False).reset_index(drop=True)


def comparaciones_pares(df: pd.DataFrame, grupo: str, y: str) -> pd.DataFrame:
    """Mann-Whitney por pares de niveles con delta de Cliff y q de BH (post hoc de Kruskal-Wallis)."""
    niveles = [k for k, g in df.groupby(grupo) if len(g) >= 20]
    filas = []
    for i, a in enumerate(niveles):
        for b in niveles[i + 1:]:
            xa, xb = df.loc[df[grupo] == a, y].dropna(), df.loc[df[grupo] == b, y].dropna()
            filas.append({"A": a, "B": b, "mediana_A": xa.median(), "mediana_B": xb.median(),
                          "cliff_delta": cliff_delta(xa, xb), "p": stats.mannwhitneyu(xa, xb).pvalue})
    out = pd.DataFrame(filas)
    out["q_BH"] = stats.false_discovery_control(out.p.to_numpy(), method="bh")
    out["efecto"] = pd.cut(out.cliff_delta.abs(), [-1, .147, .33, .474, 2], labels=["despreciable", "chico", "medio", "grande"])
    return out.sort_values("cliff_delta", key=np.abs, ascending=False).reset_index(drop=True)


# ─────────────────────────────── dependencia espacial ───────────────────────────────
def vecinos_radio(lat, lon, radio_m):
    """Listas de vecinos (indices) a <= radio_m de cada punto, sin incluirse a si mismo (BallTree haversine)."""
    from sklearn.neighbors import BallTree
    X = np.radians(np.column_stack([lat, lon]))
    ind = BallTree(X, metric="haversine").query_radius(X, r=radio_m / 6_371_000)
    return [v[v != i] for i, v in enumerate(ind)]


def moran_i(valores, vecinos, B=199, seed=SEMILLA):
    """I de Moran global con pesos binarios estandarizados por fila y p de permutacion (B permutaciones).

    I > 0: vecinos parecidos (autocorrelacion espacial) -> las observaciones NO son independientes.
    """
    z = np.asarray(valores, float) - np.mean(valores)
    tiene = np.array([len(v) > 0 for v in vecinos])
    filas = np.repeat(np.arange(len(vecinos)), [len(v) for v in vecinos])
    cols = np.concatenate([v for v in vecinos]) if len(filas) else np.array([], int)
    w = np.repeat([1 / len(v) if len(v) else 0 for v in vecinos], [len(v) for v in vecinos])
    def stat(zz):
        lag = np.bincount(filas, weights=w * zz[cols], minlength=zz.size)
        return (zz[tiene] @ lag[tiene]) / (zz[tiene] @ zz[tiene])
    I = stat(z)
    rng = np.random.default_rng(seed)
    perm = np.array([stat(rng.permutation(z)) for _ in range(B)])
    return {"I": I, "E[I]": -1 / (tiene.sum() - 1), "p_perm": (np.sum(perm >= I) + 1) / (B + 1),
            "con_vecinos_%": tiene.mean() * 100}


def spearman_bloques(x, y, grupos, B=500, nivel=0.95, seed=SEMILLA):
    """IC de Spearman por bootstrap de BLOQUES (se remuestrean grupos espaciales completos, no puntos).

    Respeta la dependencia entre puntos cercanos: el IC sale mas ancho que el de Fisher si hay autocorrelacion.
    """
    d = pd.DataFrame({"x": x, "y": y, "g": grupos}).dropna()
    idx = d.groupby("g").indices
    llaves = np.array(list(idx))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        sel = np.concatenate([idx[k] for k in rng.choice(llaves, llaves.size)])
        bs.append(stats.spearmanr(d.x.values[sel], d.y.values[sel])[0])
    a = (1 - nivel) / 2
    return stats.spearmanr(d.x, d.y)[0], *np.nanquantile(bs, [a, 1 - a])


# ─────────────────────────────── estructura multivariada ───────────────────────────────
def matriz_spearman(df: pd.DataFrame, cols, zonas: dict | None = None):
    """Spearman por pares (casos completos de cada par) con n, p y q de BH sobre el triángulo superior.

    zonas = {columna: id de la zona en la que se mide} (p. ej. el vector del bloque al que pertenece la señal). Con
    zonas, la p usa el número de combinaciones (zona de x, zona de y) DISTINTAS del par, no de filas: si varias filas
    comparten la medición de una zona, contar filas daría p optimistas. No se cuentan valores distintos: eso castigaría
    a los conteos discretos, que repiten valores sin repetir zona. Devuelve (rho, n, p, q) como DataFrames p × p.
    """
    X = df[cols]
    rho = X.corr(method="spearman")
    ok = X.notna().to_numpy(float)
    n = pd.DataFrame(ok.T @ ok, index=cols, columns=cols)
    if zonas is not None:
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                m = X[[a, b]].notna().all(axis=1).to_numpy()
                n.loc[a, b] = n.loc[b, a] = len(set(zip(np.asarray(zonas[a])[m], np.asarray(zonas[b])[m])))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = rho * np.sqrt((n - 2) / (1 - rho ** 2))
    p = pd.DataFrame(2 * stats.t.sf(np.abs(t), n - 2), index=cols, columns=cols)
    iu = np.triu_indices(len(cols), 1)
    Q = np.full((len(cols), len(cols)), np.nan)
    pv = p.to_numpy()[iu]
    qv = np.full(pv.size, np.nan)
    ok_p = ~np.isnan(pv)
    qv[ok_p] = stats.false_discovery_control(pv[ok_p], method="bh")
    Q[iu] = qv
    Q[(iu[1], iu[0])] = qv
    return rho, n, p, pd.DataFrame(Q, index=cols, columns=cols)


def psd(R) -> np.ndarray:
    """Proyecta una matriz de correlación por pares a semidefinida positiva (recorta autovalores negativos y reescala)."""
    val, vec = np.linalg.eigh(np.asarray(R, float))
    A = vec @ np.diag(np.clip(val, 1e-6, None)) @ vec.T
    d = np.sqrt(np.diag(A))
    return A / np.outer(d, d)


def kmo_bartlett(R, n) -> dict:
    """Factorabilidad de una matriz de correlación: KMO (≥ 0.6 aceptable, ≥ 0.8 bueno) por variable y global,
    y prueba de esfericidad de Bartlett (H0: R = identidad, no hay estructura común)."""
    R = np.asarray(R, float)
    p = R.shape[0]
    inv = np.linalg.inv(R)
    parcial = -inv / np.sqrt(np.outer(np.diag(inv), np.diag(inv)))
    np.fill_diagonal(parcial, 0)
    r2 = R ** 2
    np.fill_diagonal(r2, 0)
    a2 = parcial ** 2
    chi2 = -(n - 1 - (2 * p + 5) / 6) * np.linalg.slogdet(R)[1]
    gl = p * (p - 1) / 2
    return {"KMO": r2.sum() / (r2.sum() + a2.sum()), "KMO_variable": r2.sum(0) / (r2.sum(0) + a2.sum(0)),
            "bartlett_chi2": chi2, "gl": gl, "p": stats.chi2.sf(chi2, gl)}


def analisis_paralelo(n, p, B=200, percentil=95, seed=SEMILLA) -> np.ndarray:
    """Análisis paralelo de Horn: autovalores de matrices de correlación de datos normales independientes (n × p).
    Se retienen los componentes cuyo autovalor observado supera el percentil de estos (criterio más estricto que Kaiser)."""
    rng = np.random.default_rng(seed)
    ev = [np.linalg.eigvalsh(np.corrcoef(rng.standard_normal((int(n), p)), rowvar=False))[::-1] for _ in range(B)]
    return np.percentile(ev, percentil, axis=0)


def varimax(L, iteraciones=100, tol=1e-6) -> np.ndarray:
    """Rotación varimax de una matriz de cargas (p × k): cada componente queda con pocas variables de carga alta."""
    L = np.asarray(L, float)
    p, k = L.shape
    Rm, d = np.eye(k), 0
    for _ in range(iteraciones):
        Lr = L @ Rm
        u, s, vt = np.linalg.svd(L.T @ (Lr ** 3 - Lr @ np.diag((Lr ** 2).sum(0)) / p))
        Rm, d_ant, d = u @ vt, d, s.sum()
        if d_ant and d / d_ant < 1 + tol:
            break
    return L @ Rm


def correlacion_parcial(x, y, controles) -> tuple:
    """Spearman parcial de x e y controlando por `controles` (residuos de rangos por MCO). Devuelve (rho, p, n)."""
    d = pd.concat([pd.Series(np.asarray(x, float), name="x"), pd.Series(np.asarray(y, float), name="y"),
                   pd.DataFrame(np.asarray(controles, float))], axis=1).dropna()
    Rk = d.rank().to_numpy()
    Z = np.column_stack([np.ones(len(d)), Rk[:, 2:]])
    res = [Rk[:, j] - Z @ np.linalg.lstsq(Z, Rk[:, j], rcond=None)[0] for j in (0, 1)]
    r = np.corrcoef(*res)[0, 1]
    gl = len(d) - 2 - (Rk.shape[1] - 2)
    t = r * np.sqrt(gl / (1 - r ** 2))
    return r, 2 * stats.t.sf(abs(t), gl), len(d)


def meng_z(r1, r2, r12, n) -> tuple:
    """Prueba de Meng, Rosenthal y Rubin (1992) para dos correlaciones DEPENDIENTES que comparten una variable:
    ¿corr(y, x1) = r1 difiere de corr(y, x2) = r2, si corr(x1, x2) = r12? Devuelve (z, p bilateral)."""
    z1, z2 = np.arctanh(r1), np.arctanh(r2)
    rm2 = (r1 ** 2 + r2 ** 2) / 2
    f = min((1 - r12) / (2 * (1 - rm2)), 1)
    h = (1 - f * rm2) / (1 - rm2)
    z = (z1 - z2) * np.sqrt((n - 3) / (2 * (1 - r12) * h))
    return z, 2 * stats.norm.sf(abs(z))


# ─────────────────────────────── supervivencia ───────────────────────────────
def kaplan_meier(duracion, evento) -> pd.DataFrame:
    """Estimador de Kaplan-Meier con IC95 de Greenwood (log-log). evento = 1 si ocurrio, 0 si censurado."""
    d = pd.DataFrame({"t": np.asarray(duracion, float), "e": np.asarray(evento, int)}).sort_values("t")
    tabla = d.groupby("t").agg(eventos=("e", "sum"), total=("e", "size"))
    tabla["en_riesgo"] = len(d) - tabla.total.cumsum().shift(fill_value=0)
    tabla["S"] = np.cumprod(1 - tabla.eventos / tabla.en_riesgo)
    var = np.cumsum(tabla.eventos / (tabla.en_riesgo * (tabla.en_riesgo - tabla.eventos)).replace(0, np.nan)).fillna(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        se = np.sqrt(var) / np.abs(np.log(tabla.S))
        tabla["IC_inf"] = tabla.S ** np.exp(1.96 * se)
        tabla["IC_sup"] = tabla.S ** np.exp(-1.96 * se)
    return tabla[["en_riesgo", "eventos", "S", "IC_inf", "IC_sup"]]


# ─────────────────────────────── graficos ───────────────────────────────
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]   # dataviz, orden fijo
TINTA, TINTA_2, MUTED, GRID, EJE, FONDO = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def estilo():
    """Estilo matplotlib: fondo claro, grid tenue solo en y, ejes recesivos, sin marco superior/derecho."""
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
        "axes.edgecolor": EJE, "axes.labelcolor": TINTA_2, "axes.titlecolor": TINTA, "axes.titlesize": 11,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 9, "lines.linewidth": 2,
        "axes.prop_cycle": mpl.cycler(color=PALETA), "legend.frameon": False, "figure.dpi": 110,
    })
