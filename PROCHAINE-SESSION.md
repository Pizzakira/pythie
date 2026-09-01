# Prochaine session — reprise à froid

Écrit les 1er et 2 septembre 2026, à la clôture de la session 005, pour
quelqu'un qui rouvre le dépôt sans rien avoir en tête.

**Où en est le projet en une phrase.** La chaîne rend des verdicts sourcés,
refuse de juger un chiffre qu'une seule transcription a entendu, et ne publie
aucun rouge ; tout le reste attend **une confirmation humaine des voix**, et
l'auteur a commencé cette écoute sur une page qui enregistre chaque geste.

---

## Premier geste : où en est l'écoute ?

**Constaté à la clôture, le 02/09 vers 1 h** : `data/empreintes/ecoute.json`
existe mais ne contient que l'état initial (70 extraits, aucun nom), et la
base de l'artefact n'a pas encore de document `ecoute/laref2026`. Si l'auteur
avait nommé des voix sur la page en ligne avant qu'elle ne sache écrire dans
la base, ce travail est dans son navigateur et sera poussé de lui-même au
prochain rechargement de la page. Donc, avant tout le reste, regarder ce qui a
été enregistré, aux deux endroits possibles :

1. **En local** : `data/empreintes/ecoute.json` existe-t-il ? Il est écrit par
   le serveur local (`Ecoute-Demarrer.bat`) à chaque geste, et
   `data/empreintes/confirmation.yaml` a été régénéré avec lui — les champs
   `confirme`, `morceaux`, `inutilisables` disent où en est chaque grappe.
2. **En ligne** : la page publiée écrit le document `ecoute/laref2026` dans la
   base de l'artefact. Depuis une session Claude Code : outil Artifact,
   `read_db`, `get`, collection `ecoute`, document `laref2026`, `out_dir` pour
   l'obtenir en JSON, puis `python scripts/confirmation_merge.py <ce json>`.

Les deux documents portent une date `misAJour` : **le plus récent gagne**. Ne
pas fusionner les deux à la main.

Le résultat attendu : les sept grosses voix (Mélenchon, Glucksmann, Retailleau,
Le Pen, Attal, Philippe, Tondelier, à confirmer par l'oreille) avec
`confirme` rempli et au moins trois morceaux chacune. Alors :

```bash
/c/ProgramData/anaconda3/envs/whisperx/python.exe scripts/enrol.py \
    data/audio/laref2026.wav data/laref2026.whisper.json \
    --confirmer data/empreintes/confirmation.yaml
```

Chemin éprouvé de bout en bout sur des bornes fictives : embeddings calculés
sur les bornes exactes, empreintes écrites avec `human_verified: true`, refus
sous trois morceaux. Les morceaux marqués inutilisables (voix mêlées,
applaudissements, inaudible) n'entrent pas dans l'empreinte.

---

## La page d'écoute, telle qu'elle est

**En ligne** : https://claude.ai/code/artifact/2e1cfe40-c1ac-4022-b815-34ba1073b823
— régénérer avec `python scripts/confirmation_page.py`, republier à la même
adresse (le travail enregistré est indexé par grappe et par extrait, il
survit à une republication). **En local** : `Ecoute-Demarrer.bat` la sert
sur http://127.0.0.1:8765/ et enregistre dans le dossier ; la copie
`Ecoute-de-controle.html` à la racine, hors git, trouve ce serveur s'il tourne.

Ce qu'elle sait faire, tout venu de l'usage (D-068 à D-075) :

- un clic dans la bande place la lecture **et** choisit le morceau ;
- lecteur natif sous chaque bande ; clavier : espace, flèches ± 0,5 s (Maj :
  ± 2 s), `c` coupe ; position affichée en clair ; vitesse 0,75× / 1× / 1,5× ;
- un **morceau** inutilisable, avec motif, à droite des noms ; un **extrait**
  inutilisable en entier, tout en bas, qui fait apparaître un extrait de
  réserve (cinq préparés par voix, trois montrés) ; un second clic annule ;
- candidats en capitales, journalistes et chefs d'entreprise en minuscules ;
- l'état de la vidéo source affiché dans le bandeau, sondé à la fabrication ;
- persistance : base de l'artefact en ligne, serveur local hors ligne, sinon
  « dans ce navigateur seulement » et « Copier le résultat ».

Un bug trouvé par l'auteur en cliquant, pas par moi en relisant : le bouton
d'extrait inutilisable écrivait sous une mauvaise clé. Consigné dans le
journal. Le contrôle de syntaxe ne voit pas une clé fausse.

---

## Ce qui a été réglé — ne pas le refaire

**La provenance.** L'URL d'origine menait à une vidéo privée ; la passation
précédente y voyait « une mauvaise URL depuis la session 001 ». **C'était une
lecture fausse** : l'URL était juste le 31/08, le MEDEF a retiré la vidéo et
republié le même enregistrement le lendemain sous `z0gJwsrODEw`. Établi par
les dates, les durées et dix sondages textuels alignés à ± 0,5 s. Détail dans
`JOURNAL.md`, session 005, et `METHODE.md` §10.

| Fichier | État |
|---|---|
| `data/laref2026.plateau.yaml` | `source:` = vidéo publique ; titre, chaîne, durée, date de vérification, et `source_initiale` avec la preuve d'identité |
| `data/empreintes/confirmation.yaml` | régénéré par `enrol.py` depuis le cache : liens remplacés, `debut_s` ajouté, cinq extraits par voix ; les trois premiers extraits de chaque grappe sont inchangés |
| `data/laref2026.json`, `data/laref2026.whisper.json` | **volontairement inchangés** : leur `source` dit d'où ils viennent vraiment (la mise en ligne initiale) |

**Le contrôle au lancement.** `pythie/media/provenance.py` sonde une URL
YouTube par oEmbed. `fetch_transcript.py` consigne titre, chaîne et date de
récupération ; `confirmation_page.py` sonde la source avant de fabriquer la
page (`--sans-controle` hors ligne). Il vérifie qu'une adresse répond, pas que
c'est la bonne vidéo : l'identité reste établie à la main, dans le manifeste.

---

## Chantier suivant — brancher l'attribution sur la chaîne

Une fois des empreintes vérifiées existantes :

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
- les morceaux `inutilisables` de motif `superposition` sont les premiers
  exemples étiquetés de paroles superposées du projet : de quoi tester un
  détecteur le jour où il existe.

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
  session 004, et il se perd au premier écart.
- **Ne pas lever `REDS_UNLOCKED_BY_AGREEMENT`** sans un banc pré-inscrit qui
  passe.
- **Ne pas invoquer la bijection des sept grappes** pour déclarer les
  empreintes valides : elle n'a pas été pré-inscrite. Si elle doit servir, elle
  s'écrit d'abord dans un protocole, avant d'être regardée.
- **Ne pas « corriger » le champ `source` des transcriptions** pour qu'il
  pointe vers la vidéo publique : il dit d'où elles viennent, et c'est vrai.
- **Ne pas fusionner à la main** l'état en ligne et l'état local de l'écoute :
  le plus récent gagne, et c'est tout.

## État de la machine

- Environnement GPU : `C:\ProgramData\anaconda3\envs\whisperx\python.exe`
  (torch cu124, faster-whisper, speechbrain, sklearn, RTX 3090). Le python par
  défaut du projet n'a ni GPU ni ASR, mais suffit à `confirmation_page.py`,
  `fetch_transcript.py`, `ecoute_serveur.py` et `confirmation_merge.py`.
- `KMP_DUPLICATE_LIB_OK=TRUE` est nécessaire à toute commande python du projet
  (les `.bat` le posent).
- `yt-dlp` 2026.03.03 est dans le PATH ; `ffmpeg` aussi ; `node` 25 sert au
  contrôle de syntaxe du gabarit.
- `llama-server` n'a pas été lancé les 01 et 02/09 : `scripts/evaluate.py` en
  mode complet et `run_chain.py` sans `--no-model` n'ont donc pas tourné.
- Les vecteurs de voix sont en cache (`data/empreintes/vecteurs.npz`) : le
  regroupement se rejoue en une seconde, sans GPU, et il est déterministe
  (vérifié le 01/09 au soir : diff limité aux champs attendus).
