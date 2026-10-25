# ADR-0006 — Bibliothèque de styles CSS Giveaway

[← Roadmap](../ROADMAP.md)

**Statut :** fonctionnalité prévue, non implémentée ; limites à définir.

## Contexte

Sauvegarder, partager et prévisualiser des styles sans piloter OBS à distance.

## Décision ou orientation

Limiter la bibliothèque au Giveaway : styles privés par défaut, partage
explicite, copie manuelle et aperçu isolé.

## Conséquences

S’appuyer sur les [contrôles de propriété existants](../ARCHITECTURE.md#authentification-et-isolation).
L’[aperçu isolé](../ARCHITECTURE.md#administration-et-aperçus) est déjà disponible ;
la persistance et le partage des styles restent à développer.

## Travail associé et validation

Sauvegarder des blocs CSS nommés depuis `/admin`, les retrouver et les copier
dans le champ **CSS personnalisé** de la source navigateur OBS, sans
synchronisation automatique.

### Visibilité et propriété

- Chaque style appartient à un streamer identifié par son identité Twitch stable
  et reste **privé par défaut**.
- Le propriétaire peut créer, consulter, modifier, supprimer son style et
  changer sa visibilité.
- Un style **partagé** est consultable et copiable par tous les streamers
  authentifiés ayant accès au service, mais modifiable uniquement par son
  propriétaire. Aucun catalogue anonyme ni changement d'exposition réseau n'est
  prévu.
- Un streamer peut dupliquer un style partagé dans sa bibliothèque : la copie
  lui appartient, démarre privée et évolue indépendamment de l'original.
- Repasser un style en privé ou le supprimer retire son accès partagé, mais ne
  peut pas révoquer les copies déjà sauvegardées ou collées dans OBS.
  L'interface doit annoncer cette limite avant publication.

### Flux et limites de la V1

```text
/admin → bibliothèque personnelle ou partagée → copier le CSS → coller dans OBS
                         └── dupliquer un style partagé → copie personnelle privée
```

- Prévoir un nom, une description facultative, le contenu CSS, le propriétaire,
  la visibilité et les dates de création/modification. Ajouter ces données à
  PostgreSQL par une migration versionnée, sans les mêler aux secrets ou aux
  clés d'accès OBS.
- Distinguer « Mes styles » et « Styles partagés » ; identifier l'auteur des
  styles partagés avec les seules informations publiques nécessaires.
- Une modification ou suppression dans la bibliothèque ne modifie jamais le CSS
  déjà collé dans OBS. Pour actualiser le rendu, l'utilisateur copie puis colle
  à nouveau le bloc.
- Définir et documenter le contrat des sélecteurs Giveaway avant l’ouverture du
  partage, compteur compris. Le DOM courant est dans
  `app/web/static/plugins/giveaway/overlay.html` ; il ne constitue pas encore
  une promesse de compatibilité avec toutes les versions futures.
- Relier la bibliothèque à l’aperçu existant, puis valider chaque état avec des
  données fictives : compteur avec/sans durée, gagnants multiples, textes longs
  et état masqué. Aucun scénario ne doit toucher au giveaway réel.
- Reporter l'application distante, l'historique de versions, les notes et les
  commentaires. Aucun framework de thèmes ou nouveau plugin n'est nécessaire à
  cette étape.

### Isolation et sécurité

- Les contrôles de propriété sont requis dès la première sauvegarde, même avec
  une seule chaîne active.
- Vérifier les droits côté serveur pour chaque liste, lecture, copie et
  mutation. Ne jamais faire confiance à un propriétaire fourni par le
  navigateur.
  Retourner `404` pour le style privé d'un autre streamer ; refuser toute
  modification d'un style partagé par un non-propriétaire.
- Protéger les mutations contre les requêtes intersites (CSRF). Définir des
  limites de taille, de nombre de styles par propriétaire et une pagination
  avant implémentation.
- Traiter noms, descriptions et CSS comme du contenu non fiable : afficher les
  métadonnées et le code comme du texte, sans injection HTML. Exécuter le CSS
  uniquement dans un aperçu isolé (iframe sandboxée sans accès à l'origine de
  l'administration), jamais dans le document de l'administration. Restreindre
  les capacités de l'iframe et bloquer ses requêtes réseau par une CSP adaptée,
  y compris les imports, images et polices externes ; signaler que ces
  ressources ne seront pas prévisualisées. Ne pas récupérer côté serveur les
  ressources référencées par un style.
- Avertir que le CSS collé dans OBS peut masquer des éléments et charger des
  ressources externes (`url()`, `@import`, polices), donc provoquer des requêtes
  vers des tiers. Ne pas présenter un style partagé comme sûr sans contrôle ;
  inviter à relire le bloc avant utilisation.
- Exclure du partage les liens OBS authentifiés, tokens et autres secrets ; ne
  jamais les ajouter automatiquement au CSS ou aux métadonnées. Rappeler cette
  interdiction avant publication et ne pas journaliser le contenu des blocs.

### Progression et critères de fin

1. Définir les limites et le contrat des sélecteurs ; préparer la persistance et
   les autorisations par propriétaire.
2. Livrer la bibliothèque privée : création, édition, suppression et copie du
   CSS ; vérifier sa conservation après redémarrage.
3. Ajouter la publication explicite, le catalogue partagé et la duplication
   indépendante.
4. Contrôler avec deux identités et des styles fictifs : isolation des styles
   privés, refus des accès anonymes, lecture partagée sans droit d'édition,
   copie privée indépendante, retrait du partage et suppression. Vérifier les
   accès directs à l'API, pas seulement les boutons de l'interface.
5. Intégrer les styles sauvegardés à l’aperçu existant et contrôler son isolation
   et les scénarios ci-dessus dans un vrai navigateur.
6. Valider réellement dans OBS le bloc copié : transparence, états du giveaway,
   gagnants et compteur avec/sans durée. Vérifier qu'une modification du style
   d'origine n'affecte pas la copie ni le rendu déjà configuré dans OBS.

**Terminé quand :** les styles persistent, les droits ci-dessus sont vérifiés,
la prévisualisation isolée couvre chaque état avec des données fictives et le
parcours sauvegarde → partage → copie → OBS fonctionne sans exposer de secrets
ni modifier les giveaways. Distinguer contrôles d'API et validation visuelle
OBS. Les autorisations de tests/scripts restent celles
d'[AGENTS.md](../../AGENTS.md).
