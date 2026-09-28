# ADR-0005 — Isolation multi-streamer

[← Roadmap](../ROADMAP.md)

**Statut :** implémentation ajoutée ; validation simultanée réelle restante.

## Contexte

Le socle OAuth existe, mais les ressources doivent être isolées pour plusieurs
chaînes actives.

## Décision ou orientation

Rattacher les données et les ressources actives à chaque streamer, avec contrôle
systématique de l’identité de session.

## Conséquences

Adapter les migrations, unicités et cycles de vie ; vérifier l’absence de
croisements après redémarrage.

## Travail associé et validation

À partir du socle OAuth et PostgreSQL existant. La migration v2 supprime les
giveaways PostgreSQL existants (données de test non conservées) ; identités et
clés OBS restent en place. L'architecture de la cible est décrite dans
[Architecture](../ARCHITECTURE.md).

Implémentation ajoutée :

- migration versionnée vers le propriétaire par giveaway et unicité par
  streamer ; les giveaways de test préexistants sont supprimés plutôt que mal
  attribués ;
- moteurs, services, minuteurs et connexions OBS isolés par streamer ;
- abonnements EventSub multiples restaurés avec le même bot ; une révocation
  désactive uniquement le routage du streamer concerné ;
- préfixe de commande par streamer et historique paginé avec détail participants
  et gagnants ;
- opérations SQL et accès API filtrés par identité de session, avec `404` pour
  une ressource appartenant à un autre streamer.

**Terminé quand :** deux chaînes utilisent simultanément des giveaways
indépendants, y compris après redémarrage, sans commandes, données ou
révocations croisées.
