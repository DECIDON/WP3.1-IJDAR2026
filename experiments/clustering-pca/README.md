# ACP et classifications des datasets sur les indicateurs de rigidité

Ce dossier décrit les datasets du projet à partir d'indicateurs du package [`text_rigidity`](../../text-rigidity/README.md) :
ACP, puis classifications des fenêtres (FCM, CAH Ward, autres algorithmes), avec un modèle nul pour savoir si les
groupes trouvés existent ou si l'algorithme coupe un continuum.

Les indicateurs eux-mêmes sont définis dans le package et validés dans
[`../rigidity-indicators/`](../rigidity-indicators/README.md). Ce dossier ne recalcule que ce qui manque à
`windows.csv` (ĥ, ponctuation, formularité de NEM.fr sur une référence commune).

## Fenêtres : 300 mots, profil global des datasets

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv`, taille **300 mots** :
1 986 fenêtres sans recouvrement, au plus 100 par sous-corpus. Leur texte est relu dans le pivot `data/pivot/`
(`loaders.py`).

Ces analyses **décrivent les corpus** (profil global). Elles ne disent rien de l'échelle locale à 100 mots du protocole
([`docs/protocole-experimental.md`](../../docs/protocole-experimental.md)), qui sert au modèle. À 300 mots, les datasets
se séparent mieux et le bruit par fenêtre est plus faible ; en contrepartie, les sous-corpus courts ont peu de
fenêtres : ajmc-de 8, ajmc-fr 21, hipe2020-en 64, genres de NEM.fr de 2 (mail) à 16 (encyclopedia).

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
et la balance phrastique font partie des indicateurs retenus ; à 300 mots, ĥ et Distinct-2 sont presque identiques (ρ = 0,91) ; la KL dépend
d'une référence UD par langue et ne se compare qu'à langue égale.

## Cinq jeux, deux traitements de NEM.fr

La formularité d'une fenêtre se mesure contre les autres documents de son sous-corpus. Un genre de NEM.fr n'en fournit
que 600 à 3 300 tokens, sous le seuil de comparabilité de 15 000 (`analysis.MIN_REF_TOKENS`) : comme `analysis.py`,
`common.load_windows` met alors la valeur à vide. On fait donc les deux :

| dossier de `results/` | indicateurs | NEM.fr | formularité des genres de NEM.fr |
|---|---|---|---|
| `indicateurs-claude-bertrand` | les 5 | exclu (1 862 fenêtres) | règle de `analysis.py` : référence trop petite, valeur vide |
| `indicateurs-claude-bertrand-NEMpool` | les 5 | inclus (1 986 fenêtres) | référence commune à tout NEM.fr, hors document de la fenêtre (`nem_formularity.py`) |
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
« Claude-Bertrand », Kaiser retient 2 composantes : on classe dans le plan PC1-PC2, qui porte 85 à 87 % de la variance.
Dans le jeu formularité-ponctuation-balance, Kaiser n'en retient qu'une ; on classe quand même dans le plan PC1-PC2
(91,5 %).

## Résultats

1. **Deux dimensions de rigidité.** C'est le plus net sans Distinct-2 :
   - PC1 (52,9 %) = **liste** : KL des POS, ponctuation, formularité. SoDUCo (+3,4) contre la presse (hipe2020,
     newseye, letemps, ≈ −1,2) ;
   - PC2 (33,8 %) = **redondance / formule** : ĥ bas et formularité. E-NER, Old Bailey, M-POPP contre newseye et ajmc.

   Avec Distinct-2, PC1 (49,8 %) est un axe commun aux 5 indicateurs (M-POPP, SoDUCo contre la presse) et PC2 (36,9 %)
   oppose ponctuation et KL à ĥ et Distinct-2 : les mêmes deux dimensions, mélangées.
2. **Trois familles, mais un continuum autour.** CAH Ward à k = 3, sans Distinct-2 : SoDUCo (96-99 % de ses fenêtres) ;
   M-POPP (96-99 %), Old Bailey (89 %), E-NER (75 %) ; tout le reste (presse, romans, ajmc, Bâle : 87-100 %). La
   silhouette dépasse celle du modèle nul (FCM k = 3 : 0,46 contre 0,33), mais les algorithmes ne s'accordent pas
   sur le nombre de groupes (k-means et CAH : 2 ou 3 ; GMM : 6 à 8 ; HDBSCAN : 2 groupes) et l'accord avec les
   datasets reste faible (ARI 0,03 à 0,26).
3. **NEM.fr (jeux NEMpool).** Les genres se placent au pôle non rigide de PC1 (spoken −2,6, tweets −1,9) ; la
   structure des autres datasets ne change pas.
4. **Sans ĥ ni KL (formularité, ponctuation, balance).** ĥ mesure surtout la diversité du vocabulaire, que la langue,
   l'OCR, les noms propres et les nombres font varier ; la KL dépend de la langue. Sans eux :
   - PC1 (66,1 %) est un **axe de rigidité commun** (balance +0,64, ponctuation +0,63, formularité +0,44) : SoDUCo
     (+3,2) contre LitBank, hipe2020 et Old Bailey (−1,1 à −1,3) ;
   - PC2 (25,4 %) oppose la **formule** (formularité +0,90) à la **liste** (ponctuation −0,34, balance −0,29) :
     M-POPP et Old Bailey (+1,3 à +1,5) contre newseye (−0,9).

   La structure se détache mieux du modèle nul qu'avec ĥ (CAH Ward k = 4 : 0,44 contre 0,31 au plus pour le nuage
   gaussien ; 0,37 contre 0,30 dans le jeu sans Distinct-2). À k = 3 : SoDUCo ; un groupe formulaire (M-POPP 100 %,
   Old Bailey 97 %, Bâle 87 %, E-NER 64 %, GeoEDdA 60 %) ; la presse et la littérature (84-99 %). ajmc et COPIOUS se
   partagent entre le groupe de SoDUCo et celui de la presse (47-53 %) : ils ressemblent à la liste sans être
   formulaires. À k = 5, Old Bailey et E-NER (formule dans des phrases) se séparent de M-POPP imprimé, Bâle et
   GeoEDdA (formule et liste). 22 % des fenêtres ont une formularité nulle (43 à 57 % pour la presse et LitBank) : elles
   forment la traînée diagonale en bas à gauche du plan, que GMM et HDBSCAN isolent comme un groupe à part.

## Limites

- **DECIDON n'est pas inclus** : il n'est pas encore dans `loaders.py` (voir [`data/README.md`](../../data/README.md)).
- ĥ et Distinct-2 font doublon ; d'où les jeux sans Distinct-2. À 300 mots, ĥ suit presque exactement la part de mots
  distincts (ρ = 0,99) ; d'où le jeu sans ĥ.
- La KL et, dans une moindre mesure, la ponctuation dépendent de la langue.
- Effectifs faibles : ajmc-de, genres de NEM.fr (mail : 2 fenêtres, multi : 6).
