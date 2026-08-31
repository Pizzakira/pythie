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
étage 0  triggers    regex, coût nul, auditable        triggers.py
étage 1  triage      appel modèle court, sortie tôt    pipeline.py
étage 2  verify      modèle + base locale fermée       verify.py
étage 3  render      HTML deux degrés + JSON           render.py
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
python scripts/run_poc.py data/debat.json --degree 2 --out data/debat
```

On ne télécharge pas la vidéo, seulement les sous-titres — et on ne republie
pas la transcription intégrale : seuls les extraits analysés sont affichés.

## Conventions

- **Code, identifiants et commentaires : anglais.** Sans exception.
- **Documentation, cahier des charges, corpus : français.**
- Les prompts sont en français : la matière analysée l'est.

## État

Étages déterministes implémentés et testés : déclencheurs (insensibles aux
accents, car l'ASR les mutile), corpus et rangs, règle de provenance, seuils,
rendu deux degrés.

Étages modèle branchés sur Qwen3.8-27B local. **Qualité de sortie non encore
réglée** — le routage fonctionne, l'étape verdict échoue encore souvent par
troncature ou citation reconstituée. Point ouvert assumé.

Voir `SPECIFICATIONS.md` pour le cahier complet et `ETUDES/` pour l'étude des
outils existants.
