# Robustesse de la formularité et choix du Self-BLEU

La formularité ([rapport §5](../rigidity-indicators/indicateurs-rigidite.md#s5)) mesure la part d'une fenêtre prise
dans des 4-grammes qui reviennent au moins 3 fois dans les autres documents de son dataset. Ce dossier la compare au
Self-BLEU, mesure standard de la répétition entre textes. Conclusion (point 4) : **le Self-BLEU brut est l'indicateur
de formulaicité retenu**, la formularité sert de complément lisible. Le dossier vérifie :

1. **Dispersion.** Une formule doit être partagée par plusieurs documents, et non répétée dans un seul. Les
   *lexical bundles* de Biber et al. exigent une fréquence **et** une dispersion. On ajoute donc le critère
   « présent dans au moins 2, puis 3 documents distincts de la référence » (`compute_formularity(..., min_docs=k)`).
2. **Self-BLEU** (Zhu et al. 2018). Mesure-t-on la même chose qu'une métrique publiée de répétition entre textes ? On
   calcule le BLEU de chaque fenêtre contre la **même référence** que la formularité, puis on regarde ce qui le fait
   varier (précisions par taille de n-gramme, **test du mélange** des mots).
3. **Taille des n-grammes.** On compare les 3-grammes et les 5-grammes aux 4-grammes. La sensibilité au seuil
   d'occurrences (2, 3 ou 5) est déjà mesurée dans le rapport : les classements corrèlent entre 0,97 et 0,99.

## Données

Les fenêtres sont celles de `../rigidity-indicators/dataset-validation/results/windows.csv`, de 100 et de 300 mots,
hors NEM.fr (référence sous les 15 000 tokens). Les figures et les chiffres ci-dessous portent sur 100 mots, la
taille de référence de l'étude ([protocole](../../docs/protocole-experimental.md)) ; 300 mots sert de contrôle. La
formularité recalculée avec les réglages actuels retrouve exactement celle de `windows.csv`.

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
| `comparaison.md`, `comparaison.json` | formularité, Self-BLEU, MATTR, ĥ, Distinct-2 : η², effet de langue, part de 0, corrélations ; test du mélange (précisions par n, Self-BLEU sur mots mélangés) |
| `dispersion_n.png` | médiane de chaque variante par dataset |
| `self_bleu.png` | formularité contre Self-BLEU, fenêtres et médianes des datasets |

## Résultats

Les chiffres sont ceux des fenêtres de 100 mots. À 300 mots, les conclusions sont les mêmes, avec une séparation plus
nette (`resume.md`, `comparaison.md`) ; seule exception, l'effet de langue du point 4.

**1. Le critère de dispersion ne change presque rien** (`dispersion_n.png`, panneau A).
* L'ordre des datasets ne bouge pas : ρ = 0,98 à 0,99 avec la formularité actuelle entre fenêtres, 0,99 à 1,00 entre
  médianes. La séparation des datasets est la même (η² = 0,69).
* Les datasets à gabarits gardent 94 à 99 % de leur couverture avec le critère de 3 documents : M-POPP, Bâle, Old
  Bailey, GeoEDdA, ajmc. E-NER en garde 86 %.
* Trois datasets en perdent davantage :
  * **SoDUCo** (80 %) : des gabarits présents dans une ou deux pages seulement (`st <NAME> , <NUM>`, `. <NAME> , vins`).
  * **COPIOUS** (73 %) : des mesures (`<NUM> to <NUM> in .`), propres à quelques documents.
  * **7romans** (73 %) : des tournures de la langue (`qu ' il n`, `. - eh bien`), car la référence n'a que 6 romans.
* La presse en perd parfois aussi (54 à 99 %), mais sur des valeurs déjà proches de 0.

La formularité actuelle n'est donc pas faite de répétitions propres à un seul document. On peut adopter le critère à
2 documents pour coller à la définition des *lexical bundles* : il ne change rien en pratique (ρ = 0,99).

**2. La formularité et le Self-BLEU classent les datasets de la même façon** (`self_bleu.png`).

| | ρ entre fenêtres | ρ entre médianes des datasets | ρ médian dans un dataset | η² |
|---|---|---|---|---|
| Self-BLEU masqué | 0,88 | 0,95 | 0,59 | 0,75 |
| Self-BLEU brut | 0,79 | 0,91 | 0,41 | 0,76 |
| formularité | — | — | — | 0,69 |

* **Entre datasets**, l'accord est fort : c'est un argument de validité convergente.
* **À l'intérieur d'un dataset**, il est plus faible (0,41 pour le Self-BLEU brut). Ce n'est pas que le Self-BLEU
  mesure le vocabulaire ou le thème : le **test du mélange** (`comparaison.md`) le montre.
  * À l'intérieur d'un dataset, le Self-BLEU brut suit la précision des 3- et 4-grammes (ρ médian = 0,95), beaucoup
    moins celle des 1-grammes (0,49).
  * Sur la même fenêtre aux mots mélangés, il ne vaut plus que 0,15 fois sa valeur, et son classement ne tient plus
    (ρ = 0,31 avec l'original).

  Il mesure donc bien la reprise de suites de mots, comme la formularité. Les deux divergent par leurs choix de
  définition : le Self-BLEU compte toute suite retrouvée au moins une fois, noms compris ; la formularité ne garde que
  les suites vues au moins 3 fois, noms et nombres masqués. D'où deux écarts :
  * la **phraséologie ordinaire** compte pour le Self-BLEU (« qu' il avait », « c' est une », « for a long time ») :
    7romans (17,8) et LitBank (9,3) passent au-dessus de la presse (3 à 6), alors que leur formularité est nulle ou
    presque ;
  * une **formule dont seuls les noms changent** compte entière pour la formularité, pas pour le Self-BLEU : M-POPP
    80 % contre 69.
* **Les écarts les plus nets sont ajmc et COPIOUS** : leur Self-BLEU masqué (32 à 41) est au niveau de GeoEDdA et
  d'Old Bailey, alors que leur formularité est faible (3 à 9 %). Dans ajmc-en et COPIOUS, environ 13 % des 4-grammes sont des suites
  **sans mot** (`<NUM> . <NUM> ,`, références de vers ou de pages, mesures), fréquentes dans la référence. La
  formularité les exclut volontairement (« un gabarit contient au moins un mot ») ; le Self-BLEU les compte.
  C'est un choix de définition à assumer : ces suites relèvent plutôt de la structure typographique.

**3. Les 4-grammes sont un bon compromis** (`dispersion_n.png`, panneau B).
* La séparation est la même pour n = 3, 4 ou 5 (η² = 0,68 à 0,69). L'ordre change peu (ρ = 0,87 à 0,90 entre
  fenêtres).
* Les **3-grammes** captent des tournures banales de la langue : la presse et LitBank montent à 3 à 9 %, et Old
  Bailey (37 %) dépasse SoDUCo.
* Les **5-grammes** effacent les formules courtes : la presse, ajmc-en, hipe2020-en et 7romans tombent à 0.

**4. Le Self-BLEU brut est retenu, la formularité sert de complément** (`comparaison.md`). La règle du projet : à
résultats à peu près équivalents, on prend la mesure standard ; c'est à la mesure maison de montrer qu'elle apporte
quelque chose de plus. À 100 mots, la taille de référence de l'étude, elle ne le montre pas :

| 100 mots | formularité | Self-BLEU brut |
|---|---|---|
| mesure standard | non | **oui** |
| séparation des datasets (η²) | 0,69 | **0,76** |
| fenêtres à 0 | 36 % (presse et LitBank : 63 à 88 %) | **0 %** |
| ρ avec la densité de noms propres, entre fenêtres | 0,59 | **0,37** |
| ρ médian avec la densité de noms propres, dans un dataset | 0,31 | **−0,01** |
| η² de la langue newseye / hipe2020 / ajmc | **0,02** / 0,24 / 0,13 | 0,17 / **0,11** / **0,10** |
| lecture | **« x % du texte dans des gabarits »** | score de 0 à 100, seuls les rangs comptent |

* **La masse à 0** de la formularité empêche de distinguer deux textes peu formulaires, et ces zéros forment un groupe
  à part dans les classifications ([`../clustering-pca/`](../clustering-pca/README.md), point 5).
* **Le lien avec la densité de noms propres** vient du masquage : `<NAME>` fabrique des gabarits avec les noms. Dans une
  étude NER, où la densité d'entités est un facteur à part, c'est un défaut de la formularité.
* **L'effet de langue** ne départage pas : le Self-BLEU brut est plus touché dans newseye (les 1-grammes se retrouvent
  moins dans une langue à morphologie riche), la formularité dans hipe2020 et ajmc. Dans hipe2020, la langue se
  confond avec la source : hipe2020-en vient d'autres journaux que fr et de.
* **La version masquée du Self-BLEU** n'est pas retenue : elle n'est plus standard et recoupe davantage les autres
  indicateurs (ρ = 0,73 avec la densité de noms propres, 0,49 avec la typographie).

**Test de tokenisation** (`comparaison.md`). Le Self-BLEU dépend-il de la langue à cause du découpage, par exemple
des élisions françaises (« qu ' il » en trois tokens) ? On le recalcule sans les signes, puis sur des mots entiers
(découpage aux espaces, signes retirés en bordure). Non : l'effet de langue **augmente** (newseye : 0,26 et 0,33 au
lieu de 0,17 ; hipe2020 : 0,28 et 0,21 au lieu de 0,11) et la séparation baisse (0,68 au lieu de 0,76). Les signes,
communs à toutes les langues, atténuent l'effet de la morphologie. On garde la tokenisation spaCy, signes compris.

**Test des lemmes** (diagnostic, `comparaison.md`). L'effet de langue vient-il de la flexion ? On recalcule le
Self-BLEU sur les lemmes spaCy, signes compris. La lemmatisation modifie environ 30 % des tokens de la presse, dans
toutes les langues (newseye-fi 34 %, hipe2020-fr 33 %, hipe2020-de 31 %, newseye-sv 28 %). Pourtant l'effet de langue
ne baisse pas : 0,17 / 0,14 / 0,09 au lieu de 0,17 / 0,11 / 0,10 (newseye / hipe2020 / ajmc). La lemmatisation profite
surtout au français (hipe2020-fr 6,0 → 11,5 ; letemps 5,7 → 10,1), très peu au finnois et au suédois (3,0 → 3,8 ;
3,5 → 4,0). En français, elle fusionne surtout des mots grammaticaux (« les » → « le », « des » → « un ») et des formes
verbales, qui se retrouvent alors partout ; en finnois, les relations portées par les cas disparaissent sans être
remplacées par des mots. L'effet de langue tient donc moins à la flexion qu'à la structure des langues : une langue
analytique répète davantage de suites de mots grammaticaux. Le classement à l'intérieur d'un dataset ne change presque
pas (ρ = 0,97 avec le Self-BLEU sur formes). La lemmatisation n'est donc pas une correction, et on ne la retient pas.

La formularité reste utile pour décrire les corpus, pour illustrer ce que mesure le Self-BLEU, et pour une analyse de
sensibilité du modèle NER. Le choix du Self-BLEU est provisoire ; la règle de décision après les expériences NER est
dans [Mesurer la formulaicité : Self-BLEU ou formularité ?](../../docs/arbitrage-formulaicite.md).

**5. MATTR, comme ĥ et Distinct-2, ne mesure pas la formulaicité.**

| 100 mots | η² dataset | η² langue newseye / hipe2020 / ajmc | ρ avec la formularité |
|---|---|---|---|
| formularité | 0,69 | 0,02 / 0,24 / 0,13 | — |
| MATTR | 0,49 | **0,41** / 0,34 / 0,29 | −0,21 |
| ĥ | 0,53 | **0,44** / 0,37 / 0,33 | −0,27 |
| Distinct-2 | 0,36 | 0,17 / 0,13 / 0,17 | −0,33 |

Ces mesures voient la répétition **à l'intérieur de la fenêtre**, alors qu'une formule se répète d'un document à
l'autre. Un acte de M-POPP récite son gabarit une fois, avec des noms, des dates et des lieux différents : son MATTR
(0,87 pour les imprimés) dépasse celui de newseye-fr (0,85). Elles mesurent surtout la langue : les valeurs les plus
hautes sont en finnois, français d'ajmc, allemand et suédois (newseye-fi 0,95, ajmc-fr 0,94, ajmc-de 0,93,
newseye-sv 0,91). À 300 mots, leur effet de langue est encore plus fort (MATTR 0,64 dans newseye).

## Limites

* **Balises dans SoDUCo (corrigé).** Les premières versions du pivot SoDUCo gardaient les balises d'annotation
  `<TITRE-H>` et `<TITRE-P>` (environ 440 paires par variante) : l'expression régulière de `loaders.py` n'acceptait
  pas le tiret. Corrigé, puis `windows.csv` et ce dossier ont été recalculés. La formularité médiane de SoDUCo-ref
  passe de 31,5 à 27,8 % (300 mots) ; aucune conclusion ne change.
* **Self-BLEU, échelle.** Il n'y a pas de pénalité de brièveté, donc les valeurs ne se comparent pas à celles
  d'articles en génération de texte. Seuls les rangs comptent ici.
* **Références.** Les seuils de Biber (fréquence par million de mots, dispersion sur 5 textes) et ceux de Hyland
  (10 % des textes) sont cités de mémoire : à vérifier avant l'article.
