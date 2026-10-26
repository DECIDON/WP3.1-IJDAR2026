# text-rigidity

Indicateurs de rigidité textuelle, calculés sur le texte seul (sans annotation d'entités), sur des
fenêtres d'une centaine de mots. Ils servent à tester la sensibilité des modèles de reconnaissance
d'entités nommées au caractère plus ou moins rigide d'un texte (projet IJDAR 2026, ANR DECIDON).

La définition des indicateurs, leur justification et leur validation sur les datasets du projet sont
dans le rapport [`experiments/rigidity-indicators/indicateurs-rigidite.md`](../experiments/rigidity-indicators/indicateurs-rigidite.md).

## Indicateurs

| indicateur | fonction | module | signe de rigidité |
|---|---|---|---|
| formatage typographique | `compute_typographic_formatting` | `typography` | valeur haute |
| balance phrastique | `compute_phrastic_balance` | `phrastic` | valeur négative |
| formulaicité : Self-BLEU (Zhu et al. 2018) | `FormularityReference`, `compute_self_bleu` | `formularity` | valeur haute |
| formularité (complément lisible du Self-BLEU) | `FormularityReference`, `compute_formularity` | `formularity` | valeur haute |
| densité de noms propres (covariable) | `compute_name_density` | `phrastic` | aucun |
| segments averbaux (contrôle) | `compute_verbless_rate` | `phrastic` | valeur haute |

Conservés pour comparaison avec les analyses précédentes, mais non retenus : divergence KL des POS
(`divergence`), Distinct-N (`lexical`), ΔH de Bentz et al. (`entropy`), perplexité KenLM (`perplexity`).
`get_all_metrics` calcule d'un coup les indicateurs d'une fenêtre, hors Self-BLEU et formularité.

## Installation

Depuis la racine du dépôt (workspace uv) :

```bash
uv sync --all-packages
```

Ou seul, dans un autre projet : `pip install ./text-rigidity` (ajouter `[perplexity]` pour KenLM).

Les modèles spaCy (`fr_core_news_sm`, `en_core_web_sm`…, voir `SPACY_MODELS`) sont téléchargés au
premier appel de `get_nlp` s'ils ne sont pas installés. La balance phrastique et la divergence KL
téléchargent au premier appel le treebank UD de référence de la langue (PUD, depuis GitHub).

## Exemple

```python
from text_rigidity import (
    FormularityReference, compute_formularity, compute_name_density, compute_self_bleu,
    compute_phrastic_balance, compute_typographic_formatting, get_nlp,
)

text = "Martin, épicier, r. de Seine, 12. — Durand (J.-B.), md de vins, quai des Ormes, 4."
doc = get_nlp("fr")(text)  # une seule analyse spaCy, réutilisée par les indicateurs

compute_typographic_formatting(text)["typo_total"]  # marques pour 100 mots
compute_phrastic_balance(text, "fr", doc)            # < 0 : moins de mots de liaison que la prose
compute_name_density(text, "fr", doc)                # % de noms propres

# Self-BLEU et formularité : référence tirée des autres documents du même dataset
reference = FormularityReference([(doc_id, doc_text) for doc_id, doc_text in documents], lang="fr")
compute_self_bleu(text, reference, doc_id="doc-1", lang="fr", doc=doc)    # 0 à 100
compute_formularity(text, reference, doc_id="doc-1", lang="fr", doc=doc)  # % du texte dans des gabarits
# critère de dispersion (lexical bundles) : gabarits présents dans au moins 3 documents de la référence
compute_formularity(text, reference, doc_id="doc-1", lang="fr", doc=doc, min_docs=3)
```

À l'échelle locale, `exclude_spans=[(start, end)]` retire l'entité cible des comptages après
l'étiquetage du texte entier.

## Tests

```bash
uv run pytest text-rigidity                  # tous les tests
uv run pytest text-rigidity -m "not network" # sans téléchargement de treebank UD
```
