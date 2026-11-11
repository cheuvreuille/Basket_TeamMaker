# Basket_TeamMaker

Application autonome : ouvrir `basket-equipes-autonome.html`, ou servir le dossier avec `python3 -m http.server 8000`. `index.html` redirige vers l’application pour GitHub Pages.

## Postes des joueurs

Chaque fiche comporte un poste principal unique : 1 (meneur), 2 (arrière), 3 (ailier), 4 (ailier fort), 5 (pivot). Les postes secondaires sont facultatifs, en sélection multiple, et ne peuvent pas répéter le poste principal. Un poste principal est demandé lors de l’ajout ou de l’enregistrement d’une fiche. Les joueurs historiques sans poste restent utilisables dans la génération sans modification obligatoire de l’effectif.

## Compatibilité JSON

Le format d’export reste `{ "version": 1, "players": [...] }`. Un joueur contient désormais `"primaryPosition": 3` et `"secondaryPositions": [2, 4]`. Le champ historique `"positions": [3, 2, 4]` est également exporté pour les anciennes applications, avec le principal en premier. Les autres champs sont conservés.

Les anciens tableaux de joueurs, objets version 1 et données du navigateur sont migrés à la lecture : le premier poste valide de `positions` devient le principal, les suivants deviennent secondaires. Sans poste, le principal reste `null` et les secondaires `[]`. Les nouveaux champs explicites priment sur `positions`. Les postes invalides et les doublons sont ignorés ; le principal est retiré des secondaires. Il n’est pas nécessaire de réexporter les anciens JSON avant de les importer.

## Versions du moteur

Le sélecteur « Version du moteur » choisit l’algorithme de la prochaine génération locale, y compris « Nouvelle répartition ». Le résultat indique le moteur utilisé, même après un déplacement manuel. Changer le sélecteur ne recalcule pas une composition existante et ne concerne pas les appels IA.

- **Moteur v1.0** : calcul historique et priorités historiques conservés, avec uniquement le poste principal utilisé pour l’équilibrage des postes. Les secondaires sont ignorés.
- **Moteur v2.0** : ordre fixe de comparaison des compositions : (1) taille et six compétences, (2) niveau global et répartition des postes principaux, (3) couverture complémentaire permise par les secondaires et répartition de ces derniers. Le sélecteur historique de priorité est désactivé pour ce moteur.

V2 compare ces trois scores dans l’ordre, sans somme pondérée entre priorités : un gain sur un critère de rang inférieur ne compense pas une dégradation d’un critère supérieur (tolérance numérique de 1e-9). Les critères utilisent les écarts entre moyennes d’équipe ; la taille est normalisée par 20 cm et chaque compétence par un point, avec un poids égal pour les six compétences. La couverture des postes attribue au plus un poste à chaque joueur. La recherche utilise plusieurs tirages et améliorations par échanges ; elle ne garantit pas l’optimum global. Tous les présents sont répartis une fois et les effectifs diffèrent au maximum d’un joueur avant ajustement manuel.

Les implémentations sont isolées dans `ENGINE_V1` et `ENGINE_V2` et enregistrées dans `ENGINES`. Pour les évolutions futures, ajouter une version indépendante plutôt que remplacer les moteurs disponibles. Le contrat est `{present, count, priority}` en entrée et `{teams, bench, source: 'local'}` en sortie ; l’interface ajoute `engineVersion`. L’adaptation de v1 aux seuls postes principaux en version 1.5 constitue la modification explicitement demandée lors de cette refonte.

## Ajustements manuels

Après une génération locale ou IA, glisser un joueur sur une autre équipe, ou sélectionner sa destination dans le menu « Déplacer vers ». Les joueurs sont affichés par poste principal (1 à 5, postes non renseignés en dernier), y compris dans la copie. La synthèse sous chaque nom présente le niveau global en toutes lettres, la taille en cm, le genre et le nom du poste principal. Le menu de transfert est compact. Les effectifs et statistiques sont actualisés, et « Copier » utilise la composition modifiée. Les déplacements sont libres, même si une équipe devient vide ou les effectifs inégaux. Une nouvelle génération remplace les ajustements. Les compositions ne sont pas conservées après rechargement de la page.

## Vérifications

Avec Playwright Python et Chromium installés :

```sh
python3 tests/check_positions.py
python3 tests/check_manual_teams.py
python3 tests/check_engine_versions.py
```

Les tests utilisent `/usr/bin/chromium`. Ils vérifient la migration des formats historiques, les postes principaux et secondaires, la persistance, l’export/réimport, les deux moteurs, l’ordre de priorité v2, les effectifs incomplets, les déplacements et l’affichage mobile. Les appels IA sont simulés ; aucune clé réelle n’est nécessaire. La comparaison avec le moteur historique utilise des joueurs ayant chacun un seul poste principal.

## Suivi des versions

La version de l’application est affichée en haut du site (`appVersion` dans `basket-equipes-autonome.html`). Pour chaque nouvelle version, mettre à jour ce libellé et ajouter une entrée dans [CHANGELOG.md](CHANGELOG.md). La version de l’application (1.5.1), les versions des moteurs (1.0 et 2.0) et la version du format JSON (1) sont indépendantes.
