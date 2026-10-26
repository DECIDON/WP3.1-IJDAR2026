"""ACP et classifications sur des jeux d'indicateurs de rigidité (fenêtres de SIZE = 100 mots de windows.csv).

Indicateurs, tous orientés « + = plus rigide » puis centrés-réduits :
  formularité (windows.csv ; log(1 + x)) : part de la fenêtre prise dans des 4-grammes qui reviennent ailleurs dans son
      sous-corpus ;
  ĥ (taux d'entropie des mots, Bentz et al. 2017 : text_rigidity.entropy_rate_lz) : calculé ici sur le texte de la
      fenêtre (absent de windows.csv) ; bas = texte prévisible ;
  Distinct-2 (windows.csv) : part de bigrammes distincts ; bas = texte répétitif ;
  KL des POS (windows.csv ; log) : écart de la distribution des POS à une référence UD de la langue ;
  ponctuation (log(1 + x)) : signes de la famille « punctuation » du package (. , ; : ! ? …) pour 100 mots, comptés
      par text_rigidity.count_typographic_marks (balisage Markdown retiré, une suite de signes = une marque). C'est la
      part ponctuation du formatage typographique, sans parenthèses, tirets, filets ni symboles ;
  balance phrastique (windows.csv) : log-ratio mots de liaison / autres mots, moins celui de la référence PUD de la
      langue ; bas = peu de mots de liaison, style liste.
Formularité, ĥ, Distinct-2 et KL ne sont pas retenus par le rapport indicateurs-rigidite.md (sauf la formularité) :
ĥ doublonne Distinct-2 (ρ ≈ 0,8 à 100 mots, 0,9 à 300) ; la KL dépend d'une référence par langue et ne se compare qu'à langue
égale. Six jeux :
  indicateurs-claude-bertrand                    = formularité, ĥ, Distinct-2, KL, ponctuation ; genres de NEM.fr exclus
      (formularité non comparable sous 15 000 tokens de référence, règle de analysis.py) ;
  indicateurs-claude-bertrand-sans-distinct2     = idem sans Distinct-2 ;
  ...-NEMpool (pour chacun des deux)             = genres de NEM.fr compris, leur formularité étant calculée contre une
      référence commune à tout NEM.fr (nem_formularity.py), donc mesurée par rapport à NEM.fr et non au genre lui-même ;
  indicateurs-formularite-ponctuation-balance    = formularité, ponctuation, balance phrastique : sans ĥ ni KL, qui
      dépendent de la langue ; genres de NEM.fr exclus ;
  indicateurs-selfbleu-ponctuation-balance       = idem avec le Self-BLEU (text_rigidity.compute_self_bleu ;
      log(1 + x)) à la place de la formularité : le jeu principal, le Self-BLEU étant l'indicateur de formulaicité retenu.
Pour chaque jeu, dans results/<jeu>/ :
  correlations.png / .csv   ρ de Spearman entre indicateurs (fenêtres, puis médianes de groupe)
  acp.png / composantes.md  variance par composante, poids et lecture de chaque composante, plan PC1-PC2 (médianes
                            des groupes, flèches = indicateurs), position des groupes sur PC1 et PC2
  cah_groupes.png           CAH (Ward) des groupes sur leurs médianes centrées-réduites
  clusters_{FCM,CAH}_k2-6.png, clusters.json   FCM et CAH Ward, k = 2..6, sur les composantes de Kaiser (valeur
                            propre > 1, au moins 2), modèle nul (nuage gaussien sans cluster)
  algos.png / .json         contrôle du FCM : k-means, GMM, CAH, HDBSCAN, chacun avec son critère de choix de k
et results/resume_indicateurs.json.
Usage : uv run python pca_indicators.py [jeu ...]   (après nem_formularity.py ; sans argument, tous les jeux)
"""
import json
import os
import sys
import textwrap

import matplotlib
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.stats import spearmanr

from common import (IND, KS, POLES, RESULTS, SIZE, boxplots, clustering, group_order, kaiser, load_windows, loaders,
                    other_algorithms, pca, plt, pole_labels, zs)

LOG = {"formularity", "formularity_nempool", "self_bleu", "kl", "punct"}
CB = ["formularity", "h_rate", "distinct2", "kl", "punct"]
SETS = {"indicateurs-claude-bertrand": CB,
        "indicateurs-claude-bertrand-NEMpool": ["formularity_nempool"] + CB[1:],
        "indicateurs-claude-bertrand-sans-distinct2": [c for c in CB if c != "distinct2"],
        "indicateurs-claude-bertrand-sans-distinct2-NEMpool": ["formularity_nempool"] + [c for c in CB[1:] if c != "distinct2"],
        "indicateurs-formularite-ponctuation-balance": ["formularity", "punct", "balance"],
        "indicateurs-selfbleu-ponctuation-balance": ["self_bleu", "punct", "balance"]}


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


def poles(v, cols, thr=0.3):
    """Les deux pôles d'une composante en mots : (côté −, côté +), d'après les indicateurs de poids |v| ≥ thr.
    Le côté + réunit le sens rigide des indicateurs de poids positif et le sens souple de ceux de poids négatif."""
    keep = [j for j in np.argsort(-np.abs(v)) if abs(v[j]) >= thr]
    plus = [POLES[cols[j]][0 if v[j] > 0 else 1] for j in keep]
    minus = [POLES[cols[j]][1 if v[j] > 0 else 0] for j in keep]
    if (v > 0).all():                              # axe commun à tous les indicateurs
        return "moins rigide : " + ", ".join(minus), "plus rigide : " + ", ".join(plus)
    return ", ".join(minus), ", ".join(plus)


def place_labels(ax, xy, texts, styles):
    """Étiquettes au plus près de leur point sans se recouvrir ni recouvrir un point (placement glouton en pixels :
    pour chaque étiquette, la première position libre sur des cercles de rayon croissant) ; styles : un dict
    d'arguments de ax.text par étiquette. Trait de rappel quand l'étiquette est loin de son point."""
    fig = ax.figure
    fig.canvas.draw()
    to_px, to_data = ax.transData.transform, ax.transData.inverted().transform
    anchors = to_px(xy)
    frame = ax.get_window_extent()
    objs = [ax.text(0, 0, t, va="bottom", ha="left", zorder=5,
                    bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.8}, **st)
            for t, st in zip(texts, styles)]
    r = fig.canvas.get_renderer()
    size = np.array([[o.get_window_extent(r).width, o.get_window_extent(r).height] for o in objs])
    taken = [(a[0] - 5, a[1] - 5, a[0] + 5, a[1] + 5) for a in anchors]      # boîtes occupées : points, puis étiquettes
    angles = np.deg2rad([45, 0, 90, 315, 135, 270, 180, 225, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5])

    def free(b):
        inside = frame.x0 <= b[0] and b[2] <= frame.x1 and frame.y0 <= b[1] and b[3] <= frame.y1
        return inside and all(b[2] + 3 < t[0] or t[2] + 3 < b[0] or b[3] + 2 < t[1] or t[3] + 2 < b[1] for t in taken)

    for o, a, (w, h) in zip(objs, anchors, size):
        box = None
        for rad in np.arange(6, 400, 8):
            for th in angles:
                cx, cy = a[0] + rad * np.cos(th), a[1] + rad * np.sin(th)
                x0, y0 = cx - w * (1 - np.cos(th)) / 2, cy - h * (1 - np.sin(th)) / 2   # côté tourné vers le point
                if free((x0, y0, x0 + w, y0 + h)):
                    box = (x0, y0, x0 + w, y0 + h)
                    break
            if box:
                break
        box = box or (a[0] + 6, a[1] + 6, a[0] + 6 + w, a[1] + 6 + h)
        taken.append(box)
        o.set_position(to_data((box[0], box[1])))
        centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        if np.hypot(centre[0] - a[0], centre[1] - a[1]) > max(w, h) / 2 + 14:
            ax.annotate("", xy=to_data(a), xytext=to_data(centre),
                        arrowprops={"arrowstyle": "-", "color": "#8a8983", "lw": 0.6, "shrinkA": 0, "shrinkB": 0})


def fig_pca(d, cols, names, var, Vt, P, kai, out):
    """acp.png : (A) variance par composante, (B) poids des indicateurs et lecture de chaque composante,
    (C) plan PC1-PC2 avec la médiane de chaque groupe, (D, E) position des groupes sur PC1 et PC2."""
    g = d["groupe"].values
    order = group_order(g)
    p = len(names)
    pol = [poles(Vt[i], cols) for i in range(p)]
    fig = plt.figure(figsize=(26, 19))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 2.3], width_ratios=[1.5, 1, 1], hspace=0.25, wspace=0.5, top=0.95)

    # (A) variance expliquée
    a = fig.add_subplot(gs[0, 0])
    x = np.arange(1, p + 1)
    bars = a.bar(x, var, color="#2a78d6", width=0.6)
    a.bar_label(bars, labels=[f"{v:.1f} %" for v in var], fontsize=10)
    a.plot(x, np.cumsum(var), "o-", color="#52514e", lw=1.5, label="cumul")
    a.axhline(100 / p, color="#e34948", ls="--", lw=1,
              label=f"seuil de Kaiser : {100 / p:.0f} % (ce que vaut un indicateur seul)")
    a.set_xticks(x, [f"PC{i}" for i in x]); a.set_ylabel("% de la variance totale"); a.set_ylim(0, 108)
    a.legend(fontsize=9, loc="center right", frameon=False)
    a.set_title(f"A. Part de la variance portée par chaque composante\n{kai} composante(s) au-dessus du seuil de "
                f"Kaiser ; les classifications utilisent PC1 à PC{max(2, kai)} ({var[:max(2, kai)].sum():.1f} %)", fontsize=11)

    # (B) poids des indicateurs, et lecture de chaque composante en mots
    b = fig.add_subplot(gs[0, 1:])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("div", ["#eb6834", "#f2f1ee", "#2a78d6"])
    b.imshow(Vt, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    for i in range(p):
        for j in range(p):
            b.text(j, i, f"{Vt[i, j]:+.2f}", ha="center", va="center", fontsize=11,
                   fontweight="bold" if abs(Vt[i, j]) >= 0.3 else "normal", color="#0b0b0b")
    b.set_xticks(range(p), [f"{n}\n(+ = {POLES[c][0]})" for n, c in zip(names, cols)], fontsize=9)
    b.set_yticks(range(p), [f"PC{i + 1} ({var[i]:.1f} %)" for i in range(p)], fontsize=10)
    for i in range(p):
        common_axis = (Vt[i] > 0).all() or (Vt[i] < 0).all()
        txt = ("axe commun : + = plus rigide sur tous les indicateurs" if common_axis
               else f"− {pol[i][0]}\n+ {pol[i][1]}")
        b.text(p - 0.4, i, txt, va="center", ha="left", fontsize=9.5, color="#0b0b0b")
    b.set_title("B. Poids des indicateurs dans chaque composante (bleu : l'indicateur pousse la composante vers +, "
                "orange : vers −)\nÀ droite, la lecture de la composante : ce qui caractérise ses deux côtés "
                "(indicateurs de poids |w| ≥ 0,3, en gras)", fontsize=11, loc="left")

    # (C) plan PC1-PC2 : fenêtres en gris, médiane et quartiles de chaque groupe, directions des indicateurs
    c = fig.add_subplot(gs[1, 0])
    c.scatter(P[:, 0], P[:, 1], s=6, color="#b5b4ae", alpha=0.35, lw=0, label=f"une fenêtre de {SIZE} mots")
    med = np.array([np.median(P[g == grp, :2], axis=0) for grp in order])
    for grp, m in zip(order, med):
        q = np.percentile(P[g == grp, :2], [25, 75], axis=0)
        c.plot(q[:, 0], [m[1]] * 2, color="#0b0b0b", lw=0.8, alpha=0.6)
        c.plot([m[0]] * 2, q[:, 1], color="#0b0b0b", lw=0.8, alpha=0.6)
    c.scatter(med[:, 0], med[:, 1], s=40, color="#0b0b0b", zorder=4, label="médiane d'un groupe (barres : 50 % central)")
    sc = np.abs(P[:, :2]).max() / np.abs(Vt[:2]).max() * 0.6
    for j in range(p):
        c.annotate("", xy=(Vt[0, j] * sc, Vt[1, j] * sc), xytext=(0, 0),
                   arrowprops={"arrowstyle": "-|>", "color": "#2a78d6", "lw": 2})
    c.plot([], [], color="#2a78d6", lw=2, label="direction où l'indicateur augmente (sens rigide)")
    c.axhline(0, color="grey", lw=0.5, ls=":"); c.axvline(0, color="grey", lw=0.5, ls=":")
    c.set_xlabel(f"PC1 ({var[0]:.1f} % de la variance)", fontsize=10)
    c.set_ylabel(f"PC2 ({var[1]:.1f} % de la variance)", fontsize=10)
    pole_labels(c, pol[0], "x"); pole_labels(c, pol[1], "y")
    c.legend(fontsize=9, loc="lower left", framealpha=0.9)
    c.set_title(f"C. Plan PC1-PC2 : {len(P)} fenêtres, {len(order)} groupes ({os.path.basename(out)})", fontsize=11)
    tips = Vt[:2].T * sc
    place_labels(c, np.vstack([med, tips]), order + [f"{n}\n({POLES[col][0]})" for n, col in zip(names, cols)],
                 [{"fontsize": 9, "color": "#0b0b0b"}] * len(order)
                 + [{"fontsize": 10, "color": "#1c5cab", "fontweight": "bold"}] * p)

    # (D, E) position des groupes sur PC1 et PC2
    for i in (0, 1):
        boxplots(fig.add_subplot(gs[1, i + 1]), P, g, order, i, var, pol[i])
        fig.axes[-1].set_title("DE"[i] + ". " + fig.axes[-1].get_title(), fontsize=10)
    fig.suptitle(f"ACP de {p} indicateurs orientés « + = plus rigide » : " + ", ".join(names), fontsize=14, y=0.995)
    plt.savefig(f"{out}/acp.png", dpi=100, bbox_inches="tight"); plt.close()
    L = [f"# Composantes de l'ACP des indicateurs ({os.path.basename(out)})", "",
         f"{len(P)} fenêtres ({d.dataset.str.startswith('nem-').sum()} de NEM.fr), {len(names)} indicateurs orientés (+ = plus rigide), log(1 + x) pour : "
         f"{', '.join(n for n, c in zip(names, cols) if c in LOG)} ; centrés-réduits. Kaiser : {kai} composante(s), {var[:kai].sum():.1f} % de variance. Signe : somme "
         "des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux "
         "indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.", "",
         "| Composante | Poids des indicateurs | Lecture (côté − / côté +) | Groupes côté − | Groupes côté + |",
         "|---|---|---|---|---|"]
    for i in range(len(names)):
        med = {c: float(np.median(P[g == c, i])) for c in order}
        srt = sorted(order, key=med.get)
        w = ", ".join(f"{names[j]} {Vt[i, j]:+.2f}" for j in np.argsort(-np.abs(Vt[i])))
        L.append(f"| PC{i + 1} ({var[i]:.1f} %) | {w} | − {pol[i][0]} / + {pol[i][1]} | "
                 + ", ".join(f"{c} ({med[c]:+.1f})" for c in srt[:3])
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


def main(tags):
    w = add_text_indicators(load_windows())
    path = os.path.join(RESULTS, "resume_indicateurs.json")
    summary = json.load(open(path)) if os.path.exists(path) else {}
    for tag in tags:
        cols = SETS[tag]
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
        fig_pca(d, cols, names, var, Vt, P, kai, out)
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
    json.dump(summary, open(path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:] or list(SETS))
