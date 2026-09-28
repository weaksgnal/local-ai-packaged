Infrastructure only — no project code lives here.

**Stack (trimmed 2026-09-28, Ian):** two containers.
- **SearXNG** `:8081` — every Claude session's search (`curl "http://localhost:8081/search?q=…&format=json"`) and the `search-tools` MCP server in `~/.claude/settings.json` (`scripts/search-mcp/server.py`). Config: `searxng/settings.yml` (gitignored; `searxng/settings-base.yml` + `settings.overrides.yml` + `bootstrap_searxng.sh` rebuild it).
- **Open WebUI** `127.0.0.1:8080` — chat UI over Ollama on Brain (`BRAIN_IP` from `~/cgts/repo/src/swarms/cgts_config.py`). No Ollama runs here; Brain and Voice are the model hosts (`~/.claude/skills/local-inference`).

Start: `docker compose -p localai -f docker-compose.yml -f docker-compose.override.private.yml up -d` — the crontab `@reboot` line runs exactly this. NEVER plain `docker compose up` (wrong project name, no port bindings).

`scripts/ollama-mcp.mjs` is the other MCP server Claude Code loads from here (points at Brain).

**Retired 2026-09-28** (evidence: n8n held zero workflows; Caddy had no hostnames and zero requests in 10 days; the ollama-* services were profile-gated and never started; the rest was upstream coleam00/local-ai-packaged template residue): n8n, Postgres, MinIO, Caddy, Flowise, Supabase vendored repo (1.0 GB), the disabled Neo4j bind mount (523 MB), the Open WebUI 0.9.5 backup tar (963 MB), Langfuse/Caddy/n8n Docker volumes, `docker-compose.cortex.yml` (vault-api never ran here). 2.5 GB → ~10 MB. Old files: `git show f15c47b:<path>`. `archive/shared_rentals_n8n_data_2026-05` holds the last n8n `shared/` mount.

Earlier retirements: Langfuse → Brain; `cortex-neo4j-cortex` + `qdrant` 2026-04-19; `neo4j-brain-data` volume expired 2026-07-12. `~/memory/brainstorm.db` retired 2026-09-28 (see `~/memory/archive/`).
