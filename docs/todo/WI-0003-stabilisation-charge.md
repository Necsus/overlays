# WI-0003 — Diagnostic de charge et capacité Giveaway

## Cadrage

**Type :** exploration

### Objectif

Mesurer la chaîne message → commande → transaction → OBS sur une version
identifiée, puis livrer un diagnostic reproductible : capacité observée,
cohérence, limites et éventuelles corrections à cadrer. Ce WI ne livre pas
une optimisation ni une promesse de capacité non démontrée.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#données-et-configuration) : une
  connexion PostgreSQL par transaction et déploiement mono-worker.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#diffusion-et-verrous-réseau) :
  publication hors attente réseau et files du dernier état déjà implémentées.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#protection-des-entrées-publiques) :
  quotas existants ; limites applicatives et limites de transport distinctes.
- Modules à observer : `app/domain/giveaway.py`, `app/application/commands.py`,
  `app/application/service.py`, `app/infrastructure/database.py`,
  `app/infrastructure/twitch.py`, `app/web/websocket.py` et
  `app/web/static/plugins/giveaway/overlay.js`.
- [WI-0011](WI-0011-exploitation-durable.md) porte sauvegarde/restauration,
  contraintes SQL et reprise après incident. [WI-0012](WI-0012-supervision-metier.md)
  porte les sondes et la supervision ; leur implémentation sort de ce diagnostic.

### Périmètre et contraintes

- Cibles modifiables proposées : protocole, mesures et conclusions dans le
  suivi du présent WI ; documentation durable seulement pour les faits établis.
  Les modules applicatifs sont des cibles de lecture, pas de correction ici.
- Avant toute charge, faire approuver cible jetable, version, durée, paliers,
  débit de messages et d'inscriptions, nombre de streamers et de sources OBS,
  client lent, budget CPU/mémoire/connexions et conditions d'arrêt.
- Convenir des seuils de latence, erreurs et ressources avant la mesure ; les
  valeurs restent à arbitrer, pas à inventer dans ce recadrage. Mesurer au moins
  latences p50/p95, débit effectivement traité, erreurs, CPU, mémoire et connexions SQL.
- Le scénario historique de 10 000 inscriptions uniques reste un volume candidat,
  pas un débit ni une équivalence avec 10 000 spectateurs. L'autoriser avec sa
  cadence et sa durée, ou justifier un volume plus représentatif.
- Utiliser une base PostgreSQL séparée et des données fictives. Ne connecter
  aucun bot, compte ou OBS réel sans accord opérationnel distinct.
- Conserver l'architecture mono-worker et l'isolation. Indexation des participants,
  pool SQL, Redis, workers et modifications de reconnexion ne sont pas autorisés
  ici ; une correction justifiée fera l'objet d'un WI complémentaire approuvé.
- Tout fichier de mesure/test/script, instrumentation, charge ou coupure attend
  l'accord spécifique d'[AGENTS.md](../../AGENTS.md). Ce recadrage ne les autorise pas.

### Dépendances

Base jetable, moyens de mesure et protocole à autoriser. L'ordre conseillé place
la validation multi-streamer WI-0005 et la restaurabilité WI-0011 avant la campagne
de mesures ; leur clôture n'est pas nécessaire pour préparer le protocole.
Les résultats pourront guider WI-0012 et les budgets des futurs plugins, sans
bloquer la sauvegarde/restauration sur un dimensionnement préalable.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Définir la matrice de charge et les moyens de mesure à partir des modules cités. | Version, cible, paliers, seuils, budget, arrêt et éventuels fichiers explicitement approuvables. | Revue documentaire ; aucune charge avant accord spécifique. |
| T02 | Mesurer commandes/service/SQL/OBS selon le protocole approuvé. | Latences, débit, erreurs, CPU, mémoire et connexions sourcés ; coût de connexion/commit par inscription isolé autant que possible. | Mesures locales bornées sur données fictives, seulement après autorisation. |
| T03 | Observer plusieurs sources fictives, dont une lente, et la reprise réseau simulée autorisée. | Effets sur commandes, sources saines, files et ressources quantifiés ; fermetures définitives distinguées des coupures récupérables. | Clients et coupures isolés prévus au protocole ; aucune modification de reconnexion. |
| T04 | Comparer mémoire et base après inscriptions uniques/répétées et tirages du scénario. | Doublons, divergence ou rejeu éventuels identifiés, sans correction ni panne SQL injectée ici. | Lectures et scénarios fictifs autorisés ; incidents SQL approfondis dans WI-0011. |
| T05 | Produire le diagnostic et les décisions proposées dans le suivi. | Seuils comparés aux résultats ; options classées par preuve, coût et valeur, y compris ne rien changer. | Revue des mesures ; aucune optimisation déduite d'une hypothèse. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Approuver version, base jetable, matrice, seuils et moyens avant les mesures. | Scénario représentatif, borné, reproductible et sans cible réelle implicite. | Protocole, valeurs retenues et accord attribué/daté. |
| R02 | Relire les résultats des inscriptions, dont le volume de 10 000 si retenu, et des clients OBS lents. | Mesures complètes ; cohérence et écarts documentés ; résultat distinct d'une capacité en spectateurs. | Version, paramètres, comptages et mesures anonymisées. |
| R03 | Arbitrer le diagnostic et les suites proposées. | Soit aucune correction nécessaire, soit écarts acceptés ou WI de correction à cadrer ; aucune implémentation tacitement autorisée. | Rapport accepté et décisions explicites, sans résultats inventés. |

## Suivi

### Approbation du cadrage

En attente de validation humaine du cadrage et du protocole chiffré. L'accord
sur le recadrage documentaire ne vaut ni approbation du diagnostic à exécuter,
ni autorisation de charge, de fichiers de tests/scripts ou de coupures.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Existant décrit dans l'architecture ; date/version non consignées ici | T03, ancien T04 avant recadrage | Prérequis partiellement implémenté, non validé sous charge | Files du dernier état, délais et publication hors attente réseau décrits ; aucune mesure nouvelle pendant la migration. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant exécution | R01 | À autoriser | Cible, paliers, seuils, budget, charge et éventuels fichiers à approuver ; aucun essai lancé. |
| Diagnostic à livrer | R02, R03 | À effectuer | Aucune mesure de capacité ni décision d'optimisation validée par ce recadrage. |

### Validation finale

Terminé lorsque le rapport et ses preuves reproductibles sont revus, acceptés
et intégrés, avec écarts et suites arbitrés. Un seuil non atteint peut être un
résultat valide de l'exploration, pas une conformité de l'application. Aucune
capacité de 10 000 spectateurs n'est démontrée par 10 000 inscriptions.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | L'ordre d'optimisation reste guidé par les mesures ; les choix d'infrastructure ne sont pas autorisés d'avance. | Cadrage détaillé et protocole à approuver dans une session dédiée. |
| 2026-11-01 | Utilisateur et assistant | Recentrer WI-0003 sur un diagnostic ; ancien T05 transféré à WI-0012 ; anciennes pistes T02/T06 conservées comme suites conditionnelles d'indexation/reconnexion, sans code ici. | Conversation courante : accord « Valider le plan » pour le recadrage documentaire uniquement ; cadrage d'exécution en attente. |
