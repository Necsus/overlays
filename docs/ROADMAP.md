# NecsusDevOverlays — Roadmap

Ce fichier est l’index du travail restant. L’existant est décrit dans
[l’architecture](ARCHITECTURE.md) ; l’installation et l’usage dans le
[README](../README.md).

## Chantier actif — accès Internet / CI-CD

La configuration Nginx/Certbot est préparée, **non déployée et non validée**.
La procédure et les critères de validation restent dans
[DEPLOY.md](DEPLOY.md#état-et-points-à-confirmer).

- Corriger la détection du certificat sous `deploy` sans élargir l’accès aux
  clés privées ; voir les [limites CI](DEPLOY.md#limites-de-lautomatisation).
- Déployer les fichiers préparés et terminer la mise en service HTTPS.
- Valider l’accès extérieur, OAuth Twitch, OBS et le renouvellement/rechargement.
- Élucider l’absence du conteneur applicatif observée après un workflow réussi.

L’accès PostgreSQL depuis le poste de développement est un sujet réseau
séparé ; voir les [limites réseau](DEPLOY.md#4-données-réseau-et-limites).

## Priorités et dossiers ADR

Les trois dossiers « Campagnes entreprise » forment un seul chantier ; leur
découverte métier peut avancer en parallèle, sans autoriser le développement des
extensions.

| Ordre | Dossier |
| --- | --- |
| 0 | [Stabilisation sous charge](adr/0003-stabilisation-charge.md) |
| 1 | [Plugin Chat indépendant](adr/0004-plugin-chat.md) |
| 2 | [Isolation multi-streamer](adr/0005-multi-streamer.md) |
| 3 | [Bibliothèque de styles CSS Giveaway](adr/0006-styles-css-giveaway.md) |
| 4 | [Alertes Points de chaîne](adr/0007-points-de-chaine.md) |
| 5 | [Campagnes entreprise — MVP et objectifs OBS](adr/0008-campagnes-mvp.md) |
| 6 | [Campagnes entreprise — intégrations, attribution et sécurité](adr/0009-campagnes-integrations.md) |
| 7 | [Campagnes entreprise — découverte et parcours métier](adr/0010-campagnes-decouverte.md) |
| 8 | [Exploitation durable](adr/0011-exploitation-durable.md) |

## Lire et actualiser les dossiers

- Les ADR ouverts précisent contexte, décision ou orientation, conséquences et
  statut. Certains suivent une validation plutôt qu'une nouvelle décision
  d'architecture.
- Les tâches et critères de fin restent dans le dossier concerné, sans
  duplication. Les validations PostgreSQL isolées et les sauvegardes sont dans
  [ADR-0011](adr/0011-exploitation-durable.md).
- Après clôture, retirer l'entrée de cet index et déplacer l'ADR vers
  `adr/archive/`. Reporter dans l'architecture ou le README l'information
  encore utile. Les dossiers ouverts ne pointent pas vers l'archive.
- Les règles de travail, de sécurité et d'autorisation restent dans
  [AGENTS.md](../AGENTS.md). Aucun plan ne vaut autorisation de coder, créer des
  tests/scripts ou modifier le réseau.
