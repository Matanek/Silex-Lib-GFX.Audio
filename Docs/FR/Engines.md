# Réutiliser les moteurs du banc validé

`GFX.Audio.Engines` reprend la chaîne sonore du premier banc : simulation du
moteur, profils, réponses d’échappement, aspiration du 4T et mélange de sortie.
Le consommateur ne recopie ni ces calculs ni les filtres de la démo. Les huit
profils et les réglages existants sont conservés ; ce parcours ne dépend pas de
l’atelier expérimental par pièces.

## Préparer la bibliothèque

La bibliothèque est un dossier déployable contenant le moteur de calcul et ses
ressources. Construire puis préparer ce dossier avec les outils du package,
décrits dans [la préparation native](../../Native/EngineSimulator/README.md).
Les scripts n’utilisent aucun fichier de Silex-Examples. Copier ensuite ce dossier
complet avec l’application ; l’API accepte son chemin absolu ou relatif au
répertoire courant. Il n’existe pas de recherche implicite dans le dépôt de la démo.

L’[exemple autonome](../../Examples/EngineLibrary.sx) emploie exclusivement le
package. Depuis la racine du workspace :

```sh
silex compile Packages/GFX.Audio/Examples/EngineLibrary.sx --release -o Build/EngineLibrary-Consumer
Build/EngineLibrary-Consumer /chemin/absolu/vers/EngineLibrary
```

Il exerce le moteur hors ligne, sans ouvrir de fenêtre ou de périphérique sonore.

## Choisir le moteur et ses commandes

Fragment après `use GFX.Audio.Engines` :

```sx
var library = Engines.Library.open("Audio/EngineLibrary")
var engine = library.engine("454")
var controls = engine.controls()
controls.running = true
controls.accelerating = true
engine.set_controls(controls)
```

`library.profiles()` fournit les profils, leurs clés, libellés, zone rouge,
échelle de compte-tours, régime de ralenti et cycle. Les clés actuelles sont
`454`, `berline`, `sport`, `cruiser`, `moto`, `truck`, `cross4` et `cross2`.
Un profil inconnu est refusé. Un moteur possède ses phases, sa simulation et ses
historiques indépendamment des autres moteurs.

`controls()` retourne une copie. `set_controls()` valide toutes les valeurs avant
modification ; les valeurs non finies sont refusées. Les commandes reprennent
les effets du banc validé :

| Commande | Effet |
| --- | --- |
| `running` | Contact, démarreur puis fonctionnement ; couper laisse évoluer rotation et queues acoustiques |
| `accelerating` | Gaz ouverts ou relâchés, avec la réponse native du moteur |
| `idle_rpm` | Régime de maintien du banc, 700..4 000 tr/min ; ce n’est pas une imposition instantanée du régime |
| `load` | Charge du banc, 0..1 |
| `texture` | Bruit d’air et jitter du profil, 0..1 ; la combustion physique conserve ses variations |
| `exhaust` | Mélange échappement brut/filtré, 0..1, avec équilibrage et lissage existants |
| `intake` | Aspiration mesurée du `cross4`, 0..1 ; les autres profils ne fournissent pas cette voie |
| `volume` | Gain de sortie lissé, 0..1 |
| `ambience` | Part de réverbération courte, 0..1 |

Les valeurs initiales sont celles du banc : contact coupé, gaz relâchés,
maintien 800, charge 0,2, texture et échappement 1, volume 0,7, ambiance 0.
L’aspiration initiale vient du profil. L’application possède les raccourcis,
la perte de focus et les gardes de changement de véhicule.

## Produire des blocs sans bloquer l’interface

Le format est fixe : 44 100 Hz, stéréo. `Engine` implémente
`Synthesis.Generator`. `render()` calcule des frames complètes dans la tranche
fournie, par blocs internes d’au plus 480 frames. Ce parcours attend le calcul :
l’utiliser hors ligne ou dans un contexte de production qui peut attendre.

Pour une interface, `enqueue(depth:4)` demande au plus quatre blocs de 480
frames. `render_ready()` remplit une tranche de 960 samples et retourne `false`
si le prochain bloc n’est pas encore disponible ; ne pas boucler en attente dans
la frame graphique. `pending_blocks()` expose l’avance en cours. Après réception,
réalimenter la file jusqu’à la profondeur choisie. Conserver les écritures
partielles du flux audio avant de consommer le bloc suivant.

Ne pas mélanger `render()` avec des demandes asynchrones en attente. Une tranche
partielle, une profondeur hors 1..4 ou une permutation de parcours incompatible
est refusée avant consommation. Le traitement de sortie s’applique à la réception,
comme dans le premier banc. Les commandes de simulation sont prises au moment
des demandes ; l’avance audio ajoute donc un délai de commande explicite.

`current_rpm()` et `is_starting()` décrivent le dernier bloc reçu. `reset()`
annule les demandes, recrée la simulation et efface les historiques ; il conserve
les commandes. C’est une réinitialisation immédiate, susceptible de couper le son.
Pour un arrêt naturel, mettre `running` à `false` et continuer à produire la queue.
Libérer le dernier moteur ferme son entrée et libère son processus de calcul.

## Portée de cette extraction

La comparaison avec le premier banc conserve le PCM bit à bit sur les huit
profils, avec démarrage, gaz, changements d’échappement/texture/charge, volume,
ambiance et coupure. L’ancien banc reste un témoin autonome.

Cette version garde le simulateur complet et un processus par moteur. Elle
alloue et communique entre processus ; elle n’est pas adaptée à un callback
audio temps réel. La tenue dans une application lourde et le pilotage direct par
le régime du jeu restent à qualifier. La construction et l’exécution de cette
extraction sont vérifiées sur macOS ARM64 ; les autres cibles restent à préparer
et à tester. L’installation du package seule ne fournit pas encore une banque
native préconstruite pour chaque OS.
