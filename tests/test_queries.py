from deepsec_demo.queries import (
    CANONICAL_EMPLOYEE_QUERY,
    EXAMPLE_QUERIES,
    example_query_key,
    example_query_options,
)
from deepsec_demo.sql_safety import normalize_select_sql


def test_canonical_query_uses_demo_table_and_expected_columns() -> None:
    query = CANONICAL_EMPLOYEE_QUERY.lower()
    assert "from demo_hr.employees" in query
    for column in ["employee_id", "principal_name", "salary_amount", "personal_id"]:
        assert column in query


def test_example_queries_are_select_only() -> None:
    assert EXAMPLE_QUERIES
    for sql in EXAMPLE_QUERIES.values():
        normalized = normalize_select_sql(sql)
        assert normalized.lower().startswith(("select", "with"))


def test_example_query_options_map_to_existing_queries() -> None:
    options = example_query_options()
    assert options
    assert set(options.values()).issubset(EXAMPLE_QUERIES)

def test_example_query_key_matches_marimo_option_name() -> None:
    options = example_query_options()
    key = example_query_key("all_columns")
    assert key == "全列を employee_id 順に表示"
    assert key in options
    assert options[key] == "all_columns"

