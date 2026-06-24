"""Rendering helpers for marimo and console output."""

from __future__ import annotations

import pandas as pd

from deepsec_demo.db import QueryResult
from deepsec_demo.personas import Persona

SENSITIVE_COLUMNS = ("salary_amount", "personal_id", "phone_number")
FOCUS_COLUMNS = (
    "employee_id",
    "display_name",
    "principal_name",
    "manager_principal_name",
    "salary_amount",
    "personal_id",
    "phone_number",
)
DISPLAY_COLUMN_LABELS = {
    "employee_id": "employee_id",
    "display_name": "display_name",
    "principal_name": "principal_name / 自分判定",
    "manager_principal_name": "manager_principal_name / 直属部下判定",
    "salary_amount": "salary_amount / 機密",
    "personal_id": "personal_id / 機密",
    "phone_number": "phone_number / 機密",
}


def result_to_dataframe(result: QueryResult) -> pd.DataFrame:
    """Convert a query result into a pandas DataFrame without changing values."""
    return pd.DataFrame(list(result.rows), columns=list(result.columns))


def result_to_display_dataframe(result: QueryResult, null_label: str = "NULL") -> pd.DataFrame:
    """Convert a query result into a display-only DataFrame with visible NULLs."""
    dataframe = result_to_dataframe(result).astype("object")
    return dataframe.where(pd.notna(dataframe), null_label)


def result_to_sensitive_focus_dataframe(result: QueryResult) -> pd.DataFrame:
    """Build a compact display-only table focused on row identity and sensitive cells."""
    dataframe = result_to_display_dataframe(result)
    available_columns = [column for column in FOCUS_COLUMNS if column in dataframe.columns]
    focus = dataframe.loc[:, available_columns].copy()
    for column in SENSITIVE_COLUMNS:
        if column not in focus.columns:
            focus[column] = "列なし"
    ordered_columns = [column for column in FOCUS_COLUMNS if column in focus.columns]
    return focus.loc[:, ordered_columns].rename(columns=DISPLAY_COLUMN_LABELS)


def persona_markdown(persona: Persona) -> str:
    """Build a compact Japanese explanation for the selected persona."""
    roles = ", ".join(f"`{role}`" for role in persona.data_roles)
    return f"""
### 選択中のペルソナ: {persona.label_ja}

- ペルソナID: `{persona.persona_id}`
- DBユーザー: `{persona.db_username}`
- 想定データロール: {roles}
- 期待される見え方: {persona.expected_access_ja}
""".strip()


def grant_markdown(persona: Persona) -> str:
    """Build a Data Grant concept explanation for the selected persona."""
    details = "\n".join(f"- {line}" for line in persona.grant_details_ja)
    return f"""
### Data Grant の考え方

{details}

この説明は期待値の要約です。実際の行・列・セルの制御は Python ではなく Oracle Database 側の Deep Data Security が強制します。
""".strip()


def column_legend_markdown() -> str:
    """Explain the important columns in the result table."""
    return """
### 列の見方

| 列 | 意味 | デモで見るポイント |
|---|---|---|
| `principal_name` | 社員行が属するローカル・エンドユーザー | `employee_role` の自分行判定に使います。 |
| `manager_principal_name` | 直属上長のローカル・エンドユーザー | `manager_role` の直属部下判定に使います。 |
| `salary_amount` | 報酬情報 | 機密列。許可されないスコープでは `NULL` または列なしになります。 |
| `personal_id` | 個人識別子 | 機密列。`manager_tokyo` の直属部下では `NULL` になる見どころです。 |
| `phone_number` | 連絡先 | 機密列。AI や広域スコープでは返さない想定です。 |

`NULL` は表示用に見やすく置き換えています。元の DB 結果を Python 側で許可・不許可に加工しているわけではありません。
""".strip()


def db_control_markdown(persona: Persona) -> str:
    """Describe what the database is expected to enforce for a persona."""
    controls = {
        "staff_tokyo": (
            "`employee_role`",
            "`principal_name = ORA_END_USER_CONTEXT.username`",
            "自分の社員行だけを返します。自分行なので機密列も表示されます。",
        ),
        "manager_tokyo": (
            "`employee_role` + `manager_role`",
            "自分行: `principal_name = ORA_END_USER_CONTEXT.username` / 直属部下: `manager_principal_name = ORA_END_USER_CONTEXT.username`",
            "自分行の機密列は表示されます。直属部下の `personal_id` は Data Grant で列対象外のため `NULL` になります。",
        ),
        "manager_japan": (
            "`employee_role` + `country_manager_role`",
            "自分行 + `country = 'Japan'`、`department = 'Sales'`、`employment_status = 'ACTIVE'`",
            "Japan Sales の広い行は見えますが、国スコープで許可していない機密列は `NULL` になります。",
        ),
        "ai_assistant": (
            "`ai_agent_role`",
            "`employment_status = 'ACTIVE'`",
            "アクティブ社員のディレクトリ相当列だけを返します。`salary_amount`、`personal_id`、`phone_number` は `NULL` または列なしになります。",
        ),
    }
    roles, row_rule, sensitive_rule = controls[persona.persona_id]
    return f"""
### Database 側で行われる制御

| 観点 | このペルソナでの制御 |
|---|---|
| Data Role | {roles} |
| 行の条件 | {row_rule} |
| 機密列・セル | {sensitive_rule} |

同じ SQL を実行しても、Database が Data Grant を評価して、返す行・列・セル値を決めます。
""".strip()


def result_focus_intro_markdown() -> str:
    """Introduce the compact result table used in the notebook."""
    return """
### 機密列フォーカス

まずこの表を見てください。行の所属を示す列と、機密列だけを抜き出しています。全列の結果は下の折りたたみに残しています。
""".strip()


def result_summary_markdown(
    persona: Persona,
    result: QueryResult,
    executed_at: str,
    elapsed_seconds: float,
) -> str:
    """Build a result summary for a completed query."""
    sensitive_visible = [column for column in SENSITIVE_COLUMNS if column in result.columns]
    sensitive_note = (
        ", ".join(f"`{column}`" for column in sensitive_visible)
        if sensitive_visible
        else "機密列は結果列に含まれていません。"
    )
    return f"""
### 実行結果サマリ

- ペルソナ: `{persona.persona_id}` / {persona.label_ja}
- DBユーザー: `{persona.db_username}`
- 取得行数: **{len(result.rows)}**
- 返却列数: **{len(result.columns)}**
- 機密列の確認対象: {sensitive_note}
- 実行時刻: {executed_at}
- 経過時間: {elapsed_seconds:.3f} 秒
""".strip()


def safe_error_hint(exc: Exception) -> str:
    """Return a concise non-secret hint for common Oracle connection errors."""
    message = str(exc)
    if "ORA-01017" in message:
        return (
            "ORA-01017: local end user の認証または CREATE SESSION 継承を確認してください。"
            " `.env` の `DEMO_DEFAULT_PASSWORD`、`sql/03_create_end_users.sql`、"
            "`sql/04_create_data_roles.sql` が主な確認箇所です。"
        )
    if "DPY-3001" in message:
        return "DPY-3001: 接続先が Native Network Encryption / Data Integrity を要求しています。Thick mode 設定を確認してください。"
    if "DPI-1047" in message:
        return "DPI-1047: Oracle Client libraries を読み込めていません。Instant Client とライブラリ検索パスを確認してください。"
    return "詳細は `scripts/smoke_test.py` で同じペルソナを実行して確認してください。"


def query_error_markdown(persona: Persona, exc: Exception) -> str:
    """Build a safe query error message without credentials."""
    return f"""
### 問い合わせに失敗しました

- ペルソナ: `{persona.persona_id}` / {persona.label_ja}
- DBユーザー: `{persona.db_username}`
- エラー種別: `{type(exc).__name__}`
- 確認ヒント: {safe_error_hint(exc)}

`.env`、SQL セットアップ順、対象ユーザー作成、Data Grant 設定を確認してください。パスワードなどの秘密情報は表示していません。
""".strip()


def troubleshooting_markdown() -> str:
    """Return common troubleshooting notes for the notebook."""
    return """
### トラブルシューティング

- `.env` がない場合は `.env.example` をコピーして Oracle 接続情報を設定してください。
- Oracle へ接続できない場合は `ORACLE_HOST`、`ORACLE_PORT`、`ORACLE_SERVICE_NAME`、ウォレット設定を確認してください。
- ペルソナでログオンできない場合は `sql/03_create_end_users.sql` の実行状況を確認してください。
- 全ペルソナで同じ結果が返る場合は、Deep Data Security の Data Role / Data Grant が未設定、または想定と違う DB ユーザーで接続している可能性があります。
- この notebook は結果を Python 側でフィルタしません。表示差分は DB 側の制御として確認してください。
""".strip()


def highlights_markdown() -> str:
    """Return the fixed demo highlights."""
    return """
### 見どころ

- `staff_tokyo` は自分の社員レコードのみ参照できます。
- `manager_tokyo` は直属部下の行も参照できますが、部下の `personal_id` は NULL になります。
- `manager_japan` は日本営業配下の行を広く参照できますが、機微列は制限されます。
- `ai_assistant` は社員検索に必要な最小限の列だけ参照できます。
""".strip()
