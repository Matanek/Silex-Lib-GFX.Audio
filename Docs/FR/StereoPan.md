# Déplacer un son entre gauche et droite

`Processing.StereoPan` place les deux canaux d'un signal stéréo. Au centre,
il conserve gauche et droite. À l'extrême gauche, il additionne les deux
canaux à gauche et émet zéro à droite ; à l'extrême droite, il fait l'inverse.
Il transfère donc le canal opposé, au lieu de simplement le rendre silencieux.

La [démonstration](../StereoSounds.sx) joue gauche, centre, droite, puis un
déplacement par blocs préparés. Le générateur y fournit la même sinusoïde dans
les deux canaux, suivie d'une enveloppe et d'une atténuation explicites. Depuis
`SilexProject/` :

```sh
silex run Packages/GFX.Audio/Docs/StereoSounds.sx --release
```

Fragment pour un `format` stéréo et un buffer `samples` préparés :

```sx
match Processing.StereoPan.create(format, pan:-0.5, wet:1.0) {
    failure(error) => { panic(error.detail) }
    success(var effect) => {
        match effect.process(&samples[0:samples.count()]) {
            failure(error) => { panic(error.detail) }; success => {}
        }
    }
}
```

## Prévoir les niveaux et les canaux

Pan va de −1 (gauche) à +1 (droite), avec 0 au centre. Pour un pan négatif,
`angle = abs(pan) * pi/2`, `L' = L + sin(angle)*R` et `R' = cos(angle)*R`.
Pour un pan positif, `L' = cos(angle)*L` et `R' = R + sin(angle)*L`.
Les pôles et le centre utilisent des coefficients exacts.

| Pan avec wet=1 | Gauche | Droite |
| --- | --- | --- |
| −1 | L + R | 0 |
| −0,5 | L + 0,7071 R | 0,7071 R |
| 0 | L | R |
| +0,5 | 0,7071 L | R + 0,7071 L |
| +1 | 0 | R + L |

Le canal transféré suit une loi sin/cos. Le mix complet n'a pas une puissance
constante : deux canaux corrélés s'ajoutent, et deux canaux en opposition de
phase peuvent s'annuler au pôle. Deux valeurs de 0,75 donnent 1,5 au côté choisi.
Aucune normalisation ni limitation implicite ne masque cette somme ; choisir
le gain avant `Audio.create` ou l'écriture dans un flux. Ce traitement conserve
un format stéréo ; il ne convertit pas une source mono en stéréo.

Wet dose `(1 - wet) * sec + wet * panoramique`. Les coefficients combinés
sont préparés lors des réglages. Wet=0 et bypass conservent exactement le sec ;
le centre conserve également les samples. Le nombre de frames et la fréquence
de sortie restent inchangés.

## Régler le placement entre les blocs

`create(format, pan:0.0, wet:1.0)` exige deux canaux et une fréquence conforme à
[Processing.Format](Processing.md). `set_pan(pan)` accepte un float32 fini de
−1 à +1 ; `set_wet(wet)` accepte un float32 fini de 0 à 1. Ils retournent
`Result<void, Error>` et conservent les réglages en cas de refus.
`set_bypass(bypass)` reçoit un booléen, false à la création.

Les réglages prennent effet au prochain `process`, sans lissage. Pour préparer
un déplacement, choisir les positions et les frontières de blocs en frames,
comme l'exemple ; cela ne fournit pas encore un moteur d'automation.
`reset()` conserve les réglages : aucun historique audio, aucune frame de
latence de traitement ni queue. Les références de classe partagent les réglages.

## Traiter les erreurs et connaître les ressources

Les vues doivent contenir des frames stéréo complètes et des valeurs finies.
Un bloc vide ne fait rien. Une entrée invalide retourne `invalid_input`,
opération `audio.process`, avant écriture, même au centre ou sous bypass.

Si la somme dépasse la plage float32 finie, `limit_exceeded` conserve la frame
fautive intacte ; un préfixe peut déjà être traité. Reconstruire le bloc original
avant une reprise. Les valeurs finies hors de ±1 sont acceptées, ce qui ne
signifie pas qu'elles sont utilisables telles quelles pour la sortie audible.

Les coefficients trigonométriques sont calculés à la création et aux réglages.
`process` effectue un travail linéaire sans nouvelle allocation, historique ou
trigonométrie par sample. Cela ne garantit pas une latence temps réel. La vue
n'est pas conservée. [Les oracles](Validation.md) vérifient bases, loi, niveaux,
découpage, composition, reset, invalides et dépassement partiel.
