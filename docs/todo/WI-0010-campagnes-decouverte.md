# WI-0010 — Campagnes entreprise — découverte et parcours métier

## Cadrage

**Type :** exploration

### Objectif

Qualifier avec le manager et une entreprise un pilote concret : objectifs,
déclencheurs, attribution, périodes, unicité et effort d’appel de l’API. Livrable :
synthèse anonymisée distinguant besoins confirmés, hypothèses et non-priorités,
sans développer les cinq parcours ni engager une offre commerciale.

### Contexte utile

- [WI-0008](WI-0008-campagnes-mvp.md) fixe le MVP par événements entrants.
- [WI-0009](WI-0009-campagnes-integrations.md) porte les contrats, l’attribution
  et les garde-fous ; la découverte fournit les arbitrages métier nécessaires.
- Les collaborations accessibles via le manager ouvrent des entretiens, pas
  une validation du marché ni une volonté de payer démontrée.
- Besoin explicitement exprimé : couvrir aussi les collaborations mensuelles
  hors jeu vidéo, notamment boutiques, avec commandes payées, acheteurs uniques,
  montants cumulés et actions personnalisées. Le mécanisme d’attribution reste
  à confirmer partenaire par partenaire.
- Les cinq pistes ci-dessous sont exploratoires, peuvent se recouper et ne
  constituent ni un ordre de développement ni un classement des usages.

### Périmètre et contraintes

- Cibles : éléments anonymisés fournis avec autorisation, synthèse de découverte
  et décisions dans le suivi du présent WI, propositions aux cadrages non figés
  WI-0008/WI-0009. Aucun connecteur, SDK, portail ou code de campagne ici.
- Reconstituer une collaboration passée avec brief/bilan anonymisés : objectifs,
  engagements streamer, outils, données obtenues, tâches manuelles et décision
  finale. Garder contrats, secrets et données personnelles hors dépôt.
- Entretiens progressifs à partir d’une campagne réelle : résultat voulu,
  mesure disponible, manque, interlocuteur pouvant fournir les données et effort.
  Distinguer entreprise acheteuse, manager opérateur, intégrateur et streamer.
- Classer les besoins en hypothèses / confirmés / non prioritaires, avec contexte
  anonymisé et contradictions. Une catégorie non interrogée reste non explorée ;
  un seul pilote ne valide pas un segment entier.
- Choisir selon besoin concret, accès aux données, effort et calendrier. Faire
  approuver un exemple fictif de bilan/objectifs OBS avant les connecteurs ;
  séparer aide à la décision entreprise et animation de la communauté.
- L’exploration des extensions ne bloque pas le MVP entrant. Si l’entreprise
  ne peut pas envoyer d’événements, étudier l’import comme extension et demander
  un arbitrage avant toute substitution du MVP.
- Aucun accès à un compte partenaire, collecte externe, engagement commercial,
  fichier de test/script ou opération réelle n’est autorisé par cette migration.

**Parcours A — Studios indépendants sur Steam :**

- Hypothèse : montrer l’intérêt d’une collaboration (wishlists, démos si
  mesurables, achats) sans intégrer le jeu. Identifier phase annonce,
  pré-lancement, démo ou lancement, indicateur principal et disponibilité réelle
  dans les rapports du studio.
- Explorer liens UTM par campagne/streamer/emplacement et import d’export CSV
  Steamworks avec aperçu, colonnes validées et réimport idempotent. Ne pas
  présumer une API adaptée ni demander les identifiants Steam du studio.
- Bilan séparant clics de nos liens, visites et conversions Steam, avec date
  de mise à jour et caractère différé. Comparaisons/coûts par résultat seulement
  avec coûts et dénominateurs disponibles/comparables ; ne pas déduire les
  ventes futures des wishlists.
- Contrainte documentaire à revérifier au pilote dans la
  [documentation Steamworks](https://partner.steamgames.com/doc/marketing/utm_analytics?l=english) :
  résultats UTM agrégés et CSV, visites à l’heure, conversions finalisées quatre
  jours après visite, exclusions de confidentialité/seuils et fenêtre de
  conversion de 72 heures. Ce ne sont pas des capacités testées ici.
- Première valeur proposée : bilan réconcilié avec un export autorisé, distinguant
  attribué, manquant et provisoire, sans intégration dans le jeu.

**Parcours B — Éditeurs de jeux avec backend :**

- Hypothèse : joueurs qualifiés et objectifs OBS alimentés par des actions dans
  le jeu plutôt que simples clics. Choisir compte créé, tutoriel terminé,
  première partie ou niveau, en distinguant actions/personnes uniques et lien
  entre attribution et action.
- Utiliser le MVP entrant authentifié et plusieurs objectifs ; le backend
  entreprise reste la référence. Comparer à un extrait agrégé autorisé et
  traiter répétitions, annulations, pertes d’attribution et délais ; séparer
  reçu/confirmé seulement selon les statuts effectivement fournis.
- Parcours de conversion ou retour des joueurs uniquement pour une décision
  client avec données accessibles ; pas de SDK multi-moteurs sans besoin prouvé.
- Première valeur proposée : bon objectif alimenté par une action confirmée,
  bilan cohérent avec la source, effort mesuré et absence de double comptage.

**Parcours C — Éditeurs de jeux mobiles :**

- Hypothèse : exploiter l’outil d’attribution existant, par exemple AppsFlyer ou
  Adjust, sans second SDK. Identifier exports/API autorisés, dimensions par
  campagne/créateur, coûts, confidentialité et contraintes contractuelles avant
  toute promesse de connecteur.
- Garder si possible liens et IDs existants ; vérifier qu’une redirection ne
  casse ni ouverture d’application, boutique ni attribution.
- Envisager d’abord installations attribuées et action qualifiante par fichier
  ou API selon le pilote. Conserver règles, fenêtres, délais et données absentes
  de la source, sans contournement des protections de plateforme.
- Rétention par cohorte/ROAS seulement sur demande avec période, coûts inclus,
  revenus, devise et maturité définis. Revenus attribués, bénéfice et impact
  causal ne sont pas équivalents.
- Première valeur proposée : bilan compatible avec les rapports existants,
  sans nouveau SDK, et seuls agrégats approuvés/fraîcheur publiés dans OBS.

**Parcours D — Agences et managers :**

- Hypothèse : réduire préparation et consolidation multi-streamer. Décrire
  brief, liens, engagements, collecte ; mesurer temps et erreurs avant automatisation.
- Envisager une vue campagne/streamer avec liens, objectifs, résultats sourcés
  et preuves autorisées (replay, extrait ou bilan). Séparer réalisation
  contractuelle, exposition et conversion ; pas de vérification automatique du
  contenu annoncée.
- Bilan exportable et accès client limité ; délégations agence → entreprise →
  campagne sans accès global interentreprises. Protéger budgets et conditions
  individuelles des streamers.
- Comparer seulement définitions, périodes et sources compatibles ; signaler
  les manques plutôt que fabriquer un classement. Automatiser ensuite les
  collectes et modèles réellement répétitifs.
- Première valeur proposée : bilan accepté par le client avec moins de travail
  manuel mesuré, sans mélange de clients ou divulgation des conditions privées.

**Parcours E — Boutiques et collaborations mensuelles :**

- Besoin exprimé, pas intégration déjà validée : commandes payées, clients
  uniques, montants et actions personnalisées. Accepter code promotionnel,
  lien ou règle interne selon le partenaire, sans imposer une attribution.
- Identifier le déclencheur de confirmation et l’appel serveur vers notre API.
  Webhook existant ou outil serveur si conforme au contrat ; pas de connecteur
  natif Shopify/WooCommerce promis sans besoin confirmé.
- Commencer par commande payée et référence opaque : plusieurs notifications,
  même avec IDs d’événement différents, ne font pas plusieurs ventes. Acheteurs
  uniques : ID opaque ou garantie d’unicité entreprise, sans coordonnées client
  ni détail de panier.
- Mois civil ou dates contractuelles, fuseau et bornes non chevauchantes à
  décider. Nouvelle période sans effacer l’ancienne, définitions/cibles
  historiques figées et date métier distincte de réception ; règle explicite
  de retard et clôture.
- Montants ultérieurs : HT/TTC, port, remises, statut de paiement et devise
  convenus ; représentation exacte, pas d’addition de devises sans conversion
  explicite. Distinguer brut de commandes, ventes nettes et bénéfice.
- Annulations/remboursements partiels ou complets référencent la commande,
  sont dédupliqués et historisés. Décider correction de période d’origine ou
  ajustement courant, effets sur commandes/clients uniques ; ne pas retirer
  toute une commande pour chaque remboursement partiel.
- Recette envisagée pour une future extension : changement de mois, même
  commande par code+lien, notification répétée, client avec plusieurs commandes,
  retard et remboursement d’un mois précédent. Distinguer montant publiable
  OBS et données réservées au partenaire/manager.
- Première valeur proposée : commande comptée une fois au bon objectif,
  streamer et mois, avec historique préservé. Extension clients/montants validée
  seulement après réconciliation avec les résultats boutique et ajustements
  convenus, sans données client divulguées.

**Offre commerciale — hypothèses hors engagement :**

- Socle proposé : cadrage, liens et bilan sourcé ; options possibles OBS,
  intégration des conversions, consolidation multi-streamer et suivi différé.
  Ni offre ni tarifs validés.
- Avec le manager, préciser inclus/optionnel/sur devis : configuration, CSS,
  intégration, accompagnement, fréquence et suivi après campagne. Mesurer le
  coût opérationnel avant prix.
- Exposer prérequis et effort entreprise ; ne pas vendre du direct si la source
  ne fournit que du différé. Valider l’intérêt OBS séparément du bilan.
- Pas de nombre de ventes promis, attribution exhaustive ou ROI garanti.
  Définir démonstration, option incluse ou prestation payante avec accord
  explicite ; recueillir utilité et décision de renouvellement.

### Dépendances

Disponibilité du manager et d’un partenaire, autorisation des éléments
anonymisés. Aucun développement des cinq parcours ni clôture technique de
WI-0008/WI-0009 n’est nécessaire pour commencer les entretiens.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Préparer une grille de reconstitution d’une collaboration et des questions par interlocuteur dans le suivi. | Objectif, outils, données, travail manuel et décision documentables. | Revue documentaire, exemples fictifs seulement. |
| T02 | Analyser les éléments anonymisés explicitement fournis et autorisés. | Synthèse sourcée, manques et contradictions visibles, sans données personnelles. | Contrôle de provenance et de minimisation ; aucun contrat ou secret réel lu. |
| T03 | Structurer les retours des catégories effectivement interrogées. | Hypothèses, confirmés, non-priorités et non-explorés clairement distincts. | Confrontation aux retours humains autorisés, sans étude de marché inventée. |
| T04 | Comparer les candidats selon besoin, données, effort et calendrier. | Proposition de pilote et inconnues structurantes à arbitrer. | Revue documentaire avec manager ; aucun choix client pris à sa place. |
| T05 | Préparer un bilan et des objectifs OBS fictifs, puis formaliser les décisions du pilote. | Déclencheurs, attribution, périodes, unicité et effort d’API approuvables. | Validation humaine des maquettes ; aucune intégration ni appel réel. |
| T06 | Reporter les arbitrages autorisés aux cadrages WI-0008/WI-0009 non figés et consigner les extensions séparément. | MVP préservé et suites identifiées sans engagement commercial implicite. | Relecture des périmètres et références d’accord ; WI complémentaire après gel. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Avec le manager, reconstruire une collaboration depuis des éléments anonymisés autorisés. | Problème, travail manuel, données et décision finale explicités. | Synthèse anonymisée approuvée, validateur et date. |
| R02 | Interroger progressivement les interlocuteurs utiles et relire leur synthèse. | Besoins et contradictions distingués des hypothèses ; catégories non explorées signalées. | Retours autorisés et classement approuvé, sans preuve de marché généralisée. |
| R03 | Choisir un pilote et définir objectifs, déclencheurs, attribution, périodes, unicité et effort de l’appel serveur. | Partenaire et périmètre réalisables, ou blocage explicite demandant un arbitrage. | Décision manager/entreprise et référence de l’accord. |
| R04 | Faire relire bilan/objectifs fictifs et limites de l’offre. | Utilité bilan/OBS distincte, effort et éventuelles conditions commerciales explicitement décidés. | Retours et acceptation du pilote ; aucune tarification inventée. |

## Suivi

### Approbation du cadrage

En attente de validation humaine du protocole d’exploration. Les besoins
explicitement exprimés sont conservés, sans qualifier les autres hypothèses de
validées ni approuver des engagements commerciaux.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant exploration | Interlocuteurs et éléments anonymisés | À autoriser | Manager, partenaire et documents partageables à identifier ; aucun entretien réalisé par la migration. |

### Validation finale

Terminé lorsque manager et entreprise pilote ont confirmé les paramètres de
R03 et relu le livrable, avec revue indépendante, acceptation et intégration
identifiée. Ce résultat ne valide ni tous les segments ni le fonctionnement de
l’API. Une alternative par import attend un arbitrage explicite.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | Conserver les cinq pistes et le besoin boutique sans transformer la découverte en développement de connecteurs. | Cadrage d’exploration à approuver ; aucun changement du MVP autorisé par la migration. |
