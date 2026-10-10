# NecsusDevOverlays

Plateforme d’overlays Twitch pour OBS, pilotés depuis le chat et administrés par streamer. Le giveaway (inscriptions, tirages manuels ou chronométrés) est disponible ; le plugin Chat est en préparation.

## Développement local

Prérequis : Python 3.11+ et accès au PostgreSQL 18 du Geekom depuis le LAN. L’instance centrale contient `overlays` (production) et `overlays_dev` (développement), avec des rôles distincts. Le LAN exige TLS vérifié : récupérer le certificat public CA du Geekom, puis renseigner `PSQL_SSLROOTCERT` dans le `.env` local avec son chemin. La connexion locale utilise `PSQL_SSLMODE=verify-full`. Le service central et les règles réseau sont décrits dans le [runbook PostgreSQL de `geekom`](https://github.com/Necsus/geekom/blob/main/docs/runbooks/postgresql.md) et son [architecture](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
# Configurer .env localement ; ne pas partager les secrets.
python -m app.infrastructure.database
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Pour le développement, `PSQL_DB` et `PSQL_USER`/`PSQL_PASSWORD` doivent désigner le rôle de développement. Garder Twitch désactivé si la release utilise le même canal : deux bots pourraient traiter les mêmes événements.

## Déploiement sur le Geekom

Un push sur `main` publie une image taguée par commit sur GHCR, puis la déploie sur le Geekom via GitHub Actions, Tailscale et Tailscale SSH. Les PR vers `main` construisent l’image sans la publier.

Le Nginx/Certbot commun et le vhost HTTPS Overlays sont en place. PostgreSQL central et l’accès pgAdmin depuis le Mac via TLS sont en service. Les changements locaux du workflow et du Compose connectent l’application à cette instance sans provisionner PostgreSQL ; ils attendent publication et déploiement. L’application est actuellement arrêtée. Après le déploiement, valider `/health`, `/admin`, OAuth Twitch, OBS/WebSocket et l’accès HTTPS depuis l’extérieur. Voir [docs/DEPLOY.md](docs/DEPLOY.md), la [roadmap](docs/ROADMAP.md) et l’architecture du dépôt [geekom](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).

Les données d’exécution persistent dans le volume `overlays_overlays_runtime`. Le schéma de la base centrale `overlays` est en version 2.

## Administration et OBS

- `/` : accueil et accès à l’application.
- `/admin` : connexion Twitch et gestion de l’overlay.
- `/health` : contrôle de santé du service.
- `/docs` : documentation OpenAPI.

Déclarer dans la console Twitch le callback exact configuré, généralement `https://overlays.necsus.dev/auth/twitch/callback`. Autoriser le compte bot via `/auth/twitch/bot/login`, puis le streamer dans `/admin`. Copier le lien généré du plugin Giveaway dans une source navigateur OBS ; ce lien contient une clé confidentielle. Sa rotation invalide l’ancien lien.

Commandes par défaut :

| Commande | Accès | Fonction |
| --- | --- | --- |
| `!galot <lot>` | Streamer | Définit le lot |
| `!gastart [secondes]` | Streamer | Ouvre les inscriptions, durée facultative (1 à 604800 s) |
| `!join` | Viewer | S’inscrit une fois |
| `!gapull` | Streamer | Ferme les inscriptions et tire un gagnant inédit |
| `!gastop` | Streamer | Termine le giveaway |

Le préfixe est configurable dans l’administration. L’échéance et les résultats sont persistés ; un tirage automatique a lieu à l’expiration si des participants sont inscrits.

## Sécurité et données

Ne jamais versionner, afficher ou partager `.env`, `.tio.tokens.json` ou une clé OBS. `.env.example` est le modèle partageable. PostgreSQL contient les identités, giveaways, participants, gagnants et empreintes des clés OBS ; les tokens Twitch restent hors de la base.

Les sauvegardes PostgreSQL doivent être conservées hors du dépôt et leur restauration vérifiée vers une autre base vide. La procédure et les contrôles restant à valider figurent dans [ADR-0011](docs/adr/0011-exploitation-durable.md).

## Documentation

- [Déploiement Geekom](docs/DEPLOY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Licence MIT](LICENSE)
