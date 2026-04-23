"""Read-only parser for configuration.yaml to detect existing recorder filters.

Uses regex/text parsing because PyYAML cannot handle HA-specific tags like
!include, !include_dir_merge_named, etc.

Setup scenarios
---------------
1. **Complete** — Both sub-keys are managed inside the ``recorder:`` block::

       include: !include recorder_include.yaml
       exclude: !include recorder_exclude.yaml

   No wizard or banner is shown.

2. **Migration** — Inline ``include:``/``exclude:`` blocks with sub-keys exist
   inside the ``recorder:`` block. The migration wizard copies those filter
   definitions into the managed files.

3. **Fresh setup** — No ``recorder:`` block at all, or a block with no
   ``include``/``exclude`` sub-keys. The fresh-setup wizard creates both
   managed files and asks the user to add the two sub-key lines.

HA YAML support for !include in sub-key value positions
--------------------------------------------------------
HA's YAML loader resolves ``!include`` for any value position::

    recorder:
      include: !include recorder_include.yaml   # VALID
      exclude: !include recorder_exclude.yaml   # VALID

Each managed file contains only the raw filter dict for its direction
(entities/domains/entity_globs), not wrapped in any enclosing key.
"""

import re
import logging

import yaml

logger = logging.getLogger("recorder-manager.config_reader")

# Match the managed sub-key lines within the recorder block
_INC_MANAGED_RE = re.compile(
    r"^\s*include:\s*!include\s+recorder_include\.yaml\s*$",
    re.MULTILINE,
)
_EXC_MANAGED_RE = re.compile(
    r"^\s*exclude:\s*!include\s+recorder_exclude\.yaml\s*$",
    re.MULTILINE,
)


def _extract_recorder_block(text: str) -> str | None:
    """Extract the raw indented block content under ``recorder:`` in *text*.

    Returns the block as a string (without the ``recorder:`` key line), or
    None if no such block is found.
    """
    lines = text.splitlines()
    recorder_start = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("recorder:") and indent == 0:
            recorder_start = i + 1
            break

    if recorder_start is None:
        return None

    block_lines = []
    for line in lines[recorder_start:]:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            block_lines.append(line)
            continue
        indent = len(line) - len(stripped)
        if indent == 0:
            break
        block_lines.append(line)

    return "\n".join(block_lines)


def _parse_filter_block(block_text: str, section: str) -> dict:
    """Parse inline include or exclude sub-keys from the recorder block text.

    Returns a dict with keys: entities, domains, entity_globs (as lists).
    Ignores any ``!include`` directives — only reads inline values.
    """
    result: dict = {}
    lines = block_text.splitlines()
    in_section = False
    current_subkey = None
    section_indent = None

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        if stripped.startswith(f"{section}:"):
            # Skip managed !include lines — they have no inline children
            if "!include" in stripped:
                continue
            in_section = True
            section_indent = indent
            continue

        if in_section:
            if indent <= section_indent and stripped and not stripped.startswith("#"):
                in_section = False
                current_subkey = None

            if in_section:
                subkey_match = re.match(r"(\w+):", stripped)
                if subkey_match:
                    current_subkey = subkey_match.group(1)
                    result[current_subkey] = []
                    continue

                list_match = re.match(r"-\s+(.+)", stripped)
                if list_match and current_subkey is not None:
                    result[current_subkey].append(list_match.group(1).strip())

    return result


def detect_existing_filters(ha_config_path: str) -> dict:
    """Extract inline include/exclude filter definitions from configuration.yaml.

    Used by the migration wizard to read inline filter definitions so they
    can be written to the managed files.

    Returns::

        {
          "has_filters": bool,
          "include": dict,   # {entities: [], domains: [], entity_globs: []}
          "exclude": dict,
        }
    """
    try:
        with open(ha_config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        logger.warning("configuration.yaml not found at %s", ha_config_path)
        return {"has_filters": False, "include": {}, "exclude": {}}
    except Exception as e:
        logger.error("Failed to read configuration.yaml: %s", e)
        return {"has_filters": False, "include": {}, "exclude": {}}

    recorder_block = _extract_recorder_block(content)
    if recorder_block is None:
        return {"has_filters": False, "include": {}, "exclude": {}}

    include = _parse_filter_block(recorder_block, "include")
    exclude = _parse_filter_block(recorder_block, "exclude")

    return {
        "has_filters": bool(include or exclude),
        "include": include,
        "exclude": exclude,
    }


def detect_setup_status(ha_config_path: str) -> dict:
    """Determine which setup scenario applies for configuration.yaml.

    Returns::

        {
          "inc_managed": bool,        # include: !include recorder_include.yaml found
          "exc_managed": bool,        # exclude: !include recorder_exclude.yaml found
          "inc_inline":  bool,        # inline include: block with sub-keys exists
          "exc_inline":  bool,        # inline exclude: block with sub-keys exists
          "has_recorder_block": bool, # any recorder: block exists
        }

    Scenarios:
      - inc_managed AND exc_managed        → setup complete
      - inc_inline OR exc_inline           → migration needed
      - neither                            → fresh setup needed
    """
    _empty = {
        "inc_managed": False, "exc_managed": False,
        "inc_inline": False, "exc_inline": False,
        "has_recorder_block": False,
    }

    try:
        with open(ha_config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        logger.warning("configuration.yaml not found at %s", ha_config_path)
        return _empty
    except Exception as e:
        logger.error("Failed to read configuration.yaml: %s", e)
        return _empty

    recorder_block = _extract_recorder_block(content)
    has_recorder_block = recorder_block is not None and recorder_block.strip() != ""

    if not has_recorder_block:
        return {**_empty, "has_recorder_block": False}

    # Detect managed sub-keys by searching inside the recorder block
    inc_managed = bool(_INC_MANAGED_RE.search(recorder_block))
    exc_managed = bool(_EXC_MANAGED_RE.search(recorder_block))

    # Detect inline filter definitions (only when the sub-key is not managed)
    inc_inline = False
    exc_inline = False
    if not inc_managed:
        inc_inline = bool(_parse_filter_block(recorder_block, "include"))
    if not exc_managed:
        exc_inline = bool(_parse_filter_block(recorder_block, "exclude"))

    return {
        "inc_managed": inc_managed,
        "exc_managed": exc_managed,
        "inc_inline": inc_inline,
        "exc_inline": exc_inline,
        "has_recorder_block": has_recorder_block,
    }
