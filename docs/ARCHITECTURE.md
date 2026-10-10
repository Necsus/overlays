# NecsusDevOverlays — Architecture

Ce document décrit **l'implémentation actuelle**. Les évolutions sont dans la
[roadmap](ROADMAP.md), l'installation et les commandes dans le
[README](../README.md).

## Structure et flux

Python, FastAPI, TwitchIO 3/EventSub, PostgreSQL via Psycopg 3 asynchrone et
frontend HTML/JavaScript natif. Le schéma PostgreSQL version 2 supporte plusieurs streamers. Le
parcours giveaway Twitch → OBS, y compris le minuteur, est validé. Les
contrôles SQL isolés, les clés OBS, les coupures SQL et les sauvegardes
restent dans [ADR-0011](adr/0011-exploitation-durable.md).

```text
Chat Twitch → bot global → broadcaster_id → contexte streamer → commandes/Giveaway + PostgreSQL
                                                └── WebSocket réservé au propriétaire → OBS
/admin → OAuth Twitch → identité de session → contexte et abonnement EventSub du streamer
```

| Répertoire | Responsabilité |
| --- | --- |
| `app/main.py` | Assemblage FastAPI et cycle de vie des composants |
| `app/core/` | Configuration et environnement |
| `app/domain/` | Règles du giveaway, indépendantes des transports |
| `app/application/` | Commandes, permissions, orchestration et minuteur |
| `app/infrastructure/` | PostgreSQL, stockage et intégration Twitch |
| `app/web/` | Routes, WebSockets et assets administratifs/plugins |

Le service est la source de vérité. Chaque streamer possède un moteur, un
service, un verrou asynchrone et un minuteur ; OBS affiche les données mais ne
choisit jamais les gagnants.

## Déploiement et entrée web

La production utilise Debian, Docker Compose et GitHub Actions, qui construit
l’image sur les PR et publie/déploie `main` via GHCR et Tailscale SSH. Nginx et
Certbot sont gérés sur l’hôte par le dépôt `geekom`; le vhost HTTPS Overlays est
en place. L’application est déployée sur PostgreSQL central. Les contrôles HTTPS
récents renvoient 200 sur `/health` et `/`; OAuth Twitch après le renforcement
navigateur, OBS/WebSocket et le renouvellement Certbot restent à valider.

```text
Internet → IPv4 publique fixe / routeur TCP 80 et 443
         → Nginx de l’hôte → 127.0.0.1:8000 → app:8000 → geekom-postgres:5432
```

- Le Compose applicatif ne contient que `app`, qui rejoint le réseau externe
  interne `geekom_postgres_clients` créé par Geekom. Le Nginx hôte possède les
  ports 80/443 ; aucun proxy applicatif Docker ni montage de clés privées n’est
  nécessaire.
- `app` publie `127.0.0.1:8000:8000` et communique avec PostgreSQL sur le réseau
  Docker interne. Le port PostgreSQL est publié uniquement sur
  `192.168.1.112:5432` pour l’accès LAN TLS ; aucun binding Tailscale ou transfert
  Freebox n’est configuré.
- PostgreSQL central héberge les bases `overlays` et `overlays_dev` avec des
  rôles distincts. L’application et ses migrations restent gérées par ce dépôt ;
  le workflow ne crée ni base ni rôle. L’accès LAN TLS est vérifié depuis pgAdmin.
  Voir le [runbook PostgreSQL](https://github.com/Necsus/geekom/blob/main/docs/runbooks/postgresql.md)
  et l’[architecture du dépôt `geekom`](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).
- `nginx/https/default.conf` est le vhost du Nginx hôte. Il déclare le domaine,
  les chemins du certificat Overlays et l’upstream loopback ; il inclut le
  snippet HTTP-01 commun. Il redirige HTTP vers HTTPS hors challenge et relaie
  HTTP/WebSocket, avec une variable Upgrade et une zone TLS propres à Overlays.
- Nginx remplace les en-têtes proxy clients. Uvicorn reçoit
  `FORWARDED_ALLOW_IPS` depuis `OVERLAYS_PROXY_IP` : uniquement la passerelle
  `app_egress`, observée à `172.18.0.1`, plutôt qu’un wildcard. Cela permet de
  reconstruire les URL HTTPS et WebSocket derrière la publication Docker.
- Avant d’arrêter l’application, la CI vérifie cette adresse sur le réseau
  effectif. Le workflow vérifie aussi l’accès à la base par le rôle applicatif
  et refuse une base de production sans historique de migrations. Après le
  démarrage, il contrôle la santé dans le conteneur et sur le port loopback de
  l’hôte. Il livre le vhost mais ne touche pas au Nginx hôte ni à Certbot ;
  l’installation/rechargement du vhost reste manuel.
- Le script distant arrive sur STDIN via `bash -s`. Les commandes applicatives
  `run` et `exec` sont non interactives, pour préserver le flux du script. Sans
  cette précaution, une commande ponctuelle peut absorber la suite du script
  et produire un job vert sans démarrer l’application.

Le socle commun gère indépendamment le webroot, les certificats et le
renouvellement/rechargement. Les workflows réutilisables restent à définir.
Le déploiement centralisé et les sondes de santé sont validés ; les contrôles
HTTPS `/health` et `/` renvoient 200. OAuth Twitch après renforcement, OBS/WebSocket
et le dry-run Certbot avec le vhost TLS restent à valider. Procédure et détails :
[DEPLOY.md](DEPLOY.md).

## Giveaway et échéance

```text
HIDDEN → WAITING → OPEN → WINNER
   ↑        │        │       │
   └────────┴─ arrêt ┴───────┘
```

Les participants sont conservés dans une liste ; l'unicité est vérifiée en
mémoire et garantie en SQL. Le tirage utilise `secrets.choice` parmi les
participants n'ayant pas encore gagné. Les gagnants sont ordonnés et persistés.

Une durée d'inscription définit `closes_at`, échéance UTC persistée. La tâche
automatique et les commandes prennent le même verrou. Chaque inscription vérifie
aussi l'échéance avant admission. À expiration : tirage vers `WINNER`, ou
archivage `CANCELLED` puis `HIDDEN` sans participant.

Le minuteur reprend à la restauration et est annulé proprement à l'arrêt du
service. Les mutations du moteur sont publiées en mémoire après le commit SQL.
En cas d'erreur ou d'annulation pendant une écriture, le service recharge l'état
persistant avant la prochaine mutation : une connexion perdue pendant le commit
ne prouve pas son échec. Le minuteur réessaie après une seconde, mais recharge
d'abord la base pour éviter de refaire un tirage déjà validé. Tant que ce
rechargement échoue, aucune nouvelle mutation n'est autorisée.

## Données et configuration

| Stockage | Contenu |
| --- | --- |
| `.env` | Secrets et bootstrap, modèle partageable dans `.env.example` uniquement |
| `data/settings.json` | Configuration globale non secrète, validée avec Pydantic et écrite atomiquement |
| `.tio.tokens.json` | Tokens OAuth gérés par TwitchIO ; ne jamais lire, afficher ou partager |
| PostgreSQL | Identités, giveaways propriétaires, préférences, historique et empreintes des clés OBS |

Tables principales :

- `streamers` : identité Twitch stable, profil et indicateur d'activité ;
  plusieurs streamers peuvent être activés simultanément.
- `streamer_preferences` : préfixe de commandes propre à chaque streamer.
- `giveaways` : lot, statut, dates, échéance et propriétaire ; un seul giveaway
  actif par streamer.
- `participants` : unicité `(giveaway_id, twitch_user_id)`.
- `winners` : gagnants uniques par giveaway et ordre de tirage unique.
- `overlay_access_keys` : clé composée `(streamer_id, plugin_slug)`, empreinte
  unique et dates de rotation.

L'arrêt archive en `COMPLETED` après un tirage, sinon en `CANCELLED`. Le
démarrage restaure l'état actif, les participants, les gagnants et l'échéance ;
les lectures de restauration utilisent une transaction `REPEATABLE READ`. Les
dates SQL sont des `TIMESTAMPTZ` en UTC, l'activité du streamer un `BOOLEAN`, et
`participants.id` une identité générée. Les réponses web conservent leurs dates
ISO 8601.

`Database` ouvre une connexion asynchrone par transaction, sans pool ni
connexion partagée. Chaque opération valide ou annule sa transaction et ferme sa
connexion, y compris après une lecture. Les délais de connexion, de requête et
d'attente de verrou sont bornés ; les erreurs du pilote sont remplacées par un
message sans données de connexion ni valeurs SQL.

Les migrations versionnées sont définies dans `app/infrastructure/database.py`
et appliquées explicitement sous verrou PostgreSQL. La version 2 supprime les
giveaways existants (données de test), ajoute leur propriétaire et autorise
plusieurs streamers actifs. Une nouvelle exécution ne rejoue pas les versions
enregistrées ; l'application contrôle la version au démarrage. Les commandes sont dans le
[README](../README.md#développement-local).

Un verrou applicatif commun sérialise les changements d'identité et de clés avec
l'authentification/enregistrement des WebSockets, pour ne pas laisser un accès
s'enregistrer entre une vérification et une révocation. Il est distinct du
verrou métier du giveaway.

## Authentification et isolation

Trois identités distinctes : application Twitch (Client ID/Secret), compte bot
global et streamers autorisés par OAuth. Les commandes de gestion utilisent
l'identifiant stable du broadcaster et de l'auteur, jamais le nom affiché ni un
identifiant fourni par le navigateur.

La session administrative est signée, expirante et portée par un cookie
`HttpOnly`, `SameSite=Lax`, sécurisé en HTTPS. Chaque transaction OAuth possède
un state et un secret navigateur indépendants, valables dix minutes. Le secret
est dans un cookie `HttpOnly`, `SameSite=Lax`, sans Domain et avec Path `/` ;
son nom est propre au state pour préserver les connexions en onglets parallèles.
En HTTPS, ou si `SESSION_COOKIE_SECURE` est activé, il est `Secure` avec le
préfixe `__Host-`, empêchant son injection par un sous-domaine. Le HTTP local
avec cette option désactivée utilise un cookie sans ce préfixe.
Le callback vérifie la liaison avant tout échange du code ou effet métier ;
un mauvais navigateur ne consomme pas le state légitime. La consommation valide
est atomique et à usage unique. Le cookie consommé est supprimé après succès,
annulation ou erreur HTTP gérée ; un flux abandonné expire. Ces cookies ne
remplacent pas la session administrative et leur secret n'est pas envoyé à Twitch.
Le redémarrage invalide les transactions en mémoire : une connexion en cours
doit alors être relancée. Les contrôles locaux sont décrits dans
[WIS-0001](security/WIS-0001-oauth-browser-binding.md) ; les validations réelles
navigateur/Twitch restent à faire.
Les tokens OAuth restent côté serveur, hors des tables métier. Chaque message
EventSub est routé par broadcaster ; la révocation d'un abonnement retire
uniquement ce streamer du routage des commandes. Son minuteur, ses données et
ses connexions OBS en lecture restent indépendants.
Toute personne ayant accès au réseau peut tenter de se connecter : ce n'est pas
une isolation SaaS multi-client.

Une clé OBS donne uniquement un accès de lecture au plugin ciblé, indépendamment
de la session web. Elle possède 256 bits d'entropie et seule son empreinte
SHA-256 est persistée. Le plugin et le propriétaire de la clé sont vérifiés
avant diffusion ; chaque événement est routé vers son contexte. Sa valeur en clair n'est retournée qu'à la génération, avec
`Cache-Control: no-store`.

Le gestionnaire associe les connexions au streamer et ne sert que Giveaway.
Les clés OBS sont composées par streamer et plugin ; rotations et diffusions ne
concernent que le propriétaire correspondant.

## Protection des entrées publiques

Les budgets sont en mémoire **par processus**, pour le déploiement mono-worker
actuel. Ils ne sont pas partagés entre plusieurs workers ou instances. Les
limites initiales sont définies dans `app/application/oauth_state.py` et
`app/web/websocket.py`, avec un compteur commun dans
`app/application/public_limits.py` ; aucune variable d'environnement supplémentaire
n'est nécessaire.

| Ressource | Limite initiale |
| --- | --- |
| Transactions OAuth en attente, bot et streamer réunis | 512 |
| Créations de transactions OAuth | 60 par fenêtre, dont 10 par IP |
| Authentifications OBS simultanées | 32, dont 8 par IP |
| Tentatives de connexion OBS | 120 par fenêtre, dont 30 par IP |
| Connexions OBS authentifiées | 256 au total, dont 8 par streamer |

Les fenêtres de débit sont fixes, de 60 secondes, et autorisent un nouveau
budget à leur renouvellement : ce n'est pas une fenêtre glissante. Les compteurs
ne conservent que les IP admises et leur nombre est borné par le budget global.
Les IP viennent de `request.client` / `websocket.client`, reconstruits par
Uvicorn selon la confiance proxy prévue ; les en-têtes clients ne sont pas lus
directement. L'absence d'IP utilise un groupe commun `unknown`. Une IP partagée
(NAT) partage les quotas ; des clients distribués peuvent encore épuiser le
budget global. La confiance proxy effective et les seuils restent à valider.

OAuth refuse une nouvelle transaction avec HTTP `429`, `Retry-After: 60` et
`Cache-Control: no-store`, sans ajouter de cookie ni évincer un state existant.
Les callbacks déjà émis restent consommables malgré cette saturation. La purge
s'appuie sur l'ordre d'expiration, sans parcourir systématiquement les states
encore valides.

OBS réserve une place avant acceptation. Le premier message texte est limité à
512 caractères avant décodage JSON ; le token doit être l'encodage base64url
canonique de 32 octets (43 caractères), sinon aucun accès SQL n'est effectué.
Le délai total de cinq secondes couvre acceptation, réception, attente du verrou
et recherche SQL. La libération des places est garantie par `finally`, y compris
sur erreur ou annulation. Les fermetures des authentifications refusées se font
hors verrou d'accès avec le budget commun décrit dans la section suivante.

Une saturation OBS demande une fermeture `1013` après acceptation ; avant
acceptation, Starlette/Uvicorn renvoient normalement un refus HTTP `403`, à
confirmer avec le transport réel. Un message applicatif envoyé après
l'authentification ferme la connexion avec `1008` : OBS est en lecture seule,
les ping/pong du protocole WebSocket restent gérés par le transport.

La limite de 512 caractères intervient **après assemblage du message par ASGI**.
Elle ne réduit pas à elle seule les buffers de trames du serveur ni les connexions
réseau en amont. La validation transport, SQL réel et reconnexion multi-source
reste dans [WIS-0002](security/WIS-0002-public-resource-limits.md), sans test
réalisé sur la production ni modification du proxy dans cette étape.

## Diffusion et verrous réseau

Le service capture un instantané détaché du moteur après validation SQL, sous
son verrou métier, puis le publie **sans attente réseau**. Le gestionnaire possède
un émetteur asynchrone par socket enregistré et une file de capacité un. Quand
elle est pleine, l'état en attente est remplacé par le dernier instantané validé.
Les états intermédiaires peuvent être sautés ; les états effectivement envoyés
restent ordonnés et contiennent toujours l'état complet, dont les gagnants
ordonnés. L'état initial passe par ce même émetteur : aucun second écrivain ne
peut le livrer après une diffusion plus récente.

Chaque envoi dispose d'une seconde. Un client lent ou défaillant est retiré du
registre avant une fermeture `1013`. Les fermetures disposent également d'une
seconde et s'exécutent en parallèle pour un lot de sockets, hors des verrous
métier/d'accès. Le plafond global compte les émetteurs jusqu'à leur terminaison,
y compris pendant leur nettoyage, pour éviter une accumulation de tâches.
Chaque émetteur retient au plus un état courant et un état en attente ; cette
borne porte sur le nombre d'instantanés, pas leur taille en octets. Le lifespan
arrête les minuteurs puis annule et collecte les émetteurs à la fermeture.

Une rotation conserve le verrou d'accès pendant le changement SQL de clé et
le détachement synchrone des sockets concernés, qui supprime leurs files et
annule leurs émetteurs. Elle ferme ensuite uniquement les transports capturés,
hors verrou ; une nouvelle connexion du propriétaire n'est pas incluse dans
cette liste. Le détachement a lieu même si le commit échoue ou est annulé,
puisque son résultat peut être incertain. La vérification et l'enregistrement
OBS restent sous ce même verrou : une ancienne clé ne passe pas une rotation
réussie. Les données déjà confiées aux buffers réseau ne peuvent pas être
rappelées ; l'annulation empêche de poursuivre les publications applicatives.

OAuth garde la persistance de l'identité et la création/réutilisation du contexte
sous le verrou d'accès, mais attend Twitch **après sa libération**. La phase
`wait_until_ready` + abonnement, y compris validation du token et réconciliation,
partage un budget de dix secondes ; ce n'est pas un délai total pour tout OAuth.
Un timeout ou un échec contrôlé EventSub (conduit absent, abonnement non confirmé,
réponse invalide) n'empêche pas la session administrative ; sans abonnement connu
prêt, le chat reste dégradé. Ces échecs utilisent `TwitchSubscriptionError`, sans
absorber les bugs inattendus ni les erreurs de persistance de l'identité.
Les abonnements utilisent un verrou par identifiant de
streamer, réutilisé pour son contexte, plutôt qu'un verrou réseau commun à toutes
les chaînes. Les opérations d'un même streamer restent sérialisées, sans retenir
celles d'un autre.

Ces délais reposent sur l'annulation coopérative du transport. Leur efficacité
réelle, les reconnexions OBS et le comportement TwitchIO restent à confirmer dans
[WIS-0003](security/WIS-0003-network-under-locks.md). Les attentes SQL nécessaires
à la cohérence restent sous les verrous ; aucune modification du proxy, des
migrations ou du déploiement n'accompagne ce correctif.

## Routes et protocole OBS

| Route | Fonction |
| --- | --- |
| `/` | Page d’accueil publique avec accès à l’application |
| `/admin`, `/api/admin/session` | Interface et état administratif |
| `/auth/twitch/login`, `/auth/twitch/bot/login` | OAuth streamer et bot |
| `/auth/twitch/callback`, `/auth/logout` | Retour OAuth et déconnexion |
| `/api/admin/plugins/giveaway/overlay-access` | État de la clé, sans sa valeur |
| `/api/admin/plugins/giveaway/overlay-access/rotate` | Rotation authentifiée par `POST` |
| `/api/admin/plugins/giveaway/history` | Historique paginé du streamer connecté |
| `/api/admin/plugins/giveaway/history/{id}` | Détail propriétaire avec participants et gagnants |
| `/api/admin/plugins/giveaway/preferences` | Préfixe de commandes par streamer |
| `/plugins/giveaway/overlay`, `/plugins/giveaway/static` | Page et assets OBS |
| `/plugins/giveaway/ws` | WebSocket authentifié |
| `/health` | Réponse du service, pas une disponibilité complète |

La clé est placée dans le fragment de l'URL, absent de la requête HTTP initiale.
Le navigateur l'envoie comme premier message WebSocket :

```json
{"type": "overlay.authenticate", "token": "clé-fictive"}
```

Sans authentification valide sous cinq secondes, la connexion ferme avec `1008`,
sans données. Une rotation ferme uniquement les connexions du streamer
propriétaire. Les pages et scripts seuls ne contiennent aucune donnée
métier.

L'état initial et les diffusions ont la même enveloppe :

```json
{
  "type": "giveaway.state",
  "data": {
    "state": "OPEN",
    "giveaway_id": "identifiant-fictif",
    "lot": "Clavier",
    "closes_at": null,
    "participant_count": 42,
    "winners": []
  }
}
```

`closes_at` vaut une date ISO 8601 ou `null`. Un gagnant contient
`twitch_user_id` et `display_name`. `overlay_snapshot()` exclut la liste des
participants ; `snapshot()` conserve l'instantané complet interne. Le compteur
OBS est calculé localement (`Math.ceil`), sans diffusion chaque seconde : le
premier tick peut afficher `durée + 1` sans allonger l'échéance serveur. Les
textes utilisent `textContent`.

Les assets administratifs et ceux du plugin ont des montages distincts. Les
anciennes routes `/overlay`, `/api/state` et `/ws/overlay` ne sont plus
disponibles.

## Administration et aperçus

`/admin` sépare le compte et la connexion Twitch des espaces de plugins. Une
navigation locale par fragments d’URL sélectionne une seule vue à la fois :
`#account`, `#giveaway` et `#chat`. Les anciens fragments Giveaway reviennent
sur sa page unique. Les boutons
précédent/suivant du navigateur sont pris en charge ; les vues restent dans le
DOM afin de conserver le brouillon CSS lors d’un changement d’espace. Le lien
vers le compte dans la barre latérale affiche l’avatar, le nom et le login Twitch
de la session, avec une icône de repli si l’avatar est absent ou ne charge pas.
La zone d’actions du compte comprend la déconnexion et un bouton de suppression
ouvrant une confirmation frontend uniquement. La confirmation finale est
désactivée : aucun endpoint de suppression n’est appelé et aucune donnée n’est
effacée.

Giveaway regroupe l’aperçu et les actions OBS sur une page. Les boutons de copie
et de génération/régénération sont à droite du titre, sans texte visible dessous.
Générer/Régénérer précède Copier. Copier est rouge et désactivé quand la copie
est indisponible, neutre pendant le chargement, et vert quand un lien est
copiable. Les retours d’action restent accessibles aux lecteurs d’écran ; une
infobulle décrit l’état du bouton. La régénération conserve sa confirmation
d’invalidation. Si le presse-papiers échoue, un champ sélectionné apparaît pour
une copie manuelle.

Le lien généré est conservé dans `sessionStorage` avec l’identité Twitch stable
et sa date de rotation. Au rechargement, le frontend vérifie l’identité, le
format de l’URL et la rotation courante via l’API avant d’activer Copier. Une
rotation différente, une déconnexion ou un autre compte supprime la copie locale.
Un stockage navigateur bloqué laisse la copie disponible dans la page courante
uniquement. L’absence de copie locale ne signifie pas que le lien OBS est révoqué.

Le POST de génération renvoie aussi `rotated_at`, issu de l’écriture qui a créé
le lien, pour éviter de l’associer à une rotation concurrente. La base conserve
uniquement l’empreinte du token. Le secret stocké dans l’onglet est accessible au
JavaScript de l’origine ; ce stockage n’est pas une protection contre une XSS.
Les restaurations ou duplications d’onglets peuvent conserver ce stockage selon
le navigateur. Aucun `localStorage`, cookie ou journal ne reçoit le lien.
Les préférences Giveaway (préfixe) et l'historique paginé avec détail des
participants et gagnants sont présentés dans l'administration. L'entrée Chat est
uniquement une présentation « prévu » :
aucun aperçu, accès OBS ou appel d’API Chat n’est implémenté. Ajouter un plugin
implique sa navigation et ses vues propres, sans framework de plugins générique.

L’aperçu Giveaway utilise les données fictives et le renderer commun dans une
iframe `sandbox="allow-scripts"`, sans origine partagée avec l’administration.
Son viewport reste à 900 × 500 pixels ; un conteneur défilant l’accueille sur les
petits écrans sans changer les dimensions de rendu. La navigation ne reconstruit
pas l’iframe ; appliquer du CSS ou changer de scénario reconstruit son `srcdoc`.
Le CSS n’est ni persisté ni envoyé à OBS. La CSP bloque les ressources externes.

La structure HTML, les références DOM et la navigation ont fait l’objet de
contrôles ponctuels, dont une simulation DOM. Le rendu responsive et les
interactions réelles dans le navigateur restent à valider après cette refonte.

## Limites connues

- Une connexion et un commit par inscription : l'accès SQL est asynchrone, mais
  son coût reste à mesurer avant de décider d'un pool.
- Les diffusions WebSocket sont séquentielles et attendues sous verrou métier ;
  un client lent peut retarder les commandes.
- La recherche des doublons parcourt la liste des participants.
- Après une écriture incertaine, OBS peut afficher le dernier état connu
  jusqu'au rechargement ; les scénarios de coupure PostgreSQL et de changement
  d'identité restent à valider réellement.
- Supervision TwitchIO, reconnexion progressive et contrôle `ready` sont
  incomplets.
- Aucun test de charge du parcours complet ne garantit actuellement une capacité
  pour 10 000 spectateurs ; les anciens essais HTTP simples ne la démontrent
  pas.

Les contrôles restent ponctuels et manuels, sans suite de tests ajoutée. Les
validations SQL isolées, clés OBS, coupures SQL et sauvegardes restent dans
[ADR-0011](adr/0011-exploitation-durable.md).
