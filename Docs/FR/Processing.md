# Traiter les échantillons avant leur sortie

`GFX.Audio.Processing` propose `Format`, le protocole `Processor`, `LowPass`,
`Delay`, `Equalizer`, `Bitcrusher`, `Distortion`, `DistortionMode`, `StereoPan` et `levels`.
Un effet conserve son état et modifie une tranche `&float32[..]` fournie par l'application. Il peut traiter les blocs d'un
producteur, ceux d'un rendu hors ligne, ou ceux à écrire dans un flux.

Les créations retournent un `Result` et reçoivent un `Format(sample_rate:48_000,
channels:2)`. Le format est fixe pendant la vie de l'effet. Les échantillons
sont entrelacés, finis et contiennent des frames complètes ; une tranche vide
ne fait pas avancer l'état. Les valeurs dépassant ±1 sont acceptées pour
conserver la marge d'un mix, sous réserve de rester représentables en float32.
Le bitcrusher sature explicitement sa partie traitée.
Les paramètres, les coefficients et les historiques des effets sont en float32,
comme le PCM. La mesure RMS accumule l’énergie en float64.

`process(samples:&buffer[0:buffer.count()])` retourne `Result<void, Error>`.
L'ordre des appels est l'ordre des traitements : filtre puis délai produit
une autre chaîne que délai puis filtre. Le consommateur garde le même effet
entre les blocs et appelle `reset()` pour effacer son historique. Les effets
ne conservent pas la tranche après l'appel. Un `Processor` dynamique conserve
l'identité de la classe d'effet ; son réglage et son historique restent partagés.

Le travail s'exécute séquentiellement sur le thread de l'application ; aucun
callback Silex n'est lancé par le thread audio natif. Les effets n'allouent
pas de nouvelle sortie par bloc. Les vues suivent les règles de possession de
Silex et peuvent détacher une collection partagée avant mutation. La capacité
du flux détermine l'avance préparée, pas un temps de présentation garanti.
Cette API utilise la correction de toolchain qui permet aux méthodes de recevoir
les vues mutables comme les fonctions libres ; employer la toolchain locale
qualifiée avec cette tranche tant que sa publication n'est pas effectuée.

## Filtre passe-bas

`LowPass.create(format, cutoff_hz:1000.0)` crée un filtre à un pôle par canal :
`y = (1 - alpha) * y + alpha * x`, avec `alpha = 1 - exp(-2*pi*cutoff/sample_rate)`.
La coupure est strictement positive et inférieure à Nyquist ; une coupure trop
petite pour donner un coefficient non nul est rejetée.
`set_cutoff(cutoff_hz)` valide le réglage et conserve l'historique.

## Délai et écho

`Delay.create(format, delay_frames:4800, feedback:0.5, wet:0.5)` produit
`sortie = entrée + wet * retard`, et mémorise `entrée + feedback * retard`.
Le retard compte des frames, indépendamment des canaux. Chaque canal garde
sa propre queue. La capacité maximale est de 1 048 576 échantillons entrelacés.
Le retour est fini, de module inférieur à 1 ; wet est fini, non négatif et
représentable en float32. `set_feedback` et `set_wet` conservent la queue.
Pour rendre celle-ci, traiter explicitement des blocs de silence pendant une
durée choisie ; aucune attente de queue infinie n'est introduite.

## Égalisation et niveaux

`Equalizer.create(format, low_hz:250.0, high_hz:4000.0, low_gain:1.0,
mid_gain:1.0, high_gain:1.0)` partage le signal avec deux passe-bas à un pôle :
bas, différence des deux passe-bas, puis entrée moins passe-bas supérieur.
Les fréquences sont ordonnées, positives et sous Nyquist. Les gains sont finis,
non négatifs et représentables en float32. Trois gains unitaires recomposent
le signal ; trois gains à 0,5 l'atténuent explicitement.
`set_gains(low, mid, high)` conserve l'historique ; aucun lissage automatique
n'est appliqué lors d'un changement de réglage.

`levels(@samples[0:count], channels:2)` retourne un `Result<Level[], Error>` avec
crête absolue et RMS en float64 pour chaque canal, dans l'ordre d'entrelacement.
La fenêtre est exactement la tranche fournie ; une fenêtre vide donne zéro.
Cette analyse alloue ses petits tableaux par canal, sans modifier les samples.

Les entrées invalides sont rejetées avant mutation et sans changer l'état.
Un dépassement du calcul ou de l’état retourne `limit_exceeded`, sans écrêtage ni normalisation.
Dans ce cas un préfixe peut déjà être traité : appeler reset et reconstruire
le bloc original avant un nouvel essai. Pour écrire dans un flux ou créer un
son, choisir explicitement un niveau compris entre ±1, par exemple avec les
gains de l'égaliseur. La continuité entier/blocs est qualifiée à 10⁻⁶ absolu
pour les fixtures à niveau maîtrisé ; reset retire toute queue.

[Exemple : producteur indépendant filtré pendant la lecture](../ProcessedTone.sx).

[Bitcrusher : résolution, maintien, dosage et bypass](Bitcrusher.md).

[Saturer ou distordre un son](Distortion.md).

[Déplacer un son entre gauche et droite](StereoPan.md).
