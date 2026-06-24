"""SQL snippets used by the demo UI and smoke tests."""

from __future__ import annotations

from dataclasses import dataclass

DEMO_SCHEMA = "demo_hr"

CANONICAL_EMPLOYEE_QUERY = """
SELECT
  employee_id,
  principal_name,
  display_name,
  job_title,
  department,
  country,
  city,
  manager_principal_name,
  employment_status,
  salary_amount,
  personal_id,
  phone_number
FROM demo_hr.employees
ORDER BY employee_id
""".strip()


@dataclass(frozen=True)
class ExampleQuery:
    query_id: str
    label_ja: str
    sql: str


EXAMPLE_QUERY_LIST: tuple[ExampleQuery, ...] = (
    ExampleQuery(
        query_id="all_columns",
        label_ja="全列を employee_id 順に表示",
        sql="SELECT * FROM demo_hr.employees ORDER BY employee_id",
    ),
    ExampleQuery(
        query_id="sensitive_focus",
        label_ja="salary_amount と personal_id を確認",
        sql="""
SELECT
  employee_id,
  display_name,
  salary_amount,
  personal_id
FROM demo_hr.employees
ORDER BY employee_id
""".strip(),
    ),
    ExampleQuery(
        query_id="personal_id_only",
        label_ja="personal_id だけを確認",
        sql="SELECT personal_id FROM demo_hr.employees ORDER BY employee_id",
    ),
    ExampleQuery(
        query_id="directory",
        label_ja="ディレクトリ相当列だけを確認",
        sql="""
SELECT
  employee_id,
  display_name,
  job_title,
  department,
  country,
  city,
  employment_status
FROM demo_hr.employees
ORDER BY employee_id
""".strip(),
    ),
)

EXAMPLE_QUERIES: dict[str, str] = {
    "canonical": CANONICAL_EMPLOYEE_QUERY,
    **{example.query_id: example.sql for example in EXAMPLE_QUERY_LIST},
}


def example_query_key(query_id: str) -> str:
    """Return the marimo dropdown option key for an example query id."""
    for example in EXAMPLE_QUERY_LIST:
        if example.query_id == query_id:
            return example.label_ja
    valid = ", ".join(sorted(example.query_id for example in EXAMPLE_QUERY_LIST))
    raise KeyError(f"Unknown query_id {query_id!r}. Valid values: {valid}")


def example_query_options() -> dict[str, str]:
    """Return Japanese dropdown labels mapped to example query ids."""
    return {example.label_ja: example.query_id for example in EXAMPLE_QUERY_LIST}
