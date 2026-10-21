# Five-minute interview walkthrough

1. Show `specs/001-transaction-screening/spec.md`, the resolved clarifications,
   implementation plan, completed task links, and acceptance.yaml.
2. Run `uv run specgate gate spec`. Temporarily add a `[NEEDS CLARIFICATION: currency]`
   marker to the spec, rerun, observe failure, then restore the file.
3. Run tests with coverage and PR Ready. Temporarily remove a task's commit link;
   observe failure and restore it. The negative tests also cover unreachable SHAs,
   coverage regression, missing plans, duplicate AC IDs, and secret output.
4. Show a green GitHub Actions run and the required-check branch rules. The checks
   physically block merging while protection remains active.
5. Start the API or deploy with kind. Run `uv run specgate piv`; all ACs must pass.
   Stop the API forwarding and run again. Note the durable run ID and approval pause.
   Reject with `piv-resume RUN_ID`. Explain that an approval command is deliberately
   unavailable through MCP.
6. Inspect `uv run specgate audit` and `uv run specgate metrics`, or the downloaded
   Actions evidence artifacts. Explain local audit scope and why missing lead-time
   data is displayed as null rather than a made-up adoption number.

Do not use real customer transactions, real credentials, or real sanctions entries.
All sample decisions come from synthetic demonstration rules.
