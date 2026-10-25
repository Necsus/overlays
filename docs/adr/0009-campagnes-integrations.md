# ADR-0009 — Campagnes entreprise — intégrations, attribution et sécurité

[← Roadmap](../ROADMAP.md)

**Statut :** contraintes prévues ; contrats et besoins pilotes à confirmer.

## Contexte

Les événements entreprise nécessitent une attribution fiable et une séparation
des permissions.

## Décision ou orientation

Privilégier les événements entrants ; différer interrogation API et envois
sortants selon les pilotes. Distinguer déclaration reçue et réalité commerciale
vérifiée.

## Conséquences

Ces garde-fous accompagnent le [MVP](0008-campagnes-mvp.md) ; aucune exposition
publique ni modification réseau n’est autorisée par ce dossier.

## Travail associé et validation

### Modes d'intégration — entrant d'abord, autres modes ultérieurs

| Mode | Fonction | Contraintes principales |
| --- | --- | --- |
| Événements entrants | L'entreprise envoie les actions confirmées vers notre endpoint authentifié. | Identifiant d'événement stable, authentification, validation et déduplication persistante. |
| Interrogation de leur API | Notre service récupère les événements ou compteurs sur les endpoints de l'entreprise. | Authentification, pagination/curseur, fréquence, limites de débit et reprise. |
| Envois vers leur API | Notre service transmet les événements observés et résultats autorisés vers leurs endpoints. | Sélection des données, authentification, livraisons suivies et réessais bornés. |

- Définir un contrat interne versionné et une correspondance configurable des
  champs entrants/sortants : identifiants, type d'événement, date UTC, campagne,
  streamer facultatif, identifiant de suivi facultatif, valeur et unité. La
  configuration ne doit pas permettre d'exécuter du code arbitraire.
- Commencer par HTTPS et JSON avec des exemples documentés ; étendre formats et
  méthodes d'authentification à partir des besoins des entreprises pilotes.
  Distinguer ce qui est configurable sans code de ce qui exige un nouvel
  adaptateur ; ne pas construire un moteur d'intégration universel dès la
  première tranche.
- Les livrables d’intégration du pilote sont définis dans le
  [MVP](0008-campagnes-mvp.md). L’état des échanges doit rester consultable sans
  exposer les secrets.

### Mesure et attribution fiables

```text
Lien global ou streamer → redirection vers l'entreprise
                              └── action confirmée par son système
                                      → événement entrant / API interrogée
                                      → normalisation et attribution
                                      → résultats persistés → objectifs OBS
                                                           └── API de l'entreprise, si configurée
```

- Un accès au lien prouve au mieux une requête de redirection, pas une visite
  humaine, une installation ou une action dans le jeu. Distinguer clics bruts,
  clics filtrés et conversions déclarées par l'entreprise ; les robots et
  préchargements peuvent gonfler les clics. Une signature authentifie
  l'émetteur, pas la réalité commerciale de l'action.
- Pour le suivi individuel, transmettre un identifiant opaque à l'entreprise,
  qui le renvoie avec la conversion. Ne jamais y placer de clé OBS ou de secret.
  Les parcours boutique, installation et multi-appareils peuvent perdre cet
  identifiant : prévoir des événements non attribués plutôt qu'inventer une
  correspondance.
- Documenter avec l'entreprise la fenêtre et la règle d'attribution qu'elle
  applique (code promo, premier/dernier clic ou règle interne), ainsi que la
  priorité si plusieurs méthodes coexistent. Recevoir une attribution finale,
  sans compter deux fois une commande liée à un code et un lien. Définir le
  traitement des liens globaux sans streamer et l'unicité par métrique ; ne pas
  assimiler clic, personne unique et action répétable.
- Déclarer chaque métrique comme comptage d'événements, somme de valeurs ou
  instantané agrégé. Ne pas additionner les relevés successifs d'un compteur
  total, ni compter deux fois une conversion reçue par webhook et par
  interrogation API ; désigner une source de référence ou une clé de
  rapprochement fiable.
- Persister événements acceptés ou relevés nécessaires, clés de déduplication,
  résultats et curseurs avec migrations versionnées. Définir les règles pour
  événements tardifs/désordonnés, corrections, annulations et changements de
  configuration ; ne pas modifier silencieusement le sens des résultats passés.
- Les réessais doivent être idempotents, y compris après redémarrage. Pour les
  envois sortants, conserver un état de livraison et une clé stable ; le
  destinataire doit aussi dédupliquer. Ne pas promettre une livraison exactement
  une fois ni un rattrapage si la source ne le permet pas ; éviter les boucles
  de renvoi entre intégrations.

### Entreprises, permissions et sécurité

- Séparer entreprise, campagne, participation du streamer, intégration et
  objectif. Définir les droits de gestion, de consultation et d'association d'un
  streamer à une campagne ; vérifier chaque accès côté serveur. Une clé
  d'intégration entreprise n'est ni une session streamer ni une clé OBS.
- **Progression d'accès proposée, à valider avec les pilotes :** configuration
  accompagnée, puis espace entreprise autonome sur invitation, puis inscription
  libre si utile avec vérification et prévention des abus. Garder ces
  possibilités ouvertes sans affirmer connaître les modes les plus utilisés
  avant retour terrain.
- Fournir des résultats consultables/exportables limités aux campagnes
  autorisées, avec définition des métriques, source et fraîcheur des données.
  OBS ne reçoit que les objectifs et agrégats explicitement publiables, jamais
  les événements individuels ou les identifiants de suivi.
- Authentifier les événements entrants ; prévoir protection contre le rejeu,
  validation des dates et signatures lorsqu'elles sont utilisées,
  rotation/révocation des secrets et quotas. Les identifiants de
  campagne/streamer du payload doivent appartenir au périmètre autorisé de
  l'intégration.
- Pour les endpoints personnalisables, prévenir les requêtes vers le réseau
  interne (SSRF) : HTTPS, destinations autorisées, contrôle des résolutions DNS
  et redirections, exclusion des adresses privées/locales et services de
  métadonnées. Borner délais, taille des réponses, concurrence et réessais ; ne
  jamais relayer des secrets vers une autre destination.
- Les liens publics doivent pointer uniquement vers des destinations de campagne
  validées, sans paramètre permettant une redirection arbitraire. Séparer ces
  liens des accès administratifs et OBS.
- Minimiser les données et journaux ; aucun secret dans une URL, un export ou un
  événement OBS. Un identifiant pseudonyme reste potentiellement une donnée
  personnelle : cadrer information/consentement lorsque requis, responsabilités
  entreprise/service, conservation, suppression et accès avant un usage réel.
  Pas de fingerprinting ni de rapprochement interentreprises implicite.
- **Prérequis avant un pilote externe :** vérifier que l’hébergement et
  l’exposition HTTPS conviennent au pilote, valider sauvegarde/restauration et
  protection des données. Le déploiement actuel sur Geekom ne vaut pas
  validation d’un usage entreprise ; ce dossier n’autorise aucune modification
  réseau ni nouvelle exposition.
