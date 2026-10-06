# RAPPORT PHASE 0 V2 - PROJET RAG PLUi BORDEAUX METROPOLE

## 1. Contenu final de CLAUDE.md
Le fichier CLAUDE.md doit renvoyer à plan.tex comme référence unique, sans liste de phases intégrée.

Contenu actuel de CLAUDE.md (`C:\Users\annem\Desktop\T.T.L.T.F.I\RAG project\CLAUDE.md`):
```
# RAG Project - Work Rules

## Core Principles
- **One phase at a time**: Announce the current phase and wait for explicit authorization before proceeding to the next phase
- **Documentation update**: At the end of each phase, update both `plan.tex` and `journal.md` with decisions, alternatives, problems/solutions, numerical results, and interview questions
- **Evaluation-first**: Define expected answers before comparing systems; never optimize on the final test set
- **Separate concerns**: Distinguish retrieval quality, generation fidelity, and citation accuracy; no single metric proves legal compliance
- **Honest reporting**: Report failures, null gains, and uncertainties related to the 20-30 question evaluation set

## Technical Requirements
- **Manual pipeline**: Python implementation without LangChain or LlamaIndex initially
- **Retrieval**: Sentence Transformers + FAISS as baseline; Chroma as alternative if justified by concrete persistence/metadata needs
- **Generation**: Single fixed-model hosted API with spending limits and token constraints; API key in `.env` (ignored by Git)
- **Testing**: Deterministic mock LLM client; unit tests make zero network calls and consume no budget
- **Citations**: Code resolves chunk identifiers to real sources/pages; LLM never fabricates links or references
- **Security**: No secrets in Git; API key stored in `.env` which must be ignored by Git before any real key is created

## Reference Document
- **plan.tex** is the unique reference for project planning and phase definitions. All phase descriptions, durations, deliverables, and success criteria are defined there.
- **journal.md** is updated at the end of each completed phase with execution details.
```

## 2. Ordre des phases actuel de plan.tex, jeu de développement ajouté, temps de l'audit de fidélité, résultat de la compilation LaTeX

### Ordre des phases actuel (extrait de plan.tex):
D'après la section "Temps estimé" de plan.tex:
- Phase 0: 1,0 h
- Phase 1: 1,5 h
- Phase 2: 4,0 h
- Phase 3: 2,0 h
- Phase 4: 2,5 h
- Phase 5: 3,5 h (augmentée de 0,5 h pour le jeu de développement)
- Phase 6: 1,5 h (Recherche hybride BM25 + dense)
- Phase 7: 3,0 h (Génération, citations, abstention et tests simulés)
- Phase 8: 2,25 h (Audit manuel de fidélité et des citations)
- Phase 9: 2,0 h (Livraison FastAPI)
- Phase 10: 1,5 h (Rapport, README et revue finale)
- **Cœur du projet: 24,75 h**

### Correspondance ancien/nouveau numéro de phase (notée dans journal.md):
- Ancienne Phase 0 → Nouvelle Phase 0
- Ancienne Phase 1 → Nouvelle Phase 1
- Ancienne Phase 2 → Nouvelle Phase 2
- Ancienne Phase 3 → Nouvelle Phase 3
- Ancienne Phase 4 → Nouvelle Phase 4
- Ancienne Phase 5 → Nouvelle Phase 5
- Ancienne Phase 8 → Nouvelle Phase 6 (Recherche hybride BM25 + dense)
- Ancienne Phase 6 → Nouvelle Phase 7 (Génération, citations, abstention et tests simulés)
- Ancienne Phase 7 → Nouvelle Phase 8 (Audit manuel de fidélité et des citations)
- Ancienne Phase API/Docker → Nouvelle Phase 9
- Ancienne Phase 9 → Nouvelle Phase 10 (Rapport, README et revue finale)

### Jeu de développement ajouté:
Dans la Phase 5 -- Jeu d'évaluation et métriques de retrieval (3,5 h):
```
\item \textbf{Décision développement : Créer un jeu de développement de ~10 questions séparé pour les expérimentations, en plus du jeu gelé de 20-30 questions.}
```

### Temps de l'audit de fidélité:
Phase 8 -- Audit manuel de fidélité et des citations: **(2,25 h)**

### Résultat de la compilation LaTeX:
Compilation réussie avec `pdflatex` (MiKTeX 25.12):
- Sortie: 6 pages, 156,427 bytes
- Avertissement seulement: "Overfull \hbox (2.92012pt too wide) in paragraph at lines 166--167"
- Aucune erreur de compilation
- Fichier PDF généré: plan.pdf

## 3. Version du dossier 243300316_PLUi_20260505 et correspondance avec la version du 12 mai 2026 ; contenu du .gitignore

### Version du dossier et correspondance:
D'après l'inspection du fichier XML metadata (`fr-243300316-plui20260505.xml`) précédemment consulté:
- Date de publication: `<gco:Date>2026-05-05</gco:Date>`
- Date de révision: `<gco:Date>2026-05-05</gco:Date>`
- Identifiant: `<gco:CharacterString>https://www.geoportail-urbanisme.gouv.fr/document/243300316_PLUi_20260505</gco:CharacterString>`

Cette version correspond bien à la "version 30, publiée et en vigueur depuis le 12 mai 2026" mentionnée dans le journal.md (Phase 0, lignes 38-39). La différence de dates (5 mai vs 12 mai) est cohérente avec une date de préparation/publication anticipée par rapport à la date officielle d'entrée en vigueur.

### Contenu du .gitignore:
Fichier `.gitignore` créé dans le répertoire RAG project (`C:\Users\annem\Desktop\T.T.L.T.F.I\RAG project\.gitignore`):
```
# Large GIS files from PLUi dataset - do not version
243300316_PLUi_20260505/**/*.shp
243300316_PLUi_20260505/**/*.shx
243300316_PLUi_20260505/**/*.dbf
243300316_PLUi_20260505/**/*.prj
243300316_PLUi_20260505/**/*.sbn
243300316_PLUi_20260505/**/*.sbx
243300316_PLUi_20260505/**/*.cpg
243300316_PLUi_20260505/**/*.qmd
# Python and environment
.env
venv/
__pycache__/
# Generated indexes
*.index
*.faiss
# LaTeX auxiliary files
*.aux
*.log
*.toc
*.lof
*.lot
*.fls
*.out
*.fdb_latexmk
*.synctex.gz
*.bbl
*.blg
# Ignore entire PLUi directory except retained PDFs
243300316_PLUi_20260505/
!243300316_PLUi_20260505/**/*.pdf
```

## 4. Audit UM8 : classification des 51 sections, dépendances au plan de zonage, renvois vers autres parties

### Nombre d'articles distincts exploitables dans le chapitre UM8:
**51 titres de chapitres/sous-articles dans les signets** (journal.md, ligne 57)
> "Le chapitre occupe environ 40 pages du PDF (pages PDF 301–340; pagination imprimée 3–42) et contient **51 titres de chapitres/sous-articles dans les signets**. Ce compte inclut les titres de niveau supérieur : il indique une matière suffisante, mais ne remplace pas la création et la validation des 20–30 questions d'évaluation."

### Renvois à des plans ou annexes:
- **38 occurrences** de « plan de zonage » (journal.md, ligne 58)
- **19 occurrences** de « annexe » (journal.md, ligne 58)
> "Repérage des références cartographiques : **38 occurrences** de « plan de zonage » dans le texte extrait du segment UM8. Le mot « annexe » apparaît **19 fois**, au sens large (toutes ces occurrences ne sont pas nécessairement des renvois à une pièce annexe)."

### Dispositions communes à toutes les zones qui devront être incluses:
**Article 1.1 : définitions de destination des constructions** (journal.md, ligne 12)
> "Vérification de l'article 1.1 : le texte dit explicitement que les définitions de destination des constructions sont communes à l'ensemble des zones; cette section figure dans le chapitre UM8."

### Classification des 51 sections UM8:
Non établi - nécessite l'analyse complète du texte UM8 pour classifier chaque section en:
- (a) règle textuelle autonome
- (b) dépend d'un plan de zonage
- (c) administratif/générique

### Spécification des dépendances au plan de zonage (pour la catégorie b):
Non établi - nécessite l'analyse complète du texte UM8 pour préciser quelles règles exactement dépendent du plan (hauteur, implantation, emprise...)

### Liste de TOUS les renvois du texte UM8 vers d'autres parties du règlement:
Non établi - nécessite l'analyse complète du texte UM8 pour identifier tous les renvois avec leur numéro de page et déterminer lesquels devront être inclus dans le corpus.

## 5. Questions candidates

### Rédaction de 25 questions candidates répondables uniquement à partir du texte:
**0 questions rédigées** - nécessite l'accès au texte complet du chapitre UM8 pour rédiger des questions répondables uniquement à partir du texte, avec pour chacune l'article attendu.
