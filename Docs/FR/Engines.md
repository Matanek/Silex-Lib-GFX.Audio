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
échelle de compte-tours, régime de ralenti, nombre de rapports et cycle. Les clés actuelles sont
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
| `idle_rpm` | Banc libre : régime de maintien, 700..4 000 tr/min ; ce n’est pas une imposition instantanée du régime |
| `load` | Charge du banc libre, 0..1 |
| `texture` | Bruit d’air et jitter du profil, 0..1 ; la combustion physique conserve ses variations |
| `exhaust` | Mélange échappement brut/filtré, 0..1, avec équilibrage et lissage existants |
| `intake` | Aspiration mesurée du `cross4`, 0..1 ; les autres profils ne fournissent pas cette voie |
| `volume` | Gain de sortie lissé, 0..1 |
| `ambience` | Part de réverbération courte, 0..1 |

Les valeurs initiales sont celles du banc : contact coupé, gaz relâchés,
maintien 800, charge 0,2, texture et échappement 1, volume 0,7, ambiance 0.
L’aspiration initiale vient du profil. L’application possède les raccourcis,
la perte de focus et les gardes de changement de véhicule.

## Ajouter une boîte de vitesses optionnelle

Le mode libre reste le défaut de `library.engine("454")`. Pour reprendre le
contexte Route du banc validé :

```sx
var engine = library.engine("454", transmission:Engines.Transmission.automatic)
var controls = engine.controls()
controls.running = true
controls.accelerating = true
engine.set_controls(controls)
```

La présence de la transmission est fixée à la création. `controls.transmission`
passe ensuite de `Transmission.automatic` à `Transmission.manual` sans recréer
la simulation. En manuel, `controls.gear` est le rapport demandé, de 0 (point mort)
à `engine.gearing.ratios.count()`. `controls.braking` freine le véhicule du banc. Le mode
Route conserve les calculs longitudinaux existants ; il ne dépend pas de Physics.
Régime de maintien et charge du banc libre ne pilotent pas ce contexte Route.

`engine.drive_state()` retourne `null` en mode libre ; en Route, il fournit
`gear`, `speed_kmh`, `shifting`, `shift_refused` et `shift_count`, synchronisés
sur le dernier bloc reçu. Le rapport demandé peut être refusé pour surrégime :
ne pas écraser cette demande avec le rapport réel à chaque réponse. Après N en
roulant, plusieurs appuis + peuvent ainsi atteindre un rapport sûr. Une demande
refusée n’est pas engagée plus tard sans nouvelle commande.

Pour revenir au mode libre, créer un autre moteur. Dans la démo, ce changement
est possible dès le contact coupé, sans attendre le ralentissement : le nouveau
contexte réinitialise régime et vitesse. Modifier la présence de transmission
sur le moteur existant, demander un rapport hors plage
ou freiner en mode libre est refusé avant mutation. `reset()` conserve le mode
choisi et les commandes, tout en recréant le contexte arrêté.

## Choisir la démultiplication

Chaque profil fournit ses valeurs d’origine dans `profile.gearing` : `ratios`
contient les rapports de la première à la dernière vitesse, `final_drive` le
rapport de pont. Sans option supplémentaire, ces valeurs et le rendu du banc
restent inchangés. `engine.gearing` décrit la configuration réellement utilisée.

Pour une boîte plus courte, fournir la configuration à la création du moteur
Route. Fragment après ouverture de `library` :

```sx
var gearing = Engines.Gearing(ratios:[4.0, 2.5, 1.8, 1.3, 1.0], final_drive:4.5)
var engine = library.engine("454", transmission:Engines.Transmission.manual, gearing:gearing)
```

Les rapports et le pont acceptent des `float64` finis dans 0,05..20. La boîte
contient 1..12 rapports strictement décroissants ; le point mort reste la
commande 0, sans entrée dans la liste. `validate()` permet de vérifier une
configuration ; `library.engine()` la vérifie aussi avant de créer le moteur.
Cette option exige une banque native reconstruite au format v2. Les banques v1
restent utilisables avec les rapports d’origine et refusent une personnalisation.

Un rapport numérique plus élevé raccourcit la démultiplication : à vitesse de
roue égale et embrayage engagé, le régime augmente. Le comportement dépend aussi
du couple moteur, du véhicule et de sa traînée ; allonger un rapport ne garantit
pas un gain d’accélération ou de vitesse. Le passage automatique utilise la boîte
configurée. Le nombre de rapports d’origine reste disponible dans `profile.gears`.

La configuration est fixée à la création et conservée par `reset()`. Pour la
modifier, créer un autre moteur. La démo garde les changements en préparation
jusqu’à « Appliquer la démultiplication », moteur et véhicule arrêtés. Elle
permet aussi de rétablir les rapports d’origine ; ses réglages ont une précision
de 0,001, tandis que l’API accepte les valeurs `float64` directement.

## Fournir le régime depuis un jeu

Quand le jeu possède déjà son état moteur, utiliser `driven_engine` plutôt que
le banc libre ou son véhicule Route. Ce parcours exige une banque v3 :

```sx
var engine = library.driven_engine("454")
engine.set_state(Engines.OperatingState(rpm:2_500.0, load:0.65, running:true))
```

`OperatingState` contient le régime du vilebrequin en tr/min, la charge positive
de combustion `load` dans 0..1 et le contact `running`. La charge commande
l’admission et l’effort audible à régime donné ; 0 représente les gaz relâchés,
1 l’effort maximal demandé. Le frein moteur découle de la baisse de régime et
de charge. Il n’y a pas de seconde commande d’accélération contradictoire.
Toutes les valeurs doivent être finies ; le régime accepte 0..`profile.ceiling`.
Une valeur invalide est refusée avant mutation. `state()` retourne la consigne.

La création commence à régime nul, contact coupé. Le jeu fournit ensuite les
phases de démarrage, de marche et d’arrêt. Couper le contact conserve les bruits
de pompage tant que le jeu impose une rotation ; régime nul et contact coupé
laissent s’écouler la queue acoustique. `current_rpm()` donne le régime mesuré
dans le dernier bloc reçu.

Le même simulateur thermique, les profils et les traitements du banc produisent
le son. Une contrainte de rotation suit le régime fourni, avec une variation
bornée à 20 000 tr/min par seconde. Les phases et les historiques persistent
entre commandes. Ce parcours ne simule ni une autre boîte ni un autre véhicule.
Les méthodes `render`, `enqueue`, `render_ready`, `pending_blocks` et `reset`
suivent les règles ci-dessous ; `reset()` conserve la consigne. Les banques v1/v2
restent utilisables pour les bancs précédents et refusent `driven_engine`.

La démo MonsterTruck de Silex-Examples emploie cette entrée. Sa conduite n’a
pas de vilebrequin ni de boîte : un adaptateur acoustique lit la rotation des
jantes et l’effort de leur commande, sans changer les forces. Cette dérivation
reste une approximation de démo.

## Produire des blocs sans bloquer l’interface

Le format est fixe : 44 100 Hz, stéréo. `Engine` implémente
`Synthesis.Generator`, tout comme `DrivenEngine`. `render()` calcule des frames
complètes dans la tranche fournie, par blocs internes d’au plus 480 frames. Ce parcours attend le calcul :
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
audio temps réel. Le régime externe dispose d’un parcours contrôlé hors ligne ;
sa qualité à l’écoute et la tenue dans une application lourde restent à qualifier.
La construction et l’exécution de cette extraction sont vérifiées sur macOS ARM64 ; les autres cibles restent à préparer
et à tester. L’installation du package seule ne fournit pas encore une banque
native préconstruite pour chaque OS.
