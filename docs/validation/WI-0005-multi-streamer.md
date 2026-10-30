# WI-0005 — Isolation multi-streamer

## Cadrage

**Type :** implementation

### Objectif

Confirmer qu’un bot global peut desservir deux chaînes actives simultanément
sans croiser commandes, données, sessions ni accès OBS. L’implémentation est
rapportée comme disponible ; le livrable restant est sa revue et sa recette réelle.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#authentification-et-isolation) :
  identités Twitch stables, sessions, clés OBS et révocations.
- `app/main.py` : contextes métier par streamer.
- `app/web/dependencies.py`, `app/application/streamer_access.py` : admission
  administrative et contrôle des comptes activés.
- `app/infrastructure/history.py`, `app/infrastructure/overlay_access.py`,
  `app/web/routes/admin.py`, `app/web/routes/overlay.py` et
  `app/web/websocket.py` : propriété, persistance et diffusion ciblée.
- `app/infrastructure/twitch.py` : routage du chat et abonnements par chaîne.

### Périmètre et contraintes

- Cibles de la recette : livrable existant, deux identités et deux chaînes
  autorisées, clés distinctes et données temporaires.
- Rattacher données et ressources à l’ID Twitch stable ; le navigateur ne
  décide jamais du propriétaire. Un bot global, sans second bot.
- La revue documentaire est distincte de la recette réelle. Identifier d’abord
  la version déployée et faire autoriser manipulations, rotations, révocation
  et redémarrage. Préserver les secrets et les autres utilisateurs.
- Aucune correction applicative n’est exécutée par ce WI pendant la migration.
  Une correction conforme au cadrage utilise une nouvelle session ; une
  évolution de périmètre appelle un WI complémentaire.

### Dépendances

Implémentation existante et disponibilité de deux chaînes/identités pour une
recette autorisée. Aucune clôture d’un autre WI n’est requise pour préparer la
revue ; la recette dépend de l’environnement identifié et disponible.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Relire le routage dans `app/main.py` et `app/infrastructure/twitch.py`. | Chaque commande atteint uniquement le contexte du streamer identifié. | Revue indépendante ciblée, sans connexion réelle non autorisée. |
| T02 | Relire les contrôles de propriété et les filtres SQL des modules d’accès et d’historique. | Session et clé OBS bornées à leur propriétaire ; comptes désactivés refusés. | Revue des accès directs, rotations et erreurs ; aucun secret lu. |
| T03 | Préparer la recette des contextes, révocations et restaurations simultanés. | Protocole R01 à R04 applicable à une version identifiée. | Accord humain avant toute manipulation réelle ou création de tests/scripts. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Avec deux chaînes actives, utiliser commandes, préfixes, inscriptions, tirages et historique distincts. | Participants, résultats, préférences et affichages indépendants. | Version et matrice des résultats des deux chaînes, sans secrets. |
| R02 | Depuis une identité, tenter l’accès direct à une ressource de l’autre, puis exercer désactivation et révocation de session autorisées. | Accès croisés refusés et sessions révoquées selon le contrat existant. | Requêtes/résultats expurgés et identité du validateur. |
| R03 | Faire tourner une clé OBS puis révoquer un abonnement EventSub autorisé sur une chaîne. | Effets limités au propriétaire et au type d’accès concernés ; autre chaîne intacte. | Résultats avant/après, sans clés ni tokens. |
| R04 | Avec deux giveaways et leurs minuteurs, effectuer un redémarrage autorisé. | Deux états et échéances restaurés sans commande ni tirage croisé. | États et résultats observés après reprise. |

## Suivi

### Approbation du cadrage

Le document d’origine annonçait l’implémentation terminée, mais ne consignait
pas l’approbation détaillée ni la version livrée. L’accord de migration autorise
le classement en `validation/`, pas l’exécution de la recette. Faire approuver
le protocole et identifier la livraison avant les manipulations.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Existant, date et version non consignées dans la source | T01, T02 | Implémentation rapportée ; revue indépendante en attente | Isolation décrite dans l’architecture ; aucune revue séparée ou recette simultanée exécutée pendant la migration. |
| 2026-10-30, migration documentaire sans livraison applicative | T03 | Protocole proposé | R01 à R04 reprennent les validations restantes ; approbation et exécution en attente. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Livraison existante à identifier | Préparation : version, deux chaînes et protocole autorisé | En attente | Version et accord opérationnel non consignés. |
| Livraison existante à identifier | R01 | À effectuer | Aucun résultat simultané confirmé dans la source. |
| Livraison existante à identifier | R02 | À effectuer | Preuves d’accès directs et révocations à recueillir. |
| Livraison existante à identifier | R03 | À effectuer | Effets isolés des rotations et révocations à confirmer. |
| Livraison existante à identifier | R04 | À effectuer | Restauration simultanée des deux contextes à confirmer. |

### Validation finale

En attente de revue indépendante, de recette réelle simultanée, d’acceptation
humaine et de référence d’intégration. Terminé lorsque R01 à R04 sont conformes
sur la même livraison identifiée, sans donnée, commande ou révocation croisée.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Utilisateur et assistant | L’implémentation annoncée ne vaut pas recette ; conserver ce WI dans `validation/`. | Conversation courante : accord « go » sur le classement ai-wi, sans approbation opérationnelle. |
