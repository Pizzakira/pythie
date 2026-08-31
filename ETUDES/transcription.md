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
