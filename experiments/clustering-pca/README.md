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

Jeu « Claude-Bertrand », tous orientés **+ = plus rigide**, puis centrés-réduits :

| indicateur | source | transformation | sens rigide |
|---|---|---|---|
| formularité | `windows.csv` | log(1 + x) | haute |
| ĥ, taux d'entropie des mots (Bentz et al. 2017) | `entropy_rate_lz`, calculé ici | — | bas (texte prévisible) |
| Distinct-2 | `windows.csv` | — | bas (texte répétitif) |
| KL des POS | `windows.csv` | log | haute |
| ponctuation | `count_typographic_marks`, famille `punctuation` (`. , ; : ! ? …`) pour 100 mots, calculée ici | log(1 + x) | haute |

La ponctuation est la part « ponctuation » du formatage typographique : balisage Markdown retiré, une suite de signes
compte pour une marque, sans parenthèses, tirets, filets ni symboles.

À savoir avant de lire les résultats ([rapport](../rigidity-indicators/indicateurs-rigidite.md)) : seule la formularité
fait partie des indicateurs retenus ; à 300 mots, ĥ et Distinct-2 sont presque identiques (ρ = 0,91) ; la KL dépend
d'une référence UD par langue et ne se compare qu'à langue égale.

## Quatre jeux, deux traitements de NEM.fr

La formularité d'une fenêtre se mesure contre les autres documents de son sous-corpus. Un genre de NEM.fr n'en fournit
que 600 à 3 300 tokens, sous le seuil de comparabilité de 15 000 (`analysis.MIN_REF_TOKENS`) : comme `analysis.py`,
`common.load_windows` met alors la valeur à vide. On fait donc les deux :

| dossier de `results/` | indicateurs | NEM.fr | formularité des genres de NEM.fr |
|---|---|---|---|
| `indicateurs-claude-bertrand` | les 5 | exclu (1 862 fenêtres) | règle de `analysis.py` : référence trop petite, valeur vide |
| `indicateurs-claude-bertrand-NEMpool` | les 5 | inclus (1 986 fenêtres) | référence commune à tout NEM.fr, hors document de la fenêtre (`nem_formularity.py`) |
| `indicateurs-claude-bertrand-sans-distinct2` | sans Distinct-2 | exclu | comme ci-dessus |
| `indicateurs-claude-bertrand-sans-distinct2-NEMpool` | sans Distinct-2 | inclus | référence commune à tout NEM.fr |

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
uv run python pca_indicators.py    # quelques minutes
```

Pour chaque jeu, `results/<jeu>/` contient :

| fichier | contenu |
|---|---|
| `correlations.png` / `.csv` | ρ de Spearman entre indicateurs (fenêtres, puis médianes de groupe) |
| `acp.png`, `composantes.md` | éboulis, plan PC1-PC2 (flèches = indicateurs), position des groupes sur PC1 et PC2, poids de chaque composante |
| `cah_groupes.png` | CAH (Ward) des groupes sur leurs médianes |
| `clusters_FCM_k2-6.png`, `clusters_CAH_k2-6.png`, `clusters.json` | FCM (m = 2, algorithme de Seghier et al.) et CAH Ward pour k = 2 à 6 ; silhouette réelle contre celle d'un nuage gaussien de même covariance, sans cluster (10 tirages) |
| `algos.png`, `algos.json` | contrôle du FCM : k-means (silhouette maximale), GMM (BIC minimal), CAH Ward (plus grand saut), HDBSCAN ; accord avec les groupes (ARI, AMI) |

Les classifications portent sur les **composantes de Kaiser** (valeur propre > 1, au moins 2). Dans les quatre jeux,
Kaiser retient 2 composantes : on classe dans le plan PC1-PC2, qui porte 85 à 87 % de la variance.

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

## Limites

- **DECIDON n'est pas inclus** : il n'est pas encore dans `loaders.py` (voir [`data/README.md`](../../data/README.md)).
- ĥ et Distinct-2 font doublon ; d'où les jeux sans Distinct-2.
- La KL et, dans une moindre mesure, la ponctuation dépendent de la langue.
- Effectifs faibles : ajmc-de, genres de NEM.fr (mail : 2 fenêtres, multi : 6).
