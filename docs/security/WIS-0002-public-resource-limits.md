# WIS-0002 — Borner le coût des entrées publiques

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** correctif applicatif implémenté et contrôlé localement ; validation
réelle et protection transport restantes. **Priorité :** P1.
**Sévérité initiale :** élevée par impact potentiel sur tous les streamers.
**Catégorie :** CWE-400 / CWE-770, épuisement de ressources.
**Preuve initiale :** code et contrôles locaux bornés ; seuil de saturation non mesuré.

## Faille et preuve avant correctif

Les références ci-dessous décrivent l'audit initial de `41b94b9`, avant les correctifs.

- `/auth/twitch/login` et `/auth/twitch/bot/login` sont publics
  (`app/web/routes/auth.py:37-75`). Chaque appel ajoute un state dans un
  dictionnaire sans plafond (`app/application/oauth_state.py:18-28`).
- Chaque émission parcourt les states pour purger les expirés (`:45-53`).
  L'expiration à 600 s réduit la durée de conservation, pas le nombre possible
  de states dans cette fenêtre ni le coût du parcours répété.
- Le WebSocket est accepté avant authentification, puis chaque token non vide
  déclenche une recherche SQL (`app/web/routes/overlay.py:30-67`). Le délai de
  cinq secondes borne seulement la réception du premier message, pas l'attente
  du verrou ni la résolution SQL suivante.
- `parse_overlay_authentication` ne valide pas longueur/format du token
  (`app/application/overlay_access.py:22-43`) ; il n'y a pas de quota de
  connexions en attente ou par propriétaire dans le gestionnaire.
- Chaque transaction ouvre une connexion SQL (`app/infrastructure/database.py:110-137`).
  Le vhost fourni ne définit pas de limites de débit/connexions
  (`nginx/https/default.conf`).

Contrôles réalisés : 128 states simultanés acceptés et token fictif de 8 Kio
accepté. Aucun flood réseau ni mesure mémoire/SQL effectué. Les bornes de
transport éventuelles d'Uvicorn/Nginx ne sont pas des budgets applicatifs ; leur
configuration réelle et une protection amont éventuelle restent inconnues.

## Scénario et impact

Sans compte Twitch ni clé OBS valide, un client peut multiplier les requêtes de
login et les handshakes OBS avec tokens invalides, accumulant states, tâches et
recherches SQL sérialisées sous le verrou global. Un propriétaire légitime peut
aussi multiplier ses sockets authentifiées.

L'effet potentiel est une dégradation mémoire/CPU/SQL et le retard des logins,
rotations et connexions des autres streamers. Aucun accès à leurs données n'est
établi. Le volume suffisant pour provoquer une panne n'a pas été testé.

## Correctif applicatif implémenté

Les seuils, réponses et limites de fonctionnement sont décrits une seule fois
dans [l'architecture](../ARCHITECTURE.md#protection-des-entrées-publiques).

Fichiers modifiés :

- `app/application/public_limits.py` : nouveau compteur à fenêtre fixe,
  thread-safe et de taille bornée, sans dépendance ajoutée.
- `app/application/oauth_state.py` et `app/web/routes/auth.py` : plafond des
  states, purge ordonnée et budgets globaux/par IP communs aux deux flux ; refus
  HTTP sans nouvelle transaction ni cookie, sans éviction d'un state légitime.
- `app/application/overlay_access.py` : validation stricte de la longueur et de
  l'encodage du token avant calcul d'empreinte et recherche SQL.
- `app/web/websocket.py` et `app/web/routes/overlay.py` : quotas avant acceptation,
  authentifications en cours bornées globalement et par IP, connexions bornées
  globalement et par propriétaire, message initial limité avant décodage JSON,
  délai d'authentification total et libération systématique des places.

Les tokens déjà générés par l'application restent compatibles. L'enregistrement
reste sérialisé avec la rotation des clés : aucune suppression du verrou de
sécurité. La liaison navigateur du WIS-0001 et le routage par propriétaire sont
préservés. Un socket en lecture seule ne peut plus envoyer de messages
applicatifs supplémentaires après son authentification.

Aucun pool, migration, script ou fichier de test créé ; aucun secret, manifeste,
proxy ou configuration de production modifié. Aucun déploiement effectué.
La fermeture des handshakes refusés est bornée et déplacée hors du verrou.
Le correctif complémentaire des rotations/diffusions est documenté dans
[WIS-0003](WIS-0003-network-under-locks.md).

## Contrôles locaux effectués

**75 contrôles ponctuels ont réussi** (65 contrôles de base, puis 10 sur la limite
supplémentaire par IP des authentifications simultanées). Ils utilisent des
données fictives, sans accès réseau/SQL ni lecture de secrets. Modules autonomes
exécutés directement ; définitions des routes/gestionnaire exécutées avec
doublures de FastAPI, sockets et SQL. Les attentes de deadline ont été raccourcies
à 30 ms dans la simulation, en vérifiant que le code garde cinq secondes.

- [x] Plafond OAuth par défaut atteint avec 512 states ; refus sans éviction,
  récupération à consommation/expiration et admissions concurrentes bornées.
- [x] Budgets globaux et par IP, mémoire des compteurs bornée même sous refus
  répétés, renouvellement de fenêtre et admissions concurrentes contrôlés.
- [x] Refus des deux logins en `429` avec en-têtes attendus ; aucune confiance
  accordée au `X-Forwarded-For` fourni directement par le client.
- [x] Liaison navigateur, usage unique et flux bot/streamer indépendants conservés.
- [x] Tokens générés compatibles ; tokens absents, trop grands, mal formés ou non
  canoniques et messages invalides rejetés avant SQL, sans données OBS.
- [x] Délai simulé couvrant acceptation, réception, verrou et SQL ; annulation
  libérant le verrou et les quotas, erreur SQL et fermeture lente contrôlées.
- [x] Limites de handshakes et sockets, récupération après déconnexion/annulation,
  nettoyage même après erreur inattendue d'envoi initial.
- [x] B encore utilisable lorsque A atteint une limite locale ; fermeture ciblée
  et diffusion de A ne touchent pas B dans les simulations avec capacité globale.
- [x] Syntaxe des six modules Python et absence d'erreurs de whitespace contrôlées.

Aucun test de charge, FastAPI/ASGI réel, PostgreSQL, navigateur ou OBS réalisé :
les dépendances correspondantes sont absentes du Python local. LSP indisponible
(`ty`/`ruff` à installer ou reconfigurer dans `pi-lsp.json`) ; aucun outil installé.
Ces contrôles ne mesurent pas la capacité réelle ni le comportement du pilote SQL
pendant une annulation.

## Critères de clôture restants — non exécutés

- [ ] Vérifier refus HTTP/WebSocket et remise en service après quota avec les vraies
  réponses ASGI, sans données ni secret dans les réponses de refus.
- [ ] Confirmer reconstruction de l'IP par le proxy réellement installé ; tester
  des en-têtes forgés et plusieurs utilisateurs derrière une IP/NAT partagée.
- [ ] Confirmer réception SQL annulée dans le budget prévu et fermeture de la
  connexion avec le pilote réel, sur une base de test isolée.
- [ ] Valider plusieurs sources OBS, reconnexions normales et deux streamers ;
  ajuster les seuils initiaux si l'usage légitime l'exige, sans les désactiver.
- [ ] Examiner les limites de taille de trame et de connexions du serveur/proxy :
  le plafond applicatif du texte intervient après son assemblage par ASGI.
  Toute modification de configuration de production nécessite un accord séparé.
- [ ] Faire une validation sous charge bornée en environnement isolé : mémoire,
  latence et disponibilité des clients légitimes. Aucun essai de flood en production.

Les budgets sont par processus, pas une protection DDoS distribuée. Un budget
global saturé peut encore refuser un client légitime ; les seuils par IP protègent
contre la monopolisation locale, pas contre un réseau d'attaquants. Ne pas clore
ce WIS sur la seule base des simulations.
