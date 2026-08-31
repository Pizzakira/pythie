# Audit des systèmes de transcription

Enjeu : **une transcription infidèle produit une citation fabriquée.** Si l'ASR
transforme « 2,7 millions » en « 27 millions », Pythie rend un rouge
parfaitement sourcé sur une phrase que personne n'a prononcée. C'est la même
classe de faute qu'une attribution au mauvais locuteur.

État au 31 août 2026.

---

## Le piège à éviter avant tout

**Deux variantes de Whisper ne comptent pas pour deux voix.**

`bofenghuang/whisper-large-v3-french` est un *fine-tune* de Whisper. Il partage
son architecture, ses données d'origine et donc ses modes de défaillance. Le
faire concorder avec Whisper large-v3 ne prouve rien : les deux se trompent aux
mêmes endroits.

Pour que l'accord entre sources ait une valeur probante, il faut des
**architectures distinctes** :

| Famille | Architecture |
|---|---|
| Google (sous-titres YouTube) | pile propriétaire, inconnue |
| Whisper et dérivés | encodeur-décodeur seq2seq |
| Kyutai | codec Mimi + décodeur autorégressif, *delayed streams modeling* |
| Voxtral (Mistral) | pile Mistral, distincte |

Une source par famille. Pas deux Whisper.

---

## Fiches

### Kyutai STT — `stt-1b-en_fr`

**Le seul utilisable en direct, et il est français.**

- ~1 Md de paramètres, **anglais et français**
- **Délai de 0,5 seconde** — conçu pour le streaming, pas adapté après coup
- **Horodatage au mot** natif
- **VAD sémantique intégré**
- Architecture *delayed streams modeling*, héritée de Moshi ; encodage audio en
  jetons discrets par le codec Mimi
- Batching : une H100 traite 400 flux en temps réel

> **Pour Pythie.** C'est la brique du degré 1. Deux bénéfices secondaires
> notables : le VAD intégré nous dispense de Silero — un modèle de moins à
> charger pour la diarisation — et l'horodatage au mot sert directement à la
> réécoute ciblée des chiffres.

[kyutai.org/stt](https://kyutai.org/stt/) · [stt-1b-en_fr](https://huggingface.co/kyutai/stt-1b-en_fr) · [delayed-streams-modeling](https://github.com/kyutai-labs/delayed-streams-modeling/)

---

### Voxtral (Mistral AI) — `Voxtral Transcribe 2`

**La meilleure exactitude brute.**

- Sorti **février 2026**, Apache-2.0
- **5,9 % de WER moyen sur FLEURS, contre 7,4 % pour Whisper**
- Streaming temps réel natif
- ~13 langues seulement — le français en fait partie

> **Pour Pythie.** Un point et demi de WER sur Whisper, ce n'est pas marginal
> quand chaque chiffre mal transcrit devient une citation fabriquée. Couverture
> linguistique étroite : sans importance ici, on ne fait que du français.
> Candidat sérieux comme source de référence, et architecturalement
> indépendant de Whisper.

---

### WhisperX

**Ce n'est pas un modèle, c'est un assemblage** — et c'est son intérêt.

Appelle `faster-whisper` pour la transcription, puis ajoute trois étages :
1. un VAD qui localise la parole réelle
2. un **alignement forcé wav2vec2** — horodatage au mot à **±50 ms, contre
   ±500 ms** pour Whisper seul
3. la diarisation par pyannote

> **Pour Pythie, l'alignement à ±50 ms n'est pas un confort, c'est ce qui rend
> la réécoute ciblée possible.** Extraire les trois secondes autour d'un chiffre
> avec une incertitude de ±500 ms, c'est découper à côté. À ±50 ms, c'est
> chirurgical.
>
> Et sa diarisation pyannote est précisément la couche de segmentation et
> détection de chevauchement que `consensus.py` attend.

[m-bain/whisperX](https://github.com/m-bain/whisperx)

---

### Whisper large-v3 et le fine-tune français

- **Whisper large-v3** : 99+ langues, trois ans d'outillage, tourne sur
  whisper.cpp. WER 7,4 % sur FLEURS. **Hallucine sur le silence et la musique** —
  notre pire mode de défaillance, parce qu'il invente du texte fluide et
  plausible.
- **`bofenghuang/whisper-large-v3-french`** : fine-tune français. Plus de
  2 500 heures de données problématiques filtrées, ce qui a **nettement réduit
  les hallucinations**. Gains de 1,6 % de WER en court et 2,4 % en long hors
  domaine. Variantes distillées `dec2/4/8/16`, qui réduisent encore le risque
  d'hallucination en forme longue.

> **Pour Pythie.** Le distil français est le meilleur Whisper pour nous, à cause
> du filtrage anti-hallucination. Mais il ne compte que pour **une** voix de la
> famille Whisper.

---

## Recommandation : trois sources, trois architectures

| Rôle | Système | Pourquoi |
|---|---|---|
| **Direct (degré 1)** | Kyutai `stt-1b-en_fr` | 0,5 s, français natif, horodatage au mot, VAD inclus |
| **Référence (degré 2)** | WhisperX + `whisper-large-v3-french-distil` | alignement ±50 ms, anti-hallucination, diarisation pyannote |
| **Contrôle indépendant** | Sous-titres YouTube | gratuit, immédiat, pile totalement étrangère aux deux autres |

**Voxtral Transcribe 2** en remplacement de la référence si les essais lui
donnent raison sur les chiffres — c'est le seul point qui compte pour nous.

## Ce que l'accord doit porter

Pas la prose. **Seuls le chiffre et son unité doivent concorder.**

« Il y a » contre « on compte » : sans importance, Pythie ne juge pas la
formulation. « 2,7 » contre « 27 » : bloquant, aucun verdict n'est rendu sur
cet empan.

C'est une cible bien plus atteignable que l'accord phrase à phrase, et c'est
exactement ce qui détermine la justesse du verdict.

## Garde-fous obligatoires côté Whisper

- ne transcrire que là où le VAD détecte de la parole
- rejeter les segments à `no_speech_prob` élevé ou `avg_logprob` bas
- rejeter les segments à ratio de compression anormal — signature des boucles
  de répétition

## Sources

- [Kyutai STT](https://kyutai.org/stt/) · [stt-1b-en_fr](https://huggingface.co/kyutai/stt-1b-en_fr)
- [Voxtral vs Whisper 2026 — WER, streaming, matériel](https://weesperneonflow.ai/en/blog/2026-03-31-voxtral-whisper-open-source-speech-models-comparison-2026/)
- [Best open source STT model in 2026 — Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- [Best Open ASR Models in 2026 — MarkTechPost](https://www.marktechpost.com/2026/07/23/best-open-speech-recognition-asr-models-in-2026-wer-languages-latency-and-license-compared/)
- [ASR Leaderboard — arXiv 2510.06961](https://arxiv.org/html/2510.06961v4)
- [WhisperX](https://github.com/m-bain/whisperx) · [Choosing between Whisper variants — Modal](https://modal.com/blog/choosing-whisper-variants)
- [whisper-large-v3-french](https://huggingface.co/bofenghuang/whisper-large-v3-french) · [distil-dec16](https://huggingface.co/bofenghuang/whisper-large-v3-french-distil-dec16)

---

# Banc noms propres — résultat mesuré (31 août 2026)

Protocole et limites : `ETUDES/banc_noms.py`. Fenêtres de 8 s sur l'audio réel
de LaREF 2026, trois sources comparées sur **la même matière**.

## Le résultat qui tranche

À **58:45**, sur exactement les mêmes 8 secondes :

| Source | Transcription |
|---|---|
| Sous-titres YouTube | « Bruno **Rota** » |
| faster-whisper-large-v3 | « **Bruno Retailleau**, je peux vous dire que les compteurs… » |

Nom complet et correct contre nom détruit. C'est la justification empirique de
ne pas dépendre des sous-titres pour l'identification des locuteurs.

## Le cas « Talenaissance » — la nature de l'erreur compte

Phrase réelle : « en présence de monsieur Attal, la renaissance de la France »
(jeu de mots sur le parti).

| Source | Transcription | Récupérable ? |
|---|---|---|
| YouTube | `Talenaissance` | **non** — frontière détruite |
| faster-whisper | « monsieur **Aptal**, la renaissance » | oui, appariement flou |
| CrisperWhisper | « Monsieur **Abtal**, la renaissance » | oui |

Les trois échouent sur le patronyme. Mais les deux Whisper **préservent la
frontière** entre le nom et le mot suivant ; YouTube la fusionne en un mot
inexistant, et plus aucun appariement ne peut rattraper cela.

**Conséquence de conception** : ce n'est pas le taux d'erreur sur les noms qui
compte, c'est le *type* d'erreur. Une déformation reste exploitable, une fusion
est définitive.

## Écart hors noms propres

À 150:18, même phrase : CrisperWhisper écrit « dès le début du **quinquennat** »,
faster-whisper « dès le début du **café** ». Le premier a raison.

## Ce que ce banc ne vaut pas

- **Deux fenêtres sur huit** (18:13, 19:24) reposaient sur des horodatages mal
  extraits et ne contiennent pas le nom attendu. Les totaux agrégés
  (70 % / 60 % / 40 %) portent donc sur un échantillon partiellement invalide et
  **ne sont pas retenus comme mesure**. Seules valent les comparaisons
  fenêtre par fenêtre sur audio identique.
- Le biais joue **contre** les Whisper : la colonne YouTube est notée sur un
  texte qui contient le nom par construction, puisqu'il a servi à choisir la
  fenêtre.
- Huit fenêtres, dix patronymes : trop peu pour conclure au-delà des cas cités.

## Décision

Les sous-titres YouTube restent une **troisième source de contrôle**, jamais la
source d'identification. Les introductions qu'ils contiennent orientent
l'étiquetage des grappes de diarisation ; elles ne le fondent pas.

---

# Correction des noms dans le texte — écartée (31 août 2026)

**Hypothèse testée** : à partir du roster fermé, un modèle peut retrouver et
corriger les patronymes déformés par l'ASR.

**Protocole** : 11 cas — 6 déformations réelles relevées sur LaREF 2026, et
**5 pièges** : des mots français courants proches d'un patronyme, qu'aucune
correction ne doit toucher.

| Méthode | Positifs (6) | Pièges (5) | Total |
|---|---|---|---|
| Appariement flou déterministe | 2 | 2 | **4/11** |
| Qwen3.8-27B | 0 | **5** | **5/11** |

## Ce que ça montre

**L'appariement flou est dangereux.** Il transforme « le **total** des
dépenses » en Attal, « le taux **natal** » en Attal, « **détailler** le
budget » en Retailleau. Il fabriquerait des noms dans du texte ordinaire.

**Qwen est sûr mais inopérant.** Il refuse correctement les cinq pièges, et
rate cinq positifs sur six — la plupart en sortie non conforme au schéma.

L'asymétrie est ce qui compte : les échecs de Qwen sont des **abstentions**,
ceux de l'appariement flou sont des **fabrications**.

## Décision

**On ne corrige pas les noms dans la transcription.**

Ce n'est pas nécessaire. Le besoin réel est d'**étiqueter les grappes de
diarisation**, et pour cela un signal faible suffit : on agrège des dizaines de
mentions par grappe sur un débat de trois heures, donc une déformation isolée
ne pèse rien. Réécrire le texte, en revanche, exige une fiabilité qu'aucune des
deux méthodes n'atteint — et une correction erronée fabrique une citation.

Le signal des noms alimente l'étiquetage des locuteurs. Jamais le texte.

---

# Banc noms propres — version corrigée, quatre sources (1er septembre 2026)

Fenêtres reprises des horodatages ligne à ligne : les trois valeurs
approximatives de la première version invalidaient un quart de l'échantillon.
9 fenêtres, 11 patronymes, même audio pour toutes les sources.

| Source | EXACT | RÉCUP | PERDU | Utilisable |
|---|---|---|---|---|
| faster-whisper-large-v3 | 8 | 2 | 1 | **91 %** * |
| whisper-large-v3-french | 8 | 2 | 1 | **91 %** * |
| CrisperWhisper 2.0 | 5 | 2 | 4 | 64 % |
| Sous-titres YouTube | 3 | 1 | 7 | **36 %** |

\* même famille Whisper.

## Trois enseignements

**1. Les sous-titres ne suffisent pas.** 36 % contre 91 %. La décision de ne
jamais fonder l'identification des locuteurs sur eux est confirmée par la
mesure et non plus par un exemple.

**2. Le fine-tune français n'apporte rien sur les noms propres.** Score
identique au large-v3 de base. Il conserve son intérêt documenté sur
l'hallucination en forme longue — qui n'est pas ce que ce banc mesure.

**3. La correspondance des familles est démontrée, pas seulement postulée.**
À 150:18, sur la même phrase :

| Modèle | Transcription |
|---|---|
| faster-whisper-large-v3 | « dès le début du **café** » |
| whisper-large-v3-french | « dès le début du **café** » |
| CrisperWhisper | « dès le début du **quinquennat** » ✓ |

Les deux modèles Whisper commettent **la même erreur**, là où une architecture
différente réussit. C'est exactement pourquoi leur accord ne peut pas servir de
preuve : ils partagent leurs modes de défaillance.

Corollaire pour l'accord à trois sources : il faut **une source par famille**.
Whisper (l'une des deux, indifféremment), CrisperWhisper, et les sous-titres —
ou Kyutai à la place de ces derniers en direct.

## Détail d'exécution

`whisper-large-v3-french` tourne dans l'environnement `karak_crisper` et non
`karak` : les DLL `torchcodec` de ce dernier échouent au chargement, et
`transformers` passe par torchcodec dès l'import. Une première exécution a
rendu 0 % — c'était une panne, pas une mesure, et elle est consignée comme
telle.

---

# Face-à-face : whisper-large-v3-french contre faster-whisper-large-v3
## 1er septembre 2026 — extrait de 5 min (24:00 → 29:00)

Protocole : `ETUDES/banc_fr_vs_v3.py`. Même audio, français forcé sur les deux.

## Verdict : large-v3 gagne nettement

| | large-v3 | français |
|---|---|---|
| Segments | ~20 | **9** (blocs de 30 s) |
| Durée | **20,7 s** | 88,3 s |
| Vitesse | **14,5× le direct** | 3,4× |
| Chiffres repérés | 20 | 74 (gonflé, voir plus bas) |
| Boucle d'hallucination | **aucune** | **oui, ~45 répétitions** |

## L'hallucination, en clair

Le modèle français produit une boucle : la même proposition courte répétée une
quarantaine de fois d'affilée au milieu d'une phrase, avant de reprendre le fil
normalement. C'est le mode d'échec classique de Whisper en forme longue — et
précisément celui que ce fine-tune revendique d'avoir réduit par filtrage de
2 500 heures de données problématiques.

Sur cet extrait, il fait **pire** que le modèle de base, qui n'en produit
aucune.

## Deux défauts de formatage

- Il écrit **« 210 1000000000 »** au lieu de « 210 milliards » : l'échelle est
  développée en chiffres. Pour Pythie, dont tout l'objet est de comparer des
  valeurs, c'est disqualifiant en l'état.
- Il écrit « 1er », « 2ème » là où large-v3 écrit « premier », « deuxième ».

## Segmentation

large-v3 rend des segments d'une phrase, horodatés — exploitables directement.
Le modèle français, via la pile `transformers`, rend des blocs de 30 secondes
dont les horodatages ne permettent aucun alignement fin. Les 0 appariements de
chiffres du banc en découlent : ce n'est pas un désaccord, c'est une
impossibilité d'aligner.

## Réserve sur la portée de ce résultat

Le modèle français tourne ici via `transformers` avec `chunk_length_s=30`, pas
via une conversion CTranslate2 comme large-v3. Une partie de l'écart — vitesse,
segmentation, peut-être la boucle — tient à cette configuration et non au
modèle. **Le résultat vaut pour cette configuration, pas comme jugement absolu
du fine-tune.** Une conversion CT2 serait la comparaison équitable.

## Défaut de ma métrique, consigné

`repetition()` a rapporté **0 répétition pour les deux modèles**, alors que la
boucle est manifeste à la lecture. Elle comptait les *segments* identiques
consécutifs ; or la boucle vit **à l'intérieur** d'un unique bloc de 30
secondes. La métrique était aveugle au phénomène qu'elle devait mesurer.

Correctif nécessaire : compter les n-grammes répétés *dans* chaque segment,
pas seulement d'un segment à l'autre.

## Décision

**Le modèle de référence reste `faster-whisper-large-v3`** : plus rapide,
mieux segmenté, sans boucle, et sans défaut de formatage des nombres.

Le fine-tune français n'entre pas dans la chaîne en l'état. Il reste candidat à
une reprise en CTranslate2, où la comparaison serait honnête.
