# WI-0001 — Migration PostgreSQL

## Cadrage

**Type :** implementation

### Objectif

Remplacer SQLite par PostgreSQL sans changer le comportement Twitch, Giveaway
et OBS. Livrable historique : schéma v1, stockage asynchrone et release sur
PostgreSQL.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#données-et-configuration) décrit le
  stockage actuel, désormais en schéma v2 ; ce WI décrit la migration v1 passée.
- [app/infrastructure/database.py](../../app/infrastructure/database.py) porte
  les connexions Psycopg et les migrations explicites.
- [app/infrastructure/history.py](../../app/infrastructure/history.py) porte la
  persistance des giveaways.
- Le document d’origine rapportait une autorisation utilisateur de départ à
  vide et de suppression du jeu de test SQLite, sans nouveaux fichiers de tests.

### Périmètre et contraintes

- Cibles historiques : stockage applicatif, schéma v1 et dépendances de release.
- Psycopg 3 asynchrone, une connexion par transaction, migrations versionnées,
  sans ORM ni pool ; un seul worker.
- Les anciens historiques et liens OBS n’ont pas été repris. La migration du
  stockage était distincte de l’évolution multi-streamer.
- Les opérations historiques ne constituent aucune autorisation de suppression,
  migration ou déploiement aujourd’hui. Aucun de ces parcours n’est rejoué par
  la migration documentaire.

### Dépendances

Prérequis historiques : base et rôle dédiés, dépendances PostgreSQL en release
et développement. La recette chronométrée est le travail historique WI-0002.
Les contrôles SQL isolés, clés OBS, coupures et sauvegardes ont été reportés dans
[WI-0011](../todo/WI-0011-exploitation-durable.md).

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Adapter le stockage et les migrations au schéma PostgreSQL v1. | Code et schéma livrés sans reprise SQLite. | Historique seulement ; aucune migration actuelle. |
| T02 | Adapter les dépendances de release et de développement. | Application utilisable avec PostgreSQL. | Constats historiques de mise en service ; aucun déploiement actuel. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Sur la release historique, vérifier la migration no-op en version 1, `libpq` et le rôle applicatif. | Release NixOS et dev zsh fonctionnelles ; rôle propriétaire de la base dédiée sans Superuser. | Confirmation utilisateur rapportée dans le document d’origine. |
| R02 | Exercer le giveaway chronométré dans Twitch et OBS. | Parcours de bout en bout conforme. | Résultat historique de WI-0002. |

## Suivi

### Approbation du cadrage

Historique importé : autorisation de départ à vide rapportée par le document
d’origine. Approbateur : utilisateur ; date et référence précise de l’accord
non consignées. Ce cadrage reconstruit n’est pas présenté comme approuvé
rétroactivement selon ai-wi.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Historique, schéma v1 ; date et version Git non consignées | T01 | Clôturé dans la source | Code, schéma et release PostgreSQL rapportés comme livrés ; non réexécutés ici. |
| Historique, version Git non consignée | T02 | Clôturé dans la source | Dépendances de release/dev rapportées comme opérationnelles ; attribution IA détaillée non consignée. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Release PostgreSQL v1 historique | R01 | Confirmé dans la source | Mise en service, migration no-op, `libpq` et rôle confirmés par l’utilisateur ; date et pièces non consignées. |
| Release historique, version non consignée | R02 | Confirmé dans la source | Parcours chronométré confirmé par l’utilisateur ; détail dans WI-0002 ; date non consignée. |

### Validation finale

Clôture historique conservée en `done/`. La source déclarait l’implémentation et
le schéma v1 clôturés ; les preuves de revue séparée, d’intégration Git et la
date d’acceptation ne sont pas consignées. Aucune nouvelle validation n’a eu lieu.
Les contrôles reportés restent dans WI-0011.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| Non consignée dans la source | Utilisateur, rapporté par le document d’origine | Départ à vide sans import des historiques ni liens OBS. | Autorisation historique rapportée ; référence détaillée absente. |
| 2026-10-30 | Utilisateur et assistant | Conserver les conclusions et les limites de preuve sans rejouer la migration. | Conversation courante : demande de déplacer les documents archivés dans `done/`, puis accord « go » sur le plan ai-wi. |
