# Implementation Plan: Transaction screening

## Technical Context

Python 3.12+, FastAPI/Pydantic, official Python MCP SDK v2, LangGraph, SQLite,
pytest/coverage, GitHub Actions, Docker, Kubernetes kind.

## Constitution Check

Deterministic screening; synthetic data only; fail-closed gates; no recovery without
human approval; secret scanning before PR publication; auditable agent operations.

## Project Structure

`src/specgate/` holds contracts, gates, guardrails, audit storage, CLI, MCP tools,
the sample API, and the PIV graph. `tests/` verifies positive and negative paths.
`deploy/` holds kind and Kubernetes configuration. `specs/` follows spec-kit.

## Delivery and Evidence

1. Validate spec.md, plan.md, tasks.md, and AC mapping in Spec Ready.
2. Execute tests, enforce 85% coverage and no decrease from the base commit,
   validate completed task commit links, and scan sources in PR Ready.
3. Build and load an immutable commit-tagged image into a disposable kind cluster.
4. Run rollout health checks, forward localhost, and invoke LangGraph PIV.
5. On failure, persist an approval interrupt. Only an operator can resume recovery.

## Risks and Tradeoffs

SQLite gives durable local checkpoints, not distributed coordination. Audit chaining
detects edits inside the retained chain, not privileged deletion or complete rewrites.
GitHub branch protection is configured separately from workflow source. Required
checks trust repository administrators and the reviewed gate implementation.
No LLM API key is required to run tests or PIV; Claude Code supplies feature authoring.
