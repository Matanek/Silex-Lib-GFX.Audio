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
Les deux lignes ont des longueurs distinctes, ce qui préserve un caractère de
bancs jusque dans le mélange mono.
`EngineParts.motocross()` et `motocross(Cycle.two_stroke)` fournissent des monos
450 quatre temps et 250 deux temps approximatifs. Ces assemblages sont des
points de départ acoustiques, sans certification du son d’un véhicule commercial.
`Assembly()` fournit aussi un monocylindre quatre temps configurable.

Le générateur implémente `Synthesis.Generator` : il remplit des blocs PCM,
compose avec les traitements existants et alimente un `StreamProducer`.
Les commandes et le rendu appartiennent au même thread applicatif.

## Donner à chaque pièce un rôle audible

| Pièce | Paramètres | Effet du modèle |
| --- | --- | --- |
| `Block` | Cylindres, alésage/course en mm, cycle, allumage, bancs | Cylindrée, cadence et distribution des impulsions |
| `Head` | Chambre en cm³, combustion en ms | Compression géométrique, énergie et forme de la détente |
| `Intake` | Conduit `Pipe`, boîte à air en litres, absorption du filtre | Propagation, résonance et bruit pulsé d’aspiration |
| `Exhaust` | Collecteur et ligne `Pipe`, `Silencer` | Retards, réflexions aux changements de section et coloration |
| `Silencer` | Litres et absorption 0..1 | Résonance de chambre et atténuation des aigus |
| `Mechanics` | Masse du bloc en kg, amortissement 0..1 | Résonance du bloc et atténuation des vibrations |
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
thermodynamique complète. Le deux temps ne possède pas encore un pot de détente
à cônes ni un balayage détaillé. La qualité et la couverture des timbres se
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
Les rampes n’effacent ni les phases, ni les queues acoustiques.

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

Un ordre d’allumage explicite est une permutation des numéros 1..N. Les angles
explicites, un par événement, commencent à zéro et croissent dans le cycle de
720° ou 360°. Une liste vide signifie des événements régulièrement espacés.
`exhaust_banks` associe chaque cylindre à un échappement numéroté depuis zéro ;
une liste vide les dirige tous vers le premier.

Le format accepte 22 050..192 000 Hz, mono ou stéréo. Graine et amplitude 0..1
sont fixées à la préparation. La sortie est bornée par l’amplitude, par défaut
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
