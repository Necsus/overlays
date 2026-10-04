# NecsusDevOverlays

Plateforme d'overlays Twitch pour OBS, pilotés depuis le chat et regroupés dans
une administration commune.

- **Giveaway** : tirages manuels ou chronométrés, inscriptions uniques et
  gagnants multiples.
- **Chat** : plugin en préparation, pas encore disponible.

L'application prend en charge plusieurs streamers simultanément avec un bot
Twitch global. Chaque streamer possède son giveaway, ses préférences de commande,
son historique et ses clés OBS indépendants.

## Installation et lancement

Sur le poste de développement local, depuis le clone du dépôt, avec Python
3.11 ou plus récent et un accès au PostgreSQL 18 du Geekom via le LAN ou
Tailscale. La base de développement y est distincte de celle de release.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Première installation seulement, si .env n'existe pas :
cp -n .env.example .env
# Compléter soi-même .env ; pour le développement, PSQL_DB=overlays_dev
# et PSQL_USER/PSQL_PASSWORD doivent désigner le rôle de développement.
python -c "import psycopg; print('Psycopg OK')"
# Créer/mettre à jour le schéma avant de lancer l'application :
python -m app.infrastructure.database
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Déploiement Docker Compose sur Debian

Le Compose de ce dépôt est prévu pour le Geekom Debian : PostgreSQL 18.6 y
héberge `overlays` (release) et `overlays_dev` (développement). L'application de
release joint la base par le réseau backend ; le port 5432 est publié uniquement
sur l'IPv4 LAN du Geekom et son IPv4 Tailscale pour les postes de développement.
Aucun port PostgreSQL n'est redirigé depuis Internet. Créer `.env` sur le Geekom
à partir du modèle, renseigner le compte admin PG et l'IPv4 Tailscale, puis
configurer `PSQL_*` pour la base de release, `SESSION_COOKIE_SECURE=true` et
`OVERLAYS_IMAGE_TAG=sha-<commit>` avec un tag immuable publié sur GHCR.
Sur le poste de développement, configurer `.env` avec la base/le rôle
`overlays_dev` et l'adresse LAN ou Tailscale. Ne jamais versionner ces fichiers.

Cette séquence suppose des volumes Docker neufs. PostgreSQL n'applique les
variables `POSTGRES_*` qu'à l'initialisation d'un répertoire de données vide ;
ne pas réutiliser un volume existant sans en vérifier l'état. Au premier
démarrage, lancer **uniquement** PostgreSQL :

```bash
docker compose up -d db
```

L'image crée un compte admin dédié (`POSTGRES_ADMIN_USER`), distinct des rôles
applicatifs. La création initiale des deux bases et rôles est manuelle. Ouvrir
une session SQL avec le compte admin :

```bash
docker compose exec db sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Dans `psql`, créer les rôles et bases séparés. `\password` demande les mots de
passe sans les afficher ni les placer dans l'historique SQL :

```sql
CREATE ROLE overlays_release LOGIN;
\password overlays_release
CREATE ROLE overlays_dev LOGIN;
\password overlays_dev
CREATE DATABASE overlays OWNER overlays_release;
CREATE DATABASE overlays_dev OWNER overlays_dev;
```

Configurer sur le Geekom `PSQL_DB=overlays`, `PSQL_USER=overlays_release` et son
mot de passe correspondant. Sur le poste de développement, utiliser
`PSQL_DB=overlays_dev`, `PSQL_USER=overlays_dev` et son propre mot de passe.
Récupérer ensuite l'image publiée sur GHCR, puis appliquer sa migration. Si le
package est privé, authentifier auparavant Docker sur Geekom avec un accès
limité à `read:packages` ; saisir le token à l'invite et ne pas le mettre dans
`.env` ni dans la commande :

```bash
docker compose pull app
docker compose run --rm app python -m app.infrastructure.database
docker compose up -d app
```

L'exemple désactive Twitch par défaut. `TWITCH_ENABLED` initialise
`data/settings.json` seulement à sa création : après cette première création,
modifier `.env` ne change pas à lui seul la configuration persistée. Les volumes
nommés conservent la base et les données de l'application ; ne pas les supprimer
(`docker compose down -v`) sans décision explicite concernant les données. Le
démarrage Compose ne configure ni reverse proxy, ni accès navigateur, ni
sauvegardes.

### GitHub Actions

- Une PR vers `main` construit l'image sans la publier ; le contrôle `build-pr`
  est requis pour fusionner.
- Après fusion sur `main`, le workflow publie l'image sur GHCR avec les tags
  `sha-<commit>` et `main`.
- Le Geekom doit épingler un tag `sha-<commit>` via `OVERLAYS_IMAGE_TAG`, puis
  tirer l'image explicitement ; la publication seule ne redémarre pas le service.
- Le workflow n'utilise aucune variable applicative : GitHub fournit le
  `GITHUB_TOKEN` nécessaire à la publication. Les secrets runtime restent dans
  le `.env` local du Geekom.

### Dépendance `libpq` sur l'ancienne DevBox NixOS

Psycopg a besoin de `libpq`. Les commandes ci-dessous sont spécifiques à
l'ancienne DevBox NixOS ; elles ne configurent ni macOS ni le conteneur Debian.
L'installation de `libpq` sur le poste local actuel reste à vérifier.

En **zsh**, une fois par machine, ajouter dans `~/.zshrc` :

```zsh
[[ -f ~/dev/overlays/scripts/zsh-libpq.zsh ]] && source ~/dev/overlays/scripts/zsh-libpq.zsh
```

Puis `source ~/.zshrc` (ou ouvrir un nouveau terminal). Le script reprend
`LD_LIBRARY_PATH` de `overlays.service`, sans `nix-shell` et sans chemin
`/nix/store/...` figé. `shell.nix` reste disponible si tu utilises `nix-shell`.
La release n'en dépend pas : elle déclare `libpq` dans le service systemd.

Le modèle `.env.example` décrit les paramètres `PSQL_*` : **hôte sans port**,
port séparé, base, utilisateur, mot de passe et mode TLS. Ne pas placer le mot
de passe dans une commande ou une URL partagée. Le chemin Tailscale est chiffré ;
le TLS PostgreSQL pour l'accès LAN reste à configurer. Avant toute connexion sur
un LAN non fiable, configurer un certificat serveur et utiliser `verify-full`
avec une autorité de confiance ; `prefer` seul ne garantit pas le chiffrement.

La migration versionnée crée les tables et enregistre la version du schéma,
sans créer la base ou le rôle. La migration multi-streamer supprime les giveaways
existants (données de test), puis ajoute l’isolation par streamer ; exécute-la
avant de démarrer la nouvelle version. Ne lance pas en parallèle une ancienne
version de l’application sur le même schéma.

- **Rôle de migration** : droit de créer des objets dans le schéma `public`.
- **Rôle applicatif** : lecture/écriture des tables et usage de la séquence des
  participants, sans superutilisateur.
- En développement, le propriétaire de la base dédiée peut remplir les deux
  usages.

En cas d'échec, la migration affiche les noms des paramètres invalides ou une
catégorie d'erreur SQL, jamais les valeurs ni le message brut du pilote. Sans
code d'erreur exploitable, le diagnostic reste général.

Le démarrage refuse un PostgreSQL indisponible ou un schéma non
initialisé/incompatible, sans repli vers SQLite. Garder **un seul worker
Uvicorn** ; `--reload` est réservé au développement. Après un déplacement du
projet, recréer le virtualenv.

### Dépannage PostgreSQL sur NixOS

- **`libpq library not found`** : vérifier que `~/.zshrc` source
  `scripts/zsh-libpq.zsh`, puis ouvrir un **nouveau** terminal zsh (pas un
  `nix-shell`). `echo $LD_LIBRARY_PATH` doit contenir le `lib` PostgreSQL.
  Ne pas figer un chemin `/nix/store/...`. La release déclare `libpq` dans
  `overlays.service`.
- **`no pg_hba.conf entry`** : le serveur répond mais aucune règle ne correspond
  à la connexion tentée. Déclarer l'accès dans
  `services.postgresql.authentication`, pas dans le fichier généré. Limiter la
  règle à la base, au rôle et à l'adresse nécessaires (`127.0.0.1/32` pour IPv4
  local), avec authentification par mot de passe SCRAM. Vérifier l'ordre des
  règles et le choix `host`/`hostssl` selon la politique TLS ; ne pas utiliser
  `trust` ni ouvrir le réseau pour contourner l'erreur.
- **Erreur de connexion générique** : un contrôle de disponibilité ne valide pas
  les identifiants. Tester au besoin avec
  `psql -h 127.0.0.1 -p 5432 -U "ROLE_FICTIF" -d "BASE_FICTIVE" -W -c 'SELECT 1;'`,
  en remplaçant localement les noms et l'adresse. Saisir le mot de passe
  uniquement à l'invite ; ne partager aucun secret ou configuration réelle.

### Développement et release

La commande ci-dessus lance le développement sur `127.0.0.1:8001`, accessible
via `http://127.0.0.1:8001` sur la machine de développement. Le sous-domaine
`overlay-dev.necsus.dev` n'est plus utilisé. L'application se connecte à
`overlays_dev` sur le Geekom : utiliser `192.168.1.112` comme `PSQL_HOST` à la
maison, ou l'adresse/nom Tailscale du Geekom à l'extérieur.

Le nom de production retenu est **[overlays.necsus.dev](https://overlays.necsus.dev)**.
L'ancienne release NixOS utilisait `overlay.necsus.dev` ; son basculement vers le
nouveau nom et la nouvelle installation Debian restent à effectuer. La procédure
NixOS historique est dans [docs/DEPLOY.md](docs/DEPLOY.md) et ne s'applique pas
au déploiement Docker Compose sur Debian.

La release utilise PostgreSQL `overlays`, et le développement local sa base
`overlays_dev`, dans la même instance PostgreSQL 18 du Geekom. Les rôles et
mots de passe sont distincts. Même avec des bases séparées, ne pas activer Twitch
simultanément sur les deux instances pour le même canal : elles pourraient traiter
les mêmes événements.

Les instructions Twitch/OBS ci-dessous utilisent le domaine de production.
Pour le développement, garder Twitch désactivé sauf si un callback OAuth local
spécifique a été déclaré et validé dans la console Twitch ; ne pas réutiliser le
callback de production.

| Chemin | Usage |
| --- | --- |
| `/admin` | Connexion Twitch et gestion du lien OBS |
| `/health` | Vérification que le service répond |
| `/docs` | Documentation OpenAPI |

## Connecter Twitch et OBS

1. Déclarer dans l'application Twitch le callback exact :
   `https://overlays.necsus.dev/auth/twitch/callback`.
2. Démarrer le service avec Twitch activé selon `.env.example`.
3. Ouvrir `/auth/twitch/bot/login` sur le domaine HTTPS et autoriser **le compte
   bot configuré**, avec `user:read:chat`, `user:write:chat` et `user:bot`.
4. Ouvrir `/admin` avec le compte streamer et accorder `channel:bot`.
5. Générer le lien du plugin Giveaway et le copier dans une **source navigateur
   OBS** :

```text
https://overlays.necsus.dev/plugins/giveaway/overlay#<clé-OBS>
```

Le lien est confidentiel. Après génération, il reste recopiable après rechargement
dans le même onglet grâce à `sessionStorage`, si le compte et la rotation sont
inchangés. Si ce stockage est bloqué, copiez-le avant de recharger. La déconnexion
efface cette copie locale, mais ne coupe pas le giveaway. Perdre la copie locale
ne révoque pas le lien dans OBS. Le régénérer invalide l'ancien lien et déconnecte
ses sources. Les connexions OBS restent propres à chaque streamer ; connecter
un autre compte ne déconnecte pas les sources des autres.

Le rendu se personnalise dans le champ **CSS personnalisé** d'OBS. Éléments
disponibles : `#giveaway`, `#lot`, `#status`, `#participants`, `#winner`,
`#countdown`. Le compteur est masqué sans durée ou après clôture.

## Commandes Giveaway

| Commande | Accès | Effet |
| --- | --- | --- |
| `!galot <lot>` | Streamer | Prépare le lot et affiche l'overlay. |
| `!gastart [secondes]` | Streamer | Ouvre les inscriptions, avec une durée facultative. |
| `!join` | Viewer | Inscrit le viewer une seule fois. |
| `!gapull` | Streamer | Ferme les inscriptions et tire un gagnant, puis ajoute un gagnant inédit à chaque nouvel appel. |
| `!gastop` | Streamer | Termine le giveaway et masque l'overlay. |

Le préfixe `!` est le défaut et peut être personnalisé depuis les préférences
Giveaway de l’administration ; il est propre à chaque streamer.

Exemple : `!galot Clavier mécanique`, puis `!gastart 60`.

- La durée doit être un entier de **1 à 604800 secondes** (7 jours). `!gastart`
  seul n'active aucun minuteur.
- À l'échéance, un gagnant est tiré automatiquement. Sans participant, le
  giveaway est annulé et masqué.
- Un tirage manuel réussi ou `!gastop` annule le minuteur.
- Après le premier tirage, les inscriptions restent fermées ; les tirages
  suivants excluent les gagnants précédents.
- L'échéance et les gagnants sont conservés après redémarrage. Une échéance
  dépassée est traitée à la reprise.
- Une inscription traitée après l'échéance est refusée. Le serveur décide du
  tirage ; garder l'horloge du PC OBS à l'heure pour un compteur visuel correct.
  Le premier tick peut afficher `durée + 1` (arrondi supérieur) ; l'échéance
  serveur reste exacte.

## Secrets et données

Ne jamais versionner, partager ni afficher le contenu de `.env` ou
`.tio.tokens.json`. Seul `.env.example` sert de référence partageable pour les
variables attendues. Les liens OBS sont également confidentiels.

Les identités, giveaways, participants, gagnants et empreintes des clés OBS
résident désormais dans PostgreSQL. `data/settings.json` reste une configuration
locale ; les tokens Twitch restent hors de la base SQL.

L’ancienne version de test SQLite a été supprimée avec accord. La migration
multi-streamer supprime aussi les giveaways PostgreSQL préexistants de test ; les
identités Twitch et clés OBS sont conservées. Les contextes sont restaurés au
démarrage ; reconnecte un compte dans `/admin` si son autorisation Twitch doit
être renouvelée. Les liens OBS existants restent rattachés à leur streamer.

### Sauvegarde PostgreSQL

Utiliser `pg_dump` au format personnalisé (`-Fc`) et conserver les sauvegardes
hors du dépôt, avec des permissions restreintes et une durée de conservation
définie. Fournir les identifiants par un mécanisme confidentiel, jamais dans
l'historique du terminal. `pg_dump` n'interprète pas les variables applicatives
`PSQL_*` du fichier `.env`.

Vérifier la restauration avec `pg_restore` vers **une autre base vide**, puis
comparer les données et démarrer une instance isolée sans Twitch réel. Ne jamais
essayer une restauration destructive sur la base utilisée. L'automatisation et
la validation réelle restent dans
[ADR-0011](docs/adr/0011-exploitation-durable.md) ; les sauvegardes SQL ne
couvrent pas les fichiers locaux de configuration et de tokens, à protéger
séparément.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) : fonctionnement actuel, stockage,
  sécurité et limites.
- [Déploiement](docs/DEPLOY.md) : publication de la release sur NixOS.
- [Roadmap](docs/ROADMAP.md) : priorités et index des décisions (ADR).
- [AGENTS.md](AGENTS.md) : consignes de travail pour les agents IA.

## Licence

[MIT](LICENSE) — dépôt
[Necsus/overlays](https://github.com/Necsus/overlays).
