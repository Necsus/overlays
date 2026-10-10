# WIS-0003 — Ne pas laisser le réseau retenir les verrous métier et d'accès

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** ouvert, aucun correctif. **Priorité :** P1.
**Sévérité :** élevée, disponibilité potentiellement inter-streamer.
**Catégorie :** CWE-400, contention contrôlable par un client.
**Preuve :** revue et blocages reproduits avec sockets fictives ; pas de mesure réseau réelle.

## Faille et preuve

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

## Correction proposée

- Retirer atomiquement les connexions révoquées du registre sous le verrou,
  puis fermer leurs transports hors section critique avec délais bornés.
- Ne pas attendre Twitch sous le verrou global d'accès ; distinguer les étapes
  d'identité/contexte et l'abonnement réseau, en préservant leur cohérence.
- Diffuser hors verrou métier depuis un instantané validé, avec stratégie
  bornée pour clients lents et maintien de l'ordre des états. Ne pas créer une
  tâche sans limite par événement/socket.
- Garder l'invariant important : aucune ancienne clé ne peut être enregistrée
  entre vérification et rotation. Un simple retrait de tous les verrous serait
  une régression de sécurité.

## Critères de clôture — non exécutés

- [ ] Client OBS lent de A n'empêche ni commandes/minuteur de A, ni login,
  connexion et rotation de B au-delà d'un budget explicite.
- [ ] Rotation de A révoque immédiatement l'enregistrement de ses sockets,
  même si leurs transports ne répondent pas à la fermeture.
- [ ] Clé précédente refusée lors d'une authentification concurrente à la rotation.
- [ ] Indisponibilité Twitch ne retient pas le verrou d'accès global.
- [ ] Ordre des états et capacité mémoire bornée lors de diffusions rapides.
- [ ] Scénarios validés avec sockets et Twitch simulés, puis transports réels en
  environnement isolé ; pas de test de ralentissement en production.
