# NecsusDevOverlays

Plateforme d’overlays Twitch pour OBS, pilotés depuis le chat et administrés par streamer. Le giveaway (inscriptions, tirages manuels ou chronométrés) est disponible ; le plugin Chat est en préparation.

## Développement local

Prérequis : Python 3.11+ et accès au PostgreSQL 18 du Geekom. La release utilise `overlays` ; le développement utilise la base distincte `overlays_dev`.

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

Un push sur `main` publie une image taguée par commit sur GHCR, puis déclenche le déploiement Debian/Compose via GitHub Actions, Tailscale et Tailscale SSH. La configuration requise et les étapes sont dans [docs/DEPLOY.md](docs/DEPLOY.md). Les PR vers `main` construisent l’image sans la publier.

La release et le développement ont des bases et des rôles PostgreSQL distincts. Les données persistent dans des volumes Docker ; le workflow ne les supprime pas. Le déploiement peut interrompre brièvement l’application pendant la migration. DNS et proxy HTTPS sont configurés séparément.

## Administration et OBS

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
