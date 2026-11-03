# Donner une voix à un moteur thermique

Pour composer les pièces et remplacer un assemblage pendant la lecture, utiliser
[le parcours Engine.assemble](EngineParts.md). Cette page décrit le prototype
conservé par `Engine.create()`.

`Synthesis.Engine` produit un moteur quatre temps à partir du régime et de son
contexte de fonctionnement. Le jeu fournit les tours/minute, l'accélérateur,
la charge et le frein moteur ; il n'a pas à décrire les pièces mécaniques.
Ce premier modèle acoustique est un prototype à qualifier à l'écoute.

L'[exemple autonome](../../Examples/Engine.sx) fait monter un V8, puis le ramène
au ralenti dans une seule lecture continue. Depuis `SilexProject/` :

```sh
silex run Packages/GFX.Audio/Examples/Engine.sx --release
```

## Fournir le régime du jeu

Fragment après création d'un moteur :

```sx
var source = Synthesis.Engine.create()
source.set_state(3_200.0, throttle:0.8, load:0.6, engine_brake:0.0, ramp_frames:480)
source.set_character(exhaust:0.7, roughness:0.4, ramp_frames:480)
```

Le régime règle la fréquence des pulsations. `throttle` décrit l'ouverture des
gaz et `load` l'effort fourni : changer la charge à régime constant change le
signal. L'effort modifie aussi la part du front de pression dans chaque
pulsation, indépendamment du niveau global. `engine_brake` atténue l'énergie
et le mordant des pulsations pendant la décélération.
Le modèle ne calcule ni transmission, ni vitesse véhicule, ni couple aux roues.

`exhaust` va d'un échappement feutré à ouvert ; `roughness` ajoute de la modulation
bruitée et règle les différences d'énergie et d'attaque propres aux cylindres et
leur variation lente entre combustions. À zéro, ces différences sont désactivées ;
une faible turbulence d'écoulement reste modulée par la pression. Elle n'est pas
une piste de souffle indépendante et disparaît avec la queue de pression.
Leur graine est fixée à la création. Ces contrôles n'effacent
ni la phase des pulsations ni les historiques acoustiques. Le V8 regroupe ses
combustions dans deux voies selon un ordre de bancs cross-plane. Des temps de
propagation et niveaux distincts préservent ce rythme dans le mélange, y compris
en mono. Les autres
nombres de cylindres utilisent une répartition alternée simplifiée, sans
prétendre reproduire toutes les architectures réelles.

## Rendre et lire

`set_state` accepte aussi `fuel`, une disponibilité normalisée entre 0 et 1,
à 1 par défaut. Elle dose l'énergie des prochaines combustions, indépendamment
du régime mécanique. Une baisse de `fuel` ne modifie pas les pulsations déjà
injectées dans les conduits. À zéro, le moteur peut encore tourner sans produire
de nouvelles combustions ; rendre les blocs suivants laisse finir la pression
et les traitements acoustiques. Les rampes permettent une extinction progressive.
Ce contrôle n'est ni une masse d'essence ni une simulation d'injection.

Fragment pour réduire l'alimentation sur 350 ms à 48 kHz pendant que le jeu
fournit encore un régime de 1 800 tr/min :

```sx
source.set_state(1_800.0, ramp_frames:16_800, fuel:0.0)
```

Le moteur est un `Synthesis.Generator`. `render` remplit une vue PCM mono ou
stéréo et peut être composé avec les traitements existants ou alimenter un
[flux continu](Continuous.md). Les générateurs et leurs commandes s'utilisent
sur le même thread applicatif. Préparer moteur, tampons et flux avant lecture.

`set_state` et `set_character` utilisent des rampes linéaires en frames, par
défaut 480. La première frame conserve la valeur courante ; la cible est atteinte
après la durée choisie. Une nouvelle cible reprend la valeur courante. Zéro
applique un changement immédiat, susceptible d'être audible. Les commandes
n'altèrent pas les blocs déjà calculés et mis en file.

`current_rpm()` donne le régime de la prochaine frame à produire, pas celui
exactement présenté par les haut-parleurs. `reset()` vide les historiques,
réinitialise la graine et la variation des cylindres et retrouve 800 tr/min,
commandes à zéro, alimentation `fuel` à 1, échappement
0,65 et rugosité 0,4. Pour arrêter progressivement, commander zéro tr/min, rendre
la queue acoustique, puis fermer le flux ; le modèle ne produit pas lui-même
une notification de fin.

## Réglages et limites

`Engine.create(format, cylinders:8, seed:42, amplitude:0.4)` accepte :

- 22 050 à 192 000 Hz, un ou deux canaux ; défaut 48 kHz stéréo ;
- 1 à 12 cylindres, fixés à la création ;
- une graine entière, réutilisée par reset ;
- une amplitude finie entre 0 et 1, fixée à la création.

Le régime doit être fini entre 0 et 12 000 tr/min ; les autres contrôles sont
finis entre 0 et 1. Les durées acceptent 0 à 16 777 216 frames. Une entrée invalide
retourne `invalid_input` avant mutation ; `try` conserve cette erreur. Un bloc
doit contenir des frames complètes ; un bloc vide n'avance pas le moteur.

La saturation douce borne chaque sample par l'amplitude choisie. Elle ne remplace
pas la gestion du niveau lors du mélange de plusieurs sources. Chaque combustion
injecte une décharge d'échappement préparée en phase : front bref, détente positive
puis raréfaction, sans oscillateur accordé injecté dans l'excitation. Sa durée
suit 0,3 cycle quatre temps, bornée à 3–60 ms. Le front et le corps sont dosés
selon l'effort. Deux accumulateurs conservent ces contributions, suivis des
conduits et de trois résonances par voie. La dérivée de pression utilise une
échelle temporelle fixe pour garder son poids quand la fréquence d'échantillonnage
change. Cette approximation acoustique ne calcule ni cylindrée, ni pression
thermodynamique, ni débit de soupape réel. Le générateur ne fait pas
fluctuer le régime fourni : une régulation de ralenti appartient au jeu ou au
banc d'écoute. Une ambiance peut être ajoutée séparément avec
[Processing.Reverb](Reverb.md) ; aucun espace de réverbération n'est imposé.

Le modèle ne charge aucun enregistrement et ne simule pas les écoulements de gaz.
Les réponses et coefficients sont préparés à création. Le coût suit le nombre
de frames et de combustions, donc aussi le régime et le nombre de cylindres.

L'approche s'inspire de la séparation excitation/bruit/coloration étudiée dans
[Engine Simulator](https://github.com/ange-yaghi/engine-sim), avec une excitation
simplifiée indépendante. Aucun code ou fichier sonore de ce projet n'est embarqué.
