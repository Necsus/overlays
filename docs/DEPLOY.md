# Déploiement sur le Geekom

Le déploiement de production utilise Debian, Docker Compose et GitHub Actions. Un push sur `main` construit l’image, la publie sur GHCR, puis la déploie sur le Geekom via Tailscale et Tailscale SSH. La procédure NixOS historique n’est plus la procédure active.

## État et points à confirmer

- **Observé** : le dernier workflow consulté (`05d273d`) a réussi son contrôle
  interne. Lors du diagnostic sur le Geekom, seul PostgreSQL tournait ; aucun
  conteneur `app` n’existait et aucun proxy web n’était actif. Le site n’a jamais
  été accessible depuis le passage à Compose, selon l’utilisateur. La cause de
  la disparition de `app` reste inconnue.
- **Préparé dans le dépôt** : profils Nginx de bootstrap HTTP et de service HTTPS,
  transfert de leurs fichiers par CI et hook systemd de renouvellement Certbot.
  Aucun déploiement de ces changements ni changement DNS/routeur n’a été réalisé.
- **Contrôlé localement** : validation Compose avec les valeurs fictives de
  `.env.example`, syntaxe YAML et shell du workflow, et `git diff --check`.
- **Non validé** : exécution Nginx (daemon Docker local indisponible), émission
  et renouvellement ACME, HTTPS externe, OAuth Twitch et WebSocket OBS sur cette
  nouvelle entrée web.

La mise en service nécessite la procédure ci-dessous et le traitement des
[limites de l’automatisation](#limites-de-lautomatisation). Un workflow vert
ne suffit pas à déclarer le site opérationnel.

Le workflow est [`../.github/workflows/publish-ghcr.yml`](../.github/workflows/publish-ghcr.yml). Il suppose que le Geekom est déjà préparé : Debian, Docker avec le plugin Compose, Tailscale actif, Tailscale SSH configuré et compte `deploy` autorisé à utiliser Docker. Le compte doit pouvoir écrire dans `/home/deploy/apps/overlays` (ou le chemin configuré). Ne pas modifier SSH, Tailscale ou le pare-feu dans le cadre de ce guide.

## 1. Configurer GitHub Actions

Dans **Settings → Secrets and variables → Actions**, ajouter les éléments ci-dessous. Les valeurs d’exemple indiquent seulement le format ; les secrets se saisissent directement dans GitHub et ne doivent pas être copiés dans le dépôt ou les journaux.

### Variables

- `GEEKOM_APP_DIR` : chemin sous `/home/deploy/apps`, par exemple `/home/deploy/apps/overlays`.
- `GEEKOM_DEPLOY_USER` : `deploy`.
- `GEEKOM_TAILSCALE_HOST` : adresse IPv4 Tailscale du Geekom. La publication PostgreSQL indiquée par Compose n’est actuellement pas effective sur son réseau `internal: true` ; voir les limites réseau ci-dessous.
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

Le job de déploiement valide les paramètres, génère temporairement un `.env` protégé, rejoint le tailnet, puis transfère Compose et les configurations Nginx/Certbot. La sonde `tailscale ssh` récupère la clé d’hôte annoncée par Tailscale ; SSH et SCP la vérifient strictement, sans désactiver le contrôle de clé. Sur le Geekom, le workflow démarre PostgreSQL, crée ou met à jour les rôles et bases, vérifie le garde-fou de migration, tire l’image du commit, applique la migration et démarre l’application. Il contrôle ensuite `/health` depuis le conteneur. Si le compte `deploy` peut détecter les deux fichiers du certificat, il démarre Nginx, vérifie sa configuration et la recharge. Sinon il saute cette étape sans faire échouer le job ; voir les limites de l’automatisation ci-dessous.

La configuration Twitch et le préfixe de commande persistés dans `settings.json` sont réécrits depuis les variables GitHub à chaque déploiement. Les valeurs modifiées depuis l’interface admin peuvent donc être remplacées. L’application est arrêtée pendant la migration : prévoir une brève interruption.

Consulter l’onglet **Actions** pour le résultat. Le workflow évite d’imprimer les valeurs secrètes et ne dump pas les journaux des conteneurs. En cas d’échec, partager le nom de l’étape et le message non sensible, jamais les fichiers `.env`, tokens ou logs contenant des secrets.

## 3. Accès HTTPS depuis Internet

### Prérequis publics

Le proxy Nginx est configuré pour écouter sur l’adresse LAN du Geekom
(`192.168.1.112`) ; l’application n’expose aucun port hôte. L’utilisateur dispose
d’une IPv4 publique fixe et de l’accès au routeur. Avant la première émission :

- faire pointer l’enregistrement A de `overlays.necsus.dev` vers cette IPv4
  publique, jamais vers `192.168.1.112` ; vérifier aussi qu’un éventuel AAAA
  n’envoie pas les clients vers une autre destination ;
- rediriger uniquement TCP 80 et 443 du routeur vers `192.168.1.112` ;
  ne pas exposer PostgreSQL ni modifier SSH/Tailscale ;
- permettre au challenge HTTP-01 de Let’s Encrypt d’atteindre le Geekom sur 80,
  y compris lors des renouvellements.

Ces actions exposent l’interface web à Internet : les réaliser manuellement
avec confirmation de leur périmètre. Pour la première validation, utiliser
Cloudflare en mode **DNS-only**, sans Tunnel. Si son proxy HTTP est activé
ensuite, utiliser **Full (strict)** avec le certificat d’origine valide.

### Première mise en service

Les commandes suivantes sont **prévues, non exécutées**. Elles supposent qu’un
déploiement autorisé a transféré les nouveaux fichiers et démarré `app`. Ne pas
lancer de workflow en parallèle pendant la bascule entre les profils Nginx.

Sur le Geekom, définir le chemin réel et ce raccourci pour le terminal courant
(les exemples utilisent le chemin par défaut) :

```bash
APP_DIR=/home/deploy/apps/overlays
compose() {
  sudo -u deploy docker compose --project-directory "$APP_DIR" \
    -f "$APP_DIR/compose.yaml" "$@"
}
compose ps --all
```

L’application doit être en cours d’exécution. Si elle est absente, reprendre le
diagnostic/déploiement avant de considérer HTTPS disponible. Ne pas afficher
le rendu complet de `docker compose config`, qui contient des secrets.

1. Installer Certbot sur l’hôte Debian :

   ```bash
   sudo apt update
   sudo apt install certbot
   ```

2. Démarrer le bootstrap HTTP, qui ne sert que le challenge ACME :

   ```bash
   compose --profile bootstrap up -d nginx-bootstrap
   compose --profile bootstrap exec -T nginx-bootstrap nginx -t
   ```

3. Émettre le premier certificat. Remplacer l’e-mail fictif ; cette commande
   accepte les conditions de Let’s Encrypt :

   ```bash
   sudo certbot certonly --webroot \
     --webroot-path "$APP_DIR/acme-webroot" \
     --cert-name overlays.necsus.dev -d overlays.necsus.dev \
     --email adresse@example.net --agree-tos --non-interactive
   ```

   Les certificats et clés restent dans `/etc/letsencrypt` sur l’hôte : ne pas
   les copier dans le dépôt, GitHub, les journaux ou les réponses.

4. Une fois l’émission réussie, arrêter le bootstrap puis démarrer HTTPS :

   ```bash
   compose --profile bootstrap stop nginx-bootstrap
   compose --profile https up -d nginx
   compose --profile https exec -T nginx nginx -t
   ```

   Les deux profils ne doivent pas tourner simultanément : ils utilisent le
   même port 80. Nginx sert encore le challenge ACME en HTTP pour les futurs
   renouvellements ; les autres chemins HTTP redirigent vers HTTPS.

### Renouvellement et rechargement

Le drop-in livré remplace la commande `ExecStart` du service Certbot Debian et
ajoute un hook de rechargement du conteneur `overlays-nginx`. Vérifier sa
compatibilité avec le service Certbot installé et avec tout autre certificat
éventuellement géré par cet hôte avant de l’installer :

```bash
sudo install -D -m 0644 \
  "$APP_DIR/ops/systemd/certbot.service.d/overlays.conf" \
  /etc/systemd/system/certbot.service.d/overlays.conf
sudo systemctl daemon-reload
sudo systemctl enable --now certbot.timer
sudo certbot renew --cert-name overlays.necsus.dev --dry-run \
  --run-deploy-hooks --deploy-hook '/usr/bin/docker exec overlays-nginx nginx -s reload'
```

Le dry-run vérifie le renouvellement de test et le hook sans remplacer le
certificat de production. Le timer utilise le drop-in ; une commande manuelle
`certbot renew` sans `--deploy-hook` ne bénéficie pas automatiquement de cet
argument systemd. Les mises à jour du drop-in livrées par CI doivent être
réinstallées manuellement sur l’hôte, puis suivies de `daemon-reload`.

### Validation réelle attendue

Depuis un réseau extérieur au LAN (par exemple une connexion mobile), vérifier :

```bash
curl --fail --silent --show-error https://overlays.necsus.dev/health
```

Attendre HTTP 200 et `{"status":"ok"}`, avec un certificat reconnu sans option
`-k`. Vérifier ensuite `/admin`, le callback OAuth Twitch et un overlay OBS
avec son WebSocket authentifié, sans partager de tokens ni de clés OBS.
La release doit utiliser `SESSION_COOKIE_SECURE=true`. Le site n’est déclaré
opérationnel qu’après ces validations et le test de renouvellement/rechargement.

Un échec uniquement depuis le LAN peut venir du NAT loopback du routeur :
distinguer ce cas d’un échec depuis Internet avant de modifier le DNS local.

### Limites de l’automatisation

- Le workflow teste les fichiers Certbot avec `test -s` en tant que `deploy`.
  Si les répertoires `live`/`archive` sont réservés à root, ce test échoue même
  avec un certificat installé et Nginx n’est pas démarré par le job. La détection
  reste à corriger sans rendre la clé privée lisible par `deploy`.
- L’étape sautée sans certificat détecté laisse le workflow réussir. Le message
  ne distingue pas un certificat absent d’un accès refusé.
- `nginx -t` et le rechargement ne sont ni une sonde HTTP du proxy ni un test de
  disponibilité Internet. La validation externe reste manuelle.
- L’installation Certbot, le timer, DNS et routeur ne sont pas automatisés par
  GitHub Actions. Aucune de ces actions n’est réalisée en mettant à jour la doc.

## 4. Données, réseau et limites

Les données PostgreSQL et la configuration d’exécution de l’application sont stockées dans des volumes Docker persistants. Le workflow ne fait pas `docker compose down -v` et ne supprime pas ces volumes. PostgreSQL est attaché uniquement au réseau Docker `backend` configuré `internal: true`. Bien que Compose déclare des ports LAN/Tailscale, Docker ne les publie pas pour un conteneur relié uniquement à ce réseau interne ; l’application, elle, communique avec PostgreSQL sur ce réseau. Rendre PostgreSQL accessible depuis le poste de développement nécessitera une décision réseau séparée ; ne pas supprimer `internal: true` à l’aveugle.

Le contrôle `/health` est interne au conteneur : il ne valide ni le DNS, ni le proxy HTTPS, ni OAuth Twitch/OBS. Après le déploiement, valider séparément l’accès HTTPS et, si nécessaire, le parcours Twitch/OBS.

Les bases `overlays` (release) et `overlays_dev` (développement) sont distinctes, avec des rôles séparés. Le contrôle de migration refuse le passage du schéma v1 si des giveaways existants seraient supprimés. Toute base préexistante mérite une sauvegarde vérifiée avant une migration.

Conserver les secrets uniquement dans GitHub et les environnements prévus. Les administrateurs du démon Docker sur le Geekom peuvent accéder aux variables d’environnement des conteneurs. Pour sauvegardes et restauration, voir [ADR-0011](adr/0011-exploitation-durable.md) et le [README](../README.md).
