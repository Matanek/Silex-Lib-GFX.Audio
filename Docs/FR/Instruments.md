# Jouer une mélodie polyphonique

Pour un instrument à décroissance naturelle et dynamique de frappe, choisir
[le piano procédural](Piano.md). Les règles de voix et de commandes ci-dessous
sont partagées ; la section ADSR décrit le sinus.

`Synthesis.SineInstrument` joue des notes sinusoïdales avec vélocité, enveloppe
ADSR, sustain et pitch bend. `Synthesis.Sequence` place leurs commandes sur
l’horloge audio et fournit un `Generator`, composable avec les effets existants.
Aucune banque de sons ni entrée MIDI n’est nécessaire.

Pour écrire quelques notes et préparer un son sans gérer les frames ou buffers,
utiliser [le parcours musical](Music.md). `Music.Instruments.sine` configure
ce même instrument avec des durées en secondes.

[PolyphonicMelody.sx](../../Examples/PolyphonicMelody.sx) joue quatre mesures à 120 BPM :
accords, notes répétées avec identités distinctes, pédale dans la deuxième
mesure et changement de hauteur dans la quatrième. Les accents sont écrits
dans la partition. Un second passage limite le même morceau à deux voix
pour entendre leur réattribution avec le raccord par défaut. Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/PolyphonicMelody.sx --release
```

Fragment avec un `format` mono à 48 kHz et un buffer `samples` de 48 000 samples
préparés, et un helper `require(Result<void, Error>)` qui traite les erreurs :

```sx
match try Synthesis.SineInstrument.create(format, max_voices:8) {
    failure(error) => { panic(error.detail) }
    success(var instrument) => {
        let events:Synthesis.Event[] = [
            Synthesis.Event(frame:0, command:Synthesis.Command.note_on(1, 261.6256, 0.4)),
            Synthesis.Event(frame:0, command:Synthesis.Command.note_on(2, 329.6276, 0.3)),
            Synthesis.Event(frame:24_000, command:Synthesis.Command.all_notes_off),
        ]
        match try Synthesis.Sequence.create(instrument, events) {
            failure(error) => { panic(error.detail) }
            success(var source) => {
                require(try source.render(&samples[0:samples.count()]))
            }
        }
    }
}
```

Atténuer explicitement la somme avant `Audio.create`, ou composer avec un
[limiteur](Dynamics.md). Les voix s’additionnent sans normalisation cachée ;
16 voix de vélocité 1 peuvent dépasser l’intervalle audible `[-1, 1]`.

## Commander les notes

`instrument.send(command)` applique une commande entre deux rendus. Pour un
placement à l’intérieur d’un bloc, utiliser un `Event` de la séquence.
Chaque opération renvoie `Result<void, Error>`.

| Commande | Valeurs et comportement |
|---|---|
| `Command.note_on(id, frequency_hz, velocity)` | Identité entière ≥ 0, fréquence float32 positive sous Nyquist, vélocité float32 dans 0..1. Une nouvelle voix commence à phase zéro et déclenche l’ADSR. |
| `Command.note_off(id)` | Relâche cette identité ; une identité absente ne fait rien. Sous pédale, la voix attend son retrait. |
| `Command.sustain(down)` | `true` retient les touches relâchées ; `false` les fait entrer en release sans relâcher les touches encore enfoncées. |
| `Command.pitch_bend(semitones)` | float32 fini dans −24..24, commun aux voix actuelles et futures. Conserve la phase. Refuse l’ensemble si une voix occupée sort de la plage de fréquence. |
| `Command.all_notes_off` | Relâche toutes les voix, même sous pédale, selon leur durée de release. |

Deux notes de même hauteur utilisent des identités différentes. Une identité
occupée, y compris en release, refuse un nouveau `note_on`. Après extinction,
elle peut être réutilisée. Le `note_off` d’une voix volée ne relâche pas la
nouvelle identité. Une vélocité zéro occupe une voix silencieuse ; l’instrument
n’applique pas la convention MIDI « note-on zéro = note-off ».

`reset()` coupe immédiatement les voix et les fondus, remet pédale, bend et
compteur à zéro, ainsi que le gain global à 1, en gardant la configuration. `active_voices()` compte les
places occupées, y compris releases et fondus. Aucun changement aléatoire ou
humanisation n’est appliqué.

## Régler la polyphonie et l’enveloppe

`SineInstrument.create(format, ...)` accepte 1..8 canaux et une fréquence
entière de 1..16 777 216 Hz. Le sinus mono est envoyé identiquement à chaque
canal. La fréquence divisée par le sample rate doit rester positive en
float32, y compris après bend ; la limite haute est strictement Nyquist.

| Réglage | Défaut | Plage |
|---|---|---|
| `max_voices` | 16 | 1..64, allouées à la création |
| `amplitude` | 1 | float32 fini, 0..1, conservée au reset et multipliée par vélocité et gain |
| `voice_policy` | `VoicePolicy.steal_oldest` | `steal_oldest` ou `reject` |
| `attack_frames` | 240 | 0..16 777 216 |
| `decay_frames` | 2 400 | 0..16 777 216 |
| `sustain` | 0,7 | float32 fini, 0..1 |
| `release_frames` | 4 800 | 0..16 777 216 |
| `steal_fade_frames` | 32 | 0..4 096 |

Les durées sont des frames, avec la [sémantique de l’enveloppe](Synthesis.md).
Les défauts correspondent à 5 ms d’attaque, 50 ms de decay et 100 ms de
release à 48 kHz ; ils ne changent pas automatiquement avec le sample rate.

La première place libre est utilisée. À capacité pleine, `reject` retourne
`limit_exceeded` sans modifier les voix ; `steal_oldest` remplace le départ
le plus ancien, y compris s’il est en release. Avec un fondu non nul, la voix
remplacée part exactement de son dernier sample émis, puis mélange ce niveau
figé avec la nouvelle note pendant la durée choisie. Ce court raccord évite
un saut au premier sample ; il ne conserve pas une voix supplémentaire. Zéro
coupe directement. Un nouvel emprunt pendant le fondu repart du dernier sample
mélangé. Le `pitch_bend` simple est immédiat. Les [rampes continues](Continuous.md)
ajoutent `pitch_bend_to` et `gain_to` sans redémarrer les voix.

## Placer les commandes sur l’horloge audio

`Sequence.create(instrument, events, capacity:4_096)` conserve sa partition.
La capacité va de 1 à 65 536 événements. `schedule(event)` ajoute une commande
après la dernière position programmée ou au même instant, sans dépasser cette
capacité. Les événements déjà exécutés restent pour rejouer après `reset()`.
Préparer ces ajouts avant le rendu : leur stockage peut allouer.

Les positions `Event.frame` sont des entiers dans 0..9 223 372 036 854 775 807.
`rendered_frames()` donne la prochaine frame à produire. Les événements doivent
être chronologiques ; ceux d’un même instant suivent l’ordre d’insertion.
Un événement à la fin exacte d’un bloc s’applique avant le premier sample du
prochain bloc non vide. Un bloc vide ne consomme aucune commande. Une commande
en retard ou ajoutée avant la dernière position programmée est refusée, sans
rattrapage ni déplacement silencieux.

`Synthesis.frame_at(seconds:float64, sample_rate:int)` convertit un temps absolu
fini et positif ou nul, arrondi à la frame la plus proche ; une demi-frame va
vers la suivante. Le résultat est limité à 2⁵³−1 pour conserver la précision
entière du float64. Utiliser directement les frames pour les grandes positions.
À 48 kHz et 120 BPM, un temps vaut exactement 24 000 frames. Placer chaque
événement depuis l’origine évite d’accumuler des arrondis ; le rendu n’utilise
ni delta de l’interface ni temporisateur applicatif pour avancer cette horloge.

## Composer et développer un instrument

Un type utilisateur conforme à `Synthesis.Instrument` fournit `format`,
`validate(command)`, `send(command)`, `render(samples)` et `reset()`.
`validate` vérifie les valeurs sans changer l’état ; `send` vérifie aussi les
contraintes qui dépendent des notes en cours. `render` écrit toutes les frames
interlacées demandées, garde son état entre blocs et accepte un bloc vide.
`Sequence` utilise cette interface, sans connaissance du timbre de l’instrument.
Elle peut ensuite entrer dans `Processed`, `Mix` ou une modulation comme tout
`Generator`. Un instrument directement utilisable comme générateur déclare
aussi sa conformance nominale à `Generator`.

Une classe conserve son identité partagée ; un instrument struct est copié
lors de son effacement en protocole. La séquence possède ses événements et
conserve l’instrument. Manipuler l’ensemble sur un seul thread ; une autre
séquence ou un appel direct sur la même classe partage son état. Le reset de
la séquence réinitialise cet instrument et rejoue toute la partition.

Les commandes invalides retournent `invalid_input` (`audio.synthesis`), les
capacités saturées `limit_exceeded`. Les frames incomplètes sont refusées avant
écriture. Si une commande programmée échoue pendant le rendu, le préfixe déjà
produit et les commandes précédentes restent appliqués ; le curseur demeure
sur la frame fautive, la commande n’est pas consommée et le suffixe reste
intact. Réinitialiser puis reconstruire le rendu après un échec. Les erreurs
renvoyées par un instrument utilisateur sont propagées ; s’il échoue pendant
son propre rendu, son contrat détermine le préfixe affecté.

Le pool de voix, les enveloppes et le tampon de travail sont préparés à la
création. Le rendu et les commandes valides de l’instrument intégré ne font
pas grandir de collection. Le travail par frame dépend du nombre de voix
occupées et de canaux ; cette qualification ne promet pas une charge maximale
sur tous les appareils. Le [lecteur MIDI](MIDI.md) commande ces instruments.
Les banques utilisateur, les modèles d’instruments réalistes et l’humanisation
restent des capacités séparées à établir.

[Jouer une partition MIDI avec ses propres instruments](MIDI.md).

[Jouer de la guitare, du violon et de la batterie](Catalogue.md), avec des instruments intégrés et des exemples écoutables.
