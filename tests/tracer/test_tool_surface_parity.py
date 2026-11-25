# Purpose: RED-first gate test for interface parity (add-agent-tool-surface
#   task 5.1): one recorded call script produces byte-identical outcome
#   envelopes through every exposed adapter (phase 1: in-process core,
#   subprocessed core, CLI).
# Responsibilities: Record the script once, replay it through each adapter
#   against the same run directory with a fresh workspace per adapter, and
#   compare canonical envelope bytes.
"""Parity script across every exposed adapter (task 5.1, gate)."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tool_surface_fixtures as fx

from sunset.cli import main as cli_main
from sunset.tool_surface import ToolSurface

REPO = Path(__file__).resolve().parents[2]


def build_script(run, tmp_path):
    """The recorded call script: reads, ladder moves, bounded pagination,
    writes with idempotent retries, and typed refusals."""
    probe = ToolSurface(tmp_path / "probe-ws")
    probe.open(run=str(run))
    regions = probe.descriptor["regions"]
    page1 = next(r["id"] for r in regions if r["kind"] == "page"
                 and re.fullmatch(r"page:1", r["anchor"]["locator_path"]))
    page2 = next(r["id"] for r in regions if r["kind"] == "page"
                 and re.fullmatch(r"page:2", r["anchor"]["locator_path"]))
    word = next(r["id"] for r in regions if r["kind"] == "word")
    doc = next(r["id"] for r in regions if r["kind"] == "document")
    spec = {"type": "field:total", "anchors": [page1], "value": "2.500,00",
            "origin": "model:p", "extractive": False}
    claim_probe = ToolSurface(tmp_path / "probe-ws2")
    claim_probe.open(run=str(run))
    claim_id = claim_probe.propose(spec=dict(spec))["data"]["claim_id"]
    return [
        ("open", {"run": str(run)}),
        ("words", {"scope": page1}),
        ("words", {"scope": page2, "page_size": 5}),
        ("words", {"scope": page2, "page_size": 5,
                   "cursor": probe.words(scope=page2, page_size=5)["cursor"]}),
        ("zoom_in", {"scope": word}),
        ("zoom_out", {"scope": word}),
        ("zoom_out", {"scope": doc}),          # refused: root has no parent
        ("crop", {"anchor": word}),
        ("queue", {}),
        ("words", {"scope": "page-1"}),        # refused: label address
        ("words", {"scope": "a:" + "0" * 32}),  # refused: unknown scope
        ("propose", {"spec": dict(spec)}),
        ("propose", {"spec": dict(spec)}),     # idempotent repeat
        ("decide", {"claim_id": claim_id, "action": "accept"}),
        ("decide", {"claim_id": claim_id, "action": "accept"}),  # repeat
        ("decide", {"claim_id": "c:" + "0" * 32, "action": "accept"}),
        ("export", {}),
        ("export", {"audit_records": [{"claim_type": "field:total",
                                       "evidence_class": "human",
                                       "n": 400, "errors": 0}]}),
    ]


def run_core(workspace, script):
    surface = ToolSurface(workspace)
    return [getattr(surface, tool)(**args) for tool, args in script]


def run_subprocess_core(workspace, script, tmp_path):
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from sunset.tool_surface import ToolSurface\n"
        "surface = ToolSurface(sys.argv[1])\n"
        "for tool, args in json.loads(sys.argv[2]):\n"
        "    print(json.dumps(getattr(surface, tool)(**args),\n"
        "                      sort_keys=True, ensure_ascii=False))\n"
        % str(REPO))
    proc = subprocess.run(
        [sys.executable, "-B", str(driver), str(workspace),
         json.dumps(script)],
        capture_output=True, text=True, check=True, cwd=REPO)
    return [json.loads(line) for line in proc.stdout.splitlines()]


def run_cli(workspace, script, tmp_path):
    out = []
    for tool, args in script:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "sunset.cli", tool,
             "--workspace", str(workspace), "--args", json.dumps(args)],
            capture_output=True, text=True, cwd=REPO)
        assert proc.returncode in (0, 2), (tool, proc.returncode,
                                           proc.stderr)
        out.append(json.loads(proc.stdout))
    return out


def canonical_bytes(env):
    return fx.canonical(env).encode("utf-8")


def test_identical_script_identical_outcomes_through_every_adapter(tmp_path):
    run = fx.plain_run(tmp_path)
    script = build_script(run, tmp_path)
    core = run_core(tmp_path / "ws-core", script)
    sub = run_subprocess_core(tmp_path / "ws-sub", script, tmp_path)
    cli = run_cli(tmp_path / "ws-cli", script, tmp_path)
    assert len(core) == len(script) == len(sub) == len(cli)
    for i, (tool, _) in enumerate(script):
        a, b, c = (canonical_bytes(envs[i])
                   for envs in (core, sub, cli))
        assert a == b, (tool, i, a[:300], b[:300])
        assert b == c, (tool, i, b[:300], c[:300])


def test_core_replays_are_deterministic(tmp_path):
    run = fx.plain_run(tmp_path)
    script = build_script(run, tmp_path)
    a = [canonical_bytes(e) for e in run_core(tmp_path / "ws-a", script)]
    b = [canonical_bytes(e) for e in run_core(tmp_path / "ws-b", script)]
    assert a == b


def test_cli_is_invokable_and_reports_stable_exit_codes(tmp_path):
    run = fx.plain_run(tmp_path)
    ws = tmp_path / "ws"
    script = build_script(run, tmp_path)
    tool, args = script[0]  # open
    code = cli_main([tool, "--workspace", str(ws),
                     "--args", json.dumps(args)])
    assert code == 0
    ws2 = tmp_path / "ws2"
    tool, args = ("words", {"scope": "page-1"})  # refused before open
    code = cli_main([tool, "--workspace", str(ws2),
                     "--args", json.dumps(args)])
    assert code == 2
