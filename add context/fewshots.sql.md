
# Few-shot Q ↔ SQL

## 1) Count employees
Q: how many employees are there?
SQL:
SELECT COUNT(*) AS total FROM `employees`;

## 2) Recently hired employees
Q: list 5 employees hired most recently
SQL:
SELECT `emp_no`, `first_name`, `last_name`, `hire_date`
FROM `employees`
ORDER BY `hire_date` DESC
LIMIT 5;

## 3) Departments count
Q: how many departments are there?
SQL:
SELECT COUNT(*) AS total FROM `departments`;

## 4) Current managers and their departments
Q: list current department managers and their departments
SQL:
SELECT d.`dept_name`, e.`first_name`, e.`last_name`
FROM `dept_manager` m
JOIN `departments` d ON d.`dept_no` = m.`dept_no`
JOIN `employees`  e ON e.`emp_no`  = m.`emp_no`
WHERE m.`to_date` = '9999-01-01'
ORDER BY d.`dept_name`;

## 5) Average current salary by department (top 5)
Q: show top 5 departments by average current salary
SQL:
SELECT d.`dept_name`, AVG(s.`salary`) AS avg_salary
FROM `dept_emp` de
JOIN `departments` d ON d.`dept_no` = de.`dept_no`
JOIN `salaries`  s  ON s.`emp_no` = de.`emp_no`
WHERE de.`to_date` = '9999-01-01'
  AND s.`to_date`  = '9999-01-01'
GROUP BY d.`dept_name`
ORDER BY avg_salary DESC
LIMIT 5;
