# WI-0012 — Supervision et disponibilité métier

## Cadrage

**Type :** implementation

### Objectif

Distinguer processus HTTP vivant, accès PostgreSQL et réception Twitch utilisable,
puis exposer un diagnostic borné sans secrets. Livrable : contrat de santé,
sondes et supervision Twitch vérifiables sur pannes isolées, sans redémarrage
abusif du service pour une panne d'une dépendance.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#maintenance-et-limites) : la route
  `/health` actuelle ne garantit ni PostgreSQL ni EventSub.
- `app/web/routes/health.py` renvoie une réponse HTTP statique ; `app/main.py`
  démarre la tâche Twitch ; `app/infrastructure/twitch.py` connaît les
  abonnements de chat par streamer. Ces signaux ne prouvent pas à eux seuls
  qu'un message métier vient d'être reçu.
- `app/infrastructure/database.py`, `app/application/service.py` et
  `app/web/websocket.py` portent les états/erreurs, transactions et files utiles.
- [WI-0003](WI-0003-stabilisation-charge.md) apporte les mesures de charge ;
  [WI-0011](WI-0011-exploitation-durable.md) porte la cohérence de reprise et
  [WI-0013](WI-0013-controles-post-deploiement.md) les contrôles opérateur.
- Ce WI reprend l'ancien T05 de WI-0003 et l'ancien T01/ancienne R06 de WI-0011.
  Aucun de ces travaux n'est déclaré exécuté par leur transfert.

### Périmètre et contraintes

- Cibles proposées : `app/web/routes/health.py`, `app/main.py`,
  `app/infrastructure/twitch.py`, instrumentation minimale des modules cités et
  documentation dans `docs/ARCHITECTURE.md` / `docs/DEPLOY.md`.
- Faire approuver avant code le contrat de `live`/`ready` : chemins, réponses,
  délais, fraîcheur, mode Twitch désactivé et panne SQL/Twitch partielle.
  Distinguer santé du processus, disponibilité globale et état par streamer.
- Un abonnement connu ou une connexion TCP ne prouve pas une chaîne métier
  saine. Ne pas exiger des messages récents sur une chaîne silencieuse comme
  seule preuve de disponibilité ; préciser les limites des signaux observés.
- Décider comment observer une tâche Twitch terminée et signaler la dégradation.
  Toute relance automatique, politique de reprise ou modification du cycle de
  vie demande un arbitrage explicite, sans boucle de redémarrage automatique
  ni changement des règles de révocation.
- Borner coût, délais et fréquence des vérifications SQL/réseau. Ne pas ouvrir
  une transaction coûteuse à chaque requête publique ni révéler identités,
  configuration, exceptions du pilote, tokens ou détails de connexion.
- Conserver le contrat `/health` utilisé par la CI et Compose tant qu'une
  évolution de ses consommateurs n'est pas explicitement approuvée. Aucun
  changement de workflow, Compose, proxy, réseau ou service hôte dans ce cadrage.
- Choisir un diagnostic minimal exploitable : état HTTP/SQL/Twitch, erreurs,
  latences, files et connexions seulement dans la mesure utile. Les résultats
  WI-0003 guident les seuils ; pas de stack de monitoring ou dépendance nouvelle
  sans besoin démontré et accord distinct.
- Pannes simulées uniquement en environnement isolé. Les fichiers de tests/scripts,
  instrumentation retenue et opérations précises nécessitent les accords
  d'[AGENTS.md](../../AGENTS.md) ; ce recadrage n'en autorise aucune.

### Dépendances

Contrat de santé et protocole à faire approuver. WI-0003 fournit des budgets
mesurés quand disponibles, sans bloquer la définition des états de santé.
WI-0011 prouve la reprise métier après incident ; ne pas recopier cette preuve
comme si elle démontrait les délais de détection des sondes. Aucune clôture
complète de ces deux WI n'est nécessaire pour préparer le contrat.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Définir états, sondes, consommateurs et matrice des dégradations dans le suivi. | Contrat approuvable distinguant HTTP, SQL, Twitch désactivé/dégradé et portée par streamer. | Revue documentaire, sans appel réel ni changement de consommateurs. |
| T02 | Implémenter les sondes approuvées dans `app/web/routes/health.py` et les signaux minimaux nécessaires. | Contrôles bornés, réponse expurgée et `/health` compatible avec l'existant. | Contrôles isolés approuvés ; nouveaux tests et écritures après accord spécifique. |
| T03 | Observer la tâche Twitch et les abonnements dans `app/main.py` et `app/infrastructure/twitch.py`. | Échec et perte d'abonnement visibles sans faux état sain ni effet sur une autre chaîne. | Scénarios fictifs autorisés ; aucune révocation réelle implicite. |
| T04 | Exercer panne/récupération SQL et Twitch et comparer les diagnostics au contrat. | Dégradation, délais et retour à l'état sain démontrés sans fuite ni boucle de reprise. | Pannes bornées sur cible isolée, seulement après accord opérationnel. |
| T05 | Documenter limites des sondes, indicateurs et conduite opérateur. | Diagnostic exploitable, dimensionnement relié aux mesures disponibles et validations restantes explicites. | Relecture et revue indépendante ; aucune disponibilité réelle déduite du seul HTTP. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Approuver le contrat et relire les cas HTTP vivant, SQL indisponible et Twitch désactivé/dégradé. | Réponses et actions opérateur définies sans ambiguïté ni secrets. | Contrat accepté, version et limites des signaux. |
| R02 | En environnement isolé autorisé, exercer panne/récupération SQL et contrôles répétés. | Délais/coût bornés, diagnostic exact et HTTP vivant distinct de la disponibilité métier. | Paramètres, mesures et résultats expurgés. |
| R03 | Sur contextes fictifs autorisés, terminer la tâche Twitch ou retirer un abonnement puis rétablir le service. | Dégradation visible et isolée ; retour conforme au contrat sans double traitement ni redémarrage en boucle. | Matrice des états, version et résultats ; reprise métier rapprochée de WI-0011 si applicable. |
| R04 | Vérifier l'absence de régression du `/health` existant et relire le runbook. | Consommateurs actuels compatibles ; aucune information confidentielle dans la réponse ou les journaux. | Résultats ciblés, revue du contenu et acceptation humaine. |

## Suivi

### Approbation du cadrage

En attente d'approbation humaine du cadrage, du contrat de santé et des
opérations. L'accord de création documentaire ne vaut pas autorisation de code,
de tests/scripts, de panne ni de déploiement.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| 2026-11-01, recadrage documentaire | T01 à T05 | Non exécutées | Travaux transférés de WI-0003/WI-0011 ; aucun livrable applicatif ni contrôle de panne produit. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant implémentation | R01 et protocole isolé | À approuver | Chemins, états, délais, fraîcheur, cible et éventuels fichiers non décidés. |
| Livraison à identifier | R02 à R04 | À effectuer | Ancienne R06 de WI-0011 : supervision, dimensionnement et panne/récupération incomplets ; aucune preuve nouvelle. |

### Validation finale

Terminé après contrat livré, implémentation, revue indépendante, recette
conforme, acceptation et intégration identifiée. La clôture prouve les signaux
et limites convenus, pas une disponibilité permanente ni une capacité de charge
non mesurée. Toute évolution des consommateurs des sondes reste distincte.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-11-01 | Utilisateur et assistant | Extraire la supervision des anciens WI-0003/0011 afin de distinguer mesure, cohérence de reprise et détection. | Conversation courante : accord « Valider le plan » sur le recadrage documentaire et la création de WI-0012 ; cadrage d'exécution en attente. |
