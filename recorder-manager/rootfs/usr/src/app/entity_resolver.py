"""Discover all entities registered in Home Assistant via Supervisor API."""

import os
import logging
from contextlib import asynccontextmanager

import aiohttp

logger = logging.getLogger("recorder-manager.entity_resolver")


class EntityResolver:
    """Fetch all entity IDs from Home Assistant Core via the Supervisor proxy."""

    SUPERVISOR_URL = "http://supervisor/core/api/states"

    def _get_token(self) -> str:
        """Get the Supervisor API token."""
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            logger.warning("SUPERVISOR_TOKEN not set")
        return token

    @asynccontextmanager
    async def _session(self, session=None):
        """Yield an aiohttp session — reuse *session* if provided, else create one."""
        if session is not None:
            yield session
        else:
            async with aiohttp.ClientSession() as s:
                yield s

    async def get_all_entities(self, session=None) -> set:
        """Return a set of all entity_ids currently registered in HA.

        Args:
            session: Optional shared ``aiohttp.ClientSession``.
        """
        token = self._get_token()
        if not token:
            logger.warning(
                "No SUPERVISOR_TOKEN — returning empty entity set"
            )
            return set()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session(session) as s:
                async with s.get(
                    self.SUPERVISOR_URL,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.error(
                            "Failed to fetch states: HTTP %s", resp.status
                        )
                        return set()

                    states = await resp.json()
                    entity_ids = {
                        s["entity_id"]
                        for s in states
                        if "entity_id" in s
                    }
                    logger.info(
                        "Resolved %d entities from HA", len(entity_ids)
                    )
                    return entity_ids

        except Exception as e:
            logger.error("Entity resolution failed: %s", e)
            return set()

