# Déploiement de la release

Procédure historique pour publier une version figée sur
**https://overlays.necsus.dev**, distincte du dépôt de développement.
L'installation locale de dev reste dans le [README](../README.md).

**État :** cette procédure décrit l'ancienne installation NixOS, confirmée
sous `https://overlay.necsus.dev`. Le nom retenu pour le prochain déploiement est
`https://overlays.necsus.dev` ; le DNS, le proxy HTTPS et le callback Twitch
restent à basculer. Ces instructions ne sont pas une procédure Debian/Compose.

## Décisions en vigueur

| Sujet | Choix |
| --- | --- |
| Code figé | `/srv/overlays`, commit Git explicite |
| Processus | service systemd NixOS, `127.0.0.1:8000`, un worker, sans `--reload` |
| Accès cible | Nginx HTTPS `overlays.necsus.dev` → `8000` |
| Dev | historique : dépôt `/home/necsus/dev/overlays` ; cible actuelle : processus local sur `127.0.0.1:8001` |
| PostgreSQL | historique : même base `overlays` ; cible Geekom : bases `overlays` (release) et `overlays_dev` (dev), rôles distincts |

Le partage de base décrit uniquement l'ancienne installation. La séparation
release/dev sur le Geekom évite les migrations et données communes, mais ne
sépare pas les événements Twitch : deux processus connectés au même canal peuvent
traiter les mêmes commandes. Garder Twitch désactivé en développement sauf usage
d'un canal de test distinct.

Conserver des fichiers `.env` et `.tio.tokens.json` **distincts**. Ne jamais
les versionner, les afficher ni les copier dans cette documentation.

## 1. Préparer NixOS

Ajouter un module, par exemple `/etc/nixos/overlays.nix`, et l'importer dans
`/etc/nixos/configuration.nix` à côté de `overlay-proxy.nix`.

Ne pas ouvrir le port `8000` dans le pare-feu : Nginx y accède en local. Ne
pas modifier SSH, Tailscale ni le proxy existant.

```nix
{ config, pkgs, ... }:

{
  users.groups.overlays = { };
  users.users.overlays = {
    isSystemUser = true;
    group = "overlays";
    home = "/srv/overlays";
  };

  systemd.services.overlays = {
    description = "NecsusDev Overlays (release)";
    after = [ "network.target" "postgresql.service" ];
    wants = [ "postgresql.service" ];
    wantedBy = [ "multi-user.target" ];
    # ctypes.util.find_library (Psycopg) a besoin de `ld` ; LD_LIBRARY_PATH seul ne suffit pas.
    path = [ pkgs.binutils ];
    environment.LD_LIBRARY_PATH = "${config.services.postgresql.package.lib}/lib";
    serviceConfig = {
      Type = "simple";
      User = "overlays";
      Group = "overlays";
      WorkingDirectory = "/srv/overlays";
      ExecStart = "/srv/overlays/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000";
      Restart = "on-failure";
      RestartSec = "5s";
      NoNewPrivileges = true;
      PrivateTmp = true;
    };
  };
}
```

Le service échouera tant que `/srv/overlays` n'est pas installé : c'est
attendu. Construire **sans activer** :

```bash
sudo nixos-rebuild build
```

Relire le module, puis seulement :

```bash
sudo nixos-rebuild switch
```

Vérifier que l'utilisateur système existe : `getent passwd overlays`.

## 2. Installer le code figé

Depuis une session qui peut cloner le dépôt privé :

```bash
sudo mkdir -p /srv/overlays
sudo chown necsus:users /srv/overlays
git clone git@github.com:Necsus/overlays.git /srv/overlays
# Remplacer par le commit réellement retenu :
git -C /srv/overlays checkout --detach e9a274339cdf3a9dd3d8288d29b708f0dd2acddc
```

Ne pas y copier `.env`, `.tio.tokens.json` ni d'autres secrets depuis le
dépôt de développement.

```bash
cd /srv/overlays
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pg_lib=$(nix --extra-experimental-features 'nix-command flakes' build --no-link --print-out-paths 'nixpkgs#postgresql^lib') && export LD_LIBRARY_PATH="$pg_lib/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -c "import psycopg; print('Psycopg OK')"
cp -n .env.example .env
chmod 600 .env
```

Compléter `.env` **sur la machine**, sans coller de secrets dans le terminal
ni dans un ticket :

- `PSQL_*` : mêmes valeurs que l'application actuelle (`PSQL_DB=overlays`).
- `TWITCH_ADMIN_REDIRECT_URI=https://overlays.necsus.dev/auth/twitch/callback`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_SECRET` : nouvelle valeur, distincte de la dev
- Identifiants de l'application Twitch : les mêmes que pour le live, avec ce
  callback déclaré dans la console Twitch

Créer le schéma si besoin (idempotent si la version 1 existe déjà) :

```bash
python -m app.infrastructure.database
```

Puis transférer la propriété au compte du service :

```bash
sudo chown -R overlays:overlays /srv/overlays
sudo chmod 700 /srv/overlays
sudo chmod 600 /srv/overlays/.env
```

## 3. Activer la release

Avant le démarrage : désactiver Twitch dans le `.env` de **dev** ou arrêter le
processus sur `8001` s'il a Twitch activé.

```bash
sudo systemctl restart overlays.service
sudo systemctl status overlays.service --no-pager
```

Contrôles attendus, **sans exposer de secrets** :

```bash
systemctl is-active overlays.service
curl --noproxy '*' --connect-timeout 5 --max-time 10 -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health
curl --noproxy '*' --connect-timeout 5 --max-time 10 -sS -o /dev/null -w '%{http_code}\n' https://overlays.necsus.dev/health
```

Les deux `/health` doivent répondre `200`. Confirmer ensuite
https://overlays.necsus.dev/admin depuis le navigateur.

Un `502` Nginx signifie que le service n'écoute pas encore sur `8000`. Consulter
`journalctl -u overlays.service -e` sans y coller de fichier d'environnement.

Le parcours Twitch (bot, streamer, source OBS) n'est validé qu'après connexion
réelle sur le domaine de release. La commande Python de dev sur `8001` reste
indépendante.

## 4. Mettre à jour une release déjà installée

Le script `scripts/update-release.sh` enchaîne fetch local, checkout détaché,
dépendances, migration et redémarrage. Il ne lit pas, n'affiche pas et ne
copie pas `.env` ni `.tio.tokens.json`. Nginx, SSH et Tailscale restent
intacts.

```bash
cd /home/necsus/dev/overlays
# Le commit doit déjà exister dans ce dépôt ; les fichiers non commités ne
# partent pas.
git rev-parse HEAD
./scripts/update-release.sh HEAD
```

Ajouter `-y` pour ignorer la confirmation. Le script transmet le commit via un
bundle Git lisible par l'utilisateur `overlays` (son compte n'a pas accès à
`/home/necsus`). `libpq` est repris depuis `LD_LIBRARY_PATH` du service.

Contrôles attendus : `overlays.service` actif, `http://127.0.0.1:8000/health`
et `https://overlays.necsus.dev/health` en HTTP 200.

Toute migration SQL doit rester compatible avec un retour arrière, ou être
refusée. Un redémarrage de la release n'arrête pas Nginx ni la dev.

## 5. Hors périmètre actuel

- Base PostgreSQL distincte pour la dev
- Sauvegardes automatisées et restauration vérifiée
- Supervision (latences, files, état Twitch)
- Isolation des tokens et des données entre environnements
