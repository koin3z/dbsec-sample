from deepsec_demo.personas import PERSONAS, persona_dropdown_key, persona_dropdown_options


def test_required_personas_exist() -> None:
    assert set(PERSONAS) == {
        "staff_tokyo",
        "manager_tokyo",
        "manager_japan",
        "ai_assistant",
    }


def test_personas_have_required_metadata() -> None:
    for persona_id, persona in PERSONAS.items():
        assert persona.persona_id == persona_id
        assert persona.db_username
        assert persona.label_ja
        assert persona.data_roles
        assert persona.expected_access_ja
        assert persona.grant_summary_ja
        assert persona.grant_details_ja


def test_personas_do_not_use_realistic_old_example_names() -> None:
    serialized = " ".join(
        " ".join(
            [
                persona.persona_id,
                persona.db_username,
                persona.label_ja,
                persona.expected_access_ja,
                persona.grant_summary_ja,
                *persona.grant_details_ja,
            ]
        )
        for persona in PERSONAS.values()
    ).lower()
    assert "ebaker" not in serialized
    assert "manderson" not in serialized


def test_persona_dropdown_options_include_label_and_id() -> None:
    options = persona_dropdown_options()
    assert options["東京営業メンバー / staff_tokyo"] == "staff_tokyo"
    assert set(options.values()) == set(PERSONAS)


def test_persona_db_usernames_are_quoted_lowercase_end_user_names() -> None:
    assert {persona.db_username for persona in PERSONAS.values()} == {
        "staff_tokyo",
        "manager_tokyo",
        "manager_japan",
        "ai_assistant",
    }

def test_persona_dropdown_key_matches_marimo_option_name() -> None:
    options = persona_dropdown_options()
    key = persona_dropdown_key("staff_tokyo")
    assert key == "東京営業メンバー / staff_tokyo"
    assert key in options
    assert options[key] == "staff_tokyo"

