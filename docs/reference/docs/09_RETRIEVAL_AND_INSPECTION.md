# 09 — Retrieval and Inspection

## Existing retrieval role

The Agents Memory Tool SQLite index searches reference knowledge and returns ranked evidence.

## Required search output

Every match should contain:

- exact path or record ID;
- workspace or corpus source;
- score;
- matched terms;
- exact-phrase status;
- snippet;
- valid line range when applicable;
- hash;
- record type;
- authority level;
- verification state;
- excluded/archive/generated classification.

## Retrieval policy

- Search is read-only.
- Deduplicate equivalent copies.
- Prefer authoritative current records.
- Preserve conflicting results.
- Do not silently collapse production and archive copies.
- Do not treat retrieved evidence as a verified current repair.
- Narrow the search to the problem instead of scanning the entire corpus.

## Current workspace inspection

Current workspace evidence may be unnecessary for questions about general rules. It is required for project-specific verdicts.

A final `PASS` or `FAIL` concerning a workspace must not rely only on indexed historical material.
