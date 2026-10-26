# WP3.1-ijdar26
Code and experiments for the IJDAR 2026 paper on NER &amp; textual rigidity

## Organisation

| dossier | contenu |
|---|---|
| [`text-rigidity/`](text-rigidity/README.md) | package Python `text_rigidity` : les indicateurs de rigidité textuelle (formatage typographique, balance phrastique, formularité, densité de noms propres), avec ses tests |
| [`experiments/rigidity-indicators/`](experiments/rigidity-indicators/README.md) | expériences sur les indicateurs : notebook exploratoire, validation sur les datasets du projet, rapport [`indicateurs-rigidite.md`](experiments/rigidity-indicators/indicateurs-rigidite.md) |
| [`experiments/clustering-pca/`](experiments/clustering-pca/README.md) | ACP et classifications (FCM, CAH, modèle nul, autres algorithmes) des fenêtres de 300 mots des datasets sur des jeux d'indicateurs du package : profil global des corpus |
| [`experiments/formularity-robustness/`](experiments/formularity-robustness/README.md) | robustesse de la formularité : critère de dispersion, comparaison au Self-BLEU, taille des n-grammes |
| [`data/`](data/README.md) | datasets bruts partagés par les expériences : **non versionnés**, stockés hors GitHub ; seul `data/README.md` (provenance) est suivi |
| [`docs/`](docs/protocole-experimental.md) | protocole expérimental : tester la sensibilité des modèles NER à la rigidité des textes |

## Installation

Le dépôt est un workspace [uv](https://docs.astral.sh/uv/) : un seul environnement (`.venv`, Python 3.11)
pour le package et les expériences.

```bash
uv sync --all-packages      # package text_rigidity (éditable) + dépendances des expériences
uv run pytest text-rigidity # tests du package
```
