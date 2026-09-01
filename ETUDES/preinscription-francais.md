# Pré-inscription — le fine-tune français, converti en CTranslate2

**Écrit le 1er septembre 2026, avant conversion et avant toute exécution.**
Deuxième mesure pré-inscrite du projet.

---

## Ce que la question n'est pas

`bofenghuang/whisper-large-v3-french` est un fine-tune de `large-v3`. Quelle
que soit l'issue de ce banc, **il ne pourra jamais corroborer large-v3** : même
famille, mêmes modes de défaillance, et la couche d'accord l'écarte
mécaniquement (D-047, D-051). Ce n'est pas une affaire de qualité, c'est une
affaire de dépendance statistique.

Sa seule place possible est celle de **large-v3 lui-même** : la voix Whisper de
la paire, en face des sous-titres YouTube. La question est donc « remplace-t-il
le titulaire ? », jamais « s'ajoute-t-il à lui ? ».

## Question

La boucle d'hallucination mesurée le 01/09 — une trentaine de « c'est le 2ème »
consécutifs — vient-elle **des poids** ou **de la pile qui les exécute** ?

Le modèle avait été exécuté via `transformers`, qui découpe en blocs de 30 s et
rend, sur 5 minutes, 2 segments. La conversion CTranslate2 le fait passer par
`faster-whisper`, avec VAD et sans conditionnement sur le texte précédent —
exactement le régime dans lequel large-v3 ne boucle pas. Si la boucle
disparaît, elle venait de la pile ; si elle persiste, elle vient des poids et
D-046 devient définitif.

## Matériel

- Extrait de 5 minutes à partir de 24:00, `data/banc_fr/extrait.wav` : le même
  que le 01/09, et celui où la boucle est documentée.
- Comparaison contre `data/banc_fr/texte_large-v3.txt`, déjà produit.

## Le témoin de la métrique, avant tout le reste

La métrique `repetition()` du 01/09 a rendu **0 alors que la boucle était
manifeste** : elle comptait les segments consécutifs identiques, et la boucle
vivait à l'intérieur d'un segment (METHODE §11).

La nouvelle métrique compte donc la plus longue **répétition consécutive d'un
même n-gramme de mots** à l'intérieur du texte entier, sans considération de
segment.

**Elle doit d'abord se déclencher sur `texte_francais.txt`**, où l'on sait que
la boucle existe. Seuil : au moins 5 répétitions consécutives détectées. Si
elle ne les trouve pas, le banc s'arrête là et ne conclut rien — une métrique
qui rend zéro sans témoin ne se lit pas.

## Critères de succès, posés d'avance

Le modèle converti est déclaré **utilisable** si les trois sont vrais :

1. **Boucle** : plus longue répétition ≤ 2, soit le niveau de large-v3 sur le
   même extrait (à mesurer, et si large-v3 fait pire, c'est son chiffre qui
   fait foi).
2. **Chiffres** : aucune graphie de type « 210 1000000000 ». Critère mesurable
   retenu : aucun entier de 7 chiffres ou plus écrit en toutes lettres
   numériques.
3. **Vitesse** : au moins 5× le direct. large-v3 fait 14,5× ; en dessous de 5×
   le modèle n'a pas sa place dans une chaîne qui vise le direct.

## Règle de décision, posée d'avance

**Le titulaire reste titulaire à égalité.** Si le modèle converti satisfait les
trois critères, il devient un *candidat*, pas la référence : nous n'avons
aucune vérité de terrain permettant de dire laquelle des deux transcriptions
est la plus juste (D-048). Il ne remplace `large-v3` que s'il présente
**strictement moins** de pathologies mesurées — boucle plus courte, ou graphies
de nombres correctes là où large-v3 se trompe.

À défaut, D-046 est confirmé sous sa forme définitive : le fine-tune n'entre
pas dans la chaîne, et la raison est écrite.

## Ce que ce banc ne mesure pas

- Il ne dit **pas** lequel des deux modèles transcrit le plus fidèlement. Il
  mesure des pathologies, pas de l'exactitude.
- Il ne teste **pas** les variantes distillées (`dec2/4/8/16`), que
  `ETUDES/transcription.md` recommande pourtant. Elles restent à évaluer, avec
  leur propre pré-inscription.
- 5 minutes d'audio, un seul extrait. Une boucle absente ici n'est pas une
  boucle absente partout.
