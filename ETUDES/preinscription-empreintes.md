# Pré-inscription — enrôler les voix sans écouter le débat

**Écrit le 1er septembre 2026, avant toute exécution du regroupement.**
Troisième mesure pré-inscrite du projet.

---

## Le problème

Les empreintes vocales exigent, pour chaque personne, au moins trois extraits
audio dont on sait qu'ils sont d'elle. Personne ne les a marqués, et **je ne
peux pas les marquer** : je n'ai pas accès au signal, je ne peux pas
reconnaître une voix (D-048).

## L'idée qu'on teste

Ne pas reconnaître les voix : les **regrouper**, puis laisser le débat les
nommer lui-même.

1. Découper l'audio selon les segments de la transcription de référence.
2. Calculer une empreinte par segment (ECAPA-TDNN, 192 dimensions, local).
3. Regrouper les segments par similarité, sans savoir qui est qui.
4. Nommer une grappe **seulement** si les patronymes prononcés juste avant ses
   segments désignent massivement la même personne — « Alors Jean-Luc
   Mélenchon, … » précède presque toujours une prise de parole de l'intéressé.

C'est l'usage exact que D-041 autorise pour le signal des noms : **étiqueter
des grappes de diarisation, jamais réécrire le texte**. Et le manifeste de
plateau le dit déjà pour les présentations : « les introductions orientent,
elles ne prouvent pas ».

## Ce qui rend la chose vérifiable sans écouter

Si cinq passages précédés de cinq mentions différentes de « Mélenchon » sont
mutuellement semblables et éloignés des autres grappes, la seule explication
simple est que la même personne parle après chacune. **La cohérence interne
tient lieu de contrôle**, là où je ne peux pas contrôler par l'oreille.

Elle ne prouve pas l'identité : elle prouve la constance. Un animateur qui
parlerait systématiquement quinze secondes après avoir prononcé un nom
produirait la même constance sous le mauvais nom — d'où la vérification humaine
exigée plus bas.

## Paramètres balayés

| Paramètre | Valeurs | Rôle |
|---|---|---|
| distance de regroupement | 0,30 · 0,40 · 0,50 · 0,60 · 0,70 | finesse des grappes |

## Critères, posés d'avance

Une grappe devient une empreinte **seulement si les trois sont vrais** :

1. **Concentration du nom** : un patronyme réunit ≥ 60 % des mentions
   rattachées à la grappe, avec au moins **3 mentions distinctes**.
2. **Cohésion** : similarité interne moyenne ≥ 0,60.
3. **Séparation** : le centroïde est à ≤ 0,50 de similarité de tout autre
   centroïde retenu.

Le banc est **déclaré non concluant** si le regroupement rend moins de 8
grappes pour 14 intervenants : sous-regroupement, les grappes mélangent des
personnes et les taux ne se lisent pas.

Le bootstrap est **déclaré en échec** si moins de 4 des 7 candidats sont
enrôlés. Dans ce cas, le marquage à la main redevient nécessaire et le script
sert alors à préparer les fenêtres à confirmer, pas à conclure.

## Règle de décision

Parmi les distances balayées, on retient celle qui enrôle **le plus de
candidats** en satisfaisant les trois critères. À égalité, la plus petite —
c'est-à-dire le regroupement le plus fin, celui qui mélange le moins.

## Ce que cette mesure ne donne PAS

**Aucune autorité de publication.** Une empreinte enrôlée ainsi porte
`verifie_par_humain: false`, et tant que ce drapeau est faux, une attribution
qui s'appuie dessus ne peut faire naître aucun verdict coloré. La raison est la
même que pour la couche d'accord : mesurer n'est pas être autorisé.

Ce qu'il faudra pour lever ce drapeau : que quelqu'un écoute **un extrait par
voix enrôlée** et confirme le nom. C'est une minute d'écoute par personne, et
c'est irremplaçable — je peux préparer les extraits, je ne peux pas les
valider.

## Angles morts déclarés

- **Aucun détecteur de paroles superposées.** La règle de `consensus.py` —
  la superposition s'abstient d'office — ne peut pas être appliquée. Une
  empreinte calculée sur deux voix mêlées ne ressemble à aucune des deux et
  peut marquer haut contre une troisième personne. C'est le trou le plus
  sérieux de ce montage, et il ne se referme qu'avec un modèle de
  segmentation.
- Les segments viennent de l'ASR, dont les frontières ne sont pas des
  changements de locuteur : un segment à cheval sur deux tours produit une
  empreinte hybride.
- Le canal voyage avec la voix : tout est enregistré sur le même plateau, ce
  qui rapproche artificiellement toutes les empreintes entre elles.
