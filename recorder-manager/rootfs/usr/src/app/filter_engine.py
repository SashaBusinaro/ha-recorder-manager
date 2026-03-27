"""Home Assistant recorder filter evaluation engine.

Implements the exact filter priority rules documented at:
https://www.home-assistant.io/integrations/recorder/#configure-filter

For each entity, returns both the status (included/excluded) and the
specific rule that caused that status (filter transparency).
"""

from fnmatch import fnmatch
from typing import Tuple


class FilterEngine:
    """Evaluate HA recorder include/exclude filters with full transparency."""

    def evaluate(
        self,
        entity_id: str,
        include: dict,
        exclude: dict,
    ) -> Tuple[str, str]:
        """
        Evaluate whether an entity is included or excluded.

        Returns:
            ("included"|"excluded", "human-readable reason")
        """
        inc_entities = set(include.get("entities", []))
        inc_domains = set(include.get("domains", []))
        inc_globs = list(include.get("entity_globs", []))

        exc_entities = set(exclude.get("entities", []))
        exc_domains = set(exclude.get("domains", []))
        exc_globs = list(exclude.get("entity_globs", []))

        domain = entity_id.split(".")[0] if "." in entity_id else ""

        has_inc = bool(inc_entities or inc_domains or inc_globs)
        has_exc = bool(exc_entities or exc_domains or exc_globs)

        has_inc_domain_or_glob = bool(inc_domains or inc_globs)
        has_exc_domain_or_glob = bool(exc_domains or exc_globs)

        # Case 1: No filters at all
        if not has_inc and not has_exc:
            return ("included", "no filters configured")

        # Case 2: Only includes (no excludes)
        if has_inc and not has_exc:
            return self._eval_only_includes(
                entity_id, domain,
                inc_entities, inc_domains, inc_globs,
            )

        # Case 3: Only excludes (no includes)
        if has_exc and not has_inc:
            return self._eval_only_excludes(
                entity_id, domain,
                exc_entities, exc_domains, exc_globs,
            )

        # Case 4: Domain/glob includes present (may also have excludes)
        if has_inc_domain_or_glob:
            return self._eval_inc_domain_glob_with_exc(
                entity_id, domain,
                inc_entities, inc_domains, inc_globs,
                exc_entities, exc_domains, exc_globs,
            )

        # Case 5: Domain/glob excludes only (no domain/glob includes)
        if has_exc_domain_or_glob:
            return self._eval_exc_domain_glob_no_inc(
                entity_id, domain,
                inc_entities,
                exc_entities, exc_domains, exc_globs,
            )

        # Case 6: Entity-level only (no domain/glob on either side)
        if entity_id in inc_entities:
            return ("included", "entity include")
        return ("excluded", "not in entity include list")

    def _eval_only_includes(
        self, entity_id, domain, inc_entities, inc_domains, inc_globs
    ):
        """Case 2: Only includes defined."""
        if entity_id in inc_entities:
            return ("included", "entity include")

        if domain in inc_domains:
            return ("included", f"domain include: {domain}")

        for glob in inc_globs:
            if fnmatch(entity_id, glob):
                return ("included", f"glob include: {glob}")

        return ("excluded", "not matched by any include rule")

    def _eval_only_excludes(
        self, entity_id, domain, exc_entities, exc_domains, exc_globs
    ):
        """Case 3: Only excludes defined."""
        if entity_id in exc_entities:
            return ("excluded", "entity exclude")

        if domain in exc_domains:
            return ("excluded", f"domain exclude: {domain}")

        for glob in exc_globs:
            if fnmatch(entity_id, glob):
                return ("excluded", f"glob exclude: {glob}")

        return ("included", "not matched by any exclude rule")

    def _eval_inc_domain_glob_with_exc(
        self, entity_id, domain,
        inc_entities, inc_domains, inc_globs,
        exc_entities, exc_domains, exc_globs,
    ):
        """Case 4: Domain/glob includes + any excludes."""
        # Priority 1: entity include
        if entity_id in inc_entities:
            return ("included", "entity include")

        # Priority 2: entity exclude
        if entity_id in exc_entities:
            return ("excluded", "entity exclude")

        # Priority 3: glob include
        for glob in inc_globs:
            if fnmatch(entity_id, glob):
                return ("included", f"glob include: {glob}")

        # Priority 4: glob exclude
        for glob in exc_globs:
            if fnmatch(entity_id, glob):
                return ("excluded", f"glob exclude: {glob}")

        # Priority 5: domain include
        if domain in inc_domains:
            return ("included", f"domain include: {domain}")

        # Default: exclude
        return ("excluded", "not matched by any include rule")

    def _eval_exc_domain_glob_no_inc(
        self, entity_id, domain,
        inc_entities,
        exc_entities, exc_domains, exc_globs,
    ):
        """Case 5: Domain/glob excludes, no domain/glob includes."""
        # Priority 1: entity include
        if entity_id in inc_entities:
            return ("included", "entity include")

        # Priority 2: entity exclude
        if entity_id in exc_entities:
            return ("excluded", "entity exclude")

        # Priority 3: glob exclude
        for glob in exc_globs:
            if fnmatch(entity_id, glob):
                return ("excluded", f"glob exclude: {glob}")

        # Priority 4: domain exclude
        if domain in exc_domains:
            return ("excluded", f"domain exclude: {domain}")

        # Default: include
        return ("included", "not matched by any exclude rule")
