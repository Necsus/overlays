# Déploiement sur le Geekom

Le déploiement de production utilise Debian, Docker Compose et GitHub Actions. Un push sur `main` construit l’image, la publie sur GHCR, puis la déploie sur le Geekom via Tailscale et Tailscale SSH. La procédure NixOS historique n’est plus la procédure active.

Le workflow est [`../.github/workflows/publish-ghcr.yml`](../.github/workflows/publish-ghcr.yml). Il suppose que le Geekom est déjà préparé : Debian, Docker avec le plugin Compose, Tailscale actif, Tailscale SSH configuré et compte `deploy` autorisé à utiliser Docker. Le compte doit pouvoir écrire dans `/home/deploy/apps/overlays` (ou le chemin configuré). Ne pas modifier SSH, Tailscale ou le pare-feu dans le cadre de ce guide.

## 1. Configurer GitHub Actions

Dans **Settings → Secrets and variables → Actions**, ajouter les éléments ci-dessous. Les valeurs d’exemple indiquent seulement le format ; les secrets se saisissent directement dans GitHub et ne doivent pas être copiés dans le dépôt ou les journaux.

### Variables

- `GEEKOM_APP_DIR` : chemin sous `/home/deploy/apps`, par exemple `/home/deploy/apps/overlays`.
- `GEEKOM_DEPLOY_USER` : `deploy`.
- `GEEKOM_TAILSCALE_HOST` : adresse IPv4 Tailscale du Geekom. Elle sert aussi à publier PostgreSQL sur Tailscale.
- `POSTGRES_ADMIN_USER` : rôle d’administration PostgreSQL, par exemple `overlays_admin`.
- `PSQL_DB`, `PSQL_USER` : base et rôle de release, par exemple `overlays` et `overlays_release`.
- `PSQL_DEV_DB`, `PSQL_DEV_USER` : base et rôle pour le poste de développement, par exemple `overlays_dev` pour les deux.
- `TWITCH_ENABLED`, `TWITCH_CLIENT_ID`, `TWITCH_BOT_ID`, `TWITCH_OWNER_ID`, `TWITCH_BOT_LOGIN`, `TWITCH_ADMIN_REDIRECT_URI`.
- `SESSION_COOKIE_SECURE`, `SESSION_MAX_AGE_SECONDS`, `TWITCH_COMMAND_PREFIX`.

### Secrets

- `TS_OAUTH_CLIENT_ID`, `TS_AUDIENCE` : identité Tailscale utilisée par l’action GitHub et configuration correspondante dans Tailscale.
- `TWITCH_CLIENT_SECRET`, `SESSION_SECRET`.
- `POSTGRES_ADMIN_PASSWORD`, `PSQL_PASSWORD` (release), `PSQL_DEV_PASSWORD` (développement).

Le `GITHUB_TOKEN` est fourni automatiquement à Actions. Le paquet GHCR doit être accessible au workflow de déploiement. Dans la politique Tailscale, autoriser le tag `tag:ci` à joindre le Geekom comme utilisateur `deploy` via Tailscale SSH.

Utiliser des rôles et mots de passe distincts pour l’administration PostgreSQL, la release et le développement. `PSQL_DEV_PASSWORD` doit correspondre au mot de passe du rôle de développement dans le `.env` du poste local. Garder les noms de bases, rôles et rôle admin stables une fois le volume PostgreSQL initialisé.

Pour Twitch, `TWITCH_ADMIN_REDIRECT_URI` doit correspondre exactement à l’URL déclarée dans la console Twitch, généralement `https://overlays.necsus.dev/auth/twitch/callback`. Ne pas activer Twitch en développement sur le même canal que la release.

## 2. Déclencher et suivre un déploiement

Une PR vers `main` lance seulement une construction de vérification. Le déploiement se déclenche après un push sur `main` ; modifier une variable ou un secret GitHub ne déclenche pas de workflow. Après une modification de configuration, lancer le workflow en poussant un changement autorisé sur `main`.

Le job de déploiement valide les paramètres, génère temporairement un `.env` protégé, rejoint le tailnet, puis transfère Compose et les fichiers nécessaires. La sonde `tailscale ssh` récupère la clé d’hôte annoncée par Tailscale ; SSH et SCP la vérifient strictement, sans désactiver le contrôle de clé. Sur le Geekom, le workflow démarre PostgreSQL, crée ou met à jour les rôles et bases, vérifie le garde-fou de migration, tire l’image du commit, applique la migration et démarre l’application. Il contrôle ensuite `/health` depuis le conteneur.

La configuration Twitch et le préfixe de commande persistés dans `settings.json` sont réécrits depuis les variables GitHub à chaque déploiement. Les valeurs modifiées depuis l’interface admin peuvent donc être remplacées. L’application est arrêtée pendant la migration : prévoir une brève interruption.

Consulter l’onglet **Actions** pour le résultat. Le workflow évite d’imprimer les valeurs secrètes et ne dump pas les journaux des conteneurs. En cas d’échec, partager le nom de l’étape et le message non sensible, jamais les fichiers `.env`, tokens ou logs contenant des secrets.

## 3. Données, réseau et limites

Les données PostgreSQL et la configuration d’exécution de l’application sont stockées dans des volumes Docker persistants. Le workflow ne fait pas `docker compose down -v` et ne supprime pas ces volumes. Le port PostgreSQL est publié sur l’adresse LAN prévue dans `compose.yaml` et sur l’adresse Tailscale ; il n’est pas publié sur Internet. L’application ne publie pas directement son port sur l’hôte.

Le contrôle `/health` est interne au conteneur : il ne valide ni le DNS, ni le proxy HTTPS, ni OAuth Twitch/OBS. La configuration du domaine et du proxy reste distincte du workflow. Après le déploiement, valider séparément l’accès HTTPS et, si nécessaire, le parcours Twitch/OBS.

Les bases `overlays` (release) et `overlays_dev` (développement) sont distinctes, avec des rôles séparés. Le contrôle de migration refuse le passage du schéma v1 si des giveaways existants seraient supprimés. Toute base préexistante mérite une sauvegarde vérifiée avant une migration.

Conserver les secrets uniquement dans GitHub et les environnements prévus. Les administrateurs du démon Docker sur le Geekom peuvent accéder aux variables d’environnement des conteneurs. Pour sauvegardes et restauration, voir [ADR-0011](adr/0011-exploitation-durable.md) et le [README](../README.md).
