# Jouer une partition et contrôler sa lecture

`Music.Player` lit une partition MIDI avec un timbre, un instrument ou un
routage choisi. Il possède la production et l’alimentation audio ; le programme
n’écrit aucune boucle de samples. Voici un programme autonome complet, avec
[sa partition](../../Examples/MusicScore.mid) placée à côté du fichier `.sx` :

```sx
use GFX.Audio
use GFX.Audio.Music
use GFX.Audio.MIDI

func main() {
    var audio = Audio()
    let bytes = embed_bytes("MusicScore.mid")
    var score = try MIDI.Score.parse(@bytes[0:bytes.count()], 48_000) else error { panic(error.detail) }
    var timbre = Music.Timbre.retro(); timbre.amplitude = 0.10
    var player = try Music.Player.create(audio, score, using:timbre) else error { panic(error.detail) }
    let playing = try player.play() else error { panic(error.detail) }
    try player.wait() else error { panic(error.detail) }
    print("Finished; ignored messages: ", player.ignored_messages())
}
```

`wait()` alimente les lectures Audio actives jusqu’à la fin. Cette attente est
volontaire et bloque le programme autonome. Dans un jeu, utiliser le plugin
Audio et continuer la boucle applicative ; ne pas appeler `wait()` dans un système.
L’[exemple interactif](https://github.com/Matanek/Silex-Examples/tree/main/Sources/MIDIPlayer)
montre les deux modes, un choix rétro modifié et un instrument sinus intégré.
La partition d’exemple conserve ses changements de tempo ; le mode rétro compte
huit programmes ou contrôleurs non appliqués.

## Choisir le son et son interprétation

`using:` accepte un `Music.Timbre`, un `Synthesis.Instrument` intégré ou utilisateur,
ou un `MIDI.Synthesizer` déjà routé. Pour choisir l’instrument intégré, remplacer
la création du timbre par ce fragment :

```sx
var instrument = try Music.Instruments.sine(amplitude:0.16,
    release_seconds:0.15) else error { panic(error.detail) }
var player = try Music.Player.create(audio, score, using:instrument) else error { panic(error.detail) }
```

Le mode simple réunit les notes des seize canaux dans le choix sonore. Les
note-off gardent canal, hauteur et ordre FIFO d’origine ; deux canaux jouant la
même hauteur se relâchent donc correctement. La vélocité est conservée. Les
programmes, bend, pression et contrôleurs sont ignorés et comptés dans
`ignored_messages()`, sauf All Notes Off (CC123), qui relâche les notes du canal.
Ce choix ne reproduit pas l’orchestration ou les percussions General MIDI.
Le timbre dispose de seize voix avec remplacement de la plus ancienne et
transition de 1 ms ; un instrument conserve sa propre capacité et politique.

Pour conserver les programmes, sustain, volume, expression, panoramique et
bend par canal, fournir un [synthétiseur routé](MIDI.md). Chaque binding exige
un instrument distinct. Tous les canaux/programmes rencontrés doivent avoir un
binding ; une absence devient une erreur récupérable du player.

`effects:` accepte jusqu’à 32 traitements du même format que la source. Les
instruments et traitements appartiennent exclusivement à une lecture : ils
sont réinitialisés à la création et au replay. Pour deux players indépendants,
créer deux jeux d’états ; partager la partition est permis.

Le mode simple suit au plus 256 notes tenues ; un dépassement est récupérable.

## Intégrer au jeu

Préparer Audio et le player dans la configuration de l’application, puis ajouter
l’Audio fourni aux ressources avec `application.add_resource(audio)`. Le plugin
Audio conserve cette instance ; il en crée une seulement si aucune n’est fournie.
Les systèmes empruntent le player pour appeler `play()`, `pause()`, `resume()`,
`stop()` et `replay()`. Le plugin alimente les flux dans `post_update`, même
lorsque le traitement ordinaire de l’application est suspendu. Toutes les commandes
et la synthèse restent sur le thread applicatif. Aucun callback Silex n’est lancé
sur le thread audio natif. Ne pas faire échapper une référence Audio empruntée
par un système : créer le player depuis son propriétaire lors de la configuration.

`state()` retourne `ready`, `playing`, `paused`, `finished`, `stopped` ou `failed`.
`position_seconds()` suit les frames consommées, pas les frames produites en avance.
`error()` expose l’échec de la source ou du transfert ; un tel échec arrête le flux.
`is_starved()` indique une file ouverte vide : faire progresser l’application plus
régulièrement ou adapter la capacité avancée. Les compteurs d’événements concernent
la production en avance ; ils ne sont pas une notification de l’instant audible.

## Fin, possession et limites

La fin de partition relâche les notes une seule fois, puis le player rend sa queue.
`tail_seconds:` vaut le release du timbre ou 0,2 seconde pour un instrument/routage ;
choisir une queue plus longue pour un effet ou un release prolongé. La queue est
finie, entre 0 et 60 secondes ; elle ne détecte pas automatiquement le silence.
Une queue nulle peut couper une note restant tenue à la fin du fichier.

`play()` démarre une fois ; `replay()` remplace le flux et remet l’état musical à
zéro, depuis une lecture active, arrêtée ou terminée. Pause garde le PCM déjà
préparé ; arrêt le jette et suspend la production. La destruction du player libère
son flux ; le player retient Audio jusqu’à sa propre destruction. Les handles
Audio rendus par play/replay donnent accès aux groupes, niveaux et notifications
existants, et deviennent périmés quand le flux est remplacé ou libéré.

Le PCM continu se limite à une file de `capacity_frames:4800` et un bloc de
`block_frames:512` par player. La partition et les états des instruments/effets
occupent leur propre mémoire ; le morceau n’est pas pré-rendu. Le déclenchement
produit au plus la capacité plus le bloc en attente ; les transferts natifs ont
leurs allocations connues. Les tailles avancées sont respectivement celles des
flux Audio et 1..65536 frames. Une capacité très petite peut sous-alimenter la
conversion native lors d’un changement de fréquence ou de vitesse ; le test à
la même fréquence couvre des files de trois frames, celui de vitesse utilise
la capacité normale. La capacité couvre 100 ms à 48 kHz et vitesse 1 ; elle ne
garantit pas une lecture continue si le jeu reste bloqué plus longtemps.

`Audio.offline.render()` possède aussi l’alimentation et permet une exportation
déterministe. `wait()` refuse l’offline et la pause par `resource_busy` ; utiliser
render pour le premier et resume pour la seconde. Les erreurs de partition,
formats, capacité, réglages et sortie hors `[-1,1]` restent récupérables. Aucun
écrêtage caché n’est ajouté : réduire l’amplitude ou choisir un limiteur.

[Choisir le coût d’une lecture musicale](MusicResources.md).
