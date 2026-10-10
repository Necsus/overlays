# WIS-0006 — Interdire le cadrage de l'administration

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** ouvert, aucun correctif. **Priorité :** P2.
**Sévérité :** faible, exploitation conditionnelle.
**Catégorie :** CWE-1021, clickjacking / restriction de cadrage absente.
**Preuve :** absence de politique dans le dépôt ; navigateur et en-têtes réels non testés.

## Faille et preuve

`/admin` sert directement le HTML (`app/web/routes/admin.py:37-39`). Ni
`app/main.py`, ni le vhost `nginx/https/default.conf` ne définissent
`Content-Security-Policy: frame-ancestors ...` ou `X-Frame-Options`. Le HTML
administratif n'a pas de protection équivalente. La CSP de l'aperçu CSS protège
son document enfant, **pas le cadrage du document administratif parent**.

La configuration commune du Nginx installé pourrait ajouter ces en-têtes ; elle
n'est pas dans ce dépôt et n'a pas été vérifiée. Le constat porte donc sur la
protection manquante dans la configuration fournie, pas sur une capture des
réponses de production.

## Conditions et impact

Un document contrôlé par un attaquant peut tenter de charger `/admin` dans une
iframe et de superposer des éléments trompeurs aux actions de l'interface.
Le navigateur victime doit encore disposer d'une session transmise à cette iframe.

**`SameSite=Lax` bloque normalement ce cookie dans une iframe cross-site** :
une attaque authentifiée depuis n'importe quel domaine externe n'est donc pas
établie. Un scénario pertinent est une origine hostile **same-site**, telle
qu'un sous-domaine frère du domaine applicatif compromis ou contrôlé par un
attaquant. Aucune telle origine compromise n'a été identifiée pendant cet audit.
Les politiques navigateur peuvent également limiter le scénario.

Dans ces conditions, l'utilisateur peut être trompé pour déclencher une action
administrative, comme changer un préfixe ou générer un lien. La régénération
possède une confirmation qui ajoute une interaction ; la lecture automatique
par l'attaquant du lien OBS ou des données n'est pas démontrée, la politique
same-origin continuant à s'appliquer.

## Correction proposée

- Servir un en-tête CSP `frame-ancestors 'none'` sur l'administration, avec
  `X-Frame-Options: DENY` en défense complémentaire selon les navigateurs ciblés.
- Utiliser un **en-tête HTTP**, pas une balise meta pour `frame-ancestors`.
- Appliquer la politique au bon document, sans confondre le parent `/admin`,
  son aperçu `srcdoc` sandboxé et la page OBS. Vérifier la compatibilité OBS
  avant d'étendre une politique à toute l'origine.
- Une future CSP générale doit aussi tenir compte du renderer d'aperçu à nonce,
  des styles et de l'avatar Twitch ; ne pas ajouter une règle globale au hasard.

## Critères de clôture — non exécutés

- [ ] En-têtes anti-cadrage présents sur `/admin` dans les réponses réellement servies.
- [ ] Navigateur refuse le cadrage depuis une origine externe et une origine
  same-site distincte, dans un environnement de test contrôlé.
- [ ] Authentification et usage direct de l'administration fonctionnels.
- [ ] Aperçu CSS sandboxé et source navigateur OBS toujours fonctionnels.
- [ ] Aucun test avec sous-domaines ou cookies réels de production.
