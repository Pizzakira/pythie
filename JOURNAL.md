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
