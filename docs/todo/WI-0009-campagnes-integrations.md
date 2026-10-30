# WI-0009 — Campagnes entreprise — intégrations, attribution et sécurité

## Cadrage

**Type :** conception

### Objectif

Définir un contrat vérifiable d’événements entreprise pour le MVP : attribution,
idempotence, permissions et sécurité. Livrable : décisions de conception et
exemples fictifs approuvables avant l’implémentation de WI-0008.

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
- Contrat versionné et correspondance configurable des champs : ID, type,
  date UTC, campagne, streamer facultatif, suivi facultatif, valeur/unité selon
  la métrique approuvée. La configuration n’exécute jamais de code arbitraire.
- Commencer par HTTPS et JSON ; formats/authentifications supplémentaires
  répondent à des besoins confirmés. Identifier ce qui est configurable sans
  code et ce qui exige un adaptateur ; pas de moteur universel dès la V1.
- Livrables d’intégration pilote définis dans WI-0008 ; diagnostic consultable
  sans exposer les secrets.

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
- Avant pilote externe, confirmer hébergement/HTTPS adaptés, restauration et
  protection des données avec WI-0011. Aucun changement réseau, SSH, Tailscale
  ou nouvelle exposition n’est autorisé par cette conception.

### Dépendances

Besoins pilotes et arbitrages humains, explorés dans WI-0010. La conception du
contrat entrant peut commencer sans valider les cinq parcours ni implémenter
les modes ultérieurs. Ses décisions approuvées précèdent l’implémentation WI-0008.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Produire le contrat entrant MVP et les exemples fictifs dans le suivi de conception. | Champs, version, types, validation et réponses/réessais explicites. | Revue documentaire et exemples fictifs, sans appel externe. |
| T02 | Définir attribution, unicité, métriques, périodes et corrections avec les décisions pilotes disponibles. | Cas nominal, conflit, doublon, non-attribué et retard sans ambiguïté. | Table de cas de conception, sans résultat marché inventé. |
| T03 | Définir identités, droits, authentification, rotation et quotas. | Matrice de permissions distincte des accès streamer/OBS. | Revue des menaces et des références d’architecture, sans secret réel. |
| T04 | Consigner limites de données et garde-fous des futurs modes/liens. | Politique SSRF, destinations, conservation et diagnostic sans fuite ; extensions séparées du MVP. | Revue documentaire uniquement ; aucun endpoint privé interrogé. |
| T05 | Présenter le contrat et les inconnues au pilote/humain, puis reporter les arbitrages autorisés vers WI-0008 non figé. | Contrat approuvable, décisions attribuées et contraintes d’implémentation explicites. | Validation documentaire humaine ; aucune approbation déduite d’un silence. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Relire les exemples fictifs avec un interlocuteur intégrateur autorisé. | Déclencheurs, champs, attribution, périodes et réessais compris et réalisables. | Version du contrat et arbitrages anonymisés approuvés. |
| R02 | Confronter la matrice de cas aux conflits, retards, corrections et métriques agrégées. | Chaque situation a une décision explicite, sans double comptage ni attribution inventée. | Cas et décisions validés, pas une preuve de code exécuté. |
| R03 | Relire permissions, données, hébergement et menaces avec les responsables du pilote. | Prérequis et responsabilités identifiés ; aucune exposition ou collecte tacitement autorisée. | Décisions, décideur, date et référence d’accord. |

## Suivi

### Approbation du cadrage

En attente de validation humaine. Le statut `conception` borne le travail au
contrat ; il n’autorise pas l’implémentation du MVP ni des modes ultérieurs.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant contrat final | Interlocuteur pilote et règles métier | À confirmer | Besoins, déclencheurs, fenêtres d’attribution et corrections à arbitrer ; aucun contrat approuvé. |

### Validation finale

En attente de contrat livré, revue indépendante, recette documentaire et
acceptation humaine. `done/` suppose des arbitrages approuvés et une intégration
identifiée de la documentation ; cela ne prouvera pas le fonctionnement du MVP.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | Transformer les contraintes prévues en contrat de conception avant le code ; garder interrogation API et sortant hors MVP. | Cadrage et décisions pilote à approuver ; migration documentaire seulement autorisée. |
