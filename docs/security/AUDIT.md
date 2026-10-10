# Audit de sécurité — exposition Internet et isolation des streamers

[← Roadmap](../ROADMAP.md)

**Date :** 2026-10-10. **Révision de base auditée :** `41b94b9`.
**Nature :** revue du dépôt et contrôles ponctuels locaux, pas un pentest de production.

Une page d'accueil a été ajoutée parallèlement pendant l'audit (`home.py`,
`home.html` et montage dans `main.py`). Cet ajout statique a aussi été relu,
sans nouveau constat ; ces modifications préexistantes à la clôture sont
préservées et ne sont pas réalisées par cet audit.

La mise en production est annoncée par l'utilisateur ; la version et la
configuration réellement servies n'ont pas été vérifiées. Les mentions « non
déployé » des documents d'exploitation ne permettent donc pas de conclure sur
l'état actuel du serveur.

## Synthèse et WIS

WIS désigne ici une fiche de travail sécurité : preuve, impact, correction
proposée et critères de clôture. Aucun correctif applicatif n'avait été réalisé
lors de l'audit initial ; le suivi des corrections et validations ultérieures
est porté par chaque WIS. Les constats ci-dessous décrivent l'état initial.
Les priorités sont qualitatives, sans score CVSS ni mesure de capacité réelle.

| WIS | Priorité / sévérité | Constat |
| --- | --- | --- |
| [0001](WIS-0001-oauth-browser-binding.md) | P1 / élevée | Le `state` OAuth n'est pas lié au navigateur initiateur : login CSRF |
| [0002](WIS-0002-public-resource-limits.md) | P1 / élevée, impact potentiel global | Les entrées publiques consomment mémoire et SQL sans budget applicatif |
| [0003](WIS-0003-network-under-locks.md) | P1 / élevée, impact potentiel global | Des attentes réseau sous verrous permettent des blocages entre streamers |
| [0004](WIS-0004-session-revocation.md) | P2 / modérée | La déconnexion n'invalide pas un cookie déjà copié |
| [0005](WIS-0005-disabled-streamer-access.md) | P2 / modérée | `enabled=false` n'est pas appliqué uniformément aux API et clés OBS |
| [0006](WIS-0006-admin-framing.md) | P2 / faible, conditionnelle | L'administration n'a pas de politique anti-cadrage |

Les lacunes de code sont établies ; les conditions d'exploitation sont précisées
par fiche. Aucune exploitation ni compromission en production n'est démontrée.
Le dernier constat n'est **pas** une preuve de clickjacking authentifié depuis
n'importe quel site : le cookie `SameSite=Lax` réduit ce scénario.

## Périmètre et méthode

Inspectés : assemblage FastAPI, accueil statique, sessions/OAuth, routes administratives et OBS,
stockage SQL des identités/giveaways/clés, commandes et intégration Twitch,
services/minuteurs, scripts frontend, vhost Nginx, Compose, Dockerfile et
workflows de construction/déploiement. Les configurations d'infrastructure ont
été lues, pas modifiées ni exécutées.

- Aucun contenu de `.env`, de fichier de tokens ou de sauvegarde de secrets lu.
- Aucune requête adressée au site, à Twitch ou à PostgreSQL pour les essais.
- Aucune installation, aucun serveur, aucune modification du code ni des
  permissions ; aucun fichier de test ou script créé.
- Consultation externe limitée aux recommandations OAuth et à un avis public
  Starlette, sans données privées du projet.

**22 contrôles ponctuels ont réussi**, avec données fictives et petites bornes.
Les modules autonomes OAuth/clé OBS/domaine ont été importés directement.
Pour les composants nécessitant des dépendances absentes, leurs définitions ont
été exécutées après exclusion des imports, avec doublures de transports,
curseurs, route et signataire. Ce sont des simulations, **pas une suite de tests
FastAPI ni des tests PostgreSQL** ; la signature cryptographique n'a pas été
testée par la doublure de signataire.

Ces contrôles couvrent : usage unique et absence de liaison navigateur du state,
128 states en attente, acceptation d'un token fictif de 8 Kio, routage et
fermeture des sockets A/B, blocages d'envoi/fermeture simulés, paramètres de
propriété des requêtes SQL, absence de lectures enfants après une réponse
propriétaire vide, résolution plugin/empreinte, permissions des commandes,
déconnexion sans révocation et absence du filtre `enabled`.

## Scopage des streamers

**Pas d'IDOR ni de diffusion de données A vers B identifié dans les chemins
revus.** Cette conclusion ne certifie pas l'ensemble du système déployé.

| Surface | Contrôle constaté | Niveau de validation |
| --- | --- | --- |
| Identité web | Identifiant extrait du cookie signé, pas d'un paramètre navigateur (`app/web/dependencies.py:12-35`) | Revue ; simulation avec faux signataire |
| Liste et détail d'historique | Propriétaire issu de la session ; `id AND streamer_id` avant lecture des participants/gagnants (`app/infrastructure/history.py:126-166`) ; route renvoie `404` si absent | Revue ; capture des requêtes avec faux curseur, pas d'exécution SQL |
| Mutations giveaway | Paramètres SQL et prédicats propriétaire pour ouverture, inscription, tirage et arrêt (`history.py:7-88`) | Revue ; capture de quatre mutations |
| Préférences | Lecture/écriture par `identity.twitch_user_id` (`app/web/routes/admin.py:149-192`) | Revue |
| Clés OBS | Rotation par session et plugin ; résolution par empreinte + plugin (`app/infrastructure/overlay_access.py`) | Revue ; capture de la résolution |
| Commandes Twitch | Contexte choisi par `payload.broadcaster.id` ; gestion réservée à l'auteur dont l'ID est celui du broadcaster (`app/infrastructure/twitch.py:107-122`, `app/application/commands.py:62-71`) | Revue ; refus de B dans le handler A simulé |
| Diffusions / rotation | Connexions associées au propriétaire ; broadcast et fermeture ciblés (`app/web/websocket.py`) | Simulation A/B réussie |
| Restauration / minuteurs | Contexte et verrou métier par streamer ; restauration filtrée, index d'unicité par propriétaire | Revue uniquement |
| Révocation EventSub | Retrait du routage du seul abonnement concerné (`app/infrastructure/twitch.py:92-105`) | Revue uniquement |

Les requêtes enfants par `giveaway_id` seul ne constituent pas à elles seules
une IDOR : le parent est d'abord sélectionné avec son propriétaire. Le tirage
insère son gagnant après une mise à jour propriétaire dont le nombre de lignes
est vérifié, dans la même transaction.

**Deux limites de sécurité demeurent :** l'isolation de disponibilité n'est pas
complète ([WIS-0003](WIS-0003-network-under-locks.md)) et la désactivation d'un
propriétaire n'est pas une révocation uniforme
([WIS-0005](WIS-0005-disabled-streamer-access.md)). Une confusion d'identité
provoquée par OAuth peut aussi faire utiliser un overlay du compte attaquant
([WIS-0001](WIS-0001-oauth-browser-binding.md)), sans contourner les filtres SQL.

## Protections déjà présentes

- OAuth vérifie Client ID, identité du token, profil et scopes requis ; le bot
  autorisé doit correspondre à l'ID bot configuré.
- State aléatoire, expirant et consommable une seule fois.
- Cookie signé et expirant, `HttpOnly`, `SameSite=Lax` ; Compose prévoit
  `Secure=true` par défaut, sans confirmation de la valeur déployée.
- Clés OBS de 256 bits ; stockage de leur empreinte uniquement ; secret dans le
  fragment URL puis le premier message WebSocket, pas dans la requête HTTP.
- Réponse de génération avec `Cache-Control: no-store` ; participants absents
  de l'instantané OBS ; requêtes SQL paramétrées.
- Textes dynamiques rendus avec `textContent` ; aperçu CSS dans une iframe sans
  origine partagée et avec CSP restrictive. Pas de XSS identifié dans ces usages.
- Application conteneurisée non root, filesystem en lecture seule et
  `no-new-privileges` ; publication web loopback prévue, confiance proxy bornée.
- Logs d'accès Nginx désactivés dans le vhost et redaction du callback dans les
  logs d'accès Uvicorn. Cela ne certifie pas les autres logs de l'hôte.

## Points non conclus et validations restantes

1. **Admission des streamers.** Le callback inscrit et active tout compte Twitch
   présentant les scopes requis (`auth.py:187-216`, `streamers.py:7-28`).
   L'architecture le décrit comme ouvert aux personnes ayant accès au réseau.
   Ce n'est pas une prise de contrôle du bot ni une IDOR. Décider si l'inscription
   publique est voulue ; sinon, une politique d'admission serveur est nécessaire.
   Aucun WIS de contournement d'allowlist n'est ouvert : aucune allowlist n'existe.
2. **Production.** Confirmer version déployée, certificat/HTTPS, attribut Secure,
   absence d'accès public direct aux ports 8000/5432, configuration Nginx commune,
   en-têtes réellement servis, logs d'erreur et protection anti-abus éventuelle
   hors dépôt. Ne pas partager cookies, URLs OAuth ou clés OBS pour ces contrôles.
3. **Sessions/configuration.** `SessionSigner` accepte toute clé non vide et
   `Settings.session_cookie_secure` vaut `False` par défaut hors Compose.
   La CI accepte aussi `SESSION_COOKIE_SECURE=false`. Entropie réelle et
   configuration sûre non vérifiées : pas de secret faible ou de cookie non
   sécurisé affirmé sans preuve. Absence de HSTS et de CSP générale dans le
   vhost fourni : durcissement à examiner selon le proxy réellement installé.
4. **Dépendances.** Les dépendances directes sont fixées dans `requirements.txt`,
   mais les versions transitives réellement embarquées ne sont pas disponibles
   ici. `fastapi`, `twitchio`, `psycopg`, `aiohttp`, `itsdangerous` et `httpx`
   sont absents du Python local. Aucun scan CVE/SBOM de l'image n'a été réalisé.
   L'avis [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr)
   concerne Starlette `<=1.0.0` (corrigé en `1.0.1`). Version embarquée inconnue,
   pas de contrôle d'autorisation par `request.url.path` trouvé, et Host remplacé
   au proxy prévu : **pas une faille applicable confirmée de ce projet**.
5. **Validations réelles.** Compléter les critères des WIS sur un environnement
   isolé, puis vérifier deux streamers simultanés, redémarrage, rotation OBS et
   révocation EventSub. Aucun test de charge, navigateur, PostgreSQL réel ou
   Twitch/OBS effectué. Le chantier existant est
   [ADR-0005](../adr/0005-multi-streamer.md).

Référence OAuth : [RFC 9700 §2.1 et §4.7.1](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.7.1).
Les WIS portent les corrections et critères ; cet audit ne vaut pas autorisation
de les implémenter ni d'intervenir sur la production.
