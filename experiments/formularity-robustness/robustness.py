"""Robustesse de la formularité : critère de dispersion, Self-BLEU, taille des n-grammes.

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv` (100 et 300 mots), hors
NEM.fr (référence trop petite, voir le rapport §5). Pour chaque fenêtre, on recalcule :

* la formularité de référence (4-grammes vus au moins 3 fois, réglages de compute_indicators.py), qui doit retrouver
  la valeur de windows.csv ;
* la même avec un **critère de dispersion** : le 4-gramme doit aussi apparaître dans au moins 2 ou 3 documents
  distincts de la référence (lexical bundles de Biber et al.) ;
* la même avec des **3-grammes et des 5-grammes** ;
* le **Self-BLEU** (Zhu et al. 2018) contre la même référence : BLEU de la fenêtre (1- à 4-grammes, effectifs écrêtés
  par extrait de référence, lissage « method1 » de Chen et Cherry, sans pénalité de brièveté), sur le texte brut en
  minuscules et sur la séquence masquée de la formularité (<NAME>, <NUM>) ; et la seule précision des 4-grammes masqués.

Puis on compare ces mesures, et deux mesures de diversité lexicale internes à la fenêtre (MATTR, Covington et McFall
2010, sur 50 mots ; ĥ de Bentz et al. 2017), sur ce qui décide du choix d'un indicateur : séparation des datasets,
effet de la langue à corpus égal (newseye, hipe2020, ajmc), part de fenêtres à 0, recoupement avec les autres
indicateurs de windows.csv (comparaison.md, comparaison.json).

Sorties (results/) : fenetres.csv, resume.json, resume.md, comparaison.json, comparaison.md, dispersion_n.png,
self_bleu.png.
Usage : uv run python robustness.py [--figures]   (--figures : résumé et figures depuis results/fenetres.csv)
"""
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import text_rigidity as tr
from text_rigidity.formularity import formula_tokens

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
VALIDATION = os.path.join(HERE, "..", "rigidity-indicators", "dataset-validation")
sys.path.insert(0, VALIDATION)
sys.path.insert(0, os.path.join(HERE, "..", "clustering-pca"))
import loaders  # noqa: E402
from compute_indicators import WORD_RE  # noqa: E402
from analysis import MIN_REF_TOKENS, eta2  # noqa: E402
from compute_indicators import dataset_lang  # noqa: E402
from pca_indicators import place_labels  # noqa: E402

WINDOWS = os.path.join(VALIDATION, "results", "windows.csv")
FIG_SIZE = 300
# variantes de formularité : nom de colonne -> (n, min_docs, libellé)
VARIANTS = {"F": (4, 1, "4-grammes ≥ 3 fois (réglage actuel)"),
            "F_docs2": (4, 2, "+ dans ≥ 2 documents"),
            "F_docs3": (4, 3, "+ dans ≥ 3 documents"),
            "F_n3": (3, 1, "3-grammes ≥ 3 fois"),
            "F_n5": (5, 1, "5-grammes ≥ 3 fois")}
BLEU = {"sbleu_raw": "Self-BLEU, texte brut", "sbleu_masked": "Self-BLEU, noms et nombres masqués",
        "p4_masked": "précision des 4-grammes masqués"}
DIVERSITY = {"mattr": "MATTR (50 mots)", "h_rate": "ĥ (Bentz)", "distinct2": "Distinct-2"}
MULTILINGUAL = ["newseye", "hipe2020", "ajmc"]  # même corpus en plusieurs langues : l'effet de langue devrait être nul
OTHERS = ["name_density", "typo", "balance"]


def ngrams(tokens, n):
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def raw_tokens(doc):
    return [t.text.lower() for t in doc if not t.is_space]


class BleuIndex:
    """Effectifs des 1- à 4-grammes par extrait de référence, pour écrêter ceux d'une fenêtre au maximum
    observé dans un extrait de la référence (BLEU à références multiples)."""

    def __init__(self, token_lists):
        self.index = {n: defaultdict(list) for n in range(1, 5)}
        for i, toks in enumerate(token_lists):
            for n in range(1, 5):
                for g, c in Counter(ngrams(toks, n)).items():
                    self.index[n][g].append((i, c))

    def precisions(self, toks, subset):
        out = []
        for n in range(1, 5):
            c = Counter(ngrams(toks, n))
            num = sum(min(k, max((m for i, m in self.index[n].get(g, ()) if i in subset), default=0))
                      for g, k in c.items())
            out.append((num, sum(c.values())))
        return out


def bleu(prec):
    """Moyenne géométrique des précisions (×100), lissage method1 : 0,1 au lieu d'un numérateur nul."""
    return 100 * math.exp(np.mean([math.log((num or 0.1) / den) for num, den in prec]))


def dataset_rows(name, win):
    docs = loaders.load_pivot(name)
    lang = dataset_lang(name, docs)
    pairs = [(d["doc_id"], d["text"]) for d in docs]
    by_id = {str(d["doc_id"]): d for d in docs}
    refs = {n: tr.FormularityReference(pairs, lang=lang, n=n, seed=0) for n in (3, 4, 5)}
    nlp = tr.get_nlp(lang)
    chunks = tr.sample_reference_chunks(pairs, seed=0)
    parsed = list(nlp.pipe([c for _, c in chunks], batch_size=64))
    assert len(parsed) == len(refs[4].chunks)
    raw_idx, masked_idx = BleuIndex([raw_tokens(p) for p in parsed]), BleuIndex([formula_tokens(p) for p in parsed])
    rows = []
    texts = [by_id[r.doc_id]["text"][r.start:r.end] for r in win.itertuples()]
    for r, text, doc in zip(win.itertuples(), texts, nlp.pipe(texts, batch_size=32)):
        doc_id = by_id[r.doc_id]["doc_id"]
        row = {"dataset": name, "size": r.size, "doc_id": r.doc_id, "start": r.start, "F_windows_csv": r.formularity}
        for col, (n, k, _) in VARIANTS.items():
            f = tr.compute_formularity(text, refs[n], doc_id, lang, doc, min_docs=k)
            row[col] = f["formularity"]
        subset = set(refs[4].chunks_for(doc_id))
        row["ref_tokens"] = f["ref_tokens"]
        row["ref_docs"] = len({refs[4].chunks[i][0] for i in subset})
        pm = masked_idx.precisions(formula_tokens(doc), subset)
        row["sbleu_raw"] = bleu(raw_idx.precisions(raw_tokens(doc), subset))
        row["sbleu_masked"] = bleu(pm)
        row["p4_masked"] = 100 * pm[3][0] / pm[3][1]
        rows.append(row)
    return rows


def compute():
    w = pd.read_csv(WINDOWS, dtype={"doc_id": str})
    w = w[~w.dataset.str.startswith("nem-")]
    rows = []
    for name, win in w.groupby("dataset", sort=False):
        t0 = time.time()
        rows += dataset_rows(name, win)
        print(f"{name:20s} {time.time() - t0:6.1f} s", flush=True)
    return pd.DataFrame(rows)


def summarize(df):
    """η² (séparation des datasets), ρ de Spearman avec la formularité actuelle (fenêtres et médianes des datasets),
    ρ médian à l'intérieur des datasets ; médianes et part de fenêtres à 0 par dataset."""
    out = {}
    for size, d in df.groupby("size"):
        med = d.groupby("dataset")[list(VARIANTS) + list(BLEU)].median()
        within = {}
        for c in list(VARIANTS)[1:] + list(BLEU):
            rho = [spearmanr(g.F, g[c]).statistic for _, g in d.groupby("dataset") if g.F.nunique() > 3 and g[c].nunique() > 3]
            within[c] = round(float(np.nanmedian(rho)), 2)
        out[int(size)] = {
            "fenetres": len(d),
            "eta2": {c: round(float(eta2(d, c)), 2) for c in list(VARIANTS) + list(BLEU)},
            "rho_fenetres": {c: round(float(spearmanr(d.F, d[c]).statistic), 2) for c in list(VARIANTS)[1:] + list(BLEU)},
            "rho_medianes": {c: round(float(spearmanr(med.F, med[c]).statistic), 2) for c in list(VARIANTS)[1:] + list(BLEU)},
            "rho_interne_median": within,
            "medianes": med.round(1).to_dict(orient="index"),
            "part_nulle": d.groupby("dataset")[list(VARIANTS)].agg(lambda s: round(100 * float((s == 0).mean()), 1)).to_dict(orient="index"),
            "couverture_conservee_docs3": (100 * d.groupby("dataset").F_docs3.sum() / d.groupby("dataset").F.sum()).round(0).fillna(-1).to_dict(),
            "ref_docs_median": d.groupby("dataset").ref_docs.median().to_dict(),
        }
    return out


def mattr(tokens, span=50):
    """Moving-Average Type-Token Ratio (Covington et McFall 2010) : TTR moyen des fenêtres glissantes de span mots."""
    if len(tokens) < span:
        return float("nan")
    return float(np.mean([len(set(tokens[i : i + span])) / span for i in range(len(tokens) - span + 1)]))


def compare_measures(df):
    """Formularité, Self-BLEU et diversité lexicale interne (MATTR, ĥ, Distinct-2) sur les critères de choix d'un
    indicateur ; les autres indicateurs viennent de windows.csv."""
    w = pd.read_csv(WINDOWS, dtype={"doc_id": str})
    d = df.merge(w[["dataset", "size", "doc_id", "start", "end", "lang", "distinct2"] + OTHERS],
                 on=["dataset", "size", "doc_id", "start"])
    texts = {}
    for name in d.dataset.unique():
        texts.update({(name, str(x["doc_id"])): x["text"] for x in loaders.load_pivot(name)})
    win = [texts[(r.dataset, r.doc_id)][r.start:r.end] for r in d.itertuples()]
    d["mattr"] = [mattr([t.lower() for t in WORD_RE.findall(x)]) for x in win]
    d["h_rate"] = [tr.entropy_rate_lz(tr.tokenize_words(x)) for x in win]
    cols = ["F"] + list(BLEU) + list(DIVERSITY)
    out = {}
    for size, x in d.groupby("size"):
        corr = x[cols + OTHERS].corr("spearman")
        out[int(size)] = {
            "eta2_dataset": {c: round(float(eta2(x, c)), 2) for c in cols},
            "eta2_langue": {c: {m: round(float(eta2(x[x.dataset.str.startswith(m)], c, "lang")), 2) for m in MULTILINGUAL}
                            for c in cols},
            "part_nulle": {c: round(100 * float((x[c] == 0).mean()), 1) for c in cols},
            "rho": {c: {o: round(float(corr.loc[c, o]), 2) for o in ["F"] + OTHERS} for c in cols},
        }
    return out


def write_comparison_md(cmp, path):
    labels = {"F": "formularité", **BLEU, **DIVERSITY}
    lines = ["# Formularité, Self-BLEU et diversité lexicale", "",
             "Généré par `robustness.py`. η² dataset : séparation des datasets. η² langue : part de la variance due à la "
             "langue dans un même corpus multilingue (devrait être nulle). ρ : Spearman entre fenêtres.", ""]
    for size, c in cmp.items():
        lines += [f"## Fenêtres de {size} mots", "",
                  "| mesure | η² dataset | η² langue " + " / ".join(MULTILINGUAL) + " | fenêtres à 0 (%) | ρ formularité | "
                  + " | ".join(f"ρ {o}" for o in OTHERS) + " |", "|---" * (5 + len(OTHERS)) + "|"]
        for m in c["eta2_dataset"]:
            lines.append(f"| {labels[m]} (`{m}`) | {c['eta2_dataset'][m]} | "
                         + " / ".join(str(c["eta2_langue"][m][k]) for k in MULTILINGUAL)
                         + f" | {c['part_nulle'][m]} | " + " | ".join(str(c["rho"][m][o]) for o in ["F"] + OTHERS) + " |")
        lines.append("")
    open(path, "w").write("\n".join(lines))


def order_by_f(d):
    return d.groupby("dataset").F.median().sort_values(kind="stable").index.tolist()


def fig_dispersion_n(d, out):
    """Médiane de chaque variante par dataset (300 mots) : critère de dispersion à gauche, taille des n-grammes à droite."""
    order = order_by_f(d)
    med = d.groupby("dataset")[list(VARIANTS)].median().loc[order]
    y = np.arange(len(order))
    fig, axes = plt.subplots(1, 2, figsize=(14, 0.36 * len(order) + 2.2), sharey=True)
    panels = [("A. Critère de dispersion", ["F", "F_docs2", "F_docs3"]), ("B. Taille des n-grammes", ["F_n3", "F", "F_n5"])]
    styles = {"F": ("#1f1e1c", "o", 7), "F_docs2": ("#2a78d6", "s", 6), "F_docs3": ("#eb6834", "D", 6),
              "F_n3": ("#2a78d6", "s", 6), "F_n5": ("#eb6834", "D", 6)}
    for ax, (title, cols) in zip(axes, panels):
        lo, hi = med[cols].min(axis=1), med[cols].max(axis=1)
        ax.hlines(y, lo, hi, color="#c3c2b7", lw=2, zorder=1)
        for c in cols:
            col, mk, s = styles[c]
            ax.plot(med[c], y, mk, color=col, ms=s, mec="white", mew=0.8, label=VARIANTS[c][2], zorder=3)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("formularité médiane des fenêtres (% du texte pris dans des gabarits)")
        ax.grid(axis="x", color="#e8e7e3", lw=0.8); ax.set_axisbelow(True)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.legend(loc="lower right", fontsize=9, frameon=False)
    axes[0].set_yticks(y, order)
    fig.suptitle(f"La formularité change-t-elle si l'on exige des formules partagées, ou d'autres n-grammes ?\n"
                 f"{len(d)} fenêtres de {FIG_SIZE} mots ; trait gris : écart entre les variantes d'un même dataset ; "
                 f"symboles superposés : variantes égales",
                 fontsize=12, x=0.01, ha="left")
    plt.tight_layout(); plt.savefig(out, dpi=110, bbox_inches="tight"); plt.close()


def fig_self_bleu(d, s, out):
    """Formularité contre Self-BLEU (masqué, puis brut) : fenêtres en gris, médiane de chaque dataset en noir."""
    order = order_by_f(d)
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))
    for ax, c, letter in zip(axes, ["sbleu_masked", "sbleu_raw"], "AB"):
        x, yv = np.log1p(d.F), d[c]
        ax.scatter(x, yv, s=5, color="#b5b4ad", alpha=0.45, lw=0, label=f"fenêtre de {FIG_SIZE} mots")
        med = d.groupby("dataset")[["F", c]].median().loc[order]
        ax.scatter(np.log1p(med.F), med[c], s=28, color="#1f1e1c", zorder=4, label="médiane d'un dataset")
        ticks = [0, 1, 3, 10, 30, 100]
        ax.set_xticks(np.log1p(ticks), [str(t) for t in ticks])
        ax.set_xlabel("formularité (%, échelle log(1 + x))")
        ax.set_ylabel(f"{BLEU[c]} (0–100)")
        ax.set_title(f"{letter}. {BLEU[c]}\nρ de Spearman : {s['rho_fenetres'][c]:.2f} entre fenêtres, "
                     f"{s['rho_medianes'][c]:.2f} entre médianes, {s['rho_interne_median'][c]:.2f} en médiane à l'intérieur d'un dataset",
                     loc="left", fontsize=11)
        ax.grid(color="#e8e7e3", lw=0.8); ax.set_axisbelow(True)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.legend(loc="upper left", fontsize=9, frameon=False)
        place_labels(ax, np.column_stack([np.log1p(med.F), med[c]]), order, [{"fontsize": 8.5}] * len(order))
    fig.suptitle("Notre formularité mesure-t-elle la même chose que le Self-BLEU ?\n"
                 "Self-BLEU : part des 1- à 4-grammes de la fenêtre retrouvés dans les autres documents du dataset "
                 "(même référence que la formularité)", fontsize=12, x=0.01, ha="left")
    plt.tight_layout(); plt.savefig(out, dpi=110, bbox_inches="tight"); plt.close()


def write_md(summary, path):
    lines = ["# Robustesse de la formularité", "",
             "Généré par `robustness.py`. η² : part de la variance des rangs expliquée par le dataset (séparation). "
             "ρ : corrélation de Spearman avec la formularité actuelle (`F`).", ""]
    labels = {**{c: v[2] for c, v in VARIANTS.items()}, **BLEU}
    for size, s in summary.items():
        lines += [f"## Fenêtres de {size} mots ({s['fenetres']})", "",
                  "| variante | η² | ρ fenêtres | ρ médianes des datasets | ρ médian dans un dataset |", "|---|---|---|---|---|"]
        for c in list(VARIANTS) + list(BLEU):
            r = [s[k].get(c, "—") for k in ("rho_fenetres", "rho_medianes", "rho_interne_median")]
            lines.append(f"| {labels[c]} (`{c}`) | {s['eta2'][c]} | " + " | ".join(str(v) for v in r) + " |")
        lines += ["", "| dataset | docs dans la référence (médiane) | " + " | ".join(f"`{c}`" for c in VARIANTS)
                  + " | couverture conservée à ≥ 3 docs (%) | " + " | ".join(f"`{c}`" for c in BLEU) + " |",
                  "|---" * (3 + len(VARIANTS) + len(BLEU)) + "|"]
        for name, m in sorted(s["medianes"].items(), key=lambda kv: -kv[1]["F"]):
            cov = s["couverture_conservee_docs3"][name]
            lines.append(f"| {name} | {s['ref_docs_median'][name]:.0f} | " + " | ".join(f"{m[c]:.1f}" for c in VARIANTS)
                         + f" | {'—' if cov < 0 else f'{cov:.0f}'} | " + " | ".join(f"{m[c]:.1f}" for c in BLEU) + " |")
        lines.append("")
    open(path, "w").write("\n".join(lines))


def main(figures_only=False):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "fenetres.csv")
    if figures_only:
        df = pd.read_csv(path, dtype={"doc_id": str})
    else:
        df = compute()
        df.to_csv(path, index=False)
    diff = (df.F - df.F_windows_csv).abs().max()
    print(f"écart maximal avec windows.csv : {diff:.2e}")
    df = df[df.ref_tokens >= MIN_REF_TOKENS]
    summary = summarize(df)
    json.dump(summary, open(os.path.join(RESULTS, "resume.json"), "w"), ensure_ascii=False, indent=1)
    write_md(summary, os.path.join(RESULTS, "resume.md"))
    cmp = compare_measures(df)
    json.dump(cmp, open(os.path.join(RESULTS, "comparaison.json"), "w"), ensure_ascii=False, indent=1)
    write_comparison_md(cmp, os.path.join(RESULTS, "comparaison.md"))
    d = df[df["size"] == FIG_SIZE]
    fig_dispersion_n(d, os.path.join(RESULTS, "dispersion_n.png"))
    fig_self_bleu(d, summary[FIG_SIZE], os.path.join(RESULTS, "self_bleu.png"))


if __name__ == "__main__":
    main("--figures" in sys.argv[1:])
