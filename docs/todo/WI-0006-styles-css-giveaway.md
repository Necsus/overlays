# WI-0006 — Bibliothèque privée de styles CSS Giveaway

## Cadrage

**Type :** implementation

### Objectif

Sauvegarder et retrouver ses styles Giveaway, les prévisualiser puis copier
leur CSS dans OBS. Première tranche : bibliothèque personnelle persistante,
sans publication ni accès aux styles d'un autre streamer. Le partage reste
une suite conditionnelle à cadrer séparément.

### Contexte utile

- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#authentification-et-isolation) :
  identité Twitch stable et contrôle serveur du propriétaire.
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md#administration-et-aperçus) : aperçu
  fictif déjà disponible ; la persistance et le partage ne sont pas implémentés.
- `app/web/static/admin/giveaway-preview.js` et
  `app/web/static/plugins/giveaway/giveaway-renderer.js` portent l’aperçu.
- `app/web/static/plugins/giveaway/overlay.html` porte le DOM actuel ; il ne
  promet pas encore une compatibilité des sélecteurs avec toute version future.
- `app/infrastructure/database.py`, `app/web/routes/admin.py` et
  `app/web/static/admin/` sont les points d’intégration envisagés.

### Périmètre et contraintes

- Cibles proposées : migration PostgreSQL versionnée, persistance des styles,
  API admin protégée, interface « Mes styles », aperçu et documentation.
  Les styles restent distincts des secrets et clés OBS.
- Un style contient nom, description facultative, CSS, propriétaire et dates.
  Le propriétaire est l'identité Twitch de la session, jamais un champ décidé
  par le navigateur. Les styles sont strictement privés dans cette tranche.
- Le propriétaire crée, lit, modifie, supprime et copie son CSS. Ni visibilité
  configurable, catalogue partagé ni duplication inter-streamers dans ce WI.
- Le flux reste `/admin` → bibliothèque → copie → CSS personnalisé OBS. Une
  modification ou suppression ne change jamais ce qui est déjà collé dans OBS.
  Pas d’application distante, synchronisation, historique de versions, notes,
  commentaires, framework de thèmes ou nouveau plugin.
- Définir avant implémentation le contrat des sélecteurs, compteur compris, les
  tailles, quotas par propriétaire et pagination. Protéger les mutations contre
  les requêtes intersites (CSRF).
- Contrôler côté serveur listes, lectures et mutations. Répondre `404` pour un
  style étranger ; vérifier les API directes, pas uniquement les boutons.
- Noms, descriptions et CSS sont non fiables : rendu en texte, sans injection
  HTML. Exécuter le CSS seulement dans une iframe sandboxée sans accès à
  l’origine admin, jamais dans le document admin. CSP bloquant imports, images,
  polices et autres requêtes externes ; aucune récupération serveur des URLs.
- Signaler les ressources externes non prévisualisées. Un CSS collé dans OBS
  peut masquer des éléments ou charger des tiers via `url()`, `@import` et les
  polices ; la bibliothèque ne constitue pas une garantie de sûreté du CSS.
- Exclure liens OBS authentifiés, tokens et secrets des blocs et métadonnées,
  rappeler cette règle dans l'interface et ne pas journaliser le contenu CSS.
- Les scénarios fictifs couvrent compteur avec/sans durée, gagnants multiples,
  textes longs et état masqué, sans mutation du giveaway réel. Tests/scripts,
  migrations et essais réels demandent les accords d’[AGENTS.md](../../AGENTS.md).

**Suite conditionnelle conservée — partage, hors livraison de ce WI :**

- Après validation de l'usage privé et choix humain de priorité, cadrer un WI
  complémentaire avant d'ajouter visibilité, publication ou catalogue partagé.
- Le contrat envisagé reste privé par défaut : le propriétaire contrôle visibilité
  et édition ; un style partagé est lisible/copiable par les streamers authentifiés
  admis, jamais éditable par un autre. Pas de catalogue anonyme ni d'exposition nouvelle.
- La duplication produit une copie privée indépendante appartenant au copieur.
  Retrait du partage ou suppression retire l'accès à l'original, pas les copies
  sauvegardées/collées ; annoncer cette limite avant publication.
- Séparer « Mes styles » / « Styles partagés » ; afficher seulement l'identité
  publique nécessaire de l'auteur. Contrôler les lectures, copies et mutations
  directes ; rappeler l'exclusion des secrets et les risques de CSS tiers.
- Ces exigences ne sont ni implémentées ni des conditions de clôture de la V1 privée.

### Dépendances

Contrat de sélecteurs et limites à faire approuver. Réutiliser les contrôles
d’accès et l’aperçu existants ; confirmer l’isolation dans
[WI-0005](../validation/WI-0005-multi-streamer.md) avant usage multi-streamer externe.

### Tâches IA

| ID | Action et cible | Résultat attendu | Vérification autorisée |
| --- | --- | --- | --- |
| T01 | Formaliser limites de la bibliothèque privée et contrat des sélecteurs dans la documentation et les contrats de l'API. | Contrat borné et approuvé avant stockage ; partage explicitement hors V1. | Revue de conception ; valeurs non décidées à soumettre à l'humain. |
| T02 | Ajouter migration versionnée et persistance PostgreSQL des styles par propriétaire. | Bibliothèque privée conservée après redémarrage, distincte des clés OBS. | Base jetable autorisée ; aucune migration de production implicite. |
| T03 | Ajouter listes paginées, CRUD et copie CSS privés dans l’API et l’admin. | Droits serveur et protections CSRF sur toutes les mutations. | Contrôles API isolés avec deux identités fictives ; nouveaux tests sur accord. |
| T04 | Relier la bibliothèque privée à l'aperçu sandboxé et documenter les limites OBS. | États fictifs couverts, réseau bloqué, aucune mutation métier. | Revue CSP/sandbox et contrôle navigateur autorisé, sans données réelles. |
| T05 | Préparer la recette du parcours sauvegarde → aperçu → copie → OBS. | Protocole privé séparant contrôles d'API et rendu réel. | Relecture ; validation OBS uniquement après accord. |

### Recette humaine

| ID | Préparation et action humaine | Résultat attendu | Preuve |
| --- | --- | --- | --- |
| R01 | Avec deux identités et des styles fictifs, créer puis retrouver un style après redémarrage autorisé. | Persistance et confidentialité par défaut. | Version, style fictif et résultat après reprise. |
| R02 | Exercer anonymat, listes et accès directs croisés, modification et suppression de styles privés. | Seul le propriétaire accède à ses styles ; ressource étrangère refusée, y compris par API directe. | Matrice d'accès et résultats API expurgés. |
| R03 | Prévisualiser chaque état avec CSS et métadonnées hostiles/fictifs et URLs externes. | Isolation de l’admin, texte sûr, réseau bloqué et giveaway réel intact. | Résultats navigateur et contrôles réseau sans secrets. |
| R04 | Copier dans OBS un style autorisé, puis modifier l’original. | Transparence, gagnants et compteur corrects ; rendu OBS et copie inchangés sans nouveau collage. | Observation OBS, livraison et validation humaine. |

## Suivi

### Approbation du cadrage

En attente de validation humaine, notamment des limites et du contrat de
sélecteurs. Ni la migration ni le recadrage documentaire n'autorisent la
réalisation du WI ; le partage nécessitera un cadrage complémentaire.

### Réalisations IA

| Date et livraison | Tâche | État | Résultat et vérification observés |
| --- | --- | --- | --- |
| Existant, version/date non consignées ici | T04, ancien T05 avant recadrage | Prérequis partiellement disponible | Aperçu fictif isolé décrit dans l'architecture ; ni bibliothèque ni partage livrés. |

### Tâches humaines

| Livraison | Recette ou prérequis | État | Résultat, preuve, validateur et date |
| --- | --- | --- | --- |
| Avant implémentation | Limites et sélecteurs | À arbitrer | Taille CSS/métadonnées, nombre par propriétaire, pagination et compatibilité à approuver. |

### Validation finale

En attente d’implémentation, de revue indépendante et de recette R01 à R04.
Terminé lorsque styles privés et droits persistent, l'aperçu couvre les états
fictifs et le parcours OBS fonctionne sans secrets ni modification des giveaways.
Cette clôture ne livre ni ne valide le partage conditionnel.

## Commentaires et arbitrages

| Date | Auteur | Constat et proposition | Décision humaine et référence |
| --- | --- | --- | --- |
| 2026-10-30 | Assistant | L’aperçu existant ne signifie pas que la bibliothèque est implémentée ; conserver le WI dans `todo/`. | Accord de migration uniquement ; limites et exécution restent à approuver. |
| 2026-11-01 | Utilisateur et assistant | Livrer le privé d'abord ; ancien T04 et exigences de partage conservés comme suite conditionnelle, sans nouveau WI anticipé. | Conversation courante : accord « Valider le plan » pour le recadrage documentaire uniquement ; priorité et cadrage d'exécution en attente. |
