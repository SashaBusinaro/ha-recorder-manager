"""Recorder Manager — aiohttp web server with HA Ingress support."""

import os
import json
import logging

from aiohttp import web

from db_reader import DbReader
from entity_resolver import EntityResolver
from filter_engine import FilterEngine
from yaml_writer import YamlWriter
from supervisor_api import SupervisorApi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recorder-manager")

# Paths — homeassistant_config map mounts to /homeassistant inside the container
HA_CONFIG_DIR = os.environ.get("HA_CONFIG_DIR", "/homeassistant")
DB_PATH = os.path.join(HA_CONFIG_DIR, "home-assistant_v2.db")
FILTER_FILE = os.path.join(HA_CONFIG_DIR, "recorder_filters.yaml")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Components
db_reader = DbReader(DB_PATH)
entity_resolver = EntityResolver()
filter_engine = FilterEngine()
yaml_writer = YamlWriter(FILTER_FILE)
supervisor_api = SupervisorApi()


def _get_ingress_path(request: web.Request) -> str:
    """Extract the ingress base path from the X-Ingress-Path header."""
    return request.headers.get("X-Ingress-Path", "")


# --- Middleware ---

@web.middleware
async def ingress_security(request: web.Request, handler):
    """Only allow connections from the HA Ingress proxy."""
    # In development / devcontainer, skip IP check
    if os.environ.get("DEV_MODE") == "1":
        return await handler(request)

    remote = request.remote
    if remote not in ("172.30.32.2", "127.0.0.1"):
        logger.warning("Rejected connection from %s", remote)
        raise web.HTTPForbidden(text="Access denied")
    return await handler(request)


# --- Routes ---

async def handle_index(request: web.Request) -> web.Response:
    """Serve the main HTML page with injected base path."""
    ingress_path = _get_ingress_path(request)
    index_path = os.path.join(STATIC_DIR, "index.html")

    with open(index_path, "r") as f:
        html = f.read()

    # Inject the ingress base path into the HTML
    html = html.replace("__INGRESS_PATH__", ingress_path)
    return web.Response(text=html, content_type="text/html")


async def handle_db_overview(request: web.Request) -> web.Response:
    """Return database file size and per-entity statistics."""
    try:
        overview = await db_reader.get_overview()
        return web.json_response(overview)
    except Exception as e:
        logger.error("DB overview error: %s", e)
        return web.json_response(
            {"error": str(e)}, status=500
        )


async def handle_entities(request: web.Request) -> web.Response:
    """Return merged entity list with stats and filter status."""
    try:
        # Get DB stats
        db_stats = await db_reader.get_entity_stats()

        # Get all HA entities
        ha_entities = await entity_resolver.get_all_entities()

        # Get current filters
        current_filters = yaml_writer.read_filters()

        # Merge and evaluate
        merged = _merge_entities(db_stats, ha_entities, current_filters)

        return web.json_response({"entities": merged})
    except Exception as e:
        logger.error("Entities error: %s", e)
        return web.json_response(
            {"error": str(e)}, status=500
        )


async def handle_get_filters(request: web.Request) -> web.Response:
    """Return the current filter configuration."""
    filters = yaml_writer.read_filters()
    return web.json_response(filters)


async def handle_save_filters(request: web.Request) -> web.Response:
    """Save new filter configuration (without applying)."""
    try:
        data = await request.json()
        yaml_writer.write_filters(data)
        return web.json_response({"status": "saved"})
    except Exception as e:
        logger.error("Save filters error: %s", e)
        return web.json_response(
            {"error": str(e)}, status=500
        )


async def handle_preview_filters(request: web.Request) -> web.Response:
    """Dry-run filter evaluation — return per-entity status without saving."""
    try:
        data = await request.json()
        include = data.get("include", {})
        exclude = data.get("exclude", {})

        # Get all known entities
        db_stats = await db_reader.get_entity_stats()
        ha_entities = await entity_resolver.get_all_entities()
        all_entity_ids = set(db_stats.keys()) | ha_entities

        results = []
        for entity_id in sorted(all_entity_ids):
            status, reason = filter_engine.evaluate(
                entity_id, include, exclude
            )
            results.append({
                "entity_id": entity_id,
                "status": status,
                "reason": reason,
            })

        return web.json_response({"entities": results})
    except Exception as e:
        logger.error("Preview error: %s", e)
        return web.json_response(
            {"error": str(e)}, status=500
        )


async def handle_apply(request: web.Request) -> web.Response:
    """Write filters, validate config, and restart HA Core."""
    try:
        data = await request.json()

        # 1. Backup and write new filters
        yaml_writer.backup()
        yaml_writer.write_filters(data)

        # 2. Validate configuration
        check_result = await supervisor_api.check_config()
        if not check_result["success"]:
            # Restore backup on failure
            yaml_writer.restore_backup()
            return web.json_response(
                {
                    "status": "error",
                    "message": "Configuration check failed",
                    "details": check_result.get("message", ""),
                },
                status=400,
            )

        # 3. Restart HA Core
        restart_result = await supervisor_api.restart_core()
        if not restart_result["success"]:
            return web.json_response(
                {
                    "status": "error",
                    "message": "Restart failed",
                    "details": restart_result.get("message", ""),
                },
                status=500,
            )

        return web.json_response({
            "status": "success",
            "message": "Filters applied. Home Assistant is restarting.",
        })

    except Exception as e:
        logger.error("Apply error: %s", e)
        # Attempt to restore on any error
        try:
            yaml_writer.restore_backup()
        except Exception:
            pass
        return web.json_response(
            {"error": str(e)}, status=500
        )


def _merge_entities(
    db_stats: dict, ha_entities: set, current_filters: dict
) -> list:
    """Merge DB stats with HA entity list and evaluate filters."""
    include = current_filters.get("include", {})
    exclude = current_filters.get("exclude", {})

    all_entity_ids = set(db_stats.keys()) | ha_entities
    merged = []

    for entity_id in sorted(all_entity_ids):
        stats = db_stats.get(entity_id, {})
        status, reason = filter_engine.evaluate(
            entity_id, include, exclude
        )
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        merged.append({
            "entity_id": entity_id,
            "domain": domain,
            "row_count": stats.get("row_count", 0),
            "writes_per_minute": round(
                stats.get("writes_per_minute", 0.0), 4
            ),
            "in_ha": entity_id in ha_entities,
            "in_db": entity_id in db_stats,
            "filter_status": status,
            "filter_reason": reason,
        })

    return merged


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application(middlewares=[ingress_security])

    # API routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/db/overview", handle_db_overview)
    app.router.add_get("/api/entities", handle_entities)
    app.router.add_get("/api/filters", handle_get_filters)
    app.router.add_post("/api/filters", handle_save_filters)
    app.router.add_post("/api/filters/preview", handle_preview_filters)
    app.router.add_post("/api/apply", handle_apply)

    # Static files
    app.router.add_static("/static/", STATIC_DIR, show_index=False)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8099)
