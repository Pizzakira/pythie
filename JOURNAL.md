# Journal de projet — Pythie

Une entrée par session de travail. Chaque entrée consigne les **décisions
prises**, avec leur motif, ce qui a été **écarté** et pourquoi, ce qui reste
**ouvert**, et l'état à la clôture.

Convention : les décisions sont numérotées `D-nnn`, dans l'ordre chronologique,
et référençables depuis le code et le cahier. Une décision renversée n'est
jamais effacée — elle est marquée *révoquée* avec la décision qui la remplace.
On doit pouvoir reconstituer pourquoi le projet est ce qu'il est.

---

## Session 001 — 31 août 2026

**Objet** : cadrage du projet, architecture, socle logiciel.
**Durée** : session longue, conception et implémentation mêlées.

### Contexte de départ

Idée initiale : un outil de fact-checking en temps réel pour la présidentielle
française de 2027 (scrutin des 18 avril et 2 mai). Question d'entrée portant sur
la monétisation d'une audience.

### Décisions

| # | Décision | Motif |
|---|---|---|
| **D-001** | **Abandon de la monétisation et de toute logique produit** | Décision de l'auteur. L'écosystème du fact-checking est subventionné et non commercial ; seuls NewsGuard et Full Fact vendent réellement quelque chose. |
| **D-002** | **Périmètre restreint : vrai / faux / approximatif** | On compare une valeur énoncée à une valeur source. Rien d'autre. |
| **D-003** | **Aucune analyse de rhétorique, aucune mesure d'intention** | « Faux » = l'énoncé ne correspond pas à la source, jamais « le locuteur a menti ». Un énoncé rigoureusement vrai est vert, même incomplet ou orienté. |
| **D-004** | **Abandon de l'analyse de cadrage et de l'« énoncé complété »** | Proposés puis écartés : ils exigeaient précisément le jugement d'intention que D-003 refuse, et constituaient la principale surface d'attaque. |
| **D-005** | **Emphases, figures de style et attaques : non prises en compte** | Sortent au tri, jamais marquées. Exception : une figure contenant une valeur testable est ramenée à cette valeur. |
| **D-006** | **Orange = écart numérique mesuré uniquement** | Un écart se calcule et se défend par un chiffre. « Une liberté a été prise » est une appréciation. |
| **D-007** | **Seuils publiés d'avance, appliqués par le programme** | ≤ 5 % exact · 5–25 % approximatif · > 25 % faux. Un seuil interprété par le modèle ne serait pas opposable. |
| **D-008** | **Corpus fermé et hiérarchisé, interdit fort** | Les paramètres du modèle ne sont pas une source. Sans document récupéré : `unverified`, sans repli. |
| **D-009** | **Une fiche oriente, elle ne prouve jamais** | Une fiche est notre propre synthèse ; la citer serait circulaire. Citation exigée depuis `sources/`, vérifiée littéralement. |
| **D-010** | **Un verdict ne peut pas dépasser le rang de sa source** | Un `false` exige le rang 1. Mécanique, non discrétionnaire. |
| **D-011** | **Recherche académique en rang 1, préprints marqués** | Sur les affirmations scientifiques, la statistique publique n'a rien à dire. Un préprint n'est pas relu par les pairs : marqueur obligatoire. |
| **D-012** | **Deux degrés de restitution, pas deux produits** | Même matière, deux niveaux de précision. Le degré 2 n'a pas un autre usage que le degré 1. |
| **D-013** | **Filtres, compteurs et recherche dès le degré 1** | Décision de l'auteur, contre ma proposition initiale de les réserver au degré 2. |
| **D-014** | **Minutage en fin de bloc** | |
| **D-015** | **La couleur n'est jamais le seul canal** | ~8 % des hommes sont deutéranopes. Critère d'acceptation : la page en niveaux de gris reste lisible. |
| **D-016** | **Retrait humain d'un bloc à tout moment** | Le texte reste affiché, l'analyse est débranchée en attendant relecture. C'est la soupape éditoriale qui rend l'outil publiable. |
| **D-017** | **Profilage préalable des candidats sur sources de première main** | Programmes, discours enregistrés, écrits, votes. Sert la cohérence, l'enrôlement vocal et la pré-indexation. |
| **D-018** | **Erreurs récurrentes : piste, jamais verdict** | Sans cette règle, l'outil condamnerait quelqu'un pour ce qu'il a dit une autre fois, et l'antériorité deviendrait un préjugé. |
| **D-019** | **Cohérence avec le programme : troisième axe** | Un engagement n'est ni vrai ni faux, mais il se confronte au programme publié. Aucun verdict de vérité sur un engagement. |
| **D-020** | **Projet renommé Pythie** | L'étude a révélé une collision : `FacTool` est un projet académique actif (GAIR-NLP), indexé, au périmètre différent. Python + la Pythie interprète les oracles. |
| **D-021** | **Convention de langue : code en anglais, documentation en français** | Identifiants, commentaires, noms de fonctions : anglais sans exception. Prompts en français, la matière analysée l'étant. |
| **D-022** | **Modèle local par défaut (llama.cpp), backends interchangeables** | Sortie du coût par token. `OpenAIBackend` couvre Qwen, Mistral, DeepSeek, OpenRouter, vLLM. |
| **D-023** | **Serveur lancé via le `.bat` de l'auteur, en fenêtre visible** | Rien ne doit tourner de façon invisible. |
| **D-024** | **Le programme ne peut qu'affaiblir un verdict** | Le modèle est le juge. Défaut trouvé et corrigé : `apply_thresholds` fabriquait un rouge que le modèle n'avait pas rendu. Un « exact » assorti d'un écart de 40 % est une incohérence interne, donc une abstention. |
| **D-025** | **Registre d'affirmations, pas cache** | Un cache court-circuitait et un premier verdict faux était hérité en silence. Chaque occurrence est revérifiée ; seul le *travail* est réutilisé. La répétition devient une épreuve. |
| **D-026** | **Désaccord entre occurrences → retrait rétroactif** | Deux lectures contradictoires signifient qu'on ne sait pas. Le conflit est collant. |
| **D-027** | **Diarisation en ensemble fermé, par empreintes enrôlées** | Le plateau est connu ; les journalistes et animateurs reviennent. Le clustering non supervisé devient un plus proche voisin avec rejet. |
| **D-028** | **Une attribution fausse est pire qu'une absence d'attribution** | Elle fabrique une citation au lieu de se tromper sur un verdict. Origine de toutes les abstentions du système. |
| **D-029** | **Segmentation et empreintes sont deux couches, pas des alternatives** | pyannote dit *où*, les empreintes disent *qui*. Accord → attribution ; désaccord ou chevauchement → abstention. |
| **D-030** | **Trois transcriptions d'architectures distinctes** | Deux variantes de Whisper ne comptent pas pour deux voix : un fine-tune partage les modes de défaillance de son modèle d'origine. |
| **D-031** | **L'accord entre transcriptions ne porte que sur les valeurs** | « Il y a » vs « on compte » : sans importance. « 2,7 » vs « 27 » : bloquant. |
| **D-032** | **Réécoute ciblée des chiffres avant jugement** | L'alignement forcé à ±50 ms de WhisperX est ce qui rend le découpage possible. |
| **D-033** | **Corpus stable, écrit en amont, versionné** | Aucun agent n'y écrit pendant un débat : la reproductibilité impose que la même affirmation rencontre la même base à 12:04 et à 14:20. |
| **D-034** | **L'accès en lecture au dépôt entier est sans danger** | Correction d'une restriction excessive de ma part : le contrôle est en aval (`validate_provenance`), pas dans ce que le modèle peut voir. |
| **D-035** | **L'enrichissement passe par une file de relecture** | Une boucle de rétroaction amplifie ses erreurs. Rien n'entre dans le dossier durable sans humain. |
| **D-036** | **Escalade vers un modèle fort sur les seuls rouges** | Les rouges sont rares et ce sont eux qui exposent. La dépense suit le risque, pas le volume. |
| **D-037** | **Modules mémoire regroupés : une fonction, trois horizons** | Corpus (permanent), profils (d'un débat à l'autre), registre (débat en cours). Regroupement décidé par l'auteur. |
| **D-038** | **Passe d'annotation par lot** | Format unique servant de backend intérimaire *et* de jeu étalon : un verdict intérimaire et un verdict de référence sont produits des mêmes preuves et doivent être comparables. Les verdicts ingérés ne reçoivent aucun privilège. |

### Écarté, et pourquoi

- **Détournement d'une session Claude Code en backend d'inférence permanent** —
  ce n'est pas l'usage de l'outil. La contribution légitime est l'écriture du
  corpus et du jeu étalon, en amont, sous forme de fichiers versionnés, et la
  passe par lot de D-038.
- **Réutilisation des identifiants de session** pour un script tiers — même
  motif ; tentative bloquée par le garde-fou de l'environnement.
- **qwen-code comme harnais d'exécution** — sa compression de contexte résout un
  problème que nous n'avons pas (nos appels sont sans état), et lui donner des
  outils fichiers ferait perdre la reproductibilité et le décodage contraint.
  Sa place est dans la *construction* du corpus.
- **LM Studio** — écarté par l'auteur au profit de son propre llama.cpp.

### Corrections que je me suis appliquées

- Affirmation fausse : « l'agent ne rend jamais un verdict ». Le modèle **est**
  le juge ; c'est le programme qui ne juge pas et ne peut qu'opposer un veto.
- Restriction excessive sur l'accès en lecture au corpus (voir D-034).
- Exagération de la charge d'une passe d'annotation par lot, présentée comme
  irréaliste alors qu'elle ne l'est pas. La seule objection valable portait sur
  l'usage de l'outil, pas sur le volume.

### Reste ouvert

- Qualité de sortie du modèle local : le routage fonctionne, l'étape verdict
  échoue encore par troncature ou citation reconstituée.
- Diarisation testée sur vecteurs synthétiques uniquement ; modèles ONNX (VAD,
  empreinte locuteur) non téléchargés.
- Module de transcription audité mais non écrit.
- Diffusion SSE et backoffice conçus, non écrits.
- **Évaluation inexistante** — aucun jeu étalon.
- Base de connaissances : **1 domaine sur ~8**.

### État à la clôture

Dépôt : https://github.com/Pizzakira/pythie

Écrit et testé : déclencheurs (insensibles aux accents), corpus et rangs,
règle de provenance, seuils, registre d'affirmations, consensus de diarisation,
composition de fiche dynamique, rendu deux degrés.

Écrit non éprouvé : backends et escalade, vérification, empreintes vocales,
alignement, profils, passe par lot.

Documenté : `SPECIFICATIONS.md` (cahier, lecture pyramidale à quatre niveaux),
`ETUDES/outils-fact-checking.md`, `ETUDES/transcription.md`, maquette publiée.

### Prochains chantiers, dans l'ordre

1. **Le jeu étalon** — il conditionne le jugement porté sur tout le reste.
2. **Le corpus** — sans lui Pythie ne peut répondre qu'`unverified`.
3. Le module de transcription à trois sources.

---

<!-- Modèle pour les sessions suivantes :

## Session nnn — JJ mois AAAA

**Objet** :
**Participants** :

### Décisions
| # | Décision | Motif |
|---|---|---|
| D-nnn | | |

### Écarté, et pourquoi

### Reste ouvert

### État à la clôture

-->

---

## Session 002 — 31 août 2026 (suite)

**Objet** : itération 1 exécutable, bancs de mesure, corpus finances publiques.

### Décisions

| # | Décision | Motif |
|---|---|---|
| **D-039** | **Seuils en points pour les grandeurs en pourcentage** | Découvert en testant Qwen : « 45,3 % » contre 43,6 % INSEE donne un écart relatif de 3,4 %, sous la barre des 5 %, donc « exact » — alors que c'est 1,7 point de PIB, ~50 Md€. Le relatif écrase l'écart. |
| **D-040** | **Liste blanche : seuls les candidats sont analysés** | Une liste noire laissait passer les rôles ajoutés après coup (hôte, chefs d'entreprise). Tout ce qui n'est pas un candidat identifié est laissé tranquille. |
| **D-041** | **On ne corrige pas les noms dans la transcription** | Mesuré : l'appariement flou fait 4/11 et transforme « le total des dépenses » en Attal ; Qwen fait 5/11 et refuse presque tout. Le signal des noms sert à étiqueter les grappes de diarisation, jamais à réécrire le texte. |
| **D-042** | **`sources` obligatoire dans le schéma de verdict** | Avec une valeur par défaut, la grammaire contrainte laissait le modèle l'omettre : il extrayait la bonne valeur, ne citait rien, et le garde-fou abstenait. Une abstention causée par le schéma, pas par les preuves. |
| **D-043** | **Sources stockées sans points de conduite** | Une mise en page « 2025 ......... 43,6 % » rend la citation littérale impossible. Le contrôle testait la typographie et non la fidélité. |
| **D-044** | **Aucun rouge publié tant que l'accord entre transcriptions n'existe pas** | Voir le constat ci-dessous. |

### Le constat qui commande D-044

Premier rouge produit par la chaîne :

> `FALSE` (99 %) — « Je vous cite de au feu 600 millions de dettes françaises. »
> 600 millions contre 3 460 milliards (INSEE, fin 2025).

Le texte est corrompu — « de au feu ». Le locuteur a dit tout autre chose ; les
« 600 millions » sont une corruption d'ASR. Le système a donc marqué faux, avec
99 % de confiance et un sourçage impeccable, **une phrase que personne n'a
prononcée**.

Ce n'est pas un défaut de code : le verdict est juste si l'on accepte le texte.
C'est que la couche d'accord entre transcriptions n'est pas branchée, et que ce
passage n'aurait jamais dû atteindre l'étage de vérification.

C'est la citation fabriquée que toute l'architecture existe pour empêcher, et
elle est arrivée dès la première passe réelle.

### Ce qui a bien fonctionné

> `CONFLICTING_SOURCES` (90 %) — « Le déficit de l'État est de 150 milliards. »

Le modèle a refusé de comparer : le locuteur dit « l'État », la source couvre
l'ensemble des administrations publiques. Deux périmètres. Le piège signalé par
la fiche d'orientation a été attrapé plutôt que tranché à tort.

### Mesures obtenues

- **Débat LaREF 2026** : 2 233 énoncés, 309 déclencheurs (1,65/min), 173 à
  vérifier. L'étage 0 écarte 92 % pour zéro appel modèle.
- **Qwen** : échoue à diagnostiquer un défaut de données, réussit la
  comparaison de valeur. Le partage supposé est confirmé par la mesure.
- **Noms propres** : à 58:45, sur le même audio, faster-whisper écrit « Bruno
  Retailleau » là où YouTube écrit « Bruno Rota ». Et sur « Talenaissance », ce
  qui compte n'est pas le taux d'erreur mais son type : une déformation reste
  récupérable, une fusion est définitive.
- **Sous-titres** : 537 mots/minute avant correction, 179 après. Le chiffre
  contenait la preuve du bug.

### Reste ouvert

- Seuils en points définis mais **non branchés** dans `apply_thresholds` ; le
  modèle ne remplit pas toujours `stated_value` / `source_value`, ce qui les
  empêche de s'appliquer.
- Corpus : deux domaines sur huit. 24 affirmations sur 40 sortent hors corpus.
- Aucune empreinte vocale : l'étage d'attribution reste simulé.
- **Jeu étalon toujours inexistant.**

---

## Session 003 — 1er septembre 2026

**Objet** : intégration du modèle français, bancs ASR, restitution progressive.

### Décisions

| # | Décision | Motif |
|---|---|---|
| **D-045** | **`faster-whisper-large-v3` est le modèle de référence** | 7/7 sur les patronymes, 14,5× le direct, aucune boucle d'hallucination, formatage correct des nombres. |
| **D-046** | **Le fine-tune français n'entre pas dans la chaîne en l'état** | Mesuré : boucle d'hallucination d'une quarantaine de répétitions sur 5 minutes, 4× plus lent, écrit « 210 1000000000 » au lieu de « 210 milliards ». Reste candidat après conversion CTranslate2. |
| **D-047** | **L'accord entre transcriptions exige une source par famille** | Démontré et non plus supposé : à 150:18 les deux modèles Whisper écrivent « début du café », CrisperWhisper écrit « quinquennat », qui est juste. |
| **D-048** | **Aucune transcription de référence ne sera produite par moi seul** | Je n'ai pas accès au signal audio. Je peux arbitrer entre plusieurs transcriptions, pas transcrire. |
| **D-049** | **Le degré 1 se rejoue** | Les blocs apparaissent à leur minutage, le verdict rejoint la marque après. Le décalage n'est pas masqué : un verdict ne peut pas précéder sa preuve. |
| **D-050** | **Fenêtre d'analyse réglable** (`--depuis`, `--minutes`) | On éprouve sur une fenêtre, pas sur trois heures. |

### Mesures

**Banc noms propres, 9 fenêtres, 11 patronymes, même audio**

| Source | Exacts | Utilisable |
|---|---|---|
| faster-whisper-large-v3 | 8 | 91 % |
| whisper-large-v3-french | 8 | 91 % |
| CrisperWhisper 2.0 | 5 | 64 % |
| Sous-titres YouTube | 3 | **36 %** |

**Passage d'ouverture (les 7 candidats nommés à la suite)** : les trois modèles
font 7/7, les sous-titres 4/7 — ils perdent Retailleau et Glucksmann sur la
phrase même qui présente le plateau. Seul CrisperWhisper récupère « Amélie
Carrouër ».

**Face-à-face français / large-v3, 5 minutes** : large-v3 gagne sur tous les
critères. Détail dans `ETUDES/transcription.md`.

**Chaîne complète, fenêtre 22–32 min** : 2 exact, 1 approximatif, 1 faux,
1 trop vague, 10 non vérifiées.

### Mes erreurs de mesure, consignées

1. **Métrique de répétition aveugle.** `repetition()` a rapporté 0 pour les
   deux modèles alors que la boucle d'hallucination est manifeste. Elle
   comptait les segments consécutifs identiques ; la boucle vit à l'intérieur
   d'un seul bloc de 30 s.
2. **Alignement des chiffres impossible.** Le banc `banc_chiffres.py` alignait
   des blocs de sous-titres fusionnés à 25 s contre des segments Whisper de
   4 s, avec une fenêtre de 6 s. Les « 6 % de part jugeable » ne mesurent rien.
   Correctif : utiliser le fichier de sous-titres ligne à ligne.
3. **Estimation de durée mal formulée.** J'ai annoncé « 1 à 2 heures » sans
   préciser que c'était pour trois modèles sur 3h12. Pour un seul modèle,
   3h12 d'audio prend 10 à 20 minutes.
4. **Quatre fichiers cassés** par le même défaut d'échappement dans des
   heredocs. À proscrire pour tout code contenant des séquences d'échappement.

### Reproductibilité : engagement non tenu

« 45,3 % de prélèvement » a reçu `approximate` à une exécution et `exact` à la
suivante — même corpus, mêmes seuils. `METHODE.md` affirmait la
reproductibilité « tenue par construction » ; c'était faux au niveau du
verdict. Corrigé dans le document et dans son tableau récapitulatif, qui se
contredisaient l'un l'autre.

### Reste ouvert

- Accord entre transcriptions : **non implémenté**. Tant qu'il ne l'est pas,
  aucun rouge ne doit être publié (D-044).
- Corpus : deux domaines. 24 affirmations sur 40 sortent hors périmètre.
- Empreintes vocales : aucune. L'attribution reste simulée.
- Seuils en points : définis, non branchés.
- **Jeu étalon : toujours inexistant.**
- POC 2 : rien. POC 3 : outillage prêt, matière absente.
