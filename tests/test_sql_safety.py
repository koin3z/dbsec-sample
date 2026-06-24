import pytest

from deepsec_demo.sql_safety import UnsafeSqlError, normalize_select_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM demo_hr.employees",
        "SELECT employee_id, display_name FROM demo_hr.employees ORDER BY employee_id;",
        "WITH q AS (SELECT 1 AS x FROM dual) SELECT * FROM q",
    ],
)
def test_allows_select_only_queries(sql: str) -> None:
    assert normalize_select_sql(sql).lower().startswith(("select", "with"))


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM demo_hr.employees",
        "DROP TABLE demo_hr.employees",
        "SELECT * FROM demo_hr.employees; DROP TABLE demo_hr.employees",
        "BEGIN NULL; END;",
        "SELECT * FROM demo_hr.employees -- hidden",
    ],
)
def test_rejects_unsafe_sql(sql: str) -> None:
    with pytest.raises(UnsafeSqlError):
        normalize_select_sql(sql)
