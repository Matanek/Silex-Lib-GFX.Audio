# Ajouter du chorus et du flanger

`Processing.ModulatedDelay` mélange le son avec une copie dont le retard
varie suivant un sinus. Un retard de quelques dizaines de millisecondes produit
un chorus ; un retard plus court et du feedback donnent un flanger. Ces effets
utilisent les échantillons fournis, sans banque de sons.

La [démonstration complète](../../Examples/ChorusAndFlanger.sx) joue le même accord
procédural quatre fois : sec, chorus, flanger à feedback positif, puis négatif.
Une enveloppe précède le délai, et le rendu conserve une demi-seconde de silence
pour sa queue. Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/ChorusAndFlanger.sx --release
```

Fragment pour un `format` à 48 kHz et un buffer `samples` préparés :

```sx
match Processing.ModulatedDelay.create(format, max_delay_frames:1_200,
    delay_frames:720.0, depth_frames:240.0, rate_hz:0.8, feedback:0.0, wet:0.5) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choisir le retard, le mouvement et le niveau

Les durées comptent des frames, indépendamment des canaux : à 48 kHz,
48 frames valent 1 ms. `delay_frames` est le centre et `depth_frames` la
profondeur. Le retard vaut `centre + profondeur * sin(2*pi*phase)`.
La phase commence à zéro, puis avance de `rate_hz/sample_rate` par frame.
Le sinus est partagé entre les canaux ; chaque canal conserve son propre son.
Ce chorus n'ajoute donc pas automatiquement une largeur stéréo.

| Recette à 48 kHz | Centre | Profondeur | Vitesse | Feedback | Wet |
| --- | --- | --- | --- | --- | --- |
| Chorus | 720 frames / 15 ms | 240 / 5 ms | 0,8 Hz | 0 | 0,5 |
| Flanger | 96 frames / 2 ms | 72 / 1,5 ms | 0,6 Hz | ±0,75 | 0,5 |

Le retard minimal est une frame. La lecture est causale et interpolée
linéairement entre deux frames passées : une impulsion retardée de 2,5 frames
apparaît pour moitié aux frames 2 et 3. La copie traitée arrive entre
`centre-profondeur` et `centre+profondeur`, avec l'étalement de l'interpolation ;
le chemin sec n'ajoute aucune frame. Le format et le nombre de frames sont fixes.

La sortie vaut `(1-wet)*sec + wet*retard`, et le délai mémorise
`sec + feedback*retard`. Wet=1 émet seulement la copie retardée. Wet=0 et
bypass conservent exactement le sec, mais l'historique et la phase continuent.
Le feedback peut être négatif et sa valeur absolue doit rester sous 1.
Aucune normalisation ni limitation n'est ajoutée. Pour une entrée bornée par
A, l'historique est borné théoriquement par `A/(1-abs(feedback))` depuis reset ;
choisir une marge de niveau avant la sortie audible.

Avec feedback nul, après la fin de l'entrée, au plus
`ceil(centre+profondeur)` frames de silence suffisent à vider la copie retardée.
Avec feedback, la queue décroît et n'a pas de durée finie prédéfinie : continuer
à traiter du silence selon le seuil choisi par l'application. `reset()` la coupe.
L'interpolation peut atténuer les aigus ; modulation rapide, grands changements
de retard et sidebands peuvent produire de l'aliasing. Aucun filtre anti-aliasing,
suréchantillonnage ou lissage des réglages n'est promis.

## Préparer l'effet et le régler entre les blocs

`create(format, max_delay_frames, delay_frames, depth_frames:0.0,
rate_hz:0.5, feedback:0.0, wet:0.5)` retourne un `Result`.
Le format accepte 1..8 canaux et une fréquence entière de 1 à 16 777 216 Hz.
Les réglages sont des float32 finis. Centre ± profondeur doit tenir dans
[1, max_delay_frames], profondeur ≥0, vitesse ≥0 et strictement sous Nyquist.
Une vitesse positive dont le pas devient zéro est refusée. Vitesse=0 fige
la phase courante ; après reset, le retard vaut donc le centre.

`max_delay_frames` prépare la plage de réglage ; il va de 1 à
`1_048_576/channels - 1` avec division entière. Le stockage du retard possède
une frame supplémentaire pour l'interpolation. Tous les buffers sont préparés
à la création ; leur contenu float32 occupe
`4 * ((max_delay_frames+1)*channels + 2*channels)` octets logiques.
L’allocation physique ajoute la réserve et les en-têtes ; les éléments float32
occupent quatre octets sur ARM64 et des slots de huit octets sur X64.

`set_delay(delay_frames, depth_frames)` modifie les deux durées ensemble dans
la plage préparée. `set_rate(rate_hz)`, `set_feedback(feedback)` et
`set_wet(wet)` retournent `Result<void, Error>` ; un refus conserve l'état
et les réglages. `set_bypass(bool)` commence à false.
Les modifications sont immédiates au prochain bloc, sans effacer l'historique
ni redémarrer la phase. `reset()` efface l'historique et remet la phase et le
curseur à zéro, tout en gardant les réglages. Construire une autre instance
pour un état indépendant : les références de classe partagent l'effet.

## Traiter les blocs et les erreurs

Les vues doivent contenir des frames complètes et des samples finis.
Tout le bloc est vérifié avant écriture ou avancée de l'état, y compris sous
bypass. Un bloc vide ne fait rien. Les invalides retournent `invalid_input`,
opération `audio.process`.

Un dépassement float32 dans le feedback ou la sortie retourne `limit_exceeded`.
La frame fautive et son état audio restent intacts, mais un préfixe peut déjà
être traité. Appeler reset et reconstruire le bloc original avant une reprise.
Le feedback peut déborder même sous bypass, puisque l'effet continue.

Le rendu s'exécute sur le thread de l'application. Il n'alloue aucun nouveau
buffer dans `process`, ne conserve pas la vue, et calcule au plus un sinus
par frame, partagé entre les canaux. Les conversions de fréquence et les
capacités sont préparées hors boucle ; un retard figé ne recalcule pas son
sinus par frame. La phase float32 est destinée au timbre : sa précision limitée
ne constitue pas une horloge de transport musical ou une garantie temps réel.

[Les oracles](Validation.md) couvrent impulsions, échos signés, LFO connu,
annulation d'un ton, décroissance, canaux, découpage exact, reset, changements,
erreurs et composition consommatrice. Pour écrire votre propre effet, voir
[la composition](Composition.md).
