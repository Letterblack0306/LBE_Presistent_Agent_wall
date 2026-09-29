# Provider Credential Persistence Hazard

Date: 2026-09-29
Classification: HIGH / CONFIRMED LATENT RISK / NO CURRENT SECRET EXPOSURE
Status: REMEDIATED at this revision

## Finding

`reasoning-provider.json` is the live provider configuration, is Git-tracked,
is not ignored, and is a file the loader explicitly accepts an `api_key` in.
A real key written to it would be committed by an ordinary `git add`.

No secret is present today. This is a persistence hazard, not an exposure.

## Evidence chain

    reasoning_config.py:16   "api_key" is in _ALLOWED_FIELDS
    reasoning_config.py:48   api_key = raw.get("api_key")
    launch-lbe.ps1:4         the launcher reads reasoning-provider.json
    git ls-files             reasoning-provider.json  -> was TRACKED
    git check-ignore         -> was NOT ignored
    content inspection       contains no api_key      -> NO CURRENT LEAK

    future api_key written there
      -> ordinary git add / commit includes the file
      -> credential enters repository history

The R7 acceptance record, Final Architectural Invariants, requires that
credentials remain in host memory or outbound transport only and states
that leakage into repository artifacts is a terminal failure. Nothing in
the repository prevented the push that would violate it.

## Remediation applied

1. `.gitignore` now excludes `reasoning-provider.json` with a comment
   stating it may carry an api_key.
2. `git rm --cached reasoning-provider.json` removed it from the index.
   The local file was retained and still loads.
3. `reasoning-provider.example.json` remains tracked and unchanged, and
   remains the owner of example configuration.

A `.gitignore` rule alone would have been insufficient: Git continues to
track a file that is already in the index regardless of ignore rules.

## First-run regression check

`launch-lbe.ps1:71` already fails closed and names the deterministic path:

    "Provider setup is required. Create reasoning-provider.json from
     reasoning-provider.example.json, then rerun this launcher.
     No provider or credential was fabricated."

`launch-lbe.ps1:77` additionally refuses an incomplete config that lacks a
real model id. A fresh clone therefore still has an explicit, actionable
setup path, and the security fix does not degrade first run.

## Scope of this record

- It does not claim a credential leaked. None did.
- It does not rewrite history. Any key ever committed would need separate
  treatment; no such key was found by the passive scan.
- It does not authorize an active dependency audit, which answers a
  different question and remains unauthorized.
