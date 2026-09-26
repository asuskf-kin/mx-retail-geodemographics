"""Regla NSE AMAI 2024 (vigente; mismos puntos y cortes que la 2022) + imputacion de # banos completos y # autos con ENIGH 2024.

El Censo 2020 (cuestionario ampliado) solo pregunta si hay auto (si/no) y si hay
regadera y excusado, pero no CUANTOS. La regla AMAI distingue 1 vs 2+ en ambos,
asi que se estima P(2+ | 1+) con un logit entrenado en ENIGH 2024 (sureste urbano)
y cada hogar se reparte entre los 4 escenarios posibles (probabilidad por nivel).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# ---- Regla AMAI 2024 = puntos y cortes de la Regla 2022 (AMAI, Nota metodologica NSE 2024, oct-2023:
#      "mantener la regla AMAI 2022 vigente, sin cambios por dos anos mas, bajo el nuevo nombre de regla AMAI 2024").
#      Fuentes: amai.org/descargas/NOTA_METODOLOGICA_NSE_AMAI_2024_v6.pdf y amai.org/descargas/CUESTIONARIO_AMAI_2022.pdf ----
PTS_BANOS = {0: 0, 1: 24, 2: 47}
PTS_AUTOS = {0: 0, 1: 22, 2: 43}
PTS_INTERNET = {0: 0, 1: 32}
PTS_OCUP = {0: 0, 1: 15, 2: 31, 3: 46, 4: 61}
PTS_DORM = {0: 0, 1: 8, 2: 16, 3: 24, 4: 32}
CORTES = [(202, "A/B"), (168, "C+"), (141, "C"), (116, "C-"), (95, "D+"), (48, "D"), (0, "E")]
NIVELES = ["A/B", "C+", "C", "C-", "D+", "D", "E"]


def nivel_nse(puntos):
    puntos = np.asarray(puntos, dtype=float)
    out = np.full(puntos.shape, "E", dtype=object)
    for corte, niv in reversed(CORTES):
        out[puntos >= corte] = niv
    return out


def edu_censo(nivacad: pd.Series, escolari: pd.Series) -> pd.Series:
    """NIVACAD/ESCOLARI del Censo 2020 -> puntos AMAI 2024 (= 2022) de escolaridad del jefe."""
    n = pd.to_numeric(nivacad, errors="coerce")
    g = pd.to_numeric(escolari, errors="coerce").fillna(0)
    pts = pd.Series(np.nan, index=n.index)
    pts[n.isin([0, 1])] = 0                        # no estudio / preescolar
    pts[(n == 2) & (g < 6)] = 6                    # primaria incompleta
    pts[(n == 2) & (g >= 6)] = 11                  # primaria completa
    pts[(n == 3) & (g < 3)] = 12                   # secundaria incompleta
    pts[(n == 3) & (g >= 3)] = 18                  # secundaria completa
    pts[n.isin([4, 5]) & (g < 3)] = 23             # preparatoria incompleta
    pts[n.isin([4, 5]) & (g >= 3)] = 27            # preparatoria completa
    pts[n.isin([6, 7, 9])] = 23                    # carrera tecnica/comercial, normal basica
    pts[n == 8] = 27                               # tecnica con preparatoria terminada
    pts[n.isin([10, 11]) & (g < 4)] = 36           # licenciatura incompleta
    pts[n.isin([10, 11]) & (g >= 4)] = 59          # licenciatura completa
    pts[n.isin([12, 13, 14])] = 85                 # especialidad / maestria / doctorado
    return pts                                     # NaN = no especificado (99)


def edu_enigh(educa_jefe: pd.Series) -> pd.Series:
    m = {1: 0, 2: 0, 3: 6, 4: 11, 5: 12, 6: 18, 7: 23, 8: 27, 9: 36, 10: 59, 11: 85}
    return pd.to_numeric(educa_jefe, errors="coerce").map(m)


# ------------------------------- ENIGH ---------------------------------------
FEATURES = ["pts_edu", "dorm", "cuartos", "internet", "ocup", "integ", "pc", "lavadora", "micro", "otro"]


def cargar_enigh(carpeta: Path, estados) -> pd.DataFrame:
    """Hogares ENIGH 2024 en localidades de 2,500+ hab (tam_loc 1-3) de los estados dados."""
    def rd(tabla, cols):
        f = next(Path(carpeta).glob(f"conjunto_de_datos_{tabla}_enigh2024_ns/conjunto_de_datos/*.csv"))
        return pd.read_csv(f, usecols=cols, dtype={"folioviv": str, "foliohog": str, "ubica_geo": str})

    viv = rd("viviendas", ["folioviv", "bano_comp", "cuart_dorm", "num_cuarto"])
    hog = rd("hogares", ["folioviv", "foliohog", "num_auto", "num_van", "num_pick", "conex_inte",
                         "num_compu", "num_lap", "num_lavad", "num_micro"])
    con = rd("concentradohogar", ["folioviv", "foliohog", "ubica_geo", "tam_loc", "factor",
                                   "educa_jefe", "tot_integ", "ocupados"])
    con["ubica_geo"] = con["ubica_geo"].str.zfill(5)
    con = con[con.ubica_geo.str[:2].isin(estados) & con.tam_loc.isin([1, 2, 3])]
    d = con.merge(hog, on=["folioviv", "foliohog"]).merge(viv, on="folioviv")

    def num(c):
        return pd.to_numeric(d[c], errors="coerce").fillna(0)

    out = pd.DataFrame({
        "ent": d.ubica_geo.str[:2], "factor": d.factor,
        "pts_edu": edu_enigh(d.educa_jefe),
        "dorm": num("cuart_dorm").clip(0, 4), "cuartos": num("num_cuarto").clip(0, 8),
        "internet": (num("conex_inte") == 1).astype(int),
        "ocup": num("ocupados").clip(0, 4), "integ": num("tot_integ").clip(0, 8),
        "pc": ((num("num_compu") + num("num_lap")) > 0).astype(int),
        "lavadora": (num("num_lavad") > 0).astype(int),
        "micro": (num("num_micro") > 0).astype(int),
        "n_banos": num("bano_comp"),
        "n_autos": num("num_auto") + num("num_van") + num("num_pick"),
    })
    return out.dropna(subset=["pts_edu"]).reset_index(drop=True)


def entrenar_modelos(e: pd.DataFrame) -> dict:
    """Dos logits ponderados: P(2+ banos | >=1) y P(2+ autos | >=1)."""
    modelos = {}
    for var, otro in [("n_banos", "n_autos"), ("n_autos", "n_banos")]:
        s = e[e[var] >= 1].assign(otro=lambda x: (x[otro] >= 1).astype(int))
        m = LogisticRegression(max_iter=2000)
        m.fit(s[FEATURES], (s[var] >= 2).astype(int), sample_weight=s.factor)
        modelos[var] = m
    return modelos


def distribucion_nse(df: pd.DataFrame, modelos: dict) -> pd.DataFrame:
    """Probabilidad de cada nivel NSE por hogar.

    df requiere: pts_edu, dorm, cuartos, internet, ocup (14+ para la regla), ocup_model
    (misma definicion que ENIGH), integ, pc, lavadora, micro, banos1 y auto1 (0/1).
    """
    X = df.assign(ocup=df["ocup_model"].clip(0, 4))
    pb2 = modelos["n_banos"].predict_proba(X.assign(otro=df.auto1)[FEATURES])[:, 1] * df.banos1.values
    pa2 = modelos["n_autos"].predict_proba(X.assign(otro=df.banos1)[FEATURES])[:, 1] * df.auto1.values
    base = (df.pts_edu.values + df.internet.map(PTS_INTERNET).values
            + df.ocup.clip(0, 4).map(PTS_OCUP).values + df.dorm.clip(0, 4).map(PTS_DORM).values)
    prob = np.zeros((len(df), len(NIVELES)))
    for b2 in (0, 1):
        for a2 in (0, 1):
            w = (pb2 if b2 else 1 - pb2) * (pa2 if a2 else 1 - pa2)
            nb = np.where(df.banos1.values == 1, 1 + b2, 0)
            na = np.where(df.auto1.values == 1, 1 + a2, 0)
            pts = base + np.vectorize(PTS_BANOS.get)(nb) + np.vectorize(PTS_AUTOS.get)(na)
            niv = nivel_nse(pts)
            for k, n in enumerate(NIVELES):
                prob[:, k] += w * (niv == n)
    return pd.DataFrame(prob, columns=NIVELES, index=df.index)


def nse_real_enigh(e: pd.DataFrame) -> pd.Series:
    """NSE con los conteos reales de ENIGH (para validar la imputacion)."""
    pts = (e.pts_edu + e.n_banos.clip(0, 2).map(PTS_BANOS) + e.n_autos.clip(0, 2).map(PTS_AUTOS)
           + e.internet.map(PTS_INTERNET) + e.ocup.clip(0, 4).map(PTS_OCUP) + e.dorm.clip(0, 4).map(PTS_DORM))
    return pd.Series(nivel_nse(pts), index=e.index)
