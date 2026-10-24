"""Provider and model catalog for provider selection (LET-44).

Source of truth is the catalog that ``@cline/llms`` ships inside LBE's own Cline
worker (``runtime/cline_worker``). LBE does not keep a hand-written provider
list: this module only reads that catalog and adds facts it can check locally.

Readiness is a fact, never a guess:
- ``key set``      the provider's key environment variable is present (the value
                   is never read, copied or stored; only its presence is checked);
- ``listening``    a local endpoint (localhost/127.0.0.1) accepts a connection;
- ``needs <ENV>``  no key variable is present;
- ``not running``  the local endpoint refuses the connection;
- ``own login``    the provider signs in through its own tool (no key variable).
- ``own sign-in``  an LBE login-agent provider whose CLI is installed; the CLI
                   holds the sign-in, and the first turn proves it works.

Catalog data says how to reach a provider; it does not prove a key is valid or
quota is left. Only a real turn proves that.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

WORKER_DIR = Path(__file__).resolve().parent / "runtime" / "cline_worker"
CATALOG_SCRIPT = WORKER_DIR / "catalog.mjs"
_LLMS_PACKAGE = WORKER_DIR / "node_modules" / "@cline" / "llms" / "package.json"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_DEFAULT_PORTS = {"http": 80, "https": 443}

Runner = Callable[..., "subprocess.CompletedProcess[str]"]
Probe = Callable[[str, int], bool]
Which = Callable[[str], "str | None"]


class CatalogUnavailable(RuntimeError):
    """The catalog cannot be read on this machine (reason in the message)."""


def catalog_version() -> str:
    try:
        return str(json.loads(_LLMS_PACKAGE.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError) as exc:
        raise CatalogUnavailable(
            f"provider catalog is not installed: run `npm ci` in {WORKER_DIR}"
        ) from exc


def _cache_dir() -> Path:
    override = os.environ.get("LBE_CACHE_DIR")
    return Path(override) if override else Path.home() / ".lbe" / "cache"


def load_catalog(
    *,
    refresh: bool = False,
    node: str = "node",
    run: Runner = subprocess.run,
    cache_dir: Path | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Return the catalog, cached per installed ``@cline/llms`` version."""
    version = catalog_version()
    cache = (cache_dir or _cache_dir()) / f"provider-catalog-{version}.json"
    if not refresh and cache.is_file():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except ValueError:
            pass  # a damaged cache is rebuilt below
    try:
        completed = run(
            [node, str(CATALOG_SCRIPT)],
            cwd=str(WORKER_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CatalogUnavailable(f"provider catalog could not run: {exc}") from exc
    if completed.returncode != 0:
        tail = (completed.stderr or "").strip().splitlines()[-1:] or ["no output"]
        raise CatalogUnavailable(f"provider catalog failed: {tail[0][:200]}")
    try:
        catalog = json.loads(completed.stdout)
    except ValueError as exc:
        raise CatalogUnavailable("provider catalog returned invalid JSON") from exc
    if not isinstance(catalog, dict) or not isinstance(catalog.get("providers"), list):
        raise CatalogUnavailable("provider catalog has no provider list")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(catalog), encoding="utf-8")
    return catalog


def engine_for(provider: Mapping[str, Any]) -> str:
    """LBE's native engine speaks OpenAI-compatible chat; everything else goes through Cline.
    LBE's own login-agent providers run their platform CLI with its tools off."""
    if provider.get("source") == "login":
        return "login"
    native = (
        provider.get("protocol") == "openai-chat"
        and provider.get("client") == "openai-compatible"
        and bool(provider.get("base_url"))
    )
    return "native" if native else "cline"


def _tcp_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def readiness(
    provider: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    probe: Probe = _tcp_listening,
    which: Which = shutil.which,
) -> tuple[bool, str]:
    if provider.get("source") == "login":
        executable = str(provider.get("executable") or "")
        if executable and which(executable):
            return True, f"own sign-in · {executable} installed"
        return False, f"{executable or 'cli'} not installed"
    env = os.environ if environ is None else environ
    keys = [str(k) for k in provider.get("key_env") or []]
    present = next((k for k in keys if env.get(k)), None)
    base_url = str(provider.get("base_url") or "")
    parsed = urlparse(base_url) if base_url else None
    if parsed and (parsed.hostname or "").lower() in _LOCAL_HOSTS:
        port = parsed.port or _DEFAULT_PORTS.get(parsed.scheme, 80)
        if probe(parsed.hostname or "localhost", port):
            return True, "listening"
        return False, "not running"
    if present:
        return True, f"key set: {present}"
    if keys:
        return False, f"needs {keys[0]}"
    return False, "own login"


def provider_rows(
    catalog: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    probe: Probe = _tcp_listening,
    which: Which = shutil.which,
) -> list[dict[str, Any]]:
    """One row per catalog provider; ready providers first, then by name."""
    models = catalog.get("models") if isinstance(catalog.get("models"), dict) else {}
    rows = []
    for provider in catalog.get("providers") or []:
        if not isinstance(provider, dict) or not provider.get("id"):
            continue
        ready, state = readiness(provider, environ=environ, probe=probe, which=which)
        rows.append({
            "id": str(provider["id"]),
            "name": str(provider.get("name") or provider["id"]),
            "protocol": provider.get("protocol"),
            "engine": engine_for(provider),
            "base_url": provider.get("base_url"),
            "key_env": list(provider.get("key_env") or []),
            "default_model": provider.get("default_model"),
            "models": len(models.get(provider["id"]) or []),
            "ready": ready,
            "state": state,
        })
    rows.sort(key=lambda row: (not row["ready"], row["name"].lower()))
    return rows


def catalog_models(catalog: Mapping[str, Any], provider_id: str) -> list[dict[str, Any]]:
    ids = {str(p.get("id")) for p in catalog.get("providers") or [] if isinstance(p, dict)}
    if provider_id not in ids:
        raise ValueError(f"provider is not in the catalog: {provider_id}")
    models = catalog.get("models") if isinstance(catalog.get("models"), dict) else {}
    return [dict(m) for m in models.get(provider_id) or [] if isinstance(m, dict) and m.get("id")]
