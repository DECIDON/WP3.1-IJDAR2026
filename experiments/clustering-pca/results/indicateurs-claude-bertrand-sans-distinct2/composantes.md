# Composantes de l'ACP des indicateurs (indicateurs-claude-bertrand-sans-distinct2)

1862 fenêtres (0 de NEM.fr), 4 indicateurs orientés (+ = plus rigide), log(1 + x) pour : Formularité, KL POS, Ponctuation ; centrés-réduits. Kaiser : 2 composante(s), 86.8 % de variance. Signe : somme des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.

| Composante | Poids des indicateurs | Lecture (côté − / côté +) | Groupes côté − | Groupes côté + |
|---|---|---|---|---|
| PC1 (52.9 %) | KL POS +0.63, Ponctuation +0.58, Formularité +0.49, ĥ (Bentz) +0.15 | − moins rigide : POS ordinaires, peu de ponctuation, pas de formule / + plus rigide : POS atypiques, ponctuation dense, formules répétées | hipe2020 (fr, en, de) (-1.2), newseye (fr, fi, sv) (-1.2), letemps-fr (-1.2) | soduco-ref (+3.4), soduco-pero (+3.3), m-popp-printed (+1.1) |
| PC2 (33.8 %) | ĥ (Bentz) +0.78, Formularité +0.45, Ponctuation -0.39, KL POS -0.18 | − vocabulaire varié, pas de formule, ponctuation dense / + vocabulaire répétitif, formules répétées, peu de ponctuation | newseye (fr, fi, sv) (-1.2), ajmc (fr, en, de) (-1.1), soduco-pero (-0.9) | e-ner (+1.9), old-bailey (+1.6), m-popp-printed (+1.6) |
| PC3 (9.5 %) | Formularité -0.74, ĥ (Bentz) +0.57, KL POS +0.34, Ponctuation +0.12 | − formules répétées, vocabulaire varié, POS ordinaires / + pas de formule, vocabulaire répétitif, POS atypiques | m-popp-handwritten (-0.9), basel (-0.8), m-popp-printed (-0.6) | litbank (+0.7), letemps-fr (+0.4), e-ner (+0.4) |
| PC4 (3.8 %) | Ponctuation +0.70, KL POS -0.67, ĥ (Bentz) +0.22, Formularité -0.03 | − peu de ponctuation, POS atypiques / + ponctuation dense, POS ordinaires | basel (-0.4), m-popp-handwritten (-0.3), e-ner (-0.2) | geoedda (+0.5), m-popp-printed (+0.3), 7romans (+0.2) |
