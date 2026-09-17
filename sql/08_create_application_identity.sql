-- Phase 2 application identity mapped to the Identity Domain OAuth client.
-- Data Grants are not attached directly to OAuth client IDs. Instead, map the
-- client ID to an application identity, grant data roles to that identity, and
-- attach Data Grants to the data roles.
--
-- Required .env values:
-- - DEMO_APP_CLIENT_ID
-- Optional .env values:
-- - PHASE2_APP_IDENTITY, default DEEPSEC_DEMO_APP

CREATE OR REPLACE APPLICATION IDENTITY {{PHASE2_APP_IDENTITY}}
  MAPPED TO {{DEMO_APP_CLIENT_ID_MAPPING}};
