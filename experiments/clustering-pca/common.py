"""Fonctions partagées : fenêtres, étiquettes de groupe, ACP, FCM, CAH, modèle nul, autres algorithmes de regroupement.

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv`, taille 300 mots (profil
global des datasets) ; leur texte vient du pivot `data/pivot/` (loaders.py de dataset-validation), leurs indicateurs du
package text_rigidity.
"""
import json
import os
import sys
import textwrap

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import adjusted_rand_score, silhouette_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
SIZE = 300
VALIDATION = os.path.join(HERE, "..", "rigidity-indicators", "dataset-validation")
sys.path.insert(0, VALIDATION)
import loaders  # noqa: E402
from analysis import MIN_REF_TOKENS  # noqa: E402

WINDOWS = os.path.join(VALIDATION, "results", "windows.csv")
KS = range(2, 7)
LANGS = {"fr", "en", "de", "fi", "sv"}
# Indicateurs du jeu Claude-Bertrand (pca_indicators.py) : nom affiché, signe pour « + = plus rigide »
IND = {"formularity": ("Formularité", 1), "formularity_nempool": ("Formularité (NEM.fr : réf. commune)", 1),
       "h_rate": ("ĥ (Bentz)", -1), "distinct2": ("Distinct-2", -1), "kl": ("KL POS", 1), "punct": ("Ponctuation", 1),
       "balance": ("Balance phrastique", -1)}
# Ce que veut dire, en mots, une valeur haute (côté rigide) et basse (côté souple) de chaque indicateur orienté
POLES = {"formularity": ("formules répétées", "pas de formule"),
         "formularity_nempool": ("formules répétées", "pas de formule"),
         "h_rate": ("vocabulaire répétitif", "vocabulaire varié"),
         "distinct2": ("bigrammes répétés", "bigrammes variés"),
         "kl": ("POS atypiques", "POS ordinaires"),
         "punct": ("ponctuation dense", "peu de ponctuation"),
         "balance": ("peu de mots de liaison", "beaucoup de mots de liaison")}


def load_windows():
    """Fenêtres de SIZE mots, avec un identifiant `wid` et l'étiquette de groupe `groupe`."""
    w = pd.read_csv(WINDOWS, dtype={"doc_id": str})
    w = w[w["size"] == SIZE].reset_index(drop=True)
    w.insert(0, "wid", w.dataset + ":" + w.doc_id + ":" + w.start.astype(str))
    w["groupe"] = group_labels(w.dataset)
    # formularité non comparable sous MIN_REF_TOKENS de référence (genres de NEM.fr), comme dans analysis.py
    w.loc[w.ref_tokens < MIN_REF_TOKENS, "formularity"] = np.nan
    # variante NEMpool : genres de NEM.fr notés contre une référence commune à tout NEM.fr (nem_formularity.py)
    pooled = os.path.join(RESULTS, "nem_formularity_pooled.csv")
    if os.path.exists(pooled):
        nem = pd.read_csv(pooled).set_index("wid")["formularity"]
        w["formularity_nempool"] = w.formularity.fillna(w.wid.map(nem))
    return w


def group_labels(datasets):
    """Un groupe par dataset ; langues d'un même corpus fusionnées (« hipe2020 (fr, en, de) ») ; NEM.fr par genre."""
    langs = {}
    for d in dict.fromkeys(datasets):
        base, _, lg = d.rpartition("-")
        if base and lg in LANGS:
            langs.setdefault(base, []).append(lg)
    out = []
    for d in datasets:
        base, _, lg = d.rpartition("-")
        if d.startswith("nem-"):
            out.append(f"NEM.fr {d[4:]}")
        elif base in langs and len(langs[base]) > 1:
            out.append(f"{base} ({', '.join(langs[base])})")
        else:
            out.append(d)
    return out


def group_order(g):
    base = [x for x in dict.fromkeys(g) if not x.startswith("NEM.fr ")]
    return base + sorted(x for x in set(g) if x.startswith("NEM.fr "))


def palette(order):
    pal = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("Dark2").colors)
    return {c: pal[i % len(pal)] for i, c in enumerate(order)}


def zs(X):
    return (X - X.mean(0)) / X.std(0)


def pca(Z):
    """Variance expliquée (%) et vecteurs propres (lignes de Vt) d'une matrice centrée-réduite."""
    _, S, Vt = np.linalg.svd(Z, full_matrices=False)
    return S ** 2 / (S ** 2).sum() * 100, Vt


def kaiser(var, p):
    return int((var > 100 / p).sum())


def fcm(X, k, m=2.0, n_init=20, iters=300, seed=42):
    """Fuzzy C-Means (m = 2, 20 initialisations), algorithme de Seghier et al. ; renvoie appartenances et centres."""
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        U = rng.dirichlet(np.ones(k), size=len(X))
        for _ in range(iters):
            W = U ** m
            C = (W.T @ X) / W.sum(0)[:, None]
            Un = memberships(X, C, m)
            done = np.abs(Un - U).max() < 1e-6
            U = Un
            if done:
                break
        J = ((U ** m) * np.linalg.norm(X[:, None] - C[None], axis=2) ** 2).sum()
        if best is None or J < best[0]:
            best = (J, U, C)
    return best[1], best[2]


def memberships(X, C, m=2.0):
    D = np.fmax(np.linalg.norm(X[:, None, :] - C[None], axis=2), 1e-10)
    return 1.0 / ((D[:, :, None] / D[:, None, :]) ** (2 / (m - 1))).sum(2)


def fig_partitions(PD, g, order, labs, title, sil, null, path):
    """Ligne 1 : plan PC1-PC2 coloré par cluster ; ligne 2 : tableau groupe × cluster (%), k = 2..6."""
    ks = list(KS)
    fig, ax = plt.subplots(2, len(ks), figsize=(5.6 * len(ks), 5.5 + 0.3 * len(order) + 1.5),
                           gridspec_kw={"height_ratios": [5, 0.3 * len(order) + 1]})
    cmap = plt.get_cmap("tab10")
    for c_, k in enumerate(ks):
        lab = labs[k]
        for j in range(k):
            m_ = lab == j
            if m_.any():
                ax[0, c_].scatter(PD[m_, 0], PD[m_, 1], s=6, color=cmap(j), alpha=0.5, label=f"c{j}")
        ax[0, c_].legend(fontsize=7, markerscale=2)
        ax[0, c_].set_xlabel("PC1"); ax[0, c_].set_ylabel("PC2")
        ax[0, c_].set_title(f"k = {k} : silhouette {sil[k]:.2f}\nnuage gaussien sans cluster : {null[k]:.2f}", fontsize=10)
        tab = np.array([[100 * float((lab[g == grp] == j).mean()) for j in range(k)] for grp in order])
        ax[1, c_].axis("off")
        t = ax[1, c_].table(cellText=[[f"{v:.0f}" for v in r] for r in tab],
                            rowLabels=[f"{grp} (n={int((g == grp).sum())})" for grp in order],
                            colLabels=[f"c{j}" for j in range(k)], cellColours=plt.get_cmap("YlGn")(tab / 100 * 0.8),
                            loc="upper center")
        t.auto_set_font_size(False); t.set_fontsize(7.5); t.scale(1, 1.2)
    fig.suptitle(title, fontsize=11)
    plt.tight_layout(rect=(0, 0, 1, 0.97)); plt.savefig(path, dpi=100); plt.close()


def clustering(g, PD, out, suffix=""):
    """FCM (Seghier et al.) et CAH Ward sur les coordonnées PD, k = 2..6. Clusters numérotés par PC1 décroissant.
    Modèle nul : même méthode sur un nuage gaussien de même covariance, sans cluster (10 tirages). Si la silhouette réelle
    ressemble à celle du nul, la partition coupe un continuum au lieu de révéler des groupes."""
    order = group_order(g)
    dims = PD.shape[1]
    rng = np.random.default_rng(0)
    cov = np.cov(PD.T)
    nulls = [rng.multivariate_normal(np.zeros(dims), cov, size=len(PD)) for _ in range(10)]
    null_ward = [linkage(Q, "ward") for Q in nulls]
    W = linkage(PD, "ward")

    def by_pc1(lab):
        cent = np.array([PD[lab == j, 0].mean() if (lab == j).any() else -np.inf for j in range(lab.max() + 1)])
        return np.argsort(np.argsort(-cent))[lab]

    res, lf, lw = {}, {}, {}
    for k in KS:
        U, _ = fcm(PD, k)
        lf[k] = by_pc1(U.argmax(1))
        lw[k] = by_pc1(fcluster(W, k, "maxclust") - 1)
        nf = [float(silhouette_score(Q, fcm(Q, k)[0].argmax(1))) for Q in nulls]
        nw = [float(silhouette_score(Q, fcluster(L, k, "maxclust"))) for Q, L in zip(nulls, null_ward)]
        res[k] = {"FCM": {"silhouette": round(float(silhouette_score(PD, lf[k])), 3), "nul_moyen": round(float(np.mean(nf)), 3),
                          "nul_max": round(float(np.max(nf)), 3),
                          "FPC": round(float((U ** 2).sum() / len(PD)), 3),
                          "PE": round(float(-(U * np.log(U)).sum() / len(PD)), 3),
                          "clusters_non_vides": int(len(set(lf[k])))},
                  "CAH_Ward": {"silhouette": round(float(silhouette_score(PD, lw[k])), 3), "nul_moyen": round(float(np.mean(nw)), 3),
                               "nul_max": round(float(np.max(nw)), 3)},
                  "ARI_FCM_vs_CAH": round(float(adjusted_rand_score(lf[k], lw[k])), 3)}
    for name, labs, key in (("FCM (m = 2), algorithme de Seghier et al.", lf, "FCM"), ("CAH Ward", lw, "CAH_Ward")):
        fig_partitions(PD, g, order, labs, f"{name} sur PC1-PC{dims}, {len(PD)} fenêtres",
                       {k: res[k][key]["silhouette"] for k in KS}, {k: res[k][key]["nul_moyen"] for k in KS},
                       f"{out}/clusters_{key.split('_')[0]}{suffix}_k2-6.png")
    json.dump({"dims": dims, "indices": res}, open(f"{out}/clusters{suffix}.json", "w"), ensure_ascii=False, indent=1)
    return res, {k: (lf[k], lw[k]) for k in KS}


def other_algorithms(g, PD, out, suffix=""):
    """Contrôle du choix du FCM : d'autres algorithmes, chacun avec SON critère de choix du nombre de groupes.
    k-means : silhouette maximale (k = 2..15) ; GMM : BIC minimal (k = 1..10) ; CAH Ward : plus grand saut de hauteur ;
    HDBSCAN : nombre de groupes libre, avec une part de « bruit ». Accord avec les groupes : ARI et AMI (0 = hasard).
    Sorties : algos{suffix}.png (plan PC1-PC2 coloré par cluster + tableau groupe × cluster), algos{suffix}.json."""
    from sklearn.cluster import HDBSCAN, KMeans
    from sklearn.metrics import adjusted_mutual_info_score
    from sklearn.mixture import GaussianMixture
    res = {}
    sils = {k: silhouette_score(PD, KMeans(k, n_init=20, random_state=42).fit_predict(PD)) for k in range(2, 16)}
    k = max(sils, key=sils.get)
    res["k-means"] = (KMeans(k, n_init=20, random_state=42).fit_predict(PD), f"k = {k} (silhouette max {sils[k]:.2f})",
                      {"silhouette": {str(x): round(float(v), 3) for x, v in sils.items()}})
    bics = {k: GaussianMixture(k, covariance_type="full", n_init=5, random_state=42).fit(PD).bic(PD) for k in range(1, 11)}
    k = min(bics, key=bics.get)
    res["GMM (BIC)"] = (GaussianMixture(k, covariance_type="full", n_init=5, random_state=42).fit(PD).predict(PD),
                        f"k = {k} (BIC min)", {"BIC": {str(x): round(float(v), 1) for x, v in bics.items()}})
    W = linkage(PD, "ward")
    h = W[::-1, 2]                      # h[0] = dernière fusion (passage 2 -> 1)
    gaps = {k: h[k - 2] - h[k - 1] for k in range(2, 16)}  # saut entre la partition à k et celle à k+1
    k = max(gaps, key=gaps.get)
    res["CAH Ward"] = (fcluster(W, k, "maxclust") - 1, f"k = {k} (plus grand saut)",
                       {"sauts": {str(x): round(float(v), 2) for x, v in gaps.items()}})
    lab = HDBSCAN(min_cluster_size=max(5, int(0.03 * len(PD))), copy=True).fit_predict(PD)
    res["HDBSCAN"] = (lab, f"{len(set(lab) - {-1})} groupes, bruit {100 * (lab == -1).mean():.0f} %", {})

    order = group_order(g)
    fig, ax = plt.subplots(2, 4, figsize=(26, 6 + 0.33 * len(order) + 5),
                           gridspec_kw={"height_ratios": [5, 0.33 * len(order) + 1]})
    summary = {"dims": PD.shape[1]}
    for c, (alg, (lab, desc, extra)) in enumerate(res.items()):
        ids = sorted(set(lab) - {-1}, key=lambda j: -PD[lab == j, 0].mean())   # numéros par PC1 décroissant
        lab2 = np.array([{j: i for i, j in enumerate(ids)}.get(x, -1) for x in lab])
        cmap = plt.get_cmap("tab10" if len(ids) <= 10 else "tab20")
        if (lab2 == -1).any():
            ax[0, c].scatter(PD[lab2 == -1, 0], PD[lab2 == -1, 1], s=8, color="lightgrey", label="bruit")
        for j in range(len(ids)):
            ax[0, c].scatter(PD[lab2 == j, 0], PD[lab2 == j, 1], s=8, color=cmap(j), label=f"c{j}")
        ari, ami = adjusted_rand_score(g, lab2), adjusted_mutual_info_score(g, lab2)
        ax[0, c].set_title(f"{alg} sur PC1-PC{PD.shape[1]} : {desc}\nARI {ari:.2f}, AMI {ami:.2f} avec les groupes", fontsize=10)
        ax[0, c].set_xlabel("PC1"); ax[0, c].set_ylabel("PC2"); ax[0, c].legend(fontsize=7, ncol=2)
        cols = list(range(len(ids))) + ([-1] if (lab2 == -1).any() else [])
        tab = np.array([[100 * float((lab2[g == grp] == j).mean()) for j in cols] for grp in order])
        ax[1, c].axis("off")
        t = ax[1, c].table(cellText=[[f"{v:.0f}" for v in row] for row in tab],
                           rowLabels=[f"{grp} (n={int((g == grp).sum())})" for grp in order],
                           colLabels=[f"c{j}" if j >= 0 else "bruit" for j in cols],
                           cellColours=plt.get_cmap("YlGn")(tab / 100 * 0.8), loc="upper center")
        t.auto_set_font_size(False); t.set_fontsize(7); t.scale(1, 1.25)
        summary[alg] = {"choix": desc, "ARI": round(float(ari), 3), "AMI": round(float(ami), 3), **extra,
                        "repartition_pct": {grp: [round(float(v), 1) for v in row] for grp, row in zip(order, tab)}}
    plt.tight_layout(); plt.savefig(f"{out}/algos{suffix}.png", dpi=100); plt.close()
    json.dump(summary, open(f"{out}/algos{suffix}.json", "w"), ensure_ascii=False, indent=1)
    return {alg: (v["choix"], v["ARI"], v["AMI"]) for alg, v in summary.items() if alg != "dims"}


def boxplots(ax, P, g, order, i, var, poles):
    """Boîtes à moustaches des groupes sur la composante i, triées par médiane ; poles = (côté −, côté +) en mots."""
    srt = sorted(order, key=lambda c: np.median(P[g == c, i]))
    ax.boxplot([P[g == c, i] for c in srt], orientation="horizontal", tick_labels=srt, showfliers=False,
               patch_artist=True, boxprops={"facecolor": "#e8e7e3", "edgecolor": "#52514e"},
               medianprops={"color": "#0b0b0b", "lw": 2}, whiskerprops={"color": "#52514e"}, capprops={"color": "#52514e"})
    ax.axvline(0, color="grey", lw=0.5, ls=":")
    ax.set_xlabel(f"PC{i + 1} ({var[i]:.1f} % de la variance)", fontsize=10)
    pole_labels(ax, poles, "x", width=28)
    ax.set_title(f"Position des groupes sur PC{i + 1}\nboîte : 50 % central des fenêtres · trait : médiane · "
                 "moustaches : 1,5 × écart interquartile", fontsize=10)


def pole_labels(ax, poles, axis, width=42):
    """Écrit sous l'axe x (ou à gauche de l'axe y) ce que veulent dire ses deux extrémités, poles = (côté −, côté +)."""
    kw = {"transform": ax.transAxes, "fontsize": 9.5, "color": "#1c5cab", "linespacing": 1.2}
    lo, hi = (textwrap.fill(t, width) for t in (f"← {poles[0]}", f"{poles[1]} →"))
    if axis == "x":
        ax.text(0, -0.065, lo, ha="left", va="top", **kw)
        ax.text(1, -0.065, hi, ha="right", va="top", **kw)
    else:
        ax.text(-0.11, 0, lo, ha="right", va="bottom", rotation=90, **kw)
        ax.text(-0.11, 1, hi, ha="right", va="top", rotation=90, **kw)
