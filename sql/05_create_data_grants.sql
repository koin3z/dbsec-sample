-- Verified against Oracle Deep Data Security Guide 26ai (June 2026).
-- Purpose: create Data Grants for row, column, and cell-level SELECT control.
--
-- Assumptions:
-- - {{DEMO_SCHEMA}} owns the protected EMPLOYEES table.
-- - EMPLOYEES contains the columns referenced below.
-- - principal_name stores the local end-user name, for example staff_tokyo.
-- - manager_principal_name stores the manager's local end-user name.
-- - Local end users were created with quoted lowercase names, for example
--   CREATE END USER "staff_tokyo" IDENTIFIED BY ...
--
-- Do not add a conventional GRANT SELECT ON {{DEMO_SCHEMA}}.employees to demo users
-- or to the direct-logon database role. Data visibility must come from Data Grants.

-- Own employee record: own row, all demo columns visible.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.own_employee_record
  AS SELECT
  ON {{DEMO_SCHEMA}}.employees
  WHERE principal_name = ORA_END_USER_CONTEXT.username
  TO employee_role;

-- Direct reports: direct-report rows visible, personal_id unauthorized.
-- When a manager queries columns that include personal_id, the direct-report cells
-- should be returned as NULL because that column is excluded from this data grant.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.direct_reports_without_personal_id
  AS SELECT (ALL COLUMNS EXCEPT personal_id)
  ON {{DEMO_SCHEMA}}.employees
  WHERE manager_principal_name = ORA_END_USER_CONTEXT.username
  TO manager_role;

-- Japan sales scope: broader Japan Sales access, but only directory/work columns.
-- Sensitive columns such as personal_id, salary, phone, or other columns not listed
-- here remain unauthorized for rows reached only through this grant.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.japan_sales_directory
  AS SELECT (
    employee_id,
    principal_name,
    display_name,
    job_title,
    department,
    country,
    city,
    manager_principal_name,
    employment_status
  )
  ON {{DEMO_SCHEMA}}.employees
  WHERE country = 'Japan'
    AND department = 'Sales'
    AND employment_status = 'ACTIVE'
  TO country_manager_role;

-- AI assistant lookup: least-privilege directory-style access.
-- This intentionally omits principal_name and manager_principal_name to avoid
-- exposing internal account names unless the demo explicitly needs them.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.ai_employee_lookup
  AS SELECT (
    employee_id,
    display_name,
    job_title,
    department,
    country,
    city,
    employment_status
  )
  ON {{DEMO_SCHEMA}}.employees
  WHERE employment_status = 'ACTIVE'
  TO ai_agent_role;
