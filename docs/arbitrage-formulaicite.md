# Mesurer la formulaicité : Self-BLEU ou formularité ?

*Note de décision, 27 octobre 2026. Elle complète le [rapport sur les indicateurs](../experiments/rigidity-indicators/indicateurs-rigidite.md#s5)
et le [protocole expérimental](protocole-experimental.md).*

> **En bref.** Deux mesures de la formulaicité sont calculées sur la même référence : le **Self-BLEU**, mesure
> standard de la reprise de suites de mots, et la **formularité**, part du texte prise dans des gabarits fréquents.
> Elles classent les datasets de la même façon, mais divergent à l'intérieur d'un dataset, et chacune a des
> défauts. Le Self-BLEU est retenu **à titre provisoire**. Le choix définitif se fera sur les expériences NER, selon
> une règle fixée ici **avant** de voir les résultats.

## 1. Ce que mesurent les deux indicateurs

Pour une fenêtre de 100 mots, la référence est faite d'extraits des *autres* documents du dataset (20 000 tokens).

* **Self-BLEU** [Zhu et al. 2018] : moyenne géométrique des précisions des 1- à 4-grammes de la fenêtre dans la
  référence, tokens spaCy en minuscules, signes compris (`compute_self_bleu`). Toute suite retrouvée une fois compte.
* **Formularité** : part des tokens couverts par un 4-gramme vu au moins 3 fois dans la référence, noms propres et
  nombres masqués (`<NAME>`, `<NUM>`) ; adaptation des *lexical bundles* de Biber (`compute_formularity`).

## 2. Ce qu'on sait (fenêtres de 100 mots)

Chiffres de [`formularity-robustness`](../experiments/formularity-robustness/README.md) (`results/comparaison.md`)
et de [`dataset-validation`](../experiments/rigidity-indicators/dataset-validation/README.md).

| | Self-BLEU | formularité |
|---|---|---|
| appui dans la littérature | génération de texte (diversité des sorties) | linguistique de corpus (formules, registres) |
| séparation des datasets (η²) | **0,76** | 0,69 |
| fenêtres à 0 | **0 %** | 36 % (presse et LitBank : 63 à 88 %) |
| accord entre médianes des datasets (ρ) | 0,91 | |
| accord à l'intérieur d'un dataset (ρ médian) | 0,41 | |
| phraséologie ordinaire (« qu' il avait », « for a long time ») | **comptée** : 7romans 17,8, LitBank 9,3, presse 3 à 6 | écartée par le seuil de 3 occurrences |
| formule dont seuls les noms changent | comptée en partie (M-POPP : 69) | **comptée entière** (M-POPP : 80 %) |
| lien avec la densité de noms propres dans un dataset (ρ médian) | **−0,01**, mais 0,73 dans GeoEDdA, 0,42 dans SoDUCo-pero | 0,31, jusqu'à 0,79 dans GeoEDdA |
| η² de la langue newseye / hipe2020 / ajmc | 0,17 / 0,11 / 0,10 | 0,02 / 0,24 / 0,13 |

Trois points à retenir :

* **Les deux mesures reposent sur la reprise de suites de mots.** À l'intérieur d'un dataset, le Self-BLEU suit la
  précision des 3- et 4-grammes (ρ = 0,95), pas celle des mots seuls (0,49) ; si l'on mélange les mots, son
  classement ne tient plus (ρ = 0,31). Il ne mesure ni le vocabulaire ni le thème.
* **Les deux mesures dépendent de la langue**, et nos corpus ne permettent pas d'en mesurer l'ampleur proprement : la
  langue s'y confond presque toujours avec la source. Le faible effet de la formularité dans newseye ne prouve rien,
  la presse valant presque toujours 0. Dans ajmc, seul corpus d'un même genre en trois langues, les deux mesures
  classent les langues en sens inverse : la formularité met l'allemand en haut (8,8 contre 3,2 pour l'anglais), le
  Self-BLEU en bas (10,0 contre 16,3).
* **La tokenisation n'est pas en cause.** On a recalculé le Self-BLEU sans les signes, puis sur des mots entiers
  (découpage aux espaces, « qu'il » gardé en un mot). L'effet de langue *augmente* (newseye : 0,26 et 0,33 au lieu
  de 0,17) et la séparation des datasets baisse (0,68 au lieu de 0,76). Les signes, partagés par toutes les langues,
  atténuent l'effet de la morphologie : les formes fléchies du finnois ou de l'allemand se retrouvent moins telles
  quelles d'un document à l'autre. On garde donc la tokenisation spaCy, signes compris.
* **La lemmatisation ne corrige pas non plus.** Sur les lemmes, l'effet de langue reste le même (newseye 0,17,
  hipe2020 0,14, ajmc 0,09), alors que la lemmatisation modifie environ 30 % des tokens de la presse dans toutes les
  langues. Elle profite surtout au français (hipe2020-fr : 6,0 → 11,5), très peu au finnois (3,0 → 3,8) : elle
  fusionne des mots grammaticaux français (« les » → « le »), alors que les relations que le finnois porte par ses
  cas disparaissent sans être remplacées. L'effet de langue tient donc surtout à la structure des langues, plus ou
  moins analytiques, et ne se corrige pas par un prétraitement. Il faut le neutraliser dans le modèle (3.1, point 3).

## 3. Préconisations

### 3.1 Dès maintenant

1. **Mesure principale provisoire : le Self-BLEU**, tokens spaCy signes compris. Raisons : mesure standard, meilleure
   séparation, pas de masse à 0, moins lié en médiane à la densité de noms propres, qui est un facteur à part dans
   l'étude.
2. **Calculer les deux mesures partout** : profils des datasets, fenêtres des entités, et référence tirée des seuls
   documents d'entraînement en régime 2 (protocole, section 7.5). Elles partagent la référence ; le surcoût est
   négligeable.
3. **Ne jamais comparer telles quelles les valeurs de deux langues**, pour l'une ou l'autre mesure. Une différence de
   niveau entre datasets de langues différentes peut venir de la langue. Le modèle du protocole (section 10.5) s'en
   protège déjà en partie : l'écart local est calculé à l'intérieur du document, et l'effet aléatoire du dataset
   absorbe les différences de niveau entre datasets. Il faut le dire dans l'article.
4. **À l'échelle globale** (16 datasets), décrire les datasets avec les deux mesures, sans en tirer de conclusion
   entre langues.
5. **Si la formularité entre dans un modèle**, la transformer en log(1 + x) et ajouter une variable « au moins un
   gabarit dans la fenêtre » (0 ou 1), pour traiter les 36 % de zéros.

### 3.2 Après les expériences NER : règle de décision

Le modèle principal (protocole, section 10.5) est ajusté avec le Self-BLEU, puis refait à l'identique avec la
formularité (protocole, section 12). On compare, pour chaque régime, les deux coefficients de formulaicité :
l'écart local et la moyenne du document. Les deux mesures « concluent pareil » sur un coefficient si les rapports de
cotes vont dans le même sens et si la conclusion au seuil de 5 % est la même (significatif ou non).

| résultat | lecture | décision pour l'article |
|---|---|---|
| **A. Mêmes conclusions** | Le choix de la mesure ne compte pas pour la NER. | Self-BLEU dans le texte principal ; formularité en annexe, en une phrase et un tableau. |
| **B. Effet avec la formularité seulement** | L'effet passe par les gabarits fréquents, que le Self-BLEU dilue dans la phraséologie ordinaire. À vérifier : l'effet tient-il sans GeoEDdA et avec la densité de noms propres en interaction ? | Si oui, la formularité devient la mesure principale, justifiée par ce résultat et par les *lexical bundles* ; le Self-BLEU est rapporté comme mesure standard de comparaison. Sinon, on conclut que l'effet tient aux noms, pas aux formules. |
| **C. Effet avec le Self-BLEU seulement** | L'effet peut venir de la phraséologie ordinaire plutôt que des formules. À vérifier : refaire le modèle sans 7romans ni LitBank. | Si l'effet disparaît, on le décrit comme un effet de « reprise de tournures courantes », pas de formulaicité. S'il tient, Self-BLEU principal, en signalant que la formularité ne le voit pas. |
| **D. Effets de sens opposés** | Les deux mesures captent des choses différentes, que la NER traite différemment. | On rapporte les deux comme un résultat, sans mesure unique de la formulaicité. On examine les entités où elles divergent le plus. |

Dans tous les cas :
* **refaire le modèle retenu dans une seule langue**, le français, qui compte le plus de datasets. Si l'effet tient à
  langue constante, il ne vient pas de la langue ;
* **rapporter les deux mesures** au moins en annexe, avec cette règle de décision, pour que le choix ne paraisse pas
  fait après coup.

## 4. Questions encore ouvertes

* **L'ampleur réelle de l'effet de langue.** Un test propre demanderait un même texte en plusieurs langues (corpus
  parallèle) : par exemple des actes ou des textes réglementaires traduits. Aucun de nos datasets ne s'y prête.
* **Les seuils de Biber et Hyland** (fréquence par million de mots, dispersion sur 5 textes, 10 % des textes) sont
  cités de mémoire : à vérifier avant l'article.

## Références

* D. Biber, S. Conrad and V. Cortes. *If you look at…: Lexical bundles in university teaching and textbooks.*
  Applied Linguistics, 25(3):371–405, 2004.
* Y. Zhu, S. Lu, L. Zheng, J. Guo, W. Zhang, J. Wang and Y. Yu. *Texygen: A benchmarking platform for text
  generation models.* Proc. SIGIR 2018, 1097–1100, 2018.
