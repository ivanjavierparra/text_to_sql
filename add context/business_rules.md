
# Business Rules & Guardrails

- ❌ No DML/DDL: never `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`.
- ✅ Prefer simple, readable SQL with explicit `SELECT` lists and aliases.
- Wrap identifiers with backticks: `
`SELECT `first_name` FROM `employees`;`
`
- Use `LIMIT 5` unless the user clearly requests another limit.
- If the user says “today”, use `CURDATE()`.
- Use `JOIN` keys that exist and avoid cartesian products.
- For counts and aggregates: always provide an alias (e.g., `AS total`).
- If a table/column is not in schema info, do **not** reference it.
