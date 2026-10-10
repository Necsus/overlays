# ADR-0003 — Stabilisation sous charge

[← Roadmap](../ROADMAP.md)

**Statut :** orientation retenue ; mesures et validations restantes.

## Contexte

Les inscriptions, transactions et diffusions doivent rester cohérentes sous
charge.

## Décision ou orientation

Mesurer avant de complexifier ; borner les ressources et isoler les clients
lents.

## Conséquences

Ne pas ajouter Redis, microservices, pool SQL ou workers multiples sans besoin
mesuré. Le modèle SQL (une connexion par transaction, pas de pool sans mesure)
est celui de l'[architecture](../ARCHITECTURE.md#données-et-configuration) ;
les contrôles isolés et les sauvegardes sont dans
[ADR-0011](0011-exploitation-durable.md).

## Travail associé et validation

Ordre proposé, à ajuster aux mesures :

1. Mesurer message → commande → transaction → OBS sur une base PostgreSQL isolée
   avec des données fictives.
2. Indexer les participants par identifiant Twitch pour éviter les recherches
   linéaires.
3. Valider sous charge la cohérence mémoire/base et l'accès SQL asynchrone déjà
   implémenté ; mesurer le coût d'une connexion et d'un commit par inscription.
4. Valider sous charge la publication hors attente réseau et les files bornées
   du dernier état, désormais [implémentées](../ARCHITECTURE.md#diffusion-et-verrous-réseau).
5. Valider les budgets d'envoi/fermeture et l'éviction des clients lents, ainsi
   que les [quotas et limites de messages implémentés](../ARCHITECTURE.md#protection-des-entrées-publiques).
6. Superviser TwitchIO, ajouter `live`/`ready` et une reconnexion progressive
   avec jitter.

**Critères :** 10 000 inscriptions uniques persistées sans divergence ni
doublon. Un OBS lent ne bloque pas les commandes. Files et mémoire restent
bornées. Les spectateurs Twitch ne sont pas des connexions directes au serveur :
mesurer messages/s, inscriptions/s et nombre de sources OBS séparément.

Toute création de tests ou scripts de charge nécessite l'accord prévu dans
[AGENTS.md](../../AGENTS.md).
