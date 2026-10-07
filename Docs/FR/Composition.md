# Composer et moduler un son

Combinez des sources avec `Synthesis.Mix`, puis appliquez des traitements dans
leur ordre avec `Synthesis.Processed`. Les deux implémentent `Generator` : une
composition se réutilise donc comme n’importe quelle source. Le programme
[ModulatedSounds.sx](../ModulatedSounds.sx) fait entendre ces combinaisons.

Un générateur écrit par votre application peut entrer dans le mélange ; un
`Processing.Processor` personnalisé peut entrer dans la chaîne. Aucun Interop
n’est nécessaire. Le consumer [Composition.sx](../../Tests/Consumer/Tests/Composition.sx)
illustre ces deux extensions avec état.

Ces primitives requièrent la toolchain locale intégrant la lecture des propriétés
de protocole et l’itération modifiable sur les champs, jusqu’à sa publication.

## Mélange et traitements

`Mix.create(sources, gains)` accepte de 1 à 32 générateurs de même format et
un gain signé par source, entre -16 et 16. La sortie est leur somme pondérée,
sans écrêtage ni normalisation : choisissez les niveaux pour garder la marge
nécessaire à la lecture. Même une source de gain zéro avance normalement.

`Processed.create(source, effects)` applique de 0 à 32 traitements de même
format, dans l’ordre fourni. Une chaîne vide transmet la source. Les traitements
sont appelés avec le bloc reçu ; un traitement utilisateur doit conserver son
état et son résultat indépendamment du découpage. Un délai garde sa queue :
continuez à rendre une source silencieuse pour l’entendre après une note.

## Amplitude, LFO et courbe

`AmplitudeModulation.create(source, modulation, offset:0.5, depth:0.5)` multiplie
chaque frame par `offset + depth * modulation`. Le contrôle est un générateur
mono à la fréquence de la source, avec des valeurs finies dans [-1, 1]. Le même
gain s’applique à tous les canaux. `abs(offset) + abs(depth)` doit être au plus
16. Avec les valeurs par défaut, un contrôle sinus donne un tremolo entre zéro
et un ; `offset:0, depth:1` donne une modulation en anneau signée.

Un `Oscillator` de quelques hertz sert directement de LFO. Pour une transition,
`Curve.create(format, start, end, duration_frames)` produit un segment linéaire
entre deux valeurs de [-1, 1]. La frame zéro vaut `start`, la frame
`duration_frames` vaut `end`, puis cette valeur est maintenue. Une durée nulle
produit immédiatement `end`. La durée maximale est 16 777 216 frames. La courbe
avance une fois par frame et duplique sa valeur sur ses canaux ; choisissez un
format mono pour l’utiliser comme contrôle.

## Fréquence

`FrequencyModulation.create(format, modulation, frequency_hz:440,
deviation_hz:100, amplitude:1, phase:0)` produit une sinusoïde dont la fréquence
instantanée vaut `frequency_hz + deviation_hz * modulation`. Le contrôle est
mono, de même fréquence d’échantillonnage et borné dans [-1, 1]. La déviation
est positive ou nulle et toute la plage doit rester dans [0, Nyquist[.
L’amplitude est dans [0, 1], la phase initiale dans [0, 1[.

La valeur de sortie utilise la phase courante, puis intègre la fréquence de la
frame pour la suivante. Cette convention permet une courbe de hauteur continue
et un vibrato sans remise à zéro de phase. Les paramètres sont fixés à la
construction ; la commande en direct relève des instruments.

La validation de la fréquence instantanée ne garantit pas que toutes les bandes
latérales restent sous Nyquist. Une modulation audio rapide, une forte déviation
ou un contrôle discontinu peut créer du repliement spectral, y compris en AM.
Cette première FM est sinusoïdale : elle ne module pas les formes discontinues
de la palette. La qualification comprend un régime de modulation musicale
suffisamment éloigné de Nyquist ; aucune garantie générale de suréchantillonnage
ou de suppression du repliement n’est annoncée.

## État, erreurs et ressources

Les compositions conservent les objets fournis. Une classe garde son identité
partagée ; réutiliser la même instance dans plusieurs branches avance ce même
état plusieurs fois. Construisez des instances fraîches dans chaque recette
pour obtenir des voix indépendantes. Les listes sont conservées par valeur ;
modifier ensuite une liste d’entrée ne reconfigure pas la composition.

`reset()` remet à zéro toutes les sources, contrôles et traitements contenus.
Pour l’ADSR, cela revient à l’état inactif ; déclenchez ensuite `note_on()` pour
une nouvelle note. Une vue vide ne consomme aucun état. Une vue contenant une
frame incomplète est refusée avant tout rendu.

Les valeurs non finies, contrôles hors plage et dépassements float32 échouent
avec une erreur récupérable. Un générateur ou traitement peut avoir avancé avant
l’erreur et le bloc peut être partiellement écrit : remettez l’ensemble à zéro
et reconstruisez le bloc avant de réessayer. La composition ne transforme pas
une erreur d’un composant en succès.

Mix et les modulations préparent leurs tampons à la construction et traitent les
blocs de toute longueur par tranches internes d’au plus 512 frames. La chaîne
traite directement la vue reçue. Le rendu ne crée explicitement aucun tableau,
ne lit aucun fichier et n’attend aucun périphérique. Cela ne promet pas encore
une latence temps réel : les coûts du runtime et la charge seront mesurés lors
de la qualification finale. Les extensions utilisateur restent responsables de
leurs propres coûts, erreurs et garanties de blocs.
