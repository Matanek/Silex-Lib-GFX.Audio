# Historique

## [Unreleased]

- Panoramique stéréo par transfert sin/cos du canal opposé, centre neutre et pôles exacts ; dosage/bypass, dépassement récupérable et démonstration par blocs.

- Saturation douce et distorsion dure composables : drive, gain de sortie, dosage et bypass, calcul float32 stabilisé et exemples sans asset.

- Bitcrusher composable : résolution de 2 à 24 bits, maintien indépendant entre blocs, dosage et bypass ; grille signée de 256 niveaux à 8 bits, reset et recette rétro sans asset.

- Composition : mélange dosé, chaîne ordonnée de traitements extensibles, courbe linéaire, modulation d’amplitude et FM sinusoïdale avec contrôles mono, états persistants et tampons préparés.

- Synthèse : triangle, carré à rapport cyclique et dent de scie à harmoniques bornées sous Nyquist, ainsi qu’un bruit rose reproductible. Une palette exécutable compare les timbres ; un oracle spectral indépendant vérifie les formes et les bruits en Debug et Release.

- `GFX.Audio.Synthesis` ajoute un générateur extensible, un oscillateur sinus, un bruit blanc avec graine et une enveloppe ADSR. Rendu dans des vues préparées, état conservé entre blocs, paramètres récupérables et exemples sans banque de sons.

- Flux et groupes qualifiés ensemble : pauses indépendantes, fins stables et propriété des handles. La durée en secondes reste disponible pour les grandes durées en frames.

- Traitements de blocs à état : passe-bas, délai/écho, égalisation trois bandes et crête/RMS. Vues mutables sur le thread applicatif, réglages récupérables et remise à zéro explicite.

- Audio.offline et render produisent du PCM possédé par blocs, sans périphérique, normalisation ni écrêtage caché.

- Groupes de lecture : gains composés, pauses indépendantes, réaffectation et destruction sans perdre les réglages individuels.

- Format et durée explicite des sources, départ/navigation en frames et observation bornée des fins. Un déplacement efface les frames converties de l’ancienne position.

- Flux PCM bornés : alimentation par blocs copiés, saturation récupérable, pause/reprise, fermeture avec vidage du filtre, compteurs de consommation et d’abandon. Provider privé reconstruit pour les six cibles ; coordonnées 3D et inversion stéréo multicanal corrigées.

- `Audio.try_decode` charge des octets encodés possédés ; `Audio.try_load` permet de traiter les erreurs sans arrêter le programme. Les handles sont protégés entre instances d’Audio.

- `Audio.create` crée un son réutilisable depuis des échantillons `float32`
  mono ou entrelacés, avec fréquence et nombre de canaux configurables. Le son
  possède sa copie et accepte les contrôles de lecture existants.
