# Third-party notices and reproducibility

The `.specify/` infrastructure and `.claude/skills/speckit-*` integration were generated
by the real GitHub spec-kit initializer from https://github.com/github/spec-kit.

- Upstream commit: `505781d7cabb5180b7098a7d8371c48456f9d4f6`
- Upstream development version: `1.2.3.dev0`
- Initialization: `specify init outputs/specgate --integration claude --script sh --ignore-agent-tools --force --non-interactive`
- License: MIT; the upstream copyright/license is retained in `.specify/UPSTREAM_LICENSE`.
- Local customization: project constitution and five `specgate-*` wrapper skills.

To regenerate, clone the upstream repository at that commit, then run its `specify`
entry point in a scratch directory with the same integration flags. Review generated
changes before updating this repository; preserve the local SpecGate wrappers and
constitution. This project does not depend on an unpinned spec-kit installation at
runtime. Python package versions are pinned transitively in `uv.lock`.

Primary references:
- https://github.com/github/spec-kit
- https://py.sdk.modelcontextprotocol.io/
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
