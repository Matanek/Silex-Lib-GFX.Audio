# Faire évoluer un son pendant l’écoute

`Synthesis.Control` produit un signal mono que l’application peut faire varier
progressivement. Il alimente les modulations de hauteur et de gain, ainsi que
les générateurs utilisateur. Les instruments reçoivent aussi des rampes par
`Command.pitch_bend_to` et `Command.gain_to`, directement ou dans une `Sequence`.

[ContinuousSounds.sx](../../Examples/ContinuousSounds.sx) joue deux sources dans des flux
bornés : un moteur procédural dont le régime monte et descend, puis un accord
avec glissés de hauteur, variations de gain et queue d’écho. Chaque passage
utilise une seule lecture. Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/ContinuousSounds.sx --release
```

Le moteur combine deux sinus modulés et un bruit rose avec graine ; il illustre
un timbre procédural réglable, sans simuler un moteur réel ni charger de banque.
Les commandes et les accents sont explicites. Aucune humanisation n’est ajoutée.

## Changer de cible sans redémarrer

Fragment avec un helper `require(Result<void, Error>)` et un buffer mono
`samples` de 1 000 frames préparé :

```sx
match try Synthesis.Control.create(48_000, value:-1.0) {
    failure(error) => { panic(error.detail) }
    success(var pitch) => {
        require(try pitch.set(1.0, duration_frames:24_000))
        require(try pitch.render(&samples[0:samples.count()]))
        // Retarget from the next frame's current value, without resetting phase.
        require(try pitch.set(0.0, duration_frames:12_000))
    }
}
```

`Control.create(sample_rate, value:0)` accepte les fréquences entières de
1..16 777 216 Hz et les valeurs float32 finies dans −1..1. `set(value,
duration_frames:0)` accepte 0..16 777 216 frames. Le format reste mono ; un
contrôle utilisé avec plusieurs sources doit avoir des instances indépendantes,
car chaque rendu avance son état. Les classes conservées par AM/FM restent
partagées avec le contrôleur de l’application.

Une rampe de N frames émet le niveau courant à son premier sample, puis avance
linéairement ; la frame N émet exactement la cible. `current_value()` donne la
valeur de la prochaine frame. Changer la cible reprend cette valeur, même pendant
une rampe. N=0 change immédiatement et peut créer un saut. Le bloc vide n’avance
rien ; `reset()` retrouve la valeur de création et annule la rampe. Un refus de
valeur, durée ou format ne change pas l’état.

`Command.pitch_bend_to(semitones, frames)` applique la même progression dans
l’espace des demi-tons (−24..24), avec phase conservée. Le rapport de fréquence
est `2^(semitones/12)`. Toute la rampe doit garder les voix sous Nyquist et les
steps float32 positifs ; une nouvelle note est aussi vérifiée contre la cible
encore en cours. `Command.gain_to(gain, frames)` règle linéairement le gain global
0..1 de l’instrument, initialement 1, après la somme des voix. Les durées utilisent
la même plage que Control. Le reset de l’instrument remet le gain à 1 et le bend à 0.
La rampe continue à avancer quand aucune voix ne joue ; elle ne redémarre pas
avec chaque note. Les effets existants ne reçoivent pas automatiquement des
rampes de leurs paramètres.

## Alimenter un flux sans rejouer le bloc

`Synthesis.StreamProducer.create(audio, source, duration_frames,
block_frames:512, capacity_frames:4_800)` prépare un tampon de travail et ouvre
un flux de même format que le Generator. La durée finie accepte 0..int64 max,
y compris pour une source infinie. Les blocs acceptent 1..65 536 frames ; la
capacité suit [le contrat du flux](Streaming.md).

`producer.stream()` fournit le handle pour `audio.play`, les contrôles et
`stream_info`. Garder le producteur vivant pendant toute la lecture : il retient
Audio et la source, et libère le flux quand sa dernière référence disparaît.
La classe source partage son état ; un struct est copié dans la valeur de
protocole. Le producteur commence à l’état courant de la source, sans reset
implicite. Son compteur commence à zéro à la création.

`pump()` produit au plus un bloc et essaie d’en écrire le suffixe. Il retourne
le nombre de frames acceptées ou `would_block` si le flux est plein. Une
écriture partielle garde le reste du tampon ; les prochains appels l’envoient
sans re-rendre la source ni répéter les commandes. Une fois la durée entièrement
écrite, le producteur ferme automatiquement l’entrée. Les appels suivants
retournent zéro. Durée zéro ferme sans rendre de sample.

L’application préremplit le flux avant `play`, appelle `pump` régulièrement,
puis attend la fin après `input_closed()`. Elle peut appeler `wait_writable`
hors du calcul des blocs après un `would_block`, ou réessayer lors de son prochain
tour. Le producteur ne réalise aucune attente volontaire ni callback Silex
sur un thread natif. Préparer et utiliser source/producteur sur un seul thread.

## Observer l’avance et les commandes tardives

| Compteur | Signification |
|---|---|
| `produced_frames()` | Frames déjà calculées depuis la création du producteur |
| `written_frames()` | Frames acceptées par le flux |
| `pending_frames()` | Différence produced − written, toujours ≤ block_frames |
| `input_closed()` | Toutes les frames ont été écrites et l’entrée fermée |
| `stream_info().consumed_frames` | Frames prises en charge par le mixer |

Les frames calculées ne sont plus modifiées par une nouvelle cible de Control.
Programmer une commande de Sequence avant son `rendered_frames()` est refusé.
Les événements connus se placent donc sur l’horloge de production ; un geste en
direct agit sur les prochaines frames à calculer. La capacité de flux plus un
bloc borne l’avance en frames non consommées, à laquelle s’ajoute la sortie
préparée du mixer/device. `consumed_frames` n’est pas la position exacte du
haut-parleur. L’exemple utilise 1 440 frames de file et 480 de bloc à 48 kHz,
soit au plus 40 ms de PCM non consommé, hors sortie déjà préparée, à vitesse1.
Ce calcul ne promet pas une latence système uniforme ni l’absence de manque.

Pause/reprise utilisent les contrôles Audio ; la pause conserve file et bloc.
Une source ouverte affamée reste active et peut être réalimentée. Un arrêt
anticipé termine la lecture ; le prochain pump refuse de produire davantage.
La durée inclut la release des notes et la queue d’effets choisie : fermer
l’entrée ne génère pas automatiquement leur fin. Attendre `drained` pour un
vidage normal. Pour rejouer, attendre/arrêter puis libérer l’ancien producteur,
réinitialiser la source et créer un nouveau flux ; un flux déjà démarré ne se
réutilise pas.

Les écritures doivent être exclusives au producteur. Écrire ou fermer directement
son flux avant sa fin est détecté avant le prochain calcul. Un échec de la source
ou une sortie non finie/hors −1..1 bloque le producteur : libérer et reconstruire
avec une source réinitialisée. Les erreurs source/Audio sont propagées.
Le rendu interne peut dépasser −1..1, mais la sortie vers Audio doit conserver
une marge explicite ; les rampes ne normalisent pas les voix.

Le tampon Silex reste borné après préparation. `pump` inclut le transfert PCM
allouant de `Audio.write` ; il ne convient pas comme callback sans allocation.
La [qualification des ressources](Resources.md) sépare calcul et transfert.
Cela ne certifie pas les allocations internes de SDL ni un temps réel dur.
Les preuves couvrent les écritures partielles, l’identité avec le rendu mémoire, les pauses, le manque, l’arrêt,
la fermeture, les queues et la durée de vie. L’écoute du programme complète
ces preuves pour les transitions et la continuité de la sortie réelle.

[Jouer une partition MIDI avec ses propres instruments](MIDI.md).
