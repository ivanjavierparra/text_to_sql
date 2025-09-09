
# KB for Text-to-SQL (RAG)

This folder contains curated *business rules*, *schema notes*, and *few-shot SQL examples* to help your LLM generate safer SQL.
Use `build_rag_sql.py` to (re)index this knowledge into a local vector store (FAISS if available, else Chroma).

## Files
- `business_rules.md` — general guardrails and house style for SQL generation.
- `schema_notes.md` — notes about the current database and gotchas.
- `fewshots.sql.md` — pairs of Question ↔ SQL to guide the model.
- `build_rag_sql.py` — script to (re)build the vector store and return a LangChain retriever.
- `rag_config.json` — configuration (vector store path, embedding model).

## Quick start
```bash
# (optional) prepare embeddings in Ollama
ollama pull nomic-embed-text

# build the vector store
python build_rag_sql.py
```
