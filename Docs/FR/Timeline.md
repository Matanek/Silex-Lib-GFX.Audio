# Inspecter un son et suivre sa lecture

`sound_info(sound)` retourne un résultat récupérable contenant fréquence,
canaux et `Duration` : `frames(count)`, `unknown` ou `infinite`.
`duration_seconds()` donne des secondes optionnelles pour une durée finie.
La durée décrit la source sans répétition ni vitesse ; le format est celui
initialement décodé. [Timeline.sx](../Timeline.sx) montre un parcours complet.

`Playback(start_frame:...)` choisit une frame initiale entre zéro et la durée
connue, fin incluse. Les répétitions suivantes reviennent à zéro.
`seek_frames(playing, frame)` retourne un résultat récupérable ; un flux continu
retourne `unsupported`. Une frame contient un échantillon par canal. Le déplacement
conserve pause et vitesse et abandonne la sortie convertie encore dans le mixer,
avec l’historique de son filtre. Le périphérique peut déjà détenir un petit bloc.
La précision du codec peut être inférieure à celle du PCM pré-décodé.

`playback_info(playing)` donne position en frames de source, fréquence, lecture
et pause. La vitesse change rythme et hauteur ; la position repart au début
lors d’une répétition. Ce n’est pas une horloge des haut-parleurs. Un handle
collecté ou libéré renvoie `invalid_input` pour ces opérations récupérables.

## Recevoir une fin sans bloquer

Après `play`, appeler `watch_end(playing)`, puis `drain_end_events()` depuis
le contexte applicatif. Chaque `EndEvent` conserve le handle initial et une
raison `finished`, `stopped` ou `released`. `event.playback.matches(playing)`
compare l’identité, même après réutilisation d’un slot. La notification est
émise au plus une fois, après vidage du mixer ou lors de la libération.
Le premier motif terminal observé reste conservé : un arrêt demandé avant une
libération garde `stopped` ; une fin déjà détectée garde `finished`. Décharger
un Sound ne termine pas ses lectures.

L’observation explicite évite d’accumuler des notifications dans les programmes
existants. File et réservations réunies contiennent au plus 256 événements.
`watch_end` renvoie `would_block` à saturation sans arrêter la lecture ni perdre
une notification acceptée. Drainer libère de la capacité ; une demande acceptée
répétée est idempotente. Demander après collecte échoue ; demander avant la
prochaine collecte peut observer une piste déjà terminée. Le plugin collecte
les ressources mais conserve les notifications jusqu’au drainage. Aucun callback
utilisateur ne s’exécute sur le thread audio.

[Retour au guide Audio](README.md)
