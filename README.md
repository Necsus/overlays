# NecsusDevOverlays

Plateforme d’overlays Twitch pour OBS, pilotés depuis le chat et administrés par streamer. Le giveaway (inscriptions, tirages manuels ou chronométrés) est disponible ; le plugin Chat est en préparation.

## Développement local

Prérequis : Python 3.11+ et accès au PostgreSQL 18 du Geekom depuis le LAN, sous Windows ou macOS. L’instance centrale contient `overlays` (production) et `overlays_dev` (développement), avec des rôles distincts. Le LAN exige TLS vérifié : récupérer uniquement le certificat public CA du Geekom sur chaque poste, puis renseigner `PSQL_SSLROOTCERT` dans son `.env` local avec un chemin absolu vers ce fichier existant. La connexion locale exige `PSQL_SSLMODE=verify-full` (également la valeur par défaut). Les modes `prefer`, `require` et `verify-ca` sont refusés. Seule la connexion release existante `postgres` / `overlays` / `overlays_release` conserve explicitement `disable` sur le réseau Docker privé ; sa migration TLS nécessite de livrer le CA au conteneur et un certificat serveur valable pour `postgres`. Le service central, la localisation du certificat public et les règles réseau sont décrits dans le [runbook PostgreSQL de `geekom`](https://github.com/Necsus/geekom/blob/main/docs/runbooks/postgresql.md) et son [architecture](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).

Les deux postes se connectent directement à `192.168.1.112:5432` : aucune clé SSH ni aucun tunnel ne sont nécessaires sur le LAN. Le certificat serveur identifie cette adresse ; ne pas la remplacer par `localhost`. Installer le CA hors du dépôt, par exemple dans `.postgresql` du dossier utilisateur :

| Poste | Exemple fictif de `PSQL_SSLROOTCERT` dans `.env` |
| --- | --- |
| Windows | `C:/Users/votre-compte/.postgresql/geekom-postgres-ca.crt` |
| macOS | `/Users/votre-compte/.postgresql/geekom-postgres-ca.crt` |

Utiliser des `/` pour le chemin Windows dans `.env`. Remplacer les chemins d’exemple par le chemin absolu réel ; `~` et `$HOME` ne sont pas développés par cette configuration. Ne jamais copier les clés privées de l’AC ou du serveur. Hors LAN, Tailscale seul ne donne pas accès au port PostgreSQL : un tunnel SSH compatible avec la vérification TLS reste à configurer et valider séparément.

### Préparer le poste

Windows (PowerShell, sans activation du venv ni changement de politique d’exécution) :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Configurer `.env` localement, sans le partager ni le copier entre les postes. Pour le développement, `PSQL_DB` et `PSQL_USER`/`PSQL_PASSWORD` doivent désigner le rôle de développement. Garder Twitch désactivé si la release utilise le même canal : deux bots pourraient traiter les mêmes événements.

### Vérifier puis lancer

Contrôler la connexion TLS et le schéma sans appliquer de migration :

```powershell
# Windows
.\.venv\Scripts\python.exe -m app.infrastructure.database --preflight
```

```bash
# macOS, venv activé
python -m app.infrastructure.database --preflight
```

Ce contrôle ne fait que des lectures et attend un schéma initialisé compatible. Une base vide peut être accessible mais échouer à ce contrôle. La commande sans `--preflight` applique les migrations : ne pas l’utiliser comme simple test de connexion. Si une initialisation ou migration est nécessaire, vérifier explicitement la cible de développement avant de la lancer.

Démarrer ensuite l’application :

```powershell
# Windows
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

```bash
# macOS, venv activé
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## Déploiement sur le Geekom

Un push sur `main` publie une image taguée par commit sur GHCR, puis la déploie sur le Geekom via GitHub Actions, Tailscale et Tailscale SSH. Les PR vers `main` construisent l’image sans la publier.

Le Nginx/Certbot commun et le vhost HTTPS Overlays sont en place. L’application est déployée sur PostgreSQL central ; le précontrôle, les migrations et les sondes de santé du workflow ont réussi. Les contrôles HTTPS récents renvoient 200 sur `/health` et `/`. Le parcours OAuth après le renforcement de sa liaison au navigateur, OBS/WebSocket et le renouvellement Certbot restent à valider. Voir [docs/DEPLOY.md](docs/DEPLOY.md), la [roadmap](docs/ROADMAP.md) et l’architecture du dépôt [geekom](https://github.com/Necsus/geekom/blob/main/docs/architecture.md).

Les données d’exécution persistent dans le volume `overlays_overlays_runtime`. Le schéma de la base centrale `overlays` est en version 2.

## Administration et OBS

- `/` : accueil et accès à l’application.
- `/admin` : connexion Twitch et gestion de l’overlay.
- `/health` : contrôle de santé du service.
- `/docs` : documentation OpenAPI.

Déclarer dans la console Twitch le callback exact configuré, généralement `https://overlays.necsus.dev/auth/twitch/callback`. Autoriser le compte bot via `/auth/twitch/bot/login`, puis le streamer dans `/admin`. Copier le lien généré du plugin Giveaway dans une source navigateur OBS ; ce lien contient une clé confidentielle. Sa rotation invalide l’ancien lien.

La déconnexion révoque la session courante côté serveur, sans invalider les liens
OBS ni les sessions indépendantes. Les onglets partageant ce cookie sont tous
déconnectés. Les sessions sont en mémoire pour le mono-worker actuel : un
redémarrage impose une nouvelle connexion, y compris après cette mise à jour.
Un streamer dont l'accès est désactivé ne peut plus accéder à l'administration
ou à OBS ; une connexion Twitch ne le réactive pas automatiquement.

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
