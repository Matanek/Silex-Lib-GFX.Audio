# Donner au son une texture rétro

`Processing.Bitcrusher` réduit la précision d'amplitude et maintient les
échantillons pendant plusieurs frames. Les deux réglages sont indépendants :
8 bits donnent 256 niveaux ; `hold_frames:6` à 48 kHz capture 8 000 valeurs
par seconde et par canal. La sortie reste du PCM float32 à 48 kHz, avec le
même nombre de frames et de canaux.

La [démonstration exécutable](../../Examples/RetroSounds.sx) compare le même sinus sec,
à 8 bits, à 4 bits, puis à 24 bits avec maintien. Elle joue ensuite un arpège
carré et un impact bruité, sans fichier ni banque de sons. Depuis la racine
`SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/RetroSounds.sx --release
```

Elle prépare le PCM en mémoire, quantifie avant l'enveloppe et atténue
explicitement la sortie. Cela garde l'effet audible tout en adoucissant les
départs et les fins. Les huit notes occupent chacune 9 600 frames à 48 kHz ;
cette recette ne fournit pas encore un transport musical ou une entrée MIDI.

## Insérer et régler l'effet

L'effet implémente [Processing.Processor](Processing.md). Il traite une vue
mutable sur le thread applicatif et peut rejoindre une chaîne
[Synthesis.Processed](Composition.md), avant ou après les autres traitements.
Voici le fragment à utiliser une fois `format` et `samples` préparés :

```sx
match try Processing.Bitcrusher.create(format, bits:8, hold_frames:6, wet:0.75) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match try effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

Conserver la même instance entre les blocs pour conserver le maintien.
Comme les autres effets de classe, ses références partagent réglages et état.
Construire des instances fraîches pour des lectures indépendantes.

| Réglage | Défaut | Domaine | Changement |
| --- | --- | --- | --- |
| `bits`, `set_bits(bits)` | 8 | Entier de 2 à 24 | Capture à la prochaine frame |
| `hold_frames`, `set_hold_frames(hold_frames)` | 1 | Entier de 1 à 16 777 216 | Capture à la prochaine frame |
| `wet`, `set_wet(wet)` | 1 | Float32 fini de 0 à 1 | Immédiat, horloge conservée |
| `set_bypass(bypass)` | false | Booléen | Immédiat, horloge conservée |

Les trois setters numériques retournent `Result<void, Error>` ; un refus
conserve le réglage et l'état. Un appel valide à `set_bits` ou
`set_hold_frames` provoque une capture même si la valeur est identique.
`reset()` efface le maintien et provoque une capture au prochain échantillon,
en conservant les réglages, notamment wet et bypass. Aucun lissage automatique
ne masque les changements : une application qui souhaite une transition douce
prépare sa rampe de dosage.

## Comprendre les niveaux et le maintien

Avec `scale = 2^(bits - 1)`, chaque capture sature l'entrée à
`[-1, 1 - 1/scale]`, arrondit `entrée * scale` à l'entier le plus proche
(égalité vers l'entier pair), puis divise par scale. À 8 bits, les codes vont
de −128 à 127 : −1, −127/128, …, 0, …, 127/128. Zéro reste silencieux ;
+1 donne 127/128. Cette saturation appartient explicitement au timbre traité.
Les valeurs sèches finies au-delà de ±1 restent acceptées.

La première frame capture tous les canaux, puis chaque valeur quantifiée est
réutilisée pendant `hold_frames` frames, capture comprise. Les canaux ont
leurs propres valeurs et une horloge commune. Une coupure de bloc ne change
pas l'horloge ; un bloc vide ne l'avance pas. Le maintien émet dès la première frame : aucune frame de latence de traitement
ou queue ajoutée. Il ne modifie ni fréquence déclarée, ni longueur de sortie ;
il peut changer la phase spectrale du signal.

La sortie vaut `(1 - wet) * entrée + wet * valeur_maintenue`. Wet=1 utilise
la valeur traitée ; wet=0 et bypass conservent exactement les samples secs.
Dans ces deux derniers cas, les captures continuent : réactiver l'effet
retrouve la position courante du maintien. Le signal mélangé peut dépasser ±1
si la partie sèche les dépasse ; choisir son niveau avant `Audio.create` ou
l'écriture dans un flux.

Le maintien n'emploie pas de filtre anti-repliement : l'aliasing et les marches
font partie de cet effet. Il ne remplace pas la limitation harmonique des
oscillateurs et ne simule pas une console précise. Pour isoler le maintien,
24 bits rendent la quantification faible ; pour isoler les bits, garder
`hold_frames:1`.

## Validation et ressources

Les formats suivent `Processing.Format` : 1 à 2 147 483 647 Hz, 1 à 8 canaux,
frames entrelacées complètes. Tout sample non fini, y compris sous bypass,
est rejeté avec `invalid_input`, opération `audio.process`, avant écriture
ou changement d'état. Le buffer n'est pas conservé après `process`.

L'effet prépare un historique par canal à la création et ne crée pas de tableau
pendant `process`. Le coût est linéaire dans le nombre de samples, avec
quantification seulement aux captures. Cette propriété ne constitue pas une
garantie de latence temps réel ; les règles des vues et du thread applicatif
restent celles du [traitement des blocs](Processing.md).

[Les oracles numériques et la qualification](Validation.md) contrôlent grille,
arrondis, maintien, découpage, reset, dosage, bypass et composition externe.
