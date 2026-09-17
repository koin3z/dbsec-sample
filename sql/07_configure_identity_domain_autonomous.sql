-- Phase 2 Identity Domain configuration for Autonomous AI Database.
-- Run this only on Autonomous AI Database targets.
-- For non-Autonomous Oracle AI Database, use 07_configure_identity_domain.sql.
--
-- Required .env values:
-- - IDENTITY_DOMAIN_URL
-- - IDENTITY_DOMAIN_DATABASE_APP_ID
-- - IDENTITY_DOMAIN_DATABASE_CLIENT_ID
-- - IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET
--
-- Do not commit real client secrets. scripts/run_sql.py renders the secret
-- from .env at execution time.

BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_EXTERNAL_AUTHENTICATION(
    type   => 'OCI_IAM',
    params => JSON_OBJECT(
      'app_id'     VALUE {{IDENTITY_DOMAIN_DATABASE_APP_ID}},
      'domain_url' VALUE {{IDENTITY_DOMAIN_URL}}
    )
  );
END;
/

BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'OCI_IAM_DOMAIN_DB_CRED$',
    username        => {{IDENTITY_DOMAIN_DATABASE_CLIENT_ID}},
    password        => {{IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET}}
  );
END;
/
