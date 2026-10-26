"""Analyse des fenêtres produites par compute_indicators.py : profils par dataset, redondances, fiabilité,
validation de la densité de noms propres. Seuls les tableaux cités dans le rapport sont écrits.

Usage : python analysis.py [results/windows.csv]
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

import loaders

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
RETAINED = ["typo", "balance", "verbless", "formularity", "name_density", "distinct2"]
DIAGNOSTIC = ["kl", "typo_no_punct"]
MIN_REF_TOKENS = 15_000  # en dessous, la formularité n'est pas comparable entre datasets

FAMILIES = {
    "Press": ["hipe2020-fr", "hipe2020-en", "hipe2020-de", "letemps-fr", "newseye-fr", "newseye-fi", "newseye-sv"],
    "Directories": ["soduco-ref", "soduco-pero"],
    "Deeds and registers": ["m-popp-printed", "m-popp-handwritten", "basel", "old-bailey", "e-ner"],
    "Literature": ["7romans", "litbank"],
    "Scholarly texts": ["geoedda", "ajmc-fr", "ajmc-en", "ajmc-de", "copious"],
}
FAMILY_OF = {d: f for f, ds in FAMILIES.items() for d in ds}

# Étiquettes gold comptées comme PER / LOC / ORG pour valider la densité de noms propres
COARSE = {
    "pers": "PER", "PER": "PER", "PERS": "PER", "persName": "PER", "witnessName": "PER", "defendantName": "PER",
    "victimName": "PER", "PERSON": "PER", "Person": "PER", "NP-Person": "PER",
    "loc": "LOC", "LOC": "LOC", "placeName": "LOC", "LOCATION": "LOC", "GeographicalLocation": "LOC",
    "NP-Spatial": "LOC", "GPE": "LOC", "SPAT": "LOC",
    "org": "ORG", "ORG": "ORG", "BUSINESS": "ORG", "GOVERNMENT": "ORG", "COURT": "ORG",
}


def family(name):
    return FAMILY_OF.get(name, "NEM.fr" if name.startswith("nem-") else "Other")


def eta2(df, col, group="dataset"):
    """Part de la variance des rangs expliquée par le groupe (0 = aucune séparation, 1 = séparation parfaite)."""
    s = df[[group, col]].dropna()
    r = rankdata(s[col])
    g0 = r.mean()
    s = s.assign(r=r)
    between = sum(len(g) * (g.r.mean() - g0) ** 2 for _, g in s.groupby(group))
    return between / ((r - g0) ** 2).sum()


def add_gold_named_density(df):
    """Densité gold des seules entités PER/LOC/ORG (entités pour 100 mots), pour valider la densité de noms propres."""
    cache = {}
    vals = []
    for name, doc_id, a, b, n in df[["dataset", "doc_id", "start", "end", "n_words"]].itertuples(index=False):
        if name not in cache:
            cache[name] = {str(d["doc_id"]): d for d in loaders.load_pivot(name)}
        d = cache[name][str(doc_id)]
        k = sum(1 for s, e, lab in d["entities"] if s < b and e > a and lab in COARSE)
        vals.append(100 * k / n)
    df["gold_named_per100"] = vals
    return df


def profiles(df, size):
    sub = df[df["size"] == size].copy()
    sub.loc[sub.ref_tokens < MIN_REF_TOKENS, ["formularity", "formularity_k2", "formularity_k5"]] = np.nan
    cols = RETAINED + DIAGNOSTIC
    med = sub.groupby("dataset")[cols].median()
    q1 = sub.groupby("dataset")[cols].quantile(0.25)
    q3 = sub.groupby("dataset")[cols].quantile(0.75)
    med.insert(0, "family", [family(n) for n in med.index])
    med.insert(1, "windows", sub.groupby("dataset").size())
    med.insert(2, "lang", sub.groupby("dataset")["lang"].first())
    return med, q1, q3, sub


def main(path):
    df = pd.read_csv(path)
    df = add_gold_named_density(df)
    os.makedirs(RESULTS, exist_ok=True)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    out = {}
    for size in (100, 300):
        med, q1, q3, sub = profiles(df, size)
        if size == 100:
            med.to_csv(os.path.join(RESULTS, "profiles_100.csv"))
            (q3 - q1)[RETAINED].to_csv(os.path.join(RESULTS, "iqr_100.csv"))
        out[size] = (med, sub)
        print(f"\n=== Medians by dataset, {size}-word windows")
        print(med.sort_values("balance").round(2).to_string())

    # Fiabilité : séparation des datasets (eta2 sur rangs) et effet de langue (hipe2020 fr/en/de)
    rows = []
    for size in (100, 300):
        sub = out[size][1]
        hipe = sub[sub.dataset.isin(["hipe2020-fr", "hipe2020-en", "hipe2020-de"])]
        news = sub[sub.dataset.isin(["newseye-fr", "newseye-fi", "newseye-sv"])]
        for col in RETAINED + DIAGNOSTIC:
            rows.append({"size": size, "indicator": col, "dataset_separation": eta2(sub, col),
                         "language_effect_hipe2020": eta2(hipe, col), "language_effect_newseye": eta2(news, col)})
    rel = pd.DataFrame(rows).pivot(index="indicator", columns="size")
    rel.to_csv(os.path.join(RESULTS, "reliability.csv"))
    print("\n=== Dataset separation and language effect (eta2 on ranks)")
    print(rel.round(2).to_string())

    # Redondances : corrélations de Spearman entre fenêtres, toutes langues et français seul
    for size in (100, 300):
        sub = out[size][1]
        cols = RETAINED + DIAGNOSTIC
        for label, part in [("all", sub), ("fr", sub[sub.lang == "fr"])]:
            c = part[cols].corr("spearman")
            if (size, label) == (100, "fr"):
                c.to_csv(os.path.join(RESULTS, "correlations_100_fr.csv"))
            print(f"\n=== Spearman between windows, {size} words, languages: {label}")
            print(c.round(2).to_string())
        dm = out[size][0][RETAINED + DIAGNOSTIC]
        print(f"\n=== Spearman between dataset medians, {size} words")
        print(dm.corr("spearman").round(2).to_string())

    # Validation de la densité de noms propres contre la densité gold PER/LOC/ORG
    rows = []
    sub = out[100][1].copy()
    for name, g in sub.groupby("dataset"):
        if g["gold_named_per100"].sum() == 0 or g["name_density"].nunique() < 3:
            continue
        rho = spearmanr(g["name_density"], g["gold_named_per100"]).statistic
        rows.append({"dataset": name, "family": family(name), "rho_within": rho,
                     "name_density": g["name_density"].median(), "gold_density": g["gold_named_per100"].median()})
    val = pd.DataFrame(rows).set_index("dataset")
    val.to_csv(os.path.join(RESULTS, "name_density_validation.csv"))
    print("\n=== Proper-name density vs gold PER/LOC/ORG density (100-word windows)")
    print(val.round(2).sort_values("rho_within").to_string())
    print("median within-dataset rho:", round(val.rho_within.median(), 2),
          "| rho between dataset medians:", round(spearmanr(val.name_density, val.gold_density).statistic, 2))

    # La formularité suit-elle la densité de noms propres à l'intérieur des datasets ? (effet du masquage <NOM>)
    rows = []
    for name, g in out[100][1].dropna(subset=["formularity"]).groupby("dataset"):
        if g["formularity"].nunique() > 3:
            rows.append({"dataset": name, "rho_formularity_names": spearmanr(g["formularity"], g["name_density"]).statistic,
                         "rho_formularity_balance": spearmanr(g["formularity"], g["balance"]).statistic})
    within = pd.DataFrame(rows).set_index("dataset")
    within.to_csv(os.path.join(RESULTS, "formularity_within_dataset.csv"))
    print("\n=== Within-dataset correlations of formularity (100 words)")
    print(within.round(2).to_string())
    print("medians:", within.median().round(2).to_dict())

    # Sensibilité de la formularité au seuil
    med = out[100][0]
    print("\n=== Formularity: rho between thresholds (dataset medians, 100 words)",
          med[["formularity"]].join(out[100][1].groupby("dataset")[["formularity_k2", "formularity_k5"]].median()).corr("spearman").round(2).to_string(), sep="\n")
    return df, out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(RESULTS, "windows.csv"))
