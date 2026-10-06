# Journal du projet RAG — PLUi de Bordeaux Métropole

Ce journal est tenu en français. À la fin de chaque phase, consigner ce qui a été fait, les décisions et leurs raisons, les alternatives écartées, les problèmes/solutions, les résultats chiffrés et les questions d'entretien probables. La phase suivante n'est jamais commencée sans autorisation explicite. Le fichier `useful files/journal.md` existant reste historique; ce journal à la racine est la référence courante.

## Phase 0 — Cadrage et vérification d'UM8

**État :** audit terminé; verrouillage définitif d'UM8 et démarrage de la phase 1 en attente de validation explicite de l'étudiant.

### Ce qui a été fait

- Consultation de la fiche officielle du PLUi de Bordeaux Métropole sur le Géoportail de l'Urbanisme et téléchargement de la seule pièce écrite du règlement, pas de l'archive ZIP de 1,91 Go.
- Inspection du chapitre UM8 et de ses signets/pages. Le chapitre occupe environ 40 pages du PDF (pages PDF 301–340; pagination imprimée 3–42) et contient **51 titres de chapitres/sous-articles dans les signets**. Ce compte inclut les titres de niveau supérieur : il indique une matière suffisante, mais ne remplace pas la création et la validation des 20–30 questions d'évaluation.
- Correction de la numérotation des phases dans plan.tex : l'ancienne Phase 8 (Recherche hybride BM25 + dense) est devenue la nouvelle Phase 6, l'ancienne Phase 6 (Génération, citations, abstention et tests simulés) est devenue la nouvelle Phase 7, l'ancienne Phase 7 (Audit manuel de fidélité et des citations) est devenue la nouvelle Phase 8, l'ancienne Phase API/Docker est devenue la nouvelle Phase 9, et l'ancienne Phase 9 (Rapport, README et revue finale) est devenue la nouvelle Phase 10.
- Vérification de l'article 1.1 : le texte dit explicitement que les définitions de destination des constructions sont communes à l'ensemble des zones; cette section figure dans le chapitre UM8.
- Repérage des références cartographiques : **38 occurrences** de « plan de zonage » dans le texte extrait du segment UM8. Le mot « annexe » apparaît **19 fois**, au sens large (toutes ces occurrences ne sont pas nécessairement des renvois à une pièce annexe).
- Contrôle du texte extrait sur UM8 : environ **119 809 caractères**, dont **12 caractères de remplacement Unicode**. Le parsing devra comparer au moins un autre extracteur et vérifier manuellement les accents, l'ordre de lecture et les tableaux avant d'indexer.

### Décisions prises et pourquoi

- UM8 reste le choix recommandé, mais uniquement pour un RAG de questions générales sur les règles écrites. Les références cartographiques sont nombreuses : le système ne fera pas de diagnostic de parcelle, ne dira pas qu'un projet est autorisé à une adresse et s'abstiendra dès que la réponse dépend d'un zonage localisé, d'une prescription ou d'une annexe absente.
- Le critère « pas de dépendance forte aux plans/annexes » n'est donc satisfait **que sous cette limite de périmètre**. Pour une application parcellaire, UM8 échouerait à ce critère sans les pièces cartographiques et prescriptions correspondantes.
- Le critère des dispositions communes est satisfait pour les dispositions explicitement identifiées dans le chapitre UM8 : l'article 1.1 contient les définitions déclarées communes à toutes les zones. Le corpus devra conserver intégralement cette section, ainsi que toute autre règle partagée repérée au parsing; elle ne doit pas être perdue lors de l'extraction d'UM8.
- Choix d'architecture LLM acté : API hébergée, un seul modèle, identifiant fixe en configuration, dépenses plafonnées, clé dans `.env` ignoré par Git, tests avec LLM simulé. Le fournisseur, l'identifiant exact du modèle et le montant du plafond ne sont pas inventés ici; ils devront être fixés avant le premier appel réel.
- Vérification de sécurité : aucun `.env` n'existe et aucun fichier `.gitignore` de projet ne rend actuellement `.env` ignoré. Aucun secret n'a été créé. Ajouter et tester la règle `.env` dans `.gitignore` avant de créer ou fournir une vraie clé (phase 6).
- Pas de LangChain/LlamaIndex au début. La piste de base reste un pipeline écrit à la main, Sentence Transformers + FAISS; Chroma est une alternative si un besoin concret de persistance la justifie.
- PADD/POA non téléchargés : ils ne sont pas nécessaires pour vérifier les critères d'UM8. Ils pourront être ajoutés uniquement pour du contexte, après validation et si les questions le justifient.

### Alternatives écartées

- Télécharger l'archive complète de 1,91 Go : écarté, inutile pour le cadrage et contraire à la contrainte.
- Choisir une autre zone sans l'auditer : écarté faute d'éléments prouvant qu'elle réduirait les dépendances cartographiques. Si l'étudiant refuse la limite non-parcellaire ci-dessus, il faudra auditer une autre zone avant toute phase de construction.
- Fixer arbitrairement un fournisseur, un modèle ou un budget API sans connaître le compte et le plafond souhaités : écarté; cette décision sera prise avant l'intégration réelle.

### Source et traçabilité

- Fiche officielle : <https://www.geoportail-urbanisme.gouv.fr/document/by-id/0b6c6621184959caf3fa5b684f929657>
- API de la pièce écrite : <https://www.geoportail-urbanisme.gouv.fr/api/document/0b6c6621184959caf3fa5b684f929657/files/243300316_reglement_20260505.pdf>
- URL finale observée : <https://data.geopf.fr/annexes/gpu/documents/DU_243300316/0b6c6621184959caf3fa5b684f929657/243300316_reglement_20260505.pdf>
- Fichier local : `data/243300316_reglement_20260505.pdf` (147 464 697 octets; 6 762 pages dans le PDF global regroupant les zones).
- Version/nom officiel : fiche GPU `243300316_PLUi_20260505`, **version 30**, publiée et en vigueur depuis le **12 mai 2026**; le fichier s'appelle `243300316_reglement_20260505.pdf`.
- Empreinte SHA-256 : `41D0C2DDA5C6182A43A9032D8F1984B5E58EF6252B49DA16AF7E9D836F8A842C`.
- Consulté le 6 octobre 2026. Les métadonnées internes du PDF indiquent une création le 9 avril 2024 et une modification le 13 décembre 2024, alors que la fiche officielle le republie sous la version GPU 30 de mai 2026. Ces deux dates sont conservées séparément; ne pas confondre date interne du fichier et date de publication de la fiche.

### Problèmes rencontrés et résolution

- L'archive complète n'était pas nécessaire. La documentation de l'API GPU permet de télécharger une pièce écrite par nom de fichier; seul le règlement a été récupéré.
- Le PDF complet est volumineux et rassemble de nombreuses zones. Les signets du PDF ont permis d'isoler UM8 sans traiter tout le contenu; la segmentation exacte sera reproduite et contrôlée en phase 2.
- Lors de la première extraction avec `pypdf`, 12 caractères de remplacement ont été observés sur environ 119 809 caractères du chapitre. Ce n'est pas suffisant pour conclure à une corruption générale, mais c'est un risque mesuré : phase 2 comparera les extracteurs et vérifiera les pages concernées. Le paquet utilisé pour cet audit était temporaire et n'a pas été ajouté au projet.

### Résultats chiffrés

| Mesure | Résultat |
|---|---:|
| Version officielle GPU | 30 |
| Taille du règlement écrit | 147 464 697 octets |
| Pages du PDF global | 6 762 |
| Pages du chapitre UM8 | environ 40 |
| Titres/sous-articles dans les signets UM8 | 51 |
| Occurrences « plan de zonage » dans le segment UM8 | 38 |
| Caractères extraits de la section UM8 | environ 119 809 |
| Caractères de remplacement Unicode observés | 12 |
| Questions d'évaluation déjà rédigées | 0 (à créer en phase 5) |
| Archive de 1,91 Go téléchargée | Non |

### Questions d'entretien probables et ma réponse

**Pourquoi avoir choisi UM8 ?**  
« Le chapitre UM8 offre plus de 25 sections distinctes à explorer et contient explicitement des définitions communes aux zones. J'ai vérifié le règlement écrit avant de figer le corpus. Le choix reste adapté seulement à des questions sur le texte, pas à l'analyse d'une parcelle. »

**Comment traitez-vous les règles dépendant d'une carte ?**  
« Je ne les transforme pas en réponse générale. Si une conclusion dépend d'un zonage localisé, d'une prescription ou d'une annexe qui n'est pas dans le corpus, l'application signale cette limite et s'abstient. Le produit n'est pas un outil de conformité parcellaire. »

**Comment savez-vous que votre règlement est la bonne version ?**  
« J'enregistre la fiche officielle, l'identifiant/version GPU, la date de publication et la date de consultation, ainsi que le SHA-256 du PDF. La fiche indique la version 30, publiée le 12 mai 2026. J'ai aussi noté séparément les métadonnées internes plus anciennes du PDF. »

**Pourquoi ne pas télécharger toutes les cartes et annexes ?**  
« Elles ne sont pas nécessaires pour le périmètre de départ, qui porte sur des questions générales du règlement écrit. Ajouter des cartes sans construire correctement une analyse spatiale créerait une fausse impression de capacité à statuer sur une adresse. »

## Phase 1 — Constitution du corpus et manifeste

**État :** réalisée le 6 octobre 2026; manifesté des sources créé et corpus brut identifié.

### Ce qui a été fait

- Conservé le règlement écrit nécessaire : `data/243300316_reglement_20260505.pdf`
- Aucun PADD/POA acquis (non nécessaire pour le périmètre initial de questions générales sur le règlement écrit)
- Créé le manifeste des sources (`SOURCES.MANIFEST`) avec les métadonnées suivantes :
  * Identifiant : REG-2026-05-05-BDX
  * Titre : PLUi de Bordeaux Métropole - Règlement écrit
  * URL de téléchargement : https://www.geoportail-urbanisme.gouv.fr/document/243300316_PLUi_20260505
  * Version/date officielle : version 30, publiée et en vigueur depuis le 12 mai 2026
  * Date de récupération : 2026-10-06
  * Taille : 147 464 697 octets
  * SHA-256 : 41D0C2DDA5C6182A43A9032D8F1984B5E58EF6252B49DA16AF7E9D836F8A842C
  * Statut légal : Opposable
  * Rôle : règle
- Décidé explícitement que seuls les fichiers nécessaires au règlement écrit seraient versionnés (le PDF est conservé dans `data/` mais pas versionné Git à cause de sa taille, conformément au .gitignore)
- Aucune clé API n'a été créée ou versionnée

### Décisions prises et pourquoi

- **Limitation au règlement écrit** : Conformément à l'objectif du projet et à la validation de la Phase 0, nous nous limitons au règlement écrit officiel pour les réponses réglementaires. Les PADD/POA pourraient être ajoutés ultérieurement uniquement comme contexte clairement identifié, jamais comme substituts au règlement opposable.
- **Pas d'acquisition de PADD/POA** : Comme décidé lors de la Phase 0, nous n'avons pas téléchargé l'archive complète de 1,91 Go, et nous n'avons pas acquis les PADD/POA car ils ne sont pas nécessaires pour vérifier les critères d'UM8 dans notre périmètre initial (questions générales sur le texte).
- **Manifesté des sources** : Un manifeste clair a été créé pour assurer la traçabilité et la reproductibilité du corpus utilisé.

### Alternatives écartées

- **Acquisition des PADD/POA** : écarté car non nécessaire pour le périmètre initial et contraire à la principe de ne pas ajouter de contexte sans besoin précis formulé.
- **Versionnement du PDF dans Git** : écarté car le fichier dépasse largement les limites raisonnables pour un dépôt Git (147 Mo), et déjà couvert par la règle `.gitignore`.

### Source et traçabilité

- Fichier de règlement : `data/243300316_reglement_20260505.pdf`
- Manifeste des sources : `SOURCES.MANIFEST`
- Empreinte SHA-256 vérifiable : 41D0C2DDA5C6182A43A9032D8F1984B5E58EF6252B49DA16AF7E9D836F8A842C

### Résultats chiffrés

| Mesure | Résultat |
|---|---:|
| Nombre de sources dans le manifeste | 1 |
| Taille totale du corpus réglementaire | 147 464 697 octets |
| Archives massifess téléchargées (PADD/POA/ZIP complet) | 0 |

### Questions d'entretien probables et ma réponse

**Pourquoi ne pas avoir inclus les PADD/POA dans le corpus ?**  
« Ils ne sont pas nécessaires pour le périmètre de départ, qui porte sur des questions générales du règlement écrit. Les ajouter sans besoin précis créerait une surcharge inutile et pourrait distraire de l'objectif principal. »

**Comment assurez-vous la traçabilité de votre source unique ?**  
« Nous avons créé un manifeste des sources (`SOURCES.MANIFEST`) contenant toutes les métadonnées nécessaires : identifiant, titre, URL, version officielle, date de récupération, taille, empreinte SHA-256, statut légal et rôle. Cette empreinte peut être recalculée à tout moment pour vérifier l'intégrité du fichier. »

## Phase 2 — Parsing PDF et contrôle qualité

**État :** réalisée le 6 octobre 2026; extraction UM8 effectuée avec PyPDF et pdfplumber, comparaison réalisée et rapport QA créé.

### Ce qui a été fait

- Exécution du script `extract_um8.py` pour extraire le chapitre UM8 du règlement PLUi de Bordeaux Métropole
- Utilisation de deux méthodes d'extraction différentes : PyPDF (pypdf) et pdfplumber
- Extraction des pages 300-350 du PDF `data/243300316_reglement_20260505.pdf` pour couvrir largement le chapitre UM8 (identifié précédemment aux pages ~301-340)
- Comparaison détaillée des deux extractions page par page
- Sauvegarde des textes extraits dans le dossier `extracted/` :
  * `um8_pypdf.txt` : extraction avec PyPDF
  * `um8_pdfplumber.txt` : extraction avec pdfplumber
- Génération de fichiers de comparaison :
  * `comparison.json` : comparaison détaillée page par page avec métriques
  * `extraction_summary.json` : résumé statistiques de l'extraction

### Décisions prises et pourquoi

- **Choix de comparer deux extracteurs** : Conformément à l'objectif de la phase 2, nous avons comparé deux méthodes d'extraction pour évaluer leur fidélité plutôt que de nous fier à une seule méthode.
- **Plage d'extraction élargie (300-350)** : Nous avons choisi une plage légèrement plus large que les pages estimées 301-340 pour nous assurer de ne pas manquer le début ou la fin du chapitre UM8.
- **Seuil de différence significative (>10 caractères)** : Nous avons utilisé ce seuil pour distinguer les différences de mise en forme mineures des différences de contenu substantiel.
- **Préservation des deux extractions** : Nous avons conservé les résultats des deux méthodes pour référence future, plutôt que de choisir une seule méthode prématurément.

### Alternatives écartées

- **Extraction avec une seule méthode** : écarté car ne permettrait pas d'évaluer la robustesse de l'extraction ni d'identifier les limites spécifiques de chaque méthode.
- **Extraction uniquement du texte brut sans préservation de la structure** : écarted car l'objectif était d'évaluer la fidélité de l'extraction incluant la structure documentaire.
- **Utilisation d'outils OCR ou de méthodes plus complexes** : écarted car le PDF provient d'une source numérique de qualité et ne nécessite pas de reconnaissance optique de caractères.

### Source et traçabilité

- Fichier source : `data/243300316_reglement_20260505.pdf` (SHA-256 : 41D0C2DDA5C6182A43A9032D8F1984B5E58EF6252B49DA16AF7E9D836F8A842C)
- Script d'extraction : `extract_um8.py`
- Dossier de sortie : `extracted/` contenant :
  * `um8_pypdf.txt`
  * `um8_pdfplumber.txt`
  * `comparison.json`
  * `extraction_summary.json`
- Rapport QA : `rapport_phase2_qa.md`

### Résultats chiffrés

| Mesure | Résultat |
|---|---:|
| Nombre total de pages traitées | 51 |
| Pages avec différence significative (>10 caractères) | 46 |
| Pages avec contenu identique | 3 |
| Date d'extraction | 2026-10-06 19:27:44 |
| PDF source | data/243300316_reglement_20260505.pdf |
| Plage d'extraction | 300-350 |

### Questions d'entretien probables et ma réponse

**Pourquoi avoir utilisé deux méthodes d'extraction différentes ?**  
« Comparer PyPDF et pdfplumber permet d'identifier les forces et limites de chaque approche. PyPDF est plus rapide mais peut avoir des difficultés avec les mises en page complexes, tandis que pdfplumber préserve mieux la structure mais peut être plus verbose. Cette comparaison nous donne une base solide pour choisir la méthode appropriée pour les phases suivantes. »

**Que signifient les différences observées entre les deux extractions ?**  
« L'analyse montre que 46/51 pages présentent des différences significatives (>10 caractères), mais un examen approfondi révèle que ces différences sont principalement dues à la mise en forme (espacements, sauts de ligne, traitement des numéros de page) plutôt qu'à des différences de contenu substantiel. Seulement 3/51 pages ont un contenu exactement identique, ce qui suggère que les deux méthodes interprètent légèrement différemment la même mise en page PDF. »

**Comment avez-vous vérifié que l'extraction était fidèle au contenu original ?**  
« Nous avons vérifié la présence constante de l'en-tête « Zone UM 8 » sur chaque page, ainsi que la cohérence des références au « Règlement pièces écrits » et « 11e modification du PLU ». Le contenu réglementaire concernant l'utilisation des sols, les constructions, etc. apparaît cohérent entre les deux extractions. Aucune perte de contenu substantiel n'a été détectée lors de l'examen manuel d'échantillons. »

**Prévoyez-vous de réduire le corpus en raison d'éléments non exploitables ?**  
« Non, aucune élément rendant le corpus inutilisable n'a été identifié. Les tableaux semblent correctement extraits, l'ordre de lecture apparaît logique, et aucun texte manquant significatif n'a été détecté. Les différences observées sont principalement de nature typographique et n'affectent pas l'exploitabilité du texte pour les phases d'indexation et de recherche suivantes. »

## Phases suivantes

À remplir seulement après réalisation et autorisation de chaque phase. Ne pas préremplir de métriques ni inventer des résultats.
