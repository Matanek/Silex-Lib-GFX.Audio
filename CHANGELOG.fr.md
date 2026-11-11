# Historique

## [Unreleased]

- Calculer la réponse du pot de détente de `cross2` à partir de ses diamètres et longueurs. Le mono 250 2T d’`Engines.Library` utilise la pression simulée et cette réponse générée, sans enregistrement moteur. La propagation acoustique reste à une dimension et le balayage reste simplifié.

- Différencier les citadines de l’I4 de sportive : admission et calage plus sages, échappement plus restrictif et rendu extérieur feutré. Le diesel reçoit une voix hybride issue de huit excitations extraites de la référence TDI fournie, pilotées par le régime natif, avec extinction et reset déterministes. Le libellé signale cette source enregistrée et son modèle non identifié ; la simulation mécanique ne devient pas une combustion diesel. Le 454, les sportives et la cross 500 4T conservent leur parcours sonore.

- Corriger le décodage du régime natif lors des petits retours arrière du vilebrequin et arrondir les télémétries positives après conversion d’unité. L’atelier conserve le ralenti libre du banc : le ralenti nominal d’un profil n’engage plus automatiquement le dynamomètre.

- Ajouter `Engines.Vehicles` : référence Chevrolet 454 conservée échantillon par échantillon et 17 variantes préparées avec le simulateur thermique, ses définitions natives et ses réponses d’échappement. Cylindrée en cm³, adaptations mécaniques des monos, pédale continue optionnelle et définitions privées conservées au reset. Le binaire natif embarqué reste inchangé et qualifié sur macOS ARM64 ; diesel, turbo et 2T gardent les limites explicites du guide. EngineWorkshop utilise désormais cette chaîne, avec contrôle de parité du 454 ; le générateur par impulsions reste un prototype séparé.

- Ajouter `Synthesis.EngineVehicles.catalogue()` : 17 profils procéduraux de citadines essence/diesel, sportives, motocross 2T/4T, motos de course et customs, avec cylindrée, régime et réponse propres à chaque archétype. Les profils restent des inspirations sonores à qualifier par l’écoute.
- Enrichir le parcours `Engine.assemble` : attaque de combustion, allumage par compression et claquement, chicanes acoustiques, résonance de détente, sifflement mécanique et irrégularité de rotation. Valider les nouveaux réglages avant mutation ; conserver phases, rendu déterministe et stockage préparé. Réduire le niveau avant le limiteur du parcours par pièces pour préserver ses transitoires en charge ; son niveau de sortie change. `Engine.create` et la bibliothèque native `Engines` restent séparés.

## [0.5.0] - 2026-11-09

- Ajouter `Engines.Library.driven_engine` et `OperatingState` pour piloter régime et effort de combustion depuis le jeu. La chaîne thermique et acoustique conserve les phases de vilebrequin continues, borne les changements de régime et utilise le rendu FIFO existant. Les banques natives v3 exposent cette entrée ; les banques v1/v2 gardent leurs modes antérieurs.

- Ajouter `Engines.Gearing` pour régler rapports de boîte et pont à la création d’un moteur routier. Les rapports d’origine et actifs sont consultables, validés avant création et conservés au reset ; les réglages d’origine gardent leur PCM. Les nouvelles banques acceptent ces réglages ; les banques v1 conservent les valeurs par défaut.

- Exposer la transmission automatique ou manuelle optionnelle du banc validé par `Engines.Library.engine`, avec demandes de rapport, freinage et télémétrie routière synchronisée. Point mort, refus des surrégimes et réengagement sûr sont préservés ; le mode banc libre reste le défaut.

- Extraire la chaîne validée du banc moteur dans `GFX.Audio.Engines` : bibliothèque native distribuable, huit profils, réponses d’échappement d’origine, admission 4T mesurée et traitement de sortie. Génération synchrone et demandes asynchrones bornées ; le banc autonome reste l’oracle PCM et l’atelier par pièces reste expérimental. La banque native est actuellement qualifiée sur macOS ARM64, sans distribution complète sur les autres cibles.

- Corriger le rayonnement de pression des échappements par pièces et lisser les attaques des impulsions. Ajouter les niveaux d’écoute par sortie et conserver les contributions inégales des bancs du V8. Les tests distinguent les changements de timbre isolés du niveau du turbo.

- Ajouter `Synthesis.Engine.assemble` et les types `EngineParts` : bloc, cycle, allumage, culasse, admission, tuyaux, silencieux, mécanique et turbo optionnel. Régime, charge, carburant et suralimentation sont pilotés par le jeu ; mélange des branches et transitions de remplacement sont bornés. Consommateur indépendant, atelier et guides FR/EN ; le prototype `Engine.create` et le banc engine-sim autonome sont conservés.

- `Engines.Library.open()` fournit les huit moteurs standard sur macOS ARM64 sans dossier ni préparation supplémentaire. Le simulateur et ses ressources sont embarqués, gardés pendant la vie des moteurs et nettoyés à leur libération ; le chargement d’une bibliothèque personnalisée reste optionnel. Le PCM des huit profils est conservé échantillon par échantillon dans les scénarios de comparaison.

- Fournir des bibliothèques réutilisables de moteurs procéduraux, une transmission automatique ou manuelle optionnelle et des rapports de boîte configurables. Le jeu peut fournir le régime de vilebrequin et l’effort ; les modèles et limites restent ceux documentés.

- `capture_output()` observe le mix du périphérique en blocs PCM possédés et horodatés, avec file bornée, arrêt/vidange et débordement explicite sans arrêter la lecture sonore. Provider privé `silex.7` reproductible pour six cibles.

- `output_format()` expose la fréquence et les canaux du mix ; `render_f32le()` fournit le PCM hors ligne possédé pour les intégrations d’encodeurs, sans normalisation ni changement de chronologie.

- Ajoute `Synthesis.Engine`, prototype de moteur quatre temps commandé par
  régime, accélérateur, charge et frein moteur : profil V8 à deux échappements,
  1 à 12 cylindres, texture bruitée et coloration réglables, rampes continues,
  décharges de pression liées au régime et à l'effort, turbulence d'échappement, signatures et
  variations lentes par cylindre, alimentation progressive des nouvelles
  combustions préservant les événements engagés, PCM reproductible et
  exemple autonome, avec guides FR/EN.

- Adopte la déclaration `Result` unique : l’appel ordinaire rend la valeur
  ou arrête le programme sur erreur ; `try appel()` conserve le `Result`. Les
  anciens appels stockant un résultat et propagations deviennent explicites.
  Cette version requiert Silex 0.48.0 ou supérieur et les versions coordonnées
  de ses dépendances.
  Les variantes récupérables `try_*` et wrappers directs de même signature
  sont réunis sous le nom ordinaire. Les variantes booléennes, optionnelles ou
  natives gardent leur contrat.

- Ajoute `Music.Instruments.guitar`, `violin` et `drums` : cordes pincées à décroissance naturelle, violon tenu avec vibrato et kit de sept percussions `Music.Drum`. Polyphonie/commandes communes, réglages propres, exemples hors Docs, guides FR/EN et oracles numériques/ressources.

- Ajoute `Music.Instruments.piano` et `Synthesis.PianoInstrument` : piano procédural polyphonique, dynamique de frappe, déclin naturel, brillance et pédale. Partage le pool de commandes du sinus sans changer son PCM ; exemples piano/MIDI, guides FR/EN et preuves numériques.

- Ajoute les constantes musicales `Music.Key.C5`, `Cs5`, `Bb4` et les conversions `Music.key` / `Music.keys` depuis les noms de notes ; convention C4=60, altérations et erreurs récupérables documentées, PCM identique à la saisie MIDI numérique.

- Déplace les 21 exemples exécutables et leur partition MIDI dans `Examples/` ; aucun fichier `.sx` dans `Docs/`. Corrige les liens et commandes FR/EN sans modifier les sources sonores.

- Qualifie les coûts du parcours musical : préparation et lectures répétées, partition longue et alimentation possédée ; compteurs DSP séparés des allocations natives/offline, mesures ARM64 et x64/Rosetta, guides FR/EN et protocole reproductible.

- Ajoute `Music.Player` : timbre, instrument ou routage MIDI explicite ; alimentation PCM bornée possédée par Audio, contrôles pause/reprise/arrêt/replay, attente autonome, état et erreurs observables. Le plugin Audio conserve une ressource fournie et alimente les lectures sur le thread applicatif. Guide FR/EN et exemple interactif sans pompage consommateur.

- Distingue recette sonore et instrument dans `Music` : `prepare(audio, using:...)` accepte les deux, et `Music.Instruments.sine` crée l'instrument polyphonique existant avec des durées en secondes et une amplitude conservée au reset. Le nom de paramètre `instrument:` du candidat Music devient `using:`. Quatre variantes exécutables et contrôles de voix, gain, unités et erreurs.
- Ajoute `GFX.Audio.Music` : notes en temps et tempo, timbres rétro/triangle/sinus modifiables, préparation de sons courts avec buffers internes et lectures indépendantes ; instruments et effets utilisateur réutilisent les protocoles existants. Limites et exemples FR/EN qualifiés.

- Qualifie les ressources de la synthèse : compteur avec témoins en Debug/Release ARM64, événements MIDI compris ; charge stéréo 16/64 voix avec cinq effets mesurée séparément du transfert PCM, limites et marges documentées.

- Ajoute un guide de choix des recettes procédurales, du bip aux partitions MIDI, avec unités, contrôle des niveaux et contrats d’extension.

- Lissage MIDI optionnel du volume, de l’expression et de la balance, réglé en frames ; la mélodie utilise 5 ms pour éviter le craquement provoqué par une baisse d’expression sur des voix soutenues. Dates des notes conservées, cibles continues entre blocs et programmes.

- Commande MIDI 1.0 dans GFX.Audio : partitions SMF 0/1 PPQN bornées, tempo et fusion stable sans dérive d’arrondi, instruments choisis par canal/programme, identités FIFO, sustain/gain/balance/bend, fin et queues explicites ; rendu mémoire et flux sans banque ni décodeur MIDI système.

- Contrôles continus et rampes de gain/hauteur : changement de cible depuis le niveau courant, phase conservée et commandes en frames. Producteur de flux borné avec suffixe conservé lors des écritures partielles, compteurs distincts, fermeture à durée choisie et durée de vie explicite ; recettes moteur/accord sans relance de petits sons.

- Instruments polyphoniques sinusoïdaux : identités, vélocité, ADSR, sustain, bend et réattribution bornée avec raccord configurable. Partition de commandes sur l’horloge entière en frames, ordre stable, retards et capacités récupérables, instrument utilisateur composable et mélodie sans banque de sons.

- Compresseur et limiteur composables : seuil/ratio, attaque/relâchement, regain explicite, plafond de samples, crête liée entre canaux et comparaison des accents sans banque.

- Réverbération algorithmique composable : taille préparée, décroissance et amortissement réglables, dosage/bypass, historiques par canal, oracles d’échos/queue/couleur et notes pincées sans banque.

- Délai modulé composable pour chorus et flanger : interpolation causale, feedback signé, dosage/bypass avec historique continu, capacité préparée, oracles d’impulsion/ton et accord procédural sans banque.

- Panoramique stéréo par transfert sin/cos du canal opposé, centre neutre et pôles exacts ; dosage/bypass, dépassement récupérable et démonstration par blocs.

- Saturation douce et distorsion dure composables : drive, gain de sortie, dosage et bypass, calcul float32 stabilisé et exemples sans asset.

- Bitcrusher composable : résolution de 2 à 24 bits, maintien indépendant entre blocs, dosage et bypass ; grille signée de 256 niveaux à 8 bits, reset et recette rétro sans asset.

- Composition : mélange dosé, chaîne ordonnée de traitements extensibles, courbe linéaire, modulation d’amplitude et FM sinusoïdale avec contrôles mono, états persistants et tampons préparés.

- Synthèse : triangle, carré à rapport cyclique et dent de scie à harmoniques bornées sous Nyquist, ainsi qu’un bruit rose reproductible. Une palette exécutable compare les timbres ; un oracle spectral indépendant vérifie les formes et les bruits en Debug et Release.

- `GFX.Audio.Synthesis` ajoute un générateur extensible, un oscillateur sinus, un bruit blanc avec graine et une enveloppe ADSR. Rendu dans des vues préparées, état conservé entre blocs, paramètres récupérables et exemples sans banque de sons.

- Flux et groupes qualifiés ensemble : pauses indépendantes, fins stables et propriété des handles. La durée en secondes reste disponible pour les grandes durées en frames.

- Traitements de blocs à état : passe-bas, délai/écho, égalisation trois bandes et crête/RMS. Vues mutables sur le thread applicatif, réglages récupérables et remise à zéro explicite.

- Audio.offline et render produisent du PCM possédé par blocs, sans périphérique, normalisation ni écrêtage caché.

- Groupes de lecture : gains composés, pauses indépendantes, réaffectation et destruction sans perdre les réglages individuels.

- Format et durée explicite des sources, départ/navigation en frames et observation bornée des fins. Un déplacement efface les frames converties de l’ancienne position.

- Flux PCM bornés : alimentation par blocs copiés, saturation récupérable, pause/reprise, fermeture avec vidage du filtre, compteurs de consommation et d’abandon. Provider privé reconstruit pour les six cibles ; coordonnées 3D et inversion stéréo multicanal corrigées.

- `Audio.decode` charge des octets encodés possédés ; `try audio.load(...)` permet de traiter les erreurs sans arrêter le programme. Les handles sont protégés entre instances d’Audio.

- `Audio.create` crée un son réutilisable depuis des échantillons `float32`
  mono ou entrelacés, avec fréquence et nombre de canaux configurables. Le son
  possède sa copie et accepte les contrôles de lecture existants.
