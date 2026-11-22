# Historique des versions

## 3.0.2 — 22 novembre 2026

- Nouveaux libellés « Moins de passe » et « Trop de passe » pour le jeu en équipe.

## 3.0.1 — 22 novembre 2026

- Fiches accessibles en cliquant sur le cadre du joueur, avec ses présences par jour, sa dernière participation et ses cinq coéquipiers les plus fréquents.

## 3.0

- **Effectif** pour consulter, ajouter, modifier et supprimer les joueurs.
- **Entraînement** pour sélectionner les présents, générer les équipes et enregistrer la composition.
- **Match**, réservé à une future évolution.
- **Statistique** pour les présences, les coéquipiers fréquents et le suivi des séances.
- **Configuration** pour le fournisseur, le modèle et la clé de l’IA. La génération IA se lance depuis Entraînement.
- Création manuelle de séances dans **Statistique**, avec une date, des présents et des équipes facultatives.
- Moyennes de présence par jour de la semaine et pourcentages par joueur. Les jours affichés se choisissent dans **Configuration**.
- Tri croissant ou décroissant du classement par total de participations ou par taux de présence d’un jour de la semaine.
- Couleurs par jour de la semaine dans la courbe des présences, avec des repères fins pour les semaines et les mois.
- Courbes de présence séparées pour les jours sélectionnés, avec une légende filtrée et un choix des jours sauvegardé dans le JSON.
- Tri alphabétique par défaut dans **Effectif** et ordre alphabétique pour les présences dans **Entraînement** et l’ajout de joueurs à une séance.

## 2.1 — 19 novembre 2026

- Vue des coéquipiers les plus fréquents dans « Statistiques & suivi », avec joueur de référence sélectionné par liste déroulante.
- Réseau radial : référence au centre, coéquipiers reliés et cercles plus grands/foncés selon les séances communes dans la même équipe.
- Choix des 8 ou 16 coéquipiers les plus fréquents, ou de tous ; liste complète avec les comptes exacts.
- Adversaires, joueurs non affectés et simple présence simultanée exclus du calcul ; anciens joueurs conservés via l’historique.
- Recalcul après enregistrement, correction, suppression ou import de séances, sans changement du format JSON ni des moteurs.

## 2.0.1 — 19 novembre 2026

- Présences globales par jour affichées sous forme de courbe, avec un point par séance.
- Graphique des participations par joueur remplacé par un tableau : rang, joueur et nombre total de participations, par ordre décroissant (nom alphabétique en cas d’égalité).
- Joueurs de l’effectif sans participation affichés à zéro et anciens participants conservés dans le classement.
- Calcul des participations, enregistrement des séances et format JSON inchangés.

## 2.0 — 19 novembre 2026

- Onglets « Team Maker » et « Statistiques & suivi » ; services existants conservés dans le premier.
- Bouton « Save » pour enregistrer les présences, profils, compositions, couleurs et moteur utilisés le jour du clic.
- Une séance par jour local, avec confirmation avant remplacement pour éviter les doubles participations.
- Graphique des présences journalières et courbes des participations cumulées par joueur, avec filtre et tableaux de données accessibles.
- Sélection d’une date pour corriger les participants et leur affectation, renommer ou supprimer les équipes et supprimer une séance. L’effectif courant reste indépendant.
- Historique stocké localement et inclus dans le JSON existant sous `sessions`, sans changer le format des joueurs ni la version JSON 1.
- Anciens imports toujours acceptés ; l’absence de `sessions` conserve l’historique présent. Validation de l’historique avant toute modification de l’import.
- Moteurs et fonctions du Team Maker inchangés, hors import/export et ajout du bouton d’enregistrement.

## 1.6.1 — 19 novembre 2026

- Moteur 3.0 sélectionné par défaut à l’ouverture du site ; moteurs 1.0 et 2.0 toujours disponibles.

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
