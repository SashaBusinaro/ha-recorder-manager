"""Recorder Manager — aiohttp web server with HA Ingress support."""

import os
import logging
import asyncio

import aiohttp
from aiohttp import web

from db_reader import DbReader
from entity_resolver import EntityResolver
from filter_engine import FilterEngine
from yaml_writer import YamlWriter
from supervisor_api import SupervisorApi
from config_reader import detect_existing_filters, detect_setup_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recorder-manager")

# Paths — homeassistant_config map mounts to /homeassistant inside the container
HA_CONFIG_DIR = os.environ.get("HA_CONFIG_DIR", "/homeassistant")
DB_PATH = os.path.join(HA_CONFIG_DIR, "home-assistant_v2.db")
INCLUDE_FILE = os.path.join(HA_CONFIG_DIR, "recorder_include.yaml")
EXCLUDE_FILE = os.path.join(HA_CONFIG_DIR, "recorder_exclude.yaml")
HA_CONFIG_FILE = os.path.join(HA_CONFIG_DIR, "configuration.yaml")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Components
db_reader = DbReader(DB_PATH)
entity_resolver = EntityResolver()
filter_engine = FilterEngine()
yaml_writer = YamlWriter(INCLUDE_FILE, EXCLUDE_FILE)
supervisor_api = SupervisorApi()

# Strong references for fire-and-forget tasks (prevent GC before completion)
_background_tasks: set = set()


def _validate_filter_payload(data: dict) -> None:
    """Basic schema validation for filter payloads.

    Raises ValueError if the structure is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    for section in ("include", "exclude"):
        block = data.get(section, {})
        if block is None:
            continue
        if not isinstance(block, dict):
            raise ValueError(f"'{section}' must be a dict")
        for key in ("entities", "domains", "entity_globs"):
            val = block.get(key)
            if val is not None and not isinstance(val, list):
                raise ValueError(f"'{section}.{key}' must be a list")


def _get_ingress_path(request: web.Request) -> str:
    """Extract the ingress base path from the X-Ingress-Path header."""
    return request.headers.get("X-Ingress-Path", "")


# --- Middleware ---

@web.middleware
async def ingress_security(request: web.Request, handler):
    """Only allow connections from the HA Ingress proxy."""
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

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("__INGRESS_PATH__", ingress_path)
    return web.Response(text=html, content_type="text/html")


async def handle_db_overview(request: web.Request) -> web.Response:
    """Return database file size and per-entity statistics."""
    try:
        overview = await db_reader.get_overview()
        return web.json_response(overview)
    except Exception as e:
        logger.error("DB overview error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_entities(request: web.Request) -> web.Response:
    """Return merged entity list with stats and filter status."""
    try:
        db_stats = await db_reader.get_entity_stats()
        ha_entities = await entity_resolver.get_all_entities()
        current_filters = yaml_writer.read_filters()
        merged = _merge_entities(db_stats, ha_entities, current_filters)

        return web.json_response({"entities": merged, "total": len(merged)})
    except Exception as e:
        logger.error("Entities error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_get_filters(request: web.Request) -> web.Response:
    """Return the current filter configuration."""
    filters = yaml_writer.read_filters()
    return web.json_response(filters)


async def handle_setup_status(request: web.Request) -> web.Response:
    """Return setup scenario: complete, migration, or fresh_setup.

    Scenario logic:
      - inc_managed AND exc_managed        → complete
      - inc_inline OR exc_inline           → migration
      - neither                            → fresh_setup
    """
    status = detect_setup_status(HA_CONFIG_FILE)

    if status["inc_managed"] and status["exc_managed"]:
        return web.json_response({"setup_complete": True, "scenario": "complete"})

    if status["inc_inline"] or status["exc_inline"]:
        scenario = "migration"
    else:
        scenario = "fresh_setup"

    return web.json_response({"setup_complete": False, "scenario": scenario})


async def handle_setup_check(request: web.Request) -> web.Response:
    """Validate the HA configuration via the Supervisor API.

    First verifies that both ``!include`` sub-key directives are present in
    the recorder block of configuration.yaml, then runs the Supervisor config
    check.
    """
    setup = detect_setup_status(HA_CONFIG_FILE)
    if not (setup["inc_managed"] and setup["exc_managed"]):
        return web.json_response(
            {
                "status": "error",
                "message": (
                    "Both 'include: !include recorder_include.yaml' and "
                    "'exclude: !include recorder_exclude.yaml' must be present "
                    "in the recorder: block of configuration.yaml. "
                    "Please make the edits and try again."
                ),
            },
            status=400,
        )

    try:
        result = await supervisor_api.check_config()
        if result["success"]:
            return web.json_response({"status": "ok"})
        return web.json_response(
            {"status": "error", "message": result.get("message", "Check failed")},
            status=400,
        )
    except Exception as e:
        logger.error("Setup config check error: %s", e)
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_setup_reboot(request: web.Request) -> web.Response:
    """Fire-and-forget HA Core restart. Returns immediately."""
    async def _restart():
        try:
            await supervisor_api.restart_core()
        except Exception as e:
            logger.error("Reboot error: %s", e)

    task = asyncio.create_task(_restart())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return web.json_response({"status": "rebooting"})


async def handle_setup_init_default(request: web.Request) -> web.Response:
    """Create both filter files with the header comment if they don't exist."""
    try:
        result = yaml_writer.create_defaults()
        return web.json_response({"status": "ok", **result})
    except Exception as e:
        logger.error("Init default error: %s", e)
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_migration_apply(request: web.Request) -> web.Response:
    """Copy inline filter definitions from configuration.yaml to the managed files.

    Reads the inline ``include:``/``exclude:`` sub-keys from the recorder block
    and writes their contents to ``recorder_include.yaml`` and
    ``recorder_exclude.yaml``. Only filter data is copied — all other recorder
    settings (purge_keep_days, db_url, etc.) remain under user control in
    configuration.yaml.
    """
    try:
        setup = detect_setup_status(HA_CONFIG_FILE)
        if not (setup["inc_inline"] or setup["exc_inline"]):
            return web.json_response(
                {
                    "error": (
                        "No inline include/exclude filters found in "
                        "configuration.yaml. Nothing to migrate."
                    )
                },
                status=400,
            )

        result = detect_existing_filters(HA_CONFIG_FILE)
        yaml_writer.write_filters({
            "include": result["include"],
            "exclude": result["exclude"],
        })

        snippet = (
            "  include: !include recorder_include.yaml\n"
            "  exclude: !include recorder_exclude.yaml"
        )
        logger.info("Migration: inline filters copied to managed files")
        return web.json_response({"status": "ok", "snippet": snippet})
    except Exception as e:
        logger.error("Migration apply error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_save_filters(request: web.Request) -> web.Response:
    """Save new filter configuration (without applying)."""
    try:
        data = await request.json()
        _validate_filter_payload(data)
        yaml_writer.write_filters(data)
        return web.json_response({"status": "saved"})
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)
    except Exception as e:
        logger.error("Save filters error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_preview_filters(request: web.Request) -> web.Response:
    """Dry-run filter evaluation — return per-entity status without saving."""
    try:
        data = await request.json()
        include = data.get("include", {})
        exclude = data.get("exclude", {})

        db_stats = await db_reader.get_entity_stats()
        ha_entities = await entity_resolver.get_all_entities()
        all_entity_ids = set(db_stats.keys()) | ha_entities

        results = [
            {"entity_id": eid, "status": status, "reason": reason}
            for eid, (status, reason)
            in _evaluate_all_entities(all_entity_ids, include, exclude)
        ]

        return web.json_response({"entities": results})
    except Exception as e:
        logger.error("Preview error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_apply(request: web.Request) -> web.Response:
    """Write filters, validate config, and restart HA Core."""
    try:
        data = await request.json()
        _validate_filter_payload(data)

        # 1. Backup and write new filters
        yaml_writer.backup()
        yaml_writer.write_filters(data)

        # 2. Validate configuration
        check_result = await supervisor_api.check_config()
        if not check_result["success"]:
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
        try:
            yaml_writer.restore_backup()
        except Exception:
            pass
        return web.json_response({"error": str(e)}, status=500)


def _evaluate_all_entities(
    entity_ids: set, include: dict, exclude: dict
) -> list:
    """Evaluate filters for a set of entities.

    Returns a sorted list of (entity_id, (status, reason)) tuples.
    Shared by _merge_entities and handle_preview_filters.
    """
    return [
        (eid, filter_engine.evaluate(eid, include, exclude))
        for eid in sorted(entity_ids)
    ]


def _merge_entities(
    db_stats: dict, ha_entities: set, current_filters: dict
) -> list:
    """Merge DB stats with HA entity list and evaluate filters."""
    include = current_filters.get("include", {})
    exclude = current_filters.get("exclude", {})

    all_entity_ids = set(db_stats.keys()) | ha_entities
    merged = []

    for entity_id, (status, reason) in _evaluate_all_entities(
        all_entity_ids, include, exclude
    ):
        stats = db_stats.get(entity_id, {})
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        merged.append({
            "entity_id": entity_id,
            "domain": domain,
            "row_count": stats.get("row_count", 0),
            "size_bytes": stats.get("size_bytes", 0),
            "writes_per_minute": round(stats.get("writes_per_minute", 0.0), 4),
            "in_ha": entity_id in ha_entities,
            "in_db": entity_id in db_stats,
            "filter_status": status,
            "filter_reason": reason,
        })

    return merged


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application(middlewares=[ingress_security])

    # Shared HTTP client session — created once, reused across all requests
    async def on_startup(a: web.Application):
        a["client_session"] = aiohttp.ClientSession()

    async def on_cleanup(a: web.Application):
        await a["client_session"].close()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    # API routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/db/overview", handle_db_overview)
    app.router.add_get("/api/entities", handle_entities)
    app.router.add_get("/api/filters", handle_get_filters)
    app.router.add_post("/api/filters", handle_save_filters)
    app.router.add_post("/api/filters/preview", handle_preview_filters)
    app.router.add_post("/api/apply", handle_apply)
    # Setup wizard endpoints
    app.router.add_get("/api/setup/status", handle_setup_status)
    app.router.add_post("/api/setup/check", handle_setup_check)
    app.router.add_post("/api/setup/reboot", handle_setup_reboot)
    app.router.add_post("/api/setup/init-default", handle_setup_init_default)
    # Migration: copy inline filters to managed files
    app.router.add_post("/api/migration/apply", handle_migration_apply)

    # Static files
    app.router.add_static("/static/", STATIC_DIR, show_index=False)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8099)
