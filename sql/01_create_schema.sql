-- Create the demo owner schema.
-- The password placeholder is rendered by scripts/run_sql.py from DEMO_DEFAULT_PASSWORD.
-- This schema owns only synthetic demo data.

CREATE USER {{DEMO_SCHEMA}} IDENTIFIED BY {{DEMO_DEFAULT_PASSWORD}} QUOTA UNLIMITED ON USERS;

GRANT CREATE SESSION TO {{DEMO_SCHEMA}};
GRANT CREATE TABLE TO {{DEMO_SCHEMA}};

-- Do not grant broad system privileges here. If the target Oracle Deep Data
-- Security version requires additional privileges to create Data Grants in this
-- schema, add the narrow documented privilege for that version and note it here.
