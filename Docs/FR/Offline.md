# Rendre un mix en mémoire

`Audio.offline(sample_rate:48_000, channels:2)` retourne un `Result<Audio, Error>`
sans ouvrir de périphérique ni initialiser un pilote audio. Utiliser le même
Audio pour charger ou créer des sons, créer des groupes, jouer et modifier les
lectures, puis appeler `render(frames:1024)`.
[Exemple autonome](../../Examples/Offline.sx).

`render` retourne un `Result<float32[], Error>` contenant exactement le nombre
demandé de frames, entrelacées selon les canaux du format choisi. Toutes les
frames sont valides : les frames après la fin des sources sont du silence.
Une demande nulle retourne un tableau vide. Une demande négative, trop grande
pour le buffer natif de 2 147 483 647 octets ou dépassant le compteur de frames
est rejetée avant le rendu. Sur un Audio avec périphérique, l'erreur est `unsupported`.

Les tableaux possèdent leur stockage et restent utilisables après destruction
d'Audio. Le rendu n'applique ni normalisation ni écrêtage ; un mix peut dépasser
±1. Choisir explicitement l'atténuation avant de le donner à `create` ou `write`,
qui acceptent des entrées comprises entre ±1. La sortie audible conserve le
comportement de saturation de son provider ; ces deux parcours coïncident pour
les fixtures à niveau maîtrisé.

Les appels successifs reprennent l'état des lectures et des convertisseurs.
`rendered_frames()` compte les frames de sortie rendues, silence compris ;
il reste à zéro sur un Audio avec périphérique. Les positions de lecture et
les départs/navigation restent en frames du format source, distinct de cette
chronologie de sortie. Pour décaler une nouvelle source, rendre le préfixe
souhaité puis la jouer avant de rendre la suite. Même une répétition infinie
ne rend que les frames demandées. Les fins observées sont collectées après
chaque rendu. Les flux secs fournissent du silence et peuvent être réalimentés.

`wait` ne peut pas faire avancer un Audio hors ligne : il signale une erreur
si une lecture attend encore une progression. Rendre des blocs explicitement
jusqu'à la fin. Sur un flux plein, `wait_writable` retourne `resource_busy` tant
qu'un rendu est nécessaire. Aucun thread ni boucle Application n'est requis.
Le même propriétaire applicatif doit piloter ses opérations séquentiellement.

À format et commandes identiques, le rendu en un bloc ou plusieurs blocs
conserve le PCM dans une tolérance absolue de 10⁻⁶ sur les fixtures qualifiées
à niveau unitaire. Modifier les commandes entre blocs définit une autre
séquence ; les transitions spatiales peuvent dépendre de la taille d'un bloc.
