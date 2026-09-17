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

    from deepsec_demo.app_mediated import (
        build_end_user_context_provider,
        query_as_end_user_via_app,
    )
    from deepsec_demo.app_mediated_status import check_shared_app_connection
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
        check_shared_app_connection,
        datetime,
        get_persona,
        grant_markdown,
        load_app_mediated_config,
        mo,
        build_end_user_context_provider,
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

    この notebook は共有アプリケーション DB ユーザーで接続し、Identity Domain の OAuth client credentials で取得した database-access token を使って、選択したエンドユーザーの DDS security context を attach する Phase 2 デモです。provider が未設定の場合は fail-closed し、protected query は実行しません。

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
def _(ConfigError, build_end_user_context_provider, load_app_mediated_config, mo):
    try:
        _demo_config, _app_config = load_app_mediated_config()
        _phase2_provider = build_end_user_context_provider(_app_config)
        _attributes_status = "設定済み" if _app_config.context_attributes else "未設定"
        _provider_note = (
            "Identity Domain client credentials provider が設定されています。protected query 実行前に `ORA_END_USER_CONTEXT.username` を検証します。"
            if _phase2_provider.supports_real_dds_context
            else f"provider は未有効です: `{getattr(_phase2_provider, 'disabled_reason', 'provider disabled')}`"
        )
        app_config_status = mo.callout(
            mo.md(
                f"""
                ### Phase 2 設定

                - 共有 DB ユーザー: `{_app_config.app_username}`
                - DB auth mode: `{_app_config.app_auth_mode}`
                - security context mode: `{_app_config.security_context_mode}`
                - driver mode: `{_demo_config.driver_mode}`
                - context provider: `{_phase2_provider.mode}`
                - provider verified: `{_phase2_provider.supports_real_dds_context}`
                - application data roles: `{', '.join(getattr(_phase2_provider, 'data_roles', ())) or '未設定'}`
                - context attributes: `{_attributes_status}`

                {_provider_note}
                """
            ),
            kind="info" if _phase2_provider.supports_real_dds_context else "warn",
        )
    except ConfigError as exc:
        app_config_status = mo.callout(
            mo.md(
                f"""
                ### Phase 2 設定を読み込めませんでした

                `{exc}`

                `.env.example` の Phase 2 セクションを `.env` に反映してください。access token 自体は `.env` に保存しません。
                """
            ),
            kind="warn",
        )
    app_config_status
    return

@app.cell
def _(mo):
    check_app_connection = mo.ui.run_button(
        label="共有DBユーザー接続を確認",
        kind="neutral",
    )
    mo.vstack(
        [
            mo.md(
                """
                ## 1. 共有DBユーザー接続確認

                `DEEPSEC_APP` で接続できることだけを確認します。保護対象テーブルへの SELECT は実行しません。
                """
            ),
            check_app_connection,
        ]
    )
    return (check_app_connection,)


@app.cell
def _(
    ConfigError,
    check_app_connection,
    check_shared_app_connection,
    load_app_mediated_config,
    mo,
):
    mo.stop(
        not check_app_connection.value,
        mo.md("共有DBユーザー接続確認はボタンを押すまで実行されません。"),
    )
    try:
        _demo_config, _app_config = load_app_mediated_config()
        _status = check_shared_app_connection(_demo_config, _app_config)
        _dds_detail = (
            f"- ORA_END_USER_CONTEXT.username query error: `{_status.dds_query_error}`"
            if _status.dds_query_error
            else f"- ORA_END_USER_CONTEXT.username: `{_status.dds_username}`"
        )
        app_connection_status = mo.callout(
            mo.md(
                f"""
                ### 共有DBユーザー接続ステータス

                - expected shared DB user: `{_status.shared_db_user}`
                - session user: `{_status.session_user}`
                - current user: `{_status.current_user}`
                - connected as expected: `{_status.connected_as_expected}`
                {_dds_detail}

                active DDS context がない状態で protected SELECT は実行しません。
                """
            ),
            kind="info" if _status.connected_as_expected else "warn",
        )
    except ConfigError as exc:
        app_connection_status = mo.callout(
            mo.md(f"Phase 2 設定エラー: `{exc}`"),
            kind="warn",
        )
    except Exception as exc:
        app_connection_status = mo.callout(
            mo.md(
                f"共有DBユーザー接続確認に失敗しました: `{type(exc).__name__}: {exc}`"
            ),
            kind="danger",
        )
    app_connection_status
    return


@app.cell
def _(mo, persona_dropdown_key, persona_dropdown_options):
    app_persona_select = mo.ui.dropdown(
        options=persona_dropdown_options(),
        value=persona_dropdown_key("staff_tokyo"),
        label="エンドユーザー",
        full_width=True,
    )
    mo.vstack([mo.md("## 2. エンドユーザー選択"), app_persona_select])
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
def _(
    CANONICAL_EMPLOYEE_QUERY,
    ConfigError,
    build_end_user_context_provider,
    load_app_mediated_config,
    mo,
):
    try:
        _demo_config, _app_config = load_app_mediated_config()
        _phase2_provider = build_end_user_context_provider(_app_config)
        _provider_ready = _phase2_provider.supports_real_dds_context
        _disabled_reason = getattr(_phase2_provider, "disabled_reason", "provider disabled")
    except ConfigError as exc:
        _provider_ready = False
        _disabled_reason = str(exc)
    run_app_query = mo.ui.run_button(
        label="app-mediated 共通SQLを実行" if _provider_ready else "app-mediated 共通SQLを実行（未設定）",
        kind="neutral" if _provider_ready else "warn",
        disabled=not _provider_ready,
        tooltip="Identity Domain provider 設定済み" if _provider_ready else _disabled_reason,
    )
    _execution_note = (
        "Identity Domain provider が設定されているため、実行時に context attach / verify / query / clear を行います。"
        if _provider_ready
        else "Identity Domain provider が未設定のため、ボタンは無効です。"
    )
    mo.vstack(
        [
            mo.md(
                f"""
                ## 3. 実行するSQL

                direct logon 版と同じ SELECT を使います。アプリ側で行・列・セルを加工せず、Oracle Database 側の Deep Data Security Data Grant が見え方を決めます。{_execution_note}
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

                `.env` の Phase 2 設定を確認してください。access token 自体は `.env` に保存しません。
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

                秘密情報や security context payload は表示していません。共有 DB ユーザー、Phase 1 SQL セットアップ、Data Role / Data Grant、対象環境の context 注入方式を確認してください。
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
                - この notebook は Identity Domain client credentials で database-access token を取得し、公式 python-oracledb API で DDS context payload を attach します。
                - production token cache、接続プール、IAM 管理自動化は実装しません。
                - 前のユーザーの context が接続に残ると権限境界が崩れるため、実行後の clear 状態を必ず確認します。
                """
            ),
            "接続モード": mo.md(
                """
                python-oracledb の application-mediated DDS API は EndUserSecurityContext payload を connection に attach する方式です。このデモでは local database user の identity tuple と Identity Domain database-access token を使います。
                """
            ),
        }
    )
    return


if __name__ == "__main__":
    app.run()
