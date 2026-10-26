# Composantes de l'ACP des indicateurs (indicateurs-claude-bertrand-sans-distinct2)

2100 fenêtres (0 de NEM.fr), 4 indicateurs orientés (+ = plus rigide), log(1 + x) pour : Formularité, KL POS, Ponctuation ; centrés-réduits. Kaiser : 2 composante(s), 79.9 % de variance. Signe : somme des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.

| Composante | Poids des indicateurs | Lecture (côté − / côté +) | Groupes côté − | Groupes côté + |
|---|---|---|---|---|
| PC1 (49.7 %) | KL POS +0.64, Ponctuation +0.61, Formularité +0.46, ĥ (Bentz) +0.03 | − moins rigide : POS ordinaires, peu de ponctuation, pas de formule / + plus rigide : POS atypiques, ponctuation dense, formules répétées | letemps-fr (-1.3), hipe2020 (fr, en, de) (-1.2), newseye (fr, fi, sv) (-1.1) | soduco-ref (+3.3), soduco-pero (+3.0), m-popp-printed (+0.7) |
| PC2 (30.2 %) | ĥ (Bentz) +0.84, Formularité +0.43, Ponctuation -0.33, KL POS -0.04 | − vocabulaire varié, pas de formule, ponctuation dense / + vocabulaire répétitif, formules répétées, peu de ponctuation | ajmc (fr, en, de) (-1.2), newseye (fr, fi, sv) (-1.0), soduco-pero (-0.3) | e-ner (+1.7), old-bailey (+1.4), m-popp-handwritten (+1.3) |
| PC3 (14.5 %) | Formularité -0.77, ĥ (Bentz) +0.49, KL POS +0.36, Ponctuation +0.18 | − formules répétées, vocabulaire varié, POS ordinaires / + pas de formule, vocabulaire répétitif, POS atypiques | m-popp-printed (-1.3), m-popp-handwritten (-1.1), basel (-0.6) | litbank (+0.7), soduco-ref (+0.5), soduco-pero (+0.5) |
| PC4 (5.6 %) | Ponctuation +0.70, KL POS -0.68, ĥ (Bentz) +0.25, Formularité +0.00 | − peu de ponctuation, POS atypiques / + ponctuation dense, POS ordinaires | m-popp-handwritten (-0.3), basel (-0.3), e-ner (-0.2) | geoedda (+0.5), 7romans (+0.2), m-popp-printed (+0.1) |
