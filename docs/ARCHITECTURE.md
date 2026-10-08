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

La configuration du dépôt cible Debian et Docker Compose. GitHub Actions
construit l’image sur les PR, puis publie et déploie les commits de `main`
via GHCR et Tailscale SSH. Le workflow applique les migrations avant de
démarrer l’application ; son contrôle `/health` est interne au conteneur.

L’entrée web Nginx/Certbot est implémentée dans les fichiers de configuration,
mais n’est pas encore déployée ni validée sur le Geekom :

```text
Internet → IPv4 publique fixe / routeur TCP 80 et 443
         → Nginx sur 192.168.1.112 → app:8000 → db:5432
```

- `nginx-bootstrap` (profil `bootstrap`) sert uniquement le challenge ACME
  HTTP-01 ; les autres chemins répondent 404.
- `nginx` (profil `https`) termine TLS, redirige HTTP vers HTTPS hors challenge
  ACME et relaie HTTP/WebSocket vers `app` sur le réseau `app_egress`.
  La résolution DNS Docker est renouvelée pour suivre les recréations de l’app.
- L’application ne publie aucun port hôte. PostgreSQL reste sur le réseau
  `backend` interne ; les ports LAN/Tailscale déclarés ne sont pas effectifs
  dans l’état observé sur le Geekom.
- Certbot est prévu sur l’hôte Debian. Nginx monte `/etc/letsencrypt` en lecture
  seule et le webroot ACME est partagé via `acme-webroot`. Un drop-in systemd
  préparé dans `ops/` recharge Nginx après un renouvellement réussi.

Les deux profils Nginx ne doivent pas tourner simultanément : ils partagent
le port 80. Le workflow transfère leurs configurations et tente de démarrer
HTTPS si le certificat est détecté ; la vérification faite sous `deploy` peut
être bloquée par les permissions root de Certbot. Procédure, limites et
validations attendues : [DEPLOY.md](DEPLOY.md).

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
`HttpOnly`, `SameSite=Lax`, sécurisé en HTTPS. Les états OAuth sont courts et à
usage unique. Les tokens OAuth restent côté serveur, hors des tables métier. Chaque message
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

## Routes et protocole OBS

| Route | Fonction |
| --- | --- |
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
