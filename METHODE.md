# Méthode

Le mot d'ordre du projet est **scientifique**. Ce document en fait un
engagement vérifiable plutôt qu'une déclaration d'intention : il liste ce que
cela impose, et **où le projet ne le tient pas encore**.

Un document de méthode qui ne nomme que ses réussites n'est pas un document de
méthode.

---

## 1. Pré-inscription

**L'engagement.** La question, les critères de succès et la décision qui suivra
sont écrits **avant** de regarder le moindre résultat. Sinon on règle les
paramètres sur la cible et on appelle ça une validation.

**État : tenu une fois, le 01/09/2026.** `ETUDES/preinscription-accord.md` fixe
la question, deux cas témoins, les valeurs balayées, les seuils de succès et la
règle de décision — avant exécution du banc d'accord entre transcriptions.

Et la première mesure pré-inscrite a immédiatement servi à quelque chose : le
cas témoin positif a **échoué**, parce que sa prémisse était fausse. Sans
pré-inscription, j'aurais réglé un paramètre jusqu'à ce que ce cas passe, et
j'aurais publié un réglage ajusté contre un cas que j'avais mal lu. Résultats
dans `ETUDES/accord-transcriptions.md`.

**Ce qui reste** : les autres mesures du projet — seuils de verdict, seuils
d'empreinte vocale — n'ont toujours aucune pré-inscription. Une sur sept.

---

## 2. Degrés de liberté déclarés et balayés

**L'engagement.** Tout paramètre réglable est déclaré comme tel, et sa valeur
est **balayée**, jamais choisie après avoir vu le résultat.

**État : non tenu, et c'est le point le plus faible du projet.**

Les seuils suivants ont été posés à l'estime et rédigés avec l'assurance de
règles fondées :

| Paramètre | Valeur | Fondement réel |
|---|---|---|
| Seuil `exact` | écart ≤ 5 % | aucun — intuition |
| Seuil `approximate` | écart ≤ 25 % | aucun — intuition |
| Acceptation d'empreinte vocale | similarité ≥ 0,62 | aucun — intuition |
| Marge entre deux voix | ≥ 0,06 | aucun — intuition |
| Accord entre fenêtres | ≥ 0,75 | choisi après avoir vu qu'un 2-sur-3 passait |
| Fenêtres minimales par segment | 2 | aucun |
| Confiance minimale pour enrichir un profil | 0,75 | aucun |

Le dernier est le pire : **il a été relevé de 0,60 à 0,75 après avoir constaté
qu'un cas déplaisait.** C'est exactement le geste que la méthode interdit.

**Premier balayage publié, le 01/09.** Les deux paramètres de la couche
d'accord ont été balayés sur 25 combinaisons et la courbe est publiée
(`ETUDES/accord-transcriptions.md`). Elle apprend quelque chose qu'aucune
intuition n'avait vu : la tolérance temporelle, dont je me méfiais, ne déplace
rien (76 % à 5 s comme à 45 s) ; l'ancrage lexical, posé au passage, déplace la
couverture de 19 points. Aucune valeur n'a été retenue pour autant — le critère
éliminatoire du protocole n'est satisfait par aucune combinaison.

**Ce qu'il faut** : le même traitement pour les seuils qui comptent — verdict,
empreinte vocale, accord entre fenêtres — sur un jeu étalon qui n'existe pas
encore.

---

## 3. Reproductibilité

**L'engagement.** Même entrée, même version de corpus, même verdict — quel que
soit le jour et l'ordre de traitement.

**État : tenu pour le PROTOCOLE, PAS pour le verdict.**

Tenu :
- appels de vérification sans état, sans historique
- corpus figé pendant un débat, versionné dans git
- seuils appliqués par le programme, pas interprétés par le modèle
- température basse, décodage contraint par schéma

**Non tenu, mesuré le 31/08/2026.** « Or, nous sommes titulaires de trois
records, 45,3 % de prélèvement » a reçu `approximate` à une exécution et
`exact` à la suivante — même corpus, même source, même seuils. Le second
verdict est de surcroît le plus faux : 1,7 point de PIB n'est pas « exact ».

J'avais écrit ici que la reproductibilité était « tenue par construction ».
C'était faux au niveau qui compte. Deux conséquences :

1. Le registre d'affirmations (D-025) détecte ce désaccord **entre occurrences
   d'un même débat**, mais pas entre deux exécutions du même débat. Il faudrait
   rejouer N fois et traiter la dispersion comme une abstention.
2. Tant que ce n'est pas fait, un verdict isolé n'est pas un résultat
   reproductible. C'est une observation unique.

---

## 4. Falsifiabilité

**L'engagement.** Le système doit pouvoir être pris en défaut d'une manière
qu'on sait détecter.

**État : premier échec réel enregistré le 01/09.**

Trois indicateurs sont produits par le code : taux de faux rouges, taux
d'abstention, citations non retrouvées. Aucun n'a encore été mesuré sur de la
matière réelle.

Mais un cas témoin, lui, a été pris en défaut : le T+ du banc d'accord devait
être bloqué, il ne l'a pas été, et l'explication n'était pas un réglage à
corriger — c'était ma lecture de l'incident qui était fausse. Une méthode qui
ne peut pas produire ce genre de résultat ne teste rien.

---

## 5. Couverture avant exactitude

**L'engagement.** Le taux d'abstention se lit **avant** le taux d'accord.

Un système qui ne se prononce que sur 30 % des affirmations et se trompe
rarement n'est pas meilleur qu'un système couvrant 90 % avec un peu moins
d'exactitude : son taux d'accord porte sur une population qu'il a lui-même
choisie.

**État : tenu dans l'ordre d'affichage des métriques** (`run_poc.py`,
`batch.compare`), et éprouvé une fois le 01/09 : le banc d'accord publie sa
couverture avant tout autre chiffre, et le critère éliminatoire du protocole
portait précisément sur elle — une couche qui ne laisse rien passer ne se
trompe jamais, et ne vaut rien.

*Principe repris du banc ASR du projet KaraK.*

---

## 6. Comparaison par paires

**L'engagement.** Seules les affirmations jugées par **les deux** systèmes
comparés entrent dans le score. Comparer deux taux calculés sur deux
populations différentes n'a aucun sens.

**État : implémenté** dans `batch.compare` (intersection des identifiants).

---

## 7. Séparer l'erreur de mesure du phénomène

**L'engagement.** Une erreur de transcription n'est pas une affirmation fausse.
Une voix mal attribuée n'est pas un mensonge.

**État : tenu pour la transcription depuis le 01/09, toujours faux pour la
voix.**

Ce paragraphe affirmait « tenu par conception » alors que la couche d'accord
entre transcriptions **n'existait pas**. Elle existe désormais
(`pythie/media/transcripts.py`, étage 0.5) : un chiffre qu'une seconde famille
d'ASR n'a pas entendu ne reçoit aucun verdict. Mesuré sur le débat entier,
cela retire un quart des énoncés chiffrés.

Reste faux pour la voix : aucune empreinte n'est enrôlée, donc rien n'est
attribué, donc la règle « on ne juge pas un locuteur non identifié » n'est pas
appliquée — elle est contournée par un bouchon qui nomme tout le monde
« locuteur non identifié » et laisse la vérification suivre son cours. C'est
ce défaut-là, et non la transcription, qui a produit le premier rouge du
projet : la phrase était de l'animateur, et D-040 dit que seuls les candidats
sont analysés.

C'est le corollaire central : **une attribution fausse est pire qu'une absence
d'attribution**, parce qu'elle fabrique une citation au lieu de se tromper sur
un verdict.

---

## 8. Aucun résultat sans son incertitude

**L'engagement.** Tout verdict porte une confiance, et la confiance est un axe
**indépendant** du verdict — jamais encodée dans la couleur.

**État : tenu.** `confidence` est un champ distinct, affiché séparément.

**Réserve** : la confiance rendue par le modèle n'est pas calibrée. Un 0,9 ne
signifie pas « juste neuf fois sur dix ». Elle ne le deviendra qu'après mesure
sur le jeu étalon.

---

## 9. Dire ce qu'on ne mesure pas

**L'engagement.** Toute mesure déclare son périmètre et ses angles morts.

**Angles morts connus de Pythie :**

- On ne mesure **pas** si une affirmation est trompeuse, seulement si sa valeur
  correspond à la source. Un énoncé vrai et orienté est vert. C'est un choix de
  périmètre, pas un oubli.
- On ne mesure **pas** l'intention. « Faux » n'est pas « mensonge ».
- On ne mesure **pas** la qualité du corpus. Un `unverified` peut signifier que
  l'affirmation est invérifiable, ou simplement que notre base est trouée. Les
  deux se ressemblent de l'extérieur.
- La corroboration entre occurrences d'une même affirmation n'est **pas** une
  indépendance véritable : deux passes du même modèle sur les mêmes preuves
  partagent leurs biais. D'où un bonus de confiance volontairement faible.
- L'accord entre deux ASR de la **même famille** ne prouve rien. Un fine-tune
  partage les modes de défaillance de son modèle d'origine.

---

## 10. Traçabilité d'un résultat

**L'engagement.** Tout verdict publié doit pouvoir être reconstitué : *« produit
le JJ/MM contre le corpus version X, source Y millésime Z, citation vérifiée
littéralement »*.

**État : partiel.** La version de corpus est attachée au rendu ; les journaux
de réutilisation et de révision existent ; le lien complet verdict → version →
source → citation n'est pas encore assemblé en un seul enregistrement.

---

## Récapitulatif

| # | Engagement | État |
|---|---|---|
| 1 | Pré-inscription | **tenue une fois sur sept mesures** (01/09) |
| 2 | Degrés de liberté balayés | **un balayage publié, aucun seuil de verdict** |
| 3 | Reproductibilité | **protocole oui, verdict non** |
| 4 | Falsifiabilité | un cas témoin a réellement échoué le 01/09 |
| 5 | Couverture avant exactitude | tenu dans le code, éprouvé une fois |
| 6 | Comparaison par paires | tenu |
| 7 | Erreur de mesure ≠ phénomène | **transcription oui, voix non** |
| 8 | Incertitude déclarée | tenu, non calibré |
| 9 | Angles morts déclarés | tenu |
| 10 | Traçabilité | partiel |
| 11 | Métriques validées par un témoin | **non tenu — deux métriques aveugles le 01/09** |

**Conclusion, révisée le 01/09.** Le projet a mesuré quelque chose, une fois,
selon un protocole écrit d'avance — et cette mesure a corrigé une conclusion
antérieure au lieu de la confirmer. C'est ce qu'on demande à une méthode.

Ce que ça ne change pas : les seuils de verdict restent des opinions publiées,
faute de jeu étalon, et l'étage d'attribution reste un bouchon. Le 01/09 a
aussi montré où je m'étais trompé de coupable — j'avais mis sur le compte de la
transcription un défaut qui venait de l'attribution.

---

## 11. Une métrique peut être aveugle à ce qu'elle mesure

**Constat du 01/09/2026.** La métrique `repetition()` du banc ASR devait
détecter les boucles d'hallucination. Elle a rapporté **0 pour les deux
modèles**, alors qu'une boucle d'une quarantaine de répétitions était
manifeste à la simple lecture du texte.

Cause : elle comptait les *segments consécutifs identiques*. Or la pile
`transformers` rend des blocs de 30 secondes, et la boucle vivait **à
l'intérieur** d'un seul bloc.

**La leçon dépasse ce cas.** Une métrique qui rend zéro n'est pas une preuve
d'absence : c'est d'abord une hypothèse sur la forme du phénomène. Ici
l'hypothèse — « une boucle se voit entre segments » — était fausse pour l'une
des deux piles comparées.

**Règle qui en découle** : toute métrique nouvelle est validée sur un cas où
l'on sait qu'elle doit se déclencher, avant d'être utilisée pour conclure. Un
témoin, au sens du §1 du banc ASR de KaraK. Sans témoin, un zéro ne se lit pas.

Troisième occurrence, le 01/09 au soir : la couche d'accord réclamait qu'un
témoin répète « 2024 » et « 2028 » — la ponctuation finale (« en 2024, »,
« jusqu'à 2028. ») empêchait de les reconnaître comme des millésimes, et ils
devenaient des valeurs à corroborer. Trouvé en **lisant la liste des blocages**,
jamais en lisant le taux : 74 % ou 76 %, rien dans le nombre ne dit qu'un quart
des refus porte sur des dates.

Deuxième occurrence le même jour : l'alignement des chiffres de
`banc_chiffres.py` comparait des blocs de sous-titres de 25 s à des segments
Whisper de 4 s avec une tolérance de 6 s. Il a rendu « 6 % de part jugeable ».
Ce n'était pas une mesure du désaccord entre sources, mais de l'inadéquation
de ma fenêtre.
