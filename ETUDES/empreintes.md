# Empreintes vocales — enrôler sans écouter

Troisième mesure pré-inscrite. Protocole figé avant exécution :
`ETUDES/preinscription-empreintes.md`. Mesuré le 1er septembre 2026.

**Résultat court : le bootstrap échoue selon le critère posé d'avance, et il
échoue de peu.** Trois candidats enrôlés, quatre exigés. Ce qui manque tient en
quelques minutes d'écoute humaine, et le nécessaire est préparé.

---

## Le montage

Je ne peux pas reconnaître une voix : je n'ai pas accès au signal (D-048). Mais
je peux **regrouper** les voix, et laisser le débat les nommer.

1. 1 282 segments d'au moins 3 s, un vecteur chacun (ECAPA-TDNN, 192
   dimensions, local, GPU).
2. Regroupement par similarité, sans savoir qui est qui.
3. Une grappe reçoit un nom si les patronymes prononcés **juste avant ses
   prises de parole** désignent massivement la même personne.

C'est l'usage que D-041 autorise pour le signal des noms : étiqueter des
grappes, jamais réécrire du texte.

## Le regroupement fonctionne, et c'est le vrai résultat

À une distance de 0,40, huit grappes concentrent 86 % de la parole :

```
14 %  12 %  12 %  11 %  11 %  10 %  9 %  7 %
```

C'est la forme d'un plateau : sept candidats et une animatrice. Les empreintes
séparent bien les voix — ce qui n'allait pas de soi sur un enregistrement de
salle, où le canal est commun à tous et rapproche artificiellement les voix.

Et les sept plus grosses grappes reçoivent **sept noms différents** :

| Grappe | Nom suggéré | Part des mentions | Durée |
|---|---|---|---|
| 15 | Jean-Luc Mélenchon | 57 % | 20 min |
| 3 | Raphaël Glucksmann | 64 % | 18 min |
| 2 | Bruno Retailleau | 64 % | 18 min |
| 0 | Marine Le Pen | 67 % | 17 min |
| 1 | Édouard Philippe | 50 % | 18 min |
| 4 | Marine Tondelier | 45 % | 16 min |
| 8 | Gabriel Attal | 53 % | 13 min |

**Une bijection entre les sept plus grosses grappes et les sept candidats.**
Le hasard ne produit pas cela.

## Et pourtant : échec, selon la règle écrite d'avance

Le critère pré-inscrit exige qu'un patronyme réunisse **≥ 60 %** des mentions
d'une grappe. Trois y parviennent — Glucksmann, Retailleau, Le Pen — et le
protocole exigeait quatre candidats. **Bootstrap déclaré en échec.**

La bijection ci-dessus est un argument plus fort que le critère des 60 %, et je
ne l'utilise pas : elle n'a pas été pré-inscrite. S'en servir aujourd'hui pour
déclarer un succès serait choisir la mesure après avoir vu laquelle arrange —
exactement ce que la pré-inscription existe pour empêcher. Elle sera
pré-inscrite pour la prochaine fois, ou elle ne servira pas.

## Deux défauts d'instrument, corrigés en route

Aucun des deux n'était visible dans un taux ; les deux se sont vus en lisant la
liste des grappes.

**1. Une mention votait pour dix grappes.** La première version faisait voter
chaque patronyme pour toutes les grappes présentes dans les 90 secondes
suivantes. Chaque nom se dispersait, chaque grappe recevait des voix de dix
noms : **aucun patronyme ne pouvait atteindre 60 %, quel que soit le débat**.
Le critère était insatisfaisable par construction — le banc aurait échoué sur
du matériel parfait.

Correctif : une mention = une voix, pour la première prise de parole d'au moins
dix secondes **qui n'est pas celle de la personne qui prononce le nom**. Celui
qui dit « Alors Jean-Luc Mélenchon, … » pose la question ; il n'est jamais
l'intéressé. Mesuré : Retailleau passe de 57 % à 75 %, Glucksmann de 58 % à
88 %.

**2. Une candidate était invisible.** Le patronyme était pris comme « le
dernier mot du nom » : « Marine Le Pen » se réduisait à « pen », trois lettres,
écarté par le garde-fou de longueur. **Aucune de ses prises de parole ne
pouvait être nommée**, et une grappe de 17 minutes portait le mauvais nom à
50 %. Correctif : le patronyme est tout ce qui suit le prénom. Les mentions
passent de 128 à 164, et Marine Le Pen apparaît avec 67 % et une cohésion de
0,85 — la meilleure des trois retenues.

C'est la quatrième fois en deux jours qu'un défaut se trouve en lisant ce qu'un
nombre recouvre, et jamais dans le nombre lui-même.

## Ce qui reste, et qui ne peut pas être fait sans oreille

Le script écrit `data/empreintes/confirmation.yaml` : 14 grappes, avec pour
chacune le nom suggéré, la force de la preuve, **trois extraits mp3 découpés**
et trois liens horodatés vers la vidéo.

Confirmer les sept grosses grappes prend quelques minutes. Ensuite :

```bash
scripts/enrol.py … --confirmer data/empreintes/confirmation.yaml
```

et les empreintes sont écrites avec `human_verified: true`.

**Pourquoi cette confirmation n'est pas une formalité.** Le montage prouve la
constance, pas l'identité : une personne qui parlerait systématiquement après
avoir prononcé un nom produirait la même régularité sous la mauvaise étiquette.
Une empreinte fausse n'est pas une erreur de plus, c'est une citation attribuée
à quelqu'un qui ne l'a pas prononcée — la faute que tout le projet existe pour
empêcher.

D'où le drapeau `human_verified` sur chaque empreinte, et la règle qui va avec :
tant qu'il est faux, aucune attribution issue de cette empreinte ne peut porter
un verdict coloré.

## Angles morts, déclarés d'avance et toujours ouverts

- **Aucun détecteur de paroles superposées.** La règle de `consensus.py` — la
  superposition s'abstient d'office — ne peut pas être appliquée. C'est le trou
  le plus sérieux de ce montage : une empreinte calculée sur deux voix mêlées
  ne ressemble à aucune des deux et peut marquer haut contre une troisième
  personne. Il ne se referme qu'avec un modèle de segmentation (pyannote, sous
  licence à accepter).
- Les frontières de segments viennent de l'ASR, qui ne coupe pas aux
  changements de locuteur. Un segment à cheval sur deux tours produit une
  empreinte hybride.
- Tout est enregistré sur le même plateau : le canal commun rapproche toutes
  les empreintes, ce qui rend le critère de séparation plus sévère qu'il n'y
  paraît.
