from deepsec_demo.personas import PERSONAS


def test_staff_tokyo_access_mentions_own_row() -> None:
    assert "自分の行" in PERSONAS["staff_tokyo"].expected_access_ja


def test_manager_tokyo_access_mentions_direct_reports_and_null_personal_id() -> None:
    expected = PERSONAS["manager_tokyo"].expected_access_ja
    assert "直属部下" in expected
    assert "personal_id" in expected
    assert "NULL" in expected


def test_manager_japan_access_mentions_japan_sales_scope() -> None:
    expected = PERSONAS["manager_japan"].expected_access_ja
    assert "Japan Sales" in expected


def test_ai_assistant_access_mentions_least_privilege() -> None:
    expected = PERSONAS["ai_assistant"].expected_access_ja
    assert "最小権限" in expected
