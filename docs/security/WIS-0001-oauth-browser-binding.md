# WIS-0001 — Lier OAuth au navigateur initiateur

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** correctif implémenté et contrôlé localement ; validation réelle restante.
**Priorité :** P1. **Sévérité initiale :** élevée.
**Catégorie :** CWE-352, login CSRF.
**Preuve initiale :** revue et contrôle local ; pas d'exploitation réelle Twitch.

## Faille et preuve avant correctif

Les références suivantes décrivent la révision auditée `41b94b9`, avant modification.

- `app/web/routes/auth.py:37-75` émet un state pour le flux streamer ou bot,
  sans établir de cookie de transaction ni de liaison au navigateur.
- `app/application/oauth_state.py:15-38` conserve seulement expiration et flux.
- `app/web/routes/auth.py:121-184` consomme ce state sans vérifier de contexte
  navigateur ; `:245-260` pose la session de l'identité du code échangé.

Le state est bien aléatoire, expirant et à usage unique. Il prouve toutefois
uniquement qu'une connexion a été initiée **quelque part**, pas par ce navigateur.
Le contrôle local a accepté un state avec `consume(state)` sans autre identité,
puis refusé sa réutilisation et un state inconnu.

## Scénario et impact

Un attaquant lance OAuth et autorise son propre compte Twitch, mais intercepte
son retour avant consommation du code/state. Il fait ensuite ouvrir ce callback
encore valide au navigateur victime, par navigation de premier niveau. Le
serveur peut poser une session du compte attaquant dans ce navigateur.

La victime peut configurer dans OBS un overlay appartenant à l'attaquant, dont
celui-ci maîtrise les commandes sur sa chaîne. Le scopage SQL reste correct,
mais l'identité utilisée ne correspond plus à l'intention de la victime.
**Ce scénario ne démontre pas un vol du token Twitch de la victime**, ni une
usurpation du compte bot : sa vérification d'ID reste en place.

## Correctif implémenté

Le comportement actuel et les cookies sont décrits dans
[l'architecture](../ARCHITECTURE.md#authentification-et-isolation).
Les changements sont limités à `app/application/oauth_state.py` et
`app/web/routes/auth.py` : liaison serveur au secret navigateur, vérification
avant échange du code, consommation atomique après correspondance, et nettoyage
du cookie consommé sur succès ou erreur HTTP gérée. Les flux bot et streamer
conservent leurs scopes et leurs vérifications d'identité.

Aucune dépendance, migration ou configuration de production ajoutée. Aucun
correctif des autres WIS inclus. Le correctif n'est pas déployé par cette étape.
PKCE n'est pas ajouté : son support par Twitch n'a pas été établi.

## Contrôles locaux effectués

**53 contrôles ponctuels ont réussi**, exécutés en mémoire sans fichier de test
ou script créé, avec données fictives et sans accès réseau/SQL ni lecture de
secrets. Le store a été exécuté directement, avec horloge contrôlée et quatre
consommations concurrentes. Les définitions réelles des routes ont été exécutées
avec doublures de FastAPI/réponses, Twitch et finalisation métier ; les cookies
ont été sérialisés via `SimpleCookie`, pas via Starlette. Cela ne valide ni un
navigateur, ni la signature de session, ni les effets SQL réels.

- [x] Cookie absent, mauvais contexte, valeur non ASCII, state inconnu, expiré
  ou rejoué refusés ; consommation atomique unique sous concurrence.
- [x] Mauvais navigateur refusé avant les appels Twitch et les finalisations
  métier simulées ; transaction du navigateur initial encore utilisable.
- [x] Transactions parallèles indépendantes, cookies distincts et scopes bot /
  streamer non mélangés ; cookies échangés entre transactions refusés.
- [x] Cookie consommé supprimé sur succès, annulation, code absent/vide, erreur
  d'autorisation ou transport Twitch simulé ; cookie de session conservé.
- [x] Attributs `HttpOnly`, `SameSite=Lax`, Path `/`, absence de Domain,
  expiration 600 s, `Secure` et préfixe `__Host-` contrôlés en HTTPS ; repli
  HTTP local et option Secure explicite contrôlés. Secret absent de l'URL OAuth.
- [x] Syntaxe Python et absence d'ajout de secrets réels contrôlées.

Les diagnostics LSP n'ont pas pu s'exécuter : serveurs Python `ty` et `ruff`
indisponibles, à installer ou à reconfigurer dans `pi-lsp.json`. Les dépendances
FastAPI/Starlette/TwitchIO ne sont pas installées dans le Python local ; aucun
outil n'a été installé pour les contrôles.

## Critères de clôture restants — non exécutés

- [ ] Vérifier les vraies réponses FastAPI, notamment les multiples `Set-Cookie`
  après création de session et le nettoyage lors des réponses d'erreur.
- [ ] Parcours navigateur streamer et bot en HTTPS derrière le proxy, y compris
  annulation, expiration et deux onglets, sans erreur de cookie `__Host-`.
- [ ] Callback initié dans A et ouvert dans B refusé, puis succès du retour dans A,
  avec clients Twitch/SQL isolés permettant de contrôler l'absence d'effets réels.
- [ ] Vérifier le refus d'injection du cookie par une origine sœur contrôlée en test.
- [ ] Déployer uniquement sur demande explicite, puis valider OAuth réel sans
  exposer de cookies/codes/tokens dans les captures ou journaux.

Les transactions initiées avant redémarrage doivent être relancées ; les
sessions déjà créées ne sont pas révoquées par ce correctif.

Référence : [RFC 9700 §2.1 et §4.7.1](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.7.1),
qui exige la liaison du jeton anti-CSRF à l'agent utilisateur lorsque ce mécanisme
est utilisé pour protéger le callback.
