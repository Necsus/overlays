# WI-0004 — Plugin Chat indépendant

## Cadrage

**Type :** implementation

### Objectif

Afficher les messages Twitch dans une source Chat authentifiée et indépendante,
sans perturber les commandes Giveaway. Première valeur vérifiable : un message
apparaît dans OBS pendant que les commandes continuent de fonctionner.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#structure-et-flux) : un bot global
  dessert les contextes des streamers.
- `app/infrastructure/twitch.py` reçoit le chat ;
  `app/application/commands.py` traite les commandes.
- `app/application/overlay_access.py`, `app/infrastructure/overlay_access.py`,
  `app/web/routes/admin.py` et `app/web/routes/overlay.py` portent les accès OBS
  existants. Leur protocole est réutilisable, pas les clés Giveaway.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#diffusion-et-verrous-réseau) : le
  mécanisme « dernier état » de Giveaway ne constitue pas un journal de chat.
- Le plugin est prévu, non implémenté. Les valeurs produit suivantes restent
  des propositions : commandes et messages du bot affichés, 30 messages visibles,
  expiration à 60 secondes, nouveaux messages en bas, pseudo et texte ; couleur
  à décider.

### Périmètre et contraintes

- Cibles proposées : réception Twitch, routage applicatif, gestionnaire Chat
  distinct dans `app/web/`, routes Chat, ressources sous
  `app/web/static/plugins/chat/`, administration et documentation associée.
- Source prévue : `/plugins/chat/overlay#<clé-chat>` et WebSocket
  `/plugins/chat/ws`. Gestion de clé sous `/api/admin/plugins/chat/overlay-access`
  et `/rotate`, avec slug `chat`.
- Définir un message interne indépendant de TwitchIO : ID du message, ID auteur,
  login, nom affiché, texte et date de réception UTC.
- Réutiliser le bot et les événements reçus ; une erreur ou lenteur Chat ne
  bloque ni les commandes ni Giveaway. Files, mémoire et DOM bornés, délais
  d’envoi et déconnexions ciblées. Des messages trop anciens peuvent être
  abandonnés en surcharge, pas les commandes associées.
- Fenêtre vide au rechargement, sans historique persistant en V1. Rendu textuel
  sûr, expiration, reconnexion progressive et déduplication par ID si disponible.
- Source et clé propres : une rotation Chat ne ferme pas Giveaway et inversement.
  Aucun message avant authentification ; les clés des autres plugins sont refusées.
- Badges, emotes, réponses, Cheers et réglages visuels sont reportés. Cadrer
  suppressions/effacements avant usage public. Pas de second bot, d’overlay
  composite ni de framework générique de plugins ; une scène composite reste
  une étude ultérieure qui préserverait les sources indépendantes.
- Les vérifications proposées utilisent des données fictives. Toute création
  de tests/scripts et tout essai Twitch/OBS réel attendent l’accord spécifique
  d’[AGENTS.md](../../AGENTS.md).

### Dépendances

Confirmer les choix produit avant l’approbation du cadrage. Réutiliser le modèle
d’accès existant ; la recette [WI-0005](../validation/WI-0005-multi-streamer.md)
est requise avant usage externe simultané. Les mesures de WI-0003 guident les
budgets sans imposer une nouvelle infrastructure.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Définir le message Chat interne et son routage depuis `app/infrastructure/twitch.py`. | Contrat indépendant de TwitchIO, routé par ID Twitch stable. | Revue du contrat et exemples fictifs après approbation. |
| T02 | Distribuer vers commandes et service Chat sans attendre les envois réseau Chat. | Une panne du Chat n’interrompt pas les commandes. | Contrôles isolés d’erreur et de lenteur, après autorisation du protocole. |
| T03 | Ajouter le gestionnaire Chat distinct avec files bornées, délais et éviction ciblée. | Politique de surcharge explicite, consommation bornée. | Clients fictifs ; charge et nouveaux fichiers de tests sur accord spécifique. |
| T04 | Ajouter page, WebSocket et authentification Chat avec slug `chat`. | Source authentifiée, aucune diffusion croisée ni avant accès valide. | Contrôles isolés des clés et du routage de deux propriétaires. |
| T05 | Construire le rendu texte, fenêtre bornée, expiration et reconnexion dans les ressources Chat. | DOM sûr, vidé au rechargement et conforme aux choix approuvés. | Aperçu avec messages fictifs, texte HTML hostile et rafales bornées autorisées. |
| T06 | Ajouter statut et rotation de clé Chat dans les routes et l’interface admin. | Rotations et accès indépendants entre Chat et Giveaway. | Accès API directs isolés et revue des révocations ; aucune clé journalisée. |
| T07 | Documenter le parcours puis préparer la recette conjointe. | Protocole identifiant version, deux plugins et client lent. | Relecture documentaire ; exécution réelle uniquement sur accord. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Après accord, ouvrir une source Chat authentifiée et envoyer des messages Twitch pendant un giveaway. | Chat visible, commandes et Giveaway intacts. | Version et observations Twitch/OBS sans lien confidentiel. |
| R02 | Utiliser des clés Chat/Giveaway incorrectes ou échangées, puis tourner chaque clé séparément. | Refus des mauvaises clés ; rotation sans effet sur l’autre plugin. | Matrice d’accès et effets des rotations, expurgée. |
| R03 | Avec plusieurs clients autorisés dont un lent, exercer expiration, rechargement, reconnexion et texte HTML. | DOM/mémoire bornés, texte non exécuté, pas d’historique ni blocage des commandes. | Observations navigateur et mesures selon protocole approuvé. |
| R04 | Avec deux streamers, comparer messages, clés et révocations. | Aucun message ni effet de révocation croisé. | Résultats pour chaque propriétaire. |

## Suivi

### Approbation du cadrage

En attente de validation humaine, après confirmation des choix produit. La
migration ne vaut ni approbation de ces propositions ni autorisation d’implémenter.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant implémentation | Choix d’affichage | À arbitrer | Confirmer commandes/bot, nombre visible, durée, disposition et couleur ; propositions non approuvées. |
| Avant usage public | Suppressions et effacements Twitch | À cadrer | Définir le traitement requis et, si nécessaire, un WI complémentaire. |

### Validation finale

En attente d’implémentation, de revue indépendante et de recette sur une
livraison identifiée. Terminé lorsque les deux sources fonctionnent ensemble,
avec clés non interchangeables, rotations isolées, texte sûr et ressources bornées.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | Les propositions d’affichage restent ouvertes ; une inconnue structurante nécessiterait un WI préalable. | Arbitrage du cadrage requis avant exécution, sans choix produit implicite. |
