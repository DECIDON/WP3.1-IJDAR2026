# Robustesse de la formularité

La formularité ([rapport §5](../rigidity-indicators/indicateurs-rigidite.md#s5)) mesure la part d'une fenêtre prise
dans des 4-grammes qui reviennent au moins 3 fois dans les autres documents de son dataset. Ce dossier vérifie trois
choses avant de l'utiliser comme seul indicateur de formulaicité :

1. **Dispersion.** Une formule doit être partagée par plusieurs documents, et non répétée dans un seul. Les
   *lexical bundles* de Biber et al. exigent une fréquence **et** une dispersion. On ajoute donc le critère
   « présent dans au moins 2, puis 3 documents distincts de la référence » (`compute_formularity(..., min_docs=k)`).
2. **Self-BLEU** (Zhu et al. 2018). Mesure-t-on la même chose qu'une métrique publiée de répétition entre textes ? On
   calcule le BLEU de chaque fenêtre contre la **même référence** que la formularité.
3. **Taille des n-grammes.** On compare les 3-grammes et les 5-grammes aux 4-grammes. La sensibilité au seuil
   d'occurrences (2, 3 ou 5) est déjà mesurée dans le rapport : les classements corrèlent entre 0,97 et 0,99.

## Données

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv`, de 100 et de 300 mots,
hors NEM.fr (référence sous les 15 000 tokens). Les figures sont tracées sur 300 mots, l'échelle de
[`../clustering-pca/`](../clustering-pca/README.md). La formularité recalculée avec les réglages actuels retrouve
exactement celle de `windows.csv`.

## Self-BLEU : ce qui est calculé

Pour une fenêtre du document *d*, les références sont les extraits de 500 mots qui forment sa référence de
formularité : hors *d*, 20 000 tokens environ. Pour n = 1 à 4, la précision est la part des n-grammes de la fenêtre
retrouvés dans un extrait. Chaque effectif est écrêté au maximum observé dans un même extrait, comme dans BLEU à
références multiples. Le score est la moyenne géométrique des quatre précisions (×100), avec le lissage
« method1 » (0,1 au lieu d'un numérateur nul).

Il n'y a pas de pénalité de brièveté : toutes les fenêtres ont la même taille et elle ne changerait pas les rangs.

Trois variantes :

| colonne | tokens | ce qu'elle voit |
|---|---|---|
| `sbleu_raw` | texte en minuscules | Self-BLEU usuel : vocabulaire et thème communs, et formules |
| `sbleu_masked` | séquence de la formularité (`<NAME>`, `<NUM>`) | idem, mais les noms et nombres ne séparent plus deux gabarits |
| `p4_masked` | idem, 4-grammes seulement | la plus proche de la formularité, sans seuil d'occurrences |

## Comparaison avec des mesures de diversité lexicale

On compare aussi la formularité, le Self-BLEU et trois mesures de répétition **internes à la fenêtre** : MATTR
(Covington et McFall 2010, TTR moyen sur des fenêtres glissantes de 50 mots), ĥ (Bentz et al. 2017) et Distinct-2. Les
critères sont ceux qui décident du choix d'un indicateur : séparation des datasets, effet de la langue dans un même
corpus multilingue, part de fenêtres à 0, recoupement avec les autres indicateurs (`comparaison.md`).

## Script

```bash
# depuis ce dossier, après `uv sync --all-packages` à la racine et la construction de data/pivot/ (loaders.py)
uv run python robustness.py             # 5 à 6 minutes
uv run python robustness.py --figures   # résumé et figures seulement, depuis results/fenetres.csv
```

| fichier de `results/` | contenu |
|---|---|
| `fenetres.csv` | une ligne par fenêtre : toutes les variantes, Self-BLEU, taille et nombre de documents de la référence |
| `resume.md`, `resume.json` | η², corrélations avec la formularité actuelle, médianes par dataset (100 et 300 mots) |
| `comparaison.md`, `comparaison.json` | formularité, Self-BLEU, MATTR, ĥ, Distinct-2 : η², effet de langue, part de 0, corrélations |
| `dispersion_n.png` | médiane de chaque variante par dataset |
| `self_bleu.png` | formularité contre Self-BLEU, fenêtres et médianes des datasets |

## Résultats

Les chiffres sont ceux des fenêtres de 300 mots ; à 100 mots, les conclusions sont les mêmes (`resume.md`).

**1. Le critère de dispersion ne change presque rien** (`dispersion_n.png`, panneau A).
* L'ordre des datasets ne bouge pas : ρ = 0,99 avec la formularité actuelle, entre fenêtres comme entre médianes.
  La séparation des datasets est la même (η² = 0,82).
* Les datasets à gabarits gardent 94 à 99 % de leur couverture avec le critère de 3 documents : M-POPP, Bâle, Old
  Bailey, GeoEDdA, ajmc. E-NER en garde 86 %.
* Trois datasets en perdent davantage :
  * **SoDUCo** (82 %) : des gabarits présents dans une ou deux pages seulement (`st <NAME> , <NUM>`, `. <NAME> , vins`).
  * **COPIOUS** (78 %) : des mesures (`<NUM> to <NUM> in .`), propres à quelques documents.
  * **7romans** (68 %) : des tournures de la langue (`qu ' il n`, `. - eh bien`), car la référence n'a que 6 romans.
* La presse en perd aussi (43 à 94 %), mais sur des valeurs déjà proches de 0.

La formularité actuelle n'est donc pas faite de répétitions propres à un seul document. On peut adopter le critère à
2 documents pour coller à la définition des *lexical bundles* : il ne change rien en pratique (ρ = 1,00).

**2. La formularité et le Self-BLEU classent les datasets de la même façon** (`self_bleu.png`).

| | ρ entre fenêtres | ρ entre médianes des datasets | ρ médian dans un dataset | η² |
|---|---|---|---|---|
| Self-BLEU masqué | 0,92 | 0,96 | 0,65 | 0,84 |
| Self-BLEU brut | 0,87 | 0,90 | 0,44 | 0,85 |
| formularité | — | — | — | 0,82 |

* **Entre datasets**, l'accord est fort : c'est un argument de validité convergente.
* **À l'intérieur d'un dataset**, il est plus faible. Le Self-BLEU brut compte aussi le vocabulaire commun (1- et
  2-grammes), donc le thème. Il place Old Bailey au niveau de SoDUCo, et 7romans au-dessus de la presse.
* **Les écarts les plus nets sont ajmc et COPIOUS** : leur Self-BLEU masqué (26 à 41) est au niveau de GeoEDdA et
  d'Old Bailey, alors que leur formularité est faible (3 à 7 %). Dans ajmc-en et COPIOUS, environ 13 % des 4-grammes sont des suites
  **sans mot** (`<NUM> . <NUM> ,`, références de vers ou de pages, mesures), fréquentes dans la référence. La
  formularité les exclut volontairement (« un gabarit contient au moins un mot ») ; le Self-BLEU les compte.
  C'est un choix de définition à assumer : ces suites relèvent plutôt de la structure typographique.

**3. Les 4-grammes sont un bon compromis** (`dispersion_n.png`, panneau B).
* La séparation est la même pour n = 3, 4 ou 5 (η² = 0,82 à 0,83). L'ordre change peu (ρ = 0,93 entre fenêtres).
* Les **3-grammes** captent des tournures banales de la langue : la presse et LitBank montent à 3 à 8 %, et Old
  Bailey (36 %) dépasse SoDUCo.
* Les **5-grammes** effacent les formules courtes : la presse, ajmc-de et 7romans tombent à 0.

**4. Pourquoi garder la formularité plutôt que le Self-BLEU** (`comparaison.md`). Le Self-BLEU sépare un peu mieux les
datasets (η² = 0,84 à 0,85 contre 0,82) et n'a pas de masse à 0 : 22 % des fenêtres de 300 mots ont une formularité
nulle (36 % à 100 mots), ce qui forme la traînée diagonale de l'ACP. Mais :
* **sa version standard, brute, dépend de la langue** : dans newseye (même presse en fr, fi, sv), η² de la langue = 0,25
  contre 0,02 pour la formularité. Les 1-grammes se retrouvent moins dans une langue à morphologie riche ;
* **sa version masquée n'est plus standard** et recoupe davantage les autres indicateurs : ρ = 0,76 avec la densité de
  noms propres (0,68 pour la formularité), 0,49 avec la typographie (0,38). Elle compte les suites de nombres et de
  signes ;
* la formularité se lit directement (« x % du texte pris dans des gabarits ») et suit une définition de la
  linguistique de corpus, les *lexical bundles* de Biber.

Le Self-BLEU sert donc de **validation convergente** : ρ = 0,96 entre médianes des datasets.

**5. MATTR, comme ĥ et Distinct-2, ne mesure pas la formularité.**

| 300 mots | η² dataset | η² langue newseye / hipe2020 / ajmc | ρ avec la formularité |
|---|---|---|---|
| formularité | 0,82 | 0,02 / 0,32 / 0,01 | — |
| MATTR | 0,60 | **0,64** / 0,52 / 0,21 | −0,31 |
| ĥ | 0,69 | **0,74** / 0,52 / 0,12 | −0,48 |

Ces mesures voient la répétition **à l'intérieur de la fenêtre**, alors qu'une formule se répète d'un document à
l'autre. Un acte de M-POPP récite son gabarit une fois, avec des noms, des dates et des lieux différents : son MATTR
(0,86) vaut celui de newseye-fr. Elles mesurent surtout la langue : les valeurs les plus hautes sont en finnois,
allemand et suédois (newseye-fi 0,94, ajmc-de 0,92, newseye-sv 0,91).

## Limites

* **Balises dans SoDUCo (corrigé).** Les premières versions du pivot SoDUCo gardaient les balises d'annotation
  `<TITRE-H>` et `<TITRE-P>` (environ 440 paires par variante) : l'expression régulière de `loaders.py` n'acceptait
  pas le tiret. Corrigé, puis `windows.csv` et ce dossier ont été recalculés. La formularité médiane de SoDUCo-ref
  passe de 31,5 à 27,8 % (300 mots) ; aucune conclusion ne change.
* **Self-BLEU, échelle.** Il n'y a pas de pénalité de brièveté, donc les valeurs ne se comparent pas à celles
  d'articles en génération de texte. Seuls les rangs comptent ici.
* **Références.** Les seuils de Biber (fréquence par million de mots, dispersion sur 5 textes) et ceux de Hyland
  (10 % des textes) sont cités de mémoire : à vérifier avant l'article.
