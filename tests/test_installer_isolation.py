"""The installer must resolve the installed package, never the caller's checkout."""
from pathlib import Path


def test_installer_resolves_site_with_isolated_python() -> None:
    text = (Path(__file__).resolve().parents[1] / "tools" / "lbe_product_integration.ps1").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if "lbe_guard_inspector.__file__" in l)
    # `python -c` puts the current directory on sys.path: run from a source
    # checkout it imports the checkout and installs the worker into the repo.
    assert " -I -c " in line
