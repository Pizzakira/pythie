# Étude systématique des outils de fact-checking

Une fiche par outil : ce qu'il fait, **comment il fonctionne** techniquement,
son modèle, et ce qu'on en retient pour FacTool.

État au 31 août 2026. Sources en fin de fiche.

---

## AVERTISSEMENT — collision de nom

**`FacTool` existe déjà.** C'est un projet académique publié en 2023
(GAIR-NLP), « FacTool: Factuality Detection in Generative AI », avec un dépôt
GitHub actif et un papier arXiv. Il détecte les erreurs factuelles dans les
textes *générés par des LLM* — objet différent du nôtre, nom identique.

Conséquence pratique : toute recherche « factool » renvoie leur projet.
Il faudra trancher — renommer, ou assumer l'homonymie en sachant qu'elle
handicape durablement la visibilité et prête à confusion dans un domaine où la
crédibilité est l'actif principal.

---

# A. Vérification automatisée du discours

## A1. Squash — Duke Reporters' Lab

**Ce qu'il fait.** Vérification automatisée *en direct* pendant débats et
discours. Le pionnier du genre.

**Comment ça marche.** Audio → Google Speech-to-Text → **ClaimBuster** pour
repérer les affirmations vérifiables → appariement avec la base **ClaimReview**
des vérifications *déjà publiées* → affichage à l'écran en quelques secondes,
après sélection humaine.

**Financement.** 1,2 M$ (Knight Foundation, Facebook Journalism Project, Craig
Newmark Foundation).

**Statut : arrêté après quatre ans.** Quatre échecs documentés :
1. **Famine de matière** — pas assez de vérifications publiées pour alimenter
   l'appariement, surtout en local et régional.
2. **Transcription absurde** — « Armpit sweat through the last week is taking a
   terrible toll » pour « The powerful storm that swept through Iowa ».
3. **Appariement faux** — une affirmation sur les hommes ayant marché sur la
   Lune associée à une vérification sur les permis de conduire, les deux
   contenant le mot « years ».
4. **Ergonomie insoluble** — à quelle phrase rattacher le verdict, quand
   l'afficher, combien de temps le laisser.

> **Pour FacTool.** L'échec n°1 ne nous concerne pas : nous n'apparions pas
> avec des vérifications publiées, nous interrogeons des sources primaires.
> C'est la différence qui rend l'approche viable en 2026 et ne l'était pas en
> 2021. Les échecs 2 et 3 restent entiers. L'échec 4 est dissous par notre
> choix du fil qui défile plutôt que de l'incrustation synchrone.

Sources : [The lessons of Squash](https://reporterslab.org/the-lessons-of-squash-our-groundbreaking-automated-fact-checking-platform/) · [Tech & Check](https://reporterslab.org/tech-and-check/) · [Poynter](https://www.poynter.org/fact-checking/2020/how-the-duke-reporters-lab-used-the-political-conventions-to-perfect-its-automated-fact-checking-program/)

---

## A2. ClaimBuster — University of Texas at Arlington

**Ce qu'il fait.** Le composant amont de tout le domaine : repérer *quelles*
phrases méritent une vérification.

**Comment ça marche.** Apprentissage supervisé. Chaque phrase d'une
transcription reçoit un **score de 0 à 1** indiquant sa probabilité d'être une
affirmation factuelle digne de vérification. Classe en trois catégories :
opinions, faits sans enjeu, affirmations vérifiables importantes.

**Diffusion.** Site, API, compte X, Slackbot. Premier système annoncé comme
« end-to-end ».

> **Pour FacTool.** C'est exactement notre étage 1 (pertinence). Leur découpage
> en trois catégories préfigure le nôtre. Différence : ils scorent en continu,
> nous classons en catégories discrètes — plus simple à auditer, et suffisant
> puisque le score ne sert qu'à décider d'un appel modèle.

Sources : [ClaimBuster VLDB](https://www.vldb.org/pvldb/vol10/p1945-li.pdf) · [KDD'17](https://ranger.uta.edu/~cli/pubs/2017/claimbuster-kdd17-hassan.pdf)

---

## A3. Full Fact AI — Royaume-Uni

**Ce qu'il fait.** Le leader du secteur. Surveille presse, TV, radio, réseaux
sociaux et Hansard (comptes rendus parlementaires). ~300 000 phrases/jour.

**Comment ça marche.**
- **Détection** — BERT affiné (2019) sur des dizaines de milliers
  d'annotations humaines, pour étiqueter le type d'affirmation et son auteur.
- **Appariement** — les affirmations et les phrases médiatiques sont converties
  en **vecteurs** par un LLM, puis comparées par similarité. Enrichi d'un
  composant de **reconnaissance d'entités** et d'un composant
  **morpho-syntaxique**, pour éviter de confondre deux personnes ou deux lieux.
- **Pile** — Elasticsearch (recherche texte), SQL (données structurées),
  liaison **WikiData** (identification d'entités).
- **Produits** — *Trends* (qui répète des affirmations inexactes) et *Live*
  (signalement pendant les débats parlementaires et à la TV).

**Modèle.** Association caritative : dons, philanthropie, paiements de
plateformes, et **licence logicielle à plus de 45 organisations dans 30 pays**.

> **Pour FacTool.** C'est le concurrent frontal, avec dix ans d'avance. Point
> notable : leur enrichissement par entités nommées corrige précisément le mode
> d'échec n°3 de Squash. À reprendre. Leur architecture reste centrée sur
> l'appariement à des vérifications existantes — nous restons différenciés par
> l'interrogation directe des sources primaires.

Sources : [How AI can help fact checkers](https://fullfact.org/blog/2025/feb/how-ai-can-help-fact-checkers/) · [Full Fact AI](https://fullfact.ai/product/) · [Poynter](https://www.poynter.org/fact-checking/2025/the-uks-fact-checkers-are-sending-their-ai-to-help-americans-cover-elections/)

---

## A4. Factiverse — Norvège

**Ce qu'il fait.** Le plus proche de notre objet, et **commercial**.
*Factiverse Live* : transcription horodatée avec identification des locuteurs,
détection d'affirmations, recherche de preuves temps réel, verdict instantané
avec taux de corroboration.

**Comment ça marche.** Pipeline modulaire en trois étages :
1. **Détection d'affirmation** (claim detection)
2. **Récupération et reclassement des preuves** (retrieval + re-ranking)
3. **Prédiction de véracité** (stance detection)

Recherche sur Google, Bing, Wikipedia, Semantic Scholar et leur base propre
**FactiSearch** (> 350 000 vérifications). Modèles **XLM-RoBERTa-Large**
affinés, qui surpassent les grands LLM propriétaires sur les langues peu
dotées et morphologiquement riches. **110 langues** en transcription.

**Antécédents.** Premier live fact-check mondial d'un débat présidentiel
américain (27 juin 2024) ; 301 affirmations détectées sur Harris–Trump ; 259
sur le débat des VP ; 128 sur un débat de chefs de partis norvégiens.

**Modèle.** B2B, médias et administrations, tarification sur devis.

> **Pour FacTool.** Ils font déjà notre POC 1 et 2, en production, en français
> (110 langues). Notre seule différenciation défendable est le **corpus fermé
> de sources primaires françaises** : ils cherchent sur Google et Wikipedia —
> exactement ce que notre interdit fort exclut. Leur recours à des modèles
> affinés compacts plutôt qu'à un grand LLM est un choix de coût et de latence
> à considérer sérieusement pour l'étage 1.

Sources : [Factiverse Live](https://www.factiverse.ai/solutions/live) · [API](https://www.factiverse.ai/solutions/api) · [Multilingual Fact-Checking at Scale](https://arxiv.org/html/2606.08605) · [NORDIS](https://www.nordishub.eu/factiverses-ai-system-identified-128-factual-claims-during-party-leaders-debate/)

---

## A5. RMC BFM — France

**Ce qu'il fait.** Outil interne de fact-checking IA en direct, pour vérifier
les déclarations des invités à l'antenne, données croisées à chaque
intervention.

**Statut.** En test. Inscrit explicitement dans la feuille de route de CMA
Media pour les **municipales de mars 2026 puis la présidentielle de 2027**.

> **Pour FacTool.** Concurrent direct sur notre calendrier exact, avec
> l'audience et la caution éditoriale que nous n'avons pas.

Sources : [La Revue du Digital](https://www.larevuedudigital.com/un-outil-de-fact-checking-des-responsables-politiques-par-lia-en-test-chez-rmc-bfm/) · [The Media Leader](https://fr.themedialeader.com/cma-media-accelere-rmc-en-septembre-studio-createurs-nouvelle-regie-avec-brut-et-fact-checking-ia-pour-la-presidentielle/)

---

## A6. InTruth / Truth Check — extensions navigateur

**InTruth.** Extension Chrome. Écoute l'audio d'un direct, sépare les locuteurs
via **Deepgram**, isole les affirmations vérifiables, les évalue contre le web
en direct **avec Claude**, rend un verdict sourcé. Affichage par « color-coded
trust vectors ».

**Truth Check.** Extension Chrome, analyse une vidéo YouTube en une passe.

> **Pour FacTool.** Architecture quasi identique à la nôtre, y compris le
> modèle. Ce qui les distingue de nous n'est ni la technique ni le design :
> c'est l'absence de corpus contraint et de méthodologie publiée. C'est
> précisément là que se joue la crédibilité — et c'est reproductible en
> quelques semaines par n'importe qui. **Notre avantage n'est pas technique.**

Sources : [InTruth](https://intruth-beta.vercel.app/) · [Truth Check](https://chromewebstore.google.com/detail/truth-check-ai-fact-check/nchffbipfhlcfjmdjmaennchonbdnmbh)

---

# B. Outils open source et recherche

## B1. Loki — Libr-AI / OpenFactVerification

**Comment ça marche.** Pipeline complet et documenté : découpage d'un texte
long en affirmations individuelles → évaluation de leur « check-worthiness » →
génération de requêtes → collecte de preuves → verdict.

Optimisé sur cinq axes déclarés : exactitude, **latence**, robustesse, coût,
support multilingue.

> **Pour FacTool.** L'architecture la plus proche de la nôtre en open source,
> et elle valide notre entonnoir à cinq étapes. À lire avant d'aller plus loin.

Sources : [GitHub](https://github.com/Libr-AI/OpenFactVerification) · [Papier COLING 2025](https://aclanthology.org/2025.coling-demos.4.pdf)

## B2. OpenFactCheck

Cadre unifié d'évaluation de la factualité des LLM. **Intègre** Factcheck-GPT,
FacTool et FactScore dans un système unique. Bibliothèque Python.

> **Pour FacTool.** Utile comme harnais d'évaluation plutôt que comme moteur.

Sources : [GitHub](https://github.com/mbzuai-nlp/OpenFactCheck) · [arXiv](https://arxiv.org/html/2408.11832v1)

## B3. FacTool (GAIR-NLP) — l'homonyme

Cadre en **5 étapes** : extraction d'affirmations → génération de requêtes →
interrogation d'outils → collecte de preuves → vérification. Outils mobilisés :
Google Search, Google Scholar, interpréteur de code, Python, et les LLM
eux-mêmes. Couvre QA, génération de code, raisonnement mathématique et revue de
littérature scientifique. **Récupérateur de preuves à faible latence par
traitement asynchrone.**

Sources : [GitHub](https://github.com/GAIR-NLP/factool) · [arXiv 2307.13528](https://arxiv.org/pdf/2307.13528)

## B4. AVeriTeC — le banc d'essai de référence

**Ce que c'est.** Tâche partagée : récupérer des preuves et prédire la véracité
d'affirmations **réelles**, déjà vérifiées par des fact-checkers.

**Verdicts possibles :** `supported` · `refuted` · `not enough evidence` ·
`conflicting evidence/cherry-picking`.

**Évaluation.** Le *score AVeriTeC* ne compte une affirmation comme vérifiée
que si **le verdict est correct ET les preuves récupérées atteignent un seuil
de qualité**. Vérifier juste avec de mauvaises preuves ne compte pas.

**Résultats.** 2024 : 21 soumissions, gagnant TUDA_MAI à **63 %**.
2025 : contrainte de modèles à poids ouverts sur un seul GPU 23 Go et **une
minute maximum par verdict** ; gagnant CTU AIC à **33,17 %**.

> **Pour FacTool — la fiche la plus importante de cette étude.**
> Deux enseignements sévères. D'abord, **l'état de l'art plafonne autour de
> 63 %**, et à 33 % sous contrainte de latence. Un système qui prétendrait
> mieux faire en direct devrait le prouver. Ensuite, leur métrique est la
> bonne : *le verdict ne compte que si la preuve tient*. C'est exactement notre
> règle de vérification littérale des citations, formalisée par la recherche.
> Leur catégorie `conflicting evidence/cherry-picking` correspond à notre
> `sources_divergentes`. Et leur `not enough evidence` valide notre
> `non_verifie` comme sortie de premier rang, pas comme échec.
>
> **À faire : évaluer FacTool sur AVeriTeC avant tout débat réel.** C'est moins
> cher qu'un POC et comparable à l'état de l'art.

Sources : [AVeriTeC 2024](https://aclanthology.org/2024.fever-1.1.pdf) · [AVeriTeC 2025](https://aclanthology.org/2025.fever-1.15/) · [Ev2R](https://arxiv.org/pdf/2411.05375)

---

# C. Infrastructure et normes

## C1. ClaimReview / Google Fact Check Tools API

**Ce que c'est.** `ClaimReview` est un type schema.org : le balisage structuré
d'une vérification publiée — quelle affirmation, par qui, quel verdict.

**Comment ça marche.** Les rédactions balisent leurs articles ; Google les
indexe et les expose via **Fact Check Explorer** et une **API lecture/écriture**
(autorisation via Search Console). C'est le format qui alimentait Squash.

> **Pour FacTool.** Norme de sortie à produire si l'on veut être interopérable —
> mais pas source d'entrée : nos verdicts viennent des sources primaires, pas de
> vérifications tierces.

Sources : [Fact Check Tools API](https://developers.google.com/fact-check/tools/api) · [ClaimReview markup](https://developers.google.com/search/docs/appearance/structured-data/factcheck)

## C2. EFCSN / EDMO / DE FACTO

Réseau européen de standards (EFCSN), observatoire (EDMO), hub français
(DE FACTO). L'EFCSN a reçu **5 M€** (projet FACTEUR) et redistribue des
subventions jusqu'à **70 k€ par projet**. La Commission finance ces réseaux
existants via le *European Democracy Shield*.

Sources : [EFCSN FACTEUR](https://efcsn.com/funding-opportunities/efcsn-eu-grant-facteur/) · [EDMO](https://digital-strategy.ec.europa.eu/en/policies/european-digital-media-observatory)

---

# D. Évaluation de la source (et non de l'énoncé)

## D1. NewsGuard

**Comment ça marche.** Des journalistes notent les sites sur **neuf critères
journalistiques**, tous **binaires** (le site obtient tous les points du critère
ou aucun) : ne pas répéter de fausses informations, informer de façon
responsable, éviter les titres trompeurs, disposer d'une politique de
correction, séparer information et opinion, etc. Score /100. Les éditeurs sont
**contactés avant publication** et peuvent répondre.

**Modèle.** Licence aux plateformes (Microsoft), aux navigateurs et surtout aux
**agences publicitaires** — la seule vraie réussite commerciale du secteur.

**Controverse.** Accusé de constituer une censure à but lucratif et de couper
les revenus publicitaires des sites qu'il déclasse.

> **Pour FacTool.** Deux leçons. La bonne : **des critères binaires publiés à
> l'avance et un droit de réponse avant publication** — exactement notre
> dispositif. La mauvaise : même avec cette rigueur, NewsGuard est massivement
> accusé de partialité. La méthodologie publiée est nécessaire, **elle n'est
> pas suffisante**.

Sources : [Rating process](https://www.newsguardtech.com/ratings/rating-process-criteria/) · [FAQ](https://www.newsguardtech.com/newsguard-faq/)

## D2. Décodex, Media Bias/Fact Check, The Factual

Notation de fiabilité par site. Décodex (Le Monde) couvre ~3 000 sites avec
critères déclarés. Même logique, même limite : on note l'émetteur, pas
l'énoncé.

---

# E. Vérification d'images et de vidéos

## E1. InVID-WeVerify — le couteau suisse

**Comment ça marche.** Extension Chrome/Firefox, financée par Horizon 2020,
maintenue par l'**AFP Medialab** (dépôt GitHub public).
- **Fragmentation en images-clés** de vidéos (Facebook, Instagram, YouTube, X,
  Dailymotion), puis recherche inversée sur Google, Baidu, Yandex
- **Loupe** : zoom, netteté, inversion au pixel
- **Forensique** : ELA (error level analysis) et détection copy-move, **en
  local dans le navigateur, sans téléversement**
- **Deepfake** (expérimental) : découpe en trames, détection des visages,
  ensemble de cinq détecteurs CNN

Sources : [GitHub AFP-Medialab](https://github.com/AFP-Medialab/invid-verification-plugin/) · [InVID](https://www.invid-project.eu/tools-and-services/invid-verification-plugin/)

## E2. Détection de deepfakes — Sensity, Reality Defender, Hive, Deepware

| Outil | Approche | Exactitude annoncée |
|---|---|---|
| Sensity | forensique vidéo/image/audio + renseignement sur l'origine et les réseaux de repartage | 95–98 % |
| Reality Defender | multi-modèle probabiliste, sans filigrane ni authentification préalable | — |
| Hive | modération de contenu : API + files de relecture humaine, historique auditable | — |
| Deepware | scanner web et mobile | ~95 % |

> **Pour FacTool.** Hors périmètre — nous vérifions des énoncés, pas des
> images. À connaître si un débat porte sur une vidéo contestée.

Sources : [Sensity](https://sensity.ai/) · [comparatif Revelum](https://revelum.ai/insights/deepfake-detection-tools-compared/)

---

# F. Propagation et modération collective

## F1. Hoaxy + Botometer — Observatory on Social Media, Indiana University

**Hoaxy** suit la diffusion d'affirmations et des vérifications correspondantes,
et produit des **cartes de diffusion interactives**. **Botometer** score la
probabilité d'automatisation d'un compte. Code ouvert, API publique.
*Botometer X est en mode archive* : scores précalculés sur données antérieures
à juin 2023 — conséquence directe de la fermeture de l'API Twitter.

> **Pour FacTool.** Illustration du risque de dépendance à une plateforme
> tierce : un outil de recherche financé et solide, rendu inerte par une
> décision commerciale externe.

Sources : [hoaxy-backend](https://github.com/osome-iu/hoaxy-backend) · [botometer-python](https://github.com/osome-iu/botometer-python)

## F2. Community Notes (X)

**Comment ça marche — le point intéressant.** Algorithme de classement dit
**« bridging-based »**. Il ajuste un **modèle à facteurs latents** (factorisation
matricielle) sur les votes observés : chaque contributeur reçoit une position
sur un axe d'opinion déduit de son historique, chaque note reçoit un facteur de
« pente » sur cet axe. **Une note n'est publiée que si elle est jugée utile par
des contributeurs aux points de vue opposés.**

**Entièrement open source** : code et données publics, reproduisant la
production.

> **Pour FacTool.** L'idée profonde mérite attention : plutôt que de prétendre
> à la neutralité, **mesurer l'accord trans-partisan et n'afficher que ce qui le
> franchit**. C'est une réponse structurelle au reproche fait à tous les
> fact-checkers, y compris NewsGuard. Inapplicable telle quelle chez nous — nous
> n'avons pas de foule — mais elle suggère une piste d'évaluation : *nos
> verdicts seraient-ils acceptés par des lecteurs de bords opposés ?* C'est une
> métrique testable, et personne dans le champ français ne la produit.

Sources : [Note ranking code](https://communitynotes.x.com/guide/en/under-the-hood/note-ranking-code) · [Birdwatch à Community Notes, 4 ans](https://arxiv.org/html/2510.09585v2)

---

# Synthèse — ce que l'étude change pour FacTool

1. **Le nom est pris.** Homonymie avec un projet académique actif et indexé.
2. **L'état de l'art plafonne à 63 %** (AVeriTeC), et à 33 % sous contrainte
   d'une minute par verdict. Toute prétention supérieure doit être prouvée.
3. **Évaluer sur AVeriTeC avant tout débat réel** — moins cher qu'un POC,
   comparable à l'état de l'art, et leur métrique (le verdict ne compte que si
   la preuve tient) est déjà la nôtre.
4. **Notre différenciation n'est pas technique.** InTruth fait la même chose
   avec le même modèle. Elle tient au corpus fermé de sources primaires
   françaises et à la méthodologie publiée — reproductibles, mais que personne
   n'a faits.
5. **La méthodologie publiée est nécessaire et insuffisante** — NewsGuard le
   démontre.
6. **À reprendre de Full Fact** : l'enrichissement par entités nommées, qui
   corrige le mode d'échec fatal de Squash.
7. **À reprendre de Factiverse** : des modèles compacts affinés pour l'étage 1
   plutôt qu'un grand LLM, pour le coût et la latence.
8. **Piste originale, de Community Notes** : mesurer l'acceptation
   trans-partisane de nos verdicts. Personne ne le fait en France.
