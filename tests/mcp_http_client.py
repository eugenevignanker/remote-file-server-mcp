#!/usr/bin/env python3
import json
import urllib.error
import urllib.request


DEFAULT_PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class MCPHttpClient:
    def __init__(self, endpoint_url: str, protocol_version: str = DEFAULT_PROTOCOL_VERSION) -> None:
        self.endpoint_url = endpoint_url
        self.protocol_version = protocol_version
        self.session_id: str | None = None
        self._next_id = 1

    def initialize(self) -> dict:
        result = self.request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "remote-file-server-mcp-tests",
                    "version": "0.1.0",
                },
            },
            include_protocol_header=False,
        )
        negotiated = result.get("protocolVersion")
        if negotiated:
            self.protocol_version = negotiated
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        result = self.request("tools/list", {})
        return result["tools"]

    def call_tool(self, name: str, arguments: dict) -> dict:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise MCPError(f"Tool {name!r} returned isError=true: {result}")
        return result

    def call_tool_text(self, name: str, arguments: dict) -> str:
        result = self.call_tool(name, arguments)
        texts = [
            item["text"]
            for item in result.get("content", [])
            if item.get("type") == "text"
        ]
        if not texts:
            raise MCPError(f"Tool {name!r} did not return text content: {result}")
        return "".join(texts)

    def request(
        self,
        method: str,
        params: dict | None = None,
        *,
        include_protocol_header: bool = True,
    ) -> dict:
        request_id = self._allocate_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        response = self._post(payload, include_protocol_header=include_protocol_header)
        if response.get("id") != request_id:
            raise MCPError(f"Unexpected response id for {method!r}: {response}")
        if "error" in response:
            raise MCPError(f"MCP request {method!r} failed: {response['error']}")
        return response["result"]

    def notify(self, method: str, params: dict | None = None) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        self._post(payload, expect_response=False)

    def _allocate_id(self) -> int:
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _post(
        self,
        payload: dict,
        *,
        include_protocol_header: bool = True,
        expect_response: bool = True,
    ) -> dict:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if include_protocol_header:
            headers["MCP-Protocol-Version"] = self.protocol_version
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                session_id = resp.headers.get("Mcp-Session-Id")
                if session_id:
                    self.session_id = session_id

                if not expect_response:
                    if resp.status not in (200, 202):
                        raise MCPError(f"Notification {payload['method']!r} returned HTTP {resp.status}")
                    return {}

                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8")

                if "text/event-stream" in content_type:
                    return self._parse_sse_response(body, payload.get("id"))
                if not body.strip():
                    raise MCPError(f"Empty HTTP response body for {payload['method']!r}")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise MCPError(f"HTTP {exc.code} for {payload['method']!r}: {body}") from exc
        except urllib.error.URLError as exc:
            raise MCPError(f"Could not reach MCP endpoint {self.endpoint_url}: {exc}") from exc

    def _parse_sse_response(self, body: str, request_id: int | None) -> dict:
        event_data: list[str] = []
        messages: list[dict] = []

        for raw_line in body.splitlines():
            line = raw_line.strip("\r")
            if line.startswith("data:"):
                event_data.append(line[5:].lstrip())
                continue
            if line == "":
                if event_data:
                    joined = "\n".join(event_data).strip()
                    if joined:
                        messages.append(json.loads(joined))
                    event_data = []

        if event_data:
            joined = "\n".join(event_data).strip()
            if joined:
                messages.append(json.loads(joined))

        for message in messages:
            if message.get("id") == request_id:
                return message
        if messages:
            return messages[-1]
        raise MCPError("SSE response contained no JSON-RPC messages")
