# Jeu étalon

Ce que le projet appelle depuis trois sessions « le manque le plus grave », et
qui n'existait pas : un ensemble d'énoncés dont le verdict attendu est écrit à
la main, contre les sources stockées, **avant** toute exécution de la chaîne.

Sans lui, aucun taux n'est interprétable et les seuils restent des opinions
publiées (`METHODE.md` §1 et §2).

---

## Ce qu'un item contient

```yaml
- id: dep-57-3
  origine: debat                    # debat | construit
  minutage: "24:55"
  enonce: "…"                       # verbatim, tel que la chaîne le voit
  domaine: finances-publiques
  source_attendue: insee-comptes-apu-2025
  grandeur: "dépenses des administrations publiques, % du PIB"
  valeur_enoncee: "57,3 %"
  valeur_source: "57,2 %"
  millesime_source: "2025"
  ecart: "0,1 point"
  verdict_attendu: exact
  robustesse: mecanique             # mecanique | depend_du_seuil
  atteignable_aujourdhui: oui
  motif: "…"
```

Deux champs font tout le travail, et ils sont là parce qu'un jeu étalon naïf
mesure surtout son auteur.

**`robustesse`** sépare ce qui ne se discute pas de ce qui dépend d'un réglage.
« 27 millions de demandeurs d'emploi » contre 2 710 400 est faux quel que soit
le seuil : c'est `mecanique`. « 45,3 % » contre 43,6 % est un écart de 1,7
point, et l'étiquette dépend entièrement de la barre qu'on pose : c'est
`depend_du_seuil`.

- Les items `mecanique` servent à **juger le système**.
- Les items `depend_du_seuil` servent à **choisir les seuils**.

Confondre les deux, c'est régler un seuil sur des cas puis se féliciter de bien
les classer.

**`atteignable_aujourdhui`** dit si la chaîne, dans son état, peut seulement
produire le verdict attendu. Un item marqué `non` est un échec connu et
documenté, pas un bug à découvrir : il reste dans le jeu parce qu'un jeu étalon
qui n'exprime que ce que le système sait déjà faire ne mesure rien.

## Le biais, déclaré

**Les étiquettes sont écrites par l'auteur du système.** C'est un défaut réel :
je peux, sans le vouloir, étiqueter dans le sens de ce que la chaîne produit.

Trois garde-fous, aucun suffisant :

1. Chaque item cite **la source stockée et la valeur qu'elle porte**. Le
   verdict attendu se re-dérive du couple de valeurs sans me croire.
2. Les étiquettes ont été posées **avant** toute exécution de la chaîne sur ces
   énoncés, et le fichier est versionné : un ajustement après coup se voit dans
   `git log`.
3. Les cas où mon étiquette est discutable portent `robustesse:
   depend_du_seuil` et ne comptent jamais comme réussite ou échec du système.

Le vrai correctif serait un étiquetage par quelqu'un d'autre, en aveugle. Il
n'a pas eu lieu.

## Ce que ce jeu ne permet pas encore

**Il est trop petit pour calibrer quoi que ce soit.** Le corpus couvre deux
domaines ; le débat n'offre que quelques énoncés que ces deux domaines peuvent
trancher. Un balayage de seuil sur cinq couples de valeurs n'est pas une
calibration, c'est une anecdote avec une courbe.

Le chiffre nécessaire n'est pas une opinion : pour distinguer deux seuils qui
diffèrent de quelques points de taux d'accord, il faut des dizaines d'items
par classe de verdict. Nous en avons une poignée. Le banc le dit et refuse de
conclure plutôt que de publier une courbe qui aurait l'air d'une mesure.

**Ce qui débloque, dans l'ordre** : élargir le corpus (chaque domaine ajouté
rend étiquetables les énoncés qu'il couvre), puis étiqueter un second débat.

## Les items construits

Quatre items ne viennent pas du débat mais sont écrits à la main, et marqués
`origine: construit`. Ils testent le piège de définition que la fiche `emploi`
signale — un taux BIT n'est pas un effectif de catégorie A — que le débat
LaREF ne déclenche jamais.

**Ils ne comptent pas dans une mesure de performance réelle** : un énoncé
fabriqué pour tomber dans un piège n'a pas la difficulté d'un énoncé réel. Ils
servent de témoins, au sens du §11 de `METHODE.md` : ils disent si le système
attrape un piège dont on sait qu'il est là.
