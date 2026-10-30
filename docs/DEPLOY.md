# Déploiement sur le Geekom

Ce guide couvre l’application sur Debian/Docker. Le socle PostgreSQL,
Nginx/Certbot et réseau appartient au dépôt
[`geekom`](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).
Ne pas modifier SSH, Tailscale ou le pare-feu pour contourner un échec applicatif.

## État et points à confirmer

L’application est déployée sur PostgreSQL central, schéma v2. Nginx, le certificat
et le vhost HTTPS sont en place. Le déploiement Actions et les sondes internes,
loopback et HTTPS `/health` et `/` ont réussi. L’accès PostgreSQL LAN avec TLS
vérifié est validé.

Le durcissement anti-scan du vhost est versionné ; son installation, son
activation et ses contrôles sur l’hôte restent à effectuer.

Cela ne valide pas les parcours OAuth/OBS ni le renouvellement du certificat
avec ce vhost. Les vérifications restantes sont suivies dans la
[index des WI](INDEX.md), les sauvegardes dans
[WI-0011](todo/WI-0011-exploitation-durable.md).

## Prérequis de l’hôte

- Docker Engine 28+ et plugin Compose, Python 3, Nginx/Certbot communs.
- Tailscale SSH opérationnel ; compte `deploy` autorisé à utiliser Docker et à
  écrire dans le répertoire applicatif, par défaut `/home/deploy/apps/overlays`.
- PostgreSQL central provisionné, base et rôle applicatifs distincts de la dev,
  réseau Docker `geekom_postgres_clients` disponible.
- Port loopback `8000` réservé à Overlays ; seuls TCP 80/443 sont publics pour
  le web. Ne pas publier le port applicatif ou PostgreSQL sur Internet.

## Configuration GitHub Actions

Dans **Settings → Secrets and variables → Actions** :

| Variables | Valeur ou rôle |
| --- | --- |
| `GEEKOM_APP_DIR` | Chemin sous `/home/deploy/apps`, par exemple `/home/deploy/apps/overlays` |
| `GEEKOM_DEPLOY_USER` | `deploy` |
| `GEEKOM_TAILSCALE_HOST` | IPv4 Tailscale du Geekom |
| `OVERLAYS_PROXY_IP` | Passerelle Docker `app_egress`, défaut `172.18.0.1` |
| `PSQL_DB`, `PSQL_USER` | Base et rôle de production provisionnés côté Geekom |
| `TWITCH_ENABLED`, `TWITCH_CLIENT_ID`, `TWITCH_BOT_ID`, `TWITCH_OWNER_ID`, `TWITCH_BOT_LOGIN`, `TWITCH_ADMIN_REDIRECT_URI` | Configuration Twitch de production |
| `SESSION_COOKIE_SECURE`, `SESSION_MAX_AGE_SECONDS`, `TWITCH_COMMAND_PREFIX` | Session et commandes ; utiliser `SESSION_COOKIE_SECURE=true` en HTTPS |

| Secrets | Rôle |
| --- | --- |
| `TS_OAUTH_CLIENT_ID`, `TS_AUDIENCE` | Identité et configuration de l’action Tailscale |
| `TWITCH_CLIENT_SECRET`, `SESSION_SECRET` | Secrets Twitch et session |
| `PSQL_PASSWORD` | Mot de passe du rôle de production, différent de celui de la dev |

`GITHUB_TOKEN` est fourni par Actions ; le paquet GHCR doit être accessible au
workflow. La politique Tailscale doit permettre à `tag:ci` de joindre le Geekom
comme `deploy` via Tailscale SSH.

`OVERLAYS_PROXY_IP` doit correspondre à la passerelle effective du réseau
`app_egress`. Si elle change, actualiser la variable : ne jamais élargir la
confiance à `*` ou à un sous-réseau pour obtenir des liens HTTPS.

Le callback Twitch doit correspondre exactement à celui de la console Twitch,
généralement `https://overlays.necsus.dev/auth/twitch/callback`.

## Déclenchement et effets du déploiement

Une PR vers `main` construit l’image sans la publier. Un push sur `main` lance
[le workflow de publication et déploiement](../.github/workflows/publish-ghcr.yml).
Modifier une variable ou un secret GitHub ne le déclenche pas.

Le [Dockerfile](../Dockerfile) utilise un tag glissant : il suit les correctifs
Python 3.13 et les reconstructions officielles sur Debian 13 (`trixie`), sans
changer automatiquement de version mineure Python ou de version majeure Debian.
Les deux workflows construisent avec `docker build --pull` pour récupérer la
base publiée à jour. Une image déjà construite ou un conteneur démarré ne se met
pas à jour tout seul : appliquer une nouvelle base nécessite une nouvelle
construction puis un déploiement autorisé.

Points à connaître avant un déploiement autorisé :

- Une brève interruption est prévue pendant migrations et mise à jour.
- La CI utilise le rôle applicatif, sans créer de base ni de rôle PostgreSQL.
- La configuration globale `settings.json` est réécrite depuis les variables
  GitHub ; des changements administratifs peuvent donc être remplacés.
- Le volume `overlays_overlays_runtime` persiste. La base centrale a son propre
  cycle de sauvegarde, indépendant du conteneur applicatif.
- Le vhost est livré dans `$GEEKOM_APP_DIR/nginx/https/default.conf`, mais son
  installation et son rechargement sur l’hôte restent manuels.
- Le script distant utilise STDIN via `bash -s` : conserver les commandes
  `compose run`/`exec` non interactives lors d’une modification du workflow.

Consulter **Actions** pour le résultat. En cas d’échec, partager l’étape et le
message non sensible, pas les fichiers de configuration ou les tokens. Ne pas
afficher `docker compose config` ni les environnements des conteneurs : ils
contiennent des secrets. Les administrateurs Docker ont accès à ces secrets.

## Maintenance du vhost HTTPS

Le vhost est déjà installé : ne pas rejouer une première installation ni créer
un second lien dans `sites-enabled`. La CI livre le fichier sans l’activer : un
redémarrage ou déploiement du conteneur ne suffit pas à appliquer les
[protections Nginx](ARCHITECTURE.md#protection-des-entrées-publiques).

Conserver le fichier complet : le `map` et le `limit_req_zone` sont au niveau
`http`, comme l’inclusion Debian habituelle de `sites-enabled`, pas à l’intérieur
d’un bloc `server`. Leurs noms sont réservés à Overlays ; ne pas les recopier
dans un second fichier actif.

Le quota utilise l’IP vue par Nginx. Dans le schéma actuel, Nginx reçoit directement
les clients. Si un proxy Cloudflare ou un autre intermédiaire est activé,
confirmer d’abord une restitution fiable de l’IP réelle sur l’hôte : sinon le
quota s’appliquerait aux IP du proxy et pénaliserait plusieurs utilisateurs.
Ne jamais faire confiance à un `X-Forwarded-For` arbitraire. Les utilisateurs
derrière un même NAT partagent aussi le quota.

Après un changement autorisé, examiner le diff avec la version active puis
installer le fichier livré. Adapter le chemin si `GEEKOM_APP_DIR` diffère :

```bash
sudo install -o root -g root -m 0644 \
  /home/deploy/apps/overlays/nginx/https/default.conf \
  /etc/nginx/sites-available/overlays
sudo /usr/sbin/nginx -t
```

**Seulement si le test réussit**, recharger :

```bash
sudo systemctl reload nginx
```

Si le test échoue, ne pas recharger ni modifier les permissions des clés ;
corriger ou rétablir le fichier précédent. Garder le vhost commun
`acme-bootstrap` et le snippet `/etc/nginx/snippets/acme-challenge.conf` : ils
servent aussi aux autres applications. Aucun conteneur ne doit reprendre les
ports 80/443 du Nginx hôte.

Le timer Certbot et le hook de rechargement sont communs, gérés par `geekom`.
Ne pas ajouter de surcharge par application. TCP 80 doit rester accessible pour
HTTP-01. Si le proxy Cloudflare est activé, utiliser **Full (strict)** avec un
certificat d’origine valide ; distinguer sa validation de celle en DNS-only.

## Vérifications manuelles

Ces commandes sont des procédures à lancer avec accord, pas des contrôles
exécutés lors d’une modification de documentation.

Sur le Geekom, vérifier l’application publiée :

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
```

Depuis un réseau extérieur au LAN, vérifier HTTPS sans contourner TLS :

```bash
curl --fail --silent --show-error https://overlays.necsus.dev/health
```

Attendre HTTP 200 et `{"status":"ok"}`. Le premier contrôle ne prouve pas que
Nginx ou Internet fonctionne ; le second ne prouve pas les parcours métier.
Un échec uniquement depuis le LAN peut venir du NAT loopback du routeur.

Vérifier séparément `/admin`, le callback OAuth et une source OBS avec son
WebSocket authentifié. Les liens générés doivent être en `https://`. Ne partager
aucun token ou lien OBS confidentiel.

### Filtrage et limitation Nginx

Après installation, test de syntaxe et rechargement autorisés :

- Vérifier `/`, `/admin`, les ressources statiques et `/health` en HTTPS, puis
  une connexion OAuth complète et une source OBS authentifiée. Vérifier aussi
  une reconnexion OBS et la réception d’un nouvel état après ouverture du socket.
- Vérifier que les chemins fictifs `/.env`, `/production/.env`, `/.env.bak`,
  `/.git/HEAD`, `/.tio.tokens.json`, `/phpinfo.php` et `/index.php/test` répondent
  `404`. Utiliser des requêtes `HEAD` sans conserver ni afficher de corps.
  Un `404` seul ne prouve pas le filtrage par Nginx : confirmer la version du
  vhost actif et l’absence de ces sondes dans les requêtes reçues par l’application.
- Sur un environnement isolé, vérifier que les rafales au-delà du budget défini
  dans le vhost sont refusées en `429`, puis que les requêtes reprennent après
  récupération du budget. Ne pas lancer de test de charge en production ni sur
  le callback OAuth. Les messages d’un WebSocket déjà ouvert ne sont pas comptés.

Ces contrôles restent à effectuer sur Nginx et dans les vrais parcours ; une
relecture des règles ne vaut pas validation du déploiement.

### Renouvellement du certificat

Pour éprouver le renouvellement et son hook avec le vhost TLS actif :

```bash
sudo certbot renew --cert-name overlays.necsus.dev --dry-run --run-deploy-hooks
```

Contrôler ensuite le certificat réellement servi. Un dry-run réussi ne prouve
pas à lui seul que le vhost présente le bon certificat.
