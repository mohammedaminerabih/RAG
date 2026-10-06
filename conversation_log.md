# Journal de conversation — projet RAG PLUi

Transcription partielle des échanges visibles dans le contexte de travail du 6 octobre 2026. Elle commence au cadrage de la phase 0; les réponses antérieures qui ne sont pas disponibles dans ce contexte ne sont pas reconstituées. À partir d'ici, ajouter les échanges pertinents sans les réécrire.

## 2026-10-06 — Décisions de phase 0

### Utilisateur (brut)

> Décisions pour la phase 0 :
> - UM8 est acceptée à titre provisoire. Avant de la verrouiller, lis le règlement écrit et confirme : (a) assez d'articles distincts pour ~25 questions répondables, (b) pas de dépendance forte à des documents graphiques/annexes, (c) les dispositions communes à toutes les zones sont incluses dans le corpus. Si un critère échoue, propose une autre zone avant toute autre action.
> - LLM : API hébergée, un seul modèle, identifiant fixé en configuration, budget plafonné, clé dans .env ignoré par git. Tests automatisés avec LLM simulé.
> - Ne télécharge pas l'archive de 1,91 Go : récupère uniquement les pièces utiles (règlement, et PADD/POA seulement pour le contexte) et note URL, version, date, empreinte du fichier.
>
> Ce que je veux dès maintenant, dans le dossier du projet :
> 1. Un fichier LaTeX (plan.tex) avec le plan complet dès le début : objectifs, phases 0 à 9 (+ phase API/Docker), tâches, livrable, critère de réussite et temps estimé par phase (cœur ≈ 23,5 h, reranking facultatif). Il sert de référence unique pour tout le projet et se met à jour à chaque phase.
> 2. Un fichier journal.md tenu à jour tout au long du projet. Pour chaque phase : ce qu'on a fait, les décisions prises et pourquoi, les alternatives écartées, les problèmes rencontrés et comment on les a réglés, les résultats chiffrés. Il doit me permettre de réviser et de préparer l'entretien : ajoute à chaque phase une section « questions d'entretien probables et ma réponse ».
> 3. Un fichier conversation_log.md avec la trace brute de nos échanges, si c'est faisable.
>
> Protocole : annonce la phase en cours, ne passe à la suivante qu'après mon autorisation explicite, et mets à jour plan.tex et journal.md à la fin de chaque phase. Ne fais rien de plus dans cette réponse que la création de ces fichiers et la phase 0, puis arrête-toi pour validation.

### Assistant (commentaires de progression, bruts)

> Je prends ça comme feu vert pour traiter seulement la phase 0. Les corrections sont justes : je les intègre au plan, et je vais vérifier les intitulés de zones dans le règlement actuel avant d'en proposer une — sans prétendre couvrir les règles applicables à une parcelle. Le choix API/local dépend aussi de ton budget et de ton matériel, donc je vais te proposer un défaut clair et ses conditions.

> Dans le dépôt RAG, je n'ai trouvé aucun PDF : seulement le README et les documents de planification. Je vérifie les sources officielles actuelles pour te dire quoi récupérer sans risquer de partir d'une version archivée.

> J'ai trouvé dans la documentation officielle l'API qui sert une pièce écrite individuellement. Je tente maintenant l'accès au seul règlement PDF via cet endpoint — pas à l'archive. Je n'arrêterai pas la validation sur les seules métadonnées de la fiche.

> Le fichier récupéré est bien le règlement écrit seul, mais il regroupe les chapitres de nombreuses zones (6 762 pages au total), pas uniquement UM8. Je vais isoler les pages UM8 et les règles communes sans inclure les plans graphiques, puis décider si une base documentaire de 25 questions est réaliste.

> L'audit confirme 51 signets de sections dans le chapitre UM8, dont des règles générales explicitement communes à toutes les zones. En revanche, les références au plan sont réelles : UM8 ne convient qu'à des questions sur le texte, sans conclusion sur une parcelle; en cas de dépendance à une carte ou annexe, le système devra s'abstenir. Je consigne cette limite et le contrôle de version dans les trois fichiers demandés, puis je m'arrête.

