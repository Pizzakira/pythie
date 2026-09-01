# Accord entre transcriptions — résultats

Première mesure **pré-inscrite** du projet. Le protocole a été figé avant
exécution dans `ETUDES/preinscription-accord.md` ; ce document ne fait que
rapporter ce qui est sorti, y compris ce qui contredit ce que j'attendais.

Mesuré le 1er septembre 2026.

---

## Matériel

| | |
|---|---|
| Audio | débat LaREF 2026, 3 h 12 |
| Transcription principale | sous-titres YouTube, famille `youtube` |
| Témoin | `faster-whisper-large-v3`, famille `whisper` |
| Coût du témoin | 645 s de calcul sur RTX 3090 — **17,9× le direct** |
| Population | 2 267 énoncés, 174 candidats à l'étage 0, **102 porteurs de chiffre** |

Deux familles distinctes : la condition posée en D-047 est remplie.

---

## Le résultat principal : le cas témoin T+ échoue

**Il devait être bloqué. Il est confirmé, à tous les réglages.**

La phrase qui avait produit le premier rouge du projet :

> sous-titres YouTube — « Je vous cite **de au feu** 600 millions de dettes
> françaises. »
> faster-whisper — « Je rappelle votre proposition, je vous cite, **de foutre
> au feu** 600 millions de dettes françaises. »

Les deux transcriptions portent le même chiffre. **Le « 600 millions » n'était
pas une corruption d'ASR : il a été prononcé.** Les sous-titres avaient
simplement perdu le verbe « foutre », ce qui rendait la phrase illisible sans
toucher à la valeur.

### Ce que cela corrige

Le journal du 31/08 (D-044) concluait : *« les 600 millions sont une corruption
d'ASR ; le système a marqué faux une phrase que personne n'a prononcée »*. La
mesure dit le contraire. La phrase a été prononcée, le chiffre aussi.

Le vrai défaut est ailleurs, et il était sous les yeux : **c'est l'animateur qui
parle**, citant une proposition de Jean-Luc Mélenchon, et se trompant
vraisemblablement de multiple — millions pour milliards. Or D-040 dit que seuls
les candidats sont analysés. L'énoncé n'aurait jamais dû être vérifié.

Ce n'est donc pas la couche de transcription qui manquait ce jour-là, c'est
**l'étage d'attribution**, qui est encore un bouchon. Une couche d'accord entre
transcriptions n'aurait rien empêché.

C'est exactement pour cela que les cas témoins sont écrits avant la mesure : je
serais parti chercher un réglage qui bloque cette phrase, et j'aurais réglé un
paramètre contre un cas dont j'avais mal lu la cause.

**Le cas témoin négatif, lui, passe.** « 45,3 % de prélèvement » et « 57,3 % de
dépenses » sont confirmés par les deux familles : les deux verdicts publiés du
POC 1 reposent bien sur des chiffres entendus deux fois.

---

## Le balayage

Corroboration des 102 énoncés porteurs de chiffre :

| `min_anchor` | 0,00 | 0,10 | 0,20 | 0,35 | 0,50 |
|---|---|---|---|---|---|
| corroborés | 78 | 78 | 76 | 68 | 58 |
| **couverture** | **76 %** | **76 %** | **74 %** | **67 %** | **57 %** |

Et la fenêtre temporelle, de 5 s à 45 s de tolérance de part et d'autre :
**76 % à 5 s, 76 % à 45 s.** Un énoncé de différence sur 102.

**Le paramètre dont je me méfiais ne fait rien, celui que j'avais posé au
passage fait tout.** J'avais écrit dans `transcripts.py` que la fenêtre devait
« absorber la dérive » entre deux découpages — c'était l'inquiétude principale,
héritée de l'erreur d'alignement du 01/09. Elle ne mesure rien ici. C'est
l'ancrage lexical qui déplace la couverture de 19 points.

---

## Pourquoi les blocages se produisent

Un taux de blocage ne dit pas sa cause. Deux causes possibles appellent deux
remèdes opposés : un désaccord réel entre modèles (bloquer est juste) ou une
fenêtre mal posée (bloquer est un faux positif). On cherche donc chaque chiffre
bloqué dans **toute** la transcription témoin.

26 énoncés bloqués, 31 chiffres non retrouvés dans leur fenêtre :

| Où le chiffre se trouve dans le témoin | Nombre | Lecture |
|---|---|---|
| absent de toute la transcription | 10 | désaccord réel |
| à plus de 5 minutes | 16 | autre occurrence, sans rapport |
| entre 1 et 5 minutes | 1 | douteux |
| à moins de 60 s | 4 | **dérive d'alignement possible** |

Au plus 4 blocages sur 31 s'expliquent par ma fenêtre. Le reste est du
désaccord entre deux oreilles.

Exemples lus en clair :

| Sous-titres YouTube | faster-whisper |
|---|---|
| « l'État central a reculé de **05** points » | « **0,5** » |
| « **103,6 millions** » | « **3,6 millions** » |
| « les taux d'intérêt les plus élevés, **4** » | « **3 %** » |

Le premier est une graphie impossible — « 05 points ». Le deuxième change la
valeur d'un facteur 29. Aucun des deux n'est arbitrable sans écouter l'audio :
la couche ne dit pas qui a raison, elle dit qu'on ne sait pas (D-048).

---

## Ce que le chiffre de 74 % signifie vraiment

**Un quart des énoncés chiffrés n'est pas corroboré entre deux familles d'ASR.**

Dit autrement : une chaîne qui travaille sur une seule transcription rend, pour
un chiffre sur quatre, un verdict sur une valeur que la seconde oreille n'a pas
entendue. Ce n'est pas une hypothèse de conception, c'est une mesure, et elle
vaut pour tous les verdicts publiés jusqu'ici.

---

## Décision, appliquée selon la règle pré-inscrite

Le critère 1 est éliminatoire et **aucun réglage ne le satisfait**. La règle
publiée d'avance dit alors : la couche n'est pas branchée sur la publication.

Elle est donc **implémentée, exécutée, mesurée — et sans autorité**. Concrètement :

- `pipeline.guard_red` retire **tout** rouge, corroboré ou non. D-044 cesse
  d'être une consigne tenue par discipline et devient une propriété du
  programme (`REDS_UNLOCKED_BY_AGREEMENT = False`).
- L'étage 0.5 continue de bloquer les chiffres non corroborés et d'afficher
  pourquoi, ce qui est une abstention, jamais une accusation.
- Lever le verrou demandera un banc pré-inscrit qui passe, pas un drapeau
  retourné parce que la couche existe désormais.

## Défauts d'instrument corrigés en cours de route

Deux, tous deux trouvés en **lisant les blocages** plutôt qu'en lisant le taux.

1. « en 2024, » et « jusqu'à 2028. » étaient lus comme des quantités et non
   comme des millésimes : la ponctuation finale empêchait la reconnaissance
   d'année. La couche exigeait alors qu'un témoin répète un millésime.
2. Le dénominateur du banc comptait les énoncés porteurs d'une année seule,
   que la couche ne demande à personne de corroborer. 125 annoncés, 102 réels.

Les deux ont été corrigés et la mesure relancée. Aucun seuil, aucun cas témoin,
aucune règle de décision n'a été touché — seul l'instrument l'a été.

## Ce que ce banc ne dit pas

- Il ne dit **pas** laquelle des deux transcriptions a raison. Aucune vérité de
  terrain, aucun accès au signal (D-048).
- Une confirmation ne garantit **pas** que la phrase est bien transcrite : les
  mots autour d'un chiffre juste peuvent être faux — T+ en est la démonstration.
- Un seul témoin, donc une seule paire de familles. Avec un troisième
  (Kyutai, Voxtral), la question « qui a raison » deviendrait posable.
