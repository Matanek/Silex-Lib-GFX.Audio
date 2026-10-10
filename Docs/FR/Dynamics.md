# Maîtriser les écarts de niveau

`Processing.Compressor` réduit les écarts au-dessus d’un seuil et permet un
regain explicite. `Processing.Limiter` impose un plafond aux samples traités.
Ils implémentent `Processor` et se composent avec les effets de l’application.
Aucun des deux n’est ajouté automatiquement aux sources ou à la lecture.

[DynamicSounds.sx](../../Examples/DynamicSounds.sx) compare une phrase aux accents inégaux :
sec, compressé avec regain, mélange moitié sec, puis limité. L’atténuation finale
est identique dans les quatre passages ; les différences de volume sont voulues.
Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/DynamicSounds.sx --release
```

Fragment pour un `format` et un buffer `samples` préparés :

```sx
match try Processing.Compressor.create(format, threshold_db:-18.0, ratio:4.0,
    attack_seconds:0.008, release_seconds:0.12, makeup_db:9.0) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match try effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choisir les réglages

Les formats acceptent 1..8 canaux et 1..384 000 Hz entiers. Les contrôles sont
float32 finis, avec les plages suivantes. Les dBFS se rapportent à une amplitude
sample de 1 : le niveau linéaire est `exp(db * ln(10)/20)`.

| Effet / paramètre | Défaut | Plage et sens |
|---|---|---|
| Compressor `threshold_db` | −18 | −96..0 dBFS, seuil |
| Compressor `ratio` | 4 | 1..100 ; 4:1 réduit un dépassement de 12 dB à 3 dB en régime établi |
| Compressor `attack_seconds` | 0,01 | 0..10 s, montée du détecteur |
| Les deux `release_seconds` | 0,1 | 0..10 s, descente du détecteur |
| Compressor `makeup_db` | 0 | −24..24 dB, regain/atténuation après compression |
| Limiter `ceiling_db` | −1 | −96..0 dBFS, plafond des samples |
| Les deux `wet` | 1 | 0..1, dosage sec/traité |

`Compressor.create(format, ...)` et `Limiter.create(format, ...)` retournent un
`Result`. Le compresseur expose `set_threshold(threshold_db)`, `set_ratio(ratio)`,
`set_times(attack_seconds, release_seconds)` et `set_makeup(makeup_db)`.
Le limiteur expose `set_ceiling(ceiling_db)` et `set_release(release_seconds)`.
Les deux proposent `set_wet(wet)` et `set_bypass(bool)`. Les setters numériques
retournent `Result<void, Error>` ; un refus garde réglages et historique.
Les changements s’appliquent au prochain bloc, sans lissage des paramètres.

Les temps sont des constantes de filtre à un pôle, pas une durée pour atteindre
exactement la cible ni une mesure entre 10 et 90 %. Pour une durée t positive,
`alpha=1-exp(-1/(sample_rate*t))`, calculé en float32 ; t=0 donne alpha=1.
L’arrondi limite la précision des temps extrêmes. Le limiteur attaque toujours
immédiatement : aucun réglage d’attaque lente ne compromet son plafond.

## Comprendre la détection et la sortie

Une seule crête `max(abs(canal))` par frame commande tous les canaux. Ils
reçoivent la même réduction, conservant leur balance dans la précision float32.
Un canal silencieux reste silencieux. La détection liée peut donc atténuer tous
les canaux à cause d’un seul ; ce modèle ne propose pas de détection indépendante.

Le compresseur suit la crête p avec `e=e_previous+alpha*(p-e_previous)` ;
alpha vient de l’attaque en montée et du relâchement en descente. L’implémentation
emploie des formes équivalentes pour éviter les débordements intermédiaires.
Pour un seuil linéaire T, le gain vaut 1 si e<=T ou ratio=1, sinon
`(e/T)^(1/ratio-1)`. Les logarithmes sont soustraits avant exponentielle,
sans calculer un rapport susceptible de déborder. Le regain est explicite.
La [courbe statique à seuil franc](https://www.mathworks.com/help/audio/ref/compressor-system-object.html)
exprime le ratio en dB ; les temps et la détection décrits ici sont propres à Silex.
Une attaque positive laisse passer des transitoires ; ce compresseur ne garantit
aucun plafond et son regain peut produire des valeurs hors de ±1.

Le limiteur prend immédiatement e=p en montée ; en descente, son détecteur suit
le même filtre de relâchement. Si e dépasse le plafond C, la sortie traitée est
`(sample/e)*C`, bornée à ±C pour l’arrondi. Normaliser avant multiplication évite
un gain sous-normal imprécis pour une entrée immense. Sinon le sample est conservé.
Le plafond est garanti sur les samples float32 avec wet=1 et bypass=false ;
ce n’est pas une mesure true peak du signal reconstruit entre samples.

Wet dose `(1-wet)*sec + wet*traité`. Wet=0 et bypass donnent exactement le sec,
tout en faisant avancer le détecteur. Un mélange contenant du sec peut dépasser
le plafond. Le format, le nombre de frames et leur position sont conservés ;
aucun lookahead ou retard audio. Ces effets ne créent pas de queue audible dans
le silence, mais leur détecteur influence les notes suivantes. `reset()` efface
ce détecteur et garde les réglages et le bypass. Une référence de classe partage
l’état ; construire des instances distinctes pour des chaînes indépendantes.

## Préparer les ressources et traiter les erreurs

Tout le bloc est vérifié avant mutation : samples finis et frames complètes,
y compris sous bypass. Une tranche vide n’avance rien. Les invalides retournent
`invalid_input`, opération `audio.process`. Les buffers de sortie sont préparés
à la création : un float32 par canal, jusqu’à huit, plus l’état scalaire.
Les octets physiques dépendent des slots, en-têtes et réserve du runtime.

Une frame est entièrement calculée avant écriture de sortie et du détecteur.
Un dépassement float32 retourne `limit_exceeded` en gardant la frame fautive et
son état ; un préfixe peut déjà être traité. Reset et reconstruire le bloc original
avant reprise. Le regain du compresseur peut déclencher ce cas ; le limiteur
normalise les entrées extrêmes sans multiplier préalablement une grande amplitude.

`process` ne conserve pas la vue et ne crée aucun tableau. Le coût est linéaire
en samples ; la crête et le gain sont partagés entre canaux. Le compresseur
calcule au plus un logarithme et une exponentielle par frame au-dessus du seuil,
hors bypass/wet=0/ratio=1 ; les coefficients temporels sont calculés seulement
à création et changement de temps. Aucune garantie de temps réel n’est annoncée.

[Les oracles](Validation.md) couvrent courbes, temps, canaux, blocs, réglages,
extrêmes et erreurs ; [la composition](Composition.md) explique l’extension utilisateur.
