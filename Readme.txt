
Paquetes necesarios para agregarle 
1-Few-shot / consultas prearmadas: ejemplos de preguntas↔SQL que el LLM use como guía.
2-RAG con base vectorial: indexar “saber auxiliar” (schema, reglas de negocio, consultas útiles) y recuperarlo 
  dinámicamente para inyectarlo en el prompt que genera el SQL.

langchain Version: 0.3.27
langchain-community Version: 0.3.29
pip install faiss-cpu Version: 1.12.0
pip install chromadb Version: 1.0.20
pip install sentence-transformers Version: 5.1.0