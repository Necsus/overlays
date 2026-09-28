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

Sur la DevBox NixOS, depuis `/home/necsus/dev/overlays`, avec Python
3.11 ou plus récent et une base PostgreSQL dédiée déjà créée :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Première installation seulement, si .env n'existe pas :
cp -n .env.example .env
# Compléter soi-même .env avec les valeurs nécessaires.
python -c "import psycopg; print('Psycopg OK')"
# Créer/mettre à jour le schéma avant de lancer l'application :
python -m app.infrastructure.database
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Psycopg a besoin de `libpq`. En **zsh**, une fois par machine, ajouter dans
`~/.zshrc` :

```zsh
[[ -f ~/dev/overlays/scripts/zsh-libpq.zsh ]] && source ~/dev/overlays/scripts/zsh-libpq.zsh
```

Puis `source ~/.zshrc` (ou ouvrir un nouveau terminal). Le script reprend
`LD_LIBRARY_PATH` de `overlays.service`, sans `nix-shell` et sans chemin
`/nix/store/...` figé. `shell.nix` reste disponible si tu utilises `nix-shell`.
La release n'en dépend pas : elle déclare `libpq` dans le service systemd.

Le modèle `.env.example` décrit les paramètres `PSQL_*` : **hôte sans port**,
port séparé, base, utilisateur, mot de passe et mode TLS. Ne pas placer le mot
de passe dans une commande ou une URL partagée. Pour un serveur distant,
utiliser `verify-full` avec un certificat de confiance plutôt que le mode
opportuniste `prefer`.

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
via **[overlay-dev.necsus.dev](https://overlay-dev.necsus.dev)** tant que le
processus tourne. L'accès HTTPS a été contrôlé depuis le serveur et confirmé par
l'utilisateur.

**[overlay.necsus.dev](https://overlay.necsus.dev)** sert la release
(`overlays.service` → `127.0.0.1:8000`). L'utilisateur a confirmé qu'elle
fonctionne. Publication et mises à jour : [docs/DEPLOY.md](docs/DEPLOY.md).

Release et développement partagent pour l'instant la base PostgreSQL
`overlays`. Twitch ne doit être activé que sur une instance à la fois.

Les instructions Twitch/OBS ci-dessous utilisent le domaine cible de la release.
Pour tester la dev, utiliser `https://overlay-dev.necsus.dev` et déclarer son
callback exact dans l'application Twitch :
`https://overlay-dev.necsus.dev/auth/twitch/callback`. Le parcours OAuth dev
reste à valider ; ne pas connecter les deux instances au même canal pour des
essais simultanés.

| Chemin | Usage |
| --- | --- |
| `/admin` | Connexion Twitch et gestion du lien OBS |
| `/health` | Vérification que le service répond |
| `/docs` | Documentation OpenAPI |

## Connecter Twitch et OBS

1. Déclarer dans l'application Twitch le callback exact :
   `https://overlay.necsus.dev/auth/twitch/callback`.
2. Démarrer le service avec Twitch activé selon `.env.example`.
3. Ouvrir `/auth/twitch/bot/login` sur le domaine HTTPS et autoriser **le compte
   bot configuré**, avec `user:read:chat`, `user:write:chat` et `user:bot`.
4. Ouvrir `/admin` avec le compte streamer et accorder `channel:bot`.
5. Générer le lien du plugin Giveaway et le copier dans une **source navigateur
   OBS** :

```text
https://overlay.necsus.dev/plugins/giveaway/overlay#<clé-OBS>
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
