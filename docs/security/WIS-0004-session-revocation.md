# WIS-0004 — Invalider réellement une session lors de la déconnexion

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** ouvert, aucun correctif. **Priorité :** P2. **Sévérité :** modérée.
**Catégorie :** CWE-613, révocation insuffisante des sessions.
**Preuve :** revue et simulation route/dépendance, signataire fictif.

## Faille et preuve

`/auth/logout` efface uniquement le cookie du navigateur
(`app/web/routes/auth.py:269-280`). Le cookie signé contient seulement l'identité
Twitch ; sa vérification utilise signature et âge maximal, sans identifiant de
session révocable ni version serveur (`app/application/session.py:33-59`).
La dépendance administrative ne consulte pas d'état de révocation
(`app/web/dependencies.py:12-35`).

La simulation a appelé cette dépendance avant et après la route logout avec une
même valeur fictive : l'identité reste acceptée, alors que la réponse demande
bien au navigateur d'effacer le cookie. Le signataire était une doublure : la
cryptographie `itsdangerous` n'a pas été testée. Le contrôle vérifie l'absence
d'effet de la route sur la validation côté serveur, confirmée par le code.

## Scénario et impact

Si un cookie a été copié auparavant (poste partagé, extension hostile ou autre
compromission), le détenteur peut le rejouer après la déconnexion de l'utilisateur.
Il reste valide jusqu'à expiration — 8 heures par défaut, selon configuration —
ou changement du secret global.

L'attaquant conserve les droits de **ce** streamer : historique et génération
d'une nouvelle clé OBS notamment. Ce constat ne prouve ni qu'un cookie a été
volé ni un contournement du scopage inter-streamer. `HttpOnly`, `Secure` et
`SameSite` réduisent certains vols/abus, sans révoquer une copie déjà détenue.
La déconnexion ne doit pas révoquer par erreur les clés OBS indépendantes.

## Correction proposée

Ajouter un mécanisme serveur d'invalidation, au choix : sessions identifiées et
révocables, ou version d'authentification du streamer signée dans le cookie et
vérifiée à chaque accès. Choisir explicitement si logout invalide une session
ou toutes celles du compte ; éviter une liste de révocation sans expiration.

Ne pas imposer la rotation du secret global comme seule réponse à une session
compromise : elle déconnecterait tous les streamers. Coordonner le contrôle
serveur avec [WIS-0005](WIS-0005-disabled-streamer-access.md).

## Critères de clôture — non exécutés

- [ ] Un cookie fictif valide, conservé avant logout, reçoit `401` lors de son rejeu.
- [ ] La révocation de A ne déconnecte pas B ; politique multi-onglets documentée.
- [ ] Expiration, signature falsifiée et sessions inconnues restent refusées.
- [ ] Invalidation conservée après redémarrage, si le cookie peut lui survivre.
- [ ] Déconnexion et nouvelle connexion ne restaurent pas une session révoquée.
- [ ] Sources OBS continuent selon la politique indépendante de leurs clés.
- [ ] Tests avec véritable signataire et routes FastAPI en environnement isolé.
