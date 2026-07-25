# 04 — Project and Workspace Detector

## Purpose

Resolve the correct workspace and identify project characteristics that determine which guards apply.

## Required checks

- configured workspace root;
- repository identity;
- manifest and package metadata;
- language and framework signals;
- host application signals;
- generated, archived, backup, and experimental areas;
- active workspace profile.

## Duplicate-file handling

The detector must never select a file by basename alone.

Every selected file must include:

- absolute or workspace-relative path;
- workspace ID;
- repository identity;
- content hash;
- source classification;
- authority classification.

## Exclusion classes

By default, deprioritize or exclude:

- `.cep-dev`;
- archives;
- backups;
- generated outputs;
- build outputs;
- release bundles;
- vendor dependencies;
- test fixtures when production source is requested.

Excluded material may be retrieved only when the task explicitly needs it.

## Example profile

```json
{
  "workspace_id": "letterblack-cep-example",
  "root": "G:/Developments/ExampleCEP",
  "repository": "Letterblack0306/ExampleCEP",
  "project_types": ["cep-extension", "node-frontend", "extendscript-host"],
  "hosts": ["after-effects"],
  "languages": ["javascript", "extendscript", "html", "css"],
  "active_profile": "profiles/example-cep.policy.json",
  "risk_flags": ["host-bridge", "runtime-version-compatibility"],
  "confidence": 0.97
}
```
