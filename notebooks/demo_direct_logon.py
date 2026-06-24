import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    from datetime import datetime
    from time import perf_counter

    from pathlib import Path
    import sys

    # marimo may execute notebook cells with notebooks/ as the working directory.
    # Add the repository root so local package imports such as deepsec_demo work.
    _notebook_file = globals().get("__file__")
    _repo_root = (
        Path(_notebook_file).resolve().parents[1]
        if _notebook_file
        else Path.cwd().resolve()
    )
    if not (_repo_root / "deepsec_demo").exists() and (
        _repo_root.parent / "deepsec_demo"
    ).exists():
        _repo_root = _repo_root.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    import marimo as mo

    from deepsec_demo.config import ConfigError, load_config
    from deepsec_demo.db import query_as_persona
    from deepsec_demo.personas import get_persona, persona_dropdown_key, persona_dropdown_options
    from deepsec_demo.queries import (
        CANONICAL_EMPLOYEE_QUERY,
        EXAMPLE_QUERIES,
        example_query_key,
        example_query_options,
    )
    from deepsec_demo.render import (
        column_legend_markdown,
        db_control_markdown,
        grant_markdown,
        highlights_markdown,
        persona_markdown,
        query_error_markdown,
        result_focus_intro_markdown,
        result_summary_markdown,
        result_to_display_dataframe,
        result_to_sensitive_focus_dataframe,
        troubleshooting_markdown,
    )
    from deepsec_demo.sql_safety import UnsafeSqlError, normalize_select_sql

    return (
        CANONICAL_EMPLOYEE_QUERY,
        ConfigError,
        EXAMPLE_QUERIES,
        UnsafeSqlError,
        column_legend_markdown,
        datetime,
        db_control_markdown,
        example_query_key,
        example_query_options,
        get_persona,
        grant_markdown,
        highlights_markdown,
        load_config,
        mo,
        normalize_select_sql,
        perf_counter,
        persona_dropdown_key,
        persona_dropdown_options,
        persona_markdown,
        query_as_persona,
        query_error_markdown,
        result_focus_intro_markdown,
        result_summary_markdown,
        result_to_display_dataframe,
        result_to_sensitive_focus_dataframe,
        troubleshooting_markdown,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Oracle Deep Data Security デモ: 同じSQL、違う見え方

    このデモでは、実行するSQL文は変えずに、実行ユーザーだけを切り替えます。
    Phase 1 では application-mediated ではなく、選択した local end user で direct logon します。
    返ってくる行・列・セルの違いは、Python側のフィルタではなく、Oracle Database 側の Deep Data Security Data Grant によって決まります。

    ```text
    Persona selection
      -> Database session / end-user context
      -> Same SELECT statement
      -> Deep Data Security Data Grants
      -> Different rows, columns, and cells returned
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo, persona_dropdown_key, persona_dropdown_options):
    # Dropdown options are Japanese labels mapped to persona ids.
    # marimo expects the initial value to be the option key, not the mapped id.
    persona_select = mo.ui.dropdown(
        options=persona_dropdown_options(),
        value=persona_dropdown_key("staff_tokyo"),
        label="ペルソナ",
        full_width=True,
    )
    mo.vstack([mo.md("## 1. ペルソナ選択"), persona_select])
    return (persona_select,)


@app.cell(hide_code=True)
def _(get_persona, grant_markdown, mo, persona_markdown, persona_select):
    # persona_select.value is the persona id, for example "manager_tokyo".
    # This resolves display metadata and the local end-user name used for logon.
    selected_persona = get_persona(persona_select.value)
    mo.vstack(
        [
            mo.callout(mo.md(persona_markdown(selected_persona)), kind="info"),
            mo.md(grant_markdown(selected_persona)),
        ]
    )
    return (selected_persona,)


@app.cell(hide_code=True)
def _(CANONICAL_EMPLOYEE_QUERY, mo):
    # The canonical SQL is shown verbatim and is shared by every persona.
    # Differences in results should therefore come from Database-side DDS only.
    run_canonical = mo.ui.run_button(label="共通SQLを実行", kind="success")
    mo.vstack(
        [
            mo.md("## 2. 実行するSQL: すべてのペルソナで同じ"),
            mo.md(f"```sql\n{CANONICAL_EMPLOYEE_QUERY}\n```"),
            run_canonical,
        ]
    )
    return (run_canonical,)


@app.cell(hide_code=True)
def _(
    CANONICAL_EMPLOYEE_QUERY,
    ConfigError,
    UnsafeSqlError,
    column_legend_markdown,
    datetime,
    db_control_markdown,
    load_config,
    mo,
    normalize_select_sql,
    perf_counter,
    query_as_persona,
    query_error_markdown,
    result_focus_intro_markdown,
    result_summary_markdown,
    result_to_display_dataframe,
    result_to_sensitive_focus_dataframe,
    run_canonical,
    selected_persona,
):
    mo.stop(
        not run_canonical.value,
        mo.md("共通SQLはボタンを押すまで実行されません。"),
    )
    try:
        # Load Oracle connection settings from .env. Admin credentials are not used here.
        _config = load_config()
        # Keep the notebook SELECT-only; this is for demo safety, not authorization.
        _canonical_sql = normalize_select_sql(CANONICAL_EMPLOYEE_QUERY)
        _started = perf_counter()
        # Phase 1 direct logon: connect as the selected local end user,
        # for example "manager_tokyo", then run the same SELECT.
        _canonical_result = query_as_persona(_config, selected_persona, _canonical_sql)
        _elapsed_seconds = perf_counter() - _started
        _executed_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        canonical_output = mo.vstack(
            [
                mo.md(result_summary_markdown(selected_persona, _canonical_result, _executed_at, _elapsed_seconds)),
                # Explain the Data Role and Data Grant predicates before showing rows.
                mo.callout(mo.md(db_control_markdown(selected_persona)), kind="info"),
                mo.md(result_focus_intro_markdown()),
                # Display-only focus table: no rows or cells are filtered by Python.
                result_to_sensitive_focus_dataframe(_canonical_result),
                mo.accordion(
                    {
                        "全列の結果": result_to_display_dataframe(_canonical_result),
                        "列の見方": mo.md(column_legend_markdown()),
                    }
                ),
            ]
        )
    except UnsafeSqlError as exc:
        canonical_output = mo.callout(
            mo.md(f"共通SQLの検証に失敗しました: `{exc}`"),
            kind="danger",
        )
    except ConfigError as exc:
        canonical_output = mo.callout(
            mo.md(
                f"""
                ### 設定を読み込めませんでした

                `{exc}`

                `.env.example` を `.env` にコピーし、Oracle 接続情報とデモユーザーのパスワードを設定してください。
                """
            ),
            kind="warn",
        )
    except Exception as exc:
        canonical_output = mo.callout(
            mo.md(query_error_markdown(selected_persona, exc)),
            kind="danger",
        )
    canonical_output
    return


@app.cell(hide_code=True)
def _(example_query_key, example_query_options, mo):
    # Select the sample query in one cell. marimo forbids reading .value
    # from a UI element in the same cell that creates it.
    example_select = mo.ui.dropdown(
        options=example_query_options(),
        value=example_query_key("all_columns"),
        label="SQL例",
        full_width=True,
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 3. 実験用 SELECT-only パネル

                SELECT文のみ実行できます。これはデモを安全に進めるための制限です。アクセス制御の本体はDB側の Deep Data Security です。
                """
            ),
            example_select,
        ]
    )
    return (example_select,)


@app.cell(hide_code=True)
def _(EXAMPLE_QUERIES, example_select, mo):
    # Read example_select.value in this separate cell and seed the editable SQL.
    experiment_sql = mo.ui.text_area(
        value=EXAMPLE_QUERIES[example_select.value],
        label="実験用SQL入力欄",
        rows=9,
        full_width=True,
    )
    run_experiment = mo.ui.run_button(label="実験用SQLを実行", kind="neutral")
    mo.vstack([experiment_sql, run_experiment])
    return experiment_sql, run_experiment


@app.cell(hide_code=True)
def _(
    ConfigError,
    UnsafeSqlError,
    column_legend_markdown,
    datetime,
    db_control_markdown,
    experiment_sql,
    load_config,
    mo,
    normalize_select_sql,
    perf_counter,
    query_as_persona,
    query_error_markdown,
    result_focus_intro_markdown,
    result_summary_markdown,
    result_to_display_dataframe,
    result_to_sensitive_focus_dataframe,
    run_experiment,
    selected_persona,
):
    mo.stop(
        not run_experiment.value,
        mo.md("実験用SQLはボタンを押すまで実行されません。"),
    )
    try:
        _config = load_config()
        # The experiment panel allows only a single SELECT/WITH statement.
        _experiment_sql = normalize_select_sql(experiment_sql.value)
        _started = perf_counter()
        # Execute the edited SELECT through the same selected local end-user logon.
        _experiment_result = query_as_persona(_config, selected_persona, _experiment_sql)
        _elapsed_seconds = perf_counter() - _started
        _executed_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        experiment_output = mo.vstack(
            [
                mo.md(result_summary_markdown(selected_persona, _experiment_result, _executed_at, _elapsed_seconds)),
                mo.callout(mo.md(db_control_markdown(selected_persona)), kind="info"),
                mo.md(result_focus_intro_markdown()),
                result_to_sensitive_focus_dataframe(_experiment_result),
                mo.accordion(
                    {
                        "全列の結果": result_to_display_dataframe(_experiment_result),
                        "列の見方": mo.md(column_legend_markdown()),
                    }
                ),
            ]
        )
    except UnsafeSqlError as exc:
        experiment_output = mo.callout(
            mo.md(f"SQL は SELECT の単一文だけ実行できます: `{exc}`"),
            kind="warn",
        )
    except ConfigError as exc:
        experiment_output = mo.callout(
            mo.md(
                f"""
                ### 設定を読み込めませんでした

                `{exc}`

                `.env.example` を `.env` にコピーし、Oracle 接続情報とデモユーザーのパスワードを設定してください。
                """
            ),
            kind="warn",
        )
    except Exception as exc:
        experiment_output = mo.callout(
            mo.md(query_error_markdown(selected_persona, exc)),
            kind="danger",
        )
    experiment_output
    return


@app.cell(hide_code=True)
def _(highlights_markdown, mo, troubleshooting_markdown):
    mo.accordion(
        {
            "見どころ": mo.md(highlights_markdown()),
            "トラブルシューティング": mo.md(troubleshooting_markdown()),
        }
    )
    return


if __name__ == "__main__":
    app.run()
