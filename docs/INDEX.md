# NecsusDevOverlays — Index des WI

L’usage est décrit dans [README.md](../README.md), l’existant technique dans
[docs/ARCHITECTURE.md](ARCHITECTURE.md) et les opérations dans
[docs/DEPLOY.md](DEPLOY.md). Cet index remplace la roadmap ; chaque WI porte son
cadrage, ses arbitrages, ses réalisations et ses preuves.

## Méthode

La méthode reprend `ai-wi` : une intention vérifiable par fichier, tâches IA
ordonnées, recette définie dès le cadrage et suivi par livraison. Le
[docs/WI-TEMPLATE.md](WI-TEMPLATE.md) est la copie du template de référence.
Conserver exactement ses titres, leur ordre et les colonnes des tableaux.

Adaptation locale : `todo/`, `validation/`, `done/`, le template et cet index sont
directement sous `docs/`, sans dossier intermédiaire `wis/`.

| Dossier | Usage |
| --- | --- |
| `docs/todo/` | Cadrage, approbation humaine, puis exécution autorisée. |
| `docs/validation/` | Livrable implémenté ; revue indépendante et recette humaine à terminer. |
| `docs/done/` | Revue conforme, recette réussie, acceptation humaine et intégration réalisées ; historiques importés signalés ci-dessous. |

L’ID et le nom `WI-XXXX-titre.md` restent stables pendant les déplacements.
Le prochain ID disponible après cette migration est `WI-0012` ; vérifier les
trois dossiers avant toute attribution.

L’approbation humaine d’un WI fige `Cadrage`. `Suivi` et `Commentaires et
arbitrages` restent éditables ; une évolution du périmètre appelle un WI
complémentaire après arbitrage humain. Une inconnue structurante appelle un WI
préalable d’exploration ou de conception. L’accord sur cette migration
n’approuve ni les cadrages détaillés ni l’exécution des travaux futurs.

Une session d’exécution traite un seul WI. La revue utilise une session distincte
et confronte le livrable au cadrage, aux preuves et aux règles d’architecture.
Les tâches humaines ont leurs propres sessions. Un blocage conserve le fichier
dans son dossier et ouvre un commentaire avec le constat et la décision attendue.

À chaque livraison, consigner sa version et les résultats dans `Suivi`, puis
ajouter une tâche humaine par point de recette. Chaque résultat indique preuve,
validateur et date. Une nouvelle livraison ajoute des entrées et relance revue
et recette pour cette version, sans effacer l’historique. La liste globale des
tâches humaines est la réunion des suivis des WI, pas une seconde liste ici.

Utiliser les IDs des WI et des références identifiées par leur chemin depuis la
racine du projet ; les liens Markdown sont relatifs au fichier pour rester
navigables. Les décisions humaines sont datées, attribuées et liées à l’accord
explicite. Une information absente de l’historique est notée « non consignée »,
jamais reconstituée comme une preuve.

## À faire

L’ordre reprend les priorités existantes ; une dépendance ou un arbitrage peut
bloquer l’exécution sans empêcher le cadrage.

| Ordre | WI | Type | Objectif et livrable | Dépendances et prérequis |
| --- | --- | --- | --- | --- |
| 0 | [WI-0003 — Stabilisation sous charge](todo/WI-0003-stabilisation-charge.md) | implementation | Mesures et améliorations ciblées démontrant cohérence et ressources bornées. | Base jetable et protocole de charge autorisés. |
| 1 | [WI-0004 — Plugin Chat indépendant](todo/WI-0004-plugin-chat.md) | implementation | Source Chat authentifiée indépendante de Giveaway. | Choix d’affichage ; recette WI-0005 avant usage externe. |
| 3 | [WI-0006 — Bibliothèque de styles CSS Giveaway](todo/WI-0006-styles-css-giveaway.md) | implementation | Bibliothèque privée/partagée avec copie et aperçu isolé. | Limites et sélecteurs ; isolation WI-0005. |
| 4 | [WI-0007 — Alertes Points de chaîne](todo/WI-0007-points-de-chaine.md) | implementation | Récompense personnalisée affichée dans une source OBS en lecture seule. | Arbitrage d’affichage, consentement Twitch et isolation WI-0005. |
| 5 | [WI-0008 — Campagnes : MVP et objectifs OBS](todo/WI-0008-campagnes-mvp.md) | implementation | Événements entreprise idempotents et compteurs persistants par période. | Contrat WI-0009 ; WI-0005, WI-0010 et WI-0011 avant pilote externe. |
| 6 | [WI-0009 — Campagnes : intégrations, attribution et sécurité](todo/WI-0009-campagnes-integrations.md) | conception | Contrat du MVP, droits et règles d’attribution vérifiables. | Besoins et arbitrages du pilote, explorés dans WI-0010. |
| 7 | [WI-0010 — Campagnes : découverte et parcours métier](todo/WI-0010-campagnes-decouverte.md) | exploration | Besoins qualifiés et pilote sélectionné, sans développer les cinq parcours. | Disponibilité du manager et d’une entreprise ; données anonymisées autorisées. |
| 8 | [WI-0011 — Exploitation durable](todo/WI-0011-exploitation-durable.md) | implementation | Procédure de restauration et contrôles de panne/exploitation vérifiables. | Base jetable ; mesures WI-0003 pour le dimensionnement ; accords opérationnels. |

WI-0008, WI-0009 et WI-0010 constituent un seul chantier. La découverte peut
commencer avant les autres développements ; les extensions ne remplacent pas le
MVP par événements entrants. Les workflows réutilisables communs avec `geekom`
restent à cadrer, sans être autorisés par la migration.

## En validation

| Ordre | WI | Livrable existant | Reste à confirmer |
| --- | --- | --- | --- |
| 2 | [WI-0005 — Isolation multi-streamer](validation/WI-0005-multi-streamer.md) | Isolation annoncée comme implémentée. | Revue indépendante, recette réelle simultanée sur deux chaînes, acceptation et intégration identifiée. |

Les autres validations post-déploiement précédemment dans la roadmap sont
reprises dans les tâches humaines de WI-0011 : OAuth/OBS, confiance proxy,
Nginx, certificat, exposition PostgreSQL, administration et `robots.txt`.

## Terminés — historique importé

| WI | Clôture rapportée par le document d’origine | Limite des preuves |
| --- | --- | --- |
| [WI-0001 — Migration PostgreSQL](done/WI-0001-postgresql.md) | Schéma v1 et mise en service PostgreSQL clôturés. | Date, version Git et référence détaillée de l’accord non consignées. |
| [WI-0002 — Giveaway chronométré](done/WI-0002-giveaway-chronometre.md) | Recette réelle Twitch → serveur → OBS confirmée par l’utilisateur. | Date, version Git et pièces de recette non consignées. |

Ces deux WI conservent leur clôture historique à la demande de l’utilisateur.
Le cycle ai-wi n’est pas certifié rétroactivement et aucune nouvelle recette n’a
été exécutée pendant la migration. Les contrôles reportés restent dans WI-0011.

## Maintenir le suivi

Appliquer [AGENTS.md](../AGENTS.md). Reporter l’information durable dans le README,
l’architecture ou le guide de déploiement avant clôture ; les WI ouverts
référencent ces sources plutôt que les historiques terminés. Mettre à jour cet
index lors des déplacements et conserver les liens entre WI.

Ce dispositif est documentaire : aucun moteur d’exécution ni contrôle technique
du cadrage figé n’est installé.
