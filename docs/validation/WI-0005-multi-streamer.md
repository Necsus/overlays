# WI-0005 — Isolation multi-streamer

- [ ] Préparer la recette : version déployée, deux chaînes A/B, profils séparés, bot unique, données temporaires et accords nécessaires, dont l'impact du redémarrage global.
- [ ] R01 — Vérifier l'indépendance des préfixes, commandes, inscriptions/doublons, tirages, historique et affichages OBS ; empêcher qu'un ancien onglet A agisse pour B après changement de compte.
- [ ] R02 — Refuser les accès directs croisés ; déconnecter une session sans invalider les autres ; désactiver A : sessions, OAuth et OBS refusés après observation, chat/minuteur et B préservés ; réactiver sans ressusciter les sessions révoquées.
- [ ] R03 — Vérifier rotation OBS de A (ancienne clé/sockets refusées, nouvelle clé valide), puis révocation et réabonnement EventSub ciblés, même concurrents : chat seul affecté ; administration, minuteur, OBS et B préservés.
- [ ] R04 — Après redémarrage autorisé, restaurer les deux états/échéances et traiter les expirations pendant l'arrêt, avec/sans participants, sans tirage doublé ni croisement ; reprendre chat/minuteur d'un compte désactivé, invalider les anciennes sessions et conserver les clés OBS.
