# Composantes de l'ACP des indicateurs (indicateurs-claude-bertrand-sans-distinct2)

1862 fenêtres (0 de NEM.fr), 4 indicateurs orientés (+ = plus rigide), log(1 + x) pour : Formularité, KL POS, Ponctuation ; centrés-réduits. Kaiser : 2 composante(s), 86.8 % de variance. Signe : somme des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.

| Composante | Poids des indicateurs | Lecture (côté − / côté +) | Groupes côté − | Groupes côté + |
|---|---|---|---|---|
| PC1 (52.5 %) | KL POS +0.64, Ponctuation +0.59, Formularité +0.48, ĥ (Bentz) +0.11 | − moins rigide : POS ordinaires, peu de ponctuation, pas de formule / + plus rigide : POS atypiques, ponctuation dense, formules répétées | hipe2020 (fr, en, de) (-1.2), letemps-fr (-1.2), newseye (fr, fi, sv) (-1.1) | soduco-ref (+3.4), soduco-pero (+3.4), m-popp-printed (+1.0) |
| PC2 (34.4 %) | ĥ (Bentz) +0.78, Formularité +0.48, Ponctuation -0.37, KL POS -0.16 | − vocabulaire varié, pas de formule, ponctuation dense / + vocabulaire répétitif, formules répétées, peu de ponctuation | newseye (fr, fi, sv) (-1.2), ajmc (fr, en, de) (-1.1), soduco-pero (-0.9) | e-ner (+1.8), m-popp-printed (+1.7), old-bailey (+1.6) |
| PC3 (9.4 %) | Formularité -0.74, ĥ (Bentz) +0.57, KL POS +0.34, Ponctuation +0.12 | − formules répétées, vocabulaire varié, POS ordinaires / + pas de formule, vocabulaire répétitif, POS atypiques | m-popp-handwritten (-0.9), basel (-0.8), m-popp-printed (-0.6) | litbank (+0.7), letemps-fr (+0.4), e-ner (+0.4) |
| PC4 (3.8 %) | Ponctuation +0.71, KL POS -0.67, ĥ (Bentz) +0.21, Formularité -0.03 | − peu de ponctuation, POS atypiques / + ponctuation dense, POS ordinaires | basel (-0.4), m-popp-handwritten (-0.3), e-ner (-0.2) | geoedda (+0.5), m-popp-printed (+0.3), 7romans (+0.2) |
