# WI-0003 — Stabilisation sous charge

## Cadrage

**Type :** implementation

### Objectif

Démontrer la cohérence message → commande → transaction → OBS sous charge, puis
corriger les goulets mesurés. Livrable : mesures reproductibles et ressources
bornées sans blocage des commandes par un OBS lent.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#données-et-configuration) : une
  connexion PostgreSQL par transaction et déploiement mono-worker.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#diffusion-et-verrous-réseau) :
  publication hors attente réseau et files du dernier état déjà implémentées.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#protection-des-entrées-publiques) :
  quotas existants, limites applicatives et limites de transport à distinguer.
- Cibles utiles : `app/domain/giveaway.py`, `app/application/commands.py`,
  `app/application/service.py`, `app/infrastructure/database.py`,
  `app/infrastructure/twitch.py`, `app/web/websocket.py`,
  `app/web/routes/health.py` et `app/web/static/plugins/giveaway/overlay.js`.
- Les contrôles SQL isolés et les sauvegardes complémentaires sont suivis dans
  [WI-0011](WI-0011-exploitation-durable.md), pas dupliqués ici.

### Périmètre et contraintes

- Cibles modifiables proposées : modules ci-dessus et documentation durable
  concernée, après approbation détaillée du cadrage.
- Mesurer avant de complexifier. Conserver l’architecture mono-worker et
  l’isolation des streamers ; Redis, microservices, pool SQL et workers multiples
  demandent un besoin mesuré et un arbitrage distinct.
- Utiliser uniquement une base PostgreSQL isolée et des données fictives.
  Distinguer spectateurs Twitch, messages/s, inscriptions/s et sources OBS.
- Les contrôles proposés sont locaux/isolés ; tout fichier de test ou script,
  toute charge, coupure ou intervention réelle demande l’accord prévu dans
  [AGENTS.md](../../AGENTS.md). La migration documentaire n’en autorise aucun.

### Dépendances

Base jetable et protocole de mesure à faire autoriser. Exploiter les résultats
pour le dimensionnement de WI-0011, sans faire dépendre les premières mesures
de sa clôture. La recette simultanée multi-streamer reste dans WI-0005.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Définir puis mesurer les étapes commandes/service/SQL/OBS sur la base isolée approuvée. | Latences, débits, mémoire et nombre de connexions sourcés ; coût d’une connexion et d’un commit par inscription. | Protocole borné à approuver avant toute charge ; aucune donnée réelle. |
| T02 | Indexer les participants par identifiant Twitch dans `app/domain/giveaway.py` si le diagnostic le justifie. | Recherche non linéaire sans changement de règles ni doublon. | Contrôles isolés de cohérence avant/après ; fichiers de tests sur accord spécifique. |
| T03 | Contrôler la cohérence mémoire/base et les transactions asynchrones dans `service.py` et `database.py`. | Inscriptions uniques persistées sans divergence ni rejeu de tirage. | Comparaison sur données fictives et scénarios d’échec autorisés. |
| T04 | Contrôler les diffusions, files bornées, délais et éviction des clients lents dans `app/web/websocket.py`. | Un client lent ne bloque ni les commandes ni les autres sources ; mémoire bornée. | Clients isolés et charge autorisée ; distinguer contrôles applicatifs et transport. |
| T05 | Définir puis implémenter la supervision TwitchIO et les sondes `live`/`ready` dans les modules Twitch et `app/web/routes/health.py`. | Sondes effectives distinguant disponibilité métier et simple réponse HTTP. | Revue du contrat avant implémentation, puis contrôles de panne isolés autorisés. |
| T06 | Adapter la reconnexion OBS et Twitch justifiée par les mesures, avec progression et jitter. | Reprise bornée sans rafale coordonnée ni changement des fermetures définitives. | Coupures simulées isolées sur accord ; vérifier les codes de fermeture existants. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Sur base jetable et livraison identifiée, exécuter le protocole de 10 000 inscriptions uniques autorisé. | Aucun doublon ni divergence mémoire/base ; débits et latences mesurés. | Version, protocole, nombre de lignes et mesures anonymisées. |
| R02 | Connecter plusieurs sources fictives dont une lente, avec le protocole approuvé. | Commandes et sources saines progressent ; files et mémoire bornées. | Mesures de latence/mémoire et résultat de l’éviction. |
| R03 | En environnement isolé, exercer indisponibilité Twitch/SQL et reprise autorisées. | Santé métier explicite, reprises progressives et absence de double tirage. | État avant/après, version et résultats sans secrets. |

## Suivi

### Approbation du cadrage

En attente de validation humaine du cadrage et des opérations précises. L’accord
de migration n’autorise ni charge ni création de tests/scripts.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Existant décrit dans l’architecture ; date/version non consignées ici | T04 | Partiellement implémenté, non validé sous charge | Files du dernier état, délais et publication hors attente réseau décrits ; aucune mesure nouvelle dans cette migration. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant exécution | Base jetable et protocole de charge | À autoriser | Cible, budget, charge et éventuels fichiers à approuver ; aucun essai lancé. |

### Validation finale

En attente d’implémentation restante, de mesures, de revue indépendante, de
recette, d’acceptation humaine et d’intégration identifiée. Aucune capacité de
10 000 spectateurs n’est démontrée par le critère de 10 000 inscriptions.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | L’ordre d’optimisation reste guidé par les mesures ; les choix d’infrastructure ne sont pas autorisés d’avance. | Cadrage détaillé et protocole à approuver dans une session dédiée. |
