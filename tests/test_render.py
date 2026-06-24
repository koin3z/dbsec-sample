from deepsec_demo.db import QueryResult
from deepsec_demo.personas import PERSONAS
from deepsec_demo.render import (
    column_legend_markdown,
    db_control_markdown,
    grant_markdown,
    result_summary_markdown,
    result_to_dataframe,
    result_to_display_dataframe,
    result_to_sensitive_focus_dataframe,
    safe_error_hint,
)


def test_result_to_dataframe_preserves_none() -> None:
    result = QueryResult(columns=("employee_id", "personal_id"), rows=((1001, None),))
    dataframe = result_to_dataframe(result)
    assert dataframe.loc[0, "personal_id"] is None


def test_result_to_display_dataframe_marks_null_without_filtering_rows() -> None:
    result = QueryResult(columns=("employee_id", "personal_id"), rows=((1001, None),))
    dataframe = result_to_display_dataframe(result)
    assert len(dataframe) == 1
    assert dataframe.loc[0, "personal_id"] == "NULL"


def test_result_summary_mentions_persona_and_row_count() -> None:
    persona = PERSONAS["manager_tokyo"]
    result = QueryResult(columns=("employee_id", "personal_id"), rows=((1001, None), (1003, "SYN")))
    summary = result_summary_markdown(persona, result, "2026-06-23 00:00:00 UTC", 0.1)
    assert "manager_tokyo" in summary
    assert "取得行数: **2**" in summary
    assert "personal_id" in summary


def test_grant_markdown_says_db_enforces_access() -> None:
    markdown = grant_markdown(PERSONAS["ai_assistant"])
    assert "Oracle Database" in markdown
    assert "Python" in markdown
    assert "salary_amount" in markdown

def test_safe_error_hint_mentions_ora_01017_checks() -> None:
    hint = safe_error_hint(Exception("ORA-01017: invalid credential or not authorized"))
    assert "ORA-01017" in hint
    assert "DEMO_DEFAULT_PASSWORD" in hint
    assert "sql/03_create_end_users.sql" in hint
    assert "sql/04_create_data_roles.sql" in hint

def test_sensitive_focus_dataframe_highlights_sensitive_columns() -> None:
    result = QueryResult(
        columns=("employee_id", "display_name", "salary_amount", "personal_id"),
        rows=((1001, "Tokyo Staff", 7200000, None),),
    )
    dataframe = result_to_sensitive_focus_dataframe(result)
    assert "salary_amount / 機密" in dataframe.columns
    assert "personal_id / 機密" in dataframe.columns
    assert "phone_number / 機密" in dataframe.columns
    assert dataframe.loc[0, "personal_id / 機密"] == "NULL"
    assert dataframe.loc[0, "phone_number / 機密"] == "列なし"


def test_db_control_markdown_explains_database_side_controls() -> None:
    markdown = db_control_markdown(PERSONAS["manager_tokyo"])
    assert "Database 側" in markdown
    assert "manager_role" in markdown
    assert "personal_id" in markdown
    assert "NULL" in markdown


def test_column_legend_mentions_sensitive_columns() -> None:
    markdown = column_legend_markdown()
    assert "salary_amount" in markdown
    assert "personal_id" in markdown
    assert "phone_number" in markdown
    assert "Python 側" in markdown

