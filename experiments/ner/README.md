# Expériences NER : pivot PER / LOC, sous-datasets équilibrés, zero-shot

Ce dossier prépare et lance les expériences de reconnaissance d'entités du protocole
([`docs/protocole-experimental.md`](../../docs/protocole-experimental.md)), avec les arbitrages pris depuis
(novembre 2026) :

- **Annotations prises telles quelles**, version du Sheet des datasets (onglet « Matrice des entités »). On ne garde
  que PER et LOC, avec les frontières, les catégories balisées et les imbrications de chaque projet. Pas de filtre
  « nom propre » : PER ne veut pas dire nom propre (LitBank, Bâle, DECIDON annotent aussi des groupes nominaux).
- **Une langue = un jeu** (ajmc, hipe2020 et newseye ne sont pas agrégés ; NEM.fr est un seul jeu, genres
  confondus).
- **Sous-datasets équilibrés** : chaque jeu est réduit au même nombre de mentions PER + LOC, celui du plus petit
  jeu, en tirant des unités entières ([Unités de tirage](#unites)).
- **Deux familles de modèles × deux régimes** : spaCy (`*_core_news_lg` / `en_core_web_lg`) et GLiNER
  `knowledgator/gliner-relex-multi-v1.0` ; (1) zero-shot, le même modèle sur tous les jeux ; (2) fine-tuning
  jeu par jeu, en validation croisée à 6 folds (à venir).

Ce dossier est un **projet uv autonome** (pas membre du workspace racine), pour ne pas imposer torch et les gros
modèles spaCy aux expériences sur les indicateurs.

## Chaîne

| étape | script | entrée → sortie | versionné ? |
|---|---|---|---|
| 1 | `normalize.py` | données brutes → format normalisé (un document natif par ligne, labels d'origine) | non |
| 2 | `pivot.py` | normalisé → pivot PER / LOC + unités de tirage | non |
| 3a | `sample.py draw` | pivot → `splits/<jeu>.json` (unités tirées, folds) + tableau ci-dessous | **oui** |
| 3b | `sample.py materialize` | pivot + splits → sous-datasets `<jeu>.jsonl` | non |
| 4 | `zeroshot.py` | sous-datasets → prédictions d'un run | non |
| 5 | `evaluate.py` | sous-datasets + run → `recap.csv` (P, R, F1 strict et fuzzy, IC95) | non |

**Aucune donnée n'est versionnée** (licences : NEM.fr sans licence globale, Old Bailey CC BY-NC, DECIDON interne).
Seuls le code et `splits/` le sont. Les splits ne contiennent que des identifiants de documents et des offsets : avec
les mêmes données brutes, `sample.py materialize` reconstruit des sous-datasets identiques au caractère près.

```bash
cd experiments/ner
uv sync                                           # étapes 1-3 et 5
uv run python normalize.py --raw <RAW> --out <DATA>/normalized
uv run python pivot.py --normalized <DATA>/normalized --out <DATA>/pivot
uv run python sample.py materialize --pivot <DATA>/pivot --out <DATA>/sample   # splits figés : pas de draw
uv sync --group spacy --group gliner              # étape 4
uv run python zeroshot.py spacy  --sample <DATA>/sample --out <RUNS>/zeroshot_spacy_lg  --threads 12
uv run python zeroshot.py spacy  --sample <DATA>/sample --out <RUNS>/zeroshot_spacy_trf_en --spacy-en en_core_web_trf
uv run python zeroshot.py gliner --sample <DATA>/sample --out <RUNS>/zeroshot_gliner_relex_multi --threads 12
uv run python evaluate.py --sample <DATA>/sample --run <RUNS>/zeroshot_gliner_relex_multi
```

## Données brutes

`normalize.py --raw <RAW>` attend ces dossiers (chargeurs dans `sources/`, copiés de la fiche statistique des
datasets ; leur sortie a été vérifiée identique à l'octet à celle d'origine sur les 23 jeux) :

| dossier | dataset | source |
|---|---|---|
| `hipe2022/` | hipe2020 (fr, de, en), letemps, newseye (fr, fi, sv), ajmc (fr, en, de) | GitHub `hipe-eval/HIPE-2022-data`, `data/v2.1` |
| `soduco-flat/` | SoDUCo (benchmark plat DAS 2022) : référence et OCR Pero | Zenodo 6394464 (`labeled/10-…human.json`, `labeled/31-…pero.json`) |
| `soduco-nested/` | SoDUCo imbriqué (lu par le chargeur, non utilisé dans le pivot) | Zenodo 8167628 + splits HF `nlpso/m1_fine_tuning_ref_cmbert_iob2` |
| `mpopp/` | M-POPP dactylographié et manuscrit | Zenodo 10980636 (`m-popp_datasets`) |
| `7-romans/` | 7romans | GitHub `obtic-sorbonne/7-romans` (`ner/`, CoNLL) |
| `geoedda/` | GeoEDdA | HF `GEODE/GeoEDdA-NER` |
| `litbank/` | LitBank | GitHub `dbamman/litbank` (`entities/brat`) |
| `e-ner/` | E-NER | GitHub `terenceau1/E-NER-Dataset` (`all.csv`) |
| `copious/` | COPIOUS | HF `DFKI-SLT/copious` (`copious_published.zip`) |
| `basel/` | Basel Land Records | Zenodo 16919653 (`tei_nested`) |
| `oldbailey/` | Old Bailey, sessions à partir du 1ᵉʳ nov. 1834 (seule période relue à la main) | DHI, `oldbailey.zip` (= OBO XML 7.2) |
| `decidon/` | DECIDON CR JORF, gold AUGUST (101 pages, md5 `97301c30`) | interne (Label Studio, dépôt DECIDON `NER_label-studio`) |
| `nem-fr/` | NEM.fr | GitHub `ayusekyo111/NEM.fr` |

Correspondance des étiquettes vers PER / LOC : `CORPUS` dans `pivot.py` (ex. GeoEDdA `NP/NC/ENE-Person` → PER,
LitBank `LOC + GPE + FAC` → LOC, DECIDON `PER + SPK + FCT` → PER ; M-POPP : prénoms et noms contigus fusionnés,
parties d'adresse contiguës fusionnées).

<a id="unites"></a>
## Unités de tirage

Une **unité** est ce qu'on tire en entier pour constituer un sous-dataset, et ce qu'on ne coupe jamais entre
entraînement et test dans la validation croisée. On garde l'unité native de chaque dataset (page, article, entrée,
acte…) ; elle n'est remplacée par une sous-unité pré-existante que lorsqu'elle est trop grosse pour fournir assez
d'unités au budget commun :

- **7romans** : la phrase (les romans entiers dépassent chacun le budget) ;
- **LitBank** : la ligne du texte fourni, qui est une phrase (6 extraits seulement pour atteindre le budget) ;
- **newseye-fr** : la ligne OCR (9 pages seulement pour atteindre le budget) ;
- **DECIDON** : le bloc de mise en page Chandra (paragraphe séparé par une ligne vide dans `text_md`) ;
- **GeoEDdA** : l'article de l'*Encyclopédie*, qui regroupe ses paragraphes (documents natifs du jeu), pour ne
  jamais séparer deux paragraphes d'un même article.

Une frontière d'unité ne coupe jamais une entité : les morceaux qu'une entité enjambe sont fusionnés
(975 entités de newseye-fr enjambent une fin de ligne, césures comprises ; 11 de DECIDON, un saut de bloc).

**Tirage** (`sample.py draw`) : unités mélangées avec la graine 42, prises dans l'ordre jusqu'à atteindre le budget ;
une unité qui ferait dépasser le budget de plus de 5 % est sautée. SoDUCo référence et OCR reçoivent les mêmes
entrées et les mêmes folds. **Folds** : 6, répartition gloutonne équilibrée en mentions (plus grosses unités
d'abord) ; un fold reste plus lourd quand une seule unité dépasse le sixième du budget (NEM.fr, newseye-fi, -sv).

<!-- UNITES : début (généré par sample.py draw) -->
Budget commun : **866 mentions PER + LOC** par jeu (= total du plus petit jeu), graine 42, 6 folds.

| jeu | unité de tirage | unités (corpus) | mentions / unité | unités tirées | mentions tirées | mentions par fold |
|---|---|---:|---:|---:|---:|---|
| 7romans | phrase (sous-unité du roman) | 26 785 | 1.2 | 728 | 866 | 144–145 |
| ajmc-de | page | 106 | 9.1 | 95 | 874 | 144–147 |
| ajmc-en | page | 86 | 10.4 | 86 | 891 | 148–149 |
| ajmc-fr | page | 104 | 8.3 | 104 | 866 | 144–145 |
| basel | fiche de registre | 829 | 8.6 | 94 | 868 | 144–145 |
| copious | page | 668 | 19.2 | 43 | 907 | 150–153 |
| decidon-august | bloc Chandra (sous-unité de la page) | 4 994 | 1.1 | 782 | 869 | 144–145 |
| e-ner | document (dépôt EDGAR) | 52 | 32.0 | 41 | 884 | 146–148 |
| geoedda | article de l'Encyclopédie | 2 001 | 8.7 | 112 | 873 | 145–146 |
| hipe2020-de | article | 185 | 26.9 | 39 | 867 | 144–145 |
| hipe2020-en | article | 126 | 8.9 | 102 | 886 | 147–148 |
| hipe2020-fr | article | 244 | 36.8 | 28 | 885 | 145–150 |
| letemps-fr | article | 516 | 20.4 | 31 | 870 | 143–148 |
| litbank | ligne (sous-unité de l'extrait) | 8 562 | 1.6 | 497 | 867 | 144–145 |
| mpopp-dactylo | zone d'acte | 446 | 22.8 | 36 | 880 | 138–154 |
| mpopp-manuscrits | zone d'acte | 447 | 19.1 | 44 | 883 | 145–150 |
| nem-fr | échantillon (genres confondus) | 68 | 21.5 | 41 | 883 | 124–260 |
| newseye-fi | page | 93 | 32.2 | 38 | 893 | 139–196 |
| newseye-fr | ligne (sous-unité de la page) | 8 435 | 1.6 | 554 | 867 | 144–145 |
| newseye-sv | page | 84 | 35.9 | 21 | 868 | 134–177 |
| oldbailey-1834-1913 | procès | 98 114 | 5.4 | 153 | 867 | 144–145 |
| soduco-ref | entrée d'annuaire | 8 765 | 2.1 | 409 | 867 | 144–145 |
| soduco-ocr | entrée d'annuaire | 8 392 | 2.1 | 409 | 867 | 144–145 |
<!-- UNITES : fin -->

## Zero-shot

| famille | modèles | étiquettes demandées / gardées |
|---|---|---|
| spaCy, même architecture CNN pour toutes les langues | `fr_core_news_lg`, `de_core_news_lg`, `en_core_web_lg`, `fi_core_news_lg`, `sv_core_news_lg` (3.8.0) ; en bonus `en_core_web_trf` (jeux anglais seulement, pas d'équivalent transformer pour les autres langues ; pour le français, la baseline est celle du NER DECIDON, `fr_core_news_lg`) | PER, PERSON, PRS → PER ; LOC, GPE, FAC → LOC ; autres étiquettes ignorées (comptées dans `run.json`) |
| GLiNER | `knowledgator/gliner-relex-multi-v1.0` (mDeBERTa-v3-base, multilingue, décodage au niveau du token), NER seul | « person » → PER, « location » → LOC (en anglais pour toutes les langues) ; seuil 0,5 ; décodage plat |

Il n'existe pas de GLiNER bi-encodeur multilingue public (`knowledgator/gliner-bi-*` : encodeurs `ettin` et
`bge-*-en`, anglais) : d'où le choix d'un uni-encodeur multilingue, version multilingue du `gliner-relex-base` utilisé
pour les CR du JORF. Épingles : `gliner==0.2.26`, `transformers==4.56.2` (comme la forge DECIDON GLiNER-relex).

**Évaluation** (`evaluate.py`) : nervaluate (SemEval'13, algorithme du scoreur HIPE), régimes strict et fuzzy
(`ent_type`), chaque label scoré seul puis comptes sommés (micro PER + LOC), IC95 par bootstrap sur les unités.
Les modèles ne prédisent que des entités plates : les mentions imbriquées d'un même type (HIPE `NE-NESTED`,
GeoEDdA `ENE`) plafonnent le rappel. **Old Bailey** : seul le rappel est interprétable (seuls les participants
au procès sont annotés).

## Résultats : 1er jet zero-shot (2026-11-04)

Lancé par `bash run_zeroshot.sh <SAMPLE> <RUNS> mathieu_1er_jet` (CPU, 12 threads, `nice`), 23 min en tout.
Sorties (non versionnées) : `data/ner/runs/mathieu_1er_jet_zeroshot_{spacy_lg,spacy_trf_en,gliner_relex_multi}/`
(`<jeu>.jsonl` des prédictions, `run.json` des versions, `recap.csv` avec P, R, F1, comptes et IC95 par label).

F1 micro PER + LOC, strict / fuzzy :

| jeu | spaCy lg | spaCy trf (anglais) | GLiNER-relex-multi |
|---|---|---|---|
| 7romans | 0.592 / 0.751 | | 0.579 / 0.747 |
| ajmc-de | 0.180 / 0.268 | | 0.469 / 0.518 |
| ajmc-en | 0.232 / 0.310 | 0.690 / 0.744 | 0.593 / 0.633 |
| ajmc-fr | 0.196 / 0.243 | | 0.538 / 0.596 |
| basel | 0.113 / 0.555 | | 0.179 / 0.586 |
| copious | 0.425 / 0.500 | 0.638 / 0.721 | 0.662 / 0.701 |
| decidon-august | 0.342 / 0.605 | | 0.315 / 0.694 |
| e-ner | 0.580 / 0.736 | 0.675 / 0.851 | 0.418 / 0.501 |
| geoedda | 0.252 / 0.376 | | 0.321 / 0.454 |
| hipe2020-de | 0.443 / 0.563 | | 0.607 / 0.737 |
| hipe2020-en | 0.420 / 0.713 | 0.469 / 0.791 | 0.646 / 0.751 |
| hipe2020-fr | 0.614 / 0.767 | | 0.636 / 0.797 |
| letemps-fr | 0.444 / 0.579 | | 0.560 / 0.655 |
| litbank | 0.249 / 0.374 | 0.278 / 0.413 | 0.280 / 0.563 |
| mpopp-dactylo | 0.592 / 0.860 | | 0.691 / 0.782 |
| mpopp-manuscrits | 0.530 / 0.773 | | 0.649 / 0.764 |
| nem-fr | 0.683 / 0.760 | | 0.756 / 0.803 |
| newseye-fi | 0.287 / 0.669 | | 0.271 / 0.660 |
| newseye-fr | 0.317 / 0.535 | | 0.507 / 0.723 |
| newseye-sv | 0.386 / 0.602 | | 0.495 / 0.736 |
| oldbailey-1834-1913 (rappel seul) | R 0.773 | R 0.798 | R 0.859 |
| soduco-ocr | 0.346 / 0.543 | | 0.587 / 0.827 |
| soduco-ref | 0.359 / 0.550 | | 0.600 / 0.834 |

Lecture :
1. GLiNER-relex-multi devance spaCy lg presque partout : F1 strict médian hors Old Bailey 0.569 vs 0.372.
   Sur l'anglais, `en_core_web_trf` est au niveau de GLiNER, voire au-dessus (ajmc-en, e-ner).
2. Old Bailey : rappel 0.77–0.86, précision 0.15–0.17, comme attendu d'une annotation partielle.
3. Effets d'annotation visibles ailleurs, sous deux formes : (a) gros écart strict → fuzzy = conventions de
   frontière (Bâle, DECIDON, newseye-fi, SoDUCo) ; (b) rappel bas même en fuzzy là où le gold annote aussi des
   groupes nominaux (LitBank, GeoEDdA `NC` / `ENE`). Q1 (analyse globale) se lit donc en fuzzy, jeu par jeu ;
   l'analyse locale (entités d'un même jeu) n'est pas touchée.

Prochaine étape : régime 2, fine-tuning par jeu en 6-fold sur les folds de `splits/`.
