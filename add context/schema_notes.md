
# Schema Notes (MySQL Employees)

Main tables used in examples:
- `employees(emp_no, birth_date, first_name, last_name, gender, hire_date)`
- `departments(dept_no, dept_name)`
- `dept_emp(emp_no, dept_no, from_date, to_date)`
- `dept_manager(emp_no, dept_no, from_date, to_date)`
- `titles(emp_no, title, from_date, to_date)`
- `salaries(emp_no, salary, from_date, to_date)`

Gotchas:
- Active department assignment often uses `to_date = '9999-01-01'` as current.
- There can be multiple `titles` and `salaries` per employee over time.
- Use joins via `emp_no` or `dept_no` as appropriate.
