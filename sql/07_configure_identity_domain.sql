-- Phase 2 Identity Domain configuration for Oracle AI Database.
-- Run this only on non-Autonomous Oracle AI Database targets.
-- For Autonomous AI Database, use 07_configure_identity_domain_autonomous.sql.
--
-- Required .env values:
-- - IDENTITY_DOMAIN_URL
-- - IDENTITY_DOMAIN_DATABASE_APP_ID
-- - IDENTITY_DOMAIN_DATABASE_CLIENT_ID
-- - IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET
--
-- Do not commit real client secrets. scripts/run_sql.py renders the secret
-- from .env at execution time.

ALTER SYSTEM SET IDENTITY_PROVIDER_TYPE = OCI_IAM SCOPE=BOTH;

ALTER SYSTEM SET IDENTITY_PROVIDER_OAUTH_CONFIG = {{IDENTITY_PROVIDER_OAUTH_CONFIG}} SCOPE=BOTH;

BEGIN
  DBMS_CREDENTIAL.CREATE_CREDENTIAL(
    credential_name => 'OCI_IAM_DOMAIN_DB_CRED$',
    username        => {{IDENTITY_DOMAIN_DATABASE_CLIENT_ID}},
    password        => {{IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET}}
  );
END;
/
