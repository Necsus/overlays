# Déploiement sur le Geekom

Le déploiement de production utilise Debian, Docker Compose et GitHub Actions. Un push sur `main` construit l’image, la publie sur GHCR, puis la déploie sur le Geekom via Tailscale et Tailscale SSH. La procédure NixOS historique n’est plus la procédure active.

## État et points à confirmer

- **Observé** : le dernier workflow consulté (`05d273d`) a réussi son contrôle interne, mais le dernier diagnostic Docker ne montrait que PostgreSQL, sans conteneur `app`. Sa disparition reste inexpliquée ; cet état doit être revérifié.
- **Socle commun en place** : Nginx et Certbot sur l’hôte, webroot HTTP-01 commun, certificat Overlays émis, timer planifié et dry-run réussi avec le hook de rechargement du Nginx hôte. La source de cet état et du runbook commun est le dépôt d’infrastructure `geekom` (`docs/architecture.md` et `docs/runbooks/nginx-tls.md`). Ne pas réinstaller ce socle par application.
- **Préparé dans ce dépôt, non déployé** : publication de `app` sur `127.0.0.1:8000`, confiance proxy limitée à la passerelle Docker vérifiée, vhost HTTPS pour le Nginx hôte et adaptation CI sans proxy Docker/Certbot.
- **Contrôlé localement** : YAML, syntaxe shell/Python du workflow, rendu Compose avec données fictives et sans lecture du `.env` réel, conservation de PostgreSQL/volumes/réseaux et des blocs SQL/migration. Vingt contrôles ponctuels isolés couvrent la validation IPv4, la garde de passerelle et la sonde HTTP ; ils ne valident pas un conteneur ou un réseau réel. Le LSP YAML est indisponible.
- **Non validé** : exécution de cette nouvelle CI, publication réelle du port applicatif, confiance proxy effective, chargement de ce vhost sur le Geekom, HTTPS externe, OAuth Twitch et WebSocket OBS. Le daemon Docker local et un Nginx local sont indisponibles ; les contrôles statiques ou simulés ne remplacent pas ces validations.

La mise en service nécessite la procédure ci-dessous et le traitement des [limites de l’automatisation](#limites-de-lautomatisation). Un workflow vert ne suffit pas à déclarer le site opérationnel.

Le workflow est [`../.github/workflows/publish-ghcr.yml`](../.github/workflows/publish-ghcr.yml). Il suppose que le Geekom est déjà préparé : Debian, Docker Engine 28 ou supérieur avec le plugin Compose, Nginx/Certbot communs, Python 3 sur l’hôte (fourni par Certbot Debian), Tailscale actif, Tailscale SSH configuré et compte `deploy` autorisé à utiliser Docker. Le compte doit pouvoir écrire dans `/home/deploy/apps/overlays` (ou le chemin configuré). Ne pas modifier SSH, Tailscale ou le pare-feu dans le cadre de ce guide.

## 1. Configurer GitHub Actions

Dans **Settings → Secrets and variables → Actions**, ajouter les éléments ci-dessous. Les valeurs d’exemple indiquent seulement le format ; les secrets se saisissent directement dans GitHub et ne doivent pas être copiés dans le dépôt ou les journaux.

### Variables

- `GEEKOM_APP_DIR` : chemin sous `/home/deploy/apps`, par exemple `/home/deploy/apps/overlays`.
- `GEEKOM_DEPLOY_USER` : `deploy`.
- `GEEKOM_TAILSCALE_HOST` : adresse IPv4 Tailscale du Geekom. La publication PostgreSQL indiquée par Compose n’était pas effective avant la migration Docker CE et reste à revérifier sur son réseau `internal: true` ; voir les limites réseau ci-dessous.
- `OVERLAYS_PROXY_IP` : facultative, IPv4 de la passerelle Docker `app_egress` par laquelle Nginx atteint Uvicorn. Valeur par défaut vérifiée sur le Geekom : `172.18.0.1`. La CI refuse un wildcard, un CIDR ou une adresse différente des passerelles de ce réseau. Si le réseau est recréé avec une autre passerelle, actualiser cette variable avant le prochain déploiement ; ne pas élargir la confiance à `*`.
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

Le job valide les paramètres, génère temporairement un `.env` protégé, rejoint le tailnet, puis transfère Compose et le vhost applicatif Nginx. La sonde `tailscale ssh` récupère la clé d’hôte annoncée par Tailscale ; SSH et SCP la vérifient strictement, sans désactiver le contrôle de clé. Sur le Geekom, le workflow démarre PostgreSQL, prépare les rôles et bases, vérifie le garde-fou de migration et tire l’image du commit. Une commande Python sans serveur ni bot initialise le réseau applicatif si nécessaire ; la CI vérifie sa passerelle avant d’arrêter l’application. Elle conserve ensuite la séquence existante de mise à jour des rôles, migration et configuration, puis démarre `app`. Elle contrôle `/health` dans le conteneur et depuis l’hôte sur `127.0.0.1:8000`, avec HTTP 200 et `{"status":"ok"}` attendus pour la sonde hôte.

Le workflow ne lit plus les certificats et ne démarre ni ne recharge Nginx. Il dépose le vhost dans `$GEEKOM_APP_DIR/nginx/https/default.conf` ; son installation dans `/etc/nginx` reste manuelle. Les changements ultérieurs de ce fichier ne sont donc pas appliqués au proxy par un simple déploiement applicatif.

La configuration Twitch et le préfixe de commande persistés dans `settings.json` sont réécrits depuis les variables GitHub à chaque déploiement. Les valeurs modifiées depuis l’interface admin peuvent donc être remplacées. L’application est arrêtée pendant la migration : prévoir une brève interruption.

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

Les données PostgreSQL et la configuration d’exécution de l’application sont stockées dans des volumes Docker persistants. Le workflow ne fait pas `docker compose down -v` et ne supprime pas ces volumes. PostgreSQL est attaché uniquement au réseau Docker `backend` configuré `internal: true`. Bien que Compose déclare des ports LAN/Tailscale, ils n’étaient pas effectivement publiés lors du diagnostic sous l’ancien moteur Docker ; cet état reste à revérifier après sa mise à jour. L’application, elle, communique avec PostgreSQL sur ce réseau. Rendre PostgreSQL accessible depuis le poste de développement nécessitera une décision réseau séparée ; ne pas supprimer `internal: true` à l’aveugle.

Les bases `overlays` (release) et `overlays_dev` (développement) sont distinctes, avec des rôles séparés. Le contrôle de migration refuse le passage du schéma v1 si des giveaways existants seraient supprimés. Toute base préexistante mérite une sauvegarde vérifiée avant une migration.

Conserver les secrets uniquement dans GitHub et les environnements prévus. Les administrateurs du démon Docker sur le Geekom peuvent accéder aux variables d’environnement des conteneurs. Pour sauvegardes et restauration, voir [ADR-0011](adr/0011-exploitation-durable.md) et le [README](../README.md).
