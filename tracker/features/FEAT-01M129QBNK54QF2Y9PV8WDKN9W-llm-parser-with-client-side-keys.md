---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN9W
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- llm
- parser
- security
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T21:56:21.762558+00:00'
UPDATED_AT: '2026-08-11T21:56:21.762558+00:00'
---

# llm-parser-with-client-side-keys

## Background

Wires OpenAI Chat Completions, Anthropic Messages, Gemini generateContent, and Groq OpenAI-compat Chat Completions adapters behind the existing ParseStrategy seam. Keys are typed into a settings dialog, stored in sessionStorage only, and posted as multipart form fields with each import. The key never persists past the request and never reaches logs.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KZSD76M27GPPYBFTTSTCMDR3 during the schema-4 cutover. -->
