# ACP et classifications des datasets sur les indicateurs de rigidité

Ce dossier décrit les datasets du projet à partir d'indicateurs du package [`text_rigidity`](../../text-rigidity/README.md) :
ACP, puis classifications des fenêtres (FCM, CAH Ward, autres algorithmes), avec un modèle nul pour savoir si les
groupes trouvés existent ou si l'algorithme coupe un continuum.

Les indicateurs eux-mêmes sont définis dans le package et validés dans
[`../rigidity-indicators/`](../rigidity-indicators/README.md). Ce dossier ne recalcule que ce qui manque à
`windows.csv` (ĥ, ponctuation, formularité de NEM.fr sur une référence commune).

## Fenêtres : 100 mots, la taille de référence de l'étude

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv`, taille **100 mots** :
au plus 100 fenêtres sans recouvrement par sous-corpus. Leur texte est relu dans le pivot `data/pivot/`
(`loaders.py`).

C'est la taille du protocole ([`docs/protocole-experimental.md`](../../docs/protocole-experimental.md)) aux deux
échelles, globale et locale : le profil des datasets décrit ici se compare donc directement aux fenêtres autour des
entités. Les indicateurs sont des taux, mais leur bruit dépend de la longueur ; une autre taille décrirait un autre
objet que celui du modèle.

300 mots séparerait mieux les datasets (formularité η² = 0,82 contre 0,69), mais ne convient pas à l'étude :
- **à l'échelle locale**, une fenêtre de 300 mots n'est plus le contexte de l'entité. Elle contient en médiane 11 à 37
  autres entités gold selon le dataset, contre 4 à 14 à 100 mots ; SoDUCo 133 contre 44, GeoEDdA 76 contre 30 (Old
  Bailey, peu annoté, mis à part). Beaucoup
  d'entités sont dans des documents de moins de 300 mots, où la fenêtre serait le document entier, de taille
  variable : ajmc-de 91 % des entités, ajmc-fr 74 %, hipe2020-en 48 %, M-POPP manuscrit 28 %, Old Bailey 25 % ;
- **à l'échelle globale**, le tirage exclut ces documents courts. Il ne reste que 8 fenêtres pour ajmc-de, 21 pour
  ajmc-fr, 64 pour hipe2020-en, 2 pour NEM.fr mail, et le profil penche vers les documents longs : les documents de
  moins de 300 mots sont 36 % de M-POPP manuscrit, 48 % de Bâle et d'Old Bailey, 54 % de newseye-fi.

Les résultats à 300 mots servent de contrôle de robustesse (voir la fin des résultats).

Groupes : un par dataset ; les langues d'un même corpus sont fusionnées (« hipe2020 (fr, en, de) », « ajmc »,
« newseye ») ; NEM.fr est découpé par genre (« NEM.fr spoken »…).

## Indicateurs

Jeu « Claude-Bertrand » (les cinq premiers) et balance phrastique, tous orientés **+ = plus rigide**, puis centrés-réduits :

| indicateur | source | transformation | sens rigide |
|---|---|---|---|
| formularité | `windows.csv` | log(1 + x) | haute |
| ĥ, taux d'entropie des mots (Bentz et al. 2017) | `entropy_rate_lz`, calculé ici | — | bas (texte prévisible) |
| Distinct-2 | `windows.csv` | — | bas (texte répétitif) |
| KL des POS | `windows.csv` | log | haute |
| ponctuation | `count_typographic_marks`, famille `punctuation` (`. , ; : ! ? …`) pour 100 mots, calculée ici | log(1 + x) | haute |
| balance phrastique | `windows.csv` | — | basse (peu de mots de liaison, style liste) |

La ponctuation est la part « ponctuation » du formatage typographique : balisage Markdown retiré, une suite de signes
compte pour une marque, sans parenthèses, tirets, filets ni symboles.

À savoir avant de lire les résultats ([rapport](../rigidity-indicators/indicateurs-rigidite.md)) : seules la formularité
et la balance phrastique font partie des indicateurs retenus ; ĥ et Distinct-2 font doublon (ρ = 0,81 à 100 mots, 0,91 à 300) ; la KL dépend
d'une référence UD par langue et ne se compare qu'à langue égale.

## Cinq jeux, deux traitements de NEM.fr

La formularité d'une fenêtre se mesure contre les autres documents de son sous-corpus. Un genre de NEM.fr n'en fournit
que 600 à 3 300 tokens, sous le seuil de comparabilité de 15 000 (`analysis.MIN_REF_TOKENS`) : comme `analysis.py`,
`common.load_windows` met alors la valeur à vide. On fait donc les deux :

| dossier de `results/` | indicateurs | NEM.fr | formularité des genres de NEM.fr |
|---|---|---|---|
| `indicateurs-claude-bertrand` | les 5 | exclu (2 100 fenêtres) | règle de `analysis.py` : référence trop petite, valeur vide |
| `indicateurs-claude-bertrand-NEMpool` | les 5 | inclus (2 529 fenêtres) | référence commune à tout NEM.fr, hors document de la fenêtre (`nem_formularity.py`) |
| `indicateurs-claude-bertrand-sans-distinct2` | sans Distinct-2 | exclu | comme ci-dessus |
| `indicateurs-claude-bertrand-sans-distinct2-NEMpool` | sans Distinct-2 | inclus | référence commune à tout NEM.fr |
| `indicateurs-formularite-ponctuation-balance` | formularité, ponctuation, balance phrastique | exclu | règle de `analysis.py` |

Avec la référence commune (20 150 tokens au moins), la formularité d'un genre est mesurée par rapport à NEM.fr, pas
par rapport au genre lui-même.

## Scripts

| script | rôle | sortie |
|---|---|---|
| `common.py` | fenêtres et groupes, ACP, FCM, CAH, modèle nul, autres algorithmes | — |
| `nem_formularity.py` | formularité des fenêtres NEM.fr contre une référence commune à NEM.fr | `results/nem_formularity_pooled.csv` |
| `pca_indicators.py` | ĥ et ponctuation, puis pour chaque jeu : corrélations, ACP, CAH des groupes, classifications | `results/<jeu>/`, `results/resume_indicateurs.json` |

```bash
# depuis ce dossier, après `uv sync --all-packages` à la racine et la construction de data/pivot/ (loaders.py)
uv run python nem_formularity.py   # quelques secondes
uv run python pca_indicators.py    # tous les jeux, une dizaine de minutes
uv run python pca_indicators.py indicateurs-formularite-ponctuation-balance   # un seul jeu
```

Pour chaque jeu, `results/<jeu>/` contient :

| fichier | contenu |
|---|---|
| `correlations.png` / `.csv` | ρ de Spearman entre indicateurs (fenêtres, puis médianes de groupe) |
| `acp.png`, `composantes.md` | A : variance portée par chaque composante et seuil de Kaiser ; B : poids des indicateurs dans chaque composante et lecture en mots de ses deux côtés ; C : plan PC1-PC2, fenêtres en gris, médiane et 50 % central de chaque groupe, flèches = sens où chaque indicateur augmente ; D, E : position des groupes sur PC1 et PC2, avec le sens des deux extrémités de l'axe |
| `cah_groupes.png` | CAH (Ward) des groupes sur leurs médianes |
| `clusters_FCM_k2-6.png`, `clusters_CAH_k2-6.png`, `clusters.json` | FCM (m = 2, algorithme de Seghier et al.) et CAH Ward pour k = 2 à 6 ; silhouette réelle contre celle d'un nuage gaussien de même covariance, sans cluster (10 tirages) |
| `algos.png`, `algos.json` | contrôle du FCM : k-means (silhouette maximale), GMM (BIC minimal), CAH Ward (plus grand saut), HDBSCAN ; accord avec les groupes (ARI, AMI) |

Les classifications portent sur les **composantes de Kaiser** (valeur propre > 1, au moins 2). Dans les quatre jeux
« Claude-Bertrand », Kaiser retient 2 composantes : on classe dans le plan PC1-PC2, qui porte 77 à 80 % de la variance.
Dans le jeu formularité-ponctuation-balance, Kaiser n'en retient qu'une ; on classe quand même dans le plan PC1-PC2
(89,2 %).

## Résultats

Fenêtres de 100 mots. Les résultats à 300 mots (commit caf7560 dans l'historique git) sont résumés au point 6.

1. **Deux dimensions de rigidité.** C'est le plus net sans Distinct-2 :
   - PC1 (49,7 %) = **liste** : KL des POS, ponctuation, formularité. SoDUCo (+3,0 à +3,3) contre la presse
     (letemps, hipe2020, newseye, −1,1 à −1,3) ;
   - PC2 (30,2 %) = **redondance / formule** : ĥ bas et formularité. E-NER, Old Bailey, M-POPP manuscrit (+1,3 à +1,7)
     contre ajmc et newseye (−1,0 à −1,2).

   Avec Distinct-2, PC1 (42,8 %) est un axe commun aux 5 indicateurs (SoDUCo +2,2 à +2,5 contre newseye −1,5) et PC2
   (36,4 %) oppose ponctuation et KL à ĥ et Distinct-2 : les mêmes deux dimensions, mélangées.
2. **Trois familles, mais un continuum autour.** CAH Ward à k = 3, sans Distinct-2 : SoDUCo (98-100 % de ses
   fenêtres) avec les deux tiers d'ajmc (67 %), dont la ponctuation est dense ; M-POPP (91-97 %), Old Bailey (88 %),
   E-NER (74 %) ; tout le reste (presse, LitBank, 7romans : 83-89 %). Bâle, GeoEDdA et COPIOUS se partagent. La
   silhouette dépasse celle du modèle nul (CAH k = 3 : 0,38 contre 0,30 au plus ; FCM k = 3 : 0,40 contre 0,34),
   mais les algorithmes ne s'accordent pas sur le nombre de groupes (k-means et CAH : 2 à 5 ; GMM : 5 à 7 ;
   HDBSCAN : 0 à 2 groupes) et l'accord avec les datasets reste faible (ARI 0 à 0,21).
3. **NEM.fr (jeux NEMpool).** Les genres se placent au pôle non rigide de PC1 (sans Distinct-2 : spoken −2,3,
   tweets −1,5, biomedical −1,4) ; la structure des autres datasets ne change pas.
4. **Sans ĥ ni KL (formularité, ponctuation, balance).** ĥ mesure surtout la diversité du vocabulaire, que la langue,
   l'OCR, les noms propres et les nombres font varier ; la KL dépend de la langue. Sans eux :
   - PC1 (63,3 %) est un **axe de rigidité commun** (balance +0,64, ponctuation +0,63, formularité +0,45) : SoDUCo
     (+2,8) contre LitBank (−1,4), hipe2020 et letemps (−1,0) ;
   - PC2 (25,9 %) oppose la **formule** (formularité +0,89) à la **liste** (ponctuation −0,34, balance −0,29) :
     M-POPP et Old Bailey (+1,3 à +1,6) contre newseye (−0,8).

   La structure se détache du modèle nul (CAH Ward k = 5 : 0,42 contre 0,29 au plus pour le nuage gaussien ; k = 3 :
   0,37 contre 0,30). À k = 3 : SoDUCo (95-98 %) ; un groupe formulaire (M-POPP 100 %, Old Bailey 96 %, E-NER 83 %,
   Bâle 78 %, GeoEDdA 69 %, 7romans 57 %) ; la presse, LitBank et ajmc (66-89 %). À k = 5, M-POPP (96-100 %, avec
   44 % de Bâle), la formule et la liste, se sépare d'Old Bailey (82 %) et d'E-NER (76 %), la formule dans des
   phrases ; ajmc (73 %) forme un groupe avec 41 % de newseye.
5. **La masse à 0 de la formularité pèse sur les classifications.** 36 % des fenêtres de 100 mots n'ont aucun gabarit
   (newseye, letemps, hipe2020 fr et de, LitBank : 63 à 88 % ; 7romans 43 %). Elles forment la ligne diagonale en bas à gauche du plan PC1-PC2,
   que les classifications isolent comme un groupe : le troisième groupe de la CAH à k = 3 est d'abord celui des
   fenêtres sans formule. Ce groupe est réel (pas de gabarit), mais il ne dit rien des différences entre ces textes.
6. **À 300 mots** (contrôle), les mêmes deux dimensions et les mêmes familles apparaissent, avec une séparation plus
   nette : PC1-PC2 portent 85 à 87 % de la variance (91,6 % dans le jeu sans ĥ ni KL), et 22 % des fenêtres seulement
   ont une formularité nulle. La place d'ajmc est instable : à 300 mots et k = 3, il se range avec la presse ; à
   100 mots, deux tiers de ses fenêtres rejoignent SoDUCo dans le jeu sans Distinct-2.

## Limites

- **DECIDON n'est pas inclus** : il n'est pas encore dans `loaders.py` (voir [`data/README.md`](../../data/README.md)).
- ĥ et Distinct-2 font doublon (ρ = 0,81) ; d'où les jeux sans Distinct-2. À 300 mots, ĥ suit presque exactement la
  part de mots distincts (ρ = 0,99) ; d'où le jeu sans ĥ.
- La KL et, dans une moindre mesure, la ponctuation dépendent de la langue.
- Effectifs faibles : genres de NEM.fr (mail : 19 fenêtres, multi : 24).
