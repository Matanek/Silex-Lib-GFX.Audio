# Vérifier les parcours audio

Les commandes suivantes s’exécutent depuis la racine `SilexProject`, avec la
toolchain locale qui intègre la correction des vues mutables par méthode.
Les archives vérifiées doivent être présentes dans `Boundary/` ; leurs chemins
et empreintes sont déclarés dans `Package.json`. Le [guide du provider](../../Native/README.md)
décrit leur reconstruction et leur publication séparée.

```sh
SDL_AUDIODRIVER=dummy silex test Packages/GFX.Audio/Tests --nocache
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py
python3 Packages/GFX.Audio/Tests/GeneratedSamplesValidation.py
python3 Packages/GFX.Audio/Tests/OfflineValidation.py
```

La suite couvre chargement mémoire, handles et propriétaires, chronologie,
groupes et pauses, capacité du flux, silence/reprise, vidage, rendu sans
périphérique, traitements et niveaux. Le driver muet sert aux contrôles de
lecture ; les comparaisons PCM servent aux garanties de mixage et de traitement.
Les vérifications de rejet imposent un diagnostic et un code d’échec, avec une
limite de durée pour détecter les attentes qui ne peuvent pas progresser.

`ReleaseValidation.py` reprend les 13 oracles publics de `Processing`,
`Production` et `StreamGroups` en Release. Il utilise un pilote volontairement
inexistant : les oracles s’appuient sur le rendu hors ligne et ne demandent
aucun périphérique. Ils vérifient notamment la chaîne à état et le même
producteur scalaire en source complète et en flux, avec conversion 24→48 kHz,
une tolérance absolue de 10⁻⁶ et les compteurs de frames.

```sh
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target macos-x64 --execute
python3 Packages/GFX.Audio/Tests/ReleaseValidation.py --target linux-x64
```

`--target` compile et lie sans exécuter ; `--execute` demande aussi l’exécution
et suppose une cible compatible avec la machine. Les six cibles du package
sont `macos-arm64`, `macos-x64`, `linux-arm64`, `linux-x64`, `windows-arm64` et
`windows-x64`. Une liaison sur une cible ne constitue pas une preuve
d’exécution sur son système. La qualification locale a exécuté les oracles sur
macOS ARM64 et X64 via Rosetta ; les autres systèmes sont qualifiés ici au niveau de la
composition et de la liaison.

Les exemples `GeneratedTone`, `MemorySound`, `StreamingTone`, `Timeline`,
`Groups`, `Offline` et `ProcessedTone` sont des sources exécutables sous
`Docs/`. Employer par exemple :

```sh
SDL_AUDIODRIVER=dummy silex run Packages/GFX.Audio/Docs/ProcessedTone.sx --release --nocache
SDL_AUDIODRIVER=__silex_no_audio_driver__ silex run Packages/GFX.Audio/Docs/Offline.sx --release --nocache
```

Ces preuves portent sur le PCM et l’état logique du mixer. Les compteurs ne
mesurent pas l’instant exact de présentation aux haut-parleurs. Les traitements
s’exécutent sur le thread applicatif ; le provider n’appelle pas de callback
Silex sur son thread audio. Les données et les primitives restent indépendantes
d’un instrument, d’un séquenceur ou de MIDI.
