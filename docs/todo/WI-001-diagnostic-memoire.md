# WI-001 — Diagnostic de la consommation mémoire d’overlays-app

**Statut :** en cours ; 1002 connexions établies vers les IP résolues pour
EventSub et quasi-saturation des descripteurs constatées en production. Défaut
de fermeture TwitchIO reproduit sur TCP réel isolé ; explication principale
très probable, contribution exacte aux 1,4 Gio non mesurée. Correctif versionné
implémenté localement, contrôlé avec transport simulé et validé en comparaison
TCP réelle avant/après dans le conteneur jetable. Aucun déploiement.

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

L’utilisateur a depuis exécuté des relevés SSH en lecture seule et transmis
leurs résultats. Un contrôle automatisé ponctuel local compare trois scénarios
de fermeture TwitchIO avec un transport simulé ; il est détaillé dans H4.
Aucun fichier de test/script n’a été créé ni outil installé pour ce contrôle.
Un script a ensuite été créé avec accord spécifique, puis exécuté par
l’utilisateur dans un conteneur jetable pour vérifier le transport réel.

L’assistant n’a pas accédé directement au serveur. Aucun profilage mémoire,
dump, redémarrage ou déploiement n’a été effectué dans ce diagnostic. Un
correctif local du cycle TwitchIO a ensuite été implémenté avec accord ; il
n’est pas livré au serveur. Le tag de l’image et certaines versions déployées
sont connus ; le code embarqué et les dépendances transitives ne sont pas
encore entièrement vérifiés.

Références : [architecture](../ARCHITECTURE.md),
[stabilisation sous charge](../adr/0003-stabilisation-charge.md),
[déploiement](../DEPLOY.md).

## Relevés de production du 24 octobre 2026

Résultats transmis par l’utilisateur, sans logs bruts, secrets ni dump mémoire :

- Image déclarée :
  `ghcr.io/necsus/overlays:sha-12c99d244943fed8d594010e2d4a787ed7073b70`.
  Le label OCI de révision est absent ; le tag ne vérifie pas le contenu embarqué.
- Démarrage : `2026-10-11T21:09:26Z`, avec zéro redémarrage pour ce conteneur.
  Ce compteur ne renseigne pas les recréations lors de déploiements précédents.
- Versions déployées : Python **3.13.15**, TwitchIO **3.3.2**, Uvicorn **0.52.4**.
  La version d’aiohttp a ensuite été confirmée : **3.14.5**.
- Docker : **1,399 Gio** de mémoire ; un seul processus `uvicorn`, six threads.
- `/proc/1/status` : RSS **1 482 296 kB**, mémoire anonyme **1 457 788 kB**,
  mémoire fichier **24 508 kB**, swap nul. Les `kB` de `/proc` valent 1024 octets.
- `/proc/1/smaps_rollup` confirme **1 457 788 kB** de mémoire anonyme/privée sale.
  Le cgroup indique `anon = 1 493 069 824` octets, `file = 0`,
  `sock = 4096` octets : cache fichier et buffers réseau du noyau n’expliquent
  pas l’essentiel. Cela n’exclut pas des objets réseau dans le tas du processus.
- RSS et mémoire anonyme identiques à **13:31:23** et **13:34:41 UTC** : plateau
  observé sur **3 min 18 s**, sans preuve de stabilité sur plusieurs jours.
- Comptage des logs disponibles des dernières 24 h : **1188 avertissements**
  `needs to close unexpectedly`, tous associés à `Conduit Websocket`.
  Ils sont concentrés entre 01 h et 08 h UTC, avec **419 lignes entre 06 h et
  07 h**. Il s’agit de lignes, pas d’un compte vérifié de connexions distinctes.
- Aucun message de reconnexion demandée par Twitch n’a été compté ; son niveau
  de journalisation peut toutefois le rendre absent. Ce compteur ne prouve
  donc pas que le chemin H1 n’a jamais été emprunté.
- Sur une fenêtre récente de cinq minutes : **10 requêtes HTTP, toutes vers
  `/health`**, aucune autre requête HTTP et aucun nouvel avertissement de coupure
  Twitch. Cela ne mesure pas les messages de chat reçus ni les clients déjà
  connectés.

L’application est déclarée inutilisée. L’activité historique du chat Twitch,
la mémoire au démarrage et la courbe Beszel sur plusieurs jours restent inconnues.
Le trafic réseau Docker affiché est cumulé, pas un débit instantané.

**Conclusion du diagnostic à ce stade :** la mémoire réside principalement dans
les allocations anonymes du processus Python ou de ses bibliothèques natives.
Les relevés ultérieurs détaillés dans H4 montrent de très nombreuses connexions
vers les IP résolues pour EventSub et un processus proche de sa limite de
fichiers ouverts. Avec le défaut de fermeture reproduit, l’accumulation de
transports Twitch est l’explication principale très probable ; son coût mémoire
exact et le passage par cette branche dans le processus réel ne sont pas tracés.
Les sockets Twitch/EventSub sont distinctes des connexions OBS ; l’expiration
OBS décrite dans l’architecture ne les ferme pas.

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

Les avertissements de coupure constatés en production viennent de
`_create_connection_task()`, pas directement de `_reconnect()` : ils ne suffisent
pas à confirmer ce chemin. Voir également H4.

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

### H4 — Annulation du keepalive pendant sa propre fermeture

**Nettoyage interrompu et transport TCP laissé ouvert reproduits dans un
conteneur isolé issu de l’image déployée. Rétention mémoire durable et passage
par ce chemin dans le processus de production non démontrés.**

Chemin lu dans TwitchIO 3.3.2 :

1. `_process_keepalive()` constate l’expiration et attend
   `_create_connection_task()`.
2. Pour un conduit, cette méthode journalise l’avertissement de coupure puis
   attend `close()`.
3. `close()` marque le wrapper fermé/en cours de fermeture, émet
   `websocket_closed`, puis annule `_keep_alive_task`, ici la tâche courante.
4. Si `await self._socket.close()` suspend l’exécution, l’annulation peut y être
   délivrée. `CancelledError` n’est pas interceptée par `except Exception` : la
   remise à zéro des références et de `_closing` située après cet appel est sautée.

#### Contrôle ponctuel autorisé et résultats

Exécution locale de Python avec `-B`, sans nouveau fichier, réseau, Twitch,
configuration réelle ni token. Versions locales : TwitchIO **3.3.2**, aiohttp
**3.14.3**. Aucun transport aiohttp réel n’est instancié : seul son type de message
est utilisé par le faux transport. Le client simulé compte les événements sans
retenir leurs payloads et sans lancer de réassociation.

Les méthodes réelles `_process_keepalive()`, `_create_connection_task()`,
`_listen()` et `close()` sont utilisées. Le délai du scénario keepalive est
raccourci à 0,01 s et son dernier message est daté artificiellement dans le passé.
Le faux transport réveille le lecteur avant de suspendre sa fermeture.

| Scénario | Résultat |
| --- | --- |
| Fermeture depuis une tâche indépendante, transport avec attente | Faux transport fermé, références socket/keepalive/listener effacées, `_closing=False` |
| Fermeture depuis le keepalive expiré, transport avec attente | Fermeture du faux transport annulée, références conservées, `_closed=True` et `_closing=True` |
| Fermeture depuis le keepalive expiré, transport sans suspension | Nettoyage terminé malgré la demande d’auto-annulation |

Dans le scénario interrompu, un second `close()` retourne sans reprendre le
nettoyage, à cause de la garde `_closed or _closing`.

**Limites importantes :** la vraie tâche `_listen()` termine dans les trois
scénarios, y compris celui interrompu. Aucune accumulation de tâches n’est donc
reproduite. La persistance des références est constatée sur un wrapper encore
référencé par l’expérience ; elle ne prouve pas que ces objets survivraient au
ramasse-miettes. Le faux transport ouvert n’est pas une preuve de fuite de socket
réelle. Le démontage explicite de l’expérience ne laisse aucune tâche en attente.
Aucune croissance de RAM, charge répétée ou allocation de 1,4 Gio n’a été reproduite.

Les avertissements réels peuvent aussi venir du lecteur réseau, sans expiration
du keepalive : leur texte seul ne prouve pas le passage par cette auto-annulation.

#### Protocole réel exécuté et résultats

L’utilisateur a autorisé un contrôle avec un transport réel local, puis la
création de [scripts/diagnose_twitch_websocket.py](../../scripts/diagnose_twitch_websocket.py)
pour éviter un long bloc à coller dans SSH. La syntaxe, l’aide et la construction
des commandes Docker ont été contrôlées localement avec des appels Docker
simulés. Aucun conteneur ni échange réseau réel n’a été lancé pour ces contrôles.
Les diagnostics LSP sont indisponibles sur ce poste.

Les résultats ci-dessous concernent la première version du script, transférée
sous `/tmp/overlays-ws-diag.py` et sans correctif. La procédure courante de
comparaison avant/après, nécessitant deux fichiers, figure plus bas.

Le lanceur ne dépend que de la bibliothèque standard du Python de l’hôte. Il
lit l’identifiant exact de l’image d’`overlays-app`, puis alimente le Python d’un
conteneur jetable via STDIN. Il ne démarre pas l’application et ne lit ni
configuration réelle ni token. Il n’injecte aucun secret et ne monte aucun
volume ni fichier dans le conteneur.

Le conteneur possède un nom unique, un système de fichiers en lecture seule,
aucun réseau extérieur ni port publié, et des plafonds de 256 Mio, 0,5 CPU et
64 tâches. L’essai utilise uniquement son loopback, sans TLS, et vérifie les
versions TwitchIO/aiohttp avant d’ouvrir une connexion. La première version
comparait cinq fermetures normales et cinq expirations keepalive, avec un délai
raccourci à une seconde.
Les compteurs sont pris avant un nettoyage manuel de chaque cycle : ils ne
mesurent donc pas une accumulation volontaire de ressources ni la mémoire retenue.
La réassociation AutoBot n’est pas simulée.

L’expérience possède un délai asynchrone de 45 s et une alarme de 50 s ; le
lanceur borne l’appel Docker à 60 s. Docker supprime le conteneur à sa sortie ;
en cas d’interruption ou dépassement du délai du lanceur, celui-ci demande aussi
la suppression du seul conteneur temporaire qu’il a nommé. La suppression de la
copie du script dans `/tmp` reste à effectuer après collecte.

L’utilisateur a transmis une exécution complète avec Python **3.13.15**,
TwitchIO **3.3.2** et aiohttp **3.14.5**, depuis l’image exacte
`sha256:f886aa26e5725f9e7cccecaf9317a97c37a7a60d77a99dee4843430bfe970512`.

| État avant nettoyage manuel | Fermeture normale, 5 cycles | Expiration keepalive, 5 cycles |
| --- | --- | --- |
| Nettoyage du wrapper incomplet | 0/5 | 5/5 |
| WebSocket client encore ouvert | 0/5 | 5/5 |
| Transport TCP encore ouvert | 0/5 | 5/5 |
| Connexion encore ouverte côté serveur fictif | 0/5 | 5/5 |
| Tâche listener encore en cours | 0/5 | 0/5 |

Ces valeurs cumulent les observations de chaque cycle, environ 50 ms après la
fermeture attendue ; elles ne représentent pas cinq connexions ouvertes
simultanément. Après le nettoyage explicite : **zéro connexion serveur restante
et zéro tâche en attente**.

**Résultat confirmé :** pour ce scénario d’expiration keepalive, TwitchIO ne
termine pas le nettoyage et laisse réellement le transport TCP ouvert au point
de mesure. Ce n’est plus seulement une simulation de socket.

**Ce qui reste inconnu :** la durée de survie sans nettoyage manuel, le
comportement TLS et AutoBot, la fréquence de ce chemin en production et son
coût mémoire. L’expérience conserve les références nécessaires à l’inspection ;
elle ne prouve pas leur rétention après disparition des références de test.
Aucune croissance RSS ni allocation de 1,4 Gio n’a été mesurée ou reproduite.

#### Descripteurs du processus de production

Un relevé passif transmis ensuite par l’utilisateur compte **1019 descripteurs
ouverts dans `/proc/1/fd`, dont 1009 de type socket**. C’est un signal fort
renforçant la piste d’une accumulation de ressources réseau. Ce comptage ne
vérifie toutefois ni les sockets uniques par inode ni leurs destinations.

Le relevé suivant indique une limite de fichiers ouverts **soft de 1024** et
**hard de 524288** pour le processus. Le précédent comptage de 1019 descripteurs
laissait donc environ cinq places avant la limite active ; ces mesures ne sont
pas synchronisées. Augmenter la limite ne corrigerait pas une fuite et pourrait
laisser l’accumulation se poursuivre.

Les tables TCP de l’espace réseau du conteneur contiennent **1006 connexions
établies (`01`, ESTABLISHED) vers le port distant 443**. Ce ne sont donc pas
simplement des entrées TIME_WAIT. L’appariement aux descripteurs du PID 1 par
inode reste à effectuer ; le conteneur n’avait qu’un processus Uvicorn lors du
relevé des processus.

Le regroupement suivant, converti depuis l’encodage IPv4 little-endian de
`/proc`, correspond exactement aux adresses renvoyées par la résolution DNS
`eventsub.wss.twitch.tv` effectuée dans le conteneur :

| Adresse distante résolue pour EventSub, port 443 | Connexions établies |
| --- | --- |
| `143.204.194.32` | 246 |
| `143.204.194.29` | 255 |
| `143.204.194.41` | 260 |
| `143.204.194.51` | 241 |
| **Total correspondant au DNS EventSub** | **1002** |

Les quatre autres connexions vers 443 ne sont pas attribuées à un service.
La conversion des adresses et les totaux ont été vérifiés localement. La
correspondance DNS est un indice fort, mais ne vérifie pas le nom TLS de chaque
connexion et des IP de CDN peuvent être partagées.

Le défaut de fermeture reproduit, les nombreux descripteurs du processus réel
et ces destinations font de l’accumulation de transports Twitch l’explication
principale très probable. Des objets Python, états TLS et buffers utilisateurs
peuvent contribuer à la mémoire anonyme sans apparaître dans le petit compteur
`sock` du noyau. Leur taille n’a pas été mesurée. Le plateau de RAM pourrait
aussi s’expliquer par l’approche de la limite de descripteurs ; ce n’est pas
une stabilité saine démontrée.

#### Vérification amont et suite proposée

Lors de la consultation, l’[API de dernière release GitHub](https://api.github.com/repos/TwitchIO/TwitchIO/releases/latest)
annonce encore **v3.3.2**. Le [code `main` consulté](https://github.com/TwitchIO/TwitchIO/blob/main/twitchio/eventsub/websockets.py)
conserve l’annulation de `_keep_alive_task` avant l’attente de fermeture du
transport. Aucune correction officielle directement utilisable n’est donc
identifiée dans ces sources ; cela ne constitue pas une revue de toutes les PR.

#### Correctif local validé en comparaison TCP isolée, non livré

L’utilisateur a approuvé l’intégration d’un correctif de compatibilité limité à
TwitchIO 3.3.2. L’[architecture](../ARCHITECTURE.md#compatibilité-des-connexions-twitch)
décrit son installation et son comportement. Aucun fichier de bibliothèque
installée n’est modifié ; aucune dépendance ni limite de fichiers n’a changé.

Contrôles locaux ponctuels avec transport simulé et méthodes TwitchIO réelles :

- le défaut initial est reproduit avant installation du correctif ;
- après installation, le keepalive termine sa fermeture sans s’auto-annuler ;
- une fermeture normale annule toujours une autre tâche de keepalive ;
- les options `cleanup=False` et `reassociate=False` sont transmises inchangées ;
- une annulation externe continue de se propager ;
- l’installation répétée est idempotente, y compris depuis deux chargements du module ;
- une autre version de TwitchIO est refusée avant toute installation ;
- aucune tâche n’est laissée en attente et le fichier TwitchIO installé reste inchangé.

La syntaxe et l’ordre d’installation avant la construction d’AutoBot sont aussi
contrôlés. Le lanceur Docker et son nettoyage sont vérifiés avec des appels
simulés. L’utilisateur a ensuite transmis la comparaison TCP réelle réussie
sur le Geekom, détaillée ci-dessous. TLS, AutoBot réel et l’évolution RAM après
livraison restent à valider.

La version courante du diagnostic transmet via STDIN son code et la source de
`app/infrastructure/twitch_websocket.py`, sans réimplémenter le correctif. Dans
le conteneur jetable, elle compare cinq expirations `actuel` puis cinq
`corrige`, avec les mêmes limites d’isolation et de ressources. Elle restaure
la méthode initiale en fin d’essai. Un résultat inattendu termine le contrôle
en erreur.

Résultats transmis par l’utilisateur avec Python **3.13.15**, TwitchIO **3.3.2**
et aiohttp **3.14.5**, sur la même image exacte que la reproduction initiale :

| État avant nettoyage manuel | Mode `actuel`, 5 cycles | Mode `corrige`, 5 cycles |
| --- | --- | --- |
| Nettoyage du wrapper incomplet | 5/5 | 0/5 |
| WebSocket client encore ouvert | 5/5 | 0/5 |
| Transport TCP encore ouvert | 5/5 | 0/5 |
| Connexion encore ouverte côté serveur fictif | 5/5 | 0/5 |
| Tâche listener encore en cours | 0/5 | 0/5 |

Après nettoyage : **zéro connexion serveur et zéro tâche restante**. Le script
a affiché `Comparaison avant/apres reussie.`. Ces compteurs sont cumulés par
cycle, sans accumulation simultanée volontaire.

**Validation acquise :** le correctif applicatif empêche le défaut de fermeture
TCP reproduit, avec les versions de l’image déployée et un transport réel isolé.
Ce contrôle ne mesure ni l’empreinte mémoire TLS, ni les reconnexions AutoBot,
ni l’efficacité durable dans le processus de production.

Depuis le poste de travail, transférer uniquement le script et le module de
compatibilité dans le même dossier temporaire sur le serveur. Si les noms
originaux sont conservés dans `/tmp`, lancer depuis SSH :

```bash
sudo -v && python3 /tmp/diagnose_twitch_websocket.py --docker
```

Le lanceur exige `twitch_websocket.py` à côté de sa copie SSH. Il utilise toujours
l’image exacte d’`overlays-app`, même si elle ne contient pas encore le correctif.
Cela teste la correction sans reconstruire l’image ni modifier le conteneur de
production. Après collecte, supprimer les deux copies temporaires du serveur.

**Suite :** faire approuver une livraison contrôlée, puis relever la RAM et les
descripteurs au démarrage et après des reconnexions Twitch. Une baisse immédiate
après redémarrage ne prouverait pas à elle seule l’efficacité du correctif :
il faut vérifier l’absence de nouvelle accumulation. Le parcours réel AutoBot/TLS
reste aussi à confirmer. Aucun correctif n’a été livré en production ; tout
redémarrage ou déploiement du service nécessite un accord distinct.

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

- [x] Recueillir le contexte déclaré et les avertissements Twitch agrégés :
  voir les relevés de production ci-dessus.
- [ ] Consulter la courbe mémoire Beszel : croissance régulière, marches,
  pics liés à l’activité ou plateau ? Noter les horaires de corrélation.
- [x] Relever le tag d’image et les versions Python/TwitchIO/Uvicorn déployées,
  sans afficher de configuration secrète.
- [x] Confirmer la version d’aiohttp en production.
- [ ] Vérifier le code embarqué.
- [x] Distinguer mémoire anonyme du processus, cache et buffers du noyau ; ne
  pas confondre la mémoire anonyme avec les seuls objets du tas Python.
- [x] Confirmer un processus Uvicorn avec six threads.

**Résultat attendu :** contexte d’activité, version réellement examinée et nature
de la mémoire mesurée. Cela ne prouve pas encore quelle allocation est retenue.

Ne pas redémarrer avant collecte : cela ferait perdre l’état utile au diagnostic.
Les relevés passifs déjà fournis ne valent pas autorisation de modifier ou
profiler la production. Ce WI n’autorise pas de nouvelle intervention serveur ;
aucune procédure de profilage en production n’a été validée.

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

- [x] Faire approuver et exécuter une comparaison locale avec transport
  simulé : voir H4. Aucun fichier de test/script créé.
- [x] Faire approuver une reproduction avec transport réel local et un script
  dédié, sans accès Twitch ni données réelles.
- [x] Recueillir les résultats du conteneur jetable : voir le protocole H4.
- [x] Mesurer passivement les descripteurs et sockets du processus Uvicorn.
- [x] Relever la limite de descripteurs et compter les connexions établies vers 443.
- [x] Comparer les destinations IPv4 aux adresses résolues pour EventSub.
- [ ] Apparier les sockets aux descripteurs du PID 1 par inode, si nécessaire.
- [ ] Obtenir un accord distinct avant création de fichiers de tests/scripts,
  instrumentation, installation d’outils ou intervention en production.
- [ ] Relier l’évolution mémoire à une famille d’objets ou de tâches, plutôt
  qu’à la seule durée de fonctionnement.
- [x] Faire approuver et implémenter un correctif local borné avec son diagnostic.
- [x] Effectuer les contrôles locaux avec transport simulé et lanceur Docker simulé.
- [x] Recueillir la comparaison TCP réelle avant/après dans le conteneur jetable.
- [ ] Faire approuver une livraison et son suivi RAM/descripteurs en production.

Ne pas ajouter automatiquement de pool SQL, mise à jour de dépendance, worker,
redémarrage périodique ou limite mémoire Docker : ce sont des décisions
séparées, pas des conclusions du diagnostic.

## Critère de fin

Le diagnostic est terminé lorsqu’une cause est étayée par des mesures ou une
reproduction ciblée, ou qu’une hypothèse est explicitement écartée avec ses
preuves. Consigner les observations et les incertitudes restantes ici, puis
faire approuver le correctif séparément.

Le périmètre a été étendu sur accord explicite à un **correctif local borné**
et à son diagnostic comparatif. Le déploiement, le redémarrage du service, le
profilage et une campagne de charge en production restent hors de ce périmètre.
