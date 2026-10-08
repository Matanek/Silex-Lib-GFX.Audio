# Jouer des sons avec GFX.Audio

`GFX.Audio` charge des sons réutilisables ou les crée depuis des échantillons,
et contrôle chaque lecture audible
sans exposer devices SDL, mixers, pistes, cartes de canaux ou formats natifs
d’échantillons. Le package s’utilise directement ou avec son plugin
`GFX.Application`.

[Read this documentation in English.](../EN/README.md)

[Préparer quelques notes avec un timbre modifiable](Music.md), puis les rejouer sans gérer le PCM.

## Installer le package

```text
silex install GFX.Audio
```

GFX.Audio demande Silex 0.47.1 ou une version plus récente. Pour `Processing`,
utiliser la toolchain locale intégrant la correction des vues mutables par méthode
décrite dans [Traitement des blocs](Processing.md), jusqu’à sa publication.

## Jouer un son dans une application

Installez `GFX.Audio.Plugin` pour rendre la ressource Audio disponible de
`startup` jusqu’à `shutdown` :

```sx
use GFX.Audio as GFXAudio
use GFX.Application
use STD.Math

func start(audio:&GFXAudio.Audio) {
    let explosion = audio.load("Assets/Audio/Explosion.wav")
    let playing = audio.play(explosion, GFXAudio.Playback(
        volume:0.8,
        repeat:GFXAudio.Repeat.once(),
        position:Math.Vec3(4.0, 1.0, -2.0),
    ))
}

func main() {
    Application()
        ..add_plugin(GFXAudio.Plugin())
        ..add_system(Application.Schedule.startup, start)
        ..run()
}
```

`Audio.load` décode le fichier complet et retourne un handle `Audio.Sound`
stable. Un son peut alimenter plusieurs lectures simultanées. `Audio.unload`
invalide le handle, mais les lectures qui le détiennent déjà peuvent finir.

Les artefacts distribués décodent WAV, AIFF, AU, VOC, FLAC, MP3 et Ogg Vorbis.
La prise en charge appartient à l’artefact et ne se déduit pas de l’extension du
fichier.

## Charger depuis la mémoire et traiter un échec

`Audio.try_decode(bytes:@uint8[..])` décode des octets encodés, par exemple
un WAV embarqué. `Audio.try_load(path:str)` charge un fichier. Ces deux
opérations retournent `Result<Sound, STD.Error.Error>` ; `load(path)` conserve
son `panic` sur échec.

Le [programme complet](../MemorySound.sx) charge un WAV sans fichier temporaire :

```sx
use GFX.Audio

func main() {
    var audio = Audio()
    let bytes = embed_bytes("../../Assets/Audio/SpatialTone.wav")
    match audio.try_decode(@bytes[0:bytes.count()]) {
        failure(error) => { panic(error.detail) }
        success(sound) => { audio.wait(audio.play(sound)) }
    }
}
```

Le décodage complet possède son résultat : la source peut être modifiée ou
libérée dès le retour. Les octets vides, tronqués ou non reconnus produisent
`invalid_data`. Un échec d’ouverture de fichier conserve la cause `other`
actuellement fournie par STD.File et le message du provider ; il ne prétend pas
distinguer fichier absent et permission refusée. L’erreur précise aussi
`operation` (`audio.load` ou `audio.decode`) et le chemin dans `subject` pour
un fichier. Un échec n’empêche pas les chargements suivants.

Les handles `Sound` et `PlayingSound` appartiennent à leur instance d’Audio.
Une autre instance ne peut ni les décharger ni contrôler ses propres lectures
avec eux. Les handles périmés restent rejetés même après réutilisation d’une
place ou destruction du propriétaire.

## Créer un son depuis des échantillons

`Audio.create(samples:@float32[..], sample_rate:int, channels:int = 1)` crée
un `Sound` réutilisable depuis une vue d’échantillons. Aucun fichier n’est
nécessaire. Ce programme produit un la de 440 Hz pendant un quart de seconde :

```sx
use GFX.Audio
use GFX.Audio.Processing
use GFX.Audio.Synthesis

func main() {
    let format = Processing.Format(sample_rate:48_000, channels:1)
    match Synthesis.Oscillator.create(format, frequency_hz:440.0, amplitude:0.1) {
        failure(error) => { panic(error.detail) }
        success(var source) => {
            var samples:float32[] = []
            var frame = 0
            while frame < 12_000 { samples.append(0.0); frame++ }
            match source.render(&samples[0:samples.count()]) {
                failure(error) => { panic(error.detail) }; success => {}
            }
            var audio = Audio()
            let sound = audio.create(@samples[0:samples.count()], sample_rate:48_000)
            let playing = audio.play(sound)
            audio.wait(playing)
        }
    }
}
```

La [source exécutable](../GeneratedTone.sx) reprend ce programme. Depuis
`SilexProject/`, lancez `silex run Packages/GFX.Audio/Docs/GeneratedTone.sx`.

Chaque échantillon doit être fini et compris entre `-1.0` et `1.0` ; zéro
représente le silence. `sample_rate` indique le nombre de frames audio par
seconde et doit être compris entre 1 et 2 147 483 647. `channels` vaut 1 par
défaut (mono) et accepte de 1 à 8 canaux. Les canaux sont entrelacés : en
stéréo, les valeurs suivent l’ordre gauche, droite, gauche, droite.
Le tampon doit contenir au moins une frame complète et sa taille doit être
un multiple de `channels`. Une entrée invalide provoque un `panic`.

`create` copie les valeurs avant de retourner. Le tableau source peut donc
être modifié ou libéré immédiatement. La durée du son est
`samples.count() / channels / sample_rate` secondes. Comme un son chargé,
il accepte plusieurs lectures simultanées et tous les contrôles de lecture ;
`unload` invalide son handle sans interrompre les lectures qui le détiennent.
La création porte sur un tampon complet, sans alimentation continue.

## Produire du son par blocs

Un producteur peut alimenter une seule lecture continue avec une capacité
explicite, sans calculer le son entier. Le [guide du flux](Streaming.md) décrit
le préremplissage, les écritures partielles, les contrôles et la fermeture.

## Inspecter et suivre une lecture

Le [guide de chronologie](Timeline.md) décrit format, durée, navigation et
notifications de fin conservées après collecte.

## Contrôler une lecture

`Audio.play` retourne un `Audio.PlayingSound` qui identifie une instance
audible, pas le son réutilisable :

```sx
audio.set_volume(playing, 0.4)
audio.set_speed(playing, 1.1)
audio.pause(playing)
audio.resume(playing)
audio.stop(playing, fade_out_seconds:0.25)
```

Dans un programme direct sans boucle Application, `wait` attend efficacement
la fin de la lecture, y compris pendant une pause.

Le volume est un gain linéaire fini, représentable en `float32`, positif ou nul. `1.0` conserve le niveau source ;
les valeurs supérieures peuvent saturer ou devenir dangereusement fortes. La
vitesse va de `0.01` à `100.0` et modifie ensemble le rythme et la hauteur.

`Repeat.once()` joue une fois, `Repeat.times(3)` trois fois au total et
`Repeat.forever()` jusqu’à l’arrêt. `fade_in_seconds` appartient à la demande
initiale ; `stop` accepte une durée de fade-out. Les durées sont finies et
positives ou nulles ; les réglages non valides provoquent un `panic`. Un handle libéré ou collecté ne
peut pas contrôler une lecture ultérieure réutilisant son slot.

## Positionner un son

Une position peut être fournie au démarrage puis changée :

```sx
let playing = audio.play(ambience, GFXAudio.Playback(
    repeat:GFXAudio.Repeat.forever(),
    position:Math.Vec3(-3.0, 0.0, -1.0),
))

audio.set_position(playing, Math.Vec3(3.0, 0.0, -1.0))
audio.clear_position(playing)
```

Les positions sont relatives à l’auditeur dans un repère droit : X négatif à
gauche, X positif à droite, Y positif vers le haut et Z négatif vers l’avant.
Une application en coordonnées monde doit soustraire la position de l’auditeur
et tourner le résultat dans son espace local.

Ce placement fournit répartition sur les haut-parleurs et atténuation avec la
distance. Il ne promet pas encore HRTF, effet Doppler, modèle de distance ou
rolloff configurables. `set_reverse_stereo` échange les canaux gauche et droit ;
il ne lit pas les échantillons à l’envers.

## Comprendre le cycle de vie et les artefacts

Le plugin ouvre le device de sortie par défaut pendant `startup` sur le thread
principal, collecte les lectures terminées et ferme les lectures et sons
restants pendant `shutdown`. Une application sans renderer de présentation
devrait ajouter `GFX.Application.FramePacing`.

Le package possède son provider SDL3_mixer privé, lequel exige `GFX.SDL3`.
Les handles SDL ne traversent jamais l’API. Des artefacts épinglés et vérifiés
par checksum existent pour macOS, Linux et Windows, en ARM64 et x64.
Le [guide de validation](Validation.md) distingue liaison, exécution et
mesures de ressources.

La démonstration [SpatialAudio](https://github.com/Matanek/Silex-Examples/blob/main/Sources/SpatialAudio.sx)
appartient à Silex-Examples.

[Commander des groupes de lectures](Groups.md).

[Rendre un mix en mémoire](Offline.md).

[Traiter les échantillons et mesurer leurs niveaux](Processing.md).

[Vérifier les parcours audio](Validation.md).

[Fabriquer des sons procéduraux et des enveloppes](Synthesis.md).

[Composer les sources, traitements et modulations](Composition.md).

[Donner au son une texture rétro avec le bitcrusher](Bitcrusher.md).

[Saturer ou distordre un son](Distortion.md).

[Déplacer un son entre gauche et droite](StereoPan.md).

[Créer chorus et flanger avec un délai modulé](ChorusAndFlanger.md).

[Ajouter une réverbération algorithmique](Reverb.md).

[Maîtriser la dynamique avec compresseur et limiteur](Dynamics.md).

## Jouer des notes polyphoniques

Le [guide des instruments](Instruments.md) montre comment jouer une mélodie
avec ADSR, sustain et pitch bend sur une chronologie en frames, sans banque de sons.

[Faire évoluer un son et alimenter un flux](Continuous.md).

[Jouer une partition MIDI avec ses propres instruments](MIDI.md).

[Choisir et adapter une recette procédurale](Recipes.md).

[Choisir les capacités et le budget de production](Resources.md).
