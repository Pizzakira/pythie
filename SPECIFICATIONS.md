# FacTool — cahier de spécifications fonctionnelles

Document de référence unique. Toute décision arrêtée figure ici ; le fil de
discussion ne fait pas foi. Toute modification est datée en fin de document.

Version 0.1 — 31 août 2026

---

# PARTIE I — MÉTIER

## 1. Objet

Comparer une valeur énoncée dans un débat politique à la valeur publiée par une
source primaire, et dire si elle est **exacte**, **approximative** ou **fausse**.

### 1.1 Hors périmètre — décision structurante

L'outil **n'analyse pas la rhétorique**, ne qualifie aucun procédé de discours,
et **ne mesure aucune intention**. « Faux » signifie *l'énoncé ne correspond pas
à la source*, jamais *le locuteur a menti*.

Emphases, figures de style et attaques personnelles ne sont pas prises en
compte : elles sortent au tri et ne sont jamais marquées. **Exception unique** :
lorsqu'une figure contient une valeur testable (« on a dépensé quarante
milliards dans ce gouffre »), la valeur est vérifiée et la figure ignorée.

**Conséquence assumée : un énoncé rigoureusement vrai est vert, même s'il est
incomplet ou orienté.** Juger cela supposerait de lire une intention.

> Décision du 31/08/2026 — abandon de l'analyse de cadrage (« étiquettes de
> manœuvre », « énoncé complété ») initialement envisagée. Elle exigeait
> précisément le jugement que l'outil refuse de rendre, et constituait sa
> surface d'attaque principale.

### 1.2 Hors périmètre — commercial

Aucune logique de produit, de monétisation ni de capitalisation. Aucun appel à
l'action. Les deux degrés de restitution ne sont pas un entonnoir d'acquisition :
ce sont deux niveaux de précision du même travail.

## 2. L'échelle

| État | Couleur | Soulignement | Glyphe | Condition |
|---|---|---|---|---|
| Exact | vert pâle | plein | ✓ | valeur confirmée par une source primaire |
| Approximatif | orange | tireté | ≈ | écart relatif de 5 % à 25 % |
| Faux | rouge foncé | ondulé | ✗ | valeur contredite — **source de rang 1 exigée** |
| Trop vague | gris | pointillé | ? | défaut de l'énoncé, non testable en l'état |
| Sources divergentes | gris | pointillé | ⇄ | définitions incompatibles — pas une faute du locuteur |
| Non vérifié | gris | pointillé | ○ | **défaut de notre système**, affiché comme tel |
| En attente | — | tireté clignotant | ⋯ | vérification en cours |
| Hors périmètre | aucun | aucun | — | rhétorique, opinion, engagement |

### 2.1 Seuils, publiés à l'avance

- écart ≤ **5 %** → exact, qualifié « ordre de grandeur approximatif »
- **5 % < écart ≤ 25 %** → approximatif
- **> 25 %**, ou sens de variation inversé, ou ordre de grandeur erroné → faux

Appliqués **par le programme**, jamais par le modèle. Un seuil que le modèle
interpréterait ne serait pas opposable.

### 2.2 Trois qualificatifs, purement factuels

`ordre de grandeur approximatif` · `donnée d'une autre date` ·
`définition non comparable`. Ils disent à quoi la comparaison a été faite ; ils
n'accusent personne.

### 2.3 Règle de péremption

Un chiffre exact **à une date ancienne** est signalé à l'aune de la date
courante. Si la source la plus récente donne une autre valeur, l'énoncé porte
`donnée d'une autre date`, et **les deux valeurs sont affichées avec leur
millésime**. Un chiffre juste en 2000 et présenté au présent n'est pas exact.

## 3. Le corpus

Fermé, hiérarchisé, publié (`corpus/sources.yaml`). **Le rang de la source
plafonne la force du verdict.**

| Rang | Contenu | Verdict autorisé |
|---|---|---|
| 1 | Producteurs de la donnée : INSEE, DARES, DREES, France Travail, SSMSI, Banque de France, Légifrance, Eurostat, OCDE — **et la recherche académique** (arXiv, HAL, Cairn, Persée, PubMed, revues à comité) | tous, **faux** compris |
| 2 | Institutions d'analyse et de contrôle : Cour des comptes, HCFP, France Stratégie, OFCE, IPP, Assemblée, Sénat | **exact** au mieux |
| 3 | Vérifications déjà publiées (AFP Factuel, Décodeurs, CheckNews…) | **aucun** — orientent, ne prouvent pas |
| parole | Programmes, déclarations datées, scrutins | **cohérence uniquement**, jamais un fait |

**Préprints** (arXiv, HAL en dépôt simple) : rang 1, mais le marqueur
`prépublication` est obligatoire — ils ne sont pas relus par les pairs.

### 3.1 L'interdit fort

Exclus comme preuve : presse généraliste, Wikipédia, réseaux sociaux, sites de
partis, blogs et tribunes.

> **Les paramètres du modèle ne sont pas une source.** Aucun chiffre ne peut
> venir de ce que le modèle « sait ». Toute valeur doit avoir été extraite d'un
> document effectivement récupéré. Sans document : `non vérifié`. **Il n'existe
> aucun verdict de repli.**

L'interdit est appliqué **côté serveur** via `allowed_domains` de l'outil
`web_search` : le modèle n'a pas accès aux domaines absents de la liste. Ce
n'est pas une consigne contournable, c'est une propriété de la requête.

### 3.2 Exigence de traçabilité

**Toujours une source précise ET vérifiable par le lecteur.** Le lien doit
pointer la série, le tableau ou l'article — jamais une page d'accueil. La
citation exacte et le millésime sont affichés. Le lecteur doit pouvoir ouvrir
et constater lui-même.

### 3.3 Glossaire sourcé

`corpus/glossaire.yaml`. **Aucune définition n'est affirmée par l'outil** :
chacune est adossée à la source qui la produit, avec lien profond. Une
définition sans source n'entre pas dans le glossaire.

Termes couverts : chômage (BIT / catégorie A / A+B+C), inflation (IPC / IPCH),
PIB (volume / valeur), immigré (immigré INSEE / étranger / titres de séjour),
dette publique, pauvreté, pouvoir d'achat, délinquance.

Le glossaire est consulté **avant** toute recherche : il tranche
déterministiquement la grandeur invoquée, plus vite qu'une recherche et plus
sûrement qu'un jugement de modèle.

## 4. Profilage préalable des candidats

Le nombre de candidats est fini et connu à l'avance. Chacun fait l'objet d'un
dossier constitué **avant** la campagne, à partir de **sources de première
main** : discours prononcés, interventions enregistrées, productions écrites,
programme publié, votes.

### 4.1 Contenu d'un dossier candidat

`corpus/candidats/<id>.yaml`

| Section | Contenu | Usage |
|---|---|---|
| `programme` | éditions successives, datées et versionnées | axe cohérence |
| `discours` | interventions enregistrées, transcrites, horodatées | axe cohérence |
| `ecrits` | livres, tribunes signées, propositions de loi | axe cohérence |
| `votes` | scrutins publics (Assemblée, Sénat) | axe cohérence |
| `chiffres_recurrents` | valeurs qu'il cite habituellement, avec leur source réelle | pré-indexation |
| `erreurs_recurrentes` | énoncés déjà vérifiés et déjà démentis | détection amont |

### 4.2 Analyse des erreurs récurrentes

Constituée en amont sur les vérifications publiées et les analyses
universitaires. Un énoncé déjà démenti et répété est **reconnu immédiatement**
plutôt que revérifié : gain de latence et cohérence entre occurrences.

**Garde-fou obligatoire.** Une correspondance avec une erreur récurrente
**n'est jamais un verdict** : elle est une piste qui déclenche la vérification
normale contre la source primaire. Sans cette règle, l'outil condamnerait un
locuteur pour ce qu'il a dit une autre fois, et l'antériorité deviendrait un
préjugé.

### 4.3 Recueil de lieux communs

`corpus/lieux_communs.yaml`. Affirmations récurrentes du débat public français,
indépendantes du locuteur (« la France est le pays le plus taxé d'Europe »,
« les 40 milliards d'aides aux entreprises »…), documentées à partir
d'**analyses universitaires** et adossées à leur source primaire.

Même garde-fou : oriente, ne conclut pas.

### 4.4 Symétrie

Le dossier est constitué selon le **même protocole, avec la même profondeur,
pour chaque candidat**. Toute asymétrie de traitement est un défaut, et
constitue l'angle d'attaque principal contre l'outil. Le protocole est publié.

## 5. Les deux degrés de restitution

Même matière, deux niveaux de précision. Le second n'a pas un autre usage que
le premier.

**Degré 1 — pendant.** Piloté par les déclencheurs. Colonne unique, vert /
orange / rouge, **étiquette et minutage en fin de bloc**. Filtres, compteurs et
recherche présents **dès le direct**. Rapide, chiffré, forcément partiel.

**Degré 2 — après.** Balayage sémantique complet. S'ajoutent les valeurs
comparées avec leur écart, le millésime, la cohérence avec le programme, et les
sources dépliables.

## 6. Cohérence avec le programme — troisième axe

Un engagement n'est ni vrai ni faux. Il est confronté au programme publié :
`conforme` · `écart` · `absent` · `contradiction`. **Aucun verdict de vérité
n'est émis sur un engagement.**

## 7. Accessibilité

La couleur n'est **jamais** le seul canal : chaque état porte un soulignement
et un glyphe distincts. L'état existe dans le texte (aria) et dans le JSON, pas
seulement dans le pixel. Luminances séparées (vert très pâle, rouge foncé) pour
rester discriminables en deutéranopie — ~8 % des hommes.

**Critère d'acceptation : la page passée en niveaux de gris reste entièrement
lisible.** Un bouton de test l'exécute dans l'interface.

## 8. Publication de la méthodologie

Publiée **avant** toute analyse : périmètre, échelle, seuils, corpus complet,
protocole de profilage, procédure de correction. Toute modification est datée
dans `CHANGELOG.md`. Une modification silencieuse du corpus est une faute.

## 9. Cadre juridique

- Ne pas republier la transcription intégrale : seuls les extraits analysés
  sont affichés — une reproduction in extenso d'un débat diffusé est une
  reproduction d'œuvre protégée.
- Prévoir le gel du service pendant la période de silence électoral.
- Faire valider la chaîne éditoriale et la responsabilité de publication par un
  avocat en droit de la presse **avant** mise en ligne.
- Droit de réponse et procédure de correction publique documentés d'avance.

---

# PARTIE II — TECHNIQUE

## 10. Architecture

```
étage 0   déclencheurs    regex, coût nul, auditable            triggers.py
étage 1   pertinence      modèle court, sortie anticipée        analyze.trier
étage 2   vérification    modèle + corpus fermé                 analyze.verifier
étage 2b  cohérence       engagement vs programme               analyze.verifier_coherence
étage 3   restitution     HTML deux degrés + JSON               render.py
```

Entonnoir à sorties anticipées : un appel modèle n'est payé que sur ce qui a
franchi l'étage précédent.

## 11. Étage 0 — déclencheurs

Déterministe, sans modèle. Types : `pourcentage` `montant` `date_ou_periode`
`superlatif` `comparatif` `quantificateur_vague` `causalite` `engagement`
`attribution` `nombre`.

Appariement sur une copie **désaccentuée de longueur préservée** : les
sous-titres automatiques et l'ASR mutilent systématiquement les accents. Les
index restent valides, l'empan renvoyé est l'original.

Métrique produite : déclencheurs/minute et répartition par type — premier
chiffre à regarder sur un POC, il dit si le format a seulement quelque chose à
vérifier.

## 12. Étages modèle

`claude-opus-5`, thinking adaptatif. Étage 1 en effort `low` (tri bon marché),
étage 2 en effort `high` avec `web_search` + `web_fetch` restreints.

### 12.1 Trois garde-fous, appliqués après le modèle

1. **Citation vérifiée littéralement** — la chaîne citée est recherchée dans le
   document récupéré. Introuvable → verdict retiré. Les modèles citent de façon
   plausible et fausse ; comparer deux chaînes coûte zéro.
2. **Verdict ≤ rang de la source** — un « faux » sans rang 1 est déclassé
   automatiquement.
3. **Pas de source → abstention** — jamais de repli sur la mémoire du modèle.

### 12.2 Indexation préalable

Séries statistiques, glossaire, lieux communs et dossiers candidats sont
téléchargés et indexés **avant** le débat. Une consultation devient
déterministe et instantanée : on gagne la latence et la fiabilité du même
geste.

## 13. Acquisition

Sous-titres YouTube sans téléchargement vidéo. `riplib/transcript.py` du projet
`rip` fournit la logique éprouvée (`youtube-transcript-api`, extraction d'ID,
titre via oembed, gestion fine des erreurs — sous-titres désactivés, blocage
IP, réponse imparsable) ; à porter plutôt qu'à réécrire.

**Non résolu :** les sous-titres automatiques n'identifient pas les locuteurs.
Renseignement manuel pour les POC, diarisation à trancher ensuite.

## 14. Restitution temps réel

Page web mise à jour en direct par **SSE** (unidirectionnel, reconnexion
native ; WebSocket inutile, la page ne renvoie rien).

| Événement | Délai | Effet |
|---|---|---|
| `bloc` | ~15 s | ajoute le texte, marques en « en attente » |
| `verdict` | ~30 s | **patche** l'empan par son id |

**Une analyse par flux, pas par spectateur** : le serveur analyse une fois et
diffuse à N clients. Une inférence par utilisateur rendrait le coût
proportionnel à l'audience.

Le degré 2 est la même page rejouée depuis le JSON final. Si le flux tombe, la
page reste valide avec ce qu'elle a. Filtres, compteurs et recherche opèrent
côté client sur les énoncés accumulés.

## 15. Budget de latence

| Étape | Délai |
|---|---|
| Flux HLS (inhérent) | 10–30 s |
| ASR jusqu'à texte stable | 1–3 s |
| Segmentation | < 1 s |
| Recherche + verdict | 3–15 s |
| **Total** | **~20–45 s** |

Assumé, non combattu : la restitution est un fil qui défile, pas une
incrustation synchrone.

## 16. Métriques d'évaluation

Sur débat archivé, contre les vérifications de presse publiées à l'époque
(vérité terrain gratuite), dans cet ordre :

1. **Nombre de rouges** — chacun est un contentieux potentiel
2. **Taux d'abstention** — un système qui n'avoue jamais son ignorance ment
3. **Citations non retrouvées** — mesure directe de l'hallucination

Puis : rappel sur l'ensemble vérifié par les humains, accord des verdicts,
**faux positifs** (marqués faux à tort — la métrique qui décide de la
publiabilité).

**Piège méthodologique :** le corpus actuel contient des données révisées depuis
la date du débat. Épingler le millésime disponible à l'époque, sinon on mesure
autre chose.

## 17. POC

| # | Objet | Teste | Vérité terrain |
|---|---|---|---|
| 1 | Vidéo enregistrée (LaREF 2026) | chaîne complète, densité, ergonomie | non |
| 2 | Direct réel | capture de flux, latence, tenue en charge | non |
| 3 | Débat archivé (2022) | **qualité des verdicts** | oui |

Ordre : **POC 3 d'abord** — seul capable de tuer le projet. Son cœur d'analyse
est réutilisé tel quel par les deux autres.

## 18. État

Étages déterministes implémentés et testés (déclencheurs, corpus, garde-fous,
rendu deux degrés). Étages modèle écrits, **jamais exécutés** — pas de clé API
disponible à ce jour. Maquette d'interface publiée.

---

## Journal des décisions

| Date | Décision |
|---|---|
| 31/08/2026 | Abandon de la monétisation et de la logique produit |
| 31/08/2026 | Abandon de l'analyse de cadrage et de l'énoncé complété |
| 31/08/2026 | Périmètre restreint : vrai / faux / approximatif, sans lecture d'intention |
| 31/08/2026 | Orange = écart numérique mesuré uniquement, seuils publiés |
| 31/08/2026 | Interdit fort appliqué par `allowed_domains`, pas par prompt |
| 31/08/2026 | Recherche académique classée rang 1, préprints marqués |
| 31/08/2026 | Filtres, compteurs et recherche dès le degré 1 |
| 31/08/2026 | Profilage préalable des candidats sur sources de première main |
| 31/08/2026 | Erreurs récurrentes : piste, jamais verdict |
