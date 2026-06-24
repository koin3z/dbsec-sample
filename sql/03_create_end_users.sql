-- Create local end users for Phase 1 direct logon.
-- The shared password placeholder is for local demos only and is rendered from
-- DEMO_DEFAULT_PASSWORD by scripts/run_sql.py. Do not commit real passwords.
--
-- Quoted lowercase end-user names are intentional. They must match
-- ORA_END_USER_CONTEXT.username and DEMO_HR.EMPLOYEES.principal_name values.
--
-- Do not grant SELECT on {{DEMO_SCHEMA}}.employees. Visibility comes from Data
-- Grants in sql/05_create_data_grants.sql.

CREATE END USER "staff_tokyo" IDENTIFIED BY {{DEMO_DEFAULT_PASSWORD}};
CREATE END USER "manager_tokyo" IDENTIFIED BY {{DEMO_DEFAULT_PASSWORD}};
CREATE END USER "manager_japan" IDENTIFIED BY {{DEMO_DEFAULT_PASSWORD}};
CREATE END USER "ai_assistant" IDENTIFIED BY {{DEMO_DEFAULT_PASSWORD}};
