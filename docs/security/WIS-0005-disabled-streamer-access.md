# WIS-0005 — Appliquer le statut d'accès du streamer sur toutes les surfaces

[← Audit](AUDIT.md) · [← Roadmap](../ROADMAP.md)

**Statut :** ouvert, aucun correctif. **Priorité :** P2. **Sévérité :** modérée.
**Catégorie :** CWE-863, autorisation incohérente.
**Preuve :** revue et inspection SQL ; désactivation réelle non exécutée.

## Faille et preuve

Le modèle contient `streamers.enabled`. `load_streamer()` filtre sur ce statut
(`app/infrastructure/streamers.py:40-48`), utilisé par `/api/admin/session` et
les préférences (`app/web/routes/admin.py:43-50`, `:150-170`). En revanche :

- `require_session_identity` vérifie uniquement le cookie signé, sans charger le
  streamer (`app/web/dependencies.py:12-35`).
- Historique, état et rotation de clé utilisent cette identité sans appliquer
  `enabled` (`app/web/routes/admin.py:73-146`). Les requêtes restent filtrées
  par propriétaire : il ne s'agit pas d'une IDOR.
- `resolve_overlay_access_key` lit la clé sans joindre `streamers` ni contrôler
  `enabled` (`app/infrastructure/overlay_access.py:25-36`). La route OBS vérifie
  ensuite seulement l'existence du contexte en mémoire (`overlay.py:62-66`).

Ainsi, passer A à `enabled=false` peut faire refuser la page de session et les
préférences, tout en laissant son ancien cookie accéder aux autres API. Tant que
son contexte reste en mémoire, sa clé peut aussi ouvrir un nouveau socket ;
les sockets déjà ouverts ne sont pas réévalués automatiquement. Au redémarrage,
les contextes sont restaurés seulement pour les streamers actifs : ce blocage
indirect des nouveaux sockets ne corrige pas les API administratives.

Contrôles locaux : la dépendance accepte une identité avec faux signataire sans
même avoir de base disponible ; le SQL du résolveur OBS ne contient aucun
filtre d'activité. Aucun compte réel n'a été désactivé.

## Condition et impact

Il n'existe pas de route de désactivation dans le dépôt. Ce défaut devient
opérationnel lorsqu'un exploitant désactive un compte via un outil externe ou
lorsqu'une future fonctionnalité s'appuie sur ce statut. Ne pas supposer que
`enabled=false` constitue déjà une révocation fiable.

De plus, un nouveau login valide remet systématiquement `enabled=TRUE`
(`streamers.py:19-26`) : ce statut n'est pas aujourd'hui une politique de
bannissement persistante. La suppression du routage EventSub est, elle, décrite
comme une interruption du chat, pas une révocation automatique d'OBS ; les deux
notions ne doivent pas être confondues.

## Correction proposée

- Définir explicitement activité du chat, accès web/OBS et interdiction de
  réinscription ; ne pas utiliser un même booléen pour des sens incompatibles.
- Si `enabled` porte l'accès, centraliser sa vérification pour toutes les API
  administratives et la résolution OBS, indépendamment de l'interface web.
- Une désactivation d'accès doit révoquer les sessions concernées et fermer les
  sockets du propriétaire, sans affecter les autres streamers ; définir aussi
  ce qu'il advient des minuteurs.
- Si une interdiction persistante est nécessaire, un login ne doit pas la
  réinitialiser automatiquement. Cette politique doit être décidée avant codage.

## Critères de clôture — non exécutés

- [ ] Statut et contrat de révocation définis sans ambiguïté.
- [ ] A désactivé ne peut plus lire son historique ni créer de clé avec son cookie.
- [ ] Nouvelle connexion OBS de A refusée ; sockets existants fermés selon contrat.
- [ ] B reste utilisable pendant cette désactivation et après redémarrage.
- [ ] Nouveau login respecte la politique d'admission/réactivation décidée.
- [ ] Vérifications API directes avec deux comptes fictifs en SQL isolé, et pas
  uniquement un masquage de l'interface frontend.
