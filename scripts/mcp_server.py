#!/usr/bin/env python3
"""Minimal MCP stdio server exposing Solana Tx Landing offline tools."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
PROTOCOL_VERSION = "2024-11-05"


TOOLS: dict[str, dict[str, Any]] = {
    "scan_ts_transactions": {
        "description": "Scan TypeScript/JavaScript Solana transaction code for landing risks.",
        "script": "scan_ts_transactions.py",
        "schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "json"], "default": "md"},
                "fix_plan": {"type": "boolean", "default": False},
            },
            "required": ["path"],
        },
    },
    "parse_simulation_logs": {
        "description": "Classify Solana simulation logs and RPC error text.",
        "script": "parse_simulation_logs.py",
        "schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "json"], "default": "md"},
            },
            "required": ["path"],
        },
    },
    "scan_anchor_compute": {
        "description": "Scan Rust/Anchor programs for compute-heavy transaction risks.",
        "script": "scan_anchor_compute.py",
        "schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "json"], "default": "md"},
            },
            "required": ["path"],
        },
    },
    "tx_landing_report": {
        "description": "Generate a local Solana transaction landing readiness report.",
        "script": "tx_landing_report.py",
        "schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "json"], "default": "md"},
            },
            "required": ["path"],
        },
    },
    "diagnose_signature_json": {
        "description": "Diagnose a saved Solana getTransaction JSON response without network access.",
        "script": "diagnose_signature.py",
        "schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "format": {"type": "string", "enum": ["md", "json"], "default": "md"},
            },
            "required": ["path"],
        },
    },
}


def make_response(message_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def send_message(message: dict[str, Any], *, framed: bool = True) -> None:
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if framed:
        sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(payload)
    else:
        sys.stdout.write(payload.decode("utf-8") + "\n")
    sys.stdout.flush()


def read_framed_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        name, _, value = line.decode("ascii", errors="ignore").partition(":")
        headers[name.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def iter_messages(line_mode: bool) -> Any:
    if line_mode:
        for line in sys.stdin:
            if line.strip():
                yield json.loads(line)
        return

    while True:
        message = read_framed_message()
        if message is None:
            return
        yield message


def tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["schema"],
        }
        for name, spec in TOOLS.items()
    ]


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}

    spec = TOOLS[name]
    fmt = arguments.get("format", "md")
    command = ["python3", str(SCRIPT_DIR / spec["script"])]
    if name == "diagnose_signature_json":
        command.extend(["--from-json", arguments["path"], "--format", fmt])
    else:
        command.extend([arguments["path"], "--format", fmt])
        if name == "scan_ts_transactions" and arguments.get("fix_plan"):
            command.append("--fix-plan")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, cwd=Path.cwd(), env=env, text=True, capture_output=True, check=False)
    text = result.stdout if result.returncode == 0 else (result.stdout + result.stderr)
    return {"content": [{"type": "text", "text": text}], "isError": result.returncode != 0}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return make_response(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "solana-tx-landing", "version": "0.1.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return make_response(message_id, {"tools": tool_list()})
    if method == "tools/call":
        return make_response(message_id, run_tool(params.get("name"), params.get("arguments") or {}))
    if message_id is None:
        return None
    return make_response(message_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line-mode", action="store_true", help="Use newline-delimited JSON instead of Content-Length framing")
    parser.add_argument("--list-tools", action="store_true", help="Print tool metadata and exit")
    args = parser.parse_args()

    if args.list_tools:
        print(json.dumps({"tools": tool_list()}, indent=2))
        return 0

    for message in iter_messages(args.line_mode):
        response = handle(message)
        if response is not None:
            send_message(response, framed=not args.line_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
