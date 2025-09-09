
import os, json, argparse
from pathlib import Path
from typing import Any, Dict, List

from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores import Chroma

KB_DIR = Path(__file__).parent
CFG = json.loads((KB_DIR / "rag_config.json").read_text())

def make_embeddings():
    # Try Ollama first
    try:
        e = OllamaEmbeddings(model=CFG["embedding"]["model"],
                             base_url=CFG["embedding"].get("base_url","http://localhost:11434"))
        # Sanity: small embed
        _ = e.embed_query("ping")
        return e
    except Exception:
        # Fallback HuggingFace
        hf_model = CFG["fallback_embedding"]["model_name"]
        return HuggingFaceEmbeddings(model_name=hf_model)

def load_kb_documents() -> List[Document]:
    docs = []
    for fname in ["business_rules.md", "schema_notes.md", "fewshots.sql.md"]:
        p = KB_DIR / fname
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            docs.append(Document(page_content=txt, metadata={"source": fname}))
    return docs

def build_vectorstore(docs, emb):
    persist_dir = CFG["persist_dir"]
    try:
        vs = FAISS.from_documents(docs, emb)
        vs.save_local(persist_dir)
        return ("faiss", vs)
    except Exception:
        vs = Chroma.from_documents(docs, emb, persist_directory=persist_dir)
        return ("chroma", vs)

def get_retriever(vs_kind, vs_obj):
    k = CFG["search"]["k"]
    if vs_kind == "faiss":
        return vs_obj.as_retriever(search_kwargs={"k": k})
    else:
        # Chroma retriever
        return vs_obj.as_retriever(search_kwargs={"k": k})

def main():
    emb = make_embeddings()
    docs = load_kb_documents()
    if not docs:
        raise SystemExit("No knowledge docs found. Add files to KB and retry.")
    kind, vs = build_vectorstore(docs, emb)
    retriever = get_retriever(kind, vs)
    print(f"Vector store built with {len(docs)} docs using {kind}.")
    # Optional quick test:
    sample = "How many employees are there?"
    hits = retriever.get_relevant_documents(sample)
    print("Sample retrieval:", [h.metadata.get("source") for h in hits])

if __name__ == "__main__":
    main()
