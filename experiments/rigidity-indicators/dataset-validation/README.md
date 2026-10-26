# Validation des indicateurs sur les datasets du projet

Ces scripts recalculent les indicateurs de rigidité sur les datasets de `data/` (racine du dépôt), sur des fenêtres de 100 et de 300 mots. Les indicateurs eux-mêmes sont définis dans le package [`text_rigidity`](../../../text-rigidity/README.md), seule source : `compute_indicators.py` l'importe.

| script | rôle | sortie |
|---|---|---|
| `loaders.py` | lit les datasets bruts (TSV HIPE, JSON, brat, TEI, parquet…) et les convertit dans un format commun : un document = texte et spans d'entités | `../../../data/pivot/<dataset>.jsonl` |
| `compute_indicators.py` | tire au plus 100 fenêtres par sous-corpus, à tour de rôle dans les documents, et calcule les indicateurs | `results/windows.csv` |
| `analysis.py` | profils par dataset (médianes, écarts interquartiles), fiabilité, corrélations, validation de la densité de noms propres | tableaux cités dans le rapport : `results/profiles_100.csv`, `iqr_100.csv`, `reliability.csv`, `correlations_100_fr.csv`, `name_density_validation.csv`, `formularity_within_dataset.csv` (le reste est affiché dans la console) |
| `figure.py` | figure des deux axes (balance phrastique × formularité) | `../figures/rigidity_axes.png` |

```bash
# depuis ce dossier, après `uv sync --all-packages` à la racine du dépôt
python loaders.py        # une fois : construit data/pivot/
python compute_indicators.py  # environ 2 minutes sur CPU
python analysis.py
python figure.py
```

Dépendances : celles de `../pyproject.toml` (package `text_rigidity`, modèles spaCy `*_core_news_sm` / `en_core_web_sm`, `pandas`, `pyarrow`, `numpy`, `scipy`, `matplotlib`), installées par `uv sync --all-packages` ; lancer les scripts avec `uv run python …` ou après activation du `.venv`.

Choix à connaître :
- **Documents.** GeoEDdA : paragraphes regroupés par volume. Bâle : actes regroupés par les trois premiers éléments de leur identifiant. SoDUCo : une page d'annuaire par document. Old Bailey : un procès par document, tirés de 40 sessions réparties régulièrement entre 1834 et 1913. M-POPP : une page par document, entités reconstruites depuis l'encodage 1 (prénoms et noms → PER ; ville, numéro, type et nom de voie, département → LOC).
- **Formularité.** Elle n'est comparable entre sous-corpus que si la référence atteint 15 000 tokens. Ce n'est pas le cas des genres de NEM.fr (2 000 à 5 000 tokens chacun) : leur formularité est laissée vide.
- **DECIDON CR JORF n'est pas encore inclus**, faute du gold de référence (voir [`data/README.md`](../../../data/README.md)).
