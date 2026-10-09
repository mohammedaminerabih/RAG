# RAG juridique — règlement du PLUi de Bordeaux Métropole (UM8)

Prototype de recherche documentaire et de réponses sourcées sur le règlement écrit d'une zone. Le périmètre reste provisoire : le projet ne doit pas être présenté comme un outil de conformité urbanistique à une adresse.

## Architecture prévue

Le pipeline est écrit à la main, sans LangChain/LlamaIndex au démarrage : PDF officiel → extraction contrôlée page par page → sections/chunks avec pages sources et IDs stables → embeddings + index vectoriel → retrieval → LLM hébergé configuré → citations résolues par le code ou abstention. Une branche d'évaluation séparée mesurera le retrieval et la génération. Ce README décrit l'état exécutable du dépôt; les notes et documents de suivi internes sont conservés hors du dépôt.

## État actuel — phases 0 à 4 terminées

- Extraction et chunking localisés dans `src/`; recherche des limites du chapitre vérifiée sur le PDF : pages PDF **303–340**.
- 38 pages extraites; 98 sections détectées, dont 13 sans contenu ignorées; **130 chunks** produits (62–1 500 caractères, médiane 947,5).
- **59 tests automatisés** couvrent notamment l'extraction, le chunking, les pages de citation et les contrats de validation des embeddings/index.
- La page 322 (tableau de coefficient de végétalisation, article 2.1.5) et la page 324 (deux tableaux et un schéma; F1 lexical comparatif : 0,9222) ont été examinées visuellement. Le texte extrait linéarise les cellules : les questions dépendant d'une association certaine ligne/colonne sont exclues du premier jeu d'évaluation. pypdf est sélectionné explicitement aux pages 324, 327 et 328; sur 327–328, il conserve mieux les indices de hauteur HF/HT.
- Contrôle visuel des frontières sur le PDF : 302 est le sommaire UM8, 303 le début du corps UM8, 340 en est encore une page, et 341 est une page de colophon. Le sommaire UM9 est page 344 et son corps commence page 345.
- Dix chunks choisis avec une graine fixe ont été comparés manuellement au PDF. Les clauses en prose concordent; les marqueurs de liste de la page 308 et les indices HF/HT ont été normalisés, et le découpage ne commence plus au milieu d'un mot. L'échantillon confirme aussi qu'un chunk de tableau peut manquer de contexte de colonnes : ces questions restent exclues.
- L'index dense a été construit : **130 vecteurs × 384 dimensions**, modèle `intfloat/multilingual-e5-small` épinglé à une révision immuable, normalisation L2 et FAISS `IndexFlatIP`. La longueur maximale des passages est **464/512 tokens**; l'index relu contient 130 entrées et le JSON garde la correspondance position→ID de chunk.
- Le retrieval de questions, le jeu d'évaluation, le LLM et l'API ne sont **pas encore implémentés** (phase 5 et suivantes).
- UM8 est retenue comme corpus pilote de questions sur le texte écrit, pas comme outil de conformité à une adresse. L'article 1.1 contient les définitions annoncées communes à toutes les zones. Le corpus ne revendique pas l'exhaustivité des autres règles générales.

## Structure

```text
data/
  243300316_reglement_20260505.pdf   # source locale ignorée par Git (147 MB)
  extracted/                         # deux extractions + source retenue + rapports
  chunked/                           # JSON de chunks
  index/um8_index_metadata.json      # modèle, hashes, versions et mapping position→chunk
  index/um8.faiss                    # index local ignoré par Git, recréable
src/
  find_boundaries.py
  extract_um8.py
  chunk_um8.py
  embedding_config.py
  build_index.py
tests/
  test_build_index.py
requirements.txt                     # parsing, tests et index dense (phases 0–4)
SOURCES.MANIFEST                     # provenance, version, URL et SHA-256
```

## Reproduire l'état actuel (PowerShell)

Le PDF n'est pas versionné. Télécharger uniquement la pièce écrite, pas l'archive complète :

```powershell
New-Item -ItemType Directory -Force data | Out-Null
Invoke-WebRequest `
  -Uri "https://www.geoportail-urbanisme.gouv.fr/api/document/0b6c6621184959caf3fa5b684f929657/files/243300316_reglement_20260505.pdf" `
  -OutFile "data/243300316_reglement_20260505.pdf"
Get-FileHash data/243300316_reglement_20260505.pdf -Algorithm SHA256
```

L'empreinte attendue est dans `SOURCES.MANIFEST`. Puis installer et exécuter :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider tests
python src/extract_um8.py
python src/chunk_um8.py
python src/build_index.py
```

`extract_um8.py` détecte automatiquement les pages de la zone avant extraction. `find_boundaries.py` reste disponible pour vérifier séparément la plage détectée; l'extraction manuelle exige de fournir ensemble `--start` et `--end`.
La première exécution de `build_index.py` télécharge la révision épinglée du modèle dans `.cache/huggingface/` (ignoré par Git), puis crée l'index FAISS local et son JSON de provenance. Les entrées sont encodées avec le préfixe `passage:`; la phase 5 devra encoder les questions avec `query:`.

## Provenance et limites

Le manifeste officiel indique une version 30, publiée le 12 mai 2026 et en vigueur. Le fichier récupéré est le règlement écrit **par zones**, pas les plans graphiques, atlas, listes de prescriptions, annexes ou documents de contexte. Les définitions de l'article 1.1, annoncées communes à toutes les zones, sont bien présentes. Cela ne prouve pas que toutes les règles générales utiles sont couvertes; le périmètre se limite aux passages textuels disponibles et le système devra s'abstenir si une réponse dépend d'une pièce absente.

Des clauses renvoient au plan de zonage, à des prescriptions ou à des annexes. Les questions dont la réponse dépend de ces pièces devront être exclues du jeu répondable ou recevoir une abstention, sauf décision ultérieure d'élargir le corpus.

Les métriques automatiques d'extraction comparent le F1 des multiensembles de mots après normalisation : elles repèrent les pertes lexicales mais ne vérifient ni l'ordre d'une table, ni son sens juridique. Les tableaux des pages 322 et 324 ont été visualisés; leurs valeurs sont hors périmètre tant que les relations entre cellules ne sont pas représentées explicitement. Les autres tableaux ne doivent pas être considérés comme validés au seul motif que leur F1 lexical est élevé.
