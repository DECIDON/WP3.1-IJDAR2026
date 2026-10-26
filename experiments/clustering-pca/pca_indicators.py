"""ACP et classifications sur des jeux d'indicateurs « Claude-Bertrand » (fenêtres de 300 mots de windows.csv).

Indicateurs, tous orientés « + = plus rigide » puis centrés-réduits :
  formularité (windows.csv ; log(1 + x)) : part de la fenêtre prise dans des 4-grammes qui reviennent ailleurs dans son
      sous-corpus ;
  ĥ (taux d'entropie des mots, Bentz et al. 2017 : text_rigidity.entropy_rate_lz) : calculé ici sur le texte de la
      fenêtre (absent de windows.csv) ; bas = texte prévisible ;
  Distinct-2 (windows.csv) : part de bigrammes distincts ; bas = texte répétitif ;
  KL des POS (windows.csv ; log) : écart de la distribution des POS à une référence UD de la langue ;
  ponctuation (log(1 + x)) : signes de la famille « punctuation » du package (. , ; : ! ? …) pour 100 mots, comptés
      par text_rigidity.count_typographic_marks (balisage Markdown retiré, une suite de signes = une marque). C'est la
      part ponctuation du formatage typographique, sans parenthèses, tirets, filets ni symboles.
Formularité, ĥ, Distinct-2 et KL ne sont pas retenus par le rapport indicateurs-rigidite.md (sauf la formularité) :
à 300 mots, ĥ doublonne Distinct-2 (ρ ≈ 0,9) ; la KL dépend d'une référence par langue et ne se compare qu'à langue
égale. Quatre jeux :
  indicateurs-claude-bertrand                    = formularité, ĥ, Distinct-2, KL, ponctuation ; genres de NEM.fr exclus
      (formularité non comparable sous 15 000 tokens de référence, règle de analysis.py) ;
  indicateurs-claude-bertrand-sans-distinct2     = idem sans Distinct-2 ;
  ...-NEMpool (pour chacun des deux)             = genres de NEM.fr compris, leur formularité étant calculée contre une
      référence commune à tout NEM.fr (nem_formularity.py), donc mesurée par rapport à NEM.fr et non au genre lui-même.
Pour chaque jeu, dans results/<jeu>/ :
  correlations.png / .csv   ρ de Spearman entre indicateurs (fenêtres, puis médianes de groupe)
  acp.png / composantes.md  éboulis, plan PC1-PC2 (flèches = indicateurs), position des groupes sur PC1, PC2
  cah_groupes.png           CAH (Ward) des groupes sur leurs médianes centrées-réduites
  clusters_{FCM,CAH}_k2-6.png, clusters.json   FCM et CAH Ward, k = 2..6, sur les composantes de Kaiser (valeur
                            propre > 1, au moins 2), modèle nul (nuage gaussien sans cluster)
  algos.png / .json         contrôle du FCM : k-means, GMM, CAH, HDBSCAN, chacun avec son critère de choix de k
et results/resume_indicateurs.json.
Usage : uv run python pca_indicators.py   (après nem_formularity.py)
"""
import json
import os
import textwrap

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.stats import spearmanr

from common import (IND, KS, RESULTS, boxplots, clustering, group_order, kaiser, load_windows, loaders, other_algorithms,
                    palette, pca, plt, zs)

LOG = {"formularity", "formularity_nempool", "kl", "punct"}
CB = ["formularity", "h_rate", "distinct2", "kl", "punct"]
SETS = {"indicateurs-claude-bertrand": CB,
        "indicateurs-claude-bertrand-NEMpool": ["formularity_nempool"] + CB[1:],
        "indicateurs-claude-bertrand-sans-distinct2": [c for c in CB if c != "distinct2"],
        "indicateurs-claude-bertrand-sans-distinct2-NEMpool": ["formularity_nempool"] + [c for c in CB[1:] if c != "distinct2"]}


def add_text_indicators(w):
    """ĥ (text_rigidity.entropy_rate_lz) et ponctuation pour 100 mots (text_rigidity.count_typographic_marks) de chaque
    fenêtre, texte lu dans le pivot."""
    import text_rigidity as tr
    h, punct = {}, {}
    for name, part in w.groupby("dataset", sort=False):
        docs = {d["doc_id"]: d["text"] for d in loaders.load_pivot(name)}
        for i, r in zip(part.index, part.itertuples(index=False)):
            text = docs[r.doc_id][r.start:r.end]
            h[i] = tr.entropy_rate_lz(tr.tokenize_words(text))
            counts, n_words = tr.count_typographic_marks(text)
            punct[i] = 100 * counts["punctuation"] / max(n_words, 1)
    return w.assign(h_rate=pd.Series(h), punct=pd.Series(punct))


def oriented(d, cols):
    X = np.column_stack([np.log1p(d[c]) if c in LOG else d[c] for c in cols]).astype(float)
    return X * np.array([IND[c][1] for c in cols])


def fig_correlations(d, names, Z, out):
    rw = spearmanr(Z).statistic
    med = pd.DataFrame(Z, columns=names).groupby(d["groupe"].values).median()
    rc = spearmanr(med.values).statistic
    if len(names) == 2:
        rw, rc = np.array([[1, rw], [rw, 1]]), np.array([[1, rc], [rc, 1]])
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for a, r, t in ((ax[0], rw, f"ρ de Spearman sur les {len(Z)} fenêtres"), (ax[1], rc, f"ρ sur les médianes des {len(med)} groupes")):
        a.imshow(r, cmap="RdBu_r", vmin=-1, vmax=1)
        a.set_xticks(range(len(names)), names, rotation=30, ha="right"); a.set_yticks(range(len(names)), names)
        for i in range(len(names)):
            for j in range(len(names)):
                a.text(j, i, f"{r[i, j]:.2f}", ha="center", va="center", fontsize=10)
        a.set_title(t + "\n(indicateurs orientés : + = plus rigide)", fontsize=10)
    plt.tight_layout(); plt.savefig(f"{out}/correlations.png", dpi=110); plt.close()
    pd.DataFrame(rw, index=names, columns=names).round(3).to_csv(f"{out}/correlations.csv")


def fig_pca(d, names, var, Vt, P, kai, out):
    g = d["groupe"].values
    order = group_order(g)
    col = palette(order)
    fig, ax = plt.subplots(1, 4, figsize=(30, 8), gridspec_kw={"width_ratios": [0.6, 1.3, 1, 1]})
    ax[0].bar(range(1, len(var) + 1), var); ax[0].plot(range(1, len(var) + 1), np.cumsum(var), "o-", color="k")
    ax[0].axhline(100 / len(names), color="r", ls="--", lw=0.8)
    ax[0].set_title(f"Éboulis ; rouge = Kaiser ({kai} comp.)", fontsize=10)
    for c in order:
        m_ = g == c
        ax[1].scatter(P[m_, 0], P[m_, 1], s=9, color=col[c], marker="^" if c.startswith("NEM.fr") else "o", alpha=0.7, label=c)
    sc = np.abs(P[:, :2]).max() / np.abs(Vt[:2]).max() * 0.7
    for j, n in enumerate(names):
        ax[1].arrow(0, 0, Vt[0, j] * sc, Vt[1, j] * sc, color="k", width=0.01, head_width=0.1)
        ax[1].text(Vt[0, j] * sc * 1.1, Vt[1, j] * sc * 1.1, n, fontsize=9)
    ax[1].set_xlabel(f"PC1 ({var[0]:.1f} %)"); ax[1].set_ylabel(f"PC2 ({var[1]:.1f} %)")
    ax[1].legend(fontsize=6.5, markerscale=2, ncol=2); ax[1].set_title(f"ACP des indicateurs ({os.path.basename(out)})")
    for i in (0, 1):
        o = np.argsort(Vt[i])
        boxplots(ax[i + 2], P, g, order, i, var, f"− {names[o[0]]}   |   + {names[o[-1]]}")
    plt.tight_layout(); plt.savefig(f"{out}/acp.png", dpi=110); plt.close()
    L = [f"# Composantes de l'ACP des indicateurs ({os.path.basename(out)})", "",
         f"{len(P)} fenêtres ({d.dataset.str.startswith('nem-').sum()} de NEM.fr), {len(names)} indicateurs orientés (+ = plus rigide), log(1 + x) pour la "
         f"formularité, la KL et la ponctuation, centrés-réduits. Kaiser : {kai} composante(s), {var[:kai].sum():.1f} % de variance. Signe : somme "
         "des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux "
         "indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.", "",
         "| Composante | Poids des indicateurs | Groupes côté − | Groupes côté + |", "|---|---|---|---|"]
    for i in range(len(names)):
        med = {c: float(np.median(P[g == c, i])) for c in order}
        srt = sorted(order, key=med.get)
        w = ", ".join(f"{names[j]} {Vt[i, j]:+.2f}" for j in np.argsort(-np.abs(Vt[i])))
        L.append(f"| PC{i + 1} ({var[i]:.1f} %) | {w} | " + ", ".join(f"{c} ({med[c]:+.1f})" for c in srt[:3])
                 + " | " + ", ".join(f"{c} ({med[c]:+.1f})" for c in srt[::-1][:3]) + " |")
    open(f"{out}/composantes.md", "w").write("\n".join(L) + "\n")


def fig_cah_groupes(d, Z, names, out):
    med = pd.DataFrame(Z, columns=names).groupby(d["groupe"].values).median()
    L = linkage(zs(med.values), "ward")
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(med) + 2))
    dendrogram(L, labels=list(med.index), orientation="left", ax=ax, leaf_font_size=9)
    ax.set_title(textwrap.fill(f"CAH (Ward) des groupes sur les médianes de {len(names)} indicateurs "
                               f"({', '.join(names)}), centrées-réduites entre groupes", 90), fontsize=10)
    plt.tight_layout(); plt.savefig(f"{out}/cah_groupes.png", dpi=110); plt.close()
    return {k: {c: int(x) for c, x in zip(med.index, fcluster(L, k, "maxclust"))} for k in KS}


def main():
    w = add_text_indicators(load_windows())
    summary = {}
    for tag, cols in SETS.items():
        out = os.path.join(RESULTS, tag)
        os.makedirs(out, exist_ok=True)
        d = w.dropna(subset=cols).reset_index(drop=True)
        names = [IND[c][0] for c in cols]
        Z = zs(oriented(d, cols))
        fig_correlations(d, names, Z, out)
        var, Vt = pca(Z)
        Vt *= np.where(Vt.sum(1) < 0, -1, 1)[:, None]               # somme des poids >= 0 pour chaque composante
        P = Z @ Vt.T
        kai = kaiser(var, len(cols))
        fig_pca(d, names, var, Vt, P, kai, out)
        cah = fig_cah_groupes(d, Z, names, out)
        dims = max(2, kai)
        res, _ = clustering(d["groupe"].values, P[:, :dims], out)
        algos = other_algorithms(d["groupe"].values, P[:, :dims], out)
        summary[tag] = {"n_fenetres": len(d), "variance_pct": [round(float(v), 1) for v in var], "kaiser": kai,
                        "clusters": res, "autres_algorithmes": algos, "CAH_groupes": cah}
        print(tag, json.dumps({k: summary[tag][k] for k in ("n_fenetres", "variance_pct", "kaiser", "autres_algorithmes")},
                              ensure_ascii=False))
        print("  clusters", json.dumps({k: (v["FCM"]["silhouette"], v["FCM"]["nul_moyen"], v["CAH_Ward"]["silhouette"],
                                             v["CAH_Ward"]["nul_moyen"], v["ARI_FCM_vs_CAH"]) for k, v in res.items()}))
    json.dump(summary, open(os.path.join(RESULTS, "resume_indicateurs.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
