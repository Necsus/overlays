# WIS-0002 — Borner le coût des entrées publiques

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** ouvert, aucun correctif. **Priorité :** P1.
**Sévérité :** élevée par impact potentiel sur tous les streamers.
**Catégorie :** CWE-400 / CWE-770, épuisement de ressources.
**Preuve :** code et contrôles locaux bornés ; seuil de saturation non mesuré.

## Faille et preuve

- `/auth/twitch/login` et `/auth/twitch/bot/login` sont publics
  (`app/web/routes/auth.py:37-75`). Chaque appel ajoute un state dans un
  dictionnaire sans plafond (`app/application/oauth_state.py:18-28`).
- Chaque émission parcourt les states pour purger les expirés (`:45-53`).
  L'expiration à 600 s réduit la durée de conservation, pas le nombre possible
  de states dans cette fenêtre ni le coût du parcours répété.
- Le WebSocket est accepté avant authentification, puis chaque token non vide
  déclenche une recherche SQL (`app/web/routes/overlay.py:30-67`). Le délai de
  cinq secondes borne seulement la réception du premier message, pas l'attente
  du verrou ni la résolution SQL suivante.
- `parse_overlay_authentication` ne valide pas longueur/format du token
  (`app/application/overlay_access.py:22-43`) ; il n'y a pas de quota de
  connexions en attente ou par propriétaire dans le gestionnaire.
- Chaque transaction ouvre une connexion SQL (`app/infrastructure/database.py:110-137`).
  Le vhost fourni ne définit pas de limites de débit/connexions
  (`nginx/https/default.conf`).

Contrôles réalisés : 128 states simultanés acceptés et token fictif de 8 Kio
accepté. Aucun flood réseau ni mesure mémoire/SQL effectué. Les bornes de
transport éventuelles d'Uvicorn/Nginx ne sont pas des budgets applicatifs ; leur
configuration réelle et une protection amont éventuelle restent inconnues.

## Scénario et impact

Sans compte Twitch ni clé OBS valide, un client peut multiplier les requêtes de
login et les handshakes OBS avec tokens invalides, accumulant states, tâches et
recherches SQL sérialisées sous le verrou global. Un propriétaire légitime peut
aussi multiplier ses sockets authentifiées.

L'effet potentiel est une dégradation mémoire/CPU/SQL et le retard des logins,
rotations et connexions des autres streamers. Aucun accès à leurs données n'est
établi. Le volume suffisant pour provoquer une panne n'a pas été testé.

## Correction proposée

- Fixer un plafond global des transactions OAuth en attente et une politique
  d'expiration/refus de nouvelles transactions ; éviter le parcours intégral
  systématique quand le volume augmente.
- Prévoir budgets de débit et de connexions sur les endpoints publics, au proxy
  et/ou dans l'application, en utilisant uniquement une IP reconstruite fiable.
- Valider rapidement le format/longueur du token généré par l'application avant
  d'accéder à SQL, sans divulguer la validité ou le propriétaire d'un secret.
- Borner le nombre de handshakes en cours et de sockets par propriétaire ;
  imposer un délai global couvrant réception, attente et résolution.
- Définir les seuils selon l'usage OBS réel ; ne pas ajouter automatiquement un
  pool ou une dépendance. Ces limites complètent le travail sur les verrous
  de [WIS-0003](WIS-0003-network-under-locks.md).

## Critères de clôture — non exécutés

- [ ] États OAuth limités même lors d'appels publics répétés ; expiration correcte.
- [ ] Token absent, trop grand ou mal formé rejeté sans connexion SQL.
- [ ] Quotas et délai total d'authentification observables avec données fictives.
- [ ] Un client refusé ne bloque pas le login/OBS d'un autre streamer.
- [ ] Limites compatibles avec plusieurs sources OBS et reconnexions normales.
- [ ] Validation sous charge bornée, uniquement dans un environnement isolé,
  sans production ni journal contenant des secrets.
