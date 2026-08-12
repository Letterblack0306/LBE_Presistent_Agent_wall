# @letterblack/lbe

`@letterblack/lbe` is a thin npm bootstrap/launcher for the managed Python LBE
runtime. It does not implement provider, session, governance, tool, evidence,
validation, or completion behavior.

For local pre-publication use, install a packed tarball and bootstrap an
approved local `lbe_guard_inspector` wheel:

```powershell
npm install --global .\letterblack-lbe-0.1.0.tgz
lbe --install --wheel C:\artifacts\lbe_guard_inspector-0.2.0-py3-none-any.whl
lbe --help
```

Managed runtime code is stored under `LBE_HOME/runtime`; user configuration and
persistent state remain under `LBE_HOME/config` and `LBE_HOME/state`.
`LBE_HOME` may be set for a controlled installation location. Provider
credentials remain external user-owned configuration and are never stored by
the npm wrapper.
