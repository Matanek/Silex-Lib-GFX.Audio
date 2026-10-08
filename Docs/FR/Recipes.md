# Choisir une recette procédurale

Pour fabriquer un son de jeu ou d’application, commencer par une source,
contrôler sa durée et son niveau, puis ajouter les traitements qui expriment
l’intention. Le package fournit les briques ; l’application possède ses
recettes, ses graines et ses paramètres.

[English version](../EN/Recipes.md).

## Du bip à la musique

Pour une mélodie courte, [choisir un timbre ou un instrument et préparer le son](Music.md).
Pour une partition, [créer le player MIDI](MusicPlayer.md) : il possède
l’alimentation et les contrôles. Les parcours ci-dessous donnent accès aux
primitives pour une composition détaillée.

| Intention | Sources et composition | Guide et source exécutable |
| --- | --- | --- |
| Bip, impact, laser | Oscillateur, bruit blanc, filtre, ADSR ou courbe de fréquence. | [Synthèse](Synthesis.md), [ProceduralSounds.sx](../ProceduralSounds.sx) |
| Explosion, ambiance | Bruit filtré, grave et enveloppe ; mixer plusieurs générateurs. | [Composition](Composition.md), [ModulatedSounds.sx](../ModulatedSounds.sx) |
| Moteur variable | FM, harmonique et bruit rose ; commandes lissées sur la chronologie en frames. | [Production continue](Continuous.md), [ContinuousSounds.sx](../ContinuousSounds.sx) |
| Texture rétro | Onde carrée, quantification et maintien d’échantillons. | [Bitcrusher](Bitcrusher.md), [RetroSounds.sx](../RetroSounds.sx) |
| Mélodie directe | Instrument polyphonique et séquence de commandes datées en frames. | [Instruments](Instruments.md), [PolyphonicMelody.sx](../PolyphonicMelody.sx) |
| Partition MIDI | Parser la partition et fournir ses propres instruments par binding. | [MIDI](MIDI.md), [MIDIMelody.sx](../MIDIMelody.sx) |

Les sources exécutables s’utilisent depuis `SilexProject/`, par exemple
`silex run Packages/GFX.Audio/Docs/MIDIMelody.sx --release`. La démonstration
consolidée appartient à `Silex-Examples/Sources/ProceduralAudio/Main.sx` ; elle
propose `--case beep|impact|laser|explosion|engine|retro|melody|midi` et `--check`
sur son exécutable compilé. Son guide bilingue explique paramètres et variantes.
Ces parcours sont disponibles dans les branches locales livrées.

## Contrôler durée, rythme et niveau

Une frame contient un échantillon par canal. À 48 000 frames/s, 240 frames
valent 5 ms ; un bloc stéréo de 480 frames contient 960 valeurs. Les commandes
musicales et les changements de régime s’appliquent sur cette horloge, sans
attendre un timer applicatif. À 120 BPM, un temps dure 24 000 frames. Le lecteur
MIDI traduit les tempos de la partition dans cette même chronologie.

Prévoir attaque et relâchement pour les frontières du son. Un effet comme un
délai ou une réverbération peut continuer après la dernière note : laisser
assez de frames à sa queue avant de fermer le flux. Pour une commande de gain
ou de panoramique MIDI, `controller_ramp_frames` permet un lissage optionnel.

Les gains sont linéaires et les oscillateurs et filtres utilisent des hertz.
Un mix additionne ses sources ; mesurer le niveau et réduire les gains si
nécessaire, ou choisir un [limiteur](Dynamics.md). Le bitcrusher dégrade
volontairement le signal ; à 48 000 frames/s, `hold_frames:6` donne un maintien
équivalent à une fréquence effective de 8 000 Hz. Les graines fixes de bruit
et `reset` permettent de comparer exactement les variantes.

## Faire évoluer ses propres compositions

`Synthesis.Generator`, `Processing.Processor` et `Synthesis.Instrument` sont
les contrats d’extension. L’application peut implémenter ses propres sources,
effets et instruments ; les compositions publiques les acceptent. Les
[traitements](Processing.md) et la [composition](Composition.md) décrivent
format, vues de blocs et état conservé entre appels.

Pour un son court décrit en notes, `Melody.prepare` possède le rendu et la
création du son. Le parcours brut reste disponible : rendre les échantillons
puis appeler `Audio.create`. Pour un flux avancé, préparer `Synthesis.StreamProducer`,
préremplir et gérer ses écritures partielles avant de fermer l’entrée. Une
[sortie en mémoire](Offline.md) permet de vérifier le même rendu sans device.
L’écoute juge le timbre ; les comparaisons PCM vérifient la reproductibilité.
Ces briques ne fournissent ni banque d’échantillons, ni hôte VST, ni humanisation
automatique.

[Choisir le coût d’une lecture musicale](MusicResources.md).
