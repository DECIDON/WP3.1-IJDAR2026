# Expériences : indicateurs de rigidité textuelle

Mise au point et validation des indicateurs du package [`text_rigidity`](../../text-rigidity/README.md).
Le rapport [`indicateurs-rigidite.md`](indicateurs-rigidite.md) en donne les définitions, la
justification, les résultats et les indicateurs écartés.

| élément | contenu |
|---|---|
| [`exploring_textual_rigidity.ipynb`](exploring_textual_rigidity.ipynb) | notebook exploratoire : indicateurs sur quatre documents types (Proust → almanach), validation de ΔH à l'échelle corpus |
| [`dataset-validation/`](dataset-validation/README.md) | calcul des indicateurs sur les datasets du projet (`data/` à la racine), analyse et figure du rapport ; résultats dans `dataset-validation/results/` |
| `figures/` | figures du rapport (produites par `dataset-validation/figure.py`) |
| `models/` | modèles CCNet pour la perplexité KenLM (non versionnés, ~2,6 Go ; téléchargés par le notebook) |

Environnement : `uv sync --all-packages` à la racine du dépôt, puis le noyau Jupyter du `.venv`
(sélectionné depuis VS Code ou un Jupyter existant). Le notebook se lance depuis ce dossier.
