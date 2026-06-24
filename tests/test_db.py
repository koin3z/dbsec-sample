from deepsec_demo.db import direct_logon_username
from deepsec_demo.personas import PERSONAS


def test_direct_logon_username_quotes_lowercase_local_end_user() -> None:
    assert direct_logon_username(PERSONAS["manager_tokyo"]) == '"manager_tokyo"'
