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
