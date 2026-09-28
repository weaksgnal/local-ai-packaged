#!/usr/bin/env python3
"""MCP server exposing SearXNG (search) and Jina Reader (web read) as tools."""

import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Optional


def read_jsonrpc() -> Optional[dict]:
    """Read a JSON-RPC message from stdin (Content-Length framing)."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line or line.strip() == "":
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = sys.stdin.read(length)
    return json.loads(body)


def write_jsonrpc(msg: dict):
    """Write a JSON-RPC message to stdout (Content-Length framing)."""
    body = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
    sys.stdout.flush()


def respond(req_id: Any, result: dict):
    write_jsonrpc({"jsonrpc": "2.0", "id": req_id, "result": result})


def respond_error(req_id: Any, code: int, message: str):
    write_jsonrpc({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def notify(method: str, params: dict):
    write_jsonrpc({"jsonrpc": "2.0", "method": method, "params": params})


SEARXNG_URL = "http://localhost:8081"
JINA_READER_URL = "https://r.jina.ai"
JINA_SEARCH_URL = "https://s.jina.ai"


def searxng_search(query: str, num_results: int = 10, categories: str = "general") -> str:
    """Search via local SearXNG instance."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "categories": categories,
    })
    url = f"{SEARXNG_URL}/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Search error: {e}"

    results = data.get("results", [])[:num_results]
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url_str = r.get("url", "")
        snippet = r.get("content", "")
        lines.append(f"## {i}. {title}\n{url_str}\n{snippet}\n")
    return "\n".join(lines)


def jina_read(url: str) -> str:
    """Read a webpage as clean Markdown via Jina Reader."""
    target = f"{JINA_READER_URL}/{url}"
    try:
        req = urllib.request.Request(target, headers={
            "Accept": "text/markdown",
            "X-Return-Format": "markdown",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()[:50000]
    except Exception as e:
        return f"Read error: {e}"


def jina_search(query: str, num_results: int = 5) -> str:
    """Search via Jina Search and return Markdown results."""
    encoded = urllib.parse.quote(query)
    target = f"{JINA_SEARCH_URL}/{encoded}"
    try:
        req = urllib.request.Request(target, headers={
            "Accept": "text/markdown",
            "X-Return-Format": "markdown",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode()[:30000]
    except Exception as e:
        return f"Jina search error: {e}"


TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using a local SearXNG instance. Returns structured results with titles, URLs, and snippets. Use for finding information, researching topics, looking up documentation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results (default 10, max 30)", "default": 10},
                "categories": {"type": "string", "description": "Search categories: general, images, news, science, it, files", "default": "general"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_read",
        "description": "Read a webpage and return its content as clean Markdown. Uses Jina Reader to extract readable content without needing a browser. Use for reading articles, documentation, blog posts, or any URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL to read (including https://)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "jina_search",
        "description": "Search the web via Jina Search. Returns results as Markdown. Alternative to web_search when SearXNG results are insufficient.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> str:
    if name == "web_search":
        return searxng_search(
            query=arguments["query"],
            num_results=arguments.get("num_results", 10),
            categories=arguments.get("categories", "general"),
        )
    elif name == "web_read":
        return jina_read(url=arguments["url"])
    elif name == "jina_search":
        return jina_search(query=arguments["query"])
    else:
        return f"Unknown tool: {name}"


def main():
    while True:
        msg = read_jsonrpc()
        if msg is None:
            break

        method = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            respond(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "search-tools", "version": "1.0.0"},
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            respond(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result_text = handle_tool_call(tool_name, arguments)
            respond(req_id, {
                "content": [{"type": "text", "text": result_text}],
            })
        elif method == "ping":
            respond(req_id, {})
        elif req_id is not None:
            respond_error(req_id, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
