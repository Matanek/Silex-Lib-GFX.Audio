# Historique

## [Unreleased]

- Traitements de blocs à état : passe-bas, délai/écho, égalisation trois bandes et crête/RMS. Vues mutables sur le thread applicatif, réglages récupérables et remise à zéro explicite.

- Audio.offline et render produisent du PCM possédé par blocs, sans périphérique, normalisation ni écrêtage caché.

- Groupes de lecture : gains composés, pauses indépendantes, réaffectation et destruction sans perdre les réglages individuels.

- Format et durée explicite des sources, départ/navigation en frames et observation bornée des fins. Un déplacement efface les frames converties de l’ancienne position.

- Flux PCM bornés : alimentation par blocs copiés, saturation récupérable, pause/reprise, fermeture avec vidage du filtre, compteurs de consommation et d’abandon. Provider privé reconstruit pour les six cibles ; coordonnées 3D et inversion stéréo multicanal corrigées.

- `Audio.try_decode` charge des octets encodés possédés ; `Audio.try_load` permet de traiter les erreurs sans arrêter le programme. Les handles sont protégés entre instances d’Audio.

- `Audio.create` crée un son réutilisable depuis des échantillons `float32`
  mono ou entrelacés, avec fréquence et nombre de canaux configurables. Le son
  possède sa copie et accepte les contrôles de lecture existants.
