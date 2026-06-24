-- Reset the local demo namespace.
-- Destructive scope: only DEMO_HR, demo local end users, demo data roles,
-- and the direct-logon database role used by this repository.
--
-- This script also drops the older uppercase DB users from the initial scaffold
-- so environments created before the verified Deep Data Security scripts can be
-- reset cleanly.

-- Drop Data Grants first because they depend on the table and data roles.
BEGIN
  EXECUTE IMMEDIATE 'DROP DATA GRANT {{DEMO_SCHEMA}}.own_employee_record';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA GRANT {{DEMO_SCHEMA}}.direct_reports_without_personal_id';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA GRANT {{DEMO_SCHEMA}}.japan_sales_directory';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA GRANT {{DEMO_SCHEMA}}.ai_employee_lookup';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

-- Drop local end users used by direct logon.
BEGIN
  EXECUTE IMMEDIATE 'DROP END USER "staff_tokyo"';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP END USER "manager_tokyo"';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP END USER "manager_japan"';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP END USER "ai_assistant"';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

-- Drop Deep Data Security data roles and the ordinary DB role used only for
-- CREATE SESSION inheritance in direct-logon mode.
BEGIN
  EXECUTE IMMEDIATE 'DROP DATA ROLE employee_role';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA ROLE manager_role';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA ROLE country_manager_role';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP DATA ROLE ai_agent_role';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP ROLE deepsec_demo_session_role';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

-- Drop older uppercase DB users from pre-verified scaffold revisions.
BEGIN
  EXECUTE IMMEDIATE 'DROP USER STAFF_TOKYO CASCADE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1918 THEN
      RAISE;
    END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP USER MANAGER_TOKYO CASCADE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1918 THEN
      RAISE;
    END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP USER MANAGER_JAPAN CASCADE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1918 THEN
      RAISE;
    END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP USER AI_ASSISTANT CASCADE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1918 THEN
      RAISE;
    END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE {{DEMO_SCHEMA}}.employees PURGE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -942 THEN
      RAISE;
    END IF;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP USER {{DEMO_SCHEMA}} CASCADE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -1918 THEN
      RAISE;
    END IF;
END;
/
