# Pré-inscription — couche d'accord entre transcriptions

**Écrit le 1er septembre 2026, avant d'avoir exécuté le banc.**
C'est la première mesure pré-inscrite du projet. `METHODE.md` §1 était « non
tenu » depuis le début ; ce document existe pour que le §1 cesse d'être une
intention.

Ce qui suit — la question, les cas témoins, les seuils de succès et la décision
qui suivra chaque issue — est figé avant tout résultat. La transcription
faster-whisper du débat était encore en cours d'écriture au moment de la
rédaction : je ne sais pas ce qu'elle dit aux endroits testés.

---

## Question

La couche d'accord entre transcriptions (`pythie/media/transcripts.py`)
empêche-t-elle la citation fabriquée du 31/08 **sans** bloquer les énoncés que
deux transcriptions indépendantes rapportent effectivement de la même façon ?

Les deux moitiés comptent. Une couche qui bloque tout satisfait trivialement la
première et ne vaut rien : c'est le §5 de `METHODE.md` — la couverture se lit
avant l'exactitude.

## Matériel

- **Transcription principale** : sous-titres YouTube, `data/laref2026.json`,
  famille `youtube`.
- **Témoin** : `faster-whisper-large-v3`, famille `whisper`, produit le 01/09
  par `scripts/transcribe.py` sur le même audio.
- **Fenêtre** : 22 à 32 minutes, celle de la passe complète du 01/09.
- Les deux familles sont distinctes : c'est la condition posée en D-047.

## Cas témoins

Une métrique qui rend zéro n'est pas une preuve d'absence (`METHODE.md` §11).
Avant de conclure quoi que ce soit, la couche doit se déclencher là où l'on
sait qu'elle doit se déclencher, et se taire là où l'on sait qu'elle doit se
taire.

**T+ — elle doit se déclencher.** Bloc 1592,1–1616,1 s des sous-titres :

> « Je vous cite de au feu 600 millions de dettes françaises. »

C'est la phrase qui a reçu `false` à 99 % le 31/08. Le texte est corrompu.
**Succès : statut ≠ `confirmed`.** Échec : la couche confirme, et elle ne sert
à rien.

**T− — elle doit se taire.** Bloc 1472,2–1495,8 s :

> « nous sommes titulaires de trois records, 45,3 % de prélèvement […]
> 57,3 % de dépenses »

Ce sont les deux valeurs sur lesquelles le POC 1 a rendu ses verdicts sourcés.
**Succès : statut `confirmed`.**

**Réserve déclarée d'avance sur T−.** Si faster-whisper a entendu d'autres
chiffres à cet endroit, une non-confirmation est le **comportement correct** :
elle signifierait que ces valeurs n'ont jamais été corroborées, et donc que les
verdicts publiés du 01/09 reposaient sur une seule oreille. Dans ce cas le cas
T− est requalifié et publié comme tel — il ne sera pas remplacé par un autre
cas plus favorable, et le banc ne sera pas relancé jusqu'à ce qu'il passe.

## Ce qui est balayé

| Paramètre | Valeurs balayées | Rôle |
|---|---|---|
| `pad` | 5, 10, 20, 30, 45 s | tolérance d'alignement temporel |
| `min_anchor` | 0,0 · 0,1 · 0,2 · 0,35 · 0,5 | ancrage lexical exigé autour du chiffre |

25 combinaisons. Aucune n'est privilégiée d'avance.

## Critères de succès, posés d'avance

1. **T+ non confirmé** — éliminatoire. Un réglage qui confirme la bouillie
   d'ASR est disqualifié quelle que soit sa couverture.
2. **Couverture ≥ 30 %** des énoncés porteurs de chiffre dans la fenêtre. Ce
   nombre est une opinion posée avant la mesure, pas un résultat : il dit
   seulement qu'en dessous, la couche coûte plus qu'elle ne rapporte et le
   défaut est à chercher dans l'alignement, pas dans le seuil.
3. **Interprétabilité** : au moins 20 énoncés porteurs de chiffre dans la
   fenêtre. En dessous, les taux ne se lisent pas et le banc est déclaré non
   concluant.

## Règle de décision, posée d'avance

Parmi les réglages qui satisfont 1 et 2, on retient **le plus petit `pad` et le
plus grand `min_anchor`** : le plus exigeant, celui qui offre le moins de place
à une correspondance fortuite. À couverture égale, on ne préfère jamais le
réglage le plus généreux.

**Si aucun réglage ne satisfait 1 et 2 :** la couche n'est pas branchée sur la
publication. On publie le banc, on dit pourquoi, et le blocage total de D-044
reste en vigueur. Aucun seuil ne sera déplacé après coup pour faire passer un
cas déplaisant — c'est exactement le geste consigné dans `METHODE.md` §2 comme
la faute la plus grave du projet.

---

## Amendements, datés et motivés

Un protocole pré-inscrit peut être amendé ; il ne peut pas l'être en silence.

**A-1 — 01/09, après la première exécution : la fenêtre passe à tout le débat.**
La fenêtre 22–32 min ne contient que 13 énoncés porteurs de chiffre, sous le
seuil de 20 posé au critère 3 : le banc s'y déclare lui-même non concluant.
Le débat entier en contient 102. Les cas témoins, les valeurs balayées, les
seuils et la règle de décision restent inchangés — seule la population s'élargit,
et elle s'élargit à **tout** le matériel disponible, ce qui exclut de choisir
une fenêtre favorable. Les deux exécutions sont publiées
(`data/banc_accord/resultat.json` et `resultat_integral.json`).

**A-2 — 01/09 : deux défauts d'instrument corrigés, mesure relancée.**
Les millésimes suivis d'une ponctuation (« en 2024, », « jusqu'à 2028. ») étaient
lus comme des quantités à corroborer, et le dénominateur du banc comptait des
énoncés ne portant qu'une année. Les deux défauts ont été trouvés en lisant la
liste des blocages, pas en lisant le taux. Corrigés, puis tout relancé. Aucun
seuil, aucun cas témoin, aucune règle de décision n'a été modifié.

**Ce qui n'a pas été fait, et qui est le point important.** Le cas T+ échoue à
tous les réglages. Il n'a pas été remplacé, et aucun autre cas n'a été promu à
sa place — un cas témoin choisi après avoir vu qu'il passe ne démontre rien.
La règle de décision a été appliquée telle qu'écrite : aucun réglage retenu,
donc la couche ne débloque rien.

## Ce que ce banc ne mesure pas

- Il ne dit **pas** laquelle des deux transcriptions a raison. Il ne dispose
  d'aucune vérité de terrain — je n'ai pas accès au signal audio (D-048). Il
  mesure un désaccord, pas une erreur.
- Il ne mesure **pas** le taux de faux rouges. Il mesure combien de chiffres
  deux oreilles indépendantes rapportent pareil.
- Une confirmation n'est **pas** une garantie que la phrase est bien
  transcrite : les deux modèles peuvent se tromper de la même façon sur les
  mots autour d'un chiffre juste.
