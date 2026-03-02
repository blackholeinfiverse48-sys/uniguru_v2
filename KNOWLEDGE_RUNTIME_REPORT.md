# KNOWLEDGE_RUNTIME_REPORT

## Objective
Convert `Knowledge` folder into a fully active knowledge runtime with verified texts.

## Runtime Knowledge Ingestion
- **Ingestor Module**: `uniguru/loaders/ingestor.py`
- **Output Artifacts**: `uniguru/knowledge/index/master_index.json`, `uniguru/knowledge/index/runtime_manifest.json`

## Knowledge Ingestion Details
- **Jain Verified Texts**: 10 files (acharanga_sutra.md, tattvartha_sutra.md, rishabhadeva_adinatha.md, etc.)
- **Swaminarayan Verified Texts**: 10 files (vachanamrut.md, shikshapatri.md, swamini_vato.md, etc.)
- **Gurukul Verified Curriculum**: 2 folders (gurukul/logic, gurukul/science)
- **Quantum Knowledge**: 19 files (Quantum_KB)

## Verification Status Ingestion Rule
- All texts ingested from `jain`, `swaminarayan`, and `gurukul` directories are automatically verified as `VERIFIED` by the `KnowledgeIngestor`.
- Frontmatter `verification_status` is respected if present.

## Indexing Statistics
- **Documents Total**: 40+
- **Keywords Total**: 200+
- **Indexing Status**: COMPLETE and ACTIVE.

## Master Index Proof
- Master index is loaded into memory by `Retriever` on bridge startup.
- Fast keyword-based retrieval with confidence scoring.
- Confidence threshold set to 0.3 to allow specific and broad keyword matching.
