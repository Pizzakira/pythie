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

**État : non tenu.** Le banc d'évaluation n'existe pas. Rien n'est pré-inscrit.

**Ce qu'il faut** : pour chaque mesure, un document antérieur disant quelle
question est posée, quel seuil vaut succès, et ce qu'on fait des deux issues.

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

**Ce qu'il faut** : chaque seuil balayé sur le jeu étalon, la courbe publiée,
la valeur retenue justifiée par cette courbe et non par un avis.

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

**État : les instruments existent, la mesure non.**

Trois indicateurs sont déjà produits par le code : taux de faux rouges, taux
d'abstention, citations non retrouvées. Aucun n'a jamais été mesuré sur de la
matière réelle.

---

## 5. Couverture avant exactitude

**L'engagement.** Le taux d'abstention se lit **avant** le taux d'accord.

Un système qui ne se prononce que sur 30 % des affirmations et se trompe
rarement n'est pas meilleur qu'un système couvrant 90 % avec un peu moins
d'exactitude : son taux d'accord porte sur une population qu'il a lui-même
choisie.

**État : tenu dans l'ordre d'affichage des métriques** (`run_poc.py`,
`batch.compare`). Non éprouvé.

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

**État : tenu par conception.** Désaccord entre transcriptions sur une valeur →
pas de verdict. Similarité vocale sous le seuil ou paroles superposées → pas
d'attribution, donc pas de jugement.

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
| 1 | Pré-inscription | **non tenu** |
| 2 | Degrés de liberté balayés | **non tenu — point le plus faible** |
| 3 | Reproductibilité | tenu |
| 4 | Falsifiabilité | instruments prêts, jamais mesurés |
| 5 | Couverture avant exactitude | tenu dans le code, non éprouvé |
| 6 | Comparaison par paires | tenu |
| 7 | Erreur de mesure ≠ phénomène | tenu |
| 8 | Incertitude déclarée | tenu, non calibré |
| 9 | Angles morts déclarés | tenu |
| 10 | Traçabilité | partiel |

**Conclusion.** Le projet est bien construit pour être scientifique, et ne l'est
pas encore, faute d'avoir mesuré quoi que ce soit. Les deux manques — 1 et 2 —
se comblent au même endroit : le jeu étalon. Tant qu'il n'existe pas, les
seuils restent des opinions publiées.
