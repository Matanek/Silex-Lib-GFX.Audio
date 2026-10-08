# Choisir le coût d’une lecture musicale

Préparez un son court au chargement, puis réutilisez son handle au déclenchement.
Pour une partition longue, `Music.Player` produit les blocs nécessaires à la
lecture. Les deux parcours permettent de choisir un timbre ou un instrument ;
leur stockage et leur coût au démarrage diffèrent.

| Usage | Préparation | Déclenchement et progression |
| --- | --- | --- |
| Victoire ou notification | `Melody.prepare` calcule le son complet et le confie à Audio | `Audio.play` crée une lecture indépendante sans refaire la synthèse |
| Partition MIDI | Parser les événements et préparer le player, les voix et les effets | `play` préremplit la file ; Audio poursuit la production selon la consommation |

`play` reste une opération allouante. Préparer un son évite son recalcul ; cela
ne supprime pas la création d’une lecture dans le mixer. En jeu, le plugin Audio
alimente les players sur le thread applicatif. `wait` convient à un programme
autonome et bloque volontairement ce thread.

## Stockage d’une partition longue

Les valeurs initiales du player sont 4 800 frames de file et un bloc de 512
frames. À 48 kHz et vitesse 1, la file représente 100 ms. Le scratch contient
un bloc ; la progression de production est bornée par la consommation plus la
file et un bloc. Les métadonnées de partition, voix et mémoires d’effets sont
séparées de cette borne PCM. Une longue partition contient davantage de
métadonnées ; sa durée seule n’impose pas un pré-rendu du morceau.

La qualification utilise une partition de trois heures, 16 notes tenues,
32 commandes et 157 octets MIDI. Elle vérifie le préremplissage et la progression
bornés sans calculer les trois heures de PCM. Les autres oracles contrôlent fin,
queue, replay, événements de même date et écritures partielles.

Le jeu doit alimenter régulièrement le plugin. Adapter la file à sa cadence,
sa fréquence audio et sa vitesse ; une petite file peut sous-alimenter le
convertisseur. Observer `is_starved`, l’état et les erreurs du player.

## Allocations mesurées

Le compteur macOS ARM64 passe ses témoins vide, allocation et copie en Debug et
Release. Le calcul de blocs de l’instrument sinus avec cinq effets et celui de
la recette rétro préparée ne font aucune allocation ou copie libc observée dans
les phases couvertes. Les commandes valides et reset de la recette sont aussi
contrôlés. Le [contrôle avancé](Resources.md) couvre séparément les instruments,
effets, événements et reset du socle.

Le transfert natif packe les échantillons et SDL gère sa file. Le rendu offline
retourne un tableau possédé. Ces chemins allouent même si le DSP préparé
n’alloue pas. Voici les observations Release, en octets cumulés demandés à
l’allocateur, avec la fixture `MusicHeap.sx` à 48 kHz stéréo :

| Phase | Allocations | Octets cumulés |
| --- | ---: | ---: |
| Préparation du son rétro de quatre notes | 106 | 1 408 419 |
| 100 lectures préparées, chacune suivie d’un arrêt | 4 405 | 371 284 |
| Huit lectures superposées, avec collection de handles | 441 | 1 180 216 |
| Parsing du MIDI de trois heures | 17 | 14 208 |
| Préparation instrument sinus + cinq effets + player | 541 | 1 058 794 |
| Préparation recette rétro + player, sans effets | 653 | 307 810 |
| Démarrage/préremplissage, chacun des deux players | 106 | 1 423 523 |
| 100 alimentations et sorties offline, instrument + effets | 1 809 | 15 789 352 |
| 100 alimentations et sorties offline, recette sans effets | 1 807 | 15 772 968 |
| Replay de l’instrument, après arrêt | 155 | 1 641 285 |

Pause/reprise et arrêt demandent zéro allocation observée dans ces phases.
Les lectures répétées incluent ici leurs arrêts ; la collection des huit handles
est incluse dans la phase de recouvrement. Les octets cumulés comptent aussi la
croissance des buffers et les temporaires : ils ne représentent ni la mémoire
résidente ni un pic de mémoire. Les copies inline et les autres threads ne sont
pas couverts. Le témoin d’allocation x64 est invisible à cet interposeur ; aucun
verdict d’absence d’allocation n’est déduit sur cette cible.

## Durées et marge

Release, Apple M3 Pro, macOS 26.6.2. Chaque charge tient 16 notes graves
(48..63, vélocité 32/127), avec amplitude 0,025 et cinq effets : passe-bas 8 kHz,
chorus 960±240 frames à 0,7 Hz, feedback 0,1, wet 0,25 ; réverbération
taille 0,5, decay 1,5 s, damping 0,5, wet 0,3 ; compresseur initial et limiteur −3 dB.
Sept répétitions dans un ordre tournant, 64 blocs d’échauffement puis 1 000
blocs par répétition. Le tableau mesure alimentation et rendu offline complet,
avec transfert natif et allocation de sortie ; le DSP seul est séparé ci-dessous.

| Cible | Réalisation | Frames | Médiane (ms) | p95 (ms) | Max (ms) |
| --- | --- | ---: | ---: | ---: | ---: |
| ARM64 | Sinus + 5 FX | 128 | 2,633 | 4,922 | 5,568 |
| ARM64 | Sinus + 5 FX | 512 | 5,152 | 8,029 | 9,838 |
| ARM64 | Rétro + 5 FX | 128 | 10,443 | 13,514 | 17,655 |
| ARM64 | Rétro + 5 FX | 512 | 34,330 | 38,768 | 68,048 |
| x64/Rosetta | Sinus + 5 FX | 128 | 5,080 | 8,172 | 638,870 |
| x64/Rosetta | Sinus + 5 FX | 512 | 11,920 | 15,129 | 147,115 |
| x64/Rosetta | Rétro + 5 FX | 128 | 20,999 | 24,679 | 41,839 |
| x64/Rosetta | Rétro + 5 FX | 512 | 68,577 | 76,315 | 112,216 |

Le budget à 48 kHz vaut 2,667 ms pour 128 frames et 10,667 ms pour 512.
Sur ARM64, le sinus/512 utilise 48 % du budget en médiane, 75 % au p95 et
92 % au maximum. Le sinus/128 dépasse le budget au p95 ; la charge rétro dense
le dépasse déjà en médiane. Ces charges ne qualifient pas automatiquement un
jeu chargé. Réduire la polyphonie ou choisir une réalisation moins coûteuse,
puis mesurer le parcours du jeu sur sa machine.

Le DSP sinus avec cinq effets, mesuré dans l’instrument, vaut sur ARM64
0,748/1,649/2,329 ms (médiane/p95/max, 128 frames) et
3,309/5,797/6,856 ms (512). Sous Rosetta :
1,919/3,704/66,141 ms (128) et 8,248/11,843/145,138 ms (512).
Ce temps inclut les lectures d’horloge du témoin. Le temps DSP de la recette
rétro n’est pas isolé dans cette campagne de durées.

Préparer le son court prend une médiane de 94,493 ms sur ARM64 et 183,562 ms
sous Rosetta (sept observations). Un play préparé, hors arrêt, prend une
médiane/p95/max de 24/30/172 µs sur ARM64 et 15/56/215 µs sous Rosetta
(700 observations). Les lectures répétées mesurées pour les allocations
incluent aussi leurs arrêts ; ces deux métriques ont donc des frontières différentes.

Les médianes par répétition varient de 2,369 à 2,867 ms pour sinus/128 ARM64,
et de 3,659 à 5,612 ms sous Rosetta ; celles du rétro/512 vont de 33,547 à
34,900 ms et de 64,514 à 71,349 ms. Rosetta présente une dérive et un pic
à 639 ms : aucune estimation stationnaire ni marge positive n’en est déduite.
Elle ne représente pas les performances d’un processeur Intel/AMD natif.
Aucune compilation propre n’accompagne les mesures, mais les autres activités
hôte ne sont pas isolées. Contrôles de niveaux et collecte des observations
restent hors intervalle. L’offline ne mesure ni le périphérique ni l’ordonnancement
d’un jeu. Aucun seuil fragile ou certification de temps réel dur n’est ajouté.


## Reproduire et adapter

Depuis la racine du workspace ou du groupe Worktree de la Spec :

```sh
python3 Packages/GFX.Audio/Tests/Resources/ValidateMusic.py
```

Le contrôle requiert macOS ARM64 et Clang. Il crée une copie temporaire du
package pour instrumenter sa recette privée et restaure le lien workspace dans
`finally`. N’exécutez pas une autre compilation dépendant d’Audio pendant ce
contrôle. Le propriétaire et son provider restent intacts. Voir les
[instructions de la fixture](../../Tests/Resources/README.md).

Les sources de production mesurées sont celles d’Audio
`d1ce09a0b9887d58ce3a89ea584a34b3d0dc57c2`, avec Silex
`b8b81e996181b138283f6186360efe22d5845335`. Les ajouts de qualification ne
modifient pas ces sources. Les six cibles se qualifient séparément par liaison ;
les allocations et les durées ci-dessus ne sont pas des preuves de ressources
sur Linux ou Windows.

[Préparer une mélodie](Music.md) · [Commander le player MIDI](MusicPlayer.md) ·
[Vérifier les parcours audio](Validation.md)
