# WI-001 — Diagnostic de la consommation mémoire d’overlays-app

**Statut :** à diagnostiquer ; revue statique effectuée, aucune cause confirmée.

## Objectif et observation initiale

Identifier ce qui explique la consommation mémoire du conteneur `overlays-app`
avant de choisir un correctif.

La capture Beszel fournie par l’utilisateur indique :

- mémoire : **1,36 Go** ;
- durée de fonctionnement : **11 jours** ;
- CPU : **0,33 %** ;
- statut : **Healthy**.

Une capture ponctuelle ne démontre ni croissance continue ni fuite mémoire.
La consommation au démarrage, la courbe temporelle et l’activité durant cette
période ne sont pas connues. Le healthcheck confirme une réponse HTTP, pas la
bonne gestion de la mémoire.

## Travail déjà effectué

Revue statique du cycle de vie, du bot Twitch, des commandes, des transactions
SQL, du moteur Giveaway, des sessions/OAuth et des WebSockets OBS. Inspection
ciblée de TwitchIO **3.3.2** et d’Uvicorn **0.52.4** installés dans le venv local,
versions également déclarées dans `requirements.txt`.

**Aucun test, profilage, accès au serveur, redémarrage ou changement applicatif
n’a été effectué.** La révision et les dépendances réellement déployées restent
à confirmer ; le code local peut différer de l’image active depuis 11 jours.

Références : [architecture](../ARCHITECTURE.md),
[stabilisation sous charge](../adr/0003-stabilisation-charge.md),
[déploiement](../DEPLOY.md).

## Hypothèses à départager

### H1 — Rétention de sockets lors des reconnexions TwitchIO

**Piste prioritaire si la mémoire croît sans giveaway ni forte activité.**

L’application utilise `commands.AutoBot` dans
`app/infrastructure/twitch.py` (`GiveawayTwitchBot`).

Dans la copie locale de TwitchIO 3.3.2, fichier
`twitchio/eventsub/websockets.py` :

- `_reconnect()` crée une nouvelle socket en conservant son `shard_id` ;
- cette méthode l’insère dans
  `self._client._websockets[self._token_for][socket.session_id]`, y compris pour
  une socket de conduit ;
- `_cleanup()` retourne immédiatement lorsque `self._shard_id is not None`,
  sans retirer cette socket du dictionnaire `_websockets`.

Cela suggère que des sockets de conduit fermées peuvent rester référencées
après plusieurs reconnexions demandées par Twitch. Ce chemin est distinct d’une
simple coupure réseau : toutes les reconnexions ne passent pas nécessairement
par `_reconnect()`.

**À confirmer :** chemin effectivement emprunté en production, augmentation du
nombre d’objets retenus et poids mémoire. La lecture du code ne prouve pas que
cette rétention explique 1,36 Go. Quelques sockets fermées ne suffisent pas à
l’expliquer à elles seules. Ne pas présenter cela comme un bug amont reproduit.

Sur un autre PC, retrouver ce fichier dans le `site-packages` du venv : ne pas
réutiliser le chemin absolu ou la version de Python du poste initial.

### H2 — Accumulation non bornée des commandes en attente de SQL

**Piste prioritaire si la hausse accompagne des rafales de `!join` ou du SQL lent.**

Chemin observé :

1. TwitchIO `Client.dispatch()` crée une tâche asynchrone par listener/message.
2. `app/infrastructure/twitch.py`, `event_message()`, attend le handler.
3. `app/application/service.py`, `join()`, attend un verrou par streamer.
4. `app/infrastructure/database.py`, `transaction()`, ouvre une connexion SQL
   par transaction ; chaque inscription implique sa transaction.

Il n’existe pas de plafond applicatif des commandes attendant le verrou.
Lorsque l’arrivée dépasse le débit de traitement, les tâches peuvent s’accumuler
et conserver les messages Twitch et leurs variables. Les délais SQL ne bornent
pas le nombre de tâches ni leur attente préalable du verrou.

Les recherches de doublons sont linéaires dans `GiveawayService.join()` puis
`GiveawayEngine.join()` : elles peuvent aggraver le retard lorsque le nombre de
participants augmente.

**À confirmer :** débit entrant, latence SQL, nombre de tâches en attente et
évolution après résorption de la charge. Un backlog transitoire n’est pas en soi
une fuite ; une mémoire résidente restant élevée peut aussi relever des
allocateurs après un pic.

### H3 — Données métier conservées et lectures volumineuses

- `app/main.py`, `ensure_streamer_context()`, conserve moteurs, services et
  handlers dans des dictionnaires, sans éviction lors d’une désactivation.
- Un giveaway actif conserve ses participants en mémoire, y compris après un
  tirage. `app/domain/giveaway.py`, `stop()`, vide bien participants et gagnants.
- `app/infrastructure/history.py`, `load_giveaway_detail()`, charge tous les
  participants et gagnants du giveaway demandé, sans pagination du détail :
  une lecture volumineuse peut provoquer un pic, sans rétention durable prouvée.

**À confirmer :** nombre de contextes, participants des giveaways actifs et
consultations de gros historiques. Hypothèse moins convaincante avec seulement
quelques comptes et de petits giveaways.

## Ressources dont la gestion paraît déjà bornée

Dans le code inspecté, sans validation d’exécution :

- sessions : 4096 globales, 32 par streamer, avec expiration ;
- states OAuth : 512, avec expiration ;
- files OBS : un état en attente par socket, remplacé par le dernier état ;
- connexions OBS authentifiées : 256 globales, 8 par streamer ;
- connexions SQL : fermeture prévue par les context managers ;
- aucun historique complet du chat explicitement conservé dans notre code.

Ces bornes ne couvrent pas tous les buffers réseau ni les allocations des
bibliothèques. La limite applicative de 512 caractères pour l’authentification
OBS intervient après assemblage ASGI. Les paramètres transport Uvicorn ne sont
pas explicitement réduits dans le Dockerfile : ne pas confondre taille des
messages applicatifs et taille maximale des buffers.

## Reprise guidée sur l’autre PC

### 1. Reconstituer les faits sans perdre l’état actuel

- [ ] Demander si les 11 jours comportaient des giveaways importants, des
  coupures Twitch/réseau ou essentiellement de l’inactivité.
- [ ] Consulter la courbe mémoire Beszel : croissance régulière, marches,
  pics liés à l’activité ou plateau ? Noter les horaires de corrélation.
- [ ] Confirmer la révision de l’image active et les versions des dépendances,
  sans afficher les variables d’environnement ni la configuration secrète.
- [ ] Distinguer mémoire du conteneur, mémoire résidente/anonyme des processus
  et cache comptabilisé ; ne pas supposer que 1,36 Go correspond au tas Python.
- [ ] Identifier si un seul processus porte la consommation.

**Résultat attendu :** contexte d’activité, version réellement examinée et nature
de la mémoire mesurée. Cela ne prouve pas encore quelle allocation est retenue.

Ne pas redémarrer avant collecte : cela ferait perdre l’état utile au diagnostic.
Les commandes de mesure serveur restent à proposer et à faire approuver ; ce WI
n’autorise pas leur exécution et aucune procédure de profilage n’a été validée.

### 2. Choisir une mesure ciblée selon les faits

- [ ] Si croissance au repos : examiner en priorité les reconnexions TwitchIO,
  le nombre de sockets actives/fermées référencées et les tâches persistantes.
- [ ] Si croissance pendant les inscriptions : mesurer le nombre de tâches en
  attente du verrou, la durée des transactions et la résorption du backlog.
- [ ] Si croissance lors de consultations : examiner les tailles des réponses
  d’historique et la concurrence des requêtes.
- [ ] Si nécessaire, proposer une instrumentation minimale séparée permettant
  de comparer deux relevés d’allocations, avec ses limites et son coût.

N’enregistrer que des métriques agrégées : aucun payload de chat, token,
cookie, URL OBS secrète ou contenu de configuration réelle. Une inspection
mémoire brute peut contenir des secrets : ne pas l’exporter ni la partager.

### 3. Reproduire puis décider, avec accord distinct

- [ ] Proposer une reproduction isolée, à données fictives, du chemin suspect.
- [ ] Obtenir l’accord avant création de tests/scripts, instrumentation,
  installation d’outils ou exécution des contrôles.
- [ ] Relier l’évolution mémoire à une famille d’objets ou de tâches, plutôt
  qu’à la seule durée de fonctionnement.
- [ ] Proposer ensuite un correctif borné et son protocole de validation.

Ne pas ajouter automatiquement de pool SQL, mise à jour de dépendance, worker,
redémarrage périodique ou limite mémoire Docker : ce sont des décisions
séparées, pas des conclusions du diagnostic.

## Critère de fin

Le diagnostic est terminé lorsqu’une cause est étayée par des mesures ou une
reproduction ciblée, ou qu’une hypothèse est explicitement écartée avec ses
preuves. Consigner les observations et les incertitudes restantes ici, puis
faire approuver le correctif séparément.

Le périmètre de ce WI est le **diagnostic**, pas l’implémentation du correctif,
le déploiement ou une campagne de charge en production.
