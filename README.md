# Basket Team tracker

Application autonome : ouvrir `basket-equipes-autonome.html`, ou servir le dossier avec `python3 -m http.server 8000`. `index.html` redirige vers l’application pour GitHub Pages.

## Onglets de l’application

- **Effectif** permet d’ouvrir une fiche en cliquant sur le cadre du joueur, de modifier ses informations et de consulter son historique d’entraînement. La fiche affiche le total des participations, le nombre et le taux de présence pour chaque jour sélectionné dans **Configuration**, la dernière participation et jusqu’à cinq coéquipiers fréquents. Le total inclut tous les jours de la semaine.
- **Entraînement** regroupe la sélection des présents, les moteurs de génération et la composition des équipes.
- **Match** permet de préparer et d’enregistrer une équipe pour un match.
- **Statistique** donne accès aux présences, à la carte des relations et aux coéquipiers fréquents, avec un sélecteur **Entraînement / Match**.
- **Configuration** regroupe les réglages de l’IA et le choix des jours affichés dans les statistiques d’entraînement. Le bouton pour générer les équipes avec l’IA se trouve dans **Entraînement**.

## Postes des joueurs

Chaque fiche comporte un poste principal unique : 1 (meneur), 2 (arrière), 3 (ailier), 4 (ailier fort), 5 (pivot). Les postes secondaires sont facultatifs, en sélection multiple, et ne peuvent pas répéter le poste principal. Un poste principal est demandé lors de l’ajout ou de l’enregistrement d’une fiche. Les joueurs historiques sans poste restent utilisables dans la génération sans modification obligatoire de l’effectif.

## Compatibilité JSON

Le format d’export reste `{ "version": 1, "players": [...] }`. Un joueur contient désormais `"primaryPosition": 3` et `"secondaryPositions": [2, 4]`. Le champ historique `"positions": [3, 2, 4]` est également exporté pour les anciennes applications, avec le principal en premier. Les autres champs sont conservés.

Les anciens tableaux de joueurs, objets version 1 et données du navigateur sont migrés à la lecture : le premier poste valide de `positions` devient le principal, les suivants deviennent secondaires. Sans poste, le principal reste `null` et les secondaires `[]`. Les nouveaux champs explicites priment sur `positions`. Les postes invalides et les doublons sont ignorés ; le principal est retiré des secondaires. Il n’est pas nécessaire de réexporter les anciens JSON avant de les importer.

## Versions du moteur

Le moteur 3.0 est sélectionné par défaut à l’ouverture du site. Le sélecteur « Version du moteur » choisit l’algorithme de la prochaine génération locale, y compris « Nouvelle répartition ». Le résultat indique le moteur utilisé, même après un déplacement manuel. Changer le sélecteur ne recalcule pas une composition existante et ne concerne pas les appels IA.

- **Moteur v1.0** : calcul historique et priorités historiques conservés, avec uniquement le poste principal utilisé pour l’équilibrage des postes. Les secondaires sont ignorés.
- **Moteur v3.0** : reprend les trois priorités du moteur 2.0 et ajoute au premier score l’équilibre du jeu en équipe (moyenne des tendances et proportions de chaque profil extrême). Il favorise leur répartition entre équipes sans valoriser une extrémité par rapport à l’autre. Si tous les joueurs sont équilibrés, ses scores sont identiques à ceux du moteur 2.0.
- **Moteur v2.0** : ordre fixe de comparaison des compositions : (1) taille et six compétences, (2) niveau global et répartition des postes principaux, (3) couverture complémentaire permise par les secondaires et répartition de ces derniers. Le sélecteur historique de priorité est désactivé pour ce moteur.

V2 compare ces trois scores dans l’ordre, sans somme pondérée entre priorités : un gain sur un critère de rang inférieur ne compense pas une dégradation d’un critère supérieur (tolérance numérique de 1e-9). Les critères utilisent les écarts entre moyennes d’équipe ; la taille est normalisée par 20 cm et chaque compétence par un point, avec un poids égal pour les six compétences. La couverture des postes attribue au plus un poste à chaque joueur. La recherche utilise plusieurs tirages et améliorations par échanges ; elle ne garantit pas l’optimum global. Tous les présents sont répartis une fois et les effectifs diffèrent au maximum d’un joueur avant ajustement manuel.

Les implémentations sont isolées dans `ENGINE_V1`, `ENGINE_V2` et `ENGINE_V3` et enregistrées dans `ENGINES`. Pour les évolutions futures, ajouter une version indépendante plutôt que remplacer les moteurs disponibles. Le contrat est `{present, count, priority}` en entrée et `{teams, bench, source: 'local'}` en sortie ; l’interface ajoute `engineVersion`. L’adaptation de v1 aux seuls postes principaux en version 1.5 constitue la modification explicitement demandée lors de cette refonte.

## Ajustements manuels

Après une génération locale ou IA, faites glisser un joueur vers une autre équipe ou choisissez sa destination dans le menu à côté de son nom. Les joueurs sont affichés par poste principal (1 à 5, postes non renseignés en dernier), y compris dans la copie. La synthèse sous chaque nom présente le niveau global en toutes lettres, la taille en cm, le genre et le nom du poste principal. Les effectifs et statistiques s’actualisent après chaque déplacement. **Copier les équipes** utilise la composition affichée. Les déplacements sont libres, même si une équipe devient vide ou les effectifs inégaux. Une nouvelle génération remplace les ajustements. Cliquez sur **Enregistrer la composition** pour l’ajouter au suivi.

## Vérifications

Avec Playwright Python et Chromium installés :

```sh
python3 tests/check_teammates.py
python3 tests/check_history.py
python3 tests/check_teamwork.py
python3 tests/check_positions.py
python3 tests/check_manual_teams.py
python3 tests/check_engine_versions.py
```

Les tests utilisent `/usr/bin/chromium`. Ils vérifient la migration des formats historiques, les postes principaux et secondaires, la persistance, l’export/réimport, les deux moteurs, l’ordre de priorité v2, les effectifs incomplets, les déplacements et l’affichage mobile. Les appels IA sont simulés ; aucune clé réelle n’est nécessaire. La comparaison avec le moteur historique utilise des joueurs ayant chacun un seul poste principal.

## Suivi des versions

La version de l’application est affichée en haut du site (`appVersion` dans `basket-equipes-autonome.html`). Pour chaque nouvelle version, mettre à jour ce libellé et ajouter une entrée dans [CHANGELOG.md](CHANGELOG.md). La version de l’application (3.3.1), les versions des moteurs (1.0, 2.0 et 3.0) et la version du format JSON (1) sont indépendantes.

## Couleurs des équipes (1.5.2)

Chaque carte d’équipe propose la palette noir, blanc, bleu, jaune, violet et vert, ainsi qu’un sélecteur de couleur personnalisée. Les valeurs initiales suivent cet ordre : les deux premières équipes sont donc noires et blanches. Les couleurs restent attachées aux numéros d’équipe lors des transferts et des nouvelles répartitions dans la session. Elles sont réinitialisées au rechargement de la page.

## Jeu en équipe (1.6)

La fiche de chaque joueur comporte une jauge à trois niveaux (**−1 · Moins de passes**, **0 · Équilibré**, **1 · Trop de passes**). La valeur est conservée lors des modifications, des rechargements et des exports JSON dans le champ numérique `teamwork`. Les fichiers JSON et les données locales qui ne comportent pas ce champ reçoivent automatiquement la valeur `0`. Les valeurs invalides sont également ramenées à `0`. Le format JSON reste en version 1. Les exports restent lisibles par les anciennes versions de l’application, qui ignorent ce champ supplémentaire.

Seul le nouveau moteur local **3.0** tient compte de cette caractéristique. Les calculs des moteurs **1.0 et 2.0** sont inchangés et l’ignorent. Les consignes de l’option IA décrivent également ce nouveau champ.

## Statistique et suivi des séances

Dans **Entraînement**, cliquez sur **Enregistrer la composition** pour l’ajouter à la séance du jour après avoir généré et, si besoin, ajusté les équipes. Si une séance existe déjà, **Ajouter à la séance** conserve ses compositions et réunit les listes de présents. **Remplacer la séance** enregistre la composition et les présents actuels à la place des données du jour. Le bouton demande de régénérer les équipes si les présences actuelles diffèrent de la composition affichée.

Dans **Statistique**, sélectionnez une date, puis la composition à consulter ou modifier. Chaque joueur compte une fois dans les présences du jour. Pour les coéquipiers fréquents, une paire compte une fois dès qu’elle a joué dans la même équipe dans au moins une composition de la séance.

Dans **Statistique**, choisissez **Créer une séance manuellement**, renseignez la date et ajoutez les présents depuis l’effectif. Les équipes sont facultatives. Enregistrez la séance pour l’ajouter à l’historique et à l’export JSON. Si la date est déjà prise, ouvrez la séance existante pour la corriger.

L’onglet **Statistique** affiche :

- Une courbe colorée par jour de la semaine sélectionné, avec un point par séance et des repères pour les débuts de semaine et de mois.
- La moyenne des présents par jour de la semaine et le nombre de séances pris en compte.
- Un tableau de classement des joueurs, du plus au moins présent, avec le rang et le nombre total de participations. Les égalités sont départagées par nom. Les joueurs actuels sans présence sont affichés à zéro ; les anciens participants restent visibles même s’ils ont quitté l’effectif. Les noms courants sont utilisés pour les joueurs de l’effectif, et les derniers noms enregistrés pour les autres. L’identité est suivie par identifiant de joueur, pas par nom.
- Un éditeur de séance : sélection du jour, modification de la date, du nom historique des joueurs et de leur affectation ; ajout/retrait de participants depuis l’effectif ; ajout, renommage, changement de couleur ou suppression d’équipes ; suppression de la séance entière. Les modifications sont appliquées avec **Enregistrer les modifications**. Supprimer une équipe garde ses joueurs présents, sans affectation. Retirer un joueur ou supprimer une séance recalcule les graphiques.

Le classement ajoute un pourcentage pour chaque jour affiché. Par exemple, trois participations sur quatre séances du mercredi donnent 75 %. Sur mobile, la colonne des noms reste visible lorsque vous faites défiler le tableau horizontalement. Cliquez sur l’en-tête **Participations** ou sur un jour pour trier par cette colonne. Cliquez à nouveau pour inverser l’ordre. La moyenne et les pourcentages affichent un tiret pour les jours sans séance. Les sept jours sont affichés par défaut. La sélection dans **Configuration** s’applique au graphique, à sa légende, aux moyennes et aux colonnes de pourcentage. Elle est enregistrée dans le navigateur et restaurée à l’import d’une sauvegarde qui la contient.

Les corrections portent sur l’historique des séances. L’effectif, la sélection des présents et les compositions en cours se gèrent dans les onglets **Effectif** et **Entraînement**.

### Sauvegarde et compatibilité

L’export conserve le fichier `basket-joueurs.json`, le format des joueurs et la version JSON `1`. Il contient les séances, les matchs et les jours sélectionnés.

```json
{
  "version": 1,
  "players": [],
  "sessions": [],
  "matches": [],
  "statisticsWeekdays": [0, 2, 4]
}
```

Chaque séance comporte `id`, `date` (`YYYY-MM-DD`), `savedAt`, `players` (copies des participants) et `compositions`. Chaque composition contient ses propres équipes (`teams` avec `id`, `name`, `color` et `playerIds`), ses joueurs non affectés (`bench`) et ses informations de génération. Une date correspond à une séance. Un joueur peut être affecté une fois dans chacune de ses compositions. Un joueur retiré de l’effectif reste dans l’historique.

- Les anciens tableaux de joueurs et les objets JSON sans `sessions` remplacent toujours l’effectif et **conservent l’historique local existant**.
- Un objet avec `sessions` remplace l’effectif et l’historique après validation. `"sessions": []` vide explicitement l’historique.
- Un fichier sans `matches` conserve les matchs locaux. Un fichier avec `matches` remplace les matchs après validation. `"matches": []` vide l’historique des matchs.
- `statisticsWeekdays` contient les jours sélectionnés, de `0` pour lundi à `6` pour dimanche. Une liste vide masque tous les jours. Un fichier sans ce champ conserve le réglage actuel.
- Un historique de séances ou de matchs invalide, ou une sélection de jours invalide, bloque l’import entier.
- La version 3.1 relit les anciens fichiers et convertit les équipes de chaque séance en une composition. Pour restaurer un export contenant des compositions multiples, utilisez la version 3.1 ou une version ultérieure.

Les séances et les matchs sont conservés dans les clés locales `basket-sessions-v2` et `basket-matches-v1`. Exportez régulièrement le JSON pour sauvegarder les données du navigateur.

## Matchs

Dans **Match**, renseignez la date et l’équipe adverse, sélectionnez l’effectif, puis choisissez un titulaire pour chacun des cinq postes. Les autres joueurs sélectionnés apparaissent parmi les remplaçants. Cliquez sur **Enregistrer le match** pour l’ajouter à l’historique, puis sur **Nouveau match** pour en préparer un autre. Plusieurs matchs peuvent être enregistrés le même jour.

Dans **Statistique**, choisissez **Match** pour afficher les présences par date, la présence moyenne par match, le classement par nombre de matchs et les cartes de coéquipiers. Ces statistiques couvrent tous les matchs enregistrés. Chaque titulaire et chaque remplaçant compte une fois par match. Les liens entre coéquipiers reposent sur leur sélection pour le même match. **Gérer les matchs** permet de retrouver la composition, de la modifier dans **Match** ou de supprimer l’enregistrement.

Chaque match contient `id`, `date`, `opponent`, `players` (copies des profils), `starters` (identifiants dans l’ordre des postes 1 à 5) et `substitutes` (identifiants des remplaçants).

## Coéquipiers les plus fréquents

Dans **Statistique**, choisissez un **Joueur de référence**. Le réseau rapproche les coéquipiers qui ont partagé le plus de séances avec lui. Leurs liens sont plus épais et plus foncés, et leurs cercles sont plus grands. Le nombre dans chaque cercle indique les séances passées dans la même équipe. Les noms complets et les comptes sont disponibles au survol, au clavier et dans la liste détaillée.

Le calcul utilise uniquement les équipes des séances enregistrées, pas les compositions courantes non sauvegardées. Une paire est comptée une fois par séance ; adversaires, présents non affectés et joueur lui-même sont exclus. Le suivi repose sur les identifiants, conserve les joueurs archivés et se recalcule après correction, suppression ou import. Les noms suivent la même règle que le classement : nom courant si le joueur est encore dans l’effectif, sinon dernier nom enregistré.

La vue affiche les huit coéquipiers les plus fréquents par défaut. Le sélecteur permet d’en afficher seize ou tous. La liste détaillée donne toujours le classement complet. Le réseau peut défiler dans son cadre sur les petits écrans. À égalité, le tri est alphabétique.

## Carte des relations entre joueurs (3.2)

Dans **Statistique**, choisissez **Tous les jours** ou un jour de la semaine dans la carte. Chaque cercle affiche le nombre de séances auxquelles le joueur a participé. Plus deux joueurs ont figuré dans la même équipe d’une composition enregistrée, plus leur trait est épais et foncé. La disposition rapproche les duos fréquents en tenant compte de l’ensemble des liens et de la place nécessaire pour lire les noms. Deux compositions distinctes d’une même séance peuvent contribuer deux fois au lien, tandis que chaque présence compte une seule fois par séance.

Sélectionnez un cercle pour mettre en évidence ses liens et lire le nombre exact de compositions partagées. Les joueurs présents sans équipe apparaissent aussi. Le filtre est propre à la carte et les données viennent de l’historique des séances déjà inclus dans le JSON.
