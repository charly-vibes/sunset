# Purpose: Phase-1 CLI adapter over the typed agent tool surface
#   (sunset-14b, add-agent-tool-surface tasks 5.1-5.2): every core tool
#   exposed one-for-one, emitting the same envelope JSON the core returns, so
#   the parity script produces identical outcomes through both adapters.
# Responsibilities: Parse `sunset <tool> --workspace DIR [--args JSON]`,
#   dispatch to sunset.tool_surface.ToolSurface, print the envelope to stdout
#   with stable exit codes (0 ok, 2 refused, 5 error), and never raise.
# Rationale: change design decision 6 (one core, n adapters; MCP is phase 2,
#   built only when a model harness needs it — the parity requirement keeps
#   any future adapter from drifting).
"""CLI adapter: one subcommand per core tool, identical envelopes."""
import argparse
import json
import sys

from sunset.tool_surface import ToolSurface

TOOLS = ("open", "words", "crop", "zoom_in", "zoom_out",
         "queue", "propose", "decide", "export")

EXIT_CODES = {"ok": 0, "refused": 2, "error": 5}


def _envelope_text(envelope):
    return json.dumps(envelope, sort_keys=True, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sunset",
        description="Typed agent tool surface over digitization runs")
    parser.add_argument("tool", choices=TOOLS)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--args", default="{}",
                        help="tool arguments as one JSON object")
    args = parser.parse_args(argv)
    try:
        kwargs = json.loads(args.args)
    except ValueError:
        kwargs = None
    if not isinstance(kwargs, dict):
        envelope = {"status": "refused", "reason": "spec.invalid",
                    "data": {"args": args.args}, "provider_calls": 0}
        print(_envelope_text(envelope))
        return EXIT_CODES["refused"]
    surface = ToolSurface(args.workspace)
    envelope = getattr(surface, args.tool)(**kwargs)
    print(_envelope_text(envelope))
    return EXIT_CODES.get(envelope["status"], 5)


if __name__ == "__main__":
    sys.exit(main())
