Infrastructure only — no project code lives here.

Docker start: `docker compose -p local-ai -f docker-compose.yml -f docker-compose.override.private.yml up -d`
NEVER plain `docker compose up` — creates broken project without port bindings.

Services: n8n(:5678), SearXNG(:8081), Open-WebUI(:8080), Postgres(:5433), Redis(:6379), cortex-vault-api(:8000 loopback), MinIO(:9010).
LangFuse moved to Brain (10.0.0.1:3000).
M Brain starts from here: `start_m_brain.sh`.
Retired 2026-04-19 (Brief 8b): `cortex-neo4j-cortex` (was :7474/:7687) + `qdrant` (was :6333). Volumes preserved on disk for rollback.
Volume neo4j-brain-data (old M-graph, :7475) archived — EXPIRY 2026-07-12, then `docker volume rm neo4j-brain-data`.

Project code lives under `~/cgts/`, `~/memory/`, `~/local-ai/` (sibling dirs, consolidated 2026-04-08).
Cross-project source of truth: `~/memory/brainstorm.db` (query it, don't hardcode).
