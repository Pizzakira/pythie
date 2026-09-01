# Prochaine session — reprise à froid

Écrit le 1er septembre 2026 à la clôture de la session 004, pour quelqu'un qui
rouvre le dépôt sans rien avoir en tête.

**Où en est le projet en une phrase.** La chaîne rend des verdicts sourcés,
refuse de juger un chiffre qu'une seule transcription a entendu, et ne publie
aucun rouge ; tout le reste attend **une confirmation humaine des voix**, qui
n'a pas encore eu lieu parce que la page qui la permet est inutilisable en
l'état.

---

## Chantier 1 — rendre la page d'écoute utilisable

`scripts/confirmation_page.html` (gabarit) + `scripts/confirmation_page.py`
(générateur). Publiée comme artefact ; régénérer avec :

```bash
python scripts/confirmation_page.py
```

**Constaté à l'usage, sous Firefox, le 01/09 :**

### 1. On ne peut pas cliquer dans la bande pour se déplacer

**Cause identifiée par lecture du code, à vérifier avant de corriger.** La
bande porte bien un `mousedown` qui déplace la lecture :

```js
strip.addEventListener("mousedown", event => { audio.currentTime = … });
```

mais chaque morceau (`.seg`) est un enfant qui couvre toute la hauteur et
appelle `event.stopPropagation()` pour se sélectionner. Le clic n'atteint donc
**jamais** la bande : il est intercepté par le morceau. Au premier affichage il
n'existe qu'un seul morceau couvrant tout l'extrait — donc aucun clic ne
déplace jamais la lecture.

Correctif à concevoir, pas à bâcler : sélectionner un morceau ET déplacer la
lecture au même clic, ou séparer les deux gestes (clic = déplacer, clic sur
l'étiquette = sélectionner).

### 2. Pas de lecture / pause utilisable, pas de navigation fine

Il n'y a qu'un bouton rond par extrait, aucun retour de position, aucun moyen
d'avancer de deux secondes. Ce qu'il faut :

- un **`<audio controls>` natif** en plus de la bande : sous Firefox il donne
  la barre de progression, le volume, la vitesse de lecture et le clavier, pour
  zéro ligne de code, et c'est ce qui manque le plus ;
- **clavier** : espace pour lecture/pause, flèches pour ±0,5 s, `c` pour couper
  à la position courante ;
- **position affichée en clair** pendant la lecture (« 4,2 s sur 18 »), parce
  que « couper ici » n'a de sens que si l'on sait où est *ici* ;
- vitesse 0,75× utile pour trancher entre deux voix proches.

### 3. Le lien vidéo pointe vers une vidéo privée

**Le fichier `data/laref2026.plateau.yaml` porte une mauvaise URL d'origine.**

| | |
|---|---|
| écrit dans le manifeste | `https://www.youtube.com/watch?v=VM8cGxOtUvA` — **privée** |
| débat réel | `https://www.youtube.com/watch?v=z0gJwsrODEw` |

Relevé exact des fichiers à corriger, le 01/09 :

| Fichier | Rôle | Versionné |
|---|---|---|
| `data/laref2026.plateau.yaml` | **la source de la faute**, champ `source:` | oui |
| `data/empreintes/confirmation.yaml` | dérivé — 42 liens horodatés faux | oui |
| `data/laref2026.json` | champ `source` des sous-titres | non (ignoré) |
| `data/laref2026.whisper.json` | recopié depuis la ligne de commande | non (ignoré) |

Corriger le manifeste et régénérer les deux dérivés ; ne pas éditer les
dérivés à la main.

**À faire avant tout le reste, et dans cet ordre :**

1. **Vérifier de quelle vidéo viennent réellement les sous-titres.** Si
   `fetch_transcript.py` a été lancé sur `VM8cGxOtUvA`, la transcription
   principale ne décrit peut-être pas le même enregistrement que le `.wav`. Le
   banc d'accord donne 78 % de corroboration entre les deux sources, ce qui
   plaide fortement pour le même événement — mais *plaide* n'est pas *prouve*,
   et une provenance fausse est exactement ce que `METHODE.md` §10 interdit de
   laisser passer.
2. Corriger l'URL dans les trois fichiers, puis régénérer la page.
3. Se demander si la provenance mérite un contrôle automatique : un manifeste
   qui déclare une URL inaccessible devrait le signaler au lancement plutôt
   qu'à la première tentative d'un lecteur.

### 4. Une fois la page utilisable

L'écoute produit un YAML de morceaux `[début, fin, qui]`, à passer à :

```bash
python scripts/enrol.py data/audio/laref2026.wav data/laref2026.whisper.json \
    --confirmer data/empreintes/confirmation.yaml
```

Chemin déjà éprouvé de bout en bout sur des bornes fictives : embeddings
calculés sur les bornes exactes, empreintes écrites avec `human_verified: true`,
refus sous trois morceaux.

---

## Chantier 2 — brancher l'attribution sur la chaîne

Une fois des empreintes vérifiées existantes, ce qui reste :

- `scripts/run_chain.py` remplace le bouchon d'étage 1 par une identification
  réelle (`Registry.identify` sur les segments, `media/consensus.py` pour la
  règle d'accord) ;
- **seuls les candidats sont analysés** (D-040) : l'énoncé de l'animateur qui a
  produit le premier rouge du projet doit cesser d'être vérifié ;
- l'item `dette-600m-anime` du jeu étalon passe de `atteignable_aujourdhui: non`
  à mesurable — c'est le test de réussite du chantier ;
- rappel : `ACCEPT_THRESHOLD = 0,62` et `MARGIN_THRESHOLD = 0,06` n'ont jamais
  été balayés (`METHODE.md` §2). Les empreintes confirmées permettront enfin de
  le faire — avec une pré-inscription écrite d'avance, comme les trois autres.

**Angle mort qui restera ouvert** : aucun détecteur de paroles superposées, donc
la règle « la superposition s'abstient » de `media/consensus.py` n'est pas
applicable. Il faut pyannote, dont la licence doit être acceptée sur Hugging
Face avec un jeton. À demander à l'auteur du projet.

---

## Ensuite, par ordre de valeur

1. **Le corpus** — deux domaines sur huit. C'est lui qui empêche le jeu étalon
   de grandir, donc les seuils d'être calibrés. Chaque domaine ajouté rend
   étiquetables les énoncés qu'il couvre.
2. **Une troisième famille de transcription** (Kyutai, Voxtral) : avec deux
   familles on détecte un désaccord, avec trois on peut l'arbitrer. Aucune
   variante de Whisper ne peut tenir ce rôle.
3. **La reproductibilité du verdict** (`METHODE.md` §3) : rejouer N fois et
   traiter la dispersion comme une abstention.

## Ce qu'il ne faut pas faire

- **Ne pas déplacer un seuil publié pour faire passer un cas.** Deux bancs ont
  échoué le 01/09 et aucun seuil n'a bougé ; c'est le principal acquis de la
  session, et il se perd au premier écart.
- **Ne pas lever `REDS_UNLOCKED_BY_AGREEMENT`** sans un banc pré-inscrit qui
  passe.
- **Ne pas invoquer la bijection des sept grappes** pour déclarer les
  empreintes valides : elle n'a pas été pré-inscrite. Si elle doit servir, elle
  s'écrit d'abord dans un protocole, avant d'être regardée.

## État de la machine

- Environnement GPU : `C:\ProgramData\anaconda3\envs\whisperx\python.exe`
  (torch cu124, faster-whisper, speechbrain, RTX 3090). Le python par défaut du
  projet n'a ni GPU ni ASR.
- `KMP_DUPLICATE_LIB_OK=TRUE` est nécessaire à toute commande python du projet.
- `llama-server` n'écoutait pas le 01/09 : `scripts/evaluate.py` en mode complet
  et `run_chain.py` sans `--no-model` n'ont donc pas tourné.
- Les vecteurs de voix sont en cache (`data/empreintes/vecteurs.npz`) : le
  regroupement se rejoue en une seconde, sans repasser par le GPU.
