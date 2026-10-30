# WI-0002 — Validation du giveaway chronométré

## Cadrage

**Type :** implementation

### Objectif

Livrer la recette réelle du minuteur déjà implémenté, de Twitch au serveur puis
à OBS. Le contrôle isolé du mode manuel ne suffisait pas à valider ce parcours.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#cohérence-du-giveaway) décrit
  l’échéance persistée et l’autorité du serveur.
- [app/application/service.py](../../app/application/service.py) orchestre les
  mutations et le minuteur.
- [app/web/static/plugins/giveaway/giveaway-renderer.js](../../app/web/static/plugins/giveaway/giveaway-renderer.js)
  rend notamment le compteur OBS.
- La source déclarait une validation réelle confirmée par l’utilisateur ; ce
  travail ne constituait pas une nouvelle décision d’architecture.

### Périmètre et contraintes

- Cibles historiques : protocole de recette et résultats du giveaway chronométré.
- Vérifier échéances, annulations et reprises dans OBS, avec CSS personnalisé.
- Le type `implementation` désigne ici la livraison du protocole et de sa
  recette, pas l’ajout d’un nouveau minuteur.
- Aucune commande Twitch, modification de giveaway, coupure ou relance de
  service n’est autorisée aujourd’hui par cet historique.

### Dépendances

Stockage et release PostgreSQL historiques de WI-0001. Les règles actuelles sont
celles de l’architecture ; la recette passée ne valide pas chaque version future.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Définir les scénarios de recette du minuteur et du rendu OBS. | Protocole couvrant affichage, échéance, annulation et reprise. | Reconstruction documentaire depuis les scénarios clôturés ; aucune exécution actuelle. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Avec le CSS personnalisé OBS, ouvrir puis terminer un giveaway chronométré. | Compteur visible puis effacé au bon moment. | Observation Twitch/OBS de la livraison concernée. |
| R02 | Exercer tirage à échéance, gagnants supplémentaires et cas sans participant. | Résultats et affichage cohérents dans les trois cas. | Résultat de chaque scénario. |
| R03 | Annuler par tirage manuel ou arrêt, puis définir un nouveau lot sans minuteur. | Ancien minuteur sans effet ; nouveau lot conforme. | Observation des annulations et du nouveau lot. |
| R04 | Redémarrer avec une échéance future puis dépassée. | Reprise conforme de l’état et du tirage attendu. | Observation après chaque redémarrage. |

## Suivi

### Approbation du cadrage

Historique importé : confirmation utilisateur rapportée, sans date ni référence
précise de l’accord initial. La migration ne certifie pas une approbation
rétroactive du cadrage ai-wi.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Historique, date et version non consignées | T01 | Scénarios présents dans la source | Les quatre groupes de scénarios étaient cochés comme terminés ; attribution de leur préparation non consignée. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Historique, version non consignée | R01 | Confirmé dans la source | Affichage/disparition du compteur avec CSS personnalisé ; confirmation utilisateur ; date et pièces non consignées. |
| Historique, version non consignée | R02 | Confirmé dans la source | Échéance, gagnants supplémentaires et cas vide passent ; confirmation utilisateur ; date et pièces non consignées. |
| Historique, version non consignée | R03 | Confirmé dans la source | Annulations et nouveau lot sans minuteur passent ; confirmation utilisateur ; date et pièces non consignées. |
| Historique, version non consignée | R04 | Confirmé dans la source | Reprise après redémarrage, échéance dépassée comprise ; confirmation utilisateur ; date et pièces non consignées. |

### Validation finale

Clôture historique conservée en `done/` : les scénarios étaient déclarés
conformes de bout en bout Twitch → serveur → OBS. Version, date, pièces de
recette, revue indépendante et référence d’intégration non consignées. Aucun
scénario n’a été rejoué pendant cette migration.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Utilisateur et assistant | Préserver la validation réelle rapportée sans créer de nouvelles preuves. | Conversation courante : archives vers `done/`, puis accord « go » sur le plan ai-wi. |
