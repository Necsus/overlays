# NecsusDevOverlays — Roadmap

Ce fichier est l’index du travail restant. L’existant est décrit dans
[l’architecture](ARCHITECTURE.md) ; l’installation et l’usage dans le
[README](../README.md).

## Chantier actif — déploiement et validations de production

PostgreSQL central et l’accès pgAdmin LAN/TLS sont en service. Le conteneur
applicatif est arrêté en attente de la publication des changements locaux du
workflow et du Compose ; voir [DEPLOY.md](DEPLOY.md#état-et-points-à-confirmer).

- Publier les changements du workflow/Compose, redéployer l’application et
  vérifier migrations, santé et OAuth via le service central.
- Valider HTTPS depuis l’extérieur, les liens OBS générés, le WebSocket OBS et
  le renouvellement Certbot avec le vhost TLS.
- Définir et tester les sauvegardes/restaurations du volume PostgreSQL central.
- Confirmer l’inaccessibilité du port PostgreSQL depuis Tailscale et Internet.
- Définir le contrat et les workflows réutilisables communs de `geekom`.

## Sécurité — audit après mise en production

L'[audit du dépôt](security/AUDIT.md) distingue les constats locaux des
validations de production encore nécessaires. Le statut des correctifs,
les tâches et les critères de clôture sont dans chaque WIS.

- [WIS-0001 — Liaison OAuth au navigateur](security/WIS-0001-oauth-browser-binding.md)
- [WIS-0002 — Limites des entrées publiques](security/WIS-0002-public-resource-limits.md)
- [WIS-0003 — Attentes réseau sous verrous](security/WIS-0003-network-under-locks.md)
- [WIS-0004 — Révocation des sessions](security/WIS-0004-session-revocation.md)
- [WIS-0005 — Accès des streamers désactivés](security/WIS-0005-disabled-streamer-access.md)
- [WIS-0006 — Anti-cadrage de l'administration](security/WIS-0006-admin-framing.md)

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
