# WI-0008 — Campagnes entreprise — MVP et objectifs OBS

## Cadrage

**Type :** implementation

### Objectif

Permettre à une entreprise d’envoyer des actions confirmées depuis ses workflows
vers une API authentifiée et idempotente, puis afficher des compteurs OBS
persistants par objectif et période. Le service traite des déclarations ; il ne
détecte ni ne vérifie indépendamment achats ou téléchargements.

### Contexte utile

- [WI-0009](WI-0009-campagnes-integrations.md) porte le contrat d’intégration,
  l’attribution, les permissions et la sécurité à approuver avant implémentation.
- [WI-0010](WI-0010-campagnes-decouverte.md) porte la découverte des besoins et
  les cinq pistes d’extension ; elles ne remplacent pas le MVP entrant.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#authentification-et-isolation) :
  accès actuels par streamer/plugin, à étendre sans mélanger les entreprises.
- `app/infrastructure/database.py`, `app/application/`, `app/web/routes/` et
  `app/web/static/plugins/` : points d’intégration envisagés, pas une campagne
  déjà disponible. L’idée et le pilote restent non implémentés/non validés.
- Flux retenu : action confirmée côté entreprise → appel serveur authentifié →
  validation et déduplication persistante → compteur de la bonne période → OBS.

### Périmètre et contraintes

- Cibles proposées : modèle et migration PostgreSQL, réception d’événements,
  service de compteurs, accès OBS de campagne, administration/configuration
  minimale et documentation du pilote. Les fichiers précis de ces ajouts restent
  à approuver avec le contrat, sans framework générique préalable.
- Plusieurs objectifs configurables sans changer le code métier : libellé,
  cible, type d’événement et période. Exemples : téléchargement terminé,
  tutoriel fini, achat d’un pack de bienvenue ou commande payée. L’entreprise
  choisit et confirme le déclencheur.
- Un endpoint commun versionné, pas une route par entreprise ou objectif.
  Événement avec ID stable, type configuré, date et références campagne/streamer
  convenues. La clé identifie l’intégration ; le serveur vérifie références et
  types autorisés, selon le contrat de WI-0009.
- Première tranche : contribution de `+1` selon la règle de l’objectif, jamais
  un incrément libre fourni par le client. L’ID d’événement déduplique les
  réessais ; les personnes uniques demandent un ID opaque stable limité à
  l’intégration ou une garantie d’unicité entreprise. Unicité métier par
  objectif/période, sans email ou pseudo réel requis.
- Réception et effet sur le compteur dans une même transaction avant
  acquittement. Réessai identique sans effet ; même ID et contenu différent
  refusés. Documenter accepté/déjà traité/refusé et conditions de réessai.
- Appels depuis backend ou outil serveur de l’entreprise. Aucune clé dans jeu
  distribué, navigateur ou CSS OBS. Accès entreprise distinct de session
  streamer et clé OBS ; appliquer les garde-fous de WI-0009.
- L’entreprise transmet l’attribution finale convenue (lien, code promotionnel
  ou système interne). Ne pas deviner un streamer ni affecter un événement non
  attribuable à un objectif individuel. Une boutique peut garder ses codes promo.
- Définir les actions précisément : téléchargement, installation et premier
  lancement sont distincts ; panier, commande et paiement aussi. Convenir avant
  usage réel des corrections, remboursements et retards, sans moteur de workflow
  universel.
- Conserver les périodes sans remise à zéro destructive. OBS reçoit l’état
  autorisé au chargement, à la reconnexion et en mise à jour ; il ne calcule pas
  les totaux depuis des événements bruts. Source indépendante en lecture seule,
  clé propre et isolation streamer/campagne ; seuls les agrégats publiables
  sortent, jamais les événements individuels.
- Présentation proposée : libellé, valeur, cible, barre de progression. CSS
  personnalisé collé dans OBS comme Giveaway ; pas d’extension automatique de
  la bibliothèque de styles.
- Fournir au pilote accès confidentiel, événements/objectifs configurés,
  documentation des appels/erreurs, payload fictif et moyen de validation isolé.
  Aucun SDK, connecteur Steam/mobile/e-commerce, portail complet ou bilan
  marketing avancé requis pour cette tranche.
- Vérifications sur données temporaires d’abord. Tests/scripts, migrations,
  pilote externe et exposition réseau restent soumis aux accords spécifiques
  d’[AGENTS.md](../../AGENTS.md).

**Extensions conservées comme direction produit, hors première tranche :**

- Liens globaux et par streamer vers une destination de campagne validée ;
  clics/visites, inscriptions, installations, actions dans le jeu et valeurs
  cumulées (temps, points, montants avec unité/devise explicite).
- Résultats agrégés campagne/streamer ou événements associés à un suivi
  pseudonyme, sans collecte imposée de l’identité réelle du joueur. Métriques,
  cibles, unités, périodes et périmètres configurables. Partage d’un total
  global avec un streamer seulement sur décision explicite de l’entreprise.
- Après le MVP, imports justifiés par un pilote : provenance, période, aperçu,
  validation bornée, format versionné et réimport idempotent, avec mêmes règles
  de rapprochement que l’API de cette source.
- Interrogation API et envois sortants seulement selon les besoins pilotes :
  curseurs, suivi des livraisons, réessais bornés, destinations protégées et
  gestion de l’indisponibilité. Les trois modes sont une cible, pas un préalable
  à la première valeur.
- Ensuite faciliter configuration, consultation/export et diagnostic ; vérifier
  avec une seconde entreprise qu’une intégration compatible se configure sans
  changer le métier. Les parcours peuvent se recouper et partagent campagnes,
  droits, métriques, périodes et objectifs, sans moteurs ou plugins séparés.
- Un succès technique ou un pilote d’une catégorie ne valide ni les autres
  parcours ni une offre commerciale. Les montants cumulés du parcours e-commerce
  viennent après validation des compteurs simples.

### Dépendances

Contrat MVP de WI-0009 avant implémentation. Un premier essai fictif ne dépend
pas de la validation de toutes les pistes produit. Avant pilote externe : besoins
et partenaire qualifiés dans WI-0010, isolation de
[WI-0005](../validation/WI-0005-multi-streamer.md), prérequis d’exploitation et
de protection des données de [WI-0011](WI-0011-exploitation-durable.md), puis
accord opérationnel explicite.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Décliner le contrat approuvé de WI-0009 en modèle campagne/intégration/objectif/période et migration versionnée. | Références et contraintes d’unicité explicites sans données réelles. | Revue du schéma et migration sur base jetable autorisée uniquement. |
| T02 | Implémenter l’endpoint versionné et la transaction réception/déduplication/compteur. | Réessais idempotents, conflits refusés et contribution `+1` contrôlée. | Payloads fictifs valides, invalides, répétés et concurrents ; tests nouveaux sur accord. |
| T03 | Ajouter configuration minimale des attributions, événements et objectifs. | Un partenaire conserve son système et configure les types acceptés sans code métier dédié. | Contrôles isolés des droits et types/références non configurés. |
| T04 | Ajouter accès OBS indépendant, état initial/reconnexion et mises à jour des compteurs. | Seuls objectifs et agrégats autorisés du bon streamer/campagne sont exposés. | Clés et comptes fictifs de deux entreprises/deux streamers ; aucun secret dans les sorties. |
| T05 | Documenter l’accès pilote, les erreurs, les réessais et un exemple fictif. | Entreprise capable de brancher son appel serveur et diagnostiquer un rejet. | Relecture du contrat et parcours isolé, sans SDK ou connecteur annexe. |
| T06 | Préparer la recette du MVP et du passage de période ; consigner les limites avant pilote. | Protocole de redémarrage, déduplication, révocation et isolation. | Contrôles temporaires approuvés ; pilote et rendu OBS réels séparément autorisés. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Sur base jetable et livraison identifiée, envoyer événements fictifs, réessais identiques et conflits d’ID. | Bon compteur ; aucun double comptage ; contenu conflictuel refusé. | Payloads fictifs, réponses et valeurs persistées. |
| R02 | Exercer redémarrage, nouvelle période, dates tardives et règles d’unicité convenues. | Totaux retrouvés, historique préservé et bonne période métier. | États avant/après et règles appliquées. |
| R03 | Avec deux entreprises et deux streamers, essayer références étrangères, accès révoqués et mauvaises clés. | Aucun accès/compteur croisé ; erreurs d’intégration sans panne des autres plugins. | Matrice d’accès, effets constatés et absence de secrets. |
| R04 | Dans OBS autorisé, charger/reconnecter une source puis appliquer un CSS fictif. | État initial et mises à jour conformes, rendu correct sans calcul client des totaux. | Observation OBS séparée des résultats API. |
| R05 | Après prérequis et accord externe, faire brancher l’appel serveur par une entreprise pilote. | Compteur réconcilié avec sa source, effort et limites documentés ; retour du manager/client. | Bilan anonymisé autorisé, version, validateur et accord du pilote. |

## Suivi

### Approbation du cadrage

En attente du contrat et de l’approbation humaine détaillée. Le MVP entrant est
la direction retenue ; la migration n’autorise ni réalisation ni pilote.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant implémentation | Contrat WI-0009 | À approuver | Événements, unicité, période, attribution et règles de correction à figer. |
| Avant pilote externe | Partenaire et conditions opérationnelles | À autoriser | WI-0005, WI-0010, WI-0011 et accord du pilote requis ; aucune promesse commerciale déduite. |

### Validation finale

Première tranche terminée quand R01 à R04 passent sur données fictives, puis
R05 confirme entreprise → API → OBS dans un pilote autorisé. Notre garantie
porte sur le traitement des déclarations, pas leur réalité commerciale.
Revue indépendante, acceptation et intégration restent requises pour `done/`.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | Les imports/connecteurs et pistes A à E restent des extensions ; aucun remplacement implicite du MVP. | Toute substitution par import ou connecteur nécessite un arbitrage humain et, après gel, un WI complémentaire. |
