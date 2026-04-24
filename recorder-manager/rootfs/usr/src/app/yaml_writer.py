"""YAML file writer for recorder include/exclude filter definitions.

Manages two files:
  - recorder_include.yaml  — entities/domains/entity_globs to include
  - recorder_exclude.yaml  — entities/domains/entity_globs to exclude

Each file contains only the filter dict (no wrapping key), because the
files are loaded as sub-key values inside configuration.yaml::

    recorder:
      include: !include recorder_include.yaml
      exclude: !include recorder_exclude.yaml

File format example (recorder_include.yaml)::

    # Managed by Recorder Manager add-on
    entities:
      - sensor.temperature
    domains:
      - light

An empty/unconfigured file contains only the header comment.
``yaml.safe_load()`` of a comment-only file returns ``None``, which
``read_filters()`` handles as an empty section.
"""

import os
import shutil
import logging

import yaml

logger = logging.getLogger("recorder-manager.yaml_writer")

_HEADER = "# Managed by Recorder Manager add-on\n"


class YamlWriter:
    """Read and write the recorder include/exclude filter files."""

    def __init__(self, include_path: str, exclude_path: str):
        self.include_path = include_path
        self.exclude_path = exclude_path
        self.include_backup = include_path + ".bak"
        self.exclude_backup = exclude_path + ".bak"

    # ---- Read ----

    def read_filters(self) -> dict:
        """Read the current filter configuration from both files.

        Returns a dict with 'include' and 'exclude' keys.
        If a file doesn't exist or is empty (comment-only), returns {} for
        that section.
        """
        return {
            "include": self._read_file(self.include_path),
            "exclude": self._read_file(self.exclude_path),
        }

    def _read_file(self, path: str) -> dict:
        """Read a single filter file and return its contents as a dict."""
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            # safe_load returns None for comment-only or empty files
            if not isinstance(data, dict):
                return {}
            return data
        except Exception as e:
            logger.error("Failed to read filter file %s: %s", path, e)
            return {}

    # ---- Write ----

    def write_filters(self, filters: dict) -> None:
        """Write the filter configuration to both managed files.

        Args:
            filters: dict with 'include' and/or 'exclude' keys.
                     Each value is a dict with optional keys:
                     'entities', 'domains', 'entity_globs' (lists of strings).
        """
        include = filters.get("include", {}) or {}
        exclude = filters.get("exclude", {}) or {}
        self._write_section(self.include_path, include)
        self._write_section(self.exclude_path, exclude)
        logger.info(
            "Filter files written: %s, %s", self.include_path, self.exclude_path
        )

    def _write_section(self, path: str, section: dict) -> None:
        """Write a single filter section to disk.

        Always writes the header comment first. If the section has no
        meaningful content, the file contains only the header.
        All list values are sorted for deterministic output.

        Writes to a temporary file first, then atomically replaces the
        target path to prevent half-written files on crash.
        """
        output: dict = {}
        if section.get("entities"):
            output["entities"] = sorted(section["entities"])
        if section.get("domains"):
            output["domains"] = sorted(section["domains"])
        if section.get("entity_globs"):
            output["entity_globs"] = sorted(section["entity_globs"])

        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(_HEADER)
            if output:
                yaml.dump(
                    output,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
        os.replace(tmp_path, path)
        logger.debug(
            "Written %s (%d rules)",
            path,
            sum(len(v) for v in output.values()),
        )

    # ---- Defaults ----

    def create_defaults(self) -> dict:
        """Create both filter files with the header comment if they don't exist.

        Returns::

            {
              "include_status": "created" | "exists",
              "exclude_status": "created" | "exists",
            }
        """
        return {
            "include_status": self._create_default(self.include_path),
            "exclude_status": self._create_default(self.exclude_path),
        }

    def _create_default(self, path: str) -> str:
        """Create a header-only file if it doesn't exist. Returns status string."""
        if os.path.isfile(path):
            return "exists"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(_HEADER)
            logger.info("Created default filter file: %s", path)
            return "created"
        except Exception as e:
            logger.error("Failed to create default filter file %s: %s", path, e)
            raise

    # ---- Backup / Restore ----

    def backup(self) -> None:
        """Create backups of both filter files."""
        self._backup_file(self.include_path, self.include_backup)
        self._backup_file(self.exclude_path, self.exclude_backup)

    def restore_backup(self) -> None:
        """Restore both filter files from their backups."""
        self._restore_file(self.include_backup, self.include_path)
        self._restore_file(self.exclude_backup, self.exclude_path)

    def _backup_file(self, src: str, dst: str) -> None:
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            logger.info("Backup created: %s", dst)

    def _restore_file(self, src: str, dst: str) -> None:
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            logger.info("Backup restored: %s", dst)
        else:
            logger.warning("No backup file to restore: %s", src)
