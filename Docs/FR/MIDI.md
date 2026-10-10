# Jouer une partition MIDI avec ses propres instruments

`GFX.Audio.MIDI` lit une partition et commande les instruments procéduraux de
l’application. [MIDIMelody.sx](../../Examples/MIDIMelody.sx) joue deux pistes à 120 puis
150 BPM, avec changement de programme, balance stéréo, expression, sustain et
queue d’écho. Elle lisse les changements de volume, d’expression et de balance
sur 240 frames (5 ms à 48 kHz) pour éviter les sauts de niveau. La fixture `.mid`
contient des événements, aucune banque de sons.
Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/MIDIMelody.sx --release
```

Le parcours principal est `Score.parse` ou `Score.read`, le choix explicite des
`Binding`, puis `Synthesizer.create` et `Player.create`. Le Player est un
`Synthesis.Generator` : il se compose avec les effets et le
[producteur de flux](Continuous.md), ou se rend dans un tampon en mémoire.

## Choisir les sons et les canaux

Fragment avec un `score:MIDI.Score` lu à 48 kHz et un
`lead:Synthesis.Instrument` stéréo préparé à la même fréquence :

```sx
match try MIDI.Synthesizer.create([
    MIDI.Binding(channel:0, program:0, instrument:lead),
], gain:0.25, controller_ramp_frames:240) {
    failure(error) => { panic(error.detail) }
    success(var synth) => {
        match try MIDI.Player.create(score, synth) {
            failure(error) => { panic(error.detail) }
            success(var player) => { require(try player.render(&samples[0:samples.count()])) }
        }
    }
}
```

Le fragment suppose aussi un tampon stéréo `samples` et le helper
`require(Result<void, Error>)`. L’exemple complet fournit toute la préparation.
Canaux 0..15 et programmes 0..127 utilisent les valeurs du protocole ; le canal
souvent affiché « 1 » porte donc la valeur 0. Le programme initial de chaque
canal vaut 0. Le choix du programme commande les prochaines notes ; les notes
antérieures, leurs releases et leur sustain restent dans leur instrument.
Sélectionner un couple canal/programme absent, ou lui envoyer un note-on,
provoque `unsupported`, sans son implicite.
Aucun traitement spécial du canal de percussion ni correspondance General MIDI.

`Synthesizer.create(bindings, note_capacity:256, bend_range:2, gain:0.2,
controller_ramp_frames:0)` accepte
1..128 bindings distincts, un pool de 1..4 096 notes tenues, ±0..24 demi-tons et
un gain fini 0..1. Tous les instruments doivent avoir le même format stéréo,
à fréquence entière 1..16 777 216 Hz. Utiliser une instance indépendante par
binding ; des références vers la même classe partageraient les voix et contrôles.
Les classes sont partagées avec l’application ; les structs sont copiés dans
la valeur de protocole. Le gain global reste explicite : la somme n’est pas
normalisée et l’application garde une marge pour la sortie vers Audio.

## Envoyer des messages directement

`send(channel, Message)` retourne `true` pour un message traduit et `false`
pour une pression ou un contrôleur ignoré. Les valeurs hors plage produisent
`invalid_input` avant mutation. Un message valide peut encore être refusé par
l’instrument, notamment pour sa capacité ou une fréquence hors plage.

| Message | Interprétation |
|---|---|
| `note_on(note, velocity)` | Note 0..127, fréquence A4=440 Hz pour note69, vélocité divisée par127 ; zéro devient note-off |
| `note_off(note, velocity)` | Relâche la plus ancienne note encore tenue de même canal/hauteur ; vélocité de relâchement validée mais ignorée |
| `program_change(program)` | Sélectionne un binding existant pour les prochaines notes |
| `pitch_bend(value)` | Valeur14bits 0..16383, centre8192 ; `(value−8192)/8192 * bend_range` demi-tons |
| `control_change(7, value)` | Volume7bits du canal, initial127 |
| `control_change(11, value)` | Expression7bits, initial127, multipliée par le volume |
| `control_change(10, value)` | Balance linéaire : 0 gauche,64 centre,127 droite ; atténue seulement le canal opposé |
| `control_change(64, value)` | Sustain :0..63 relâché,64..127 enfoncé |
| `control_change(123, value)` | Note-off de toutes les touches du canal, en respectant sustain |
| `control_change(120, value)` | Coupe immédiatement tous les instruments du canal par reset, puis réapplique bend/sustain de canal |

Volume, expression et balance sont appliqués après le rendu de chaque instrument
et valent aussi pour les voix d’un ancien programme. Bend et sustain sont
transmis à tous les bindings du canal. Pour éviter un craquement lors d’un
changement de niveau sur des voix encore audibles, choisir
`controller_ramp_frames:240` (5 ms à 48 kHz). Cette durée, bornée à
0..16 777 216 frames, lisse linéairement les gains stéréo résultant de CC7, CC11
et CC10. Zéro conserve le changement immédiat, et reste la valeur par défaut.
La première frame garde le niveau courant ; la cible est atteinte après la
durée choisie. Une nouvelle cible repart du niveau courant, même pendant une
rampe. Tous les programmes d’un canal partagent cette progression, avancée une
fois par frame ; reset restaure les niveaux initiaux et annule les rampes.
Les événements gardent leur date exacte : ce lissage n’ajoute ni humanisation
ni retard aux notes, ni rampe au bend, au sustain ou à l’arrêt immédiat CC120.
Pour les valeurs MIDI de gain et de balance, les LSB haute résolution sont ignorés,
comme CC0/32 bank select,
CC121 reset controllers, RPN/NRPN, modulation et les autres contrôleurs.
`poly_pressure` et `channel_pressure` sont validés puis ignorés.

Les notes répétées ont des identités distinctes et un appariement FIFO explicite.
Le pool de notes tenues est indépendant du pool de voix de l’instrument ; un
vol de voix ne retire pas une touche MIDI encore tenue. Un note-off sans touche
correspondante est accepté sans effet. `held_notes()` compte les touches.
`finish()` retire le sustain et relâche toutes les voix, sans couper leur queue.
`reset()` coupe et retrouve programmes0, volume/expression127, balance/bend0,
pédale relâchée et compteur d’identités initial. Les commandes multi-instruments
propagent le premier refus ; les instruments précédents peuvent avoir accepté.
Il n’y a pas de rollback implicite des instruments utilisateur : reset/reconstruire
après erreur avant replay.

## Lire et borner une partition

`Score.parse(bytes:@uint8[..], sample_rate, maximum_bytes:1_048_576,
maximum_tracks:64, maximum_events:65_536)` ne conserve pas la vue d’entrée.
`Score.read(path, sample_rate, ...)` lit les octets avec STD.File puis utilise le
même parser ; les erreurs de fichier restent celles de STD.File. La préparation
se fait hors du rendu. Bornes configurables :14..16 777 216 bytes,1..256 pistes,
1..65 536 événements. Chaque événement, même métadonnée ou SysEx ignoré, compte
avant stockage ; les tailles de chunks et payloads sont vérifiées avant lecture.

Formats0/1, division PPQN1..32767, statuts canal et running status sont pris en
charge. Une piste doit terminer par end-of-track, et les nombres de pistes
annoncés/réels doivent correspondre. Un tempo format1 hors première piste est
refusé. Format2 et division SMPTE retournent `unsupported` ; données tronquées,
VLQ de plus de quatre octets, longueur invalide et structure incompatible
retournent `invalid_input`, dépassements de capacité/horloge `limit_exceeded`.
Les chunks inconnus sont sautés selon leur longueur ; un header étendu est accepté.
Les métadonnées inconnues et SysEx F0/F7 sont sautés selon leur longueur et
comptés dans `ignored_events`. Les extensions de métadonnées reconnues sont
sautées après les champs connus. Meta/SysEx annulent le running status.
Pression et contrôleurs non rendus restent inspectables dans `events`.

Le Score expose `sample_rate`, `ppqn`, `track_count`, `events`, `end_frame` et
`ignored_events`. Les événements possèdent `frame`, `channel`, `message`.
La fusion ordonne tick, index de piste, puis ordre dans la piste ; les événements
arrondis à la même frame conservent cet ordre musical. Le tempo par défaut est
500 000 µs par noire (120 BPM). L’horloge accumule exactement les fractions de
frame avec des entiers ; chaque position absolue est arrondie au plus proche,
demi-frame vers la suivante, sans addition d’arrondis par événement/bloc.
Les frames doivent tenir dans int64, même après arrondi ; le refus est récupérable.

## Rendre les événements et leurs queues

`Player.create(score, synth)` exige la même fréquence. Il commence à la frame0
sans réinitialiser implicitement le synthétiseur ; utiliser des instruments
neufs ou appeler reset avant replay. Le rendu segmente aux événements ;
`rendered_frames()` donne la position produite, `ignored_messages()` compte
les messages non rendus rencontrés. Le bloc vide ne déclenche rien. Un événement
à la fin d’un bloc attend le prochain bloc non vide. À `end_frame`, après les
derniers événements, le Player appelle finish une fois. Il continue ensuite
à rendre les releases ; ajouter la durée de queue choisie au StreamProducer.
`reset()` remet instruments, position et compteur des messages ignorés.

Un refus conserve la position de l’événement fautif et ne le consomme pas ; le
préfixe et les commandes antérieures peuvent déjà être appliqués. Une erreur de
rendu utilisateur peut modifier son état et son tampon avant refus. Source,
instruments et producteur se rendent sur un seul thread, avec ownership exclusif
de leur chronologie. Aucun port matériel, callback natif Silex, décodeur MIDI SDL,
hébergement VST ou chargement automatique de banques ne participe à ce parcours.

Les [preuves](Validation.md) couvrent timing, formats, contrôleurs, identités,
queues, erreurs, limites et égalité mémoire/flux. Le parser et le routage restent
écrits en Silex ; l’écoute complète leur qualification sonore.

Les règles de fichier suivent [RP-001 de la MIDI Association](https://midi.org/standard-midi-files-specification),
avec les [messages canal](https://midi.org/expanded-midi-1-0-messages-list) et
[contrôleurs MIDI1.0](https://midi.org/midi-1-0-control-change-messages).
