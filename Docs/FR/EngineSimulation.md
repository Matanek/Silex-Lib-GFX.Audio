# Simuler un assemblage de cylindres

`GFX.Audio.EngineSimulation` expose un premier modèle expérimental de moteur
4T. Définir la géométrie et le déphasage de chaque cylindre, puis créer un
simulateur. Le démarreur, l’allumage, les gaz et le couple résistant pilotent
la rotation. Le mode `hold_rpm` impose un régime pour un essai comparatif.
Relâcher ce mode reprend la rotation libre à partir du régime courant.

```sx
var engine = EngineSimulation.Simulator.create(
    EngineSimulation.Assembly(cylinders:[
        EngineSimulation.Cylinder(),
        EngineSimulation.Cylinder(firing_degrees:180.0)
    ]))
engine.set_controls(EngineSimulation.Controls(starter:true, ignition:true, throttle:0.2))
```

Pour modeler la sortie d’échappement, renseigner `Assembly.exhausts` avec
un à quatre `EngineParts.Exhaust` et affecter chaque cylindre avec
`exhaust_index`, index à partir de zéro. Un conduit, son diamètre et le
silencieux façonnent la détente qui arrive de chaque groupe de cylindres.
`outlet_level` règle le couplage acoustique de la sortie. Une liste vide
utilise la résonance générique sur l’index zéro.

```sx
use GFX.Audio.Synthesis.EngineParts

let first = EngineParts.Exhaust(pipe:EngineParts.Pipe(length_mm:1_180.0, diameter_mm:50.0))
let second = EngineParts.Exhaust(outlet_level:0.35)
var twin = EngineSimulation.Simulator.create(EngineSimulation.Assembly(
    cylinders:[EngineSimulation.Cylinder(), EngineSimulation.Cylinder(firing_degrees:180.0, exhaust_index:1)],
    exhausts:[first, second]))
```

`set_exhaust(paths, cylinder_outlets)` permet de changer d’échappement en
cours de rendu. Fournir une sortie par cylindre dans l’ordre de l’assemblage,
avec des index à partir de zéro. Le simulateur applique la première
configuration au démarrage, puis mélange progressivement les deux
échappements pendant 40 ms. Un nouvel appel pendant la transition retient
le dernier choix pour la transition suivante. Le régime, les phases et les
commandes continuent d’évoluer. `reset()` remet à zéro le dernier échappement
demandé.

Le simulateur est un `Synthesis.Generator` mono à 48 kHz. `render()` calcule
le mix et `render_sources()` calcule les trois sources isolées dans le même
pas de temps. Chaque appel avance le moteur d’autant de frames que contient
le tampon. `cylinder(index)` retourne un instantané par cylindre, avec une
phase en degrés sur le cycle de 720°, une position mesurée depuis le point
mort haut et l’indice de la dernière frame d’allumage s’il y en a eu.
`reset()` remet l’horloge, les commandes, la mécanique et les filtres à leur
état initial. Piloter et rendre une instance depuis le même fil d’exécution.

La cinématique bielle-manivelle relie position et vitesse du piston au
vilebrequin. Une approximation de la compression et de la combustion
fournit la pression. La charge résolue à travers la bielle module l’effort
de glissement et déplace latéralement la jupe du piston dans son jeu.
Le contact avec la paroi excite les résonances du bloc. Le débit d’admission
suit le déplacement du piston et une ouverture de soupape simplifiée. Ses
pulsations excitent la résonance de Helmholtz du plénum et le mode
quart d’onde du conduit. Le modèle retarde leur rayonnement selon la
longueur du trajet vers l’entrée d’air. La turbulence suit le débit.
Le papillon atténue la propagation vers l’entrée à faible ouverture.
Les dimensions d’admission sont estimées à partir de la cylindrée.
À chaque allumage, une variation bornée de charge et de durée de combustion
modifie la pression et le couple. Elle est plus marquée à faible ouverture
des gaz. Chaque cylindre rejoue sa séquence après `reset()`.

La détente du gaz à l’ouverture d’échappement excite la troisième voie.
L’alésage influe sur la durée de combustion et le couplage acoustique.
La durée de détente augmente avec la taille du cylindre, et la pression
module le front à l’ouverture. Les résonances de la sortie générique
descendent lorsque les dimensions augmentent. Les sorties configurées
modélisent les réflexions et l’amortissement de leurs conduits. Les
paramètres par défaut représentent un monocylindre de banc.
