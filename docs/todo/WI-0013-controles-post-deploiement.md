# WI-0013 — Contrôles opérateur post-déploiement

## Cadrage

**Type :** exploration

### Objectif

Établir, sur une livraison identifiée, quels parcours et protections du
déploiement fonctionnent réellement et quels contrôles restent bloqués.
Livrable : dossier de résultats opérateur, limites et suites explicites ;
aucune réimplémentation de l'application ni modification du socle par défaut.

### Contexte utile

- [docs/DEPLOY.md](../DEPLOY.md) porte le runbook et les responsabilités Geekom ;
  [docs/ARCHITECTURE.md](../ARCHITECTURE.md#déploiement-et-entrée-web) décrit le proxy.
- `nginx/https/default.conf` contient le durcissement livré, dont activation et
  validation hôte restent à confirmer ; la CI ne recharge pas Nginx.
- `app/web/routes/auth.py`, `app/web/routes/admin.py`,
  `app/web/routes/overlay.py`, `app/web/admin_security.py` et les ressources
  admin/OBS sont des cibles de lecture et de parcours, pas de correction ici.
- Ce WI reprend les anciennes R07 à R11 de
  [WI-0011](WI-0011-exploitation-durable.md), avec leurs statuts non validés.
- L'utilisateur a confirmé dans la conversation la livraison fonctionnelle de
  l'application après le changement de base Docker. Cela ne constitue pas une
  preuve des contrôles détaillés ci-dessous ; version et résultats sont à identifier.

### Périmètre et contraintes

- Cibles modifiables proposées : protocoles/résultats dans le suivi du présent
  WI et état utile de `docs/DEPLOY.md`. Le code, vhost, workflows, Compose et
  configuration hôte restent inchangés par ce cadrage.
- Séparer préparation documentaire, recette navigateur/Twitch/OBS et contrôles
  opérateur. Identifier livraison, cible, créneau et validateur avant chaque
  manipulation ; aucun accès réel n'est autorisé par le recadrage.
- OAuth/OBS : liaison au navigateur, reconnexion, révocation, refus des comptes
  désactivés et confiance proxy effective. Réutiliser une preuve WI-0005 seulement
  si livraison et scénario correspondent ; ne pas présenter un `/health` réussi
  comme une recette métier.
- Nginx : prérequis opérateur d'installation/activation du vhost livré à faire
  autoriser séparément selon le runbook. Après cet accord et sur environnement
  approprié, recueillir `nginx -t`, anti-scan, quota isolé, ressources et OAuth/OBS.
  Aucun rechargement automatique ni test de charge en production.
- Certbot : dry-run/hook avec vhost actif et certificat réellement servi, seulement
  après accord opérateur. Ne jamais lire de clé privée ni élargir l'accès réseau.
- PostgreSQL : vérifier l'absence d'exposition Tailscale/Internet par un contrôle
  borné explicitement autorisé ; TLS LAN déjà validé ne prouve pas cette absence.
  Aucun scan large ni modification SSH, Tailscale ou pare-feu pour obtenir un succès.
- Navigateur : administration, refus du cadrage, aperçu isolé, navigation/copie,
  responsive et disponibilité de `robots.txt`. Ce dernier n'est pas une sécurité.
- Ne lire ni afficher `.env`, `.tio.tokens.json`, leurs sauvegardes, clés OBS,
  cookies ou tokens. Recueillir uniquement résultats expurgés, jamais les liens
  OBS confidentiels, environnements ou configuration réelle complète.
- Un résultat négatif ou un contrôle indisponible reste explicite, avec risque,
  responsable et suite proposée. Toute correction, activation du vhost, rotation,
  renouvellement, réseau ou fichier de test/script nécessite un accord spécifique
  selon [AGENTS.md](../../AGENTS.md), pas la seule présence d'une recette.

### Dépendances

Livraison identifiée, accès opérateur autorisé et disponibilité des parcours.
Ce WI ne dépend pas de la clôture de WI-0003, WI-0011 ou WI-0012 pour préparer ses
contrôles. [WI-0005](../validation/WI-0005-multi-streamer.md) porte la recette
simultanée des deux chaînes ; ne pas la déplacer ni la déclarer réussie ici.
Les actions du socle `geekom` conservent leurs propres autorisations.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Identifier version, preuves existantes et opérations des cinq familles de contrôle. | Matrice livraison/scénario/cible/accord/validateur sans secret. | Revue documentaire uniquement avant accord de manipulation. |
| T02 | Préparer OAuth/OBS et navigateur avec les limites du proxy et des accès actuels. | Parcours reproductibles distincts d'une simple sonde HTTP. | Lecture du code et protocole ; aucune connexion réelle implicite. |
| T03 | Préparer les contrôles opérateur Nginx, Certbot et exposition PostgreSQL selon le runbook. | Méthodes bornées, conditions préalables et responsabilités explicites. | Relecture ; aucun rechargement, renouvellement ou contrôle réseau avant accord dédié. |
| T04 | Analyser les résultats expurgés fournis par l'opérateur et les écarts. | Conforme, non conforme et non vérifié distingués ; aucune preuve fabriquée. | Résultats autorisés seulement ; pas de configuration réelle ou journaux sensibles. |
| T05 | Mettre à jour état opérationnel et suites dans le suivi et `docs/DEPLOY.md`. | Dossier accepté, risques attribués et corrections à cadrer séparément. | Relecture et revue indépendante ; aucun correctif applicatif ou infrastructure implicite. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Sur livraison et créneau autorisés, parcourir OAuth/OBS, reconnexion et révocation comprises. | Liaison au navigateur, sessions révoquées, comptes désactivés refusés et confiance proxy vérifiées. | Version et matrice des parcours sans cookie, token ni clé. |
| R02 | Après autorisation séparée de l'éventuelle activation du vhost, appliquer les contrôles Nginx du runbook. | Syntaxe, filtrage sensible/PHP, quota isolé et parcours légitimes vérifiés ; aucun résultat présumé. | `nginx -t`, statuts et observations, sans charge en production. |
| R03 | Sur accord opérateur, éprouver renouvellement Certbot/hook et certificat servi avec le vhost actif. | Résultats et limites connus, sans accès aux clés privées. | Dry-run/hook, certificat servi, version et date. |
| R04 | Avec une méthode et des cibles précisément autorisées, vérifier l'inaccessibilité PostgreSQL depuis Tailscale et Internet. | Absence d'exposition constatée, ou anomalie documentée sans modifier le réseau. | Cibles non secrètes, méthode bornée et résultat. |
| R05 | Dans un vrai navigateur autorisé, vérifier admin, aperçu, cadrage, navigation/copie, responsive et `robots.txt`. | Résultats observés et écarts documentés sans partager les accès confidentiels. | Matrice navigateur, statuts et observations expurgées. |

## Suivi

### Approbation du cadrage

En attente de validation humaine du cadrage et des opérations précises.
L'accord de création documentaire ne permet ni recette réelle ni activation,
rechargement, renouvellement, rotation, scan ou changement d'accès.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| 2026-10-30, migration documentaire dans WI-0011 | Ancien T06 | Suivi repris, sans recette | Anciennes R07 à R11 reprises de la roadmap sans résultat nouveau. |
| 2026-11-01, recadrage documentaire | T01 à T05 | Non exécutées | Transfert vers un WI distinct ; aucun contrôle opérateur ni livrable applicatif produit. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant opérations | Version, cibles, créneaux et accords | À identifier et autoriser | Le fonctionnement livré confirmé par l'utilisateur ne valide pas R01 à R05. |
| Déploiement Geekom existant, version à identifier | R01, ancienne R07 de WI-0011 | À confirmer | Parcours OAuth/OBS et confiance proxy restant à valider réellement. |
| Vhost anti-scan versionné, non activé lors de sa livraison locale | R02, ancienne R08 de WI-0011 | À effectuer | Installation, syntaxe et parcours réels non validés par la revue locale. |
| Déploiement Geekom existant, version à identifier | R03, ancienne R09 de WI-0011 | À effectuer | Renouvellement et hook avec vhost TLS actif non confirmés. |
| Déploiement Geekom existant, version à identifier | R04, ancienne R10 de WI-0011 | À confirmer | Accès LAN TLS validé ; inaccessibilité Tailscale/Internet restant à contrôler. |
| Déploiement Geekom existant, version à identifier | R05, ancienne R11 de WI-0011 | À confirmer | Administration navigateur et disponibilité de `robots.txt` à confirmer. |

### Validation finale

Terminé après collecte/revue du dossier, arbitrage explicite des contrôles non
conformes ou non réalisables, acceptation et intégration identifiée. Une clôture
avec réserves doit nommer risques, responsable et suites ; elle ne transforme
jamais une absence de preuve en conformité ni en autorisation de pilote externe.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-11-01 | Utilisateur et assistant | Extraire les anciennes R07 à R11 de WI-0011 sans changer leurs résultats ni autoriser les opérations du socle. | Conversation courante : accord « Valider le plan » sur le recadrage documentaire et la création de WI-0013 ; cadrage et accords opérateur en attente. |
