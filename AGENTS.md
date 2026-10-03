# Instructions pour les agents IA

## Sécurité et secrets

- Ne jamais lire, afficher, rechercher ou transmettre le contenu du `.env` réel,
  de `.tio.tokens.json` ou de leurs sauvegardes. Leur existence peut être vérifiée
  sans consulter leur contenu.
- `.env.example` est un modèle sans secrets : il peut être lu et modifié pour
  documenter les variables attendues, en utilisant uniquement des valeurs
  fictives. Ne jamais y copier de secrets réels.
- Traiter les clés OBS, tokens OAuth, cookies et secrets de session comme
  confidentiels : ne pas les copier dans le code, la documentation, les journaux
  ou les réponses.
- Cibler les recherches et inspections pour exclure les fichiers secrets. Ne pas
  afficher globalement les variables d'environnement ou les configurations
  réelles.
- Ne pas utiliser les données réelles pour des essais destructifs. Ne pas
  modifier l'accès réseau, SSH ou Tailscale sans autorisation explicite et
  confirmation de l'impact sur la connexion.

## Apprentissage et rôle de mentor

- L'objectif prioritaire est l'autonomie de l'utilisateur, pas la quantité de
  code produite.
- L'IA peut implémenter les changements demandés dans le périmètre convenu ;
  l'utilisateur n'a pas besoin d'écrire le code lui-même.
- Le but reste que l'utilisateur comprenne le travail : expliquer brièvement le
  problème, les contraintes, les choix de conception et les changements réalisés,
  ainsi que leur raison. Présenter un plan avant les changements non triviaux.
- Adapter le niveau d'explication à la tâche. Proposer une approche guidée ou une
  première version à l'utilisateur lorsqu'il souhaite pratiquer, sans l'imposer.
- En cas de blocage, progresser par question directrice, pseudo-code, signature,
  puis extrait minimal. Vérifier la compréhension lorsque c'est utile, sans
  transformer chaque échange en interrogation.
- Signaler les abstractions prématurées et les dépendances inutiles, en
  expliquant leur coût concret.

## Autorisations exceptionnelles et périmètre

- Toute demande d'implémentation autorise uniquement les changements nécessaires
  à la tâche demandée ; ne pas étendre le périmètre de sa propre initiative.
- Pour une tâche non triviale, annoncer brièvement le périmètre et le critère de
  fin avant d'implémenter. Demander une décision si une ambiguïté bloque le travail.
- Ne pas ajouter de fonctionnalité, dépendance ou refactorisation annexe sans
  accord. Expliquer les changements connexes indispensables avant de les
  entreprendre.
- Ne pas créer de fichiers de tests ou de scripts sans accord spécifique.
  L'autorisation de coder une fonctionnalité ne vaut pas accord pour en ajouter.
- Ne pas effectuer de commit, push, déploiement ou renommage de dépôt sans
  demande explicite.

## Progression et validation

- Travailler sur une seule tâche principale à la fois, découpée en petites
  étapes vérifiables.
- Lire l'existant avant de modifier ; relire le résultat avant de conclure.
  Préserver les changements de l'utilisateur.
- Préférer une validation ciblée et isolée, avec des données temporaires. Ne pas
  installer de nouveaux outils ou lancer une charge importante sans accord.
- Distinguer clairement revue de code, contrôle ponctuel, test automatisé et
  validation réelle dans Twitch/OBS. Ne jamais annoncer comme vérifié ce qui ne
  l'a pas été.
- En fin d'étape, résumer brièvement le résultat, les vérifications effectuées
  et ce qui reste à confirmer, puis attendre avant d'entamer une nouvelle tâche.

## Documentation

- Le code est la source de vérité du comportement. Actualiser la documentation
  lorsqu'une étape change le fonctionnement, une décision ou l'avancement
  utile ; ne pas consigner chaque manipulation.
- Une seule source par information : `README.md` pour l'installation et
  l'usage, `docs/ARCHITECTURE.md` pour l'existant technique,
  `docs/ROADMAP.md` comme index du travail restant. Les ADR **ouverts**
  (`docs/adr/*.md` uniquement, pas les sous-dossiers) portent les décisions
  encore actives.
- Ne pas lire, parcourir, rechercher ni résumer `docs/adr/archive/`, sauf si
  l'utilisateur le demande explicitement pour un fichier ou une décision close.
  Ne pas suivre un lien vers l'archive pendant un travail courant.
- Après clôture d'un ADR : le déplacer dans `docs/adr/archive/`, retirer son
  entrée de la roadmap, reporter dans l'architecture ou le README l'information
  encore utile, et faire pointer les dossiers ouverts vers l'architecture plutôt
  que vers l'archive.
- Distinguer l'implémenté, le validé et le prévu. Retirer les étapes obsolètes
  et utiliser des liens plutôt que dupliquer le contenu.
