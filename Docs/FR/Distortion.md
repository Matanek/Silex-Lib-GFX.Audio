# Saturer ou distordre un son

`Processing.Distortion` donne au signal une saturation douce ou un écrêtage
dur. `drive` pousse le signal dans la courbe ; `output_gain` règle ensuite
son niveau et `wet` dose le résultat avec l'entrée sèche. Il traite tous les
canaux indépendamment et rejoint une chaîne [Processed](Composition.md).

La [démonstration exécutable](../SaturatedSounds.sx) compare le même sinus sec,
une saturation douce avec drive 2 puis 8, et un écrêtage dur avec drive 8.
Elle applique ensuite une enveloppe et une atténuation explicites. Depuis
`SilexProject/`, lancer :

```sh
silex run Packages/GFX.Audio/Docs/SaturatedSounds.sx --release
```

Fragment pour un `format` et un buffer `samples` déjà préparés :

```sx
match Processing.Distortion.create(format, drive:4.0,
    mode:Processing.DistortionMode.soft, output_gain:0.5, wet:0.75) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Choisir la courbe et le niveau

Pour `z = drive * entrée`, le mode `soft` calcule `z / (1 + abs(z))` et
`hard` limite z à [-1, 1]. Les expressions float32 sont stabilisées pour
éviter un dépassement sur les grandes entrées finies, même avec drive 256.
Les deux courbes sont symétriques et zéro reste zéro. Le mode doux diminue
aussi le niveau des petits signaux ; il n'emploie pas de compensation implicite.
Le résultat traité vaut `output_gain * courbe(z)`, puis la sortie vaut
`(1 - wet) * entrée + wet * résultat_traité`.

Drive=0 supprime la partie traitée. Le gain de sortie peut faire dépasser ±1 :
choisir explicitement un niveau adapté avant `Audio.create` ou un flux. Un
mélange avec une entrée sèche au-delà de ±1 peut également dépasser ce domaine.
Wet=0 et bypass conservent exactement les samples secs ; wet=1 utilise
uniquement la sortie traitée. Les valeurs sèches finies au-delà de ±1 sont
acceptées. La saturation modifie les harmoniques et peut produire du repliement ;
aucun oversampling ni filtre anti-repliement n'est ajouté.

## Régler l'effet entre les blocs

| Réglage | Défaut | Domaine |
| --- | --- | --- |
| `drive`, `set_drive(drive)` | 2 | Float32 fini de 0 à 256 |
| `mode`, `set_mode(mode)` | soft | `DistortionMode.soft` ou `.hard` |
| `output_gain`, `set_output_gain(output_gain)` | 1 | Float32 fini de 0 à 16 |
| `wet`, `set_wet(wet)` | 1 | Float32 fini de 0 à 1 |
| `set_bypass(bypass)` | false | Booléen |

Les setters numériques retournent `Result<void, Error>` et conservent le
réglage si la valeur est refusée. Tous les changements sont immédiats au
prochain `process`, sans lissage : une transition douce se prépare dans
l'application. `reset()` conserve les réglages ; l'effet ne possède pas
d'historique audio, n'ajoute aucune frame de latence de traitement ni queue.
Les références à la même classe partagent ses réglages.

## Formats, erreurs et ressources

Les formats, frames entrelacées et vues suivent [Processing](Processing.md).
Un bloc vide ne produit rien. Non-finis et frames incomplètes retournent
`invalid_input`, opération `audio.process`, avant toute écriture, même avec
wet=0 ou bypass. La vue n'est pas conservée après l'appel.

Le calcul est linéaire en samples, sans historique ou tableau alloué pendant
`process`. Cela ne garantit pas une latence temps réel. Les
[oracles numériques](Validation.md) contrôlent les courbes, extrêmes, canaux,
découpages, changements, invalides et ordre avec un traitement du consommateur.
