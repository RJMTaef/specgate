# Architecture decisions

## 1. Extend GitHub spec-kit

The upstream initializer generated the real templates, scripts, and Claude skills.
SpecGate adds five wrappers rather than reimplementing that authoring workflow.
Structured acceptance.yaml is a narrow execution contract next to the canonical
Markdown specification. IDs bind human intent to deployed smoke checks. The current
parser requires our documented AC/task line formats and exact AC membership.

## 2. One gate engine, distinct authorities

The CLI and official MCP SDK server share `gates.py` through an audited facade.
GitHub Actions runs pytest first, supplies coverage evidence, measures PR-base
coverage in a separate checkout, and creates the required status checks. A local
JSON result cannot satisfy a required GitHub check. PR Ready fails closed if its
coverage evidence is missing. Baseline measurement uses the same Python version,
but each revision's frozen lockfile and test suite.

This design assumes trusted repository administrators and review of gate changes.
For hostile contributors, put the gate implementation and workflow policy in a
separately protected repository or organization-required workflow with separate
ownership. The current implementation is a portfolio reference, not certified
regulatory enforcement.

## 3. Durable deterministic operational agent

LangGraph nodes are `probe → approval → recover`. Probe maps one HTTP smoke check
to every AC. Failed probes interrupt into SQLite before recovery. The CLI resumes
the same run with an explicit decision. Rejection ends without running kubectl;
approval issues one fixed-target rollout undo request. There is no LLM choosing
HTTP assertions or shell commands. Authoring is agentic through Claude Code;
operational evaluation deliberately uses deterministic tools.

The graph may replay a node after a crash. Local audit metadata can contain repeat
events; no exactly-once claim is made. A crash around a rollback side effect can
leave recovery ambiguous. Inspect Kubernetes revisions before retrying a recovery
whose result is unknown. Production recovery should use an idempotent controller
and an authorized, independently authenticated approval service.

## 4. Keep sensitive payloads outside evidence

Screening does not store transfer data. Audit events contain action, feature,
timestamp, and outcome. Secret scans return rule names rather than matches. Claude
hooks are scoped to this repository and can be disabled by the local operator.
Audit hashes are a useful integrity check, not a substitute for external retention.

## 5. Measure observed delivery

Pass rate is successes divided by completed/failed/error gate invocations in the
current audit database. Spec-to-PR time is first spec commit timestamp to actual
GitHub PR creation. Metrics are job-scoped and surfaced in Actions summaries, not
a fabricated dashboard. A separate collector can aggregate retained CI artifacts.
