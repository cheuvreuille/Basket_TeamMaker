# Historique des versions

## 1.6 — 19 novembre 2026

- Jauge « Jeu en équipe » : −1 Trop perso, 0 Équilibré, 1 Trop altruiste, avec sauvegarde dans les fiches et les exports.
- Import et migration du stockage local rétrocompatibles : « Équilibré » par défaut si l’information est absente ou invalide.
- Nouveau moteur 3.0, basé sur les priorités du moteur 2 et intégrant l’équilibre des tendances et la répartition des profils extrêmes dans son premier critère.
- Moteurs 1.0 et 2.0 conservés sans modification de leur code ni prise en compte du jeu en équipe.

## 1.5.2 — 19 novembre 2026

- Couleurs par équipe : noir, blanc, bleu, jaune, violet et vert ; noir et blanc pour les deux premières équipes.
- Choix d’une couleur de la palette ou d’une couleur personnalisée dans chaque carte d’équipe.
- Couleurs conservées lors des transferts et des nouvelles générations pendant la session ; contraste du numéro adapté automatiquement.

## 1.5.1 — 11 novembre 2026

- Synthèse sous les noms : niveau global en toutes lettres, taille en cm, genre et intitulé du poste principal. Les légendes restent dans l’effectif ; les équipes utilisent le format compact « Confirmé · 175 cm · Homme · Meneur ».

- Joueurs classés par poste principal croissant (1 à 5) dans les équipes et dans la composition copiée ; postes non renseignés en dernier.
- Ordre actualisé après chaque transfert, pour les générations locales et IA.
- Menu de transfert compact avec libellés courts.

## 1.5 — 11 novembre 2026

- Poste principal unique et postes secondaires multiples, affichés séparément dans les fiches et les équipes.
- Migration des anciens imports et du stockage local : premier poste valide comme principal, autres postes comme secondaires ; anciens joueurs sans poste conservés.
- Moteur v1.0 adapté pour ignorer les postes secondaires.
- Nouveau moteur v2.0 : priorité stricte à la taille et aux six compétences, puis au niveau global et au poste principal, puis aux postes secondaires.
- Export conservant le format JSON version 1 et le champ historique `positions`, en plus des nouveaux champs.

## 1.4 — 11 novembre 2026

- Sélecteur de version du moteur dans « Créer les équipes ».
- Algorithme existant conservé sous le nom « Moteur v1.0 » et isolé pour permettre l’ajout de versions indépendantes.
- Version du moteur affichée dans le résultat et conservée après les ajustements manuels.

## 1.3 — 7 novembre 2026

- Déplacement manuel des joueurs entre équipes par glisser-déposer ou menu de destination, utilisable au clavier et sur mobile.
- Mise à jour immédiate des effectifs, des moyennes et de la composition copiée.
- Équipes vides prises en charge et compositions retouchées signalées dans le résultat.

## 1.2 — 30 octobre 2026

Version de référence de l’application au début du suivi des versions.

- Gestion des joueurs, du genre et des présences.
- Tri de l’effectif par taille, niveau général ou genre.
- Postes 1 à 5 en sélection multiple, pris en compte dans l’équilibrage local et les consignes IA.
- Import/export JSON rétrocompatible.
- Affichage de la version dans l’en-tête du site.
