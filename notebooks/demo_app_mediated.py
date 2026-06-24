import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell
def _():
    from datetime import datetime
    from time import perf_counter

    from pathlib import Path
    import sys

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

    from deepsec_demo.app_mediated import query_as_end_user_via_app
    from deepsec_demo.config import ConfigError, load_app_mediated_config
    from deepsec_demo.personas import get_persona, persona_dropdown_key, persona_dropdown_options
    from deepsec_demo.queries import CANONICAL_EMPLOYEE_QUERY
    from deepsec_demo.render import (
        grant_markdown,
        persona_markdown,
        result_to_display_dataframe,
    )
    from deepsec_demo.sql_safety import UnsafeSqlError, normalize_select_sql

    return (
        CANONICAL_EMPLOYEE_QUERY,
        ConfigError,
        UnsafeSqlError,
        datetime,
        get_persona,
        grant_markdown,
        load_app_mediated_config,
        mo,
        normalize_select_sql,
        perf_counter,
        persona_dropdown_key,
        persona_dropdown_options,
        persona_markdown,
        query_as_end_user_via_app,
        result_to_display_dataframe,
    )


@app.cell
def _(mo):
    mo.md("""
    # Oracle Deep Data Security Phase 2: application-mediated

    この notebook は共有アプリケーション DB ユーザーで接続し、選択したエンドユーザーの security context を問い合わせ直前に付与します。問い合わせ後は必ず context を解除し、接続に前回ユーザーの context を残さないことを確認します。

    ```text
    marimo / Python app
      -> shared DB connection user
      -> attach selected end-user security context
      -> execute the same SELECT
      -> clear end-user security context
      -> close or reuse the connection
    ```
    """)
    return


@app.cell
def _(ConfigError, load_app_mediated_config, mo):
    try:
        _demo_config, _app_config = load_app_mediated_config()
        _token_status = "設定済み" if _app_config.database_access_token else "未設定"
        _key_status = "設定済み" if _app_config.end_user_context_key else "未設定"
        _attributes_status = "設定済み" if _app_config.context_attributes else "未設定"
        _status_kind = (
            "info"
            if _app_config.database_access_token and _app_config.end_user_context_key
            else "warn"
        )
        app_config_status = mo.callout(
            mo.md(
                f"""
                ### Phase 2 設定

                - 共有 DB ユーザー: `{_app_config.app_username}`
                - security context mode: `{_app_config.security_context_mode}`
                - driver mode: `{_demo_config.driver_mode}`
                - database access token: `{_token_status}`
                - local end-user context key: `{_key_status}`
                - context attributes: `{_attributes_status}`

                token と context key の実値は表示しません。未設定の場合、実行時に設定エラーとして止まります。
                """
            ),
            kind=_status_kind,
        )
    except ConfigError as exc:
        app_config_status = mo.callout(
            mo.md(
                f"""
                ### Phase 2 設定を読み込めませんでした

                `{exc}`

                `.env.example` の Phase 2 セクションを `.env` に反映してください。token や context key は対象環境の公式手順で取得した値を設定します。
                """
            ),
            kind="warn",
        )
    app_config_status
    return


@app.cell
def _(mo, persona_dropdown_key, persona_dropdown_options):
    app_persona_select = mo.ui.dropdown(
        options=persona_dropdown_options(),
        value=persona_dropdown_key("staff_tokyo"),
        label="エンドユーザー",
        full_width=True,
    )
    mo.vstack([mo.md("## 1. エンドユーザー選択"), app_persona_select])
    return (app_persona_select,)


@app.cell
def _(app_persona_select, get_persona, grant_markdown, mo, persona_markdown):
    selected_end_user = get_persona(app_persona_select.value)
    mo.vstack(
        [
            mo.callout(mo.md(persona_markdown(selected_end_user)), kind="info"),
            mo.md(grant_markdown(selected_end_user)),
        ]
    )
    return (selected_end_user,)


@app.cell
def _(CANONICAL_EMPLOYEE_QUERY, mo):
    run_app_query = mo.ui.run_button(label="app-mediated 共通SQLを実行", kind="success")
    mo.vstack(
        [
            mo.md(
                """
                ## 2. 実行するSQL

                direct logon 版と同じ SELECT を使います。アプリ側で行・列・セルを加工せず、Oracle Database 側の Deep Data Security Data Grant が見え方を決めます。
                """
            ),
            mo.md(f"```sql\n{CANONICAL_EMPLOYEE_QUERY}\n```"),
            run_app_query,
        ]
    )
    return (run_app_query,)


@app.cell
def _(
    CANONICAL_EMPLOYEE_QUERY,
    ConfigError,
    UnsafeSqlError,
    datetime,
    load_app_mediated_config,
    mo,
    normalize_select_sql,
    perf_counter,
    query_as_end_user_via_app,
    result_to_display_dataframe,
    run_app_query,
    selected_end_user,
):
    mo.stop(
        not run_app_query.value,
        mo.md("app-mediated 共通SQLはボタンを押すまで実行されません。"),
    )
    try:
        _demo_config, _app_config = load_app_mediated_config()
        _canonical_sql = normalize_select_sql(CANONICAL_EMPLOYEE_QUERY)
        _started = perf_counter()
        _app_result = query_as_end_user_via_app(
            _demo_config,
            _app_config,
            selected_end_user,
            _canonical_sql,
        )
        _elapsed_seconds = perf_counter() - _started
        _executed_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        app_query_output = mo.vstack(
            [
                mo.md(
                    f"""
                    ### 実行結果サマリ

                    - 共有 DB ユーザー: `{_app_result.shared_db_user}`
                    - 選択エンドユーザー: `{_app_result.end_user}` / {selected_end_user.label_ja}
                    - context 付与済み: `{_app_result.context_attached}`
                    - 実行後 context 解除済み: `{_app_result.context_cleared}`
                    - 取得行数: **{len(_app_result.rows)}**
                    - 実行時刻: {_executed_at}
                    - 経過時間: {_elapsed_seconds:.3f} 秒
                    """
                ),
                result_to_display_dataframe(_app_result),
            ]
        )
    except UnsafeSqlError as exc:
        app_query_output = mo.callout(
            mo.md(f"共通SQLの検証に失敗しました: `{exc}`"),
            kind="danger",
        )
    except ConfigError as exc:
        app_query_output = mo.callout(
            mo.md(
                f"""
                ### Phase 2 設定エラー

                `{exc}`

                `.env` の Phase 2 設定、`ORACLE_DRIVER_MODE=thin`、database access token、local end-user context key を確認してください。
                """
            ),
            kind="warn",
        )
    except Exception as exc:
        app_query_output = mo.callout(
            mo.md(
                f"""
                ### app-mediated 問い合わせに失敗しました

                - 選択エンドユーザー: `{selected_end_user.db_username}` / {selected_end_user.label_ja}
                - エラー種別: `{type(exc).__name__}`

                秘密情報、token、security context payload は表示していません。共有 DB ユーザー、Phase 1 SQL セットアップ、Data Role / Data Grant、対象環境の security context provider 設定を確認してください。
                """
            ),
            kind="danger",
        )
    app_query_output
    return


@app.cell
def _(mo):
    mo.accordion(
        {
            "Phase 2 の前提": mo.md(
                """
                - Phase 1 の SQL セットアップが完了していること。
                - `APP_DATABASE_ACCESS_TOKEN` と `APP_END_USER_CONTEXT_KEY` は対象環境の公式手順で取得した値を使うこと。
                - この notebook は production token cache、OAuth flow、接続プール、IAM 管理自動化を実装しません。
                - 前のユーザーの context が接続に残ると権限境界が崩れるため、実行後の clear 状態を必ず確認します。
                """
            ),
            "接続モード": mo.md(
                """
                python-oracledb の end-user security context payload API は Thin mode を前提にしています。接続先が Native Network Encryption などで Thick mode を必須にする場合は、Phase 2 用に Thin mode で接続できるサービスまたは Oracle 公式手順に沿った別構成を使います。
                """
            ),
        }
    )
    return


if __name__ == "__main__":
    app.run()
