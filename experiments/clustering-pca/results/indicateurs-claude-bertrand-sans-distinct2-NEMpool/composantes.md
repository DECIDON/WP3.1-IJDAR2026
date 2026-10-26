# Composantes de l'ACP des indicateurs (indicateurs-claude-bertrand-sans-distinct2-NEMpool)

1986 fenêtres (124 de NEM.fr), 4 indicateurs orientés (+ = plus rigide), log(1 + x) pour la formularité, la KL et la ponctuation, centrés-réduits. Kaiser : 2 composante(s), 84.6 % de variance. Signe : somme des poids ≥ 0 ; une composante dont tous les poids ont le même signe est un axe de rigidité commun aux indicateurs, sinon elle OPPOSE des indicateurs censés aller dans le même sens.

| Composante | Poids des indicateurs | Groupes côté − | Groupes côté + |
|---|---|---|---|
| PC1 (51.8 %) | KL POS +0.62, Ponctuation +0.57, Formularité (NEM.fr : réf. commune) +0.52, ĥ (Bentz) +0.16 | NEM.fr spoken (-2.6), NEM.fr tweets (-1.9), NEM.fr encyclopedia (-1.5) | soduco-ref (+3.4), soduco-pero (+3.3), m-popp-printed (+1.2) |
| PC2 (32.9 %) | ĥ (Bentz) +0.80, Formularité (NEM.fr : réf. commune) +0.41, Ponctuation -0.41, KL POS -0.17 | newseye (fr, fi, sv) (-1.2), ajmc (fr, en, de) (-1.1), soduco-pero (-0.9) | NEM.fr spoken (+1.9), e-ner (+1.9), old-bailey (+1.6) |
| PC3 (9.8 %) | Formularité (NEM.fr : réf. commune) -0.74, ĥ (Bentz) +0.50, KL POS +0.45, Ponctuation +0.04 | m-popp-handwritten (-0.9), m-popp-printed (-0.7), basel (-0.7) | NEM.fr politique (+1.0), NEM.fr spoken (+1.0), NEM.fr biomedical (+0.9) |
| PC4 (5.6 %) | Ponctuation +0.71, KL POS -0.62, ĥ (Bentz) +0.30, Formularité (NEM.fr : réf. commune) -0.13 | NEM.fr spoken (-3.0), NEM.fr tweets (-0.7), basel (-0.5) | geoedda (+0.4), NEM.fr prose (+0.4), 7romans (+0.2) |
