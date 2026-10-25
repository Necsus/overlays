# NecsusDevOverlays

Plateforme d’overlays Twitch pour OBS, pilotés depuis le chat et administrés par streamer. Le giveaway (inscriptions, tirages manuels ou chronométrés) est disponible ; le plugin Chat est en préparation.

## Développement local

Prérequis : Python 3.11+, Windows ou macOS et accès LAN au PostgreSQL 18 du Geekom. Utiliser la base `overlays_dev` et son rôle dédié, jamais les identifiants de production.

La connexion LAN utilise `192.168.1.112:5432` avec `PSQL_SSLMODE=verify-full`. Récupérer uniquement le certificat public CA selon le [runbook PostgreSQL de `geekom`](https://github.com/Necsus/geekom/blob/main/docs/runbooks/postgresql.md), puis renseigner `PSQL_SSLROOTCERT` dans le `.env` local. Ne pas remplacer l’adresse par `localhost` : le certificat identifie l’IP LAN. Aucun tunnel SSH n’est nécessaire sur ce réseau. Installer le CA hors du dépôt :

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

Un push sur `main` publie et déploie l’image via GitHub Actions ; une PR construit seulement l’image. Configuration, effets du déploiement et procédures : [docs/DEPLOY.md](docs/DEPLOY.md).

## Administration et OBS

- `/` : accueil et accès à l’application.
- `/admin` : connexion Twitch et gestion de l’overlay.
- `/health` : contrôle de santé du service.
- `/docs` : documentation OpenAPI.

Déclarer dans la console Twitch le callback exact configuré, généralement `https://overlays.necsus.dev/auth/twitch/callback`. Autoriser le compte bot via `/auth/twitch/bot/login`, puis le streamer dans `/admin`. Copier le lien généré du plugin Giveaway dans une source navigateur OBS ; ce lien contient une clé confidentielle. Sa rotation invalide l’ancien lien.

La déconnexion révoque la session courante côté serveur, sans invalider les liens
OBS ni les sessions indépendantes. Les onglets partageant ce cookie sont tous
déconnectés. Un redémarrage impose une nouvelle connexion.
Un streamer dont l'accès est désactivé ne peut plus accéder à l'administration
ou à OBS ; une connexion Twitch ne le réactive pas automatiquement.

Un WebSocket OBS est fermé après six heures sans nouvel état Giveaway envoyé.
Les ping/pong réseau ne prolongent pas ce délai. L’overlay est alors effacé et
ne se reconnecte pas automatiquement : rafraîchir la source navigateur OBS
pour reprendre, même si un giveaway est encore ouvert. Les reconnexions après
une coupure réseau restent automatiques.

Commandes par défaut :

| Commande | Accès | Fonction |
| --- | --- | --- |
| `!galot <lot>` | Streamer | Définit le lot |
| `!gastart [secondes]` | Streamer | Ouvre les inscriptions, durée facultative (1 à 604800 s) |
| `!join` | Viewer | S’inscrit une fois |
| `!gapull` | Streamer | Ferme les inscriptions et tire un gagnant inédit |
| `!gastop` | Streamer | Termine le giveaway |

Le préfixe est configurable dans l’administration. L’échéance et les résultats sont persistés ; un tirage automatique a lieu à l’expiration si des participants sont inscrits.

L’aperçu CSS utilise des données fictives et ne modifie pas le giveaway réel. Le CSS n’est ni sauvegardé ni envoyé à OBS : le copier dans le champ **CSS personnalisé** de la source navigateur. Les ressources externes ne sont pas chargées dans l’aperçu. Le plugin Chat et la suppression de compte ne sont pas encore disponibles.

## Sécurité et données

Ne jamais versionner, afficher ou partager `.env`, `.tio.tokens.json` ou une clé OBS. `.env.example` est le modèle partageable. PostgreSQL contient les identités, giveaways, participants, gagnants et empreintes des clés OBS ; les tokens Twitch restent hors de la base.

Les sauvegardes PostgreSQL doivent être conservées hors du dépôt et leur restauration vérifiée vers une autre base vide. La procédure reste à définir et valider : voir [ADR-0011](docs/adr/0011-exploitation-durable.md).

## Documentation

- [Déploiement Geekom](docs/DEPLOY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Licence MIT](LICENSE)
