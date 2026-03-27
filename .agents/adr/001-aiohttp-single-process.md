# ADR-001: Single-process Python with aiohttp

**decision**: Use a single Python process with aiohttp as the web framework.

**rationale**: The base image (`base-python:3.14-alpine3.23`) provides Python
natively. aiohttp is lightweight, async-capable, and has zero dependency on
build tools (unlike Flask+gunicorn or FastAPI+uvicorn which add complexity).
A single process is sufficient — the add-on serves one user at a time via
ingress, has no concurrent write paths, and SQLite queries are offloaded to
threads. This choice minimises container image size (critical for Raspberry Pi
SD card installs) and startup time.

**rejected alternatives**:
- Flask + gunicorn: requires a separate WSGI process manager, adds complexity
  without benefit for a single-user ingress add-on.
- FastAPI + uvicorn: heavier dependency chain (starlette, pydantic, uvicorn);
  OpenAPI/Swagger generation is unnecessary for an internal add-on API.
- Node.js / Express: would require a different base image (no official HA
  Node.js base), losing Alpine optimisations and S6-overlay integration.
- Nginx + separate backend: over-engineered for a single-process app; HA
  ingress already provides the reverse proxy layer.

**revisit if**: the add-on needs to handle concurrent multi-user access,
long-running background tasks, or WebSocket-heavy real-time features.
