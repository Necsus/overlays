# WI-0007 — Alertes Points de chaîne

## Cadrage

**Type :** implementation

### Objectif

Afficher dans une source OBS indépendante une utilisation réelle de récompense
personnalisée Twitch : pseudo, titre de la récompense et coût en points de cette
utilisation, sans action sur son traitement métier.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#structure-et-flux) : bot global,
  routage par streamer et plugins OBS indépendants.
- `app/infrastructure/twitch.py`, `app/infrastructure/twitch_oauth.py` et
  `app/web/routes/auth.py` : consentement, abonnements et révocations Twitch.
- `app/application/overlay_access.py`, `app/infrastructure/overlay_access.py`
  et les routes admin/overlay : modèle d’accès à réutiliser avec une clé propre.
- [Documentation EventSub](https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelchannel_points_custom_reward_redemptionadd) :
  faisabilité documentaire, pas validation d’une récompense réelle.
- Fonctionnalité prévue, non implémentée. Le coût n’est ni un solde ni un cumul,
  et le titre de récompense est indépendant du lot Giveaway.

### Périmètre et contraintes

- Cibles proposées : intégration OAuth/EventSub, service Points de chaîne,
  gestionnaire de diffusion distinct, routes/page sous
  `/plugins/channel-points/`, gestion de clé admin et documentation.
- Source prévue : `/plugins/channel-points/overlay#<clé-points>`, WebSocket et
  clé propres. Réutiliser le protocole, jamais une clé Giveaway ou Chat ; aucune
  diffusion avant authentification.
- Page transparente avec sélecteurs stables pseudo/récompense/points ; CSS
  personnalisé copié dans OBS. Pas d’application distante ni d’extension de la
  bibliothèque de styles Giveaway dans cette tranche.
- Déclencher à réception, sans attendre la validation manuelle du streamer.
  L’alerte ne prouve pas la récompense honorée ; une annulation ultérieure ne
  retire pas une alerte déjà vue.
- Lecture seule : ni création, validation, remboursement, son, animation avancée
  ou action Giveaway. Récompenses automatiques et changements de statut hors V1.
- Source vide au chargement, sans historique persistant ni rattrapage des arrêts.
- Prérequis Twitch : points de chaîne activés, récompense personnalisée et
  consentement streamer `channel:read:redemptions`. Les droits actuels du bot
  de chat ne suffisent pas ; aucun droit de gestion pour ce simple affichage.
- Événement `channel.channel_points_custom_reward_redemption.add`, version `1`,
  filtré par `broadcaster_user_id`. Pas de filtre `reward_id` ni de sélection de
  récompense en V1 : toutes les récompenses personnalisées de la chaîne.
- Utiliser `user_name`, `reward.title`, `reward.cost`, ainsi que l’ID d’utilisation,
  l’ID streamer, l’ID récompense et `redeemed_at` pour routage et déduplication
  bornée en mémoire. Ne pas transmettre la saisie libre du spectateur.
- Vérifier la prise en charge dans la version de TwitchIO utilisée, et gérer
  reprise/révocation par streamer sans second bot ni webhook public par défaut.
- Pseudo et titre sont rendus comme du texte, jamais du HTML. Borner les envois
  et isoler les clients lents ; aucun blocage de Chat ou Giveaway.
- Affichage à confirmer : proposition de huit secondes, puis masquage ; la
  dernière utilisation remplacerait la précédente et relancerait la durée.
  Si chaque alerte doit rester visible, décider d’une file bornée, de sa limite
  et de sa politique de débordement avant le code.
- Contrôles fictifs et recette réelle sont distincts. Tout test/script,
  consentement réel et essai Twitch/OBS suit les accords d’[AGENTS.md](../../AGENTS.md).

### Dépendances

Arbitrage d’affichage, compte Twitch éligible et autorisation de la recette.
Réutiliser les accès existants et valider l’isolation de
[WI-0005](../validation/WI-0005-multi-streamer.md) avant usage externe.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Vérifier le contrat EventSub et TwitchIO, puis préparer l’évolution du consentement et de l’abonnement. | Permission minimale et événement corrects, cycle de reprise/révocation défini. | Revue de code/documentation ; essai réel seulement avec consentement autorisé. |
| T02 | Définir l’événement interne indépendant de TwitchIO et son routage par streamer/plugin. | Champs minimaux et déduplication bornée, sans garantie exactement une fois après redémarrage. | Exemples fictifs, doublons et horodatages ; tests nouveaux sur accord. |
| T03 | Ajouter service, source, WebSocket et gestion de clé propre dans l’admin. | Accès authentifié et rotations/révocations isolées des autres plugins. | Contrôles d’accès directs et sockets fictifs autorisés. |
| T04 | Rendre l’alerte textuelle et son masquage selon l’arbitrage approuvé. | Valeurs correctes, CSS personnalisable, comportement rapproché borné. | Navigateur fictif, texte hostile et événements rapprochés, sans mutation Twitch. |
| T05 | Préparer puis documenter la recette conjointe et les limites de livraison. | Protocole de doublons, reconnexions, clients lents et deux streamers. | Relecture et contrôles isolés autorisés ; validation réelle séparée. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Avec une chaîne éligible et le consentement autorisé, utiliser une vraie récompense personnalisée. | Événement reçu, bons pseudo/titre/coût affichés sans gestion métier de la récompense. | Version et observation Twitch → serveur → OBS sans tokens. |
| R02 | Exercer doublons fictifs, utilisations rapprochées, masquage et reconnexion selon protocole autorisé. | Déduplication bornée et règle d’affichage approuvée ; source vide sans rattrapage inventé. | Scénarios et résultats distincts de la recette réelle. |
| R03 | Avec deux streamers et les autres plugins, essayer mauvaises clés, rotation et révocation ciblées. | Aucun accès ni arrêt croisé ; les clients lents ne bloquent pas les autres plugins. | Matrice des accès et résultats par source. |
| R04 | Dans OBS, appliquer un CSS fictif et observer la transparence et les sélecteurs. | Affichage stylable et masquage complet après la durée retenue. | Observation du rendu et validation de l’utilisateur. |

## Suivi

### Approbation du cadrage

En attente de validation humaine, en particulier du remplacement des alertes ou
de la file bornée. Les propositions ne sont pas des décisions acquises.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant implémentation | Durée et utilisations rapprochées | À arbitrer | Confirmer huit secondes et remplacement, ou cadrer file/limites/débordement. |
| Avant recette réelle | Éligibilité et consentement Twitch | À autoriser | Chaîne, récompense, créneau et permissions à identifier, sans partager de secrets. |

### Validation finale

En attente d’implémentation, revue indépendante, recette et acceptation sur une
livraison identifiée. Terminé lorsque R01 à R04 confirment une utilisation réelle
stylable, sans action métier ni diffusion croisée.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | La faisabilité documentaire ne remplace pas l’essai Twitch ; le choix d’affichage reste préalable. | Migration approuvée ; arbitrages produit et opérations réelles en attente. |
