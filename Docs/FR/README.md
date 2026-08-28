# Jouer des sons avec GFX.Audio

`GFX.Audio` charge des sons réutilisables et contrôle chaque lecture audible
sans exposer devices SDL, mixers, pistes, cartes de canaux ou formats
d’échantillons. Le package s’utilise directement ou avec son plugin
`GFX.Application`.

[Read this documentation in English.](../EN/README.md)

## Installer le package

```text
silex install GFX.Audio
```

GFX.Audio demande Silex 0.39.0 ou une version plus récente.

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

Le volume est un gain linéaire positif ou nul. `1.0` conserve le niveau source ;
les valeurs supérieures peuvent saturer ou devenir dangereusement fortes. La
vitesse va de `0.01` à `100.0` et modifie ensemble le rythme et la hauteur.

`Repeat.once()` joue une fois, `Repeat.times(3)` trois fois au total et
`Repeat.forever()` jusqu’à l’arrêt. `fade_in_seconds` appartient à la demande
initiale ; `stop` accepte une durée de fade-out. Un handle libéré ou collecté ne
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
par checksum existent pour macOS ARM64, Linux x64, Windows x64 et Windows
ARM64 ; cette dernière cible reste reconnue et expérimentale dans la matrice
Silex.

La démonstration [SpatialAudio](https://github.com/Matanek/Silex-Examples/blob/main/Sources/SpatialAudio.sx)
appartient à Silex-Examples.
