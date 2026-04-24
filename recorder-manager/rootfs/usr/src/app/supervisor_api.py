"""Supervisor API client for config validation and HA Core restart."""

import os
import logging
from contextlib import asynccontextmanager

import aiohttp

logger = logging.getLogger("recorder-manager.supervisor_api")


class SupervisorApi:
    """Interact with the HA Supervisor API."""

    BASE_URL = "http://supervisor"

    def _get_headers(self) -> dict:
        """Build authorization headers using SUPERVISOR_TOKEN."""
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @asynccontextmanager
    async def _session(self, session=None):
        """Yield an aiohttp session — reuse *session* if provided, else create one."""
        if session is not None:
            yield session
        else:
            async with aiohttp.ClientSession() as s:
                yield s

    async def check_config(self, session=None) -> dict:
        """Validate the Home Assistant configuration.

        POST /core/check

        Returns:
            {"success": True/False, "message": "..."}
        """
        try:
            async with self._session(session) as s:
                async with s.post(
                    f"{self.BASE_URL}/core/check",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json()
                    result = data.get("result", "")

                    if result == "ok":
                        logger.info("Configuration check passed")
                        return {"success": True, "message": "Config valid"}

                    message = data.get("message", "Unknown error")
                    logger.warning("Configuration check failed: %s", message)
                    return {"success": False, "message": message}

        except Exception as e:
            logger.error("Config check request failed: %s", e)
            return {"success": False, "message": str(e)}

    async def restart_core(self, session=None) -> dict:
        """Restart Home Assistant Core.

        POST /core/restart

        Returns:
            {"success": True/False, "message": "..."}
        """
        try:
            async with self._session(session) as s:
                async with s.post(
                    f"{self.BASE_URL}/core/restart",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json()
                    result = data.get("result", "")

                    if result == "ok":
                        logger.info("HA Core restart initiated")
                        return {
                            "success": True,
                            "message": "Restart initiated",
                        }

                    message = data.get("message", "Unknown error")
                    logger.warning("Restart failed: %s", message)
                    return {"success": False, "message": message}

        except Exception as e:
            logger.error("Restart request failed: %s", e)
            return {"success": False, "message": str(e)}

