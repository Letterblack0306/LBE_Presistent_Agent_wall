"""Credential references for provider profiles.

Windows Credential Manager is the host implementation.  The fallback is
intentionally unavailable rather than persisting an API key in local JSON,
SQLite, receipts, diagnostics, or workspace files.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


class CredentialStoreUnavailable(RuntimeError):
    pass


class WindowsCredentialStore:
    _TYPE_GENERIC = 1

    def __init__(self, *, prefix: str = "LetterBlack/LBE/") -> None:
        self.prefix = prefix
        if os.name != "nt":
            raise CredentialStoreUnavailable("Windows Credential Manager is unavailable on this host")
        self._advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)

    def put(self, credential_id: str, secret: str) -> None:
        if not credential_id.strip() or not secret:
            raise ValueError("credential_id and secret are required")
        # pywin32 is optional; use it when installed because it handles the
        # native structure safely and keeps this boundary small.
        try:
            import win32cred  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CredentialStoreUnavailable("install pywin32 to store a Windows credential") from exc
        win32cred.CredWrite({
            "Type": self._TYPE_GENERIC,
            "TargetName": self.prefix + credential_id,
            "UserName": credential_id,
            "CredentialBlob": secret,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }, 0)

    def get(self, credential_id: str) -> str:
        try:
            import win32cred  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CredentialStoreUnavailable("install pywin32 to read a Windows credential") from exc
        try:
            value = win32cred.CredRead(self.prefix + credential_id, self._TYPE_GENERIC, 0)["CredentialBlob"]
        except Exception as exc:
            raise ValueError(f"credential not found: {credential_id}") from exc
        return value.decode("utf-16-le") if isinstance(value, bytes) else str(value)

    def delete(self, credential_id: str) -> None:
        try:
            import win32cred  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CredentialStoreUnavailable("install pywin32 to remove a Windows credential") from exc
        try:
            win32cred.CredDelete(self.prefix + credential_id, self._TYPE_GENERIC, 0)
        except Exception as exc:
            raise ValueError(f"credential not found: {credential_id}") from exc
