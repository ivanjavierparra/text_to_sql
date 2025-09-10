#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import List, Dict, Any
from pathlib import Path
import json
import re

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from langchain_community.utilities import SQLDatabase
from langchain_community.vectorstores import DocArrayInMemorySearch  # liviano y 100% local

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------

# Ollama local (ajustá si corrés en otro host/puerto)
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")

LLM_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
EMB_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Conexión MySQL (tu ejemplo)
DB_URI = os.environ.get("DB_URI", "mysql+pymysql://root:root@localhost/employees")

# ¿Querés usar retriever sobre “table cards” (True) o pegar un texto largo con el esquema (False)?
USE_RETRIEVER = True

# ---------------------------------------------------------------------------
# 1) BASE DE DATOS
# ---------------------------------------------------------------------------
db = SQLDatabase.from_uri(DB_URI)
print("Dialect:", db.dialect)
print("Usable tables (sample):", list(db.get_usable_table_names())[:10])

# ---------------------------------------------------------------------------
# 2) ESQUEMA MANUAL
#    - Modo A: pegar un texto plano (SCH_TEXT)
#    - Modo B: pasar “table cards” (SCHEMA_CARDS), se indexan y se recuperan por pregunta
# ---------------------------------------------------------------------------

# MODO A — Texto plano (puede ser un subset de tus 500 tablas o el DDL resumido)
SCH_TEXT = """
-- employees(id, birth_date, first_name, last_name, gender, hire_date)
-- salaries(emp_no, salary, from_date, to_date) FK->employees.emp_no
-- titles(emp_no, title, from_date, to_date) FK->employees.emp_no
-- departments(dept_no, dept_name)
-- dept_emp(emp_no, dept_no, from_date, to_date) FKs->employees.emp_no, departments.dept_no
-- dept_manager(emp_no, dept_no, from_date, to_date) FKs->employees.emp_no, departments.dept_no
"""

# MODO B — “Table cards”: una tarjeta por tabla (ideal para 500+)
#   - Podés construir esto programáticamente desde tus metadatos y guardarlo en JSON/YAML.
#   - Cada card debe tener un 'table' y un 'content' (descripción/DDL/columnas)
SCHEMA_CARDS: List[Dict[str, str]] = [
    {
        "table": "employees",
        "content": """Table: employees
Columns:
- emp_no (INT, PK)
- birth_date (DATE)
- first_name (VARCHAR)
- last_name (VARCHAR)
- gender (ENUM('M','F'))
- hire_date (DATE)
Notes: Master list of employees."""
    },
    {
        "table": "salaries",
        "content": """Table: salaries
Columns:
- emp_no (INT, FK employees.emp_no)
- salary (INT)
- from_date (DATE)
- to_date (DATE) -- usually '9999-01-01' means current
Notes: Salary history per employee."""
    },
    {
        "table": "titles",
        "content": """Table: titles
Columns:
- emp_no (INT, FK employees.emp_no)
- title (VARCHAR)
- from_date (DATE)
- to_date (DATE)"""
    },
    {
        "table": "departments",
        "content": """Table: departments
Columns:
- dept_no (CHAR)
- dept_name (VARCHAR)"""
    },
    {
        "table": "dept_emp",
        "content": """Table: dept_emp
Columns:
- emp_no (INT, FK employees.emp_no)
- dept_no (CHAR, FK departments.dept_no)
- from_date (DATE)
- to_date (DATE)
Notes: Employee department assignments."""
    },
    {
        "table": "dept_manager",
        "content": """Table: dept_manager
Columns:
- emp_no (INT, FK employees.emp_no)
- dept_no (CHAR, FK departments.dept_no)
- from_date (DATE)
- to_date (DATE)
Notes: Department managers over time."""
    },
    # ... añade aquí el resto de tus tables como "cards"
]

# Si preferís cargar las cards desde archivo:
# SCHEMA_CARDS = json.loads(Path("schema_cards.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# 3) FEW-SHOTS SQL (EJEMPLOS)
#    Agregá acá queries típicas de tu día a día (MySQL).
# ---------------------------------------------------------------------------

EXAMPLES_SQL: List[Dict[str, str]] = [
    {
        "question": "How many employees are there?",
        "sql": "SELECT COUNT(*) AS total_employees FROM employees;"
    },
    {
        "question": "What is the average salary of current employees?",
        "sql": (
            "SELECT AVG(s.salary) AS avg_salary_current "
            "FROM salaries s "
            "WHERE s.to_date = '9999-01-01';"
        ),
    },
    {
        "question": "Top 5 departments by number of current employees",
        "sql": (
            "SELECT d.dept_name, COUNT(*) AS headcount "
            "FROM dept_emp de "
            "JOIN departments d ON d.dept_no = de.dept_no "
            "WHERE de.to_date = '9999-01-01' "
            "GROUP BY d.dept_name "
            "ORDER BY headcount DESC "
            "LIMIT 5;"
        ),
    },
    {
        "question": "Latest hire date per department (top 5)",
        "sql": (
            "SELECT d.dept_name, MAX(e.hire_date) AS latest_hire "
            "FROM employees e "
            "JOIN dept_emp de ON de.emp_no = e.emp_no "
            "JOIN departments d ON d.dept_no = de.dept_no "
            "GROUP BY d.dept_name "
            "ORDER BY latest_hire DESC "
            "LIMIT 5;"
        ),
    },
    {
        "question": "Average salary by title in year 2010",
        "sql": (
            "SELECT t.title, AVG(s.salary) AS avg_salary_2010 "
            "FROM titles t "
            "JOIN salaries s ON s.emp_no = t.emp_no "
            "WHERE s.from_date <= '2010-12-31' AND s.to_date >= '2010-01-01' "
            "GROUP BY t.title "
            "ORDER BY avg_salary_2010 DESC;"
        ),
    },
]

def render_examples_block(examples: List[Dict[str, str]]) -> str:
    lines = []
    for ex in examples:
        lines.append(f'Q: {ex["question"]}\nSQL:\n{ex["sql"]}\n')
    return "\n".join(lines)

EXAMPLES_BLOCK = render_examples_block(EXAMPLES_SQL)

# ---------------------------------------------------------------------------
# 4) RETRIEVER (solo si USE_RETRIEVER=True) — indexa las "table cards"
# ---------------------------------------------------------------------------
retriever = None
if USE_RETRIEVER:
    embeddings = OllamaEmbeddings(model=EMB_MODEL, base_url=os.environ["OLLAMA_HOST"])
    vectorstore = DocArrayInMemorySearch.from_texts(
        texts=[c["content"] for c in SCHEMA_CARDS],
        embedding=embeddings,
        metadatas=[{"table": c["table"]} for c in SCHEMA_CARDS],
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 12})

def get_schema_context(question: str) -> str:
    """
    Devuelve el contexto de esquema a inyectar en el prompt.
    - Si USE_RETRIEVER=True => top-k table cards relevantes
    - Si no => el texto plano SCH_TEXT
    """
    if USE_RETRIEVER and retriever is not None:
        docs = retriever.get_relevant_documents(question)
        block = []
        for d in docs:
            t = d.metadata.get("table", "unknown")
            block.append(f"## {t}\n{d.page_content}")
        return "\n\n".join(block)
    else:
        return SCH_TEXT.strip()

# ---------------------------------------------------------------------------
# 5) PROMPT del generador de SQL (sólo MySQL, sin fences, sin explicaciones)
# ---------------------------------------------------------------------------
SYSTEM = """You are an expert MySQL query generator.
Given the user question, the database schema context, and the examples, produce ONE valid MySQL SELECT query.
Rules:
- Return ONLY the SQL, without ``` fences, comments, or any explanation.
- Use ONLY tables/columns from the provided schema context.
- Prefer explicit column names over SELECT *.
- If the query could be large and has no aggregation, add a LIMIT 100.
- Never perform DML/DDL (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER).
- Double-check JOIN keys and date filters.
- The SQL dialect is MySQL."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        (
            "human",
            "Schema context:\n{schema_context}\n\n"
            "Examples:\n{examples_sql}\n\n"
            "Question: {question}\n"
            "SQL (MySQL only):"
        ),
        MessagesPlaceholder("agent_scratchpad"),  # reservado si luego agregás razonamiento en cadena
    ]
)

# ---------------------------------------------------------------------------
# 6) LLM y cadena para generar SQL
# ---------------------------------------------------------------------------
llm = ChatOllama(
    model=LLM_MODEL,
    base_url=os.environ["OLLAMA_HOST"],
    temperature=0,
)

def strip_code_fences(x: str) -> str:
    s = x.strip()
    s = re.sub(r"^```sql\s*|\s*```$", "", s, flags=re.I|re.S)
    s = s.strip().rstrip(";") + ";"  # aseguro ; final
    return s

sql_generator = (
    RunnablePassthrough.assign(
        schema_context=lambda x: get_schema_context(x["question"]),
        examples_sql=lambda x: EXAMPLES_BLOCK,
    )
    | PROMPT
    | llm
    | StrOutputParser()
)

# ---------------------------------------------------------------------------
# 7) Funciones utilitarias: generar y ejecutar
# ---------------------------------------------------------------------------
def generate_sql(question: str) -> str:
    raw = sql_generator.invoke({"question": question})
    return strip_code_fences(raw)

def run_sql(sql: str) -> Any:
    return db.run(sql)

# ---------------------------------------------------------------------------
# 8) DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    q = "how many employees are there? You MUST RETURN ONLY MYSQL QUERIES."
    sql = generate_sql(q)
    print("\nSQL generado:\n", sql)
    try:
        res = run_sql(sql)
        print("\nResultado:\n", res)
    except Exception as e:
        print("\nError al ejecutar SQL:", e)
