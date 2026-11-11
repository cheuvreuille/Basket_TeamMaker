# Historique des versions

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
