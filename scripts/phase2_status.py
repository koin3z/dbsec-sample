"""Check Phase 2 shared app DB user connectivity without protected queries."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepsec_demo.app_mediated import build_end_user_context_provider
from deepsec_demo.app_mediated_status import check_shared_app_connection
from deepsec_demo.config import ConfigError, load_app_mediated_config


def _display(value: object) -> str:
    return "<none>" if value is None else str(value)


def main() -> int:
    try:
        demo_config, app_config = load_app_mediated_config()
        status = check_shared_app_connection(demo_config, app_config)
        provider = build_end_user_context_provider(app_config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Exception as exc:
        print(f"Phase 2 shared app connection failed: {type(exc).__name__}: {exc}")
        return 1

    print(f"shared_db_user={status.shared_db_user}")
    print(f"session_user={_display(status.session_user)}")
    print(f"current_user={_display(status.current_user)}")
    print(f"connected_as_expected={status.connected_as_expected}")
    print(f"ora_end_user_context_username={_display(status.dds_username)}")
    if status.dds_query_error:
        print(f"ora_end_user_context_query_error={status.dds_query_error}")
    print(f"context_provider={provider.mode}")
    print(f"protected_query_enabled={provider.supports_real_dds_context}")
    if provider.supports_real_dds_context:
        print("protected_query_note=enabled after per-query ORA_END_USER_CONTEXT verification")
    else:
        print(f"protected_query_note={getattr(provider, 'disabled_reason', 'provider disabled')}")
    return 0 if status.connected_as_expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
