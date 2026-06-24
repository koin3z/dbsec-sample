-- Verified against Oracle Deep Data Security Guide 26ai (June 2026).
-- Purpose: create locally managed data roles, direct-logon session role,
-- and assign data roles to local end users.
--
-- Prerequisites:
-- - Local end users must already exist, preferably as quoted lowercase names:
--   "staff_tokyo", "manager_tokyo", "manager_japan", "ai_assistant".
-- - Run 00_reset.sql first, or drop deepsec_demo_session_role manually.
-- - The executing user needs privileges to create/grant data roles and create roles.

-- Locally managed Deep Data Security data roles.
CREATE OR REPLACE DATA ROLE employee_role;
CREATE OR REPLACE DATA ROLE manager_role;
CREATE OR REPLACE DATA ROLE country_manager_role;
CREATE OR REPLACE DATA ROLE ai_agent_role;

-- Standard database role used only to allow direct database sessions.
-- Do not grant SELECT on the protected table through this role.
BEGIN
  EXECUTE IMMEDIATE 'CREATE ROLE deepsec_demo_session_role';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1921 THEN
      RAISE;
    END IF;
END;
/
GRANT CREATE SESSION TO deepsec_demo_session_role;

-- For direct logon, local end users inherit CREATE SESSION through their data role.
GRANT deepsec_demo_session_role TO employee_role;
GRANT deepsec_demo_session_role TO manager_role;
GRANT deepsec_demo_session_role TO country_manager_role;
GRANT deepsec_demo_session_role TO ai_agent_role;

-- Assign data roles to local end users.
-- Quoted lowercase names are intentional so ORA_END_USER_CONTEXT.username matches
-- principal_name values such as staff_tokyo and manager_tokyo.
GRANT DATA ROLE employee_role TO "staff_tokyo";

GRANT DATA ROLE employee_role TO "manager_tokyo";
GRANT DATA ROLE manager_role TO "manager_tokyo";

GRANT DATA ROLE employee_role TO "manager_japan";
GRANT DATA ROLE country_manager_role TO "manager_japan";

GRANT DATA ROLE ai_agent_role TO "ai_assistant";
