-- Phase 2 Data Grants for application-mediated DDS.
-- Data Grants attach to Data Roles, not directly to OAuth client IDs.
-- Row, column, and cell control remains enforced by Oracle Deep Data Security.
-- Do not add a normal GRANT SELECT on {{DEMO_SCHEMA}}.employees.

-- Application directory lookup: active employees, non-sensitive directory fields.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.app_directory_lookup_grant
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
  TO {{PHASE2_APP_DIRECTORY_DATA_ROLE}};

-- Sensitive lookup: requires both the application identity role and a verified
-- end-user security context. Without ORA_END_USER_CONTEXT.username, this grant
-- fails closed by matching no employee row.
CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.app_own_sensitive_lookup_grant
  AS SELECT (
    employee_id,
    principal_name,
    display_name,
    salary_amount,
    personal_id,
    phone_number
  )
  ON {{DEMO_SCHEMA}}.employees
  WHERE principal_name = ORA_END_USER_CONTEXT.username
  TO {{PHASE2_APP_SENSITIVE_DATA_ROLE}};
