# NecsusDevOverlays — Roadmap

Index du travail restant. L’existant est dans [l’architecture](ARCHITECTURE.md),
l’usage dans le [README](../README.md) et l’état du déploiement dans
[DEPLOY.md](DEPLOY.md#état-et-points-à-confirmer).

## Validations post-déploiement

- Parcours OAuth Twitch avec liaison au navigateur.
- Liens et WebSockets OBS, reconnexions et confiance proxy effective.
- Renouvellement Certbot avec le vhost TLS actif.
- Inaccessibilité de PostgreSQL depuis Tailscale et Internet.
- Administration dans un vrai navigateur : refus de cadrage, aperçu isolé,
  navigation, copie des liens et rendu responsive.
- Disponibilité de `robots.txt` en production.

La validation des protections d’accès doit couvrir révocation des sessions,
comptes désactivés et isolation des propriétaires, pas seulement la connexion
nominale. Les sauvegardes et scénarios de panne sont suivis dans ADR-0011.

## Priorités et dossiers ADR

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

Les trois dossiers Campagnes forment un seul chantier. La découverte métier
peut avancer en parallèle, sans autoriser le développement des extensions.
Les workflows réutilisables communs de `geekom` restent à définir et tester.

## Tenir la documentation à jour

Les ADR ouverts portent décisions, questions et critères de fin, sans répéter
l’implémentation. Après clôture, retirer leur entrée de cet index, déplacer le
dossier dans `adr/archive/` et conserver seulement l’information utile dans
l’architecture ou le README. Les documents ouverts ne pointent pas vers l’archive.

Les règles de travail restent dans [AGENTS.md](../AGENTS.md) ; un plan ne vaut
pas autorisation de coder, tester ou intervenir sur la production.
