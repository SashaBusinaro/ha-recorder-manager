"""YAML fragment writer for recorder include/exclude filters."""

import os
import shutil
import logging

import yaml

logger = logging.getLogger("recorder-manager.yaml_writer")


class YamlWriter:
    """Read and write the recorder_filters.yaml fragment."""

    def __init__(self, filter_file_path: str):
        self.path = filter_file_path
        self.backup_path = filter_file_path + ".bak"

    def read_filters(self) -> dict:
        """Read the current filter configuration from disk.

        Returns a dict with 'include' and 'exclude' keys.
        If the file doesn't exist, returns empty filters.
        """
        if not os.path.isfile(self.path):
            return {"include": {}, "exclude": {}}

        try:
            with open(self.path, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                return {"include": {}, "exclude": {}}

            return {
                "include": data.get("include", {}),
                "exclude": data.get("exclude", {}),
            }
        except Exception as e:
            logger.error("Failed to read filter file: %s", e)
            return {"include": {}, "exclude": {}}

    def write_filters(self, filters: dict) -> None:
        """Write the filter configuration to disk.

        Args:
            filters: dict with 'include' and/or 'exclude' keys.
        """
        include = filters.get("include", {})
        exclude = filters.get("exclude", {})

        # Build the output dict, omitting empty sections
        output = {}

        if include:
            inc = {}
            if include.get("entities"):
                inc["entities"] = sorted(include["entities"])
            if include.get("domains"):
                inc["domains"] = sorted(include["domains"])
            if include.get("entity_globs"):
                inc["entity_globs"] = sorted(include["entity_globs"])
            if inc:
                output["include"] = inc

        if exclude:
            exc = {}
            if exclude.get("entities"):
                exc["entities"] = sorted(exclude["entities"])
            if exclude.get("domains"):
                exc["domains"] = sorted(exclude["domains"])
            if exclude.get("entity_globs"):
                exc["entity_globs"] = sorted(exclude["entity_globs"])
            if exc:
                output["exclude"] = exc

        with open(self.path, "w") as f:
            if output:
                yaml.dump(
                    output,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            else:
                # Write an empty file (no filters)
                f.write("# No recorder filters configured\n")

        logger.info("Filter file written: %s", self.path)

    def backup(self) -> None:
        """Create a backup of the current filter file."""
        if os.path.isfile(self.path):
            shutil.copy2(self.path, self.backup_path)
            logger.info("Backup created: %s", self.backup_path)

    def restore_backup(self) -> None:
        """Restore the filter file from backup."""
        if os.path.isfile(self.backup_path):
            shutil.copy2(self.backup_path, self.path)
            logger.info("Backup restored: %s", self.path)
        else:
            logger.warning("No backup file to restore")
