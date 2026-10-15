"""Owner-authorized validation command and the cache-free default."""
from lbe_guard_inspector.runtime.validation_command_policy import (
    DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG,
    OWNER_AUTHORITY_VALIDATION_POLICY_ID,
    catalog_for_owner_authority,
)


def _package(**overrides):
    value = {
        "issue_id": "I-1",
        "owner_file_or_module": "hello.txt",
        "owner_reason": "owner",
        "owner_evidence": ["user request"],
        "owner_status": "OWNER_PROVEN",
        "allowed_paths": ["hello.txt"],
        "validation_command": "git status --porcelain",
    }
    value.update(overrides)
    return value


def _find(catalog):
    return catalog.find(operation_id="reasoning.inspect", mode="coding", evidence_kind="focused_test")


def test_default_command_cannot_write_a_pytest_cache_into_the_project() -> None:
    policy = _find(DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG)
    assert policy.command[-2:] == ("-p", "no:cacheprovider")


def test_no_package_keeps_the_fixed_repository_policy() -> None:
    assert catalog_for_owner_authority(None) is DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG


def test_validated_package_supplies_the_validation_command() -> None:
    policy = _find(catalog_for_owner_authority(_package()))
    assert policy.policy_id == OWNER_AUTHORITY_VALIDATION_POLICY_ID
    assert policy.command == ("git", "status", "--porcelain")
    assert policy.timeout_seconds == 300.0


def test_quoted_arguments_are_tokenized_not_shell_interpreted() -> None:
    policy = _find(catalog_for_owner_authority(_package(validation_command='python -m pytest -k "a and b"')))
    assert policy.command == ("python", "-m", "pytest", "-k", "a and b")


def test_invalid_package_falls_back_to_the_fixed_policy() -> None:
    bad = _package()
    bad.pop("allowed_paths")
    assert catalog_for_owner_authority(bad) is DEFAULT_VALIDATION_COMMAND_POLICY_CATALOG
