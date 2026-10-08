# Contrôler des groupes de lectures

Créer des catégories avec `audio.group(volume:0.5)` puis passer `group` dans
`Audio.Playback`. `set_volume`, `pause`, `resume` et `stop` acceptent un groupe
comme une lecture. [Exemple complet](../../Examples/Groups.sx).

Le gain audible est le produit du gain individuel, du groupe et du gain général.
Changer un gain de groupe conserve les réglages individuels. Toute nouvelle
lecture hérite immédiatement de son gain et de sa pause courants. Les commandes
de groupe parcourent les lectures présentes seulement lors de la commande ;
aucun calcul supplémentaire n'est ajouté au rendu de chaque frame.

Une pause individuelle et une pause de groupe sont deux raisons indépendantes.
`resume(group)` ne réveille pas une lecture individuellement en pause ;
`resume(playing)` ne réveille pas une lecture appartenant à un groupe en pause.
Les commandes ne redémarrent jamais une lecture terminée.

`assign_group(playing, group)` retourne un `Result<void, Error>`. Passer `null`
retire le groupe. Le changement conserve le gain individuel et la pause
individuelle, applique le nouveau gain et retire l'ancienne raison de pause.
Les handles invalides, périmés ou provenant d'un autre Audio sont rejetés.

`destroy_group(group)` retourne `false` pour un handle invalide. Les membres
survivants sont détachés : leur gain individuel reste actif et seule la pause
du groupe disparaît. `contains(group)` vérifie son appartenance et sa génération.
`Group.is_valid()` indique seulement une identité non vide, pas sa validité actuelle.

`stop(group, fade_out_seconds:0.0)` arrête les membres présents et conserve les
réglages du groupe pour les lectures futures. Les fins observées avec
`watch_end` gardent les raisons de [chronologie](Timeline.md).
Les groupes n'ont pas de hiérarchie. Les flux PCM utilisent les mêmes commandes.
