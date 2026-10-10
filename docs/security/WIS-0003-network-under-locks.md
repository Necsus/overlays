# WIS-0003 — Ne pas laisser le réseau retenir les verrous métier et d'accès

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** correctif applicatif implémenté et contrôlé localement ; validation
réelle restante. **Priorité :** P1.
**Sévérité initiale :** élevée, disponibilité potentiellement inter-streamer.
**Catégorie :** CWE-400, contention contrôlable par un client.
**Preuve initiale :** revue et blocages reproduits avec sockets fictives ; pas de mesure réseau réelle.

## Faille et preuve avant correctif

Les références ci-dessous décrivent l'audit initial de `41b94b9`, avant les correctifs.

Trois usages d'un verrou retiennent des attentes réseau :

1. Les mutations du giveaway attendent `_broadcast_state()` sous le verrou
   métier (`app/application/service.py:125-201`). Le gestionnaire envoie à
   chaque socket séquentiellement, sans délai applicatif
   (`app/web/websocket.py:26-41`). Un envoi suspendu retarde aussi les sockets
   suivantes, les commandes et le minuteur du même streamer.
2. Une rotation garde `database.access_lock` pendant
   `disconnect_streamer()` (`app/web/routes/admin.py:80-89`). Celui-ci attend
   chaque `websocket.close()` sans délai applicatif (`websocket.py:14-24`).
   Ce verrou est commun aux logins et authentifications OBS de **tous** les
   streamers, pas seulement au propriétaire de la rotation.
3. Le callback OAuth conserve ce même verrou pendant toute
   `complete_streamer_authorization()` (`app/web/routes/auth.py:183-184`),
   y compris la disponibilité et l'abonnement Twitch (`:220-225`). Le timeout
   de 10 s entoure seulement `wait_until_ready()`, pas `subscribe_to_streamer()`.
   Les limites éventuelles de la bibliothèque ne garantissent pas un budget
   court pour la section critique entière.

Contrôles locaux : une doublure bloquant `send_json()` empêche la livraison au
socket suivant ; une doublure bloquant `close()` sous le verrou partagé empêche
une seconde opération de l'acquérir. Les doublures ont ensuite été libérées.
Cela démontre la dépendance du code, **pas** un blocage infini garanti avec
Uvicorn réel : ses buffers et délais de fermeture peuvent limiter l'effet.

## Scénario et impact

Un détenteur d'une clé OBS valide ouvre un client lent puis provoque ou attend
une diffusion/rotation. Un streamer autorisé peut aussi répéter des connexions
OAuth pendant que Twitch est lent. Les opérations concernées attendent le
réseau au lieu de libérer leur verrou.

L'isolation des **données** reste correcte, mais pas celle de la **disponibilité** :
une chaîne peut retarder l'authentification et les rotations des autres. Une clé
OBS prévue pour la lecture peut donc influer sur le traitement métier.

## Correctif applicatif implémenté

Le fonctionnement et les budgets sont décrits dans
[l'architecture](../ARCHITECTURE.md#diffusion-et-verrous-réseau).

- `app/application/service.py` : publication synchrone de l'instantané validé,
  sans attendre les sockets sous le verrou métier, y compris après restauration
  et expiration. La cohérence SQL/mémoire reste inchangée.
- `app/web/websocket.py` : un émetteur par socket, file de capacité un avec
  remplacement de l'état en attente, envois et fermetures bornés, détachement
  synchrone et collecte des tâches. Les émetteurs en cours de nettoyage comptent
  encore dans le plafond global du WIS-0002.
- `app/web/routes/overlay.py` : l'état initial utilise la même file que les
  diffusions ; le budget de fermeture est partagé avec le gestionnaire.
- `app/web/routes/admin.py` : rotation SQL et détachement sous le verrou d'accès,
  puis fermeture des seuls sockets capturés hors verrou. Révocation également
  sur erreur/annulation de commit, sans exposer de nouvelle clé sur échec.
- `app/web/routes/auth.py` : seule la phase identité/contexte reste sous le
  verrou d'accès ; le budget Twitch couvre readiness **et** abonnement.
- `app/infrastructure/twitch.py` : verrou réutilisé par streamer pour la
  validation du token et l'abonnement, évitant une sérialisation réseau globale
  tout en préservant celle des callbacks d'un même propriétaire.
- `app/main.py` : arrêt des émetteurs dans le lifespan, après les minuteurs.

Les instantanés complets permettent de sauter des états intermédiaires, pas de
réordonner ceux envoyés. Il n'y a pas de tâche créée par publication. La révocation
empêche toute nouvelle publication vers le socket retiré, mais ne peut rappeler
les données déjà envoyées aux buffers du transport. Les verrous protégeant les
transactions SQL et la course vérification/rotation sont conservés.

Aucune dépendance, migration, configuration de production ou proxy modifié.
Aucun fichier de test/script créé, aucun secret lu, aucun déploiement effectué.

## Contrôles locaux effectués

**85 contrôles ponctuels ont réussi** : 62 contrôles de base, puis 23 contrôles
complémentaires de nettoyage et de non-régression WIS-0002, avec données fictives
et doublures de framework, sockets, SQL et Twitch, sans accès à un service réel.
Le moteur de Giveaway est exécuté directement ; les définitions du service, du gestionnaire,
des routes et du bot sont exécutées avec imports de remplacement. Les délais
sont raccourcis dans la simulation, sans modifier les valeurs du code source.
L'échéance utilise une horloge fictive pour éviter un essai prolongé.

- [x] Envoi de A bloqué : socket sain de A et publications de B encore livrés.
- [x] Commandes, inscriptions, tirages distincts, arrêt et minuteur progressent
  sans attendre cet envoi ; unicité des participants et rechargement après erreur
  de persistance conservés.
- [x] Instantanés détachés du moteur ; publications rapides coalescées dans l'ordre,
  un seul écrivain par socket, aucune tâche supplémentaire par publication.
- [x] Détachement immédiat avant fermeture lente ; B continue à s'authentifier
  pendant la fermeture des anciens sockets de A.
- [x] Authentification concurrente avec l'ancienne clé refusée après rotation ;
  nouvelle clé utilisable, nouvelle connexion de A non fermée par le lot précédent.
- [x] Erreur SQL et annulation après commit simulé : détachement conservé, verrou
  libéré et réponse d'erreur/annulation sans succès de rotation.
- [x] Timeouts/erreurs d'envoi et de fermeture nettoyés ; plafond global maintenu
  même pendant une fermeture lente ; capacité récupérée après terminaison.
- [x] Fermetures d'un lot parallèles, collecte des émetteurs à l'arrêt, aucune
  tâche émettrice restante à la fin des contrôles. Registre nettoyé même lorsque
  les callbacks de terminaison sont encore différés ; un ancien callback ne
  peut pas supprimer un nouvel émetteur.
- [x] Compteurs de file équilibrés après coalescence, envoi, erreur et annulation ;
  états en attente retirés immédiatement au détachement.
- [x] Quotas, rejet avant SQL, délai d'authentification total et restriction de
  lecture seule du WIS-0002 conservés ; ordre état initial/diffusion contrôlé.
- [x] Twitch A bloqué : B s'abonne indépendamment et le verrou d'accès reste libre.
- [x] Callbacks du même streamer sérialisés sans double abonnement ; annulation
  libérant son verrou, réconciliation réutilisable après timeout.
- [x] Le timeout englobe readiness et abonnement ; session administrative encore
  créée malgré le timeout, contexte unique malgré les callbacks concurrents.
- [x] Syntaxe des sept modules modifiés, liens locaux de documentation et
  whitespace (`git diff --check`) contrôlés.

La revue de la source publique de TwitchIO 3.3.2
([client](https://github.com/PythonistaGuild/TwitchIO/blob/v3.3.2/twitchio/client.py)
et [tokens](https://github.com/PythonistaGuild/TwitchIO/blob/v3.3.2/twitchio/authentication/tokens.py))
complète ces simulations de concurrence ; elle n'exécute ni le client réel ni
l'écriture de son fichier d'authentification.

FastAPI/Starlette/TwitchIO/Psycopg sont absents du Python local : aucune intégration
ASGI/PostgreSQL, navigateur, OBS ou Twitch réelle exécutée. Les LSP Python
`ty`/`ruff` sont indisponibles ; les installer ou corriger leurs commandes dans
`pi-lsp.json` pour obtenir des diagnostics. Aucun outil installé.

## Critères de clôture restants — non exécutés

- [ ] Tester le backpressure et la fermeture avec le vrai transport ASGI/OBS :
  confirmer l'annulation dans les budgets définis, le code `1013` et la reconnexion.
- [ ] Observer commandes et minuteur de A, puis login/connexion/rotation de B,
  pendant un ralentissement contrôlé de A dans un environnement isolé.
- [ ] Rejouer la course rotation/authentification avec PostgreSQL réel, y compris
  erreurs/annulations et vérification du refus de la clé précédente après succès.
- [ ] Valider deux abonnements TwitchIO simultanés pour des streamers distincts,
  deux callbacks d'un même streamer et la reprise après timeout/révocation.
- [ ] Confirmer que la phase Twitch lente ne bloque pas les accès OBS/rotations et
  produit bien un statut de chat dégradé côté interface, sans secret dans les logs.
- [ ] Mesurer l'ordre visible, les files et les tâches lors de diffusions rapides,
  puis leur nettoyage à l'arrêt réel de l'application ; mesurer aussi les octets,
  puisque le nombre borné d'instantanés ne borne pas la taille d'un giveaway.

Les budgets dépendent de l'annulation coopérative des bibliothèques ; les contrôles
locaux ne prouvent ni cette coopération réelle ni une isolation contre toute
charge SQL/CPU. Ne pas clore sur la seule base des doublures, et ne pas faire
d'essai de ralentissement en production.
