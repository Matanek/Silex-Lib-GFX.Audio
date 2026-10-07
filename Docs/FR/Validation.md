# Vérifier les parcours audio

Les commandes suivantes s’exécutent depuis la racine `SilexProject`, avec la
toolchain locale qui intègre la correction des vues mutables par méthode.
Les archives vérifiées doivent être présentes dans `Boundary/` ; leurs chemins
et empreintes sont déclarés dans `Package.json`. Le [guide du provider](../../Native/README.md)
décrit leur reconstruction et leur publication séparée.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy silex test Packages/GFX.Audio/Tests --nocache
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py
python3 Packages/GFX.Audio/Tests/GeneratedSamplesValidation.py
python3 Packages/GFX.Audio/Tests/OfflineValidation.py
```

La suite couvre chargement mémoire, handles et propriétaires, chronologie,
groupes et pauses, capacité du flux, silence/reprise, vidage, rendu sans
périphérique, traitements et niveaux. Le driver muet sert aux contrôles de
lecture ; les comparaisons PCM servent aux garanties de mixage et de traitement.
Le pilote vidéo factice permet aussi le test de coexistence SDL avec une fenêtre
sans accès au bureau. Les vérifications de rejet imposent un diagnostic et un code d’échec, avec une
limite de durée pour détecter les attentes qui ne peuvent pas progresser.

`ReleaseValidation.py` reprend les 23 oracles publics de `Processing`,
`Production`, `StreamGroups` et `Synthesis` en Release. Il utilise un pilote
volontairement inexistant : les oracles s’appuient sur le rendu hors ligne et ne demandent
aucun périphérique. Ils vérifient notamment la chaîne à état et le même
producteur scalaire en source complète et en flux, avec conversion 24→48 kHz,
une tolérance absolue de 10⁻⁶ et les compteurs de frames. Les oracles de synthèse
couvrent sinus, bruit reproductible, niveaux ADSR, blocs invalides et
conformances de protocoles depuis un consommateur externe.

```sh
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target macos-x64 --execute
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target linux-x64
```

`--target` compile et lie sans exécuter ; `--execute` demande aussi l’exécution
et suppose une cible compatible avec la machine. Les six cibles du package
sont `macos-arm64`, `macos-x64`, `linux-arm64`, `linux-x64`, `windows-arm64` et
`windows-x64`. Une liaison sur une cible ne constitue pas une preuve
d’exécution sur son système. La qualification conservée ci-dessous porte sur
les 13 oracles du socle ; elle ne qualifie pas automatiquement les ajouts de
synthèse pour ces cibles.

Les exemples `GeneratedTone`, `MemorySound`, `StreamingTone`, `Timeline`,
`Groups`, `Offline`, `ProcessedTone` et `ProceduralSounds` sont des sources
exécutables sous `Docs/`. Employer par exemple :

```sh
SDL_AUDIODRIVER=dummy silex run Packages/GFX.Audio/Docs/ProcessedTone.sx --release --nocache
SDL_AUDIODRIVER=__silex_no_audio_driver__ silex run Packages/GFX.Audio/Docs/Offline.sx --release --nocache
```

Ces preuves portent sur le PCM et l’état logique du mixer. Les compteurs ne
mesurent pas l’instant exact de présentation aux haut-parleurs. Les traitements
s’exécutent sur le thread applicatif ; le provider n’appelle pas de callback
Silex sur son thread audio. Les données et les primitives restent indépendantes
d’un instrument, d’un séquenceur ou de MIDI.

## Qualification conservée du 7 octobre 2026

La livraison locale de la production audio a été qualifiée sur GFX.Audio
`a821c4a8776151761eea8a062540271b987e1166` et Silex
`4e1dfdbe339c3972f86684a5898030bbea404c72`. Ce dernier apporte la correction
des vues mutables par méthode. Les socles étaient GFX
`46d14c329b6acae53a1fb70038fb8496e3b080bc` et STD
`4112bb54390c55d39e85a5414991359abdff15dc`.

Les cinq livraisons ci-dessous ont été intégrées dans les branches `main`
locales. Cette table conserve les commits des reçus de `gfx-audio-production`
après le retrait de sa capsule ; elle ne qualifie pas automatiquement un futur
commit.

| Reçu livré | GFX.Audio | Silex |
| --- | --- | --- |
| `memory-stream-core` | `d5efc07170c11c59da5708f1f31889aabe78fd27` | — |
| `timeline-groups` | `7405034b8a8f1cbbd96005c6c8abf2abfeeaeaf5` | — |
| `offline-render` | `9c5a0d97567db074960d576b2cf35c723d99628d` | — |
| `block-processing` | `78fcbe478706ac1e3a7e6459a3b5a0fad899bf7b` | `4e1dfdbe339c3972f86684a5898030bbea404c72` |
| `production-final` | `a821c4a8776151761eea8a062540271b987e1166` | `4e1dfdbe339c3972f86684a5898030bbea404c72` |

La suite audio a réussi **53 tests sur 53, dans 19 fichiers**, y compris après
réintégration depuis la racine du workspace. Les **13 oracles PCM Release** ont
été exécutés sur macOS ARM64 et X64 via Rosetta, sans pilote audio ; ils ont
été composés et liés pour les six cibles. Linux et Windows n’ont pas été
exécutés. Les sept exemples cités plus haut ont réussi en Release ; les dix
rejets de `GeneratedSamplesValidation.py` et le rejet d’attente hors ligne de
`OfflineValidation.py` ont produit les échecs explicites attendus.

Les gates du compilateur `zig build test` et `zig build check` étaient vertes :
244 tests de langage dans 93 fichiers, 84 tests d’admission de l’optimiseur et
28 programmes. Le cas `Tests/ControlFlow/MutableViewCalls.sx` a aussi été
exécuté en interprétation, ARM64 Debug/Release et X64 Release, avec résultat
`2.25`.

Les six archives du provider `SDL3_mixer-3.2.4-silex.6` ont été reconstruites
deux fois à l’identique. Les empreintes du manifeste, des métadonnées
d’artefacts, de [SHA256SUMS](../../Boundary/SHA256SUMS.txt) et du
[patch](../../Boundary/SDL3_mixer-3.2.4-silex.6.patch) concordaient lors de la
livraison finale. Les archives locales sont conservées ; leurs URLs réservées
ne constituent pas une publication.

L’utilisateur avait autorisé la réintégration sous réserve de tests verts et
de l’absence de défaut connu. Il a explicitement accepté la clôture le
7 octobre 2026 : « on clos la spec, puisque tout est ok, et réintégré dans les
branch main locale ». Les tests, scripts, exemples et explications restent dans
les dépôts. Cette clôture ne publie ni branche distante, ni tag, ni release.
