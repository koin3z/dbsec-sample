from pathlib import Path

from deepsec_demo.config import DemoConfig
from scripts.run_sql import iter_statements, render_template

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"


def test_required_sql_files_exist() -> None:
    expected = {
        "00_reset.sql",
        "01_create_schema.sql",
        "02_create_sample_data.sql",
        "03_create_end_users.sql",
        "04_create_data_roles.sql",
        "05_create_data_grants.sql",
        "06_validate.sql",
        "07_configure_identity_domain.sql",
        "07_configure_identity_domain_autonomous.sql",
        "07_create_shared_app_user.sql",
        "08_create_application_identity.sql",
        "09_create_phase2_data_roles.sql",
        "10_create_phase2_data_grants.sql",
        "11_validate_phase2.sql",
    }
    assert {path.name for path in SQL_DIR.glob("*.sql")} >= expected


def test_sql_files_do_not_use_realistic_old_example_names() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in SQL_DIR.glob("*.sql")).lower()
    assert "ebaker" not in combined
    assert "manderson" not in combined


def test_data_role_and_data_grant_files_are_executable_verified_sql() -> None:
    roles = (SQL_DIR / "04_create_data_roles.sql").read_text(encoding="utf-8")
    grants = (SQL_DIR / "05_create_data_grants.sql").read_text(encoding="utf-8")
    assert "UNVERIFIED_DDS_DDL" not in roles
    assert "UNVERIFIED_DDS_DDL" not in grants
    assert "CREATE OR REPLACE DATA ROLE employee_role" in roles
    assert "CREATE ROLE deepsec_demo_session_role" in roles
    assert 'GRANT DATA ROLE employee_role TO "staff_tokyo"' in roles
    assert "CREATE OR REPLACE DATA GRANT {{DEMO_SCHEMA}}.own_employee_record" in grants
    assert "ORA_END_USER_CONTEXT.username" in grants
    assert len(list(iter_statements(roles))) == 16
    assert len(list(iter_statements(grants))) == 4


def test_standard_setup_sql_has_expected_statement_counts() -> None:
    counts = {
        path.name: len(list(iter_statements(path.read_text(encoding="utf-8"))))
        for path in SQL_DIR.glob("*.sql")
    }
    assert counts["00_reset.sql"] == 19
    assert counts["01_create_schema.sql"] == 3
    assert counts["02_create_sample_data.sql"] == 15
    assert counts["03_create_end_users.sql"] == 4
    assert counts["04_create_data_roles.sql"] == 16
    assert counts["05_create_data_grants.sql"] == 4
    assert counts["06_validate.sql"] == 4
    assert counts["07_create_shared_app_user.sql"] == 2
    assert counts["07_configure_identity_domain.sql"] == 3
    assert counts["07_configure_identity_domain_autonomous.sql"] == 2
    assert counts["08_create_application_identity.sql"] == 1
    assert counts["09_create_phase2_data_roles.sql"] == 4
    assert counts["10_create_phase2_data_grants.sql"] == 2
    assert counts["11_validate_phase2.sql"] == 6



def test_shared_app_user_placeholder_does_not_bypass_data_grants(monkeypatch) -> None:
    source = (SQL_DIR / "07_create_shared_app_user.sql").read_text(encoding="utf-8")
    executable_text = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("--")
    ).upper()
    assert "GRANT SELECT" not in executable_text
    assert "{{APP_DB_PASSWORD}}" not in source
    assert "{{APP_IAM_MAPPING}}" in source
    assert "IDENTIFIED GLOBALLY AS" in source
    assert "EndUserSecurityContext payload" in source
    assert "CREATE END USER SECURITY CONTEXT" not in source

    monkeypatch.setenv("APP_DB_USERNAME", "DEEPSEC_APP")
    monkeypatch.setenv(
        "APP_IAM_MAPPING",
        "IAM_PRINCIPAL_OCID=ocid1.instance.region1..example",
    )
    rendered = render_template(
        source,
        DemoConfig(
            host="localhost",
            port=1521,
            service_name="FREEPDB1",
            protocol="tcp",
            wallet_location=None,
            demo_schema="DEMO_HR",
            default_password="local_demo_password",
        ),
    )

    assert "CREATE USER DEEPSEC_APP IDENTIFIED GLOBALLY AS" in rendered
    assert "'IAM_PRINCIPAL_OCID=ocid1.instance.region1..example'" in rendered
    assert "app_password" not in rendered
    assert "GRANT CREATE SESSION TO DEEPSEC_APP" in rendered


def test_phase2_identity_domain_sql_uses_application_identity_pattern(monkeypatch) -> None:
    config_sql = (SQL_DIR / "07_configure_identity_domain.sql").read_text(
        encoding="utf-8"
    )
    app_identity_sql = (SQL_DIR / "08_create_application_identity.sql").read_text(
        encoding="utf-8"
    )
    roles_sql = (SQL_DIR / "09_create_phase2_data_roles.sql").read_text(
        encoding="utf-8"
    )
    grants_sql = (SQL_DIR / "10_create_phase2_data_grants.sql").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([config_sql, app_identity_sql, roles_sql, grants_sql])
    executable_text = "\n".join(
        line for line in combined.splitlines() if not line.strip().startswith("--")
    ).upper()

    assert "GRANT SELECT" not in executable_text
    assert "APPLICATION IDENTITY" in app_identity_sql
    assert "{{DEMO_APP_CLIENT_ID_MAPPING}}" in app_identity_sql
    assert "IAM_OAUTH_CLIENT_ID" not in grants_sql
    assert "TO {{PHASE2_APP_DIRECTORY_DATA_ROLE}}" in grants_sql
    assert "TO {{PHASE2_APP_SENSITIVE_DATA_ROLE}}" in grants_sql
    assert "ORA_END_USER_CONTEXT.username" in grants_sql
    assert "change_me" not in combined

    monkeypatch.setenv("IDENTITY_DOMAIN_URL", "https://idcs-example.identity.oraclecloud.com:443")
    monkeypatch.setenv("IDENTITY_DOMAIN_DATABASE_APP_ID", "database-app-id")
    monkeypatch.setenv("IDENTITY_DOMAIN_DATABASE_CLIENT_ID", "database-client-id")
    monkeypatch.setenv("IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET", "secret/with+symbols=")
    monkeypatch.setenv("DEMO_APP_CLIENT_ID", "demo-client-id")
    monkeypatch.setenv("PHASE2_APP_IDENTITY", "DEEPSEC_DEMO_APP")

    demo_config = DemoConfig(
        host="localhost",
        port=1521,
        service_name="FREEPDB1",
        protocol="tcp",
        wallet_location=None,
        demo_schema="DEMO_HR",
        default_password="local_demo_password",
    )
    rendered_config = render_template(config_sql, demo_config)
    rendered_app_identity = render_template(app_identity_sql, demo_config)
    rendered_grants = render_template(grants_sql, demo_config)

    assert "IDENTITY_PROVIDER_TYPE = OCI_IAM" in rendered_config
    assert '"app_id":"database-app-id"' in rendered_config
    assert '"domain_url":"https://idcs-example.identity.oraclecloud.com:443"' in rendered_config
    assert "username        => 'database-client-id'" in rendered_config
    assert "password        => 'secret/with+symbols='" in rendered_config
    assert "MAPPED TO 'IAM_OAUTH_CLIENT_ID=demo-client-id'" in rendered_app_identity
    assert "TO APP_DIRECTORY_LOOKUP_ROLE" in rendered_grants
    assert "TO APP_SENSITIVE_LOOKUP_ROLE" in rendered_grants


def test_phase2_validate_sql_avoids_unstable_dictionary_column_names() -> None:
    validate_sql = (SQL_DIR / "11_validate_phase2.sql").read_text(encoding="utf-8")
    assert "all_tab_columns" in validate_sql.lower()
    assert "SELECT *\nFROM dba_application_identities" in validate_sql
    assert "application_identity, mapped_to" not in validate_sql.lower()


def test_validate_sql_checks_principal_name_case_alignment() -> None:
    validate_sql = (SQL_DIR / "06_validate.sql").read_text(encoding="utf-8")
    assert "principal_name_case" in validate_sql
    assert "CASE_MISMATCH" in validate_sql
    assert "ORA_END_USER_CONTEXT.username" in validate_sql


def test_template_rendering_redacts_no_secret_in_source_sql() -> None:
    source = (SQL_DIR / "03_create_end_users.sql").read_text(encoding="utf-8")
    assert "change_me" not in source
    rendered = render_template(
        source,
        DemoConfig(
            host="localhost",
            port=1521,
            service_name="FREEPDB1",
            protocol="tcp",
            wallet_location=None,
            demo_schema="DEMO_HR",
            default_password="local_demo_password",
        ),
    )
    assert 'CREATE END USER "staff_tokyo" IDENTIFIED BY' in rendered
    assert '"local_demo_password"' in rendered


def test_readme_marks_dds_ddl_as_verified() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CREATE DATA ROLE" in readme
    assert "CREATE DATA GRANT" in readme
    assert "確認済みの実行 SQL" in readme
    assert "実機検証できていない" not in readme
