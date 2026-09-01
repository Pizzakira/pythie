# Pythie — cahier de spécifications

Document de référence unique. Toute décision arrêtée figure ici ; le fil de
discussion ne fait pas foi.

Version 0.2 — 31 août 2026

---

## Lecture pyramidale

Ce document se lit à quatre profondeurs. **Chaque niveau se suffit à lui-même** :
on s'arrête où l'on a la réponse cherchée, sans avoir besoin du suivant.

```
                        ┌───────────────┐
              NIVEAU 0  │   UNE PHRASE  │   ce que c'est
                        └───────┬───────┘
                    ┌───────────┴───────────┐
          NIVEAU 1  │  CINQ PRINCIPES       │   ce qui gouverne
                    │  + LA CHAÎNE          │   toutes les décisions
                    └───────────┬───────────┘
              ┌─────────────────┴─────────────────┐
    NIVEAU 2  │      TREIZE MODULES               │   de quoi c'est fait
              └─────────────────┬─────────────────┘
        ┌───────────────────────┴───────────────────────┐
NIVEAU 3│  SPÉCIFICATION DE CHAQUE MODULE               │   comment ça marche
        └───────────────────────────────────────────────┘
```

### Niveau 0 — une phrase

> Pythie compare chaque valeur énoncée dans un débat à celle publiée par une
> source primaire, et la rapporte comme exacte, approximative ou fausse.
> Elle ne juge ni la rhétorique ni les intentions.

### Niveau 1 — ce qui gouverne tout

Cinq principes, un corollaire, cinq étages. Si vous ne lisez qu'une page, lisez
la section II et le schéma de la section III : tout le reste en découle
mécaniquement.

Le principe le plus lourd de conséquences tient en une ligne : **une
attribution fausse est pire qu'une absence d'attribution**, parce qu'elle
fabrique une citation au lieu de se tromper sur un verdict. C'est de lui que
viennent toutes les abstentions du système.

### Niveau 2 — treize modules

Le tableau de la section III. Il dit ce qui existe, ce qui reste à écrire, et
ce qui manque.

### Niveau 3 — la spécification

Section IV, un module par sous-section, dans l'ordre de la chaîne.

---

# I. Ce que fait Pythie

Lit ce qui est dit dans un débat, compare chaque valeur énoncée à la valeur
publiée par une source primaire, et la rapporte comme **exacte**,
**approximative** ou **fausse**.

## I.1 Hors périmètre — décision structurante

L'outil **n'analyse pas la rhétorique**, ne qualifie aucun procédé de discours,
et **ne mesure aucune intention**. « Faux » signifie *l'énoncé ne correspond pas
à la source*, jamais *le locuteur a menti*.

Emphases, figures de style et attaques personnelles ne sont pas prises en
compte : elles sortent au tri et ne sont jamais marquées. **Exception unique** :
lorsqu'une figure contient une valeur testable — « on a dépensé quarante
milliards dans ce gouffre » — la valeur est vérifiée et la figure ignorée.

**Conséquence assumée : un énoncé rigoureusement vrai est vert, même s'il est
incomplet ou orienté.** Juger cela supposerait de lire une intention.

## I.2 Hors périmètre — commercial

Aucune logique de produit, de monétisation ni de capitalisation. Les deux
degrés de restitution ne sont pas un entonnoir d'acquisition : ce sont deux
niveaux de précision du même travail.

---

# II. Les cinq principes

Tous appliqués **par le programme**, jamais par le modèle. C'est ce qui les rend
opposables.

**1. Les paramètres du modèle ne sont pas une source.**
Aucun chiffre ne peut venir de ce que le modèle « sait ». Toute valeur doit
provenir d'un document effectivement fourni. Sans document : `unverified`. Il
n'existe aucun verdict de repli.

**2. Une fiche oriente, elle ne prouve jamais.**
Les `FICHE.md` sont nos propres synthèses ; s'en servir comme preuve serait
circulaire. Toute citation retenue doit provenir d'un fichier sous `sources/`.

**3. Un verdict ne peut pas être plus fort que sa source.**
Un `false` exige une source de rang 1. Mécanique, pas discrétionnaire.

**4. Le modèle juge, le programme ne peut qu'affaiblir.**
Le modèle est le juge — c'est sa fonction. Le programme choisit ce qu'il voit
et peut retirer un verdict, jamais en fabriquer un. Un « exact » assorti d'un
écart de 40 % est une incohérence interne : abstention, pas accusation.

**5. Le désaccord est une abstention, pas un vote.**
Partout où deux sources d'information divergent — deux transcriptions, deux
couches de diarisation, deux occurrences d'une affirmation, deux niveaux de
modèle — on ne tranche pas : on retire le verdict. Deux lectures
contradictoires signifient qu'on ne sait pas.

### Le corollaire qui gouverne l'attribution

**Une attribution fausse est pire qu'une absence d'attribution.**

Attribuer une affirmation au mauvais locuteur, ou juger une phrase mal
transcrite, ne produit pas un verdict erroné : ça produit une **citation
fabriquée**. C'est la pire sortie possible. D'où : sous le seuil de
reconnaissance vocale, en cas de paroles superposées, ou en cas de désaccord
entre transcriptions sur un chiffre — **on n'attribue pas et on ne juge pas**.

---

# III. Architecture générale

Cinq étages en série, deux couches transverses, une couche humaine.

```
ACQUISITION → TEXTE → ATTRIBUTION → ANALYSE → RESTITUTION
      └──────────────── MÉMOIRE ────────────────┘
      └──────────────── TRAÇABILITÉ ────────────┘
                   GOUVERNANCE (humaine)
```

| # | Module | Rôle |
|---|---|---|
| 1 | Acquisition | flux, audio, sous-titres, normalisation |
| 2 | Transcription | trois sources, accord restreint aux valeurs |
| 3 | Attribution | empreintes vocales, consensus, rejet |
| 4 | Déclencheurs | étage 0 déterministe, sans modèle |
| 5 | Moteur de score | tri, routage, verdict, garde-fous |
| 6 | Module LLM | backends interchangeables, escalade |
| 7 | **Mémoire** | corpus · profils · registre (trois horizons) |
| 8 | Diffusion | SSE, corrections rétroactives |
| 9 | Interface | deux degrés, filtres, compteurs, recherche |
| 10 | Backoffice | retrait humain, relecture, édition |
| 11 | Traçabilité | journal d'audit, versions, reproductibilité |
| 12 | **Évaluation** | jeu étalon, métriques de publiabilité |
| 13 | Gouvernance | méthodologie, correction, droit de réponse |

---

# IV. Les modules

## 1. Acquisition

`pythie/media/audio.py`

On télécharge **l'audio seul**, jamais la vidéo, et on ne republie jamais la
transcription intégrale : seuls les extraits analysés sont affichés. Reproduire
in extenso un débat diffusé serait une reproduction d'œuvre protégée.

Normalisation unique en **16 kHz mono PCM** : tout l'aval (VAD, empreintes,
ASR) l'attend, et la même entrée redonne toujours les mêmes échantillons.

## 2. Transcription

`ETUDES/transcription.md`

**L'enjeu principal du projet.** Une transcription infidèle produit une citation
fabriquée : « 2,7 millions » devenu « 27 millions » donne un rouge parfaitement
sourcé sur une phrase que personne n'a prononcée.

### Trois sources, trois architectures

| Rôle | Système | Pourquoi |
|---|---|---|
| Direct (degré 1) | **Kyutai `stt-1b-en_fr`** | 0,5 s de délai, français natif, horodatage au mot, VAD sémantique inclus. *Non installé.* |
| Référence (degré 2) | **`faster-whisper-large-v3`** | 7/7 sur les patronymes, 14,5× le direct, aucune boucle d'hallucination (D-045) |
| Deuxième voix | **CrisperWhisper 2.0** | architecture distincte : c'est lui qui rattrape « quinquennat » là où les deux Whisper écrivent « café » |
| Contrôle | **Sous-titres YouTube** | gratuit, immédiat, pile étrangère — mais 36 % seulement sur les patronymes |

> **Écarté le 01/09/2026 (D-046)** : `whisper-large-v3-french`. Mesuré sur
> 5 minutes réelles — boucle d'hallucination d'une quarantaine de répétitions,
> 4× plus lent, écrit « 210 1000000000 » au lieu de « 210 milliards ». Reste
> candidat après conversion CTranslate2, la comparaison actuelle lui étant
> défavorable pour des raisons de configuration autant que de modèle.

**Piège à ne pas commettre : deux variantes de Whisper ne comptent pas pour deux
voix.** Un fine-tune partage l'architecture et les modes de défaillance de son
modèle d'origine. L'accord n'a valeur de preuve qu'entre architectures
distinctes.

### L'accord ne porte que sur les valeurs

Pas la prose. « Il y a » contre « on compte » : sans importance. **« 2,7 »
contre « 27 » : bloquant**, aucun verdict n'est rendu sur cet empan.

Cible bien plus atteignable que l'accord phrase à phrase, et c'est exactement
ce qui détermine la justesse du verdict.

### Réécoute ciblée

Un déclencheur numérique donne son horodatage. On extrait les trois secondes
autour et on relance l'ASR sur ce seul fragment. **Le chiffre est réécouté
avant d'être jugé.** L'alignement à ±50 ms est ce qui rend ce découpage
possible.

### Garde-fous anti-hallucination

Whisper invente du texte fluide sur le silence et la musique. Trois
protections : ne transcrire que là où le VAD détecte de la parole ; rejeter les
segments à `no_speech_prob` élevé ou `avg_logprob` bas ; rejeter les ratios de
compression anormaux, signature des boucles de répétition.

## 3. Attribution

`pythie/media/voiceprint.py` · `consensus.py` · `align.py`

**Ce n'est pas de la diarisation en ensemble ouvert.** Le plateau est connu :
les candidats sont une liste finie et publiée, les animateurs et journalistes
reviennent d'un plateau à l'autre. Tous sont **enrôlés à l'avance** depuis les
enregistrements référencés dans leurs dossiers.

Le clustering non supervisé devient une recherche du plus proche voisin avec
seuil de rejet.

### Deux couches complémentaires, pas des alternatives

- **Segmentation** (pyannote) : *où* le locuteur change, *où* les voix se
  superposent — mais des étiquettes anonymes
- **Empreintes** : *qui* c'est — mais aucune détection de chevauchement

On fait tourner les deux. **Accord → on attribue. Désaccord ou chevauchement →
abstention.**

### Règles de rejet

- similarité sous le seuil (0,62) → non attribué
- marge trop faible entre deux voix enrôlées (< 0,06) → non attribué
- moins de 75 % des fenêtres concordantes → non attribué
- paroles superposées → non attribué, quelle que soit la confiance
- **enrôlement sur moins de trois enregistrements → refusé** : une empreinte
  bâtie sur un seul extrait capture le micro, pas la voix

### Rôles

Le médiateur et les journalistes sont enrôlés eux aussi. Étant identifiés de
façon fiable, la règle « le médiateur n'est pas analysé » s'applique
automatiquement.

## 4. Déclencheurs

`pythie/triggers.py`

Étage 0, sans modèle. Coût nul, latence nulle, **auditable** : un regex se
vérifie, un jugement de modèle ne se vérifie pas.

Types : `percentage` `amount` `date_or_period` `superlative` `comparative`
`vague_quantifier` `causality` `pledge` `attribution` `number`.

Appariement sur une copie **désaccentuée de longueur préservée** — l'ASR et les
sous-titres automatiques mutilent systématiquement les accents ; les index
restent valides et l'empan renvoyé est l'original.

Limite assumée : les déclencheurs attrapent le chiffré, pas le qualitatif. D'où
le partage entre degré 1 (piloté par déclencheurs) et degré 2 (balayage
sémantique complet).

## 5. Moteur de score

`pythie/verify.py` · `brief.py` · `pipeline.py`

### L'échelle

| État | Couleur | Soulignement | Condition |
|---|---|---|---|
| `exact` | vert pâle | plein | valeur confirmée |
| `approximate` | orange | tireté | écart de 5 % à 25 % |
| `false` | rouge foncé | ondulé | contredite — **rang 1 exigé** |
| `too_vague` | gris | pointillé | défaut de l'énoncé |
| `conflicting_sources` | gris | pointillé | définitions incompatibles, pas une faute du locuteur |
| `unverified` | gris | pointillé | **défaut de notre système** |
| `pending` | — | tireté | vérification en cours |
| `out_of_scope` | aucune | aucun | rhétorique, opinion, engagement |

**Seuils publiés d'avance et appliqués par le programme** : ≤ 5 % exact ·
5–25 % approximatif · > 25 % faux. Un seuil que le modèle interpréterait ne
serait pas opposable.

### Trois qualificatifs, purement factuels

`ordre de grandeur approximatif` · `donnée d'une autre date` · `définition non
comparable`. Ils disent à quoi la comparaison a été faite ; ils n'accusent
personne.

### Règle de péremption

Un chiffre exact **à une date ancienne** est signalé à l'aune de la date
courante, et **les deux valeurs sont affichées avec leur millésime**. Un chiffre
juste en 2000 présenté au présent n'est pas exact.

### Fiche composée dynamiquement

Le modèle ne reçoit pas la base entière mais une fiche **composée pour
l'affirmation en cours** : définitions applicables, pièges correspondants,
liste courte des sources à ouvrir.

Le routage est **déterministe et journalisable** — appariement de termes contre
le glossaire, sans appel modèle. Le contexte reste constant quelle que soit la
taille du corpus.

### Troisième axe : cohérence

Un engagement n'est ni vrai ni faux, mais il se confronte au programme publié :
`consistent` · `divergent` · `absent` · `contradicted`. **Aucun verdict de
vérité n'est émis sur un engagement.**

## 6. Module LLM

`pythie/backend.py`

Pythie ne parle jamais à un modèle, elle parle à un `Backend`. Tout fournisseur
capable de rendre du JSON conforme se branche.

| Backend | Usage |
|---|---|
| `LocalBackend` | llama.cpp, décodage contraint par grammaire GBNF |
| `OpenAIBackend` | Qwen (DashScope), Mistral, DeepSeek, OpenRouter, vLLM |
| `AnthropicBackend` | Claude, pour l'escalade |
| `EscalatingBackend` | modèle local partout, modèle fort là où ça compte |

### L'escalade

Le modèle local traite tout. **Seule une affirmation qui s'oriente vers un rouge
est escaladée** vers un modèle fort. Les rouges sont rares et ce sont eux qui
exposent : la dépense reste proportionnelle au risque, pas au volume. Désaccord
entre les deux niveaux → abstention.

### Ce qui n'est pas un backend

Une session Claude Code interactive n'est pas un point de terminaison. Le
détournement en backend d'inférence est écarté ; la contribution légitime de
Claude est **l'écriture du corpus et du jeu étalon**, en amont, sous forme de
fichiers versionnés.

## 7. Mémoire — trois horizons

Une seule fonction, trois durées de vie.

### 7.1 Corpus — permanent

`corpus/base/` · `corpus/sources.yaml` · `corpus/glossaire.yaml`

**Donnée stable, écrite en amont, versionnée dans git.** Aucun agent n'y écrit
pendant un débat : la reproductibilité impose que la même affirmation vérifiée à
12:04 et à 14:20 rencontre la même base.

Structure pyramidale :

```
corpus/base/
  INDEX.md                  niveau 0 — quels domaines existent
  <domaine>/
    FICHE.md                niveau 1 — où trouver quoi, quels pièges
    sources/
      <fichier>             niveau 2 — LA SOURCE PRIMAIRE stockée
      <fichier>.meta.yaml   url d'origine, millésime, empreinte, rang
```

Rangs : **1** producteurs de la donnée (INSEE, DARES, France Travail, Eurostat,
Légifrance — et la recherche académique, préprints marqués) · **2**
institutions d'analyse et de contrôle · **3** vérifications déjà publiées, qui
orientent sans jamais prouver · **parole** programmes et votes, recevables pour
la seule cohérence.

**Glossaire sourcé** : aucune définition n'est affirmée par l'outil, chacune est
adossée à la source qui la produit avec un lien profond que le lecteur peut
ouvrir.

**Interdits** : presse généraliste, Wikipédia, réseaux sociaux, sites de partis,
blogs et tribunes. L'accès en lecture au dépôt entier ne pose pas de problème —
le contrôle est en aval : `validate_provenance` rejette toute citation absente
de `sources/`.

### 7.2 Profils candidats — d'un débat à l'autre

`corpus/candidats/`

Constitués **avant** la campagne à partir de sources de première main :
programmes datés et versionnés, discours enregistrés, écrits signés, votes.
Servent trois usages : l'axe cohérence, l'enrôlement vocal, et la
pré-indexation des chiffres récurrents.

**Symétrie obligatoire** : même protocole, même profondeur, pour chaque
candidat. Toute asymétrie est l'angle d'attaque principal contre l'outil.

**Enrichissement encadré.** Une boucle de rétroaction amplifie ses erreurs : un
rouge erroné devenu « erreur récurrente » biaiserait tous les débats suivants et
transformerait l'antériorité en préjugé. Donc l'enrichissement passe par une
**file de relecture** humaine, et une entrée promue reste une **piste** qui
déclenche la vérification normale — jamais un verdict.

### 7.3 Registre d'affirmations — le débat en cours

`pythie/memory.py`

Chaque vérification est un appel **sans état** : contexte neuf, aucun
historique. Ce qui persiste, c'est l'analyse, ici, hors du modèle.

**C'est un registre, pas un cache.** Un cache court-circuiterait — même clé,
verdict stocké, on ne redemande jamais — et un premier verdict faux serait
hérité en silence par toutes les répétitions.

Chaque occurrence est **revérifiée à froid**. Ce qui est réutilisé est le
*travail* : routage, sources ouvertes, grandeur identifiée. Le jugement est
rejoué.

La répétition devient une épreuve :
- **accord** entre occurrences indépendantes → confiance renforcée (bonus
  modeste : deux passes du même modèle ne sont pas pleinement indépendantes)
- **désaccord** → verdict retiré sur *toutes* les occurrences, y compris celles
  déjà affichées, qui sont **corrigées rétroactivement**
- le conflit est **collant** : une quatrième occurrence ne repart pas à zéro

## 8. Diffusion temps réel

Page mise à jour par **SSE** — flux unidirectionnel, reconnexion native ;
WebSocket inutile, la page ne renvoie rien.

| Événement | Délai | Effet |
|---|---|---|
| `bloc` | ~15 s | ajoute le texte, marques en attente |
| `verdict` | ~30 s | patche l'empan par son id |
| `revision` | variable | réécrit un verdict déjà affiché |
| `retrait` | humain | neutralise un bloc |

**Une analyse par flux, pas par spectateur** : le serveur analyse une fois et
diffuse à N clients. Une inférence par utilisateur rendrait le coût
proportionnel à l'audience.

Budget de latence assumé : HLS 10–30 s · ASR 1–3 s · segmentation < 1 s ·
verdict 3–15 s → **20 à 45 secondes**. Non combattu : la restitution est un fil
qui défile, pas une incrustation synchrone.

## 9. Interface

`pythie/render.py` · maquette dans `mockup/`

**Degré 1 — pendant.** Colonne unique, vert / orange / rouge, étiquette et
**minutage en fin de bloc**. Filtres, compteurs par locuteur et recherche
présents dès le direct. Format débat (2 à n intervenants) ou discours unique
avec médiateur.

**Degré 2 — après.** Même matière, précision supérieure : valeurs comparées avec
écart, millésime, cohérence au programme, sources dépliables.

**Accessibilité** — la couleur n'est jamais le seul canal : soulignement et
glyphe distincts par état, état présent dans le JSON et l'`aria-label`,
luminances séparées pour la deutéranopie (~8 % des hommes). Le soulignement
ondulé de l'erreur reprend l'idiome du correcteur orthographique, déjà installé
chez le lecteur.

**Critère d'acceptation : la page en niveaux de gris reste entièrement
lisible.** Un bouton de test l'exécute dans l'interface.

## 10. Backoffice

Un relecteur humain peut **retirer un bloc à tout moment** : le texte reste
affiché, l'analyse est débranchée, l'interface redevient neutre, en attente de
révision. Les passages sont éditables.

Un bloc retiré ne peut pas revenir par la porte de l'enrichissement de profil.

## 11. Traçabilité

Ce qui sauve en cas de contestation : *« ce verdict a été produit le 12 mars
contre le corpus version 2027-03-01, source INSEE série X millésime T4 2026,
citation vérifiée littéralement »*.

- version du corpus attachée à chaque restitution
- journal des réutilisations de travail et des revérifications
- journal des révisions rétroactives, avec leur motif
- `CHANGELOG.md` daté pour toute modification du corpus — une modification
  silencieuse est une faute
- l'état existe dans le JSON, pas seulement dans le pixel

## 12. Évaluation

**Le module qui décide de la valeur de tous les autres.** Sans lui, on ne sait
pas si Pythie est juste huit fois sur dix ou trois fois sur dix — et un système
faux quatre fois sur dix qui affiche des rouges sur des candidats est un
générateur de contentieux.

### Le jeu étalon

Cent affirmations d'un débat passé, chacune annotée à la main : verdict, source
primaire réelle, grandeur invoquée, millésime, citation. C'est la copie du
correcteur.

Le débat de l'entre-deux-tours 2022 est le bon matériau : les vérifications
publiées à l'époque par l'AFP, les Décodeurs et CheckNews fournissent une
vérité terrain gratuite.

**Piège méthodologique** : le corpus actuel contient des données révisées depuis.
Il faut épingler le millésime disponible à l'époque, sinon on mesure autre
chose.

### Les métriques, dans l'ordre

1. **Taux de faux rouges** — affirmations vraies marquées fausses. **Décide de
   la publiabilité.** Chacune est un contentieux potentiel.
2. **Taux d'abstention** — un système qui n'avoue jamais son ignorance ment.
3. **Citations non retrouvées** — mesure directe de l'hallucination.
4. Rappel sur l'ensemble vérifié par les humains, accord des verdicts.

### Repère externe

L'état de l'art plafonne à **63 %** sur AVeriTeC, et **33 %** sous contrainte
d'une minute par verdict. Toute prétention supérieure doit être prouvée. Leur
métrique est déjà la nôtre : *un verdict ne compte que si la preuve tient*.

## 13. Gouvernance

Non logicielle, et sans elle le reste est inexploitable.

- **Méthodologie publiée avant** toute analyse : périmètre, échelle, seuils,
  corpus complet, protocole de profilage, procédure de correction.
- **Procédure de correction publique** et droit de réponse documentés d'avance.
- **Gel du service** pendant la période de silence électoral.
- **Validation juridique** de la chaîne éditoriale et de la responsabilité de
  publication par un avocat en droit de la presse, avant mise en ligne.
- **Symétrie de traitement** vérifiable entre candidats.

Rappel de marché : 45 % des Français jugent les fact-checkers biaisés et 43 %
estiment qu'ils divisent en imposant « une » vérité. La méthodologie publiée est
**nécessaire et insuffisante** — NewsGuard le démontre. C'est pourquoi le
périmètre est volontairement étroit : on compare des valeurs, on ne juge pas des
intentions.

---

# V. Conventions

- **Code, identifiants et commentaires : anglais.** Sans exception.
- **Documentation, cahier, corpus : français.**
- Les prompts sont en français : la matière analysée l'est.

---

# VI. État au 31 août 2026

| Module | État |
|---|---|
| Déclencheurs, corpus et rangs, provenance, seuils, registre, consensus, rendu | écrit et testé |
| Backends, vérification, empreintes, alignement, profils, fiche dynamique | écrit, non éprouvé |
| Transcription | audité, écrite (`scripts/transcribe.py`) |
| Accord entre transcriptions | écrit et mesuré, **sans autorité de publication** |
| Diffusion SSE, backoffice | conçu, non écrit |
| **Évaluation** | **inexistant** |
| Base de connaissances | **1 domaine sur ~8** |

Qualité de sortie du modèle local : le routage fonctionne, l'étape verdict
rend désormais des verdicts réels et sourcés. Deux défauts corrigés le
01/09/2026 — des sources mises en page avec des points de conduite, donc
inquotables, et un champ `sources` facultatif que la grammaire laissait omettre.

Transcription : `faster-whisper-large-v3` retenu comme référence (D-045). Le
fine-tune français est écarté — après conversion CTranslate2, il ne boucle plus
et devient le plus rapide, mais il écrit les échelles en chiffres, ce qui coupe
chaque valeur en deux (D-046, reformulé le 01/09).

L'accord entre sources est implémenté (étage 0.5) et mesuré : 78 % des énoncés
chiffrés du débat sont corroborés par une seconde famille d'ASR, un cinquième
ne l'est pas. Le banc pré-inscrit qui devait le valider a **échoué**, donc la
couche ne débloque rien et **aucun rouge n'est publié** (D-044, désormais
appliqué par le programme — D-055). Voir `ETUDES/accord-transcriptions.md`.

Ce même banc a corrigé le diagnostic du 31/08 : le premier rouge du système ne
venait pas d'une corruption d'ASR mais d'une phrase réellement prononcée **par
l'animateur**. Le maillon manquant est l'attribution, pas la transcription.

Reproductibilité au niveau du verdict : **non tenue**, mesurée. Voir METHODE §3.

## Ordre des chantiers

1. **Le jeu étalon** — il conditionne le jugement porté sur tout le reste.
2. **L'attribution des locuteurs** — remontée de la quatrième à la deuxième
   place le 01/09 : sans elle, la règle « seuls les candidats sont analysés »
   (D-040) ne s'applique à rien, et c'est ce défaut qui a produit le premier
   rouge du projet.
3. **Le corpus** — sans lui Pythie ne peut répondre qu'`unverified`.
4. La troisième source de transcription (Kyutai ou Voxtral) : avec deux
   familles on détecte un désaccord, avec trois on peut l'arbitrer.
5. Le reste.

---

# Journal des décisions

| Date | Décision |
|---|---|
| 31/08 | Abandon de la monétisation et de la logique produit |
| 31/08 | Abandon de l'analyse de cadrage et de l'énoncé complété |
| 31/08 | Périmètre restreint : vrai / faux / approximatif, sans lecture d'intention |
| 31/08 | Orange = écart numérique mesuré uniquement, seuils publiés |
| 31/08 | Interdit fort appliqué par construction, pas par consigne |
| 31/08 | Recherche académique en rang 1, préprints marqués |
| 31/08 | Filtres, compteurs et recherche dès le degré 1 |
| 31/08 | Profilage préalable des candidats sur sources de première main |
| 31/08 | Erreurs récurrentes : piste, jamais verdict |
| 31/08 | Projet renommé Pythie (collision avec le FacTool académique) |
| 31/08 | Modèle local llama.cpp par défaut, backends interchangeables |
| 31/08 | Le programme ne peut qu'affaiblir un verdict, jamais le renforcer |
| 31/08 | Cache remplacé par un registre : revérification à chaque occurrence |
| 31/08 | Diarisation en ensemble fermé par empreintes enrôlées |
| 31/08 | Trois transcriptions d'architectures distinctes, accord sur les valeurs |
| 31/08 | Escalade vers un modèle fort sur les seuls rouges |
| 31/08 | Modules 7-8-9 regroupés : la mémoire est une fonction à trois horizons |
| 01/09 | La famille d'un ASR est déclarée dans le fichier, jamais devinée |
| 01/09 | L'accord entre transcriptions porte sur le chiffre, ancré par son contexte |
| 01/09 | Le silence d'un témoin n'est pas une confirmation |
| 01/09 | Aucun rouge publié : garanti par le programme, pas par la consigne |
| 01/09 | Une grandeur en pourcentage se compare en points |
| 01/09 | Première mesure pré-inscrite ; son cas témoin a échoué, et le protocole a été suivi |
| 01/09 | Fine-tune français écarté pour la graphie des échelles, non plus pour la boucle |
