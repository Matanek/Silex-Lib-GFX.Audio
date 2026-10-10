# Donner une réverbération au son

`Processing.Reverb` ajoute une queue diffuse au signal, sans fichier
d'impulsion ni banque de sons. Choisir une taille de pièce à la création,
puis régler la décroissance, l'amortissement des aigus et le mélange sec/traité.

La [démonstration](../../Examples/ReverberantSounds.sx) joue trois notes pincées,
puis laisse résonner le silence. Elle compare le son sec, une pièce courte,
une queue longue brillante et une queue longue sombre. L'enveloppe précède
l'effet ; les derniers blocs de silence rendent sa queue. Depuis
`SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/ReverberantSounds.sx --release
```

Fragment pour un `format` et un buffer `samples` préparés :

```sx
match try Processing.Reverb.create(format, room_size:0.65, decay_seconds:2.0,
    damping:0.5, wet:0.45) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match try effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Régler l'espace, la couleur et les niveaux

`create(format, room_size:0.5, decay_seconds:1.5, damping:0.5, wet:0.3)`
retourne un `Result`. Le format accepte 1..8 canaux et une fréquence entière
de 1 à 384 000 Hz. Room size, damping et wet sont des float32 finis de 0 à 1 ;
decay va de 0,05 à 20 secondes.

Room size agrandit les retards, sans représenter une dimension physique en
mètres. Il reste fixe : préparer une nouvelle instance pour une autre taille.
`set_decay(decay_seconds)`, `set_damping(damping)` et `set_wet(wet)`
retournent `Result<void, Error>`. Un refus garde les réglages et l'historique.
`set_bypass(bool)` commence à false.
Les changements sont immédiats au prochain bloc, sans lissage et sans effacer
la queue ; une variation brutale peut s'entendre.

Wet dose `(1-wet)*sec + wet*réverbération`. Wet=1 émet seulement la queue ;
wet=0 et bypass préservent exactement le sec tout en alimentant l'historique.
Il faut encore traiter le silence après la source pour entendre la fin.
La queue n'a pas de durée finie prédéfinie : l'application choisit son seuil
et sa durée de rendu. `reset()` efface tous les retards et filtres, tout en
gardant la taille et les réglages ; il coupe donc la queue.

Chaque canal possède ses retards et filtres. Aucun son ne passe vers un autre
canal : un canal silencieux reste silencieux, deux entrées identiques donnent
deux sorties identiques. Cette version ne crée pas de largeur stéréo, ne
convertit pas le mono et ne simule pas une salle physique mesurée.
Une référence de classe partage son état ; créer deux instances pour deux
réverbérations indépendantes.

Les retours peuvent amplifier certaines fréquences. Le mélange interne des
quatre lignes utilise un gain fixe de 0,25 par ligne ; il ne normalise pas
leur contenu selon le niveau ou la durée. Aucun limiteur n'est ajouté.
Prévoir une marge avant `Audio.create` ou un flux audible, qui demandent des
samples dans ±1. Les calculs acceptent les entrées finies hors de ±1.

## Connaître les retards et la décroissance

Le réseau emploie quatre lignes à feedback filtré en parallèle, puis deux
diffuseurs allpass en série. La structure s'appuie sur les
[réverbérateurs de Schroeder décrits par Julius O. Smith](https://www.dsprelated.com/freebooks/pasp/Schroeder_Reverberators.html).
L'implémentation Silex définit ses propres retards et réglages.

Les six longueurs sont `max(1, round(base * scale))`, calculées en float32
à la création, avec `scale=(0.5+1.5*room_size)*sample_rate/48000`.
Les bases à 48 kHz sont 1429, 1783, 1973, 2099, puis 241 et 83 frames.
Round arrondit les demi-entiers en s'éloignant de zéro. Aux fréquences très
basses, plusieurs longueurs se confondent ; le comportement reste causal,
mais ne représente pas une réverbération naturelle.

Pour une ligne de longueur D : le sample retardé v passe dans
`f=(1-d)*v+d*f_précédent`, avec `d=0.95*damping` ; la ligne reçoit
`sec+g*f`, où `g=exp(-ln(1000)*D/(sample_rate*decay_seconds))`.
Damping nul conserve des retours brillants ; l'augmenter amortit leurs aigus.
Le réglage decay détermine une décroissance nominale de 60 dB pour une ligne
isolée sans amortissement. Il ne garantit pas le RT60 mesuré du réseau complet :
couleur, interférences et diffuseurs modifient sa réponse.

Le mélange est la moyenne des quatre samples retardés. Chaque allpass de
coefficient 0,5 calcule `y=retard-0.5*x` et mémorise `x+0.5*y`.
Ces deux étages diffusent les échos ; ils ne sont pas un second mélange wet.
Le chemin sec n'ajoute aucune frame. La première sortie traitée apparaît après
la plus courte ligne de feedback, sans ajouter les longueurs des diffuseurs,
qui possèdent un chemin direct. Le format et le nombre de frames sont conservés.

## Traiter les erreurs et préparer les ressources

Tout le bloc est vérifié avant écriture ou avancée de l'état : samples finis,
frames complètes, y compris sous bypass. Une tranche vide ne fait rien.
Les invalides retournent `invalid_input`, opération `audio.process`.
Un dépassement float32 retourne `limit_exceeded` avant de modifier la frame
fautive ou son historique, mais un préfixe peut déjà être traité. Appeler
reset et reconstruire le bloc original avant une reprise. Le feedback peut
déborder même sous bypass, puisque les retards continuent.

Les buffers sont privés et préparés à la création. Les retards contiennent au
plus 973 824 samples float32 pour 384 kHz, huit canaux et room size=1.
Le volume logique des valeurs float32 est
`4 * (channels * somme_des_six_longueurs + 15*channels + 4)` octets.
Ce calcul ne mesure pas l’allocation physique : ARM64 utilise des éléments
float32 de quatre octets, X64 des slots de huit octets ; la réserve de capacité,
les en-têtes et trois tableaux de six entiers s’ajoutent. La durée de
décroissance ne change pas la capacité logique. Les coefficients de retour sont calculés à la
création et à `set_decay`, sans allocation.

`process` ne conserve pas la vue et n'alloue pas de nouveau buffer. Par frame
et canal, il traite quatre lignes filtrées et deux allpass, avec un coût constant
par sample ; aucune exponentielle n'est recalculée dans cette boucle.
Il s'exécute sur le thread de l'application, sans garantie de temps réel.

[Les preuves](Validation.md) contrôlent les premiers échos analytiques,
l'amortissement, la queue, les canaux, les blocs, les réglages, les limites,
les erreurs et la composition. Voir aussi [chorus et flanger](ChorusAndFlanger.md)
pour un retard mobile, ou [la composition](Composition.md) pour un effet personnel.
