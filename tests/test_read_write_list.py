#!/usr/bin/env python3
import json
import sys
import uuid

from mcp_http_client import MCPError, MCPHttpClient


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_read_write_list.py <mcp-endpoint-url>", file=sys.stderr)
        return 2

    client = MCPHttpClient(sys.argv[1])
    test_id = uuid.uuid4().hex[:8]
    base_dir = f"mcp-smoketests/read-write-list-{test_id}"
    file_path = f"{base_dir}/hello.txt"
    expected_content = f"hello from {test_id}\nline two\n"

    try:
        client.initialize()
        tools = {tool["name"] for tool in client.list_tools()}
        required = {"make_directory", "write_file", "read_file", "list_files", "get_file_info"}
        missing = sorted(required - tools)
        if missing:
            raise MCPError(f"Server is missing required tools: {missing}")

        print(f"Creating directory {base_dir}")
        print(client.call_tool_text("make_directory", {"path": base_dir}))

        print(f"Writing file {file_path}")
        print(client.call_tool_text("write_file", {"path": file_path, "content": expected_content}))

        print(f"Listing directory {base_dir}")
        listing = json.loads(client.call_tool_text("list_files", {"path": base_dir}))
        file_names = {entry["name"] for entry in listing}
        if "hello.txt" not in file_names:
            raise MCPError(f"hello.txt not found in listing: {listing}")

        print(f"Reading file {file_path}")
        actual_content = client.call_tool_text("read_file", {"path": file_path})
        if actual_content != expected_content:
            raise MCPError(
                f"Unexpected file content for {file_path!r}: expected {expected_content!r}, got {actual_content!r}"
            )

        print(f"Inspecting file {file_path}")
        info = json.loads(client.call_tool_text("get_file_info", {"path": file_path}))
        if info.get("type") != "file":
            raise MCPError(f"Expected file type metadata, got: {info}")
        if "permissions" not in info:
            raise MCPError(f"Expected permissions in metadata, got: {info}")

        print("PASS read/write/list")
        return 0
    except MCPError as exc:
        print(f"FAIL read/write/list: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
