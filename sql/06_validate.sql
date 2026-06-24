-- Admin-side validation helpers.
-- These queries confirm ordinary demo objects and, where available in the target
-- dictionary, local end users. They do not prove Deep Data Security behavior;
-- validate DDS by connecting as each persona and running the canonical SELECT or
-- scripts/smoke_test.py.

SELECT COUNT(*) AS employee_count
FROM {{DEMO_SCHEMA}}.employees;

SELECT employee_id, principal_name, display_name, country, city, manager_principal_name
FROM {{DEMO_SCHEMA}}.employees
ORDER BY employee_id;

-- Must return no rows. If rows are returned here, principal_name values do not
-- match quoted lowercase local end-user names used by ORA_END_USER_CONTEXT.username.
SELECT employee_id, principal_name, manager_principal_name,
       CASE
         WHEN principal_name = LOWER(principal_name) THEN 'OK'
         ELSE 'CASE_MISMATCH'
       END AS principal_name_case,
       CASE
         WHEN manager_principal_name IS NULL
              OR manager_principal_name = LOWER(manager_principal_name) THEN 'OK'
         ELSE 'CASE_MISMATCH'
       END AS manager_name_case
FROM {{DEMO_SCHEMA}}.employees
WHERE principal_name != LOWER(principal_name)
   OR manager_principal_name != LOWER(manager_principal_name)
ORDER BY employee_id;

SELECT username, account_status
FROM dba_users
WHERE username IN (
  '{{DEMO_SCHEMA}}',
  'staff_tokyo',
  'manager_tokyo',
  'manager_japan',
  'ai_assistant'
)
ORDER BY username;

-- If your 26ai environment exposes dictionary views for Deep Data Security data
-- roles, data-role grants, local end users, and data grants, query them here.
-- View names and columns can differ by privilege model, so this script keeps
-- those checks manual rather than guessing dictionary names.

-- Manual direct-logon validation using the canonical SELECT:
--
-- SELECT
--   employee_id,
--   principal_name,
--   display_name,
--   job_title,
--   department,
--   country,
--   city,
--   manager_principal_name,
--   employment_status,
--   salary_amount,
--   personal_id,
--   phone_number
-- FROM demo_hr.employees
-- ORDER BY employee_id;
--
-- Connect as "staff_tokyo".
-- Expected: only employee_id 1001; own sensitive values visible.
--
-- Connect as "manager_tokyo".
-- Expected: employee_id 1001, 1002, 1003.
-- Expected: personal_id for 1001 and 1002 is NULL; personal_id for 1003 is visible.
--
-- Connect as "manager_japan".
-- Expected: employee_id 1001, 1002, 1003, 1004, 1005 at minimum for Japan Sales.
-- Expected: non-own sensitive columns are NULL unless another applicable grant allows them.
--
-- Connect as "ai_assistant".
-- Expected: active employee directory data only.
-- Expected: salary_amount, personal_id, and phone_number are NULL or unavailable.
