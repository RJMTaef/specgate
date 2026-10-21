"""Official Python MCP SDK server. No rollback approval tool is exposed to agents."""

import os
from pathlib import Path

from mcp.server import MCPServer

from specgate.service import Pipeline


def create_server(root: Path) -> MCPServer:
    server = MCPServer("SpecGate")
    pipeline = Pipeline(root)

    @server.tool()
    def validate_spec(feature: str) -> dict:
        """Validate spec-kit artifacts and their acceptance-to-smoke mapping."""
        return pipeline.validate_spec(feature)

    @server.tool()
    def check_gate(gate: str = "spec") -> dict:
        """Inspect spec or PR gate; PR requires CI coverage evidence and fails without it."""
        return pipeline.check_gate(gate)

    @server.tool()
    def get_pipeline_status() -> dict:
        """Get current readiness. GitHub Actions is the merge authority."""
        return pipeline.get_pipeline_status()

    @server.tool()
    def run_piv(feature: str, base_url: str = "http://127.0.0.1:8000") -> dict:
        """Run AC-mapped checks; a failure persists a human approval interruption."""
        return pipeline.run_piv(feature, base_url)

    @server.tool()
    def guard_output(feature: str, text: str) -> dict:
        """Secret-scan agent output before writing a review artifact intended for a PR."""
        return pipeline.guard_output(feature, text)

    return server


def main():
    create_server(Path(os.environ.get("SPECGATE_ROOT", "."))).run()


if __name__ == "__main__":
    main()
