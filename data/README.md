# Données brutes des datasets IJDAR 2026

Téléchargées le 23 octobre 2026 à partir des liens de `IJDAR_datasets.ods` (feuille « Matrice des entités », datasets validés). Ce sont les fichiers tels que publiés.

**Ces fichiers ne sont pas versionnés** (voir `.gitignore`) : ils sont stockés sur un espace partagé, hors GitHub. Pour travailler, les copier dans ce dossier en respectant l'arborescence ci-dessous ; `data/pivot/` est régénéré par `experiments/rigidity-indicators/dataset-validation/chargeurs.py`.

| dossier | dataset | source | contenu | licence |
|---|---|---|---|---|
| `7romans/` | 7romans | Hugging Face `compnet-renard/7-romans-ner` | un parquet (tokens + étiquettes) | voir `README.md` |
| `hipe2022/` | hipe2020 (fr, en, de), letemps, newseye (fr, fi, sv ; de exclu), ajmc (fr, en, de), topres19th | GitHub `hipe-eval/HIPE-2022-data` (clone, dernier commit) | TSV HIPE, versions v1.0 à v2.1 ; utiliser `data/v2.1` | voir le dépôt |
| `soduco/` | SoDUCo (NER imbriquée) | Zenodo 8167628 | JSON : transcription de référence et OCR Pero, entités imbriquées | CC BY 4.0 |
| `m-popp/` | M-POPP | Zenodo 10980636 | archive complète (1 Go, images comprises) ; seuls les fichiers `labels-*.json` (imprimés et manuscrits, encodages 1 à 5) sont extraits | CC BY 4.0 |
| `geoedda/` | GeoEDdA | Hugging Face `GEODE/GeoEDdA-NER` | `train/val/test.jsonl` | voir `README.md` |
| `litbank/` | LitBank | GitHub `dbamman/litbank` | entités au format brat et TSV (`entities/`) | voir le dépôt |
| `e-ner/` | E-NER | GitHub `terenceau1/E-NER-Dataset` | CSV au format CoNLL (`all.csv`) | voir `LICENSE` |
| `nem-fr/` | NEM.fr | GitHub `ayusekyo111/NEM.fr` | 68 textes, annotations brat (entités) et POS, 12 genres | aucune licence indiquée |
| `basel/` | Basel Land Records | Zenodo 16919653 | TEI simple et imbriquée, format BeNASch, documentation | CC BY 4.0 |
| `copious/` | COPIOUS | nactem.ac.uk/copious | brat, train/dev/test (668 documents) | voir le site |
| `old-bailey/` | Old Bailey Proceedings | Sheffield ORDA, figshare 4775434 (*Old Bailey Online XML Data*, v7.2, 2017) | XML des sessions (`sessionsPapers/`, 951 fichiers de 1834 à 1913) ; les pages DHI et oldbaileyonline.org renvoient une erreur 403 | CC BY-NC 4.0 |
| `decidon-cr-jorf/` | DECIDON CR JORF | **copie locale**, pas un téléchargement : `~/projets/decidon_ner/input/project-9-at-2026-04-23-16-27-3ecfe9c1.json` | export Label Studio, 50 pages annotées (PER, SPK, COM, FCT…) | interne |

Points à vérifier :

* **DECIDON CR JORF.** La table annonce 101 pages. L'export local n'en contient que 50 : ce n'est probablement pas la version de référence.
* **Old Bailey.** vérifier que la sélection 1834-1913 corresponde à la « partie vérifiée ».