# Produire du son par blocs

Un producteur fournit des échantillons `float32` au fil de la lecture, sans
préparer le son entier. Il conserve sa propre chronologie ; `GFX.Audio` reçoit
ses blocs et les joue dans une seule lecture continue. Le programme
[StreamingTone.sx](../../Examples/StreamingTone.sx) produit un la de 440 Hz par blocs et peut
être exécuté depuis `SilexProject/` avec
`silex run Packages/GFX.Audio/Examples/StreamingTone.sx`.

## Ouvrir, remplir et jouer

`Audio.stream(sample_rate:int, channels:int = 1, capacity_frames:int = 4_800)`
retourne `Result<Stream, STD.Error.Error>`. La fréquence et les canaux restent
fixes. Les échantillons suivent les mêmes conventions que `Audio.create` :
valeurs finies entre -1 et 1, canaux entrelacés et frames complètes.
Une frame contient un échantillon par canal. La fréquence accepte de 1 à
2 147 483 647 Hz, les canaux de 1 à 8 ; la capacité doit être positive et
`capacity_frames * channels * 4` ne doit pas dépasser 2 147 483 647 octets.

Fragment du parcours, après création d’`audio`, de `stream` et du producteur :

```sx
var block = producer.next(256)
match audio.write(stream, @block[0:block.count()]) {
    failure(error) => { panic(error.detail) }
    success(frames) => { assert(frames == 256) }
}
block.clear()
let playing = audio.play(stream)
```

Écrire avant `play` permet un préremplissage. `play` démarre le flux une seule
fois et retourne un `PlayingSound` pour les contrôles habituels : volume,
volume général, pause/reprise, vitesse, position, inversion stéréo et fondus.
La répétition n’est pas applicable à un flux ; une valeur autre que `once`
provoque un `panic`. Un flux arrêté ne peut pas être redémarré : ouvrir une
nouvelle source donne une nouvelle chronologie.

## Respecter la capacité

`write` ne bloque pas. Son résultat donne le nombre de frames copiées et
acceptées. Il peut accepter un préfixe ; garder les frames restantes et les
présenter lors d’un prochain appel. En stéréo, avancer la vue de
`frames_acceptées * 2` échantillons. Une file pleine produit la cause
`would_block`, récupérable. Un bloc vide est accepté avec zéro frame.
La source acceptée peut être modifiée ou libérée dès le retour.

Dans une application, consulter `stream_info` puis produire selon l’espace
disponible à chaque mise à jour. Pour un programme direct,
`wait_writable(stream, minimum_frames:int = 1)` permet une attente explicite,
sans boucle active. Cette attente doit rester hors d’un système de mise à jour
qui doit continuer à fonctionner. Une file pleine avant démarrage ou pendant
une pause renvoie `resource_busy`, au lieu d’attendre un progrès impossible.

Les appels à une même instance d’Audio sont sérialisés côté application.
Le producteur et ses traitements s’exécutent sur ce côté ; aucun callback Silex
n’est invoqué par le thread audio. La capacité borne les frames acceptées qui
n’ont pas encore été consommées logiquement. Les petits tampons internes de
conversion et de sortie ne constituent pas une file illimitée de blocs.

## Manque de données et fin de source

Quand les données manquent, la lecture reste active, contribue au silence et
reprend avec les prochains blocs. `StreamInfo.starved` indique une source
démarrée, ouverte, non arrêtée et non en pause, dont la file logique est vide.
Ce constat ne compte pas les interruptions déjà passées et ne mesure pas le
silence exact présenté par le périphérique.

`close(stream)` ferme l’entrée et vide les données restantes, y compris la fin
du filtre de rééchantillonnage. La fermeture est idempotente. Les écritures
suivantes échouent avec `invalid_input`. Fermer avant démarrage est autorisé ;
les données seront lues au premier `play`.

`wait(playing)` attend la fin logique d’un flux fermé. Sur une source encore
ouverte, le manque de données ne suffit pas à terminer cette attente.
`stop(playing)` termine volontairement la source ; le fondu éventuel peut finir
avec les données disponibles, même si la source était vide. Les frames non
mélangées sont abandonnées. `release(stream)` ou `release(playing)` libère la
lecture et invalide les deux handles ; la destruction d’Audio libère aussi ses
flux. Une lecture de flux terminée conserve ses ressources jusqu’à `release`
ou destruction pour ne pas supprimer sa sortie déjà préparée.

## Lire la chronologie

`stream_info(stream)` retourne un `Result<StreamInfo, STD.Error.Error>`, avec
format, capacité, compteurs et états `started`, `closed`, `drained`, `stopped`,
`starved`. Les compteurs sont en frames de source :

- `written_frames` : frames acceptées depuis l’ouverture ;
- `consumed_frames` : frames prises en charge par la piste de mixage ;
- `queued_frames` : frames écrites qui restent à consommer ;
- `discarded_frames` : frames abandonnées après arrêt.

L’identité `written = consumed + queued + discarded` reste vraie. `drained`
indique une fin de source fermée, entièrement consommée, avec sortie préparée
vidée du mixer ; un arrêt anticipé
est décrit par `stopped`. Ces informations se mettent à jour lors de
`stream_info`, `is_playing`, `wait` et de la collecte du plugin. Elles ne sont
pas une horloge exacte des haut-parleurs : le périphérique peut encore avoir
une petite quantité de son préparé à présenter.

Un ancien handle, un handle d’une autre instance ou des données malformées
produisent des erreurs récupérables lors des opérations `Result`. Les contrôles
historiques de lecture gardent leur convention à `panic` sur handle invalide.

[Retour au guide Audio](README.md)

## Groupes et événements

Une lecture de flux reçoit les mêmes `Playback(group:..., volume:...)` et
contrôles de groupe qu’un son fini. Les gains maître, groupe et lecture se
multiplient. Une pause de groupe conserve les frames ; une pause individuelle
reste active après la reprise ou la destruction du groupe.

Appeler `watch_end(playing)` après `play(stream)`, puis `drain_end_events()` sur
le thread applicatif. Une source ouverte à court de données ne produit pas de
fin. `close` suivi du vidage produit `finished`, un arrêt volontaire `stopped`,
et la libération d’une lecture active `released`. Chaque lecture observée
produit au plus un événement ; sa référence reste comparable avec `matches`
après libération, sans désigner une nouvelle lecture au même index.

[Le contrat des événements](Timeline.md) décrit la capacité bornée et les
erreurs de réservation ; [les groupes](Groups.md) décrivent le détachement.

[Faire évoluer un son et alimenter un flux](Continuous.md).
