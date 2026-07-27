from __future__ import annotations

from audit_controller import register_rule, run_rule


def test_unexpected_rule_error_is_blocked_not_a_workspace_failure() -> None:
    def raises_unexpected(_ctx, _params):
        raise UnboundLocalError("internal test failure")

    register_rule("generic", "test.unexpected_error", raises_unexpected)
    result = run_rule("generic", "test.unexpected_error", object())

    assert result.status == "blocked"
    assert "UnboundLocalError" in result.message
