# Pythie

Lit ce qui est dit, le compare aux sources primaires, et rapporte si la valeur
énoncée est **exacte**, **approximative** ou **fausse**.

Écrit en Python — et la Pythie interprète les oracles.

## Périmètre

**Ce que fait l'outil.** Il isole les énoncés contenant une valeur testable,
cherche cette valeur dans un corpus fermé de sources primaires, et compare.

**Ce qu'il ne fait pas.** Il n'analyse pas la rhétorique, ne qualifie aucun
procédé de discours, et ne mesure aucune intention. « Faux » signifie *l'énoncé
ne correspond pas à la source*, jamais *le locuteur a menti*.

Les emphases, figures de style et attaques personnelles ne sont pas prises en
compte. Exception unique : lorsqu'une figure contient une valeur testable, la
valeur est vérifiée et la figure ignorée.

**Conséquence assumée : un énoncé rigoureusement vrai est vert, même s'il est
incomplet ou orienté.** Juger cela supposerait de lire une intention.

## Les trois principes

**1. Les paramètres du modèle ne sont pas une source.**
Aucun chiffre ne peut venir de ce que le modèle « sait ». Toute valeur doit
provenir d'un document effectivement fourni. Sans document : `unverified`. Il
n'existe aucun verdict de repli.

**2. Une fiche oriente, elle ne prouve jamais.**
Les `FICHE.md` sont nos propres synthèses : s'en servir comme preuve serait
circulaire. Toute citation retenue doit provenir d'un fichier sous `sources/`.
Le programme le vérifie et rejette le reste.

**3. Un verdict ne peut pas être plus fort que sa source.**
Un `false` exige une source de rang 1. Mécanique, pas discrétionnaire.

## Architecture

```
étage 0    triggers   regex, coût nul, auditable            triggers.py
étage 0.5  accord     chiffre entendu deux fois, ou pas jugé  media/transcripts.py
étage 1    triage     appel modèle court, sortie tôt        pipeline.py
étage 2    verify     modèle + base locale fermée           verify.py
étage 3    render     HTML deux degrés + JSON               render.py
```

Entonnoir à sorties anticipées : un appel modèle n'est payé que sur ce qui a
franchi l'étage précédent.

### La base pyramidale

```
corpus/base/
  INDEX.md                    niveau 0 — quels domaines existent
  <domaine>/
    FICHE.md                  niveau 1 — où trouver quoi, quels pièges
    sources/
      <fichier>               niveau 2 — LA SOURCE PRIMAIRE stockée
      <fichier>.meta.yaml     provenance : url d'origine, date, empreinte, rang
```

Le modèle ne cherche jamais. Il descend la pyramide et lit ce qu'on lui tend.
Ce qui n'est pas dans la base n'existe pas pour lui : l'interdit fort est une
propriété physique du corpus, pas une consigne.

## L'échelle

| État | Couleur | Soulignement | Condition |
|---|---|---|---|
| `exact` | vert pâle | plein | valeur confirmée |
| `approximate` | orange | tireté | écart de 5 % à 25 % |
| `false` | rouge foncé | ondulé | contredite — **rang 1 exigé** |
| `too_vague` | gris | pointillé | défaut de l'énoncé |
| `conflicting_sources` | gris | pointillé | définitions incompatibles |
| `unverified` | gris | pointillé | **défaut de notre système** |
| `pending` | — | tireté | vérification en cours |
| `out_of_scope` | aucune | aucun | rhétorique, opinion, engagement |

Seuils publiés à l'avance et appliqués **par le programme**, jamais par le
modèle : ≤ 5 % exact · 5–25 % approximatif · > 25 % faux.

**Une grandeur en pourcentage se compare en points**, jamais relativement :
≤ 0,3 point exact · 0,3–1 point approximatif · au-delà, le modèle tranche.
Sans cette règle, 45,3 % contre 43,6 % du PIB donne un écart relatif de 3,4 %
— donc « exact » — pour 1,7 point de PIB, soit une cinquantaine de milliards.

## Accessibilité

La couleur n'est jamais le seul canal : chaque état porte un soulignement et un
glyphe distincts, et l'état existe dans le JSON et dans l'`aria-label`.
**Critère d'acceptation : la page en niveaux de gris reste entièrement
lisible.**

## Installation

```bash
pip install -r requirements.txt
```

Modèle local via llama.cpp (`llama-server`, API compatible OpenAI, décodage
contraint par grammaire GBNF) :

```bash
# lancer le serveur, puis
export PYTHIE_LLM_URL=http://127.0.0.1:1234/v1
export PYTHIE_LLM_MODEL=Qwen3.8-27B
```

## Usage

```bash
python scripts/fetch_transcript.py "<url youtube>" --sortie data/debat.json

# une seconde oreille, d'une AUTRE famille : sans elle, aucun chiffre n'est corroboré
python scripts/transcribe.py data/audio/debat.webm --modele large-v3 \
    --sortie data/debat.whisper.json

python scripts/run_chain.py data/debat.json --famille youtube \
    --temoin data/debat.whisper.json --depuis 22 --minutes 10
python scripts/run_poc.py data/debat.json --degree 2 --out data/debat
```

On ne télécharge pas la vidéo, seulement les sous-titres — et on ne republie
pas la transcription intégrale : seuls les extraits analysés sont affichés.

## Conventions

- **Code, identifiants et commentaires : anglais.** Sans exception.
- **Documentation, cahier des charges, corpus : français.**
- Les prompts sont en français : la matière analysée l'est.

## État au 1er septembre 2026

**POC 1 réussi.** La chaîne tourne de bout en bout sur le débat LaREF 2026 et
rend des verdicts réels et sourcés :

```
« 57,3 % de dépenses publiques »  -> EXACT        INSEE 57,2 % du PIB 2025
« 45,3 % de prélèvement »         -> APPROXIMATIF INSEE 43,6 % du PIB 2025
```

Citation retrouvée mot pour mot dans la source stockée, URL INSEE jointe.
Le degré 1 se rejoue au minutage réel : `--rejeu 12` accélère douze fois.

### Transcription — mesuré

| Source | Patronymes exacts | Utilisable |
|---|---|---|
| `faster-whisper-large-v3` | 8/11 | **91 %** — retenu |
| `whisper-large-v3-french` | 8/11 | 91 % — **écarté**, boucle d'hallucination |
| CrisperWhisper 2.0 | 5/11 | 64 % — deuxième voix |
| Sous-titres YouTube | 3/11 | 36 % |

### Accord entre transcriptions — mesuré

Un chiffre qu'une seconde famille d'ASR n'a pas entendu ne reçoit aucun verdict.
Sous-titres YouTube contre `faster-whisper-large-v3`, débat entier, 102 énoncés
chiffrés :

| | |
|---|---|
| corroborés | **74 %** |
| bloqués | 26 % — dont au plus 4 cas sur 31 imputables à l'alignement |

**Un quart des énoncés chiffrés n'est pas corroboré entre deux familles.** Une
chaîne qui travaille sur une seule transcription rend donc, pour un chiffre sur
quatre, un verdict sur une valeur que la seconde oreille n'a pas entendue.

La couche est **implémentée, mesurée, et sans autorité** : le banc pré-inscrit
qui devait la valider a échoué, donc elle ne débloque rien. Aucun rouge n'est
publié, corroboré ou non — et c'est désormais le programme qui le garantit, non
plus une consigne. Détail : `ETUDES/accord-transcriptions.md`.

### Ce qui bloque encore

- **Attribution des locuteurs** : premier blocage du projet. Aucune empreinte
  enrôlée, donc la règle « seuls les candidats sont analysés » est inapplicable.
  Le premier rouge du système portait sur une phrase de l'animateur — mesuré le
  01/09, contre ce que la session précédente avait conclu.
- **Rouges** : bloqués en bloc par le programme, jusqu'à un banc qui passe.
- **Corpus** : deux domaines sur huit. 24 affirmations sur 40 hors périmètre.
- **Reproductibilité du verdict** : non tenue, mesurée. Voir `METHODE.md` §3.
- **Jeu étalon** : inexistant. Sans lui, les seuils restent des opinions.

### Documentation

| Fichier | Contenu |
|---|---|
| `SPECIFICATIONS.md` | le cahier, en lecture pyramidale à quatre niveaux |
| `METHODE.md` | les engagements scientifiques, **et où ils ne sont pas tenus** |
| `JOURNAL.md` | 56 décisions datées avec leur motif, et mes erreurs |
| `ETUDES/` | outils de fact-checking existants, et bancs de transcription |
| `ETUDES/preinscription-accord.md` | le protocole, écrit **avant** la mesure |
| `ETUDES/accord-transcriptions.md` | ce que la mesure a rendu, y compris son échec |
