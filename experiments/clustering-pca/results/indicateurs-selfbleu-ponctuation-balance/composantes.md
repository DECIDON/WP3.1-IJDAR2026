# Composantes de l'ACP des indicateurs (indicateurs-selfbleu-ponctuation-balance)

2100 fenêtres (0 de NEM.fr), 3 indicateurs orientés (+ = plus rigide), log(1 + x) pour : Self-BLEU, Ponctuation ; centrés-réduits. Kaiser : 1 composante(s), 59.6 % de variance. Signe : somme des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.

| Composante | Poids des indicateurs | Lecture (côté − / côté +) | Groupes côté − | Groupes côté + |
|---|---|---|---|---|
| PC1 (59.6 %) | Ponctuation +0.66, Balance phrastique +0.66, Self-BLEU +0.35 | − moins rigide : peu de ponctuation, beaucoup de mots de liaison, peu de reprises / + plus rigide : ponctuation dense, peu de mots de liaison, suites de mots reprises | litbank (-1.1), hipe2020 (fr, en, de) (-1.0), letemps-fr (-1.0) | soduco-ref (+2.8), soduco-pero (+2.7), m-popp-printed (+0.9) |
| PC2 (29.7 %) | Self-BLEU +0.94, Balance phrastique -0.26, Ponctuation -0.23 | − peu de reprises / + suites de mots reprises | newseye (fr, fi, sv) (-1.1), hipe2020 (fr, en, de) (-0.6), letemps-fr (-0.5) | m-popp-handwritten (+1.6), m-popp-printed (+1.5), old-bailey (+1.4) |
| PC3 (10.8 %) | Ponctuation -0.71, Balance phrastique +0.70, Self-BLEU +0.02 | − ponctuation dense, beaucoup de mots de liaison / + peu de ponctuation, peu de mots de liaison | 7romans (-0.5), old-bailey (-0.4), geoedda (-0.4) | m-popp-handwritten (+0.7), e-ner (+0.6), m-popp-printed (+0.3) |
