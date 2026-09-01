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

**État : tenu trois fois, le 01/09/2026.** Trois protocoles écrits avant
mesure — `preinscription-accord.md`, `preinscription-francais.md`,
`preinscription-empreintes.md` — chacun fixant la question, les cas témoins,
les valeurs balayées, les seuils de succès et la règle de décision.

**Deux des trois ont échoué à leur propre critère, et aucun seuil n'a bougé
pour les sauver.**

- Accord entre transcriptions : le cas témoin positif a échoué **parce que sa
  prémisse était fausse**. Sans pré-inscription, j'aurais réglé un paramètre
  jusqu'à ce que ce cas passe, contre un cas que j'avais mal lu.
- Empreintes vocales : trois candidats enrôlés, quatre exigés. Une bijection
  entre les sept plus grosses grappes et les sept candidats était sous les yeux
  — argument plus fort que le critère retenu, et **non invoqué**, faute d'avoir
  été pré-inscrit.

C'est le premier jour où la méthode sert à trancher plutôt qu'à se décrire.

**Ce qui reste** : les seuils de verdict et les seuils d'acceptation
d'empreinte n'ont toujours aucune pré-inscription, faute de matière étiquetée
pour les balayer.

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
rien (81 % à 5 s comme à 45 s) ; l'ancrage lexical, posé au passage, déplace la
couverture de 21 points. Aucune valeur n'a été retenue pour autant — le critère
éliminatoire du protocole n'est satisfait par aucune combinaison.

**Le jeu étalon existe depuis le 01/09, et il est trop petit.**
`ETUDES/etalon/laref2026.yaml` : 16 énoncés étiquetés à la main contre les
sources stockées, dont 6 seulement portent un couple de valeurs qu'une barre
puisse trancher. `scripts/evaluate.py --seuils` balaye les barres sans faire
tourner aucun modèle, et **refuse de retenir une valeur** : il faudrait des
dizaines de couples par unité de comparaison, il y en a quatre en points et
deux en relatif.

Ce que le tableau montre déjà, sans qu'on puisse en conclure : les barres
publiées (0,3 / 1,0 point) reproduisent 2 étiquettes sur 4, là où 0,1 / 2,0 en
reproduit 4. **Ce n'est pas une raison de changer les barres** — c'est une
raison d'élargir le corpus jusqu'à ce que la mesure devienne lisible. Déplacer
un seuil sur quatre items serait le geste même que ce document interdit.

**Ce qu'il faut** : le même traitement pour les seuils d'empreinte vocale et
d'accord entre fenêtres, et surtout assez de matière étiquetée pour que le
balayage cesse d'être une anecdote avec une courbe.

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

**État : deux échecs réels enregistrés le 01/09.**

Trois indicateurs sont produits par le code : taux de faux rouges, taux
d'abstention, citations non retrouvées. Aucun n'a encore été mesuré sur de la
matière réelle.

Mais deux bancs ont été pris en défaut par leurs propres cas témoins. Le T+ du
banc d'accord devait être bloqué et ne l'a pas été — l'explication n'était pas
un réglage à corriger, c'était ma lecture de l'incident qui était fausse. Le
bootstrap des empreintes n'a enrôlé que trois candidats sur les quatre exigés.
Une méthode qui ne peut pas produire ce genre de résultat ne teste rien.

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
cela retire un cinquième des énoncés chiffrés.

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

**État : partiel, et pris en défaut le 01/09.** La version de corpus est
attachée au rendu ; les journaux de réutilisation et de révision existent ; le
lien complet verdict → version → source → citation n'est pas encore assemblé en
un seul enregistrement.

**Le contre-exemple, trouvé par un lecteur et non par le programme** : le
1er septembre, l'URL d'origine déclarée dans `data/laref2026.plateau.yaml`
menait à une vidéo privée, et les 42 liens horodatés de l'écoute de contrôle
avec elle.

**Ce que j'en ai d'abord conclu était faux.** J'ai écrit que le manifeste
portait « une mauvaise URL depuis la session 001 ». Vérifié le soir même :
l'URL était juste le 31 août — les sous-titres et l'audio en viennent, on ne
récupère pas 484 blocs d'une vidéo privée — et le diffuseur a retiré cette
mise en ligne pour republier le même enregistrement le lendemain sous un autre
identifiant. Dix sondages textuels répartis sur le débat tombent au même
instant à ± 0,5 s dans les deux pistes. La source avait **bougé**, pas menti.

Deux leçons, et non une :

1. **Une provenance ne se vérifie pas toute seule.** Rien dans la chaîne
   n'avait jamais tenté d'ouvrir cette URL, donc rien ne pouvait signaler
   qu'elle ne répondait plus. Depuis le 01/09, la récupération des sous-titres
   et la fabrication de la page d'écoute sondent la source et consignent ce
   qu'elles ont vu (`pythie/media/provenance.py`, D-066).
2. **Une adresse seule ne permet pas de distinguer « déplacée » de
   « fausse ».** Il a fallu la date du fichier téléchargé, sa durée et la date
   de mise en ligne pour trancher — aucune n'était dans le manifeste. Il porte
   désormais le titre, la chaîne, la durée, la date de vérification et
   l'adresse initiale avec la preuve d'identité (D-065). C'est la condition
   pour qu'un lecteur futur puisse refaire ce que j'ai fait à la main.

Ce qui reste vrai de l'engagement : le lien complet verdict → version → source
→ citation n'est toujours pas assemblé en un seul enregistrement.

---

## Récapitulatif

| # | Engagement | État |
|---|---|---|
| 1 | Pré-inscription | **trois protocoles écrits avant mesure** (01/09) |
| 2 | Degrés de liberté balayés | **un balayage publié, aucun seuil de verdict** |
| 3 | Reproductibilité | **protocole oui, verdict non** |
| 4 | Falsifiabilité | **deux bancs ont échoué à leur propre critère** |
| 5 | Couverture avant exactitude | tenu dans le code, éprouvé une fois |
| 6 | Comparaison par paires | tenu |
| 7 | Erreur de mesure ≠ phénomène | **transcription oui, voix non** |
| 8 | Incertitude déclarée | tenu, non calibré |
| 9 | Angles morts déclarés | tenu |
| 10 | Traçabilité | **partiel — la source sondée au lancement depuis le 01/09 ; le lien verdict → citation pas encore assemblé** |
| 11 | Métriques validées par un témoin | **six instruments pris en défaut, tous corrigés** |
| 12 | Ce qu'une machine propose, une personne le confirme | tenu, par un drapeau dans la donnée |

**Conclusion, au soir du 01/09.** Trois mesures ont été conduites selon des
protocoles écrits d'avance. **Deux ont échoué à leur propre critère, et aucun
seuil n'a été déplacé pour les sauver** — dans un cas en laissant de côté un
argument plus fort que le critère retenu, faute qu'il ait été pré-inscrit. Une
de ces mesures a corrigé une conclusion antérieure au lieu de la confirmer :
j'avais imputé à la transcription un défaut qui venait de l'attribution.

C'est le premier jour où ce document sert à trancher plutôt qu'à décrire des
intentions.

Ce que ça ne change pas : les seuils de verdict restent des opinions publiées,
faute d'un jeu étalon assez large, et l'étage d'attribution attend une
confirmation humaine que rien ne peut remplacer.

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

## L'inventaire des instruments pris en défaut, au 01/09/2026

Six, en deux jours. **Aucun n'était visible dans le nombre qu'il produisait ;
tous se sont vus en lisant ce que ce nombre recouvrait.**

| # | Le défaut | Ce qu'il faussait |
|---|---|---|
| 1 | `repetition()` comptait les segments identiques consécutifs | Rendait 0 sur une boucle de 45 répétitions vivant à l'intérieur d'un bloc de 30 s |
| 2 | `banc_chiffres.py` alignait des blocs de 25 s sur des segments de 4 s | Rendait « 6 % de part jugeable » — une mesure de ma fenêtre, pas du désaccord |
| 3 | Millésimes suivis d'une ponctuation lus comme des quantités | La couche d'accord exigeait qu'un témoin répète « 2024 » |
| 4 | Mots d'échelle amputés par un point final | « 150 milliards. » lu comme 150 — un facteur mille. La couverture passait de 74 % à 78 % une fois corrigé |
| 5 | Le balayage de seuils comptait des items qu'aucune barre ne produit | Toutes les barres baissaient de la même quantité : invisible dans un classement |
| 6 | Une mention de patronyme votait pour les dix grappes suivantes | Rendait le critère des 60 % **insatisfaisable par construction** : le banc aurait échoué sur du matériel parfait |

Le sixième est le plus instructif. Un critère peut être hors d'atteinte non
parce que la réalité lui résiste, mais parce que l'instrument ne peut pas le
produire. **Un échec ne se lit pas davantage qu'un zéro** : avant de conclure
qu'une hypothèse est fausse, il faut vérifier que le montage pouvait la
confirmer.

S'y ajoute un défaut d'un autre genre, qui ne fausse pas une mesure mais la
rend aveugle à une partie du monde : le patronyme pris comme « le dernier mot
du nom » réduisait « Marine Le Pen » à « pen », trois lettres, écarté par un
garde-fou de longueur. Une candidate était **invisible** au mécanisme entier,
et rien dans aucun taux ne le disait.

---

## 12. Ce qu'une machine propose, une personne le confirme

**L'engagement.** Quand une identification ne peut pas être vérifiée par le
programme, elle est **marquée comme non vérifiée dans la donnée elle-même**, et
ce marquage a des effets : tant qu'il est là, rien ne s'appuie dessus.

**Le cas d'espèce.** Les empreintes vocales du 01/09 sont construites sans que
personne n'ait écouté : on regroupe les voix, puis les patronymes prononcés
juste avant une prise de parole nomment les grappes. Le montage prouve la
**constance**, pas l'**identité** — quelqu'un qui parlerait systématiquement
après avoir prononcé un nom produirait la même régularité sous la mauvaise
étiquette.

**Ce qui est tenu.** `VoicePrint.human_verified` est faux par défaut, y compris
pour une empreinte écrite par une version antérieure du format. Une attribution
issue d'une empreinte non confirmée ne peut porter aucun verdict coloré.

**Le coût de la confirmation est d'une minute d'écoute par voix ; le coût d'une
erreur est une citation attribuée à quelqu'un qui ne l'a pas prononcée.** Le
rapport entre les deux est ce qui justifie de bloquer.

**Généralisation.** La même forme s'applique partout où une machine propose une
identité : le drapeau vit dans la donnée, pas dans une note de documentation,
et le programme refuse tant qu'il est faux.
