# Formularité, Self-BLEU et diversité lexicale

Généré par `robustness.py`. η² dataset : séparation des datasets. η² langue : part de la variance due à la langue dans un même corpus multilingue (devrait être nulle). ρ : Spearman entre fenêtres.

## Fenêtres de 100 mots

| mesure | η² dataset | η² langue newseye / hipe2020 / ajmc | fenêtres à 0 (%) | ρ formularité | ρ name_density | ρ typo | ρ balance |
|---|---|---|---|---|---|---|---|
| formularité (`F`) | 0.69 | 0.02 / 0.24 / 0.13 | 36.1 | 1.0 | 0.59 | 0.34 | -0.34 |
| Self-BLEU, texte brut (`sbleu_raw`) | 0.76 | 0.17 / 0.11 / 0.1 | 0.0 | 0.79 | 0.37 | 0.27 | -0.19 |
| Self-BLEU, noms et nombres masqués (`sbleu_masked`) | 0.75 | 0.11 / 0.31 / 0.11 | 0.0 | 0.88 | 0.73 | 0.49 | -0.42 |
| précision des 4-grammes masqués (`p4_masked`) | 0.73 | 0.06 / 0.26 / 0.08 | 12.7 | 0.88 | 0.75 | 0.51 | -0.46 |
| Self-BLEU, tokens spaCy sans signes (`sbleu_nopunct`) | 0.68 | 0.26 / 0.28 / 0.13 | 0.0 | 0.63 | 0.13 | -0.09 | 0.08 |
| Self-BLEU, mots entiers (découpage aux espaces) (`sbleu_words`) | 0.68 | 0.33 / 0.21 / 0.16 | 0.0 | 0.61 | 0.12 | -0.1 | 0.1 |
| MATTR (50 mots) (`mattr`) | 0.49 | 0.41 / 0.34 / 0.29 | 0.0 | -0.21 | 0.05 | 0.17 | -0.2 |
| ĥ (Bentz) (`h_rate`) | 0.53 | 0.44 / 0.37 / 0.33 | 0.0 | -0.27 | 0.04 | 0.22 | -0.22 |
| Distinct-2 (`distinct2`) | 0.36 | 0.17 / 0.13 / 0.17 | 0.0 | -0.33 | -0.13 | 0.05 | -0.01 |

**Test du mélange, 100 mots.** ρ médian à l'intérieur d'un dataset entre le Self-BLEU brut (ou la formularité) et : 1-grammes, 2-grammes, 3-grammes, 4-grammes, Self-BLEU, mots mélangés, formularité. Le Self-BLEU sur mots mélangés vaut en médiane 0.15 fois l'original.

| | 1-grammes | 2-grammes | 3-grammes | 4-grammes | Self-BLEU, mots mélangés | formularité |
|---|---|---|---|---|---|---|
| Self-BLEU brut | 0.49 | 0.77 | 0.95 | 0.95 | 0.31 | 0.41 |
| formularité | 0.1 | 0.26 | 0.35 | 0.42 | 0.12 | — |

**Test de tokenisation, 100 mots.** Médianes par langue dans les corpus multilingues ; ρ médian à l'intérieur d'un dataset avec le Self-BLEU spaCy et avec la densité de noms propres.

| | Self-BLEU, texte brut | Self-BLEU, tokens spaCy sans signes | Self-BLEU, mots entiers (découpage aux espaces) | formularité |
|---|---|---|---|---|
| ajmc-de | 10.0 | 3.0 | 3.0 | 8.8 |
| ajmc-en | 16.3 | 5.4 | 5.3 | 3.2 |
| ajmc-fr | 14.0 | 4.1 | 3.3 | 5.8 |
| hipe2020-de | 4.4 | 2.0 | 2.0 | 0.0 |
| hipe2020-en | 5.2 | 4.3 | 4.5 | 4.9 |
| hipe2020-fr | 6.0 | 4.9 | 3.9 | 0.0 |
| newseye-fi | 3.0 | 1.4 | 1.2 | 0.0 |
| newseye-fr | 4.7 | 3.3 | 2.0 | 0.0 |
| newseye-sv | 3.5 | 1.7 | 1.6 | 0.0 |
| ρ interne avec le Self-BLEU spaCy | 1.0 | 0.8 | 0.71 | — |
| ρ interne avec la densité de noms | -0.01 | -0.1 | -0.11 | 0.31 |

## Fenêtres de 300 mots

| mesure | η² dataset | η² langue newseye / hipe2020 / ajmc | fenêtres à 0 (%) | ρ formularité | ρ name_density | ρ typo | ρ balance |
|---|---|---|---|---|---|---|---|
| formularité (`F`) | 0.82 | 0.02 / 0.32 / 0.01 | 22.4 | 1.0 | 0.68 | 0.38 | -0.37 |
| Self-BLEU, texte brut (`sbleu_raw`) | 0.85 | 0.25 / 0.28 / 0.22 | 0.0 | 0.87 | 0.49 | 0.31 | -0.24 |
| Self-BLEU, noms et nombres masqués (`sbleu_masked`) | 0.84 | 0.17 / 0.39 / 0.32 | 0.0 | 0.92 | 0.76 | 0.49 | -0.44 |
| précision des 4-grammes masqués (`p4_masked`) | 0.83 | 0.09 / 0.35 / 0.26 | 3.3 | 0.92 | 0.79 | 0.51 | -0.49 |
| Self-BLEU, tokens spaCy sans signes (`sbleu_nopunct`) | 0.78 | 0.37 / 0.45 / 0.1 | 0.0 | 0.73 | 0.26 | -0.02 | 0.01 |
| Self-BLEU, mots entiers (découpage aux espaces) (`sbleu_words`) | 0.79 | 0.43 / 0.37 / 0.12 | 0.0 | 0.72 | 0.26 | -0.03 | 0.02 |
| MATTR (50 mots) (`mattr`) | 0.6 | 0.64 / 0.52 / 0.21 | 0.0 | -0.31 | -0.04 | 0.12 | -0.2 |
| ĥ (Bentz) (`h_rate`) | 0.69 | 0.74 / 0.52 / 0.12 | 0.0 | -0.48 | -0.05 | 0.17 | -0.19 |
| Distinct-2 (`distinct2`) | 0.64 | 0.39 / 0.37 / 0.1 | 0.0 | -0.61 | -0.25 | 0.04 | 0.03 |

**Test du mélange, 300 mots.** ρ médian à l'intérieur d'un dataset entre le Self-BLEU brut (ou la formularité) et : 1-grammes, 2-grammes, 3-grammes, 4-grammes, Self-BLEU, mots mélangés, formularité. Le Self-BLEU sur mots mélangés vaut en médiane 0.11 fois l'original.

| | 1-grammes | 2-grammes | 3-grammes | 4-grammes | Self-BLEU, mots mélangés | formularité |
|---|---|---|---|---|---|---|
| Self-BLEU brut | 0.57 | 0.76 | 0.92 | 0.95 | 0.26 | 0.44 |
| formularité | 0.15 | 0.21 | 0.43 | 0.46 | 0.15 | — |

**Test de tokenisation, 300 mots.** Médianes par langue dans les corpus multilingues ; ρ médian à l'intérieur d'un dataset avec le Self-BLEU spaCy et avec la densité de noms propres.

| | Self-BLEU, texte brut | Self-BLEU, tokens spaCy sans signes | Self-BLEU, mots entiers (découpage aux espaces) | formularité |
|---|---|---|---|---|
| ajmc-de | 8.3 | 2.0 | 2.0 | 3.8 |
| ajmc-en | 16.1 | 7.1 | 7.1 | 3.6 |
| ajmc-fr | 13.9 | 7.0 | 4.9 | 3.1 |
| hipe2020-de | 3.5 | 2.0 | 2.1 | 0.0 |
| hipe2020-en | 7.4 | 5.1 | 5.3 | 3.5 |
| hipe2020-fr | 9.2 | 6.8 | 3.4 | 1.1 |
| newseye-fi | 2.2 | 1.3 | 0.7 | 0.0 |
| newseye-fr | 6.0 | 2.8 | 2.1 | 1.1 |
| newseye-sv | 2.9 | 1.7 | 1.6 | 0.0 |
| ρ interne avec le Self-BLEU spaCy | 1.0 | 0.79 | 0.67 | — |
| ρ interne avec la densité de noms | 0.01 | -0.14 | -0.03 | 0.42 |
