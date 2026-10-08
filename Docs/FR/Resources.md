# Choisir les capacités et le budget de production

Préparez les instruments, effets et buffers avant de calculer les blocs.
Les événements utilisent l’horloge entière en frames ; le débit de calcul et
le remplissage du flux déterminent la marge de production disponible.
Le tempo de la partition reste indépendant de la cadence de l’application.

## Préparer puis rendre

`SineInstrument.create(max_voices:16)` prépare de 1 à 64 voix par instrument.
À capacité pleine, `voice_policy` refuse la note ou remplace la plus ancienne,
avec un raccord réglable. Une chaîne `Processed` accepte au plus 32 traitements.
Les capacités de délai et la taille de réverbération sont préparées à création ;
leurs historiques persistent entre blocs. Un changement qui reconstruit un
effet ou une source doit se faire hors du calcul de blocs.

`Sequence` retient jusqu’à sa capacité choisie de 1 à 65 536 événements.
`schedule` peut faire grandir sa collection : appelez-le hors du rendu.
Le rendu consomme les événements déjà préparés, sans les recopier. MIDI prépare
également sa partition et ses registres de notes avant lecture : jusqu’à 128
bindings et de 1 à 4 096 identités de notes retenues, selon le choix de l’application.
Les limites de fichier, pistes et événements sont explicites dans le [guide MIDI](MIDI.md).

Fournissez une vue mutable d’un buffer possédé et préparé à `render`/`process`.
L’instrument sinusoïdal et les modulations calculent par tranches internes
d’au plus 512 frames ; un appel plus grand effectue davantage de travail.
Les helpers de rendu en mémoire de l’application et `Audio.render` produisent
au contraire un nouveau tableau possédé. Les effets et instruments utilisateur restent responsables de leurs
propres allocations, durées, niveaux et erreurs.

## Calcul et transfert PCM

Le compteur de test sur macOS ARM64 a détecté **zéro allocation** lors du
premier bloc, de 100 blocs successifs, des commandes valides et du reset pour
les quatre charges ci-dessous, en Debug et Release. Un oscillateur isolé,
une `Sequence` avec notes au milieu des blocs et un `MIDI.Player` jusqu’à la
fin et au relâchement passent aussi ce contrôle. Phase vide et croissance d’un
tableau servent de témoins. Aucun appel aux copies libc n’est détecté dans ces
phases ; les écritures ou copies inline ne sont pas comptées.

Ce résultat couvre le thread applicatif marqué, pas les threads SDL. Le compteur
ne couvre pas les allocations Silex x64 par syscalls directs ; son témoin positif
y échoue. Il ne fournit donc aucune preuve de zéro allocation sur x64, Linux
ou Windows. Voir [le test reproductible](../../Tests/Resources/README.md).

`Audio.write` packe les échantillons dans un buffer natif temporaire puis SDL
gère sa file. Une écriture partielle de 127 frames stéréo demande 1 016 octets
pour ce buffer ; les recharges de file peuvent ajouter des allocations.
`StreamProducer.pump` inclut ce transfert : **il n’est pas sans allocation**.
Appelez-le sur le thread applicatif, avec préremplissage et capacité explicites.
La capacité du flux et le buffer Silex bornent les frames retenues ; ces mesures
ne certifient ni les détails mémoire de SDL ni ses délais.

## Charge mesurée

Mesure du 8 octobre 2026, Apple M3 Pro (12 cœurs, 18 Go), macOS 26.6.2,
Release, 48 kHz stéréo. Voix sinus de `110 + 13 × id` Hz, vélocité `0.25 / N`,
ADSR par défaut ; passe-bas 8 kHz, chorus (960 ± 240 frames, 0.7 Hz,
feedback 0.1, wet 0.25), réverbération (taille 0.5, 1.5 s, damping 0.5,
wet 0.3), compresseur par défaut et limiteur −3 dB.

Sept répétitions par charge, 64 blocs d’échauffement puis 1 000 blocs mesurés,
ordre des charges tournant. Le compteur d’allocations est désactivé. Le temps
inclut les lectures d’horloge à résolution microseconde ; stockage des mesures,
contrôles numériques et affichage se font hors de l’intervalle. Le transfert
PCM, SDL, le périphérique et l’ordonnancement d’une application ne sont pas mesurés.

| Voix / frames | Budget du bloc | ARM64 natif : médiane / p95 / max | x64 sous Rosetta : médiane / p95 / max |
|---|---:|---:|---:|
| 16 / 128 | 2 667 µs | 156 / 161 / 236 µs | 348 / 357 / 977 µs |
| 16 / 512 | 10 667 µs | 607 / 620 / 1 367 µs | 1 362 / 1 383 / 1 625 µs |
| 64 / 128 | 2 667 µs | 339 / 346 / 374 µs | 827 / 837 / 1 004 µs |
| 64 / 512 | 10 667 µs | 1 307 / 1 335 / 1 544 µs | 3 207 / 3 229 / 9 027 µs |

Les médianes entre répétitions varient respectivement de 155–159, 605–607,
338–340 et 1 302–1 321 µs sur ARM64 ; de 348–352, 1 360–1 364, 827–828
et 3 205–3 210 µs sous Rosetta. La charge de 16 voix prend environ 6 % du
budget en médiane sur ARM64 ; celle de 64 voix environ 12–13 %. Sous Rosetta,
ces parts montent à 13 % et 30–31 %, avec un pic à 85 % à 64 voix/512 frames.
Ce pic laisse peu de marge pour une application chargée. Rosetta ne représente
pas les performances d’un processeur Intel ou AMD natif.

La préparation demande entre 778 048 et 803 920 octets cumulés à l’allocateur
ARM64 pour ces charges. Ce total inclut créations et croissance des buffers,
pas seulement leur taille finale ; ce n’est pas un pic de mémoire résidente.
L’allocation physique Silex peut dépasser `frames × channels × 4`.

Les sources DSP mesurées sont celles d’Audio `ada2c3570df1ffa3ac7065a11ab9892abff40af7`,
compilées avec Silex `cfc682ca4018081063fef25a6f429868f3dbb655`.
La réconciliation avec Silex `60d90abf1d7a689eef421b54fb9bd58b09d2313e`
reproduit exactement les deux binaires chronométrés. Les durées ne sont ni un test de succès à seuil fixe ni une certification de
temps réel dur. Requalifiez la charge de votre application sur sa machine,
avec ses instruments, effets, commandes et marge de transfert.

[Faire évoluer un son et alimenter un flux](Continuous.md) ·
[Vérifier les parcours audio](Validation.md)

[Choisir le coût d’une lecture musicale](MusicResources.md).
