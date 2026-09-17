-- Optional Phase 2 setup for the shared application DB user.
-- This script is not part of the Phase 1 direct-logon setup path.
--
-- The shared app user is a global user mapped to OCI IAM / Identity Domains.
-- Set APP_IAM_MAPPING to one Oracle-supported mapping expression, for example:
--   IAM_PRINCIPAL_OCID=ocid1.instance.region1..example
--   IAM_GROUP_NAME=identity_domain/AppDatabasePrincipals
--
-- Do not put client secrets, database tokens, private keys, or passwords in SQL.
-- Do not grant normal SELECT on {{DEMO_SCHEMA}}.employees to {{APP_DB_USERNAME}}.
-- Protected table access must continue to come from Deep Data Security Data Grants.
--
-- The official application-mediated DDS path remains driver-managed: the client
-- driver attaches an EndUserSecurityContext payload containing a database-access
-- token to the connection. This setup only maps the shared DB schema to IAM.

CREATE USER {{APP_DB_USERNAME}} IDENTIFIED GLOBALLY AS {{APP_IAM_MAPPING}};
GRANT CREATE SESSION TO {{APP_DB_USERNAME}};
