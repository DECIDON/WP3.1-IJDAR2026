# Formularité, Self-BLEU et diversité lexicale

Généré par `robustness.py`. η² dataset : séparation des datasets. η² langue : part de la variance due à la langue dans un même corpus multilingue (devrait être nulle). ρ : Spearman entre fenêtres.

## Fenêtres de 100 mots

| mesure | η² dataset | η² langue newseye / hipe2020 / ajmc | fenêtres à 0 (%) | ρ formularité | ρ name_density | ρ typo | ρ balance |
|---|---|---|---|---|---|---|---|
| formularité (`F`) | 0.69 | 0.02 / 0.24 / 0.13 | 36.2 | 1.0 | 0.59 | 0.34 | -0.33 |
| Self-BLEU, texte brut (`sbleu_raw`) | 0.76 | 0.17 / 0.11 / 0.1 | 0.0 | 0.79 | 0.37 | 0.27 | -0.19 |
| Self-BLEU, noms et nombres masqués (`sbleu_masked`) | 0.75 | 0.11 / 0.31 / 0.11 | 0.0 | 0.87 | 0.73 | 0.49 | -0.42 |
| précision des 4-grammes masqués (`p4_masked`) | 0.73 | 0.06 / 0.26 / 0.08 | 12.7 | 0.88 | 0.75 | 0.51 | -0.46 |
| MATTR (50 mots) (`mattr`) | 0.5 | 0.41 / 0.34 / 0.29 | 0.0 | -0.22 | 0.04 | 0.16 | -0.19 |
| ĥ (Bentz) (`h_rate`) | 0.54 | 0.44 / 0.37 / 0.33 | 0.0 | -0.27 | 0.04 | 0.21 | -0.21 |
| Distinct-2 (`distinct2`) | 0.36 | 0.17 / 0.13 / 0.17 | 0.0 | -0.33 | -0.13 | 0.04 | 0.0 |

## Fenêtres de 300 mots

| mesure | η² dataset | η² langue newseye / hipe2020 / ajmc | fenêtres à 0 (%) | ρ formularité | ρ name_density | ρ typo | ρ balance |
|---|---|---|---|---|---|---|---|
| formularité (`F`) | 0.82 | 0.02 / 0.32 / 0.01 | 22.4 | 1.0 | 0.68 | 0.38 | -0.38 |
| Self-BLEU, texte brut (`sbleu_raw`) | 0.86 | 0.25 / 0.28 / 0.22 | 0.0 | 0.87 | 0.49 | 0.31 | -0.24 |
| Self-BLEU, noms et nombres masqués (`sbleu_masked`) | 0.84 | 0.17 / 0.39 / 0.32 | 0.0 | 0.93 | 0.76 | 0.49 | -0.44 |
| précision des 4-grammes masqués (`p4_masked`) | 0.83 | 0.09 / 0.35 / 0.26 | 3.3 | 0.92 | 0.79 | 0.51 | -0.49 |
| MATTR (50 mots) (`mattr`) | 0.61 | 0.64 / 0.52 / 0.21 | 0.0 | -0.32 | -0.06 | 0.1 | -0.18 |
| ĥ (Bentz) (`h_rate`) | 0.69 | 0.74 / 0.52 / 0.12 | 0.0 | -0.49 | -0.07 | 0.15 | -0.17 |
| Distinct-2 (`distinct2`) | 0.66 | 0.39 / 0.37 / 0.1 | 0.0 | -0.63 | -0.3 | -0.01 | 0.08 |
