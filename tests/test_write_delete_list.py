#!/usr/bin/env python3
import json
import sys
import uuid

from mcp_http_client import MCPError, MCPHttpClient


def decode_json_payload(tool_name: str, text: str):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPError(f"Tool {tool_name!r} did not return JSON: {text!r}") from exc

    if isinstance(payload, dict) and "error" in payload:
        raise MCPError(f"Tool {tool_name!r} failed: {payload['error']}")
    return payload


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_write_delete_list.py <mcp-endpoint-url>", file=sys.stderr)
        return 2

    client = MCPHttpClient(sys.argv[1])
    test_id = uuid.uuid4().hex[:8]
    base_dir = f"mcp-smoketests/write-delete-list-{test_id}"
    file_path = f"{base_dir}/delete-me.txt"

    try:
        client.initialize()
        tools = {tool["name"] for tool in client.list_tools()}
        required = {"make_directory", "write_file", "delete_path", "list_files"}
        missing = sorted(required - tools)
        if missing:
            raise MCPError(f"Server is missing required tools: {missing}")

        print(f"Creating directory {base_dir}")
        print(client.call_tool_text("make_directory", {"path": base_dir}))

        print(f"Writing file {file_path}")
        print(client.call_tool_text("write_file", {"path": file_path, "content": "delete me"}))

        print(f"Verifying file appears in {base_dir}")
        before_delete = decode_json_payload("list_files", client.call_tool_text("list_files", {"path": base_dir}))
        if not isinstance(before_delete, list):
            raise MCPError(f"Tool 'list_files' returned unexpected payload: {before_delete}")
        if "delete-me.txt" not in {entry["name"] for entry in before_delete}:
            raise MCPError(f"delete-me.txt not present after write: {before_delete}")

        print(f"Deleting file {file_path}")
        print(client.call_tool_text("delete_path", {"path": file_path}))

        print(f"Verifying file is absent from {base_dir}")
        after_delete = decode_json_payload("list_files", client.call_tool_text("list_files", {"path": base_dir}))
        if not isinstance(after_delete, list):
            raise MCPError(f"Tool 'list_files' returned unexpected payload: {after_delete}")
        if "delete-me.txt" in {entry["name"] for entry in after_delete}:
            raise MCPError(f"delete-me.txt still present after delete: {after_delete}")

        print("PASS write/delete/list")
        return 0
    except MCPError as exc:
        print(f"FAIL write/delete/list: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
