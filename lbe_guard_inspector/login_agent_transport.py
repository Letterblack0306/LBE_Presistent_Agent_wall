"""Reasoning transport for platforms that authenticate by the user's own login.

Some provider platforms (Claude, Codex, Gemini) are reached through the user's
account login held by the platform's own CLI, not through an API key. This
transport runs that installed CLI headless and returns an OpenAI chat-completion
shaped reply, so the existing backends, schema validation, and governed tool
execution are unchanged.

Boundaries:
- The platform CLI owns login and credentials. LBE never reads or stores them.
- The CLI only reasons. Its own tools are disabled or sandboxed read-only and it
  runs in an empty scratch directory, so it cannot touch the workspace; every
  effect still goes through LBE's governed tools.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Sequence

from .reasoning_provider import ProviderError

ENDPOINT_SCHEME = "login-agent://"


@dataclass(frozen=True)
class LoginAgentSpec:
    provider_id: str
    executable: str
    login_hint: str
    # (model, system_prompt, output_file) -> argv after the executable; prompt goes on stdin
    build_args: Callable[[str, str, str], Sequence[str]]
    reads_output_file: bool = False
    system_in_args: bool = False


def _claude_args(model: str, system_prompt: str, _out: str) -> Sequence[str]:
    args = ["-p", "--output-format", "text", "--tools", "", "--no-session-persistence",
            "--setting-sources", "", "--system-prompt", system_prompt]
    if model:
        args += ["--model", model]
    return args


def _codex_args(model: str, _system: str, out: str) -> Sequence[str]:
    args = ["exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
            "--ignore-rules", "-s", "read-only", "--color", "never", "-o", out]
    if model:
        args += ["-m", model]
    return [*args, "-"]


def _gemini_args(model: str, _system: str, _out: str) -> Sequence[str]:
    args = ["-p", "Follow the instructions on stdin and reply with the final answer only.",
            "-o", "text", "--approval-mode", "default"]
    if model:
        args += ["-m", model]
    return args


LOGIN_AGENT_SPECS: dict[str, LoginAgentSpec] = {
    "claude-code": LoginAgentSpec("claude-code", "claude", "run `claude` and sign in", _claude_args),
    "openai-codex-cli": LoginAgentSpec(
        "openai-codex-cli", "codex", "run `codex login`", _codex_args, reads_output_file=True),
    "gemini-cli": LoginAgentSpec("gemini-cli", "gemini", "run `gemini` and sign in", _gemini_args),
}

def spec_from_mapping(provider_id: str, raw: Mapping[str, Any]) -> LoginAgentSpec:
    """Build a spec from JSON so any platform CLI can be added without code.

    {"executable": "opencode", "args": ["run"], "model_args": ["-m", "{model}"],
     "system_args": ["--system", "{system}"], "output_file_arg": ["-o", "{out}"],
     "login_hint": "run `opencode auth login`"}
    The prompt always goes on stdin; "{model}", "{system}", "{out}" are substituted.
    """
    executable = raw.get("executable")
    if not isinstance(executable, str) or not executable.strip():
        raise ValueError(f"login agent {provider_id!r}: executable must be a non-empty string")

    def tokens(key: str) -> list[str]:
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"login agent {provider_id!r}: {key} must be a list of strings")
        return value

    base, model_args, system_args, out_args = (
        tokens("args"), tokens("model_args"), tokens("system_args"), tokens("output_file_arg"))

    def build(model: str, system: str, out: str) -> Sequence[str]:
        sub = {"{model}": model, "{system}": system, "{out}": out}

        def fill(parts: Sequence[str]) -> list[str]:
            result = []
            for part in parts:
                for key, value in sub.items():
                    part = part.replace(key, value)
                result.append(part)
            return result

        argv = fill(base) + fill(out_args)
        if system_args:
            argv += fill(system_args)
        if model and model_args:
            argv += fill(model_args)
        return argv

    return LoginAgentSpec(
        provider_id, executable.strip(), str(raw.get("login_hint") or f"sign in with `{executable}`"),
        build, reads_output_file=bool(out_args), system_in_args=bool(system_args))


def load_extra_login_agents(path: str | os.PathLike[str] | None = None) -> dict[str, LoginAgentSpec]:
    """Register login-agent entries from the custom providers file (or `path`)."""
    from .custom_providers import login_agent_entries

    added = {pid: spec_from_mapping(pid, raw)
             for pid, raw in login_agent_entries(str(path) if path else None).items()
             if pid not in LOGIN_AGENT_SPECS}
    LOGIN_AGENT_SPECS.update(added)
    return added


# model ids meaning "let the platform pick its default"
_DEFAULT_MODEL_IDS = frozenset({"", "default", "login-default"})


def is_login_agent(provider_id: str) -> bool:
    return provider_id in LOGIN_AGENT_SPECS


def login_agent_status(provider_id: str) -> dict[str, Any]:
    """Cheap, no-network answer to "is the CLI for this platform present"."""
    spec = LOGIN_AGENT_SPECS[provider_id]
    path = shutil.which(spec.executable)
    return {"provider_id": provider_id, "auth": "login", "executable": path,
            "installed": path is not None, "login_hint": spec.login_hint}


class LoginAgentTransport:
    """JsonTransport that answers chat-completion payloads via a platform CLI."""

    supports_cancellation = True

    def __init__(self, provider_id: str) -> None:
        if provider_id not in LOGIN_AGENT_SPECS:
            raise ValueError(f"no login-agent binding for provider {provider_id!r}")
        self._spec = LOGIN_AGENT_SPECS[provider_id]
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._cancelled = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.kill()

    def stream_json(self, *, endpoint: str, payload: Mapping[str, Any],
                    headers: Mapping[str, str], timeout_seconds: float) -> Iterator[Mapping[str, Any]]:
        yield self.post_json(endpoint=endpoint, payload=payload, headers=headers,
                             timeout_seconds=timeout_seconds)

    def post_json(self, *, endpoint: str, payload: Mapping[str, Any],
                  headers: Mapping[str, str], timeout_seconds: float) -> Mapping[str, Any]:
        spec = self._spec
        exe = shutil.which(spec.executable)
        if exe is None:
            raise ProviderError(
                "PROVIDER_LOGIN_UNAVAILABLE",
                f"{spec.provider_id}: `{spec.executable}` is not installed; install it and {spec.login_hint}",
            )
        system_prompt, prompt = _flatten_messages(payload)
        model = str(payload.get("model") or "").strip()
        if model in _DEFAULT_MODEL_IDS:
            model = ""
        with tempfile.TemporaryDirectory(prefix="lbe-login-agent-") as scratch:
            out_file = os.path.join(scratch, "last-message.txt")
            argv = [exe, *spec.build_args(model, system_prompt, out_file)]
            stdin_text = prompt if spec.provider_id == "claude-code" else f"{system_prompt}\n\n{prompt}"
            env = dict(os.environ)
            env.setdefault("NO_COLOR", "1")
            with self._lock:
                self._cancelled = False
            try:
                proc = subprocess.Popen(
                    argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace", cwd=scratch, env=env,
                )
            except OSError as exc:
                raise ProviderError("PROVIDER_LOGIN_UNAVAILABLE", f"{spec.provider_id}: cannot start CLI: {exc}") from exc
            with self._lock:
                self._proc = proc
            try:
                stdout, stderr = proc.communicate(stdin_text, timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                proc.communicate()
                raise ProviderError("PROVIDER_TIMEOUT", f"{spec.provider_id}: CLI did not answer within {timeout_seconds:g}s") from exc
            finally:
                with self._lock:
                    self._proc = None
            if self._cancelled:
                raise ProviderError("PROVIDER_CANCELLED", f"{spec.provider_id}: turn cancelled")
            if proc.returncode != 0:
                detail = (stderr or stdout or "").strip().replace("\n", " ")[:300]
                code = "PROVIDER_LOGIN_REQUIRED" if _looks_like_auth_failure(detail) else "PROVIDER_HTTP_ERROR"
                hint = f" ({spec.login_hint})" if code == "PROVIDER_LOGIN_REQUIRED" else ""
                raise ProviderError(code, f"{spec.provider_id}: CLI exited {proc.returncode}{hint}: {detail}")
            text = stdout
            if spec.reads_output_file and os.path.exists(out_file):
                with open(out_file, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
        return {"choices": [{"message": {"role": "assistant", "content": text.strip()}, "finish_reason": "stop"}]}


def _flatten_messages(payload: Mapping[str, Any]) -> tuple[str, str]:
    system: list[str] = []
    user: list[str] = []
    for message in payload.get("messages", ()) or ():
        content = message.get("content")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        (system if message.get("role") == "system" else user).append(content)
    response_format = payload.get("response_format")
    if isinstance(response_format, Mapping):
        schema = (response_format.get("json_schema") or {}).get("schema")
        if schema is not None:
            system.append(
                "Reply with exactly one JSON object and nothing else (no prose, no code fence). "
                "It must validate against this JSON Schema:\n" + json.dumps(schema, sort_keys=True)
            )
    system.append("Do not use tools, read files, or run commands. Answer only from the input provided.")
    return "\n\n".join(system), "\n\n".join(user)


def _looks_like_auth_failure(detail: str) -> bool:
    lowered = detail.lower()
    return any(token in lowered for token in (
        "not logged in", "login", "log in", "sign in", "unauthorized", "401", "authenticate", "credential"))
