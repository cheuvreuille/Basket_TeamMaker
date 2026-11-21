# Basket_TeamMaker

Application autonome : ouvrir `basket-equipes-autonome.html`, ou servir le dossier avec `python3 -m http.server 8000`. `index.html` redirige vers l’application pour GitHub Pages.

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

Après une génération locale ou IA, glisser un joueur sur une autre équipe, ou sélectionner sa destination dans le menu « Déplacer vers ». Les joueurs sont affichés par poste principal (1 à 5, postes non renseignés en dernier), y compris dans la copie. La synthèse sous chaque nom présente le niveau global en toutes lettres, la taille en cm, le genre et le nom du poste principal. Le menu de transfert est compact. Les effectifs et statistiques sont actualisés, et « Copier » utilise la composition modifiée. Les déplacements sont libres, même si une équipe devient vide ou les effectifs inégaux. Une nouvelle génération remplace les ajustements. Les compositions non enregistrées ne sont pas conservées après rechargement de la page. Le bouton « Save » permet désormais de les archiver dans le suivi.

## Vérifications

Avec Playwright Python et Chromium installés :

```sh
python3 tests/check_whatsapp_prototype.py
python3 tests/check_teammates.py
python3 tests/check_history.py
python3 tests/check_teamwork.py
python3 tests/check_positions.py
python3 tests/check_manual_teams.py
python3 tests/check_engine_versions.py
```

Les tests utilisent `/usr/bin/chromium`. Ils vérifient la migration des formats historiques, les postes principaux et secondaires, la persistance, l’export/réimport, les deux moteurs, l’ordre de priorité v2, les effectifs incomplets, les déplacements et l’affichage mobile. Les appels IA sont simulés ; aucune clé réelle n’est nécessaire. La comparaison avec le moteur historique utilise des joueurs ayant chacun un seul poste principal.

## Suivi des versions

La version de l’application est affichée en haut du site (`appVersion` dans `basket-equipes-autonome.html`). Pour chaque nouvelle version, mettre à jour ce libellé et ajouter une entrée dans [CHANGELOG.md](CHANGELOG.md). La version de l’application (2.2), les versions des moteurs (1.0, 2.0 et 3.0) et la version du format JSON (1) sont indépendantes.

## Couleurs des équipes (1.5.2)

Chaque carte d’équipe propose la palette noir, blanc, bleu, jaune, violet et vert, ainsi qu’un sélecteur de couleur personnalisée. Les valeurs initiales suivent cet ordre : les deux premières équipes sont donc noires et blanches. Les couleurs restent attachées aux numéros d’équipe lors des transferts et des nouvelles répartitions dans la session. Elles sont réinitialisées au rechargement de la page.

## Jeu en équipe (1.6)

La fiche de chaque joueur comporte une jauge à trois niveaux : **−1 : Trop perso**, **0 : Équilibré**, **1 : Trop altruiste**. La valeur est conservée lors des modifications, des rechargements et des exports JSON dans le champ numérique `teamwork`. Les fichiers JSON et les données locales qui ne comportent pas ce champ reçoivent automatiquement la valeur `0`. Les valeurs invalides sont également ramenées à `0`. Le format JSON reste en version 1. Les exports restent lisibles par les anciennes versions de l’application, qui ignorent ce champ supplémentaire.

Seul le nouveau moteur local **3.0** tient compte de cette caractéristique. Les calculs des moteurs **1.0 et 2.0** sont inchangés et l’ignorent. Les consignes de l’option IA décrivent également ce nouveau champ.

## Statistiques & suivi (2.0)

L’onglet **Team Maker** conserve le fonctionnement actuel. Après une génération locale ou IA et les éventuels transferts, **Save** enregistre une séance datée du jour local du navigateur. Elle contient les joueurs présents, une copie de leurs profils, les équipes affichées, leurs couleurs et la version du moteur. Le bouton demande de régénérer les équipes si les présences ne correspondent plus à la composition affichée. Un second enregistrement le même jour propose de remplacer la séance ; chaque joueur ne participe donc qu’une fois par jour.

L’onglet **Statistiques & suivi** affiche :

- Une courbe du nombre de présents pour chaque jour enregistré, avec un point par séance.
- Un tableau de classement des joueurs, du plus au moins présent, avec le rang et le nombre total de participations. Les égalités sont départagées par nom. Les joueurs actuels sans présence sont affichés à zéro ; les anciens participants restent visibles même s’ils ont quitté l’effectif. Les noms courants sont utilisés pour les joueurs de l’effectif, et les derniers noms enregistrés pour les autres. L’identité est suivie par identifiant de joueur, pas par nom.
- Un éditeur de séance : sélection du jour, modification de la date, du nom historique des joueurs et de leur affectation ; ajout/retrait de participants depuis l’effectif ; ajout, renommage, changement de couleur ou suppression d’équipes ; suppression de la séance entière. Les modifications sont appliquées avec **Enregistrer les modifications**. Supprimer une équipe garde ses joueurs présents, sans affectation. Retirer un joueur ou supprimer une séance recalcule les graphiques.

Les corrections portent uniquement sur l’historique. Elles ne modifient pas les joueurs, présences ou compositions du Team Maker. Les copies de profils sont conservées pour permettre de futurs suivis de complémentarité ; cette première version présente les deux statistiques de présence demandées.

### Sauvegarde et compatibilité

L’export conserve le fichier `basket-joueurs.json`, le format des joueurs et la version JSON `1`, avec un champ supplémentaire :

```json
{
  "version": 1,
  "players": [],
  "sessions": []
}
```

Chaque séance comporte `id`, `date` (`YYYY-MM-DD`), `savedAt`, `players` (copies des participants), `teams` (`id`, `name`, `color`, `playerIds`), `bench` (présents non affectés), `source`, `engineVersion` et `manuallyEdited`. Les références aux joueurs sont propres aux copies de la séance : un joueur retiré plus tard de l’effectif reste dans l’historique. Une date ne peut contenir qu’une séance ; chaque participant ne peut être affecté qu’une fois.

- Les anciens tableaux de joueurs et les objets JSON sans `sessions` remplacent toujours l’effectif et **conservent l’historique local existant**.
- Un objet avec `sessions` remplace l’effectif et l’historique après validation. `"sessions": []` vide explicitement l’historique.
- Un historique invalide (date en double, joueur inconnu dans une équipe, affectation en double…) bloque l’import entier : aucune modification partielle de l’effectif.
- Les anciennes versions de l’application peuvent encore lire `players`, mais ignorent `sessions` et ne le réexportent pas.

Les séances persistent dans la clé locale `basket-sessions-v2`, séparée de la clé existante des joueurs. Aucun serveur, compte ni service externe n’est nécessaire. Exportez régulièrement le JSON pour conserver une sauvegarde des deux ensembles de données.

## Coéquipiers les plus fréquents (2.1)

Dans **Statistiques & suivi**, choisir un **Joueur de référence**. Il apparaît au centre d’un réseau de cercles reliés : le nombre indique les séances jouées dans la même équipe, et les cercles les plus grands et foncés correspondent aux coéquipiers les plus fréquents. La taille et la couleur sont relatives au maximum du joueur sélectionné. Les noms complets et les comptes sont disponibles au survol, au clavier et dans la liste détaillée.

Le calcul utilise uniquement les équipes des séances enregistrées, pas les compositions courantes non sauvegardées. Une paire est comptée une fois par séance ; adversaires, présents non affectés et joueur lui-même sont exclus. Le suivi repose sur les identifiants, conserve les joueurs archivés et se recalcule après correction, suppression ou import. Les noms suivent la même règle que le classement : nom courant si le joueur est encore dans l’effectif, sinon dernier nom enregistré.

La vue affiche les huit coéquipiers les plus fréquents par défaut pour rester lisible. Le sélecteur permet d’en afficher seize ou tous ; la liste complète reste disponible dans tous les cas. Pour les réseaux importants, plusieurs anneaux sont utilisés et le schéma peut défiler dans son cadre, notamment sur mobile. À égalité, le tri est alphabétique. Aucune nouvelle donnée ni version de format JSON n’est nécessaire : les relations sont calculées à partir des séances existantes.

## WhatsApp integration — POC de lecture (2.2)

**MAQUETTE — À NE PAS UTILISER en production avant validation des votes dans votre groupe.**

La passerelle utilise **whatsapp-web.js 1.34.8**, bibliothèque non officielle, et non l’API Meta WhatsApp Business. La version et ses dépendances sont verrouillées dans `package-lock.json`. Les méthodes et champs ont été vérifiés dans le paquet distribué, notamment `selectedOptions[].localId` (y compris la valeur `0`), `voter`, `interractedAtTs` et les retraits de vote (liste d’options vide).

### Démarrer sur un PC ou serveur local

Prévoir Node.js 20 ou supérieur et Chromium/Chrome. Depuis le dépôt :

```sh
npm ci
npm start
```

Le service écoute uniquement sur l’interface locale `127.0.0.1`, port `8787`, et sert aussi Team Maker à la racine. Ouvrir l’application depuis ce service est le parcours recommandé : les données du navigateur restent attachées à leur origine, donc exporter/importer le JSON permet de déplacer l’effectif et l’historique depuis GitHub Pages vers cette instance locale.

Si Chromium est déjà installé, indiquer son chemin avec `WA_CHROMIUM_PATH`. Dans cet environnement cloud, l’installation a été vérifiée avec :

```sh
PUPPETEER_SKIP_DOWNLOAD=true npm --cache /tmp/basket-npm-cache ci --no-audit --no-fund
WA_CHROMIUM_PATH=/usr/bin/chromium WA_NO_SANDBOX=1 npm start
```

`WA_NO_SANDBOX=1` est une adaptation au conteneur de développement ; le parcours PC conserve le bac à sable de Chrome par défaut. Ne pas désactiver les contrôles TLS. L’interface GitHub Pages reste autonome pour les autres fonctions, mais ne peut pas exécuter ce service Node.js.

### Connexion et session

1. Dans **WhatsApp integration**, saisir l’adresse du service local et cliquer sur **Connecter WhatsApp**.
2. Scanner le QR avec WhatsApp → **Appareils connectés**. L’état passe de connexion à QR, authentification, puis connecté.
3. Choisir le groupe de basket. Son identifiant est conservé sur le service.
4. Cliquer sur **Importer le dernier sondage** : lecture de 500 messages récents au maximum, détection des messages `poll_creation`, filtrage par présence/entraînement ou par mot du titre. La liste permet de choisir un autre sondage pour éviter de confondre plusieurs questions.
5. Vérifier les votes nominatifs par réponse et les comparer à WhatsApp sur 2 ou 3 sondages récents, puis sur les plus anciens accessibles. Un résultat vide n’est pas une preuve d’absence de votes.

La session `LocalAuth` est conservée dans `.whatsapp-data/auth`. Le service essaie de la restaurer au démarrage, se reconnecte après une coupure réseau, et demande une nouvelle connexion après expiration/révocation. **Arrêter le suivi de connexion** arrête seulement l’actualisation de l’écran ; pour révoquer la session, utiliser WhatsApp → Appareils connectés. Aucun QR brut, nom ou contenu de conversation n’est journalisé par la passerelle.

Le chemin persistant peut être changé avec `WA_DATA_DIR`. Ce dossier doit rester privé : il contient l’accès à la session et le profil synchronisé par WhatsApp Web, qui peut lui-même conserver des données. Le fichier `settings.json` contient seulement le groupe choisi et la correspondance des identités. Ce dossier, les caches, `.env` et `node_modules` sont exclus de Git. Ne pas partager une archive ou un snapshot contenant une session connectée.

### Correspondance et application explicite

Associer manuellement chaque identité WhatsApp à une fiche Team Maker ; aucun rapprochement automatique par nom n’est effectué. Les associations `whatsappId → playerId` sont conservées par le service et plusieurs identités d’un même joueur peuvent pointer sur sa fiche. Si un joueur est retiré de l’effectif, son ancienne association ne permet pas une application silencieuse : les votants de la réponse choisie doivent être rattachés à des fiches actuelles.

Choisir la bonne réponse d’entraînement, consulter l’aperçu, puis cliquer sur **Appliquer cette réponse aux présences**. Les votes sont relus avant l’action ; s’ils ont changé, l’application demande de revoir l’aperçu. Une erreur de lecture, une association manquante ou un vote contradictoire présent/absent bloque l’application.

- Mode par défaut : cocher les votants confirmés, décocher les absences/blessures explicites, conserver les autres cases. Les non-répondants et les autres réponses restent distincts des refus.
- Mode remplacement : remplacer toute la sélection par les seuls votants de cette réponse. Les non-répondants ne sont alors pas cochés, sans être qualifiés de refus explicites dans l’aperçu.

Les cases restent corrigeables manuellement dans Team Maker. Aucune équipe n’est générée et aucune séance historique n’est créée automatiquement. La resynchronisation met seulement la lecture et l’aperçu à jour, jamais les présences. Les données de démonstration ne peuvent pas être appliquées.

### Fiabilité et limites

Le serveur utilise `getChats`, `getChatById`, `fetchMessages({limit:500})`, `getPollVotes` et `vote_update`. Les versions successives d’un vote sont réduites au dernier vote par identité ; un retrait n’est pas un refus. Une relecture toutes les 60 secondes complète les événements `vote_update` ; l’interface peut aussi demander **Resynchroniser les votes**. La passerelle n’expose aucune route d’envoi de message ni de vote.

L’accès aux votes dépend de leur disponibilité réelle dans WhatsApp Web et de la bibliothèque. Les 500 messages accessibles ne garantissent pas l’historique complet ni une reconstruction depuis janvier 2026. L’import historique et l’application automatique en arrière-plan restent des étapes futures. Informer les membres de l’équipe de la collecte avant le POC.

**Validation actuelle :** dépendances installées, service HTTP lancé et testé, Chromium lancé, API et UI vérifiées avec un client WhatsApp simulé. Dans le cloud, la navigation réelle vers `web.whatsapp.com` échoue avec `ERR_TUNNEL_CONNECTION_FAILED` ; l’accès HTTPS via le proxy renvoie `403 Forbidden`. Aucun QR réel, vote réel ou historique de compte n’a donc été validé. Le test doit être poursuivi sur un PC disposant de l’accès à WhatsApp, ou après autorisation réseau dans l’environnement.

### Configuration et accès

- `PORT` : port local, `8787` par défaut.
- `WA_CHROMIUM_PATH` : exécutable Chrome/Chromium si nécessaire.
- `WA_DATA_DIR` : dossier persistant privé.
- `WA_NO_SANDBOX` : adaptation explicite au conteneur uniquement.
- `WA_ALLOWED_ORIGINS` : origines HTTP(S) supplémentaires, séparées par des virgules. Par exemple l’origine GitHub Pages exacte si l’on souhaite connecter cette interface à la passerelle. Le navigateur peut imposer des autorisations supplémentaires pour accéder à un service local depuis une page publique ; utiliser l’interface servie localement évite ce problème.

Par défaut, le service refuse les origines étrangères et les en-têtes Host non locaux. Il ne doit pas être exposé tel quel sur Internet. Un hébergement distant nécessiterait HTTPS et une authentification dédiée ; aucun jeton WhatsApp ne doit être intégré à la page GitHub Pages.

Les imports/exports existants des joueurs et séances sont inchangés. Les associations WhatsApp sont conservées séparément sur le service et ne figurent pas dans ce JSON. Les deux scripts métiers existants sont inchangés ; seul le nouveau module réalise l’application explicite en appelant les fonctions existantes `persist()` et `render()`.

### Tests supplémentaires

```sh
npm test
python3 tests/check_whatsapp_prototype.py
python3 tests/check_whatsapp_bridge.py
```

Les tests Node simulent le client de lecture : session/QR, reconnexion, groupe, dernier sondage, votes multiples, retraits, synchronisation et contrôle des accès HTTP. Les tests navigateur couvrent les associations, les modes d’application, la relecture avant application, les erreurs, la démonstration et l’affichage mobile. Aucun de ces tests ne prouve la disponibilité réelle des votes de votre compte.

Sources : [whatsapp-web.js Client](https://docs.wwebjs.dev/Client.html), [LocalAuth](https://wwebjs.dev/guide/creating-your-bot/authentication.html), et paquet npm `whatsapp-web.js@1.34.8` vérifié localement.
