# Préparer une mélodie et la jouer

Décrivez quelques notes, choisissez un timbre ou un instrument et préparez un son réutilisable.
`GFX.Audio.Music` possède les buffers, les conversions de temps et le rendu ;
aucune banque de sons n'est nécessaire. Utilisez la toolchain locale contenant
les conversions optionnelles et les arguments nommés partagés, jusqu'à publication.

```sx
use GFX.Audio
use GFX.Audio.Music

func main() {
    var audio = Audio()
    var melody = try Music.Melody.create([
        Music.Note(key:Music.Key.C5, beats:0.5), Music.Note(key:Music.Key.E5, beats:0.5),
        Music.Note(key:Music.Key.G5, beats:0.5), Music.Note(key:Music.Key.C6, beats:1.25),
    ], tempo:187.5) else error { panic(error.detail) }
    let victory = try melody.prepare(audio) else error { panic(error.detail) }
    audio.wait(audio.play(victory))
}
```

Do5–Mi5–Sol5–Do6 : trois temps de 160 ms puis un dernier de 400 ms,
avec articulation à 80 % et relâchement rétro de 30 ms. Préparer au chargement
du jeu ; chaque `audio.play(victory)` crée ensuite une lecture indépendante,
sans recalculer la mélodie. `audio.wait` sert seulement à cette démonstration
autonome : le jeu poursuit sa boucle après `play`.

La préparation emprunte le mix via `audio:&Audio` sans le conserver. Elle est donc utilisable depuis un système recevant une ressource Audio mutable, ainsi que depuis une variable Audio possédée.

## Écrire les notes par leur nom

`Music.Key.C5`, `Cs5` et `Bb4` sont des constantes `int`, directement utilisables
comme `key`. Le suffixe `s` signifie *sharp* (dièse), `b` signifie bémol ;
`Cs5` et `Db5` donnent le même numéro. La convention est **C4 = 60**, C5 = 72
et A4 = 69. Les constantes restent dans 0..127 ; `CMinus1` désigne C-1 (0),
`G9` vaut 127. Les altérations peuvent changer d’octave : `Bs3` vaut `C4`.

Pour une liste de constantes, le compilateur actuel demande l’annotation `int[]` :

```sx
let notes:int[] = [Music.Key.C5, Music.Key.E5, Music.Key.G5, Music.Key.C6]
```

Pour des noms connus, utilisez les conversions directes dans `main()` :

```sx
let sharp = Music.key("D#3") // 51
let flat = Music.key("Bb4")  // 70
let notes = Music.keys(["C5", "E5", "G5", "C6"])
```

Les noms textuels acceptent A à G, une altération ASCII optionnelle `#` ou `b`,
puis une octave à un chiffre, éventuellement négative. La lettre de note peut
être minuscule ; les espaces, les doubles altérations et les symboles Unicode
ne sont pas acceptés. La hauteur résultante doit rester dans 0..127 : C-1 et
B#-2 valent 0, Cb-1 et G#9 sont rejetés. Aucun accordage n’est changé.

Un appel ordinaire à `key` donne `int`, et à `keys` donne `int[]`. Une entrée
invalide déclenche `panic`. Pour des noms saisis ou chargés, ajoutez `try`
au même appel et examinez le `Result` :

```sx
let candidate = (try Music.key("C#5")) // Result<int, Error>
match candidate {
    success(number) => { print(number) }
    failure(error) => { print(error.detail) }
}
let notes = try Music.keys(["C5", "E5", "G5", "C6"]) else error { panic(error.detail) }
```

`key` retourne `Result<int, Error>` et `keys` retourne `Result<int[], Error>`.
Une erreur conserve `invalid_input`, l’opération `audio.music.key` et le nom dans
`subject`. Les deux conversions de listes conservent ordre et répétitions et
acceptent une liste vide ; la variante récupérable ne retourne aucun résultat
partiel. Ces conversions interviennent à la description des notes, hors rendu DSP.
Les numéros MIDI restent utilisables directement.

Dans une fonction récupérable, une ancienne propagation devient explicite :
`try Music.key(name) else error { return Result<int, Error>.failure(error) }`.
Sans bloc `else`, `try Music.key(name)` conserve désormais le résultat.

## Changer le son

Fragment à utiliser avec `audio` et `melody` ci-dessus :

```sx
var timbre = Music.Timbre.soft()
timbre.release_seconds = 0.15
timbre.amplitude = 0.16
let softer = try melody.prepare(audio, using:timbre) else error { panic(error.detail) }
```

Les trois points de départ sont `retro()` (carré, 8 bits, maintien 125 µs),
`soft()` (triangle, attaque 10 ms) et `sine()` (sinus). Leurs champs modifiables
sont `waveform`, `amplitude`, `duty_cycle`, `attack_seconds`, `decay_seconds`,
`sustain`, `release_seconds`, `bits` et `hold_seconds`. Les formes d'onde et
l'ADSR suivent [les primitives de synthèse](Synthesis.md). Le carré emploie
les harmoniques bornées du package ; le maintien et la quantification sont
appliqués avant l'enveloppe, qui conserve son raccord silencieux.

Ce sont des choix sonores subjectifs, sans imitation acoustique garantie.
Modifier un timbre puis préparer produit un nouveau Sound ; le précédent et
ses lectures conservent leur PCM. Les notes et le tempo appartiennent à une
copie possédée par Melody ; modifier la liste source ne change pas la mélodie.

Le timbre est une recette sonore ; il ne reçoit pas de commandes et ne conserve
pas de voix actives. La préparation produit chaque note puis somme ses queues.
Les presets du timbre ne constituent donc pas un catalogue d'instruments.

## Choisir un instrument intégré

Fragment à utiliser avec `audio` et `melody` ci-dessus :

```sx
var instrument = try Music.Instruments.sine(amplitude:0.16,
    attack_seconds:0.003, decay_seconds:0.03, sustain:0.35, release_seconds:0.1)
    else error { panic(error.detail) }
let tone = try melody.prepare(audio, using:instrument, tail_seconds:0.1)
    else error { panic(error.detail) }
audio.wait(audio.play(tone))
```

`Music.Instruments.sine` crée le véritable `Synthesis.SineInstrument`
polyphonique du package. L'instrument reçoit les commandes musicales et possède
ses voix. Cette entrée accepte les durées en secondes et choisit par défaut
un format mono à 48 kHz, une amplitude de 0,2, une attaque de 5 ms, un déclin
de 50 ms, un sustain de 0,7, un relâchement de 100 ms et 16 voix. `max_voices`
accepte 1..64 ; `voice_policy` choisit rejet ou réattribution de la voix la
plus ancienne, cette dernière par défaut. `steal_fade_seconds` vaut 1 ms par
défaut et se limite à 4 096 frames au format choisi. L'amplitude par voix
reste distincte de la vélocité et du gain pilotable ; reset la conserve.
Les durées sont arrondies à la frame la plus proche et chaque étape ADSR
se limite à 16 777 216 frames. Les réglages invalides retournent un `Result`.

Les [commandes de notes, sustain, pitch bend et gain](Instruments.md) restent
disponibles sur cet instrument. Une mélodie préparée fige leur résultat ;
modifier ou commander ensuite l'instrument ne modifie pas le Sound préparé.
Le format choisi lors de sa création doit correspondre à celui de `prepare`.
Le sinus sert les tons et alertes simples. [Music.Instruments.piano](Piano.md)
ajoute un piano procédural avec dynamique de frappe et décroissance naturelle.
Les timbres rétro restent directement utilisables
pour les effets courts et la musique.

## Apporter un instrument et des effets

[MusicalSounds.sx](../../Examples/MusicalSounds.sx) joue successivement la victoire rétro,
un timbre modifié, l'instrument intégré et un instrument applicatif conforme au protocole existant
`Synthesis.Instrument`. Depuis SilexProject :

```sh
silex run Packages/GFX.Audio/Examples/MusicalSounds.sx --release
```

La même opération `melody.prepare(audio, using:instrument, tail_seconds:0.1)`
construit les événements et rend l'instrument. `effects:[myEffect]` ajoute
jusqu'à 32 traitements `Processing.Processor`, dans l'ordre indiqué, après
la somme des notes. Ils partagent le format demandé. Leur queue s'obtient
avec `tail_seconds`, sans deviner la durée d'un traitement utilisateur.

La préparation réinitialise l'instrument choisi et les effets puis
consomme leur état. Une classe reste partagée avec ses autres détenteurs ;
utiliser une instance dédiée sur le thread applicatif. Une erreur de rendu
peut laisser ces objets modifiés : les réinitialiser ou les reconstruire
avant réessai. Les [primitives avancées](Instruments.md) restent disponibles.

## Rythme, durée et limites

`Music.Note` accepte `key` (numéro MIDI 0..127), `beats` positif, `velocity`
dans 0..1 (1 par défaut) et `gate` dans ]0, 1] (0,8 par défaut). La note
suivante commence après la durée `beats` ; `gate` indique la fraction tenue.
Les queues peuvent donc se recouvrir. `Melody.create` accepte 1..4 096 notes
et un `tempo` positif fini, 120 BPM par défaut. Les dates absolues sont
arrondies à la frame la plus proche ; la fraction tenue doit occuper au
moins une frame. Le tempo ne dépend pas de la cadence de l'application.

`prepare` produit du mono à 48 kHz par défaut. `format:Processing.Format(...)`
permet 1..192 000 Hz et 1..8 canaux. Un instrument choisi doit avoir
ce même format. Le timbre intégré envoie le signal identiquement aux canaux ;
une note à Nyquist ou au-delà est refusée.

La durée du Sound est la durée musicale plus `tail_seconds`. Sans cet
argument, la queue vaut le release du timbre intégré ou 100 ms pour un
instrument choisi, y compris l'instrument sinus intégré. Une queue explicite plus courte coupe le relâchement ;
une queue plus longue laisse les effets finir puis ajoute du silence.
`max_seconds` limite durée musicale et queue à 30 s par défaut ; il peut être
remplacé dans ]0, 300]. Le résultat est aussi limité à 16 777 216 samples.
Ces limites protègent une préparation de son court, qui matérialise le PCM.

Les erreurs de description, de réglage, de format ou de niveau reviennent
comme `Result` ; les dépassements de notes, de durée ou de stockage utilisent
`limit_exceeded`. Le mix n'est ni normalisé ni écrêté : un sample non fini ou
hors ±1 est refusé avant `Audio.create`. Réduire le niveau ou choisir un
[limiteur](Dynamics.md). Les échecs natifs de `Audio.create` conservent son
contrat existant.

La préparation alloue le PCM et les états de travail, puis Audio conserve
sa copie ; ces coûts appartiennent au chargement, pas à chaque déclenchement.
Le timbre intégré utilise un scratch de 512 frames, mais le résultat complet
reste en mémoire. `audio.unload(sound)` libère le son réutilisable ; les
lectures déjà démarrées peuvent finir. `audio.release(playing)` libère une
lecture. Tous ces handles appartiennent à leur instance Audio.

Le [player MIDI](MusicPlayer.md) possède l’alimentation continue et les contrôles
de lecture. Le [parcours avancé](MIDI.md) conserve le routage par canal/programme.
Les [coûts musicaux](MusicResources.md) distinguent préparation, déclenchement
et production continue.

[Jouer une partition avec un player et des contrôles de lecture](MusicPlayer.md).

[Jouer de la guitare, du violon et de la batterie](Catalogue.md), avec des instruments intégrés et des exemples écoutables.
