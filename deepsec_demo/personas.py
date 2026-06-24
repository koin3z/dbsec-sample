"""Persona metadata for the direct-logon demo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    persona_id: str
    label_ja: str
    db_username: str
    data_roles: tuple[str, ...]
    expected_access_ja: str
    grant_summary_ja: str
    grant_details_ja: tuple[str, ...]


PERSONAS: dict[str, Persona] = {
    "staff_tokyo": Persona(
        persona_id="staff_tokyo",
        label_ja="東京営業メンバー",
        db_username="staff_tokyo",
        data_roles=("employee_role",),
        expected_access_ja="自分の行（employee_id 1001）のみを表示し、機微列も自分の行では表示されます。",
        grant_summary_ja="employee_role が principal_name = ORA_END_USER_CONTEXT.username の行を許可します。",
        grant_details_ja=(
            "employee_role: principal_name = 現在のユーザー の行を参照可能。",
            "自分の社員レコードなので salary_amount、personal_id、phone_number も参照可能。",
        ),
    ),
    "manager_tokyo": Persona(
        persona_id="manager_tokyo",
        label_ja="東京営業マネージャ",
        db_username="manager_tokyo",
        data_roles=("employee_role", "manager_role"),
        expected_access_ja="自分の行と直属部下を表示します。直属部下の personal_id は NULL になります。",
        grant_summary_ja="employee_role に加えて manager_role が manager_principal_name で直属部下を許可します。",
        grant_details_ja=(
            "employee_role: 自分の社員レコードを参照可能。",
            "manager_role: manager_principal_name = 現在のユーザー の行を参照可能。",
            "直属部下の personal_id は許可されないため NULL。",
        ),
    ),
    "manager_japan": Persona(
        persona_id="manager_japan",
        label_ja="日本営業責任者",
        db_username="manager_japan",
        data_roles=("employee_role", "country_manager_role"),
        expected_access_ja="自分の行と、Japan Sales のアクティブな従業員を広く表示します。国スコープの Data Grant 外の機微列は NULL になります。",
        grant_summary_ja="country_manager_role が country = 'Japan' かつ department = 'Sales' の行と限定列を許可します。",
        grant_details_ja=(
            "employee_role: 自分の社員レコードを参照可能。",
            "country_manager_role: Japan / Sales / ACTIVE の行を参照可能。",
            "国スコープでは salary_amount、personal_id、phone_number などの機微列を許可しない。",
        ),
    ),
    "ai_assistant": Persona(
        persona_id="ai_assistant",
        label_ja="AIアシスタント",
        db_username="ai_assistant",
        data_roles=("ai_agent_role",),
        expected_access_ja="最小権限で、アクティブ従業員のディレクトリ相当列のみを表示します。",
        grant_summary_ja="ai_agent_role が employment_status = 'ACTIVE' の行とディレクトリ相当列のみを許可します。",
        grant_details_ja=(
            "ai_agent_role: ACTIVE な社員のディレクトリ情報のみ参照可能。",
            "salary_amount、personal_id、phone_number は許可しない。",
            "AI 風の主体でも、DB が必要最小限のデータだけを返す。",
        ),
    ),
}


def get_persona(persona_id: str) -> Persona:
    """Return a configured persona by id."""
    try:
        return PERSONAS[persona_id]
    except KeyError as exc:
        valid = ", ".join(sorted(PERSONAS))
        raise KeyError(f"Unknown persona_id {persona_id!r}. Valid values: {valid}") from exc


def persona_dropdown_key(persona_id: str) -> str:
    """Return the marimo dropdown option key for a persona id."""
    persona = get_persona(persona_id)
    return f"{persona.label_ja} / {persona_id}"


def persona_dropdown_options() -> dict[str, str]:
    """Return Japanese dropdown labels mapped to persona ids."""
    return {
        f"{persona.label_ja} / {persona_id}": persona_id
        for persona_id, persona in PERSONAS.items()
    }
