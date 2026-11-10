# Assembler un moteur sonore avec des pièces

`Synthesis.Engine.assemble` prépare un moteur à partir de pièces typées. Le jeu
fournit ensuite régime, charge, accélérateur et alimentation. La génération
fonctionne sans démo, sans fichier sonore et sans processus auxiliaire.

L’[exemple complet](../../Examples/EngineAssembly.sx) assemble un V8, remplace
un silencieux et lit un flux continu. Depuis la racine du workspace :

```sh
silex run Packages/GFX.Audio/Examples/EngineAssembly.sx --release
```

Ajouter `--check` au binaire compilé permet d’exercer le même consommateur
sans ouvrir de périphérique audio.

## Partir d’une signature de véhicule

`GFX.Audio.Synthesis.EngineVehicles.catalogue()` fournit 17 profils acoustiques :
citadines essence trois/quatre cylindres et turbodiesel, sportives I4 turbo,
flat-six, V8 cross-plane, V10 et V12, cross 125/250/500 deux temps et 250/500
quatre temps, motos de course I4/V4 et customs bicylindres 1 200/1 800 cm³.
Chaque `Profile` contient `id`, `name`, `parts`, `idle_rpm`, `redline_rpm`,
`response_seconds` et `roughness`. Les identifiants restent indépendants des
libellés d’interface. Les régimes et le temps de réponse sont des indications
pour le banc du consommateur ; le générateur ne simule pas une transmission.

Fragment après les imports `GFX.Audio.Synthesis` et
`GFX.Audio.Synthesis.EngineVehicles` :

```sx
let profile = EngineVehicles.catalogue()[9]
var engine = Synthesis.Engine.assemble(profile.parts)
engine.set_character(1.0, profile.roughness, ramp_frames:0)
engine.set_state(6_000.0, throttle:0.85, load:0.7)
```

Ce profil est un mono cross 250 deux temps. La génération demeure entièrement
procédurale. Les profils sont des archétypes stylisés, sans enregistrements ni
reproduction certifiée de véhicules commerciaux. Ce prototype est distinct de
la [chaîne thermique de référence](Vehicles.md), désormais employée par
l’atelier des véhicules pour conserver le son d’EngineLibrary.

## Choisir un assemblage puis remplacer une pièce

Fragment après les imports `GFX.Audio.Synthesis` et
`GFX.Audio.Synthesis.EngineParts` :

```sx
var parts = EngineParts.v8()
parts.exhausts[0].silencer = EngineParts.Silencer(
    volume_litres:18.0, absorption:0.8)
var engine = Synthesis.Engine.assemble(parts)
engine.set_state(3_200.0, throttle:0.8, load:0.6)
```

`EngineParts.v8()` fournit un V8 7,45 L à deux lignes, ordre cross-plane.
Les deux lignes ont des longueurs distinctes et des niveaux de sortie 1 et 0,1,
comme le banc Chevrolet de référence. `Exhaust.outlet_level` (0..1, défaut 1)
règle la contribution entendue de chaque sortie ; ce niveau d’écoute ne modifie
pas la cylindrée ou l’allumage. Deux lignes identiques au même niveau peuvent
effacer le rythme propre à chaque banc dans leur somme mono.
`EngineParts.motocross()` et `motocross(Cycle.two_stroke)` fournissent des monos
450 quatre temps et 250 deux temps approximatifs. Ces assemblages sont des
points de départ acoustiques, sans certification du son d’un véhicule commercial.
`Assembly()` fournit aussi un monocylindre quatre temps configurable.

Le générateur implémente `Synthesis.Generator` : il remplit des blocs PCM,
compose avec les traitements existants et alimente un `StreamProducer`.
Les commandes et le rendu appartiennent au même thread applicatif.

## Comprendre le rôle de chaque pièce

| Pièce | Paramètres | Effet du modèle |
| --- | --- | --- |
| `Block` | Cylindres, alésage/course en mm, cycle, allumage, bancs | Cylindrée, cadence et distribution des impulsions |
| `Head` | Chambre en cm³, combustion en ms, `ignition`, `sharpness` | Compression géométrique, énergie et attaque ; claquement propre à l’allumage par compression |
| `Intake` | Conduit `Pipe`, boîte à air en litres, absorption du filtre | Propagation, résonance et bruit pulsé d’aspiration |
| `Exhaust` | Collecteur et ligne `Pipe`, `Silencer`, `outlet_level`, `expansion_litres` | Retards, réflexions et résonance de détente optionnelle |
| `Silencer` | Litres, absorption 0..1, `baffles` | Résonance de chambre, atténuation et filtrages successifs des chicanes |
| `Mechanics` | Masse du bloc en kg, amortissement, `clatter`, `whine` | Résonance du bloc, claquement bruité et sifflement lié à la rotation |
| `Turbo` facultatif | Roue en mm, pales, pression maximale en bar, inertie en secondes | Sifflement, montée/retombée et bruit de décharge |

Les combustions et aspirations partagent l’horloge du vilebrequin. À régime
égal, le deux temps allume chaque tour et le quatre temps tous les deux tours.
L’admission et la mécanique continuent pendant une coupure de carburant si
le jeu conserve un régime non nul. Les voies sont mélangées après leurs
traitements ; elles ne constituent pas une série de sons indépendants.

`Block.displacement_litres()` calcule la cylindrée. `Assembly.compression_ratio()`
calcule `1 + volume déplacé par cylindre / volume de chambre`. Le paramètre
`Head.chamber_cc` concerne une chambre. Ce rapport est géométrique ; la
compression effective d’un deux temps dépendrait aussi de ses lumières.

Les conduits utilisent des retards aller-retour à 343 m/s et des réflexions
atténuées ; les chambres utilisent des résonances préparées. L’excitation,
les pertes, le bruit mécanique et le turbo sont des approximations acoustiques.
Le modèle ne calcule pas les soupapes, les écoulements, le couple ou la
thermodynamique complète. La détente du deux temps ajoute une résonance liée
au volume ; elle ne simule ni les cônes ni le balayage. Les chicanes sont des
étages de filtrage acoustique, sans calcul de contre-pression. La qualité et la couverture des timbres se
qualifient à l’écoute, indépendamment de la disponibilité des pièces.

## Piloter le moteur et isoler les voies

`set_state(rpm, throttle:0, load:0, engine_brake:0, ramp_frames:480, fuel:1,
boost:0)` reçoit des commandes finies. RPM va de 0 à 20 000 ; les autres valeurs
vont de 0 à 1. `boost` est une demande acoustique normalisée, avec l’inertie
configurée dans le turbo. Le jeu reste propriétaire de la dynamique du véhicule.

`set_mix(EngineParts.Mix(...), ramp_frames:480)` dose séparément `exhaust`,
`intake`, `mechanics` et `turbo`, chacun entre 0 et 1. Mettre trois voies à zéro
permet d’écouter la quatrième. `set_character(exhaust, roughness)` conserve ses
commandes 0..1 : niveau d’ouverture global et variations entre combustions.
Les variations de `roughness` agissent sur l’énergie des combustions et une
petite ondulation de la rotation. Les rampes n’effacent ni les phases, ni les queues acoustiques.

`fuel:0` arrête les futures combustions. Pour un arrêt complet, fournir aussi
un régime qui descend vers zéro, puis rendre la queue. `current_rpm()` décrit
la prochaine frame produite, pas la position exacte des haut-parleurs.

## Changer les pièces pendant la lecture

Modifier une copie d’assemblage n’altère pas un moteur déjà construit :

```sx
parts.exhausts[0].pipe.length_mm = 1_000.0
engine.set_parts(parts, transition_frames:2_400)
```

`set_parts` valide et prépare les coefficients et tampons sur le thread appelant.
À 48 kHz, le fondu par défaut dure 50 ms. Le nouvel assemblage reprend le régime,
les rampes de commande et la phase du vilebrequin ; ses résonances démarrent dans
le fondu. Le mix défini dans le nouvel assemblage prend effet avec lui.

Pendant un fondu, une seule demande suivante est retenue ; une nouvelle demande
remplace cette attente. Il y a au plus trois modèles préparés et deux modèles
rendus simultanément. La durée acceptée va de 0 à 16 777 216 frames ; zéro
remplace immédiatement et peut cliquer. Le découpage des blocs ne change pas
le PCM de la transition. Un refus ne modifie pas le son en cours.

`parts()` fournit la dernière définition demandée. `cylinders` décrit le modèle
en cours de transition. `reset()` retient le dernier assemblage demandé,
annule les transitions, vide les historiques et retrouve 800 tr/min, gaz/charge/
frein moteur/boost à zéro, alimentation à 1, ouverture à 1, rugosité à 0,15
et mix de cette définition. Il ne constitue pas un arrêt
progressif. La libération de la dernière référence libère le stockage préparé.

## Valider les dimensions

`Assembly.validate()` et `assemble` retournent `invalid_input` avant mutation
pour une définition invalide. `try` conserve l’erreur pour la traiter.

- 1..16 cylindres ; alésage 20..200 mm, course 20..250 mm ;
- chambre 1..500 cm³, combustion 0,1..8 ms, compression géométrique 2..25 ;
- 1..4 échappements ; conduits 20..5 000 mm et diamètre 5..250 mm ;
- chambre de silencieux et boîte à air 0,05..100 L ; absorptions 0..1 ;
- masse mécanique 1..2 000 kg ; amortissement 0..1 ;
- turbo : roue 20..150 mm, 2..16 pales, pression 0,1..4 bar, inertie 0,01..5 s.

`Head.ignition` vaut `Ignition.spark` par défaut ou `Ignition.compression`.
`Head.sharpness`, `Mechanics.clatter` et `Mechanics.whine` vont de 0 à 1
(défaut 0). `Silencer.baffles` accepte 0..8 (défaut 0) ;
`Exhaust.expansion_litres` accepte 0..30 L (défaut 0, résonance désactivée).
Les valeurs non finies sont refusées. La mécanique reste une approximation
du bruit rayonné : les réglages ne déterminent pas une puissance moteur.

Un ordre d’allumage explicite est une permutation des numéros 1..N. Les angles
explicites, un par événement, commencent à zéro et croissent dans le cycle de
720° ou 360°. Une liste vide signifie des événements régulièrement espacés.
`exhaust_banks` associe chaque cylindre à un échappement numéroté depuis zéro ;
une liste vide les dirige tous vers le premier.

Le format accepte 22 050..192 000 Hz, mono ou stéréo. Graine et amplitude 0..1
sont fixées à la préparation. La pression des lignes est transformée en rayonnement de sortie, avec une
attaque lissée et un gain de restitution commun. Ce modèle reste une
approximation acoustique ; il ne garantit pas un effet perceptible de chaque
petite variation de géométrie dans un mélange complet. Isoler la voie et comparer
à régime/charge identiques avant de juger un réglage.

Une marge de niveau avant le limiteur préserve davantage les attaques en
charge ; le niveau du parcours par pièces est réduit par rapport au précédent
modèle. La sortie est bornée par l’amplitude, par défaut
0,4. Les blocs doivent contenir des frames complètes ; un bloc vide n’avance rien.
L’ancienne fabrique `Engine.create()` conserve le prototype quatre temps et son
contrat [existant](Engine.md) ; `assemble` ouvre le parcours par pièces.

## Stockage et mesure

Les tampons et coefficients sont préparés à la construction ou à `set_parts`.
Le contrôle macOS ARM64 Debug/Release observe zéro allocation pendant le premier
bloc, 1 000 blocs avec commandes et mix, le fondu préparé et reset. La préparation
et le remplacement des pièces allouent ; ils doivent rester hors d’un callback
audio temps réel. Ce compteur concerne le thread appelant et exclut SDL,
`Audio.write`, le flux et l’interface. Voir [les ressources](Resources.md).
