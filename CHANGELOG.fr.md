# Historique

## [Unreleased]

- `Audio.try_decode` charge des octets encodés possédés ; `Audio.try_load` permet de traiter les erreurs sans arrêter le programme. Les handles sont protégés entre instances d’Audio.

- `Audio.create` crée un son réutilisable depuis des échantillons `float32`
  mono ou entrelacés, avec fréquence et nombre de canaux configurables. Le son
  possède sa copie et accepte les contrôles de lecture existants.
