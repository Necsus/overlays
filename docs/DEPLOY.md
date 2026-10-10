# Déploiement sur le Geekom

Le déploiement de production utilise Debian, Docker Compose et GitHub Actions. Un push sur `main` construit l’image, la publie sur GHCR, puis la déploie sur le Geekom via Tailscale et Tailscale SSH.

## État et points à confirmer

- **PostgreSQL central** : service en bonne santé, bases `overlays` et `overlays_dev` et rôles distincts provisionnés. L’accès pgAdmin depuis le LAN avec TLS et vérification du certificat est validé. Le schéma de production est en version 2.
- **Application** : déployée sur PostgreSQL central. Le précontrôle en lecture seule et les migrations ont réussi ; les sondes internes et loopback du workflow sont passées.
- **Réseau web** : Nginx/Certbot, le webroot HTTP-01 commun, le certificat Overlays et le vhost HTTPS sont en place. Les contrôles HTTPS récents renvoient 200 sur `/health` et `/`. Le parcours OAuth après le renforcement de sa liaison au navigateur, OBS/WebSocket et le renouvellement Certbot avec le vhost TLS actif restent à valider. La source de vérité du socle hôte est le dépôt `geekom`.
- **Contrôles** : build PR et déploiement GitHub Actions réussis. Syntaxe YAML/Bash/Python, rendu Compose avec valeurs fictives, `git diff --check` et liens Markdown des documents modifiés ont été vérifiés. Aucun test OAuth Twitch réel ni test OBS/WebSocket n’a été effectué.

Le workflow de déploiement n’administre pas PostgreSQL : il utilise le réseau central, vérifie la connexion avec le rôle applicatif et exécute les migrations de schéma Overlays. Le provisioning, l’accès LAN et les opérations PostgreSQL relèvent du dépôt et des runbooks Geekom. Un workflow vert ne valide pas à lui seul les parcours externes ni OBS/WebSocket.

Le workflow est [`../.github/workflows/publish-ghcr.yml`](../.github/workflows/publish-ghcr.yml). Il suppose que le Geekom est déjà préparé : Debian, Docker Engine 28 ou supérieur avec le plugin Compose, Nginx/Certbot communs, Python 3 sur l’hôte (fourni par Certbot Debian), Tailscale actif, Tailscale SSH configuré et compte `deploy` autorisé à utiliser Docker. Le compte doit pouvoir écrire dans `/home/deploy/apps/overlays` (ou le chemin configuré). Ne pas modifier SSH, Tailscale ou le pare-feu dans le cadre de ce guide.

## 1. Configurer GitHub Actions

Dans **Settings → Secrets and variables → Actions**, ajouter les éléments ci-dessous. Les valeurs d’exemple indiquent seulement le format ; les secrets se saisissent directement dans GitHub et ne doivent pas être copiés dans le dépôt ou les journaux.

### Variables

- `GEEKOM_APP_DIR` : chemin sous `/home/deploy/apps`, par exemple `/home/deploy/apps/overlays`.
- `GEEKOM_DEPLOY_USER` : `deploy`.
- `GEEKOM_TAILSCALE_HOST` : adresse IPv4 Tailscale du Geekom, utilisée par le runner pour Tailscale SSH.
- `OVERLAYS_PROXY_IP` : facultative, IPv4 de la passerelle Docker `app_egress` par laquelle Nginx atteint Uvicorn. Valeur par défaut vérifiée sur le Geekom : `172.18.0.1`. La CI refuse un wildcard, un CIDR ou une adresse différente des passerelles de ce réseau. Si le réseau est recréé avec une autre passerelle, actualiser cette variable avant le prochain déploiement ; ne pas élargir la confiance à `*`.
- `PSQL_DB`, `PSQL_USER` : base et rôle applicatif de production, provisionnés depuis Geekom (par exemple `overlays` et `overlays_release`). L’hôte Compose est le nom interne `postgres` ; l’application ne reçoit aucun identifiant admin ni rôle de développement.
- `TWITCH_ENABLED`, `TWITCH_CLIENT_ID`, `TWITCH_BOT_ID`, `TWITCH_OWNER_ID`, `TWITCH_BOT_LOGIN`, `TWITCH_ADMIN_REDIRECT_URI`.
- `SESSION_COOKIE_SECURE`, `SESSION_MAX_AGE_SECONDS`, `TWITCH_COMMAND_PREFIX`.

### Secrets

- `TS_OAUTH_CLIENT_ID`, `TS_AUDIENCE` : identité Tailscale utilisée par l’action GitHub et configuration correspondante dans Tailscale.
- `TWITCH_CLIENT_SECRET`, `SESSION_SECRET`.
- `PSQL_PASSWORD` : mot de passe du rôle applicatif de production, provisionné depuis Geekom. Le `.env` local utilise aussi le nom `PSQL_PASSWORD`, mais avec la valeur distincte du rôle `overlays_dev`.

Le `GITHUB_TOKEN` est fourni automatiquement à Actions. Le paquet GHCR doit être accessible au workflow de déploiement. Dans la politique Tailscale, autoriser le tag `tag:ci` à joindre le Geekom comme utilisateur `deploy` via Tailscale SSH.

Utiliser un rôle et un mot de passe distincts pour chaque application/environnement ; le compte admin reste uniquement côté Geekom. Les noms `PSQL_DB` et `PSQL_USER` doivent correspondre à la base et au rôle provisionnés sur l’instance centrale. Ne jamais saisir de mot de passe dans cette documentation ou les journaux.

Pour Twitch, `TWITCH_ADMIN_REDIRECT_URI` doit correspondre exactement à l’URL déclarée dans la console Twitch, généralement `https://overlays.necsus.dev/auth/twitch/callback`. Ne pas activer Twitch en développement sur le même canal que la release.

## 2. Déclencher et suivre un déploiement

Une PR vers `main` lance seulement une construction de vérification. Le déploiement se déclenche après un push sur `main` ; modifier une variable ou un secret GitHub ne déclenche pas de workflow. Après une modification de configuration, lancer le workflow en poussant un changement autorisé sur `main`.

Le job valide les paramètres, génère temporairement un `.env` protégé contenant uniquement les identifiants de connexion applicatifs, rejoint le tailnet, puis transfère Compose et le vhost applicatif Nginx. La sonde `tailscale ssh` récupère la clé d’hôte annoncée par Tailscale ; SSH et SCP la vérifient strictement. Le workflow ne démarre pas PostgreSQL et ne crée ni base ni rôle : il rejoint `geekom_postgres_clients`, vérifie la connexion et le garde-fou via le rôle applicatif, applique les migrations de schéma Overlays puis démarre `app`. Le workflow contrôle `/health` dans le conteneur et sur `127.0.0.1:8000`. L’instance et son provisionnement relèvent exclusivement du dépôt et des opérations Geekom.

Le script distant est transmis par l’entrée standard à `bash -s`. Les commandes ponctuelles `compose run` et le contrôle `compose exec` de santé sont non interactifs pour préserver ce flux. La version locale n’effectue aucun `exec` PostgreSQL, heredoc SQL ou bootstrap d’administration ; la création des bases/rôles est opérée depuis Geekom.

Le workflow ne lit plus les certificats et ne démarre ni ne recharge Nginx. Il dépose le vhost dans `$GEEKOM_APP_DIR/nginx/https/default.conf` ; son installation dans `/etc/nginx` reste manuelle. Les changements ultérieurs de ce fichier ne sont donc pas appliqués au proxy par un simple déploiement applicatif.

La configuration Twitch et le préfixe de commande persistés dans `settings.json` sont réécrits depuis les variables GitHub à chaque déploiement. Les valeurs modifiées depuis l’interface admin peuvent donc être remplacées. Le déploiement arrête l’application pendant la mise à jour : prévoir une brève interruption.

Consulter l’onglet **Actions** pour le résultat. Le workflow évite d’imprimer les valeurs secrètes et ne dump pas les journaux des conteneurs. En cas d’échec, partager le nom de l’étape et le message non sensible, jamais les fichiers `.env`, tokens ou logs contenant des secrets.

## 3. Accès HTTPS depuis Internet

### Contrat applicatif et prérequis

Le fichier [`nginx/https/default.conf`](../nginx/https/default.conf) est maintenant un **vhost du Nginx hôte**, pas une configuration de conteneur. Il porte les domaines, les chemins de certificat et l’upstream de cette application :

- domaine et certificat : `overlays.necsus.dev` ;
- upstream : `127.0.0.1:8000`, publié par Compose ; réserver ce port à Overlays ;
- challenge : inclusion de `/etc/nginx/snippets/acme-challenge.conf`, avec webroot commun `/var/www/acme` ;
- certificats privés : uniquement sur l’hôte, jamais montés dans les conteneurs applicatifs ;
- variables WebSocket et zone de cache TLS propres à Overlays, pour cohabiter avec les autres vhosts.

Le DNS A et la redirection Freebox ont permis l’émission du certificat via HTTP-01. Ne pas rejouer l’installation ou l’émission initiale. Maintenir l’accès public TCP 80 pour le renouvellement ; vérifier séparément TCP 443 pour HTTPS. Ne pas ouvrir le port 8000, PostgreSQL, SSH ou Tailscale sur Internet. Pour la première validation, utiliser Cloudflare en mode **DNS-only**, sans Tunnel. Si son proxy HTTP est activé ensuite, utiliser **Full (strict)** avec le certificat d’origine valide.

### Première mise en service du vhost

Cette procédure est **préparée, non exécutée**. Ne pas lancer de workflow en parallèle pendant la mise en service.

1. Après un déploiement explicitement autorisé, confirmer que `app` existe et tourne, sans afficher de secrets :

   ```bash
   sudo -u deploy docker compose --project-directory /home/deploy/apps/overlays \
     -f /home/deploy/apps/overlays/compose.yaml ps --all
   curl --fail --silent --show-error http://127.0.0.1:8000/health
   ```

   Attendre HTTP 200 et `{"status":"ok"}`. Si le port est déjà occupé par un autre service, ne pas l’arrêter à l’aveugle. Pour un chemin applicatif différent, adapter les commandes. Ne pas afficher le rendu complet de `docker compose config`, qui contient des secrets.

2. Installer le vhost livré par ce déploiement dans le répertoire du Nginx hôte. **Pour cette première installation, s’arrêter si le fichier ou le lien `overlays` existe déjà**, et examiner la configuration existante avant de la remplacer :

   ```bash
   sudo install -o root -g root -m 0644 \
     /home/deploy/apps/overlays/nginx/https/default.conf \
     /etc/nginx/sites-available/overlays
   sudo ln -s /etc/nginx/sites-available/overlays /etc/nginx/sites-enabled/overlays
   sudo /usr/sbin/nginx -t
   ```

   Conserver `acme-bootstrap` activé : il reste le serveur HTTP par défaut pour les autres applications, tandis que le vhost Overlays inclut lui-même le snippet ACME. Aucun conteneur Nginx ne doit reprendre les ports 80/443. Si un ancien proxy Docker est présent, diagnostiquer et organiser sa bascule explicitement ; la CI ne supprime pas les conteneurs orphelins.

3. **Seulement si `nginx -t` réussit**, recharger :

   ```bash
   sudo systemctl reload nginx
   ```

   En cas de test invalide, ne pas recharger : corriger la configuration ou retirer seulement le lien ajouté lors de cette première installation, puis refaire le test. Le Nginx déjà en cours continue avec sa configuration précédente. Ne pas modifier les permissions des clés pour contourner une erreur.

### Renouvellement et rechargement

Le timer et le hook commun `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx` sont gérés par `geekom`. L’ancien drop-in Overlays et son rechargement de conteneur sont abandonnés. Ne pas surcharger le service Certbot par application.

Une fois le vhost HTTPS installé, refaire le dry-run pour cette configuration :

```bash
sudo certbot renew --cert-name overlays.necsus.dev --dry-run --run-deploy-hooks
```

Puis contrôler le certificat réellement servi en HTTPS. Le dry-run précédent a validé le hook sur le socle HTTP, pas encore le chargement du certificat par ce vhost TLS.

### Validation réelle attendue

Depuis un réseau extérieur au LAN (par exemple une connexion mobile), vérifier :

```bash
curl --fail --silent --show-error https://overlays.necsus.dev/health
```

Attendre HTTP 200 et `{"status":"ok"}`, avec un certificat reconnu sans option `-k`. Vérifier ensuite `/admin`, le callback OAuth Twitch et un overlay OBS avec son WebSocket authentifié, sans partager de tokens ni de clés OBS. Les liens OBS générés doivent commencer par `https://` ; sinon vérifier l’adresse source du proxy et `OVERLAYS_PROXY_IP`, plutôt que faire confiance à toutes les adresses. La release doit utiliser `SESSION_COOKIE_SECURE=true`.

Le site n’est déclaré opérationnel qu’après ces validations et le test de renouvellement/rechargement avec le vhost TLS. Un échec uniquement depuis le LAN peut venir du NAT loopback du routeur : distinguer ce cas d’un échec depuis Internet avant de modifier le DNS local.

### Limites de l’automatisation

- Les sondes internes et loopback contrôlent l’application, pas le vhost, le certificat ni la disponibilité Internet. Un workflow vert ne prouve pas que HTTPS fonctionne.
- Le vhost est livré mais doit être copié, testé et rechargé manuellement sur l’hôte, y compris après un changement de sa configuration.
- DNS, routeur, première émission et configuration du Nginx partagé ne sont pas automatisés par ce workflow. Les workflows réutilisables `geekom` restent à définir.
- Les versions Docker antérieures à 28 ont une [limite connue pour les ports publiés sur localhost](https://docs.docker.com/engine/network/port-publishing/), potentiellement joignables depuis le même réseau L2. Le Geekom a été migré vers Docker CE ; versions et contrôles sont suivis dans `geekom`. Cela ne remplace pas le contrôle de la publication applicative et de son isolation LAN après déploiement. Ne pas modifier le pare-feu à l’aveugle.

## 4. Données, réseau et limites

Les données d’exécution de l’application sont stockées dans des volumes Docker persistants. Le workflow ne fait pas `docker compose down -v` et ne supprime pas ces volumes. PostgreSQL est géré centralement dans `geekom` ; l’application le rejoint sur le réseau Docker interne `geekom_postgres_clients`. La production et le développement utilisent les bases `overlays` et `overlays_dev`, avec des rôles distincts. L’accès pgAdmin depuis le LAN utilise TLS avec vérification du certificat ; le port PostgreSQL n’est publié ni sur Tailscale ni sur Internet. Ne pas modifier les réseaux ou publications à l’aveugle. Le garde-fou de schéma v1/v2 demeure propre aux migrations Overlays.

Conserver les secrets uniquement dans GitHub et les environnements prévus. Les administrateurs du démon Docker sur le Geekom peuvent accéder aux variables d’environnement des conteneurs. Pour sauvegardes et restauration, voir [ADR-0011](adr/0011-exploitation-durable.md) et le [README](../README.md).
