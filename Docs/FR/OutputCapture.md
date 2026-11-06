# Observer le mix pendant sa lecture

`audio.capture_output()` ouvre une observation du mix final de cette instance
Audio, pendant sa lecture sur le périphérique. Elle respecte le gain et les
traitements déjà appliqués au mix. Elle ne remplace pas la lecture et ne capture
ni microphone, ni haut-parleurs, ni son du système ou d’une autre application.

Le parcours consommateur est dans
[OutputCapture.sx](../../Tests/Consumer/Smokes/OutputCapture.sx).
Après création d’un `Audio`, appeler `capture_output(capacity_frames:96_000)` puis
`read_f32le(max_frames:4096)` sur le `OutputCapture` obtenu. Les deux opérations
renvoient un `Result` avec les erreurs STD ordinaires. `Audio.offline` utilise
`render`/`render_f32le` ; sa capture de périphérique est refusée.

## Blocs et chronologie

Chaque `CaptureBlock` possède ses octets : la lecture suivante ne les modifie
pas. `bytes` contient du float32 IEEE entrelacé, petit-boutiste ; `frames` compte
les groupes de canaux, et non les valeurs flottantes individuelles.
`output_format()` donne la fréquence et le nombre de canaux. Le mix est copié
tel quel, sans nouvelle normalisation ou conversion de canaux.

`first_frame` place le début du bloc dans la chronologie de la capture. Le délai
jusqu’au premier bloc est exprimé en frames par un plancher cumulé ; les blocs
suivants avancent par leur nombre entier de frames. Cette origine ne représente
pas l’instant de sortie physique d’un haut-parleur. Une lecture peut renvoyer
un bloc vide : elle n’attend jamais de nouvelles données.

Les temps `elapsed_seconds` et `first_frame_seconds` des statistiques sont en
double précision. L’horloge monotone de la période et le compteur de samples sont
distincts : un périphérique ou pilote qui ne progresse pas à sa fréquence annoncée
ne devient pas une preuve de synchronisation avec les images. Le compteur de
samples avance par blocs ; ce n’est pas une horloge vidéo interpolée.

## Ressources et concurrence

La capture possède un tampon de `capacity_frames`, alloué et touché avant son
branchement. Le défaut est 96 000 frames, soit 768 000 octets de PCM stéréo et
deux secondes à 48 kHz. Les blocs retournés et les sons de l’application s’ajoutent.
Une seule capture peut être active par mixeur ; une seconde demande est refusée
avec `resource_busy`. Les mixeurs indépendants gardent leurs captures indépendantes.

Un seul consommateur peut appeler `read_f32le`. Il peut travailler sur un worker
pendant que l’application commande la lecture sonore. L’observateur natif copie
les samples et publie des compteurs atomiques ; aucun code Silex, encodage, fichier,
allocation ou attente n’est exécuté par cet observateur sur le thread audio.
Les coûts du mixeur lui-même restent ceux du mixeur. L’inactivité de la capture
ne crée aucun tampon ni travail d’observation supplémentaire.

`statistics()` expose capacité, file, pic, frames produites/lues/abandonnées,
plus grand bloc, temps et états. Les instantanés de file sont observationnels,
pas une réservation ; la lecture décide elle-même du nombre effectivement obtenu.
Les compteurs de file restent bornés. Si un bloc ne tient pas, la capture passe
en échec sans bloquer la lecture sonore. L’erreur est persistante : la lecture
renvoie `resource_exhausted`, et aucune discontinuité n’est présentée comme un flux
complet. Un changement de format ou l’épuisement des compteurs est aussi signalé.

`stop()` détache l’observation et fige la durée ; les blocs déjà capturés peuvent
encore être lus. Il est idempotent et ne stoppe aucun son. L’arrêt synchronise le
retrait avec le mixeur : l’appeler sur le propriétaire ou un worker, jamais depuis
son propre callback audio. Détruire un ancien handle arrêté ne détache pas une
nouvelle capture. Le handle conserve Audio jusqu’à sa destruction, même après
`stop`, afin de préserver le mixeur pendant la vidange et le nettoyage.

## Limites de cette primitive

Elle ne crée pas de vidéo ni de fichier et ne choisit pas la politique d’une
application lorsque le lecteur est trop lent. L’encodeur ou la capture vidéo doit
traiter l’échec, les éventuels silences de bord et la relation de ses horloges.
La capacité n’est pas une promesse universelle de cadence ou de coût nul.
Les tests de lecture factice qualifient la fonction ; la synchronisation temporelle
se qualifie séparément sur un périphérique réel et sur les artefacts décodés.
