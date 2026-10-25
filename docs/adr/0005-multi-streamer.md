# ADR-0005 — Isolation multi-streamer

[← Roadmap](../ROADMAP.md)

**Statut :** implémenté ; validation simultanée réelle restante.

## Décision

Rattacher données et ressources actives à l’identité Twitch stable du streamer.
Un bot global dessert les chaînes ; les accès web et OBS ne doivent jamais
croiser leurs propriétaires. L’existant est décrit dans
[l’architecture](../ARCHITECTURE.md#authentification-et-isolation).

## Validation restante

Avec deux chaînes actives simultanément, vérifier :

- commandes, préfixes, participants, résultats et historique indépendants ;
- refus des accès directs à une ressource de l’autre propriétaire ;
- rotation d’une clé OBS et révocation EventSub sans effet sur l’autre chaîne ;
- restauration des deux giveaways et de leurs minuteurs après redémarrage.

**Terminé quand :** ces parcours sont confirmés en conditions réelles, sans
commande, donnée ou révocation croisée.
