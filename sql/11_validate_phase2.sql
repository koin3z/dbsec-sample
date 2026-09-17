-- Phase 2 validation queries for Identity Domain and DDS metadata.
-- These statements do not query the protected employee table.
--
-- Oracle 26ai preview/patch levels can expose different dictionary view
-- column names for DDS application identity metadata. This validation script
-- intentionally prints the view columns first and then uses SELECT * so it does
-- not fail on a renamed DISPLAY column such as APPLICATION_IDENTITY vs NAME.

SELECT name, value
FROM v$parameter
WHERE name IN ('identity_provider_type', 'identity_provider_oauth_config')
ORDER BY name;

SELECT table_name, column_id, column_name, data_type
FROM all_tab_columns
WHERE owner = 'SYS'
  AND table_name IN (
    'DBA_APPLICATION_IDENTITIES',
    'DBA_DATA_ROLES',
    'DBA_DATA_ROLE_GRANTS',
    'DBA_DATA_GRANTS'
  )
ORDER BY table_name, column_id;

SELECT *
FROM dba_application_identities
WHERE ROWNUM <= 50;

SELECT *
FROM dba_data_roles
WHERE ROWNUM <= 50;

SELECT *
FROM dba_data_role_grants
WHERE ROWNUM <= 50;

SELECT *
FROM dba_data_grants
WHERE ROWNUM <= 50;
