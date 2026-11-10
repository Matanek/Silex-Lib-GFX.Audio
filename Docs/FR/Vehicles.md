# Créer un moteur de véhicule avec la chaîne de référence

`GFX.Audio.Engines.Vehicles` prépare un moteur thermique avec le simulateur
d’EngineLibrary. Le profil `454` conserve sa définition d’origine et son PCM.
Les citadines ajoutent un rendu extérieur feutré ; le diesel utilise une voix
hybride issue d’un enregistrement TDI. Les profils restent à qualifier par l’écoute.

Depuis la racine du workspace, l’[exemple sans périphérique](../../Examples/VehicleEngine.sx)
produit des blocs PCM et affiche le régime final :

```sh
silex run Packages/GFX.Audio/Examples/VehicleEngine.sx --debug
```

Pour écouter et exporter un WAV, utiliser l’[atelier des véhicules](https://github.com/Matanek/Silex-Examples/tree/main/Sources/EngineWorkshop).

## Choisir et piloter un moteur

Fragment après les imports `GFX.Audio.Engines` et `GFX.Audio.Engines.Vehicles` :

```sx
var engine = Vehicles.create("cross-250-4t", displacement_cc:300.0)
var controls = engine.controls()
controls.running = true
controls.throttle = 0.6
controls.load = 0.2
engine.set_controls(controls)
```

`create(key:"454", displacement_cc:null)` retourne un `Engines.Engine` en mode
banc libre. Il conserve les parcours `render`, `enqueue` et `render_ready`
[documentés pour les moteurs de référence](Engines.md). La simulation possède
le mouvement du vilebrequin ; la commande ne remplace pas le régime par une
courbe artificielle. Ce parcours ne configure pas de transmission routière.

`Controls.throttle` est une pédale continue optionnelle 0..1. Quand elle est
renseignée, elle remplace `accelerating` ; `null` conserve exactement la
commande historique tout-ou-rien. Le contact coupé ferme les gaz. Une valeur
non finie ou hors plage est refusée avant mutation. Les autres commandes,
dont charge, texture, réponse d’échappement, admission, volume et ambiance,
conservent leur sens. Le réglage `exhaust` mélange le signal brut et la réponse
filtrée : ce n’est pas un nombre de chicanes ou une contre-pression.

## Catalogue et cylindrée

`catalogue()` fournit 18 `Profile` avec `key`, `name`, `displacement_cc`,
`cylinders`, `strokes`, `idle_rpm`, `redline_rpm` et `note` :

- référence `454` ; citadines `city-i3`, `city-i4`, `city-diesel` ;
- sportives `sport-turbo-i4`, `sport-flat6`, `sport-v8`, `sport-v10`, `sport-v12` ;
- cross `cross-125-2t`, `cross-250-2t`, `cross-500-2t`, `cross-250-4t`, `cross-500-4t` ;
- course `race-i4`, `race-v4` ; customs `custom-1200`, `custom-1800`.

`Profile.idle_rpm` décrit un ralenti nominal ; ce n’est pas la commande de
maintien du banc. Conserver `Controls.idle_rpm` à 800 laisse le ralenti libre,
comme dans EngineLibrary. Copier automatiquement le ralenti nominal dans
cette commande engagerait le dynamomètre.

La valeur de cylindrée est en cm³ pour l’ensemble du moteur. Le réglage accepte
50..12 000 cm³ finis et vérifie aussi les limites géométriques du modèle choisi
(alésage 20..200 mm et chambre 1..500 cm³ pour les définitions redimensionnées).
Il agit sur les dimensions et les chambres du simulateur. Les monos adaptent
aussi frottements, inertie et charge du banc à leur taille. `reset()` conserve
la définition et les commandes. Un profil inconnu ou une cylindrée invalide
retourne `invalid_input` avant création du processus moteur.

La référence `454` garde sa géométrie d’origine. Fournir une autre cylindrée
est refusé ; choisir `sport-v8`, construit depuis la définition GM LS, pour un
V8 modifiable. Les V10/V12, I4 de course et customs réutilisent les définitions
LFA, Ferrari 412 T2, Hayabusa et Harley de la banque. Les géométries et chambres
peuvent être adaptées ; ces noms ne certifient pas une reproduction commerciale.

## Écouter les citadines

Les citadines essence utilisent une admission moins ouverte, un calage plus
court et une ligne plus restrictive que l’I4 de sportive. Leur rendu extérieur
atténue le niveau et les harmoniques aiguës. Cette écoute proche n’est pas un
modèle de propagation spatiale ou d’habitacle. Les niveaux ne sont pas normalisés :
une citadine reste plus discrète qu’une sportive au même volume d’écoute.

`city-diesel` combine ce fond d’échappement assourdi avec huit excitations
acoustiques tirées de la référence TDI fournie. Le régime simulé pilote leur
cadence, la charge leur niveau, et la coupure fait décroître cette voix.
`texture` règle la variation entre excitations ; `exhaust` assourdit également
leur réponse. Le rendu est hybride et contient du son enregistré transformé ;
il ne rejoue pas le montage complet. Le reset remet à zéro filtres et phases.

Le nom du moteur enregistré n’est pas identifié. L’extrait ne certifie donc
ni une cylindrée de 1,6 L ni un modèle Volkswagen précis. `note` et le libellé
du catalogue indiquent ce parcours hybride. La voix n’intervient pas sur le
454, les sportives, les motos ou la cross 500 4T.

## Préparation et limites

La création prépare une copie privée des ressources natives et démarre un
processus par moteur. Elle alloue et peut attendre les opérations de fichiers ;
la garder hors d’un callback audio ou d’un chemin par frame. La définition est
fixée à la création. Dans un atelier, remplacer la géométrie moteur arrêté.
Le rendu interactif consomme les blocs prêts ; le rendu synchrone convient à
l’export hors ligne. La fréquence reste 44 100 Hz, stéréo.

La banque native demeure disponible sur macOS ARM64 seulement. Les autres
cibles retournent l’erreur de disponibilité de `Engines.Library.open()`.
Le binaire et les ressources standard embarqués sont conservés ; la fabrique
personnalise uniquement sa copie temporaire.

La mécanique diesel reste approximative : le simulateur conserve l’allumage
commandé et ne modélise pas l’auto-inflammation ni l’injection diesel. La voix
enregistrée corrige sa texture acoustique, pas cette thermodynamique.
Le profil I4 de sportive ne simule pas la suralimentation.
Le 2T conserve le modèle simplifié de lumières et de balayage de la banque,
sans pot de détente à cônes. Ces limites sont aussi indiquées dans `note`.

Le test consommateur compare chaque échantillon du `454` à `Library.engine("454")`
sur démarrage, accélération et coupure. Il exerce aussi les 18 architectures,
la pédale continue, les erreurs et le reset d’une cylindrée personnalisée.
`CityVoices.sx` mesure le niveau des essences, distingue les transitoires diesel
et vérifie reset, extinction et parité entre rendu synchrone et rendu prêt.
Cette preuve préserve la référence et le fonctionnement ; elle ne remplace
pas l’écoute des variantes. Le prototype `Synthesis.EngineVehicles` reste un
générateur distinct et n’est plus la source sonore de l’atelier.
