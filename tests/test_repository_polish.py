from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_copy_pasteable_phase1_path_in_order() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = [
        "uv sync",
        "cp .env.example .env",
        "uv run python scripts/run_sql.py --file sql/00_reset.sql",
        "uv run python scripts/run_sql.py --file sql/01_create_schema.sql",
        "uv run python scripts/run_sql.py --file sql/02_create_sample_data.sql",
        "uv run python scripts/run_sql.py --file sql/03_create_end_users.sql",
        "uv run python scripts/run_sql.py --file sql/04_create_data_roles.sql",
        "uv run python scripts/run_sql.py --file sql/05_create_data_grants.sql",
        "uv run python scripts/run_sql.py --file sql/06_validate.sql",
        "uv run pytest",
        "uv run marimo edit notebooks/demo_direct_logon.py",
    ]

    position = -1
    for command in commands:
        next_position = readme.find(command, position + 1)
        assert next_position != -1, f"README is missing command: {command}"
        assert next_position > position, f"README command is out of order: {command}"
        position = next_position


def test_env_example_uses_only_placeholders_for_secret_like_values() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ORACLE_ADMIN_PASSWORD=change_me" in env_example
    assert "DEMO_DEFAULT_PASSWORD=change_me" in env_example
    assert "APP_DB_PASSWORD=change_me" in env_example
    assert "APP_DATABASE_ACCESS_TOKEN=" in env_example
    assert "APP_END_USER_CONTEXT_KEY=" in env_example
    assert "TODO" in env_example


def test_gitignore_excludes_local_env_and_wallet_material() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert ".env.*" in gitignore
    assert "!.env.example" in gitignore
    assert "*.pem" in gitignore
    assert "*.key" in gitignore
    assert "*.p12" in gitignore
    assert "*.sso" in gitignore
    assert "wallet/" in gitignore


def test_dds_sql_files_are_marked_verified_for_26ai() -> None:
    roles = (ROOT / "sql/04_create_data_roles.sql").read_text(encoding="utf-8")
    grants = (ROOT / "sql/05_create_data_grants.sql").read_text(encoding="utf-8")
    assert "Verified against Oracle Deep Data Security Guide 26ai" in roles
    assert "Verified against Oracle Deep Data Security Guide 26ai" in grants
    assert "UNVERIFIED" not in roles
    assert "UNVERIFIED" not in grants

def test_marimo_notebooks_bootstrap_repo_root_for_local_package_imports() -> None:
    for notebook in [
        ROOT / "notebooks/demo_direct_logon.py",
        ROOT / "notebooks/demo_app_mediated.py",
    ]:
        source = notebook.read_text(encoding="utf-8")
        assert 'globals().get("__file__")' in source
        assert '"deepsec_demo"' in source
        assert "sys.path.insert" in source
        assert "from deepsec_demo." in source


def test_readme_mentions_missing_deepsec_demo_package_workaround() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "deepsec-demo" in readme
    assert "PYTHONPATH=. uv run marimo edit notebooks/demo_direct_logon.py" in readme

