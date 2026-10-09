# Jouer de la guitare, du violon et de la batterie

Choisir un instrument avec `Music.Instruments.guitar()`, `violin()` ou `drums()`,
puis le passer à `using:` dans une mélodie ou un [player MIDI](MusicPlayer.md).
Les trois instruments produisent leur son sans fichiers audio. Le
[piano](Piano.md) et le [sinus](Instruments.md) restent disponibles.

## Préparer une mélodie de guitare

La position de pincement change la couleur ; près du milieu de la corde,
certaines harmoniques disparaissent. Les notes décroissent naturellement même
si elles restent tenues. Cet exemple prépare une mélodie réutilisable :

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var guitar = try Music.Instruments.guitar(pluck_position:0.18) else error { panic(error.detail) }
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.G3, beats:0.5),
        Music.Note(key:Music.Key.B3, beats:0.5),
        Music.Note(key:Music.Key.D4, beats:1.0),
    ], tempo:120.0) else error { panic(error.detail) }
    let sound = try melody.prepare(audio, using:guitar, tail_seconds:0.15) else error { panic(error.detail) }
    audio.wait(audio.play(sound)); assert(audio.unload(sound))
}
```

Remplacer la création de `guitar` par `Music.Instruments.violin()` donne des
notes entretenues jusqu’au relâchement. `brightness` règle la couleur et la
vélocité change l’intensité et le spectre. Le violon propose une attaque douce
et un vibrato réglable. La polyphonie permet de jouer plusieurs notes ; il
s’agit d’un modèle de violon, sans couche d’ensemble automatique.

## Écrire une partie de batterie

`Music.Drum` fournit des numéros utilisables directement comme `Music.Note.key`.
Le kit contient sept percussions, avec les numéros de la carte General MIDI :

| Touche | Numéro MIDI | Son |
| --- | --- | --- |
| `Music.Drum.kick` | 36 | Grosse caisse |
| `Music.Drum.snare` | 38 | Caisse claire |
| `Music.Drum.closed_hat` | 42 | Charleston fermé |
| `Music.Drum.open_hat` | 46 | Charleston ouvert |
| `Music.Drum.low_tom` | 45 | Tom grave |
| `Music.Drum.high_tom` | 50 | Tom aigu |
| `Music.Drum.crash` | 49 | Cymbale crash |

L’[exemple batterie](../../Examples/Drums.sx) joue un rythme, puis les sept
sons séparément. Le kick descend rapidement en hauteur, les toms ont des modes
inharmoniques, la caisse claire ajoute du bruit et les cymbales une texture aiguë.
Toutes les frappes décroissent naturellement. `decay_seconds` règle leur durée
relative : à 0.6, la décroissance de 60 dB est de 0.45 s pour le kick,
0.25 s pour la caisse claire, 0.08/0.5 s pour les charlestons, 0.6/0.45 s
pour les toms et 1.5 s pour la crash. Les modes supérieurs décroissent plus vite.

Comme les autres instruments, `note_off` amortit la note sur `release_seconds` ;
une note très courte coupe donc une résonance longue. Augmenter `beats`/`gate`
pour entendre la queue naturelle. La pédale retarde cet amortissement. Les
charlestons occupent des voix indépendantes, sans étouffement automatique.

Pour les commandes directes, `note_on` reçoit la fréquence de la touche MIDI
obtenue par `MIDI.frequency(Music.Drum.kick)`. Le kit reconnaît les sept touches
avec une tolérance relative de 0.1 %, puis choisit son modèle de percussion ;
la fréquence de sélection n’est pas celle de la résonance entendue. Le bend
modifie les résonances tonales, pas le bruit. Une autre touche produit une erreur
`invalid_input`, y compris dans `Melody.prepare` et lors du rendu MIDI.
Choisir explicitement le kit pour les canaux de batterie via les
[bindings MIDI](MIDI.md) ; aucune sélection automatique par canal ou programme.
Ce sous-ensemble ne constitue pas une banque General MIDI complète.

## Adapter les instruments

| Réglage | Guitare | Violon | Batterie |
| --- | --- | --- | --- |
| `amplitude` / `brightness` | 0.2 / 0.65 | 0.2 / 0.65 | 0.2 / 0.65 |
| `pluck_position` | 0.18, dans [0.05, 0.95] | — | — |
| `decay_seconds` | 2.0, dans (0, 30] | — | 0.6, dans (0, 5] |
| `attack_seconds` | Attaque fixe de 3 ms | 0.05, dans [0, 5] | Attaque fixe de 1 ms |
| `release_seconds` | 0.08 | 0.2 | 0.04 |
| `vibrato_cents` / `vibrato_hz` | — | 12 / 5.5, dans [0, 50] / [0, 12] | — |

Les amplitudes et brillances sont finies dans [0, 1], les relâchements dans
[0, 5] secondes. Pour supprimer le vibrato, utiliser `vibrato_cents:0.0`.
Les durées sont arrondies en frames ; une décroissance arrondie à zéro est
rejetée. La guitare adapte sa décroissance au registre entre 0.5 et 1.5 fois
la valeur configurée. Les modèles guitare/batterie libèrent leur voix après
une décroissance nominale de 80 dB, même sous pédale. Le violon la conserve
jusqu’au relâchement ou au vol de voix.

Chaque factory accepte `max_voices` (16 par défaut, 1..64), `voice_policy`
(`steal_oldest` par défaut ou `reject`), `steal_fade_seconds` (1 ms par défaut,
0..4096 frames) et `format` (48 kHz mono par défaut, 1..8 canaux).
Le taux est de 1..192000 Hz pour les cordes et de 512..192000 Hz pour la batterie.
Un `note_on` doit rester positif et sous Nyquist, y compris après bend.
Les canaux reçoivent le même signal ; les sommes de voix peuvent dépasser
l’amplitude d’une voix, donc adapter le niveau au nombre de notes simultanées.

Les objets retournés sont `Synthesis.GuitarInstrument`, `ViolinInstrument` et
`DrumsInstrument`, conformes aux protocoles `Instrument` et `Generator`.
Leurs factories `create(format, ...)` exposent les mêmes paramètres, en frames
pour les durées (`attack_frames`, `decay_frames`, `release_frames`,
`steal_fade_frames`). Leurs valeurs par défaut en frames correspondent à 48 kHz.
Les [commandes communes](Instruments.md), identités, rampes, reset et règles
de rejet/vol de voix sont conservés. `active_voices()` compte les voix occupées.

## Écouter et qualifier

Depuis la racine `SilexProject`, avec le package local lié :

```sh
silex run Packages/GFX.Audio/Examples/Guitar.sx --release
silex run Packages/GFX.Audio/Examples/Violin.sx --release
silex run Packages/GFX.Audio/Examples/Drums.sx --release
```

Les cordes comparent deux réglages sur la même mélodie ; la batterie fait
entendre chaque pièce du kit. Le rendu est modal : 32 harmoniques pour les
cordes, 8 modes et du bruit déterministe pour les percussions. Les modes proches
de Nyquist sont atténués, puis omis au-dessus. Ces synthèses stylisées n’incluent
ni corpus enregistré, ni couplage de cordes, ni interaction physique non linéaire
archet/corde.

[Oracles numériques](../../Tests/Consumer/Tests/Catalogue.sx) et
[compteur de ressources](../../Tests/Resources/ValidateCatalogue.py) vérifient
les comportements et l’absence d’allocation/copie mesurée sur le thread appelant
pendant commandes, rendu et reset en Debug/Release ARM64. La préparation alloue
les tables et le pool bornés. Les pilotes dummy permettent les tests de lecture,
mais l’écoute humaine reste nécessaire pour apprécier le résultat.
