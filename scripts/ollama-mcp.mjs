#!/usr/bin/env node
/**
 * Ollama MCP Server — exposes Brain's Ollama as MCP tools for Claude Code
 * Usage: node ollama-mcp.mjs [OLLAMA_URL]
 * Default URL: http://10.0.0.1:11434  (Brain on Cortex bridge0)
 * Updated 2026-04-06: repointed from Voice (legacy) to Brain.
 */

const OLLAMA_URL = process.argv[2] || process.env.OLLAMA_URL || "http://10.0.0.1:11434";

// MCP stdio transport — reads JSON-RPC from stdin, writes to stdout
let buffer = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop(); // keep incomplete line
  for (const line of lines) {
    if (line.trim()) handleMessage(JSON.parse(line));
  }
});

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + "\n");
}

function reply(id, result) {
  send({ jsonrpc: "2.0", id, result });
}

function err(id, code, message) {
  send({ jsonrpc: "2.0", id, error: { code, message } });
}

const TOOLS = [
  {
    name: "ollama_chat",
    description: `Chat with a model running on Brain (Ollama at ${OLLAMA_URL}). Fast local inference, no API cost. Available models: gemma4:e2b (default, daytime, ~54 t/s), gemma4:31b (overnight, deep reasoning, ~5 t/s — pass think:false in options for non-reasoning prompts).`,
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string", description: "The message to send" },
        model: { type: "string", description: "Model to use (default: gemma4:e2b)", default: "gemma4:e2b" },
        system: { type: "string", description: "Optional system prompt" },
      },
      required: ["prompt"],
    },
  },
  {
    name: "ollama_list_models",
    description: "List all models currently available on Brain's Ollama instance.",
    inputSchema: { type: "object", properties: {} },
  },
];

async function ollamaChat({ prompt, model = "gemma4:e2b", system }) {
  const messages = [];
  if (system) messages.push({ role: "system", content: system });
  messages.push({ role: "user", content: prompt });

  const res = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, stream: false }),
  });

  if (!res.ok) throw new Error(`Ollama error: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.message?.content ?? JSON.stringify(data);
}

async function ollamaListModels() {
  const res = await fetch(`${OLLAMA_URL}/api/tags`);
  if (!res.ok) throw new Error(`Ollama error: ${res.status}`);
  const data = await res.json();
  return data.models?.map(m => `${m.name} (${Math.round(m.size / 1e9 * 10) / 10}GB)`).join("\n") ?? "No models found";
}

async function handleMessage(msg) {
  const { id, method, params } = msg;

  if (method === "initialize") {
    reply(id, {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "ollama-mcp", version: "1.0.0" },
    });
  } else if (method === "tools/list") {
    reply(id, { tools: TOOLS });
  } else if (method === "tools/call") {
    const { name, arguments: args } = params;
    try {
      let text;
      if (name === "ollama_chat") text = await ollamaChat(args);
      else if (name === "ollama_list_models") text = await ollamaListModels();
      else throw new Error(`Unknown tool: ${name}`);
      reply(id, { content: [{ type: "text", text }] });
    } catch (e) {
      reply(id, { content: [{ type: "text", text: `Error: ${e.message}` }], isError: true });
    }
  } else if (method === "notifications/initialized") {
    // no-op
  } else if (id !== undefined) {
    err(id, -32601, `Method not found: ${method}`);
  }
}
