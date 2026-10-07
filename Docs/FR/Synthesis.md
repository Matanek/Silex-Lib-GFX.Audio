# Fabriquer un son sans fichier audio

`GFX.Audio.Synthesis` génère sinus, triangle, carré et dent de scie avec
`Oscillator`, des bruits reproductibles avec `WhiteNoise` et `PinkNoise`,
et une enveloppe ADSR avec `Envelope`.
Le [programme ProceduralSounds.sx](../ProceduralSounds.sx) produit un bip puis
un impact associant un grave et du bruit filtré, sans banque ni asset sonore.

Depuis la racine du workspace, avec Silex 0.47.1 ou une version plus récente :

```sh
silex run Packages/GFX.Audio/Docs/ProceduralSounds.sx --release
```

Le [programme WaveformPalette.sx](../WaveformPalette.sx) permet de comparer les
quatre formes, un carré à 25 %, le bruit blanc et le bruit rose :

```sh
silex run Packages/GFX.Audio/Docs/WaveformPalette.sx --release
```

Le bruit rose en Release ARM64 requiert également la toolchain locale intégrant
la correction des retours de boucle de parité, jusqu’à sa publication.

## Générer puis jouer

Un générateur écrit dans un tampon déjà dimensionné. Ce programme produit un
quart de seconde de sinus à faible niveau, puis utilise la lecture Audio habituelle :

```sx
use GFX.Audio
use GFX.Audio.Processing
use GFX.Audio.Synthesis

func main() {
    let format = Processing.Format(sample_rate:48_000, channels:1)
    match Synthesis.Oscillator.create(format, frequency_hz:440.0, amplitude:0.1) {
        failure(error) => { panic(error.detail) }
        success(var source) => {
            var samples:float32[] = []
            var frame = 0
            while frame < 12_000 { samples.append(0.0); frame++ }
            match source.render(&samples[0:samples.count()]) {
                failure(error) => { panic(error.detail) }; success => {}
            }
            var audio = Audio()
            let sound = audio.create(@samples[0:samples.count()], sample_rate:48_000)
            let playing = audio.play(sound)
            audio.wait(playing)
        }
    }
}
```

Le générateur remplace les valeurs de la vue, conserve sa phase entre appels
et ne conserve pas la vue. Le même tampon peut être réutilisé pour plusieurs
blocs. Une vue vide n’avance pas l’état ; une frame incomplète est rejetée avant
mutation. Les canaux sont entrelacés ; ces sources mono dupliquent la même
valeur dans chaque canal du format. Le rendu ne demande pas de périphérique :
ses valeurs peuvent aussi servir à une analyse, un flux ou un mix en mémoire.

`Generator` demande `format`, `render(samples:&float32[..])` et `reset()`.
Une classe utilisateur peut s’y conformer sans Interop. Un protocole dynamique
conserve l’identité de la classe : utiliser deux instances pour deux états
indépendants. Les appels restent séquentiels sur le thread applicatif.

## Régler les sources

`Oscillator.create(format, frequency_hz:440.0, amplitude:1.0, phase:0.0,
waveform:Waveform.sine, duty_cycle:0.5)`
retourne un `Result<Oscillator, Error>`. La phase initiale compte des cycles
dans `[0, 1)`. La fréquence est finie, non négative et strictement sous Nyquist ;
son pas doit rester représentable. Une fréquence nulle conserve la valeur à
la phase choisie. L’amplitude est finie entre 0 et 1.

`set_frequency` conserve la phase ; `set_amplitude` change le niveau sans lissage
automatique. `reset` revient à la phase initiale et garde les réglages courants.
`Waveform` propose `sine`, `triangle`, `square` et `sawtooth`. Le rapport cyclique
est fini et strictement entre 0 et 1 ; il est validé pour chaque forme, et seul
le carré l’utilise. `waveform` et `duty_cycle` se lisent sur l’instance et se
choisissent à la création.

```sx
var source = Synthesis.Oscillator.create(format, frequency_hz:375.0,
    waveform:Synthesis.Waveform.square, duty_cycle:0.25)
```

Triangle, carré et dent de scie sont des sommes harmoniques : au plus 64
harmoniques, toutes strictement sous Nyquist, pondérées par une moyenne de
Fejér. Leurs fronts sont donc arrondis ; près de Nyquist, le timbre s’appauvrit
et le niveau peut diminuer. Le carré à rapport cyclique différent de 50 %
possède une composante continue. Les formes restent dans le domaine unitaire,
avec une marge de calcul float32 de 10⁻⁵. Les coefficients se préparent à la
création et au changement de fréquence ; leur nombre ne croît pas avec la durée.
La phase zéro du triangle monte depuis zéro ; la dent de scie monte de −1
vers +1 et le carré commence sa portion positive à la phase zéro. Aux
discontinuités idéales, la somme harmonique produit une transition lissée.

`WhiteNoise.create(format, seed:42, amplitude:1.0)` retourne un
`Result<WhiteNoise, Error>`. La même graine et les mêmes commandes donnent la
même séquence ; `reset` reprend cette séquence en gardant l’amplitude courante.
Tous les entiers signés sont acceptés. Les graines sont normalisées dans un état
fini ; des graines distinctes peuvent correspondre à la même séquence.
`set_amplitude` accepte le même domaine que l’oscillateur. Ce bruit sert à la
production sonore, pas à la cryptographie.

`PinkNoise.create(format, seed:42, amplitude:1.0)` retourne un
`Result<PinkNoise, Error>` avec les mêmes règles de graine, amplitude et reset.
Il combine douze valeurs maintenues à des cadences d’octaves et un bruit blanc
à chaque frame, selon Voss-McCartney, puis divise leur somme par 13. Cette
normalisation borne les valeurs et donne un niveau RMS inférieur au bruit
blanc à amplitude égale. Le spectre rose reste une approximation ; la
qualification contrôle une puissance par octave presque constante entre
187,5 et 6 000 Hz à 48 kHz. Elle ne garantit pas une loi 1/f à toute fréquence.

Les calculs et phases sont en float32, comme le PCM de Processing. La fréquence
du format va de 1 à 16 777 216 Hz et ses canaux de 1 à 8 ; cette borne garantit
que le taux entier est exactement représentable dans ce chemin de calcul.
Une fréquence très petite reste soumise à la résolution de phase float32.

## Donner une attaque et un relâchement

`Envelope.create(format, attack_frames:240, decay_frames:2_400, sustain:0.5,
release_frames:4_800)` retourne un `Result<Envelope, Error>`.
Les durées comptent des frames, indépendamment des canaux : 240 frames à
48 kHz correspondent à 5 ms. Chaque durée va de 0 à 16 777 216 frames ;
le sustain est un niveau fini dans `[0, 1]`.

L’enveloppe démarre inactive. `note_on()` repart de zéro, monte linéairement
vers 1, descend vers le sustain et y reste jusqu’à `note_off()`.
Le relâchement repart du niveau courant, même pendant l’attaque ou la décroissance.
Un second note-off pendant le relâchement ne le recommence pas. Une durée nulle
franchit immédiatement son étape. La frame utilise son niveau courant, puis
avance l’état : une attaque de deux frames produit `0, 0.5`, suivis du pic `1`.

`process(&samples[...])` multiplie les valeurs du bloc et satisfait le protocole
`Processing.Processor`. Appliquer explicitement source, enveloppe, puis filtre
ou délai selon le timbre souhaité. Le traitement accepte les valeurs finies
au-delà de ±1, sans normalisation ; le gain d’enveloppe reste entre 0 et 1.
Les invalides sont rejetés avant mutation du bloc et de l’état.
`is_active()` reste vrai jusqu’à la fin du relâchement, y compris pour un sustain
nul ; `reset()` revient au silence inactif. Le redéclenchement et les changements
abrupts de réglage peuvent créer une discontinuité : aucun lissage n’est implicite.

## Utiliser les blocs et connaître les limites

Les rendus entier et découpé conservent l’état à 10⁻⁶ absolu sur les fixtures
qualifiées. La génération ne redimensionne pas le tampon et ne crée pas de
sortie par frame ; les allocations cachées du runtime et la charge temps réel
ne sont pas encore mesurées pour cette capacité. Aucun callback Silex n’est
appelé depuis le thread audio.

Une création ou un réglage invalide retourne `invalid_input`, avec l’opération
`audio.synthesis`. Un échec de réglage conserve l’ancien état. Les générateurs
sont des sources continues ; choisir explicitement la durée de rendu ou fermer
le flux après les blocs voulus. Les files partielles restent régies par
[le contrat du flux](Streaming.md).

[Traiter les blocs](Processing.md) · [Rendre un mix en mémoire](Offline.md) ·
[Retour au guide Audio](README.md)
