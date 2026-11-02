"""Figure des deux axes de rigidité : balance phrastique (liste ↔ phrase) et Self-BLEU (formules), par dataset.

Usage : python figure.py  (lit results/profiles_100.csv, écrit ../figures/rigidity_axes.png)
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "figures", "rigidity_axes.png")

# Couleurs catégorielles dans l'ordre fixe de la palette validée ; une forme par famille en plus de la couleur
FAMILY_STYLE = {
    "Press": ("#2a78d6", "o"),
    "Directories": ("#eb6834", "s"),
    "Deeds and registers": ("#1baf7a", "D"),
    "Literature": ("#eda100", "^"),
    "Scholarly texts": ("#e87ba4", "v"),
}
TEXT, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#e4e3df", "#c3c2b7"
# Décalages des étiquettes (points) pour éviter les chevauchements
OFFSETS = {
    "soduco-pero": (6, -11), "soduco-ref": (6, 4), "m-popp-handwritten": (6, -10), "m-popp-printed": (6, 4),
    "basel": (6, 2), "old-bailey": (-8, 6), "geoedda": (6, 4), "e-ner": (6, -3), "copious": (6, 3),
    "ajmc-de": (-6, -10), "ajmc-fr": (6, -4), "ajmc-en": (-6, 3), "hipe2020-en": (6, 4), "7romans": (6, 4), "litbank": (6, -8),
}
RIGHT_ALIGNED = {"old-bailey", "ajmc-en", "ajmc-de"}
# Points confondus près de zéro : une étiquette commune sous l'axe, reliée par un trait (coordonnées des données)
GROUPS = {
    "newseye-fr, -fi, -sv": (["newseye-fr", "newseye-fi", "newseye-sv"], (-0.72, -6)),
    "letemps-fr, hipe2020-de": (["letemps-fr", "hipe2020-de"], (-0.22, -10)),
    "hipe2020-fr": (["hipe2020-fr"], (0.12, -5)),
}


def main():
    med = pd.read_csv(os.path.join(HERE, "results", "profiles_100.csv"), index_col=0)
    med = med.dropna(subset=["self_bleu"])
    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    for fam, (color, marker) in FAMILY_STYLE.items():
        g = med[med.family == fam]
        ax.scatter(g.balance, g.self_bleu, s=64, color=color, marker=marker, edgecolor="white", linewidth=1.5,
                   label=fam, zorder=3)
    grouped = {n for members, _ in GROUPS.values() for n in members}
    for label, (members, (dx, dy)) in GROUPS.items():
        g = med.loc[[m for m in members if m in med.index]]
        ax.annotate(label, (g.balance.mean(), g.self_bleu.mean()), xytext=(dx, dy), textcoords="data",
                    fontsize=8, color=TEXT, ha="center", zorder=4,
                    arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.8, shrinkA=0, shrinkB=4))
    for name, row in med.iterrows():
        if name in grouped:
            continue
        dx, dy = OFFSETS.get(name, (6, 4))
        ax.annotate(name, (row.balance, row.self_bleu), xytext=(dx, dy), textcoords="offset points",
                    fontsize=8, color=TEXT, ha="right" if name in RIGHT_ALIGNED else "left", zorder=4)
    ax.axvline(0, color=AXIS, linewidth=0.8, zorder=1)
    ax.set_ylim(-14, 80)
    ax.set_xlabel("Phrastic balance (median, 100-word windows)\n← more list-like than reference prose      more sentence-like →",
                  color=MUTED, fontsize=9)
    ax.set_ylabel("Self-BLEU against the rest of the dataset (median, 0–100)", color=MUTED, fontsize=9)
    ax.set_title("Two rigidity axes: list ↔ sentence and formulaicity", color=TEXT, fontsize=11, loc="left")
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT, loc="upper right")
    plt.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    plt.savefig(OUT, facecolor="#fcfcfb")
    print(OUT)


if __name__ == "__main__":
    main()
