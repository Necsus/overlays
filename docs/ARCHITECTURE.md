# NecsusDevOverlays — Architecture

Ce document décrit les choix et contraintes de l’existant. L’usage est dans le
[README](../README.md), les opérations dans [DEPLOY.md](DEPLOY.md) et le travail
restant dans la [roadmap](ROADMAP.md). Les signatures, routes, constantes et
schémas détaillés restent dans le code.

## Structure et flux

FastAPI, TwitchIO/EventSub, PostgreSQL via Psycopg asynchrone et frontend natif.
Un bot global dessert plusieurs streamers ; chacun possède son contexte métier.

```text
Chat Twitch → bot global → broadcaster_id → Giveaway + PostgreSQL
                                                └── état propriétaire → OBS
/admin → OAuth Twitch → session → contexte du streamer
```

- `app/domain/` : règles du giveaway, indépendantes des transports.
- `app/application/` : orchestration, commandes et gestion des accès.
- `app/infrastructure/` : persistance et intégration Twitch.
- `app/web/` : HTTP, WebSockets et interfaces.
- `app/main.py` : assemblage et cycle de vie.

Le serveur décide des résultats ; OBS ne fait qu’afficher un état.

## Déploiement et entrée web

```text
Internet → routeur TCP 80/443 → Nginx hôte → 127.0.0.1:8000 → app
                                                            └── PostgreSQL central
```

Le dépôt `geekom` gère PostgreSQL, Nginx et Certbot. Ce dépôt gère l’application,
ses migrations et son vhost ; la CI livre ce dernier sans le recharger.
La procédure et les responsabilités sont dans [DEPLOY.md](DEPLOY.md).

## Données et configuration

| Stockage | Responsabilité |
| --- | --- |
| `.env` | Secrets et bootstrap ; seul `.env.example` est partageable |
| `data/settings.json` ou volume runtime en production | Configuration globale non secrète |
| `.tio.tokens.json` | Tokens gérés par TwitchIO, hors base métier |
| PostgreSQL | Identités, préférences, giveaways, historique et empreintes des clés OBS |

Production et développement utilisent des bases et rôles distincts. Les
migrations sont explicites, pas exécutées au démarrage du serveur. La migration
v2 a supprimé les anciens giveaways de test plutôt que de leur inventer un
propriétaire ; ne pas l’utiliser pour importer des données historiques.

Le LAN exige TLS vérifié. La connexion de production sur le réseau Docker privé
reste une exception sans TLS ; sa migration exige de livrer le CA au conteneur
et un certificat serveur valable pour le nom `postgres`.

Une connexion par transaction, sans pool : mesurer ce coût avant de complexifier.
Le déploiement reste **mono-worker** : sessions, transactions OAuth, quotas,
contextes métier et connexions OBS sont locaux au processus. Ajouter des workers
nécessiterait de coordonner ces ressources, pas seulement de changer Uvicorn.

### Cohérence du giveaway

Les mutations d’un streamer sont sérialisées et publiées après commit SQL.
Une erreur pendant le commit ne prouve pas l’échec de l’écriture : le service
recharge la base avant toute nouvelle mutation, sans rejouer aveuglément un
tirage. Tant que ce rechargement échoue, les mutations restent bloquées et OBS
peut afficher le dernier état connu.

L’échéance est persistée et restaurée côté serveur ; le compteur OBS est un
rendu local, pas l’autorité sur la clôture des inscriptions.

## Authentification et isolation

- Distinguer application Twitch, compte bot et identité du streamer. Les droits
  et le routage reposent sur les identifiants Twitch stables, jamais les noms
  affichés ou un propriétaire déclaré par le navigateur.
- Session administrative et clé OBS sont indépendantes. Une clé donne seulement
  accès au plugin de son propriétaire ; seule son empreinte est persistée.
- OAuth est lié au navigateur qui l’a initié. Un redémarrage invalide les
  connexions OAuth en cours et les sessions administratives.
- `streamers.enabled` contrôle l’admission web/OBS, pas le chat ni les minuteurs.
  OAuth ne réactive pas un compte désactivé. La révocation des accès déjà ouverts
  est périodique, pas instantanée ; un aller-retour désactivation/réactivation
  entre deux observations peut ne pas révoquer les anciens cookies.
- Une panne de vérification refuse les API et nouvelles connexions et ferme les
  sockets non vérifiables, sans conclure que les sessions ont été révoquées.
- Une révocation EventSub retire le routage du chat concerné, sans arrêter son
  giveaway ni ses connexions OBS en lecture.

Ce modèle n’est pas à lui seul une politique d’admission SaaS : toute personne
ayant accès au site peut tenter OAuth. L’administration refuse le cadrage ;
les pages OBS restent intégrables.

## Protection des entrées publiques

Les budgets OAuth, sessions et OBS sont bornés **par processus**. Leurs seuils
sont définis dans `app/application/session.py`, `oauth_state.py`,
`public_limits.py` et `app/web/websocket.py` ; les recopier ici créerait une
seconde source de vérité.

Les quotas par IP dépendent de la confiance proxy configurée dans
[DEPLOY.md](DEPLOY.md#configuration-github-actions). Un NAT partage les quotas ;
des clients distribués peuvent épuiser le budget global. Les fenêtres de débit
sont fixes, pas glissantes.

La limite applicative du message d’authentification OBS intervient après son
assemblage ASGI : elle ne borne pas à elle seule les buffers du transport.

## Diffusion et verrous réseau

OBS reçoit des **instantanés complets**, pas un journal d’événements. Chaque
socket possède un émetteur et une file d’un état : le dernier état remplace
l’état en attente. Des états intermédiaires peuvent donc être sautés, sans
perdre l’état final. Cette politique ne convient pas telle quelle à un flux Chat.
La borne porte sur le nombre d’états, pas sur leur taille.

Les envois et fermetures réseau ne retiennent pas le verrou métier. Le verrou
d’accès coordonne changements d’identité, rotations et admission OBS pour éviter
qu’un accès s’enregistre pendant sa révocation ; SQL reste sous ce verrou,
mais les échanges Twitch et fermetures réseau en sortent. Les délais réseau
reposent sur l’annulation coopérative des transports.

Une rotation détache aussi les connexions si le résultat du commit est incertain.
Les octets déjà envoyés ne peuvent pas être rappelés. Un échec d’abonnement
EventSub connu peut laisser l’administration accessible avec un chat dégradé ;
une connexion web réussie ne prouve pas que le bot reçoit les commandes.

## Administration et aperçus

Le lien OBS est conservé dans `sessionStorage` pour permettre sa recopie dans
l’onglet, avec vérification du compte et de la rotation. Ce secret reste
accessible au JavaScript de l’origine : ce n’est pas une protection contre une
XSS. L’absence de copie locale ne révoque pas la clé côté serveur.

L’aperçu CSS utilise le renderer OBS et des données fictives dans une iframe
sandboxée sans origine partagée ; sa CSP bloque les ressources externes.
L’usage et les limites visibles sont décrits dans le
[README](../README.md#administration-et-obs).

## Maintenance et limites

- Avant toute mise à jour de TwitchIO, réévaluer
  `app/infrastructure/twitch_websocket.py` ; retirer ce contournement après
  validation d’une correction amont.
- La recherche de participants est linéaire et chaque inscription ouvre une
  transaction. Les optimisations doivent partir de mesures.
- La supervision Twitch et les contrôles de disponibilité sont incomplets :
  `/health` ne garantit ni PostgreSQL ni EventSub. `robots.txt` n’est pas un
  contrôle d’accès ni une garantie de désindexation.
- Aucune capacité de 10 000 spectateurs n’est démontrée ; distinguer spectateurs,
  messages reçus et sources OBS connectées. Voir
  [ADR-0003](adr/0003-stabilisation-charge.md).

Les validations restent ponctuelles et manuelles, sans suite automatisée.
Leur suivi se trouve dans la roadmap et les ADR ouverts, pas dans ce document.
