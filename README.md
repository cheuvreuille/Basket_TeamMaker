# Basket_TeamMaker

Application autonome : ouvrir `basket-equipes-autonome.html`, ou servir le dossier avec `python3 -m http.server 8000`. `index.html` redirige vers l’application pour GitHub Pages.

Les postes possibles se cochent dans la fiche du joueur : 1 (meneur), 2 (arrière), 3 (ailier), 4 (ailier fort), 5 (pivot). Plusieurs choix sont possibles ; ne rien cocher signifie « non renseigné ».

La génération locale favorise des postes complémentaires, en complément du niveau, de la taille et des compétences. Un joueur polyvalent ne couvre qu’un poste à la fois dans ce calcul. Le critère est renforcé avec la priorité « Complémentarité des rôles » et reste souple quand l’effectif ne permet pas de couvrir tous les postes. La demande à l’IA inclut également ces consignes.

## Compatibilité JSON

Le format d’export reste `{ "version": 1, "players": [...] }`. Chaque joueur peut maintenant contenir `"positions": [1, 3]`. Les champs existants restent inchangés. Les anciens exports (objet version 1 ou tableau de joueurs) et les données déjà enregistrées dans le navigateur restent utilisables : un champ `positions` absent devient `[]`. Les postes invalides sont ignorés et les doublons supprimés.

## Vérifications

Avec Playwright Python et Chromium installés :

```sh
python3 tests/check_positions.py
python3 tests/check_manual_teams.py
python3 tests/check_engine_versions.py
```

Le test utilise `/usr/bin/chromium`. Il vérifie la sélection multiple, la persistance, les imports historiques, l’export/réimport, l’équilibrage des postes, les effectifs incomplets et l’affichage mobile. L’appel IA est simulé ; aucune clé réelle n’est nécessaire.

## Suivi des versions

La version de l’application est affichée en haut du site (`appVersion` dans `basket-equipes-autonome.html`). Pour chaque nouvelle version, mettre à jour ce libellé et ajouter une entrée dans [CHANGELOG.md](CHANGELOG.md). La version de l’application est indépendante de la version du format JSON d’import/export, qui reste à `1`.

## Ajustements manuels (version 1.3)

Après une génération locale ou IA, glisser un joueur sur une autre équipe, ou sélectionner sa destination dans le menu « Déplacer vers ». Les effectifs et statistiques sont actualisés, et « Copier » utilise la composition modifiée. Les déplacements sont libres, même si une équipe devient vide ou les effectifs inégaux. Une nouvelle génération remplace les ajustements. Comme les propositions initiales, les compositions modifiées ne sont pas conservées après rechargement de la page.

## Versions du moteur

Le sélecteur « Version du moteur » choisit l’algorithme de la prochaine génération locale, y compris « Nouvelle répartition ». Le résultat indique le moteur utilisé, même après un déplacement manuel. Le sélecteur ne recalcule pas une composition existante et ne concerne pas les appels IA.

Le moteur actuel est **v1.0**, indépendant de la version de l’application (1.4) et du format JSON (1). Son calcul est isolé dans `ENGINE_V1`. Pour toute évolution du calcul, conserver ce moteur et ses fonctions de score, créer une implémentation indépendante et l’ajouter au registre `ENGINES` sous une nouvelle version. Les options du sélecteur proviennent de ce registre. Une implémentation reçoit `{present, count, priority}` et retourne `{teams, bench, source: 'local'}` ; l’interface ajoute `engineVersion`.
