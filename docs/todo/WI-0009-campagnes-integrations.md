# WI-0009 — Campagnes entreprise — intégrations, attribution et sécurité

## Cadrage

**Type :** conception

### Objectif

Définir pour le cas prioritaire qualifié dans WI-0010 un contrat vérifiable
d'événements entrants : attribution, idempotence, permissions et sécurité.
Livrable : décisions de conception et exemples fictifs approuvables avant
l'implémentation WI-0008, pas l'architecture de tous les futurs connecteurs.

### Contexte utile

- [WI-0008](WI-0008-campagnes-mvp.md) fixe le MVP entrant et les compteurs OBS.
- [WI-0010](WI-0010-campagnes-decouverte.md) qualifie les besoins pilotes et les
  pistes d’extension ; les contrats restent à confirmer avec ces interlocuteurs.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#authentification-et-isolation) décrit
  les identités actuelles ; une entreprise, une session streamer et une clé OBS
  ne sont pas la même autorité.
- [docs/DEPLOY.md](../DEPLOY.md) décrit Geekom ; le déploiement actuel ne vaut
  pas validation d’un usage entreprise ni autorisation d’exposition supplémentaire.

### Périmètre et contraintes

- Cibles de conception : résultats et arbitrages dans le suivi du présent WI,
  propositions au cadrage WI-0008 tant qu’il n’est pas figé, et exemples fictifs.
  Aucun code, connecteur, secret ou changement réseau n’est livré par ce WI.
- Entrant d’abord : l’entreprise confirme l’action et envoie un événement
  authentifié avec ID stable. Les deux autres modes restent ultérieurs selon
  le pilote : interrogation d’API (pagination/curseurs, fréquence, quotas,
  reprise) et envois sortants (sélection autorisée, suivi, réessais bornés).
- Contrat versionné des champs nécessaires au cas retenu : ID, type, date UTC,
  campagne, streamer facultatif selon le contrat et éventuel suivi opaque. La contribution MVP
  est `+1` décidée côté serveur ; valeur libre, sommes et unités supplémentaires
  restent hors de cette tranche. La configuration n'exécute aucun code arbitraire.
- Commencer par HTTPS et JSON ; formats/authentifications supplémentaires
  répondent à des besoins confirmés. Identifier ce qui est configurable sans
  code et ce qui exige un adaptateur ; pas de moteur universel dès la V1.
- Livrable technique d'intégration défini dans WI-0008, pilote réel à cadrer
  séparément ; diagnostic consultable sans exposer les secrets.
- Dans les repères ci-dessous, sommes/instantanés, curseurs, interrogation API,
  sortant, redirections et portail d'entreprise restent des extensions. Le contrat
  à livrer couvre seulement l'entrant `+1` et le besoin qualifié ; conserver les
  garde-fous futurs sans exiger leur conception détaillée ou leur implémentation.
  Une correspondance configurable des champs reste une piste d'intégration,
  pas un moteur universel préalable au contrat entrant.

**Mesure et attribution :**

- Une redirection prouve au mieux une requête, pas une visite humaine,
  installation ou action dans un jeu. Séparer clics bruts, filtrés et conversions
  déclarées ; robots et préchargements gonflent les clics. Une signature prouve
  l’émetteur, pas la réalité commerciale de l’action.
- Pour un suivi individuel nécessaire, transmettre un ID opaque rendu avec la
  conversion, jamais une clé OBS ou un secret. Boutique, installation et
  multi-appareils peuvent perdre l’attribution ; conserver des non-attribués
  plutôt qu’inventer un rapprochement.
- Convenir de fenêtre et règle d’attribution entreprise (code, premier/dernier
  clic ou règle interne), ainsi que la priorité en cas de coexistence. Recevoir
  une attribution finale sans doubler une commande reliée à un code et un lien.
  Définir liens globaux sans streamer et unicité par métrique ; distinguer clic,
  personne unique et action répétable.
- Déclarer la métrique : nombre d’événements, somme ou instantané agrégé. Ne pas
  additionner des relevés successifs d’un total ni compter deux fois webhook et
  interrogation API ; source de référence ou clé de rapprochement explicite.
- Persister événements/relevés utiles, déduplication, résultats et curseurs via
  migrations versionnées. Définir retards, désordre, corrections, annulations et
  changements de configuration sans réinterprétation silencieuse de l’historique.
- Réessais idempotents après redémarrage. Pour le sortant, état de livraison et
  clé stable, avec déduplication du destinataire. Aucune promesse « exactement
  une fois » ni de rattrapage absent de la source ; prévenir les boucles de renvoi.

**Entreprises, permissions et sécurité :**

- Séparer entreprise, campagne, participation streamer, intégration et objectif.
  Droits de gestion, lecture et association contrôlés côté serveur. Une clé
  d’intégration n’est ni une session streamer ni une clé OBS.
- Progression d’accès proposée, à valider : configuration accompagnée, espace
  entreprise sur invitation, puis inscription libre si justifiée avec prévention
  des abus. Ne pas affirmer les usages du marché sans retour terrain.
- Consultation/export limités aux campagnes autorisées, métriques définies et
  données sourcées avec fraîcheur. OBS reçoit seulement objectifs et agrégats
  publiables, sans événement individuel ni identifiant de suivi.
- Authentifier les entrants, prévenir rejeu, valider dates/signatures selon la
  méthode retenue, faire tourner/révoquer les secrets et borner les quotas.
  Références campagne/streamer du payload dans le périmètre de l’intégration.
- Pour des destinations configurables ultérieures : HTTPS, destinations
  autorisées, contrôle DNS/redirections, refus des réseaux privés/locaux et
  métadonnées (SSRF). Borner délais, réponses, concurrence et réessais ; aucun
  secret relayé vers une autre destination.
- Liens publics uniquement vers destinations de campagne validées, sans
  redirection arbitraire paramétrable ; accès admin et OBS séparés.
- Minimiser données et journaux ; pas de secret dans URL, export ou événement
  OBS. Un pseudonyme peut rester personnel : cadrer information/consentement
  lorsque requis, responsabilités entreprise/service, conservation, suppression
  et accès avant usage réel. Pas de fingerprinting ni de rapprochement
  interentreprises implicite.
- Avant un futur pilote externe, confirmer restauration avec
  [WI-0011](WI-0011-exploitation-durable.md), supervision avec
  [WI-0012](WI-0012-supervision-metier.md), hébergement/HTTPS et contrôles pertinents
  avec [WI-0013](WI-0013-controles-post-deploiement.md), ainsi que protection des
  données et accords dédiés. Aucun changement réseau, SSH, Tailscale ou nouvelle
  exposition n'est autorisé par cette conception.

### Dépendances

Décision documentée de [WI-0010](WI-0010-campagnes-decouverte.md) identifiant un
besoin et des données réalisables, puis arbitrages humains. Préparer des
questions ne nécessite pas de finir les cinq parcours ; un résultat négatif ou
inconclusif de découverte ne justifie pas de figer un contrat spéculatif.
La séquence de livraison est WI-0010 → WI-0009 → WI-0008 ; les modes ultérieurs
ne sont ni prérequis ni livrables du présent contrat.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Produire le contrat entrant MVP et les exemples fictifs dans le suivi de conception. | Champs, version, types, validation et réponses/réessais explicites. | Revue documentaire et exemples fictifs, sans appel externe. |
| T02 | Définir attribution, unicité, compteur `+1`, périodes et traitement des corrections du cas qualifié. | Cas nominal, conflit, doublon, non-attribué, retard et correction acceptée/refusée explicites, sans moteur universel. | Table de cas de conception, sans résultat marché inventé ni implémentation de sommes. |
| T03 | Définir identités, droits, authentification, rotation et quotas. | Matrice de permissions distincte des accès streamer/OBS. | Revue des menaces et des références d’architecture, sans secret réel. |
| T04 | Définir minimisation, conservation et diagnostic de l'entrant ; référencer les repères des extensions. | Contrat MVP sans fuite ; SSRF/destinations et autres modes conservés hors conception détaillée de cette livraison. | Revue documentaire uniquement ; aucun endpoint privé interrogé. |
| T05 | Présenter le contrat et les inconnues au pilote/humain, puis reporter les arbitrages autorisés vers WI-0008 non figé. | Contrat approuvable, décisions attribuées et contraintes d’implémentation explicites. | Validation documentaire humaine ; aucune approbation déduite d’un silence. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Relire les exemples fictifs avec un interlocuteur intégrateur autorisé. | Déclencheurs, champs, attribution, périodes et réessais compris et réalisables. | Version du contrat et arbitrages anonymisés approuvés. |
| R02 | Confronter la matrice du compteur `+1` aux conflits, retards, corrections et périodes. | Chaque situation a une décision explicite, sans double comptage ni attribution inventée ; métriques avancées hors livraison. | Cas et décisions validés, pas une preuve de code exécuté. |
| R03 | Relire permissions, données, hébergement et menaces avec les responsables du pilote. | Prérequis et responsabilités identifiés ; aucune exposition ou collecte tacitement autorisée. | Décisions, décideur, date et référence d’accord. |

## Suivi

### Approbation du cadrage

En attente de validation humaine après qualification du cas WI-0010. L'accord
de recadrage documentaire n'approuve pas le contrat ; le statut `conception`
n'autorise ni l'implémentation MVP ni celle des modes ultérieurs.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant contrat final | Décision WI-0010, interlocuteur et règles métier | À confirmer | Besoin réalisable, déclencheurs, attribution et corrections à arbitrer ; aucun contrat approuvé. |

### Validation finale

En attente de contrat livré, revue indépendante, recette documentaire et
acceptation humaine. `done/` suppose des arbitrages approuvés et une intégration
identifiée de la documentation ; cela ne prouvera pas le fonctionnement du MVP.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | Transformer les contraintes prévues en contrat de conception avant le code ; garder interrogation API et sortant hors MVP. | Cadrage et décisions pilote à approuver ; migration documentaire seulement autorisée. |
| 2026-11-01 | Utilisateur et assistant | Borner le contrat au cas qualifié et au compteur entrant `+1` ; conserver les repères d'extensions sans les concevoir tous ; séquence WI-0010 → WI-0009 → WI-0008. | Conversation courante : accord « Valider le plan » pour le recadrage documentaire uniquement. |
