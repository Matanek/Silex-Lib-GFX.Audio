# Jouer un piano procédural

`Music.Instruments.piano()` crée un piano polyphonique sans banque sonore.
Écrire les notes, choisir le piano puis préparer et jouer la mélodie :

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.C4, beats:0.5, velocity:0.4),
        Music.Note(key:Music.Key.E4, beats:0.5, velocity:0.7),
        Music.Note(key:Music.Key.G4, beats:1.0, velocity:1.0),
    ], tempo:110.0) else error { panic(error.detail) }
    var piano = try Music.Instruments.piano() else error { panic(error.detail) }
    let sound = try melody.prepare(audio, using:piano, tail_seconds:0.2) else error { panic(error.detail) }
    audio.wait(audio.play(sound))
    assert(audio.unload(sound))
}
```

[Écouter le registre, les réglages et trois vélocités](../../Examples/Piano.sx) :

```sh
silex run Packages/GFX.Audio/Examples/Piano.sx --release
```

Exécuter depuis la racine SilexProject. La préparation calcule le son une fois ;
les lectures suivantes réutilisent le Sound. Le piano peut aussi être passé à
[Music.Player](MusicPlayer.md) pour une partition MIDI, avec `using:piano`.
Le player MIDI de Silex-Examples propose `--piano`.

## Choisir le caractère du piano

| Réglage | Défaut | Signification et plage |
|---|---|---|
| `amplitude` | 0,2 | Niveau maximal d’une voix avant gain, 0..1 |
| `brightness` | 0,65 | Brillance de la frappe, 0..1 ; la vélocité la module aussi |
| `decay_seconds` | 3 | Temps de perte de 60 dB du fondamental à A4, >0..30 s |
| `release_seconds` | 0,15 | Durée d’étouffement après relâchement, 0..5 s |
| `max_voices` | 16 | Capacité allouée à la création, 1..64 |
| `voice_policy` | `steal_oldest` | Remplacer le départ le plus ancien ou `reject` |
| `steal_fade_seconds` | 0,001 | Raccord lors du remplacement, 0..4 096 frames |
| `format` | 48 kHz mono | 1..192 000 Hz, 1..8 canaux |

Les secondes sont arrondies à la frame la plus proche. Le déclin doit occuper
au moins une frame ; les autres durées acceptent zéro. Le format doit correspondre
à celui de la préparation ou du player. Les réglages non finis ou hors plage
retournent un `Result` en échec avant création.

Le son décroît même lorsque la touche reste enfoncée. Les graves décroissent
plus lentement, les aigus plus vite ; les partiels aigus s’éteignent plus tôt.
Une frappe forte augmente le niveau et enrichit le spectre. `brightness` change
la couleur sans changer les notes. Chaque voix finit naturellement au bout
d’environ 80 dB de décroissance du fondamental, même pédale enfoncée.

Les [commandes d’instrument](Instruments.md) permettent accords, identités de
notes distinctes, sustain, bend et rampes de gain. La pédale retarde l’étouffement
des touches relâchées ; elle ne fige pas leur énergie. `all_notes_off` étouffe
toutes les voix même sous pédale. `reset()` coupe les voix immédiatement et
conserve les réglages. Prévoir une queue au moins aussi longue que le relâchement
pour éviter de couper celui-ci à la fin d’une mélodie ou partition.

## Modèle et ressources

Le modèle combine jusqu’à 24 partiels légèrement inharmoniques par voix et un
court transitoire de frappe déterministe. Il atténue les partiels proches de
Nyquist et omet ceux qui le dépassent, également pendant le bend. Les canaux
reçoivent le même signal ; ce modèle ne produit pas une image stéréo acoustique.

Cette première version fournit un caractère de piano synthétisé. Elle ne simule
pas toutes les cordes couplées, la résonance sympathique ou la table d’harmonie,
et n’utilise ni échantillons enregistrés ni paramètres ajustés sur un piano réel.
L’écoute reste nécessaire pour choisir son usage musical.

Voix, tableaux de partiels et scratch sont préparés à la création. Les commandes
et le rendu ne font pas grandir de collection ; le coût dépend des voix occupées,
des partiels et des canaux. La capacité de 64 voix est une borne de stockage,
pas une garantie de charge sur tous les appareils. Les mesures des ressources
du sinus ne constituent pas une mesure de charge du piano.

Pour programmer directement en frames, `Synthesis.PianoInstrument.create`
accepte le même modèle avec `decay_frames` (défaut 144 000), `release_frames`
(7 200) et `steal_fade_frames` (48), soit les durées par défaut à 48 kHz.
Ces défauts en frames ne changent pas avec le sample rate. Les commandes, le
rendu, `active_voices()` et la remise à zéro suivent le protocole Instrument.

[Choisir timbre ou instrument](Music.md) · [Jouer une partition MIDI](MusicPlayer.md)
