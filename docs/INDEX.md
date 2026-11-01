# NecsusDevOverlays — Index des WI

L’usage est décrit dans [README.md](../README.md), l’existant technique dans
[docs/ARCHITECTURE.md](ARCHITECTURE.md) et les opérations dans
[docs/DEPLOY.md](DEPLOY.md). Cet index remplace la roadmap ; chaque WI porte son
cadrage, ses arbitrages, ses réalisations et ses preuves.

## Méthode

La méthode `ai-wi` privilégie des WI courts. Le
[docs/WI-TEMPLATE.md](WI-TEMPLATE.md) sert d'aide : garder seulement les champs
utiles, sans imposer de tableaux ni de rubriques vides.

- Cadrage : objectif, cibles et prérequis essentiels ; accord humain avant
  exécution ou changement de périmètre. Explorer d'abord les inconnues structurantes.
- Tâches IA ordonnées et recette humaine exhaustive en checklists : une ligne
  par action avec critère de réussite. La recette est l'unique liste humaine.
- Guide proposé dans la conversation au moment d'aborder une tâche humaine,
  avec accord avant manipulation ; aucun protocole détaillé généré d'avance.
- Suivi limité à l'état courant, la version utile, une preuve brève et les
  blocages ouverts. Cocher les résultats réellement obtenus ; relancer les
  validations concernées après une nouvelle livraison, sans journal historique.
- Une session d'exécution par WI, revue indépendante et sessions humaines
  distinctes ; références utiles par liens, sans duplication de contenu.

| Dossier | Usage |
| --- | --- |
| `docs/todo/` | Cadrage, approbation humaine, puis exécution autorisée. |
| `docs/validation/` | Livrable disponible ; revue et recette à terminer. |
| `docs/done/` | Revue conforme, recette réussie, acceptation et intégration identifiée. |

ID et nom `WI-XXXX-titre.md` stables ; prochain ID prévu : `WI-0014`, à vérifier
dans les trois dossiers. Template et index restent directement sous `docs/`.
Consulter les WI clos ou migrer d'autres WI uniquement sur demande.
Un accord documentaire n'autorise pas les opérations de recette.

## Priorités et états

Le recadrage documentaire du 2026-11-01 distingue le socle, les candidats produit
et la trajectoire entreprise. L'ordre conseillé du socle est **WI-0005 → WI-0011
→ WI-0003** : confirmer l'isolation existante, démontrer la restaurabilité, puis
mesurer la charge avant de décider des optimisations. La préparation des
protocoles peut avancer sans attendre les disponibilités de chaque recette.

Cet ordre n'est pas une dépendance technique générale ni une autorisation
opérationnelle. WI-0012/WI-0013 peuvent devenir prioritaires si un risque est
identifié. Les positions produit restent des choix humains ; aucun des onze
WI ouverts n'est autorisé à l'exécution par ce recadrage.

## À faire

| Position | WI | Type | Objectif et livrable | Dépendances et prérequis |
| --- | --- | --- | --- | --- |
| Socle 2 | [WI-0011 — Sauvegarde, restauration et cohérence de reprise](todo/WI-0011-exploitation-durable.md) | implementation | Procédure et preuves de restauration sur base séparée, états et reprise cohérents. | Sources/cibles isolées et opérations approuvées ; ne dépend pas des mesures WI-0003. |
| Socle 3 | [WI-0003 — Diagnostic de charge et capacité Giveaway](todo/WI-0003-stabilisation-charge.md) | exploration | Mesures reproductibles et décisions ; aucune optimisation dans ce WI. | Version, base jetable, cadence/durée, seuils, ressources et arrêt à approuver. |
| Transverse | [WI-0012 — Supervision et disponibilité métier](todo/WI-0012-supervision-metier.md) | implementation | Contrat et sondes HTTP/SQL/Twitch, dégradation observable et contrôles bornés. | Contrat de santé et protocole isolé ; mesures WI-0003 utiles, pas un verrou pour préparer le contrat. |
| Transverse | [WI-0013 — Contrôles opérateur post-déploiement](todo/WI-0013-controles-post-deploiement.md) | exploration | Dossier OAuth/OBS, proxy, Nginx/Certbot, exposition SQL et navigateur. | Livraison, cibles, créneaux et accords opérateur précis ; aucune modification du socle implicite. |
| Candidat produit suivant | [WI-0004 — Plugin Chat indépendant](todo/WI-0004-plugin-chat.md) | implementation | Chat OBS authentifié sans bloquer Giveaway ; modération conforme au contrat retenu. | Affichage et modération à arbitrer avant code ; WI-0005 avant usage externe simultané. |
| Produit conditionnel | [WI-0006 — Bibliothèque privée de styles CSS Giveaway](todo/WI-0006-styles-css-giveaway.md) | implementation | Sauvegarde personnelle, aperçu isolé et copie CSS ; partage hors V1. | Besoin/priorité, limites et sélecteurs à approuver ; isolation WI-0005. |
| Produit conditionnel | [WI-0007 — Alertes Points de chaîne](todo/WI-0007-points-de-chaine.md) | implementation | Utilisation de récompense affichée dans une source indépendante en lecture seule. | Besoin, faisabilité TwitchIO/OAuth, chaîne éligible et règle d'affichage ; WI-0005 avant usage externe. |
| Entreprise 1 | [WI-0010 — Campagnes : découverte et parcours métier](todo/WI-0010-campagnes-decouverte.md) | exploration | Un cas prioritaire et une décision étayée, y compris négative/inconclusive ; cinq pistes conservées. | Priorité entreprise, manager, périmètre/budget et données anonymisées autorisés. |
| Entreprise 2 | [WI-0009 — Campagnes : intégrations, attribution et sécurité](todo/WI-0009-campagnes-integrations.md) | conception | Contrat entrant `+1` du besoin qualifié ; garde-fous des extensions conservés hors conception détaillée. | Décision positive et cas réalisable WI-0010 ; règles et arbitrages humains. |
| Entreprise 3 | [WI-0008 — Campagnes : MVP et objectifs OBS](todo/WI-0008-campagnes-mvp.md) | implementation | Livraison technique événements/API/compteurs OBS sur données fictives ; pilote externe séparé. | Besoin WI-0010 et contrat WI-0009 approuvés ; aucune nécessité d'explorer les cinq pistes. |

La séquence entreprise est **WI-0010 → WI-0009 → WI-0008**, seulement si cette
trajectoire est priorisée. Une exploration négative/inconclusive peut être
clôturée après acceptation, mais ne débloque pas automatiquement contrat ou code.
La réussite technique du MVP n'est pas la validation d'un client ou du marché.

## En validation

| Position | WI | Livrable existant | Reste à confirmer |
| --- | --- | --- | --- |
| Socle 1 | [WI-0005 — Isolation multi-streamer](validation/WI-0005-multi-streamer.md) | Isolation annoncée comme implémentée ; document inchangé pendant le recadrage. | Revue indépendante, recette réelle simultanée sur deux chaînes, acceptation et intégration identifiée. |

Les validations ne changent pas de résultat par leur transfert : sauvegarde et
reprise restent dans WI-0011 ; ancien T05 de WI-0003 et ancien T01/R06 de WI-0011
sont dans WI-0012 ; anciennes R07 à R11 de WI-0011 sont dans WI-0013. Une preuve
peut être référencée entre WI seulement pour la même livraison et le même scénario.

## Suites conditionnelles à cadrer

Ces suites sont conservées dans leurs WI sources ; aucun ID supplémentaire
n'est créé avant priorisation et cadrage propres :

- Optimisations après diagnostic : index des participants, connexion/commit SQL
  ou reconnexion avec progression/jitter selon les preuves de WI-0003.
- Partage CSS après bibliothèque privée : visibilité, catalogue authentifié,
  duplication indépendante et retrait, décrits dans WI-0006.
- Pilote entreprise réel après MVP : ancienne R05 et prérequis conservés dans
  WI-0008 ; besoin/partenaire, restauration, isolation, supervision, contrôles
  pertinents, protection des données et accord du pilote à confirmer.
- Extensions campagnes : cinq pistes de WI-0010 et directions de WI-0008/0009,
  sans substituer import ou connecteur au MVP entrant sans arbitrage.
- Workflows réutilisables communs avec `geekom`, toujours à cadrer.

## Terminés — historique importé

| WI | Clôture rapportée par le document d’origine | Limite des preuves |
| --- | --- | --- |
| [WI-0001 — Migration PostgreSQL](done/WI-0001-postgresql.md) | Schéma v1 et mise en service PostgreSQL clôturés. | Date, version Git et référence détaillée de l’accord non consignées. |
| [WI-0002 — Giveaway chronométré](done/WI-0002-giveaway-chronometre.md) | Recette réelle Twitch → serveur → OBS confirmée par l’utilisateur. | Date, version Git et pièces de recette non consignées. |

Ces deux WI conservent leur clôture historique à la demande de l’utilisateur.
Le cycle ai-wi n’est pas certifié rétroactivement et aucune nouvelle recette n’a
été exécutée pendant la migration. Les contrôles reportés restent ouverts,
répartis après recadrage entre WI-0011, WI-0012 et WI-0013.

## Maintenir le suivi

Appliquer [AGENTS.md](../AGENTS.md). Reporter l’information durable dans le README,
l’architecture ou le guide de déploiement avant clôture ; les WI ouverts
référencent ces sources plutôt que les historiques terminés. Mettre à jour cet
index lors des déplacements et conserver les liens entre WI.

Ce dispositif est documentaire : aucun moteur d’exécution ni contrôle technique
du cadrage figé n’est installé.
