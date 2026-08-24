# 08 — LBE Gallery and Indexed Knowledge

## Purpose

Store and retrieve distilled engineering knowledge without treating all records as equally authoritative.

## Record types

- rule;
- deterministic guard metadata;
- workspace profile;
- architecture pattern;
- handler pattern;
- data-flow pattern;
- state-owner pattern;
- validation pattern;
- failure pattern;
- repair pattern;
- anti-pattern;
- verified proof;
- protected checkpoint;
- confirmed decision;
- negative example;
- historical chat or Q&A context.

## Required metadata

- ID;
- title;
- record type;
- project types;
- workspace scope;
- trigger;
- problem;
- rationale;
- evidence references;
- source classification;
- authority level;
- confidence;
- verification status;
- verified timestamp;
- superseded status;
- hash or version.

## Retrieval boundary

The gallery supplies context. It does not:

- decide which workspace is active;
- prove the current project has the same defect;
- authorize edits;
- produce final verdicts.

## Authority requirement

Search results must preserve their source class, authority, verification state, and workspace scope in the evidence package.
