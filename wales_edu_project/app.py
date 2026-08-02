"""
YAGO2geo native relation-instance completeness report
======================================================

Produces a self-contained HTML report for two scopes:
1. UK-wide data available in the Neo4j model
2. Wales (22 Welsh unitary authorities)

Rows evaluated:
- Ward -> Ward: TOUCHES
- Community -> Community: TOUCHES
- UnitaryAuthority -> Ward: WITHIN / CONTAINS inverse

Method:
- Geometry-derived relations are the reference set (Omega).
- Native Neo4j relations are the asserted set (O).
- Row completeness = |native ∩ geometry-reference| / |geometry-reference|.
- Scope relation-instance completeness for these rows
  (distinct from the model-level SpCom over the eight SCQs) =
    sum(matched reference instances) / sum(reference instances).

The script is READ ONLY. It never creates, deletes, or updates Neo4j data.

Run configuration:
- Set DATABASE_MODE near the top of this file.
- LOCAL evaluates local Neo4j only.
- CLOUD evaluates Neo4j Aura only.
- BOTH evaluates both databases and creates a comparison.
- Connection settings are stored directly in LOCAL_CONFIG and CLOUD_CONFIG.
- No PowerShell runner or environment variables are required.
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from neo4j import GraphDatabase
    from pyproj import Transformer
    from shapely import wkt
    from shapely.geometry.base import BaseGeometry
    from shapely.ops import transform
    from shapely.strtree import STRtree
    from shapely.validation import make_valid
except ImportError as exc:
    raise SystemExit(
        "Missing package. Run:\n"
        "pip install neo4j shapely pyproj\n\n"
        f"Original error: {exc}"
    )


# ==========================================================
# DATABASE AND REPORT CONFIGURATION
# ==========================================================

# Choose one:
# "LOCAL" = local Neo4j only
# "CLOUD" = Neo4j Aura only
# "BOTH"  = local and cloud, followed by a comparison
DATABASE_MODE = "CLOUD"   # the local database still holds the old adjacency


# ----------------------------------------------------------
# Local Neo4j connection
# ----------------------------------------------------------
LOCAL_CONFIG = {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": os.environ.get("NEO4J_LOCAL_PASSWORD", "QWEasd1QWE"),
    "database": "wales-education-kg",
}


# ----------------------------------------------------------
# Neo4j Aura connection
# ----------------------------------------------------------
CLOUD_CONFIG = {
    "uri": "neo4j+s://1e982852.databases.neo4j.io",
    "user": "1e982852",
    "password": os.environ.get("NEO4J_CLOUD_PASSWORD", "4kbPrn_-FsWEKiZTsuCnu5xvotFjME8q6W0dLN7JD3k"),
    "database": "1e982852",
}


CARDIFF_OS_ID = "25484"

# Official Welsh unitary-authority OS IDs used to distinguish Wales from UK-wide.
WELSH_UA_OS_IDS = {
    "25492", "25494", "25502", "25484", "25496", "44426",
    "25498", "25493", "25483", "25497", "25495", "25491",
    "25500", "25490", "25485", "25487", "25489", "25486",
    "25482", "25776", "44425", "25831",
}

# The Wales Euro Region node. Some Welsh units reach this and nothing else:
# of the 396 nodes typed OS_COMMUNITYWARD, only 204 reach a Welsh unitary
# authority through WITHIN within three hops, 114 have the region as their
# only ancestor, and 78 carry no WITHIN edge at all. Selecting Wales by a
# path to an authority alone therefore drops 48.5% of Welsh community wards,
# which is why the In Wales column split roughly in half.
WALES_EURO_REGION_OS_ID = "41424"

# Source classes that exist only in Wales. Membership by class is the fallback
# for the units that carry no usable WITHIN path at all.
WELSH_ONLY_RAW_TYPES = {
    "OS_COMMUNITYWARD",
    "OS_COMMUNITY",
    "OS_CCOMMUNITY",
}

# The six classes that fell through map_os_type untouched. They were absent
# from every audited row even though the European Region alone is the parent
# of more than half the Welsh WITHIN relations. Only the region has Welsh
# instances; the other five are English and are audited in the UK scope only.
UNNORMALISED_PARENT_TYPES = {
    "OS_EuropeanRegion",
    "OS_County",
    "OS_District",
    "OS_MetropolitanDistrict",
    "OS_LondonBorough",
    "OS_GreaterLondonAuthority",
}
ENGLISH_ONLY_PARENT_TYPES = UNNORMALISED_PARENT_TYPES - {"OS_EuropeanRegion"}

# Boundary tolerance applied only to DISJOINT polygon pairs.
TOUCH_TOLERANCE_METRES = 1.0
VERIFICATION_SAMPLE_SIZE = 10


OUTPUT_FILES = {
    "LOCAL": "yago2geo_completeness_local.html",
    "CLOUD": "yago2geo_completeness_cloud.html",
    "BOTH": "yago2geo_local_cloud_completeness_report.html",
}

# Raw YAGO2geo/OS naming variants that correspond to the two target levels.
# Other classes such as OS_District, OS_County and OS_LondonBorough are NOT
# silently folded into Ward or Community.
TYPE_GROUPS = {
    "Community": {"Community", "OS_COMMUNITY", "OS_CCOMMUNITY"},
    "Ward": {"Ward", "OS_COMMUNITYWARD"},
}
TYPE_GROUPS["Ward-Community"] = TYPE_GROUPS["Ward"] | TYPE_GROUPS["Community"]
UA_TYPES = {"UnitaryAuthority"}

WGS84_TO_BNG = Transformer.from_crs(
    "EPSG:4326", "EPSG:27700", always_xy=True
).transform


@dataclass(frozen=True)
class Unit:
    uri: str
    os_id: str | None
    name: str | None
    raw_type: str | None
    wkt_text: str | None
    # NEW: the true pre-normalisation raw type (e.g. "OS_COMMUNITY",
    # "OS_CivilParishorCommunity"), read from the a.raw_type property
    # added by load_to_neo4j.py. None if the database has not been
    # reloaded since that change, or for node types that predate it.
    # NOTE: the existing `raw_type` field above is actually the
    # NORMALISED type ("Ward"/"Community"/"UnitaryAuthority") despite
    # its name — kept as-is so existing code that reads it is untouched.
    db_raw_type: str | None = None

    @property
    def key(self) -> str:
        # FIX: index by URI, never by os_id.
        # OS IDs are NOT unique across units: id 101 belongs both to
        # Llanblethian East (Vale of Glamorgan) and Abbey Ward (Birmingham).
        # Keying on os_id collapsed distinct units, so one unit's geometry was
        # compared against another unit's asserted TOUCHES edges, which
        # produced impossible "Extra" pairs. The URI is unique by construction.
        return f"uri:{self.uri}"


def env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing {name}. Set NEO4J_URI, NEO4J_USER, "
            "NEO4J_PASSWORD and NEO4J_DATABASE."
        )
    return value


def clean_wkt(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    for prefix in (
        "<http://www.opengis.net/def/crs/EPSG/0/4326>",
        "<HTTP://WWW.OPENGIS.NET/DEF/CRS/EPSG/0/4326>",
    ):
        text = text.replace(prefix, "")
    text = text.strip()
    if text.upper().startswith("DATA TRUNCATED "):
        text = text[len("DATA TRUNCATED "):].strip()
    return text or None


def parse_geometry(value: Any) -> BaseGeometry:
    text = clean_wkt(value)
    if not text:
        raise ValueError("missing WKT")
    geom = make_valid(wkt.loads(text))
    if geom.is_empty:
        raise ValueError("empty geometry")
    return make_valid(transform(WGS84_TO_BNG, geom))


def unit_from_record(record: Any) -> Unit:
    has_db_raw_type = "db_raw_type" in record.keys()
    return Unit(
        uri=str(record["uri"]),
        os_id=str(record["os_id"]).strip() if record["os_id"] is not None else None,
        name=str(record["name"]) if record["name"] is not None else None,
        raw_type=str(record["type"]) if record["type"] is not None else None,
        wkt_text=str(record["wkt"]) if record["wkt"] is not None else None,
        db_raw_type=(
            str(record["db_raw_type"])
            if has_db_raw_type and record["db_raw_type"] is not None
            else None
        ),
    )


def deduplicate(units: Iterable[Unit]) -> tuple[list[Unit], list[dict[str, Any]]]:
    """Deduplicate by OS ID when available, otherwise URI."""
    chosen: dict[str, Unit] = {}
    audit: list[dict[str, Any]] = []

    def score(unit: Unit) -> tuple[int, int]:
        return (
            1 if unit.wkt_text else 0,
            1 if not (unit.raw_type or "").startswith("OS_") else 0,
        )

    for unit in units:
        current = chosen.get(unit.key)
        if current is None:
            chosen[unit.key] = unit
            continue

        keep, other = (unit, current) if score(unit) > score(current) else (current, unit)
        chosen[unit.key] = keep
        audit.append(
            {
                "stable_key": unit.key,
                "kept_name": keep.name,
                "kept_type": keep.raw_type,
                "other_name": other.name,
                "other_type": other.raw_type,
            }
        )

    return list(chosen.values()), audit


def prepare_geometries(
    units: list[Unit],
) -> tuple[list[Unit], list[BaseGeometry], list[dict[str, Any]]]:
    """
    Parse and project geometries without allowing one bad record to stop the report.

    Diagnostics include excluded records and retained warnings.
    """
    valid_units: list[Unit] = []
    geoms: list[BaseGeometry] = []
    diagnostics: list[dict[str, Any]] = []

    for unit in units:
        try:
            geom = parse_geometry(unit.wkt_text)
            geoms.append(geom)
            valid_units.append(unit)

            boundary = geom.boundary
            if geom.geom_type == "GeometryCollection":
                diagnostics.append(
                    {
                        "key": unit.key,
                        "name": unit.name,
                        "raw_type": unit.raw_type,
                        "severity": "Warning",
                        "action": "Retained",
                        "geometry_type": geom.geom_type,
                        "error": (
                            "Geometry became a GeometryCollection after repair. "
                            "Exact topology is attempted; boundary-tolerance testing "
                            "may be unavailable."
                        ),
                    }
                )
            elif boundary is None or boundary.is_empty:
                diagnostics.append(
                    {
                        "key": unit.key,
                        "name": unit.name,
                        "raw_type": unit.raw_type,
                        "severity": "Warning",
                        "action": "Retained",
                        "geometry_type": geom.geom_type,
                        "error": (
                            "Geometry has no usable boundary. Exact topology is "
                            "attempted, but boundary-tolerance testing is skipped."
                        ),
                    }
                )
        except Exception as exc:
            diagnostics.append(
                {
                    "key": unit.key,
                    "name": unit.name,
                    "raw_type": unit.raw_type,
                    "severity": "Failure",
                    "action": "Excluded",
                    "geometry_type": None,
                    "error": str(exc),
                }
            )

    return valid_units, geoms, diagnostics


def geometry_touch_pairs(
    units: list[Unit],
) -> tuple[
    set[tuple[str, str]],
    set[tuple[str, str]],
    set[tuple[str, str]],
    set[tuple[str, str]],
    list[dict[str, Any]],
]:
    """
    Return:
      adjusted_pairs: exact touches + disjoint boundary gaps <= tolerance
      exact_pairs: exact Shapely touches only
      tolerance_pairs: disjoint near-touch pairs added by tolerance
      rejected_pairs: overlapping/containing pairs rejected from TOUCHES
      diagnostics
    """
    valid_units, geoms, diagnostics = prepare_geometries(units)
    if not geoms:
        return set(), set(), set(), set(), diagnostics

    tree = STRtree(geoms)
    exact_pairs: set[tuple[str, str]] = set()
    tolerance_pairs: set[tuple[str, str]] = set()
    rejected_pairs: set[tuple[str, str]] = set()

    for i, geom in enumerate(geoms):
        key_a = valid_units[i].key
        candidates = tree.query(geom.buffer(TOUCH_TOLERANCE_METRES))
        for candidate in candidates:
            j = int(candidate)
            if i == j:
                continue
            key_b = valid_units[j].key
            if key_a >= key_b:
                continue

            other = geoms[j]
            pair = (key_a, key_b)

            try:
                if geom.touches(other):
                    exact_pairs.add(pair)
                    continue

                # Overlap/containment is not TOUCHES, even when boundary distance is zero.
                if not geom.disjoint(other):
                    rejected_pairs.add(pair)
                    continue

                boundary_a = geom.boundary
                boundary_b = other.boundary
                if (
                    boundary_a is None
                    or boundary_b is None
                    or boundary_a.is_empty
                    or boundary_b.is_empty
                ):
                    continue

                if boundary_a.distance(boundary_b) <= TOUCH_TOLERANCE_METRES:
                    tolerance_pairs.add(pair)

            except Exception as exc:
                diagnostics.append(
                    {
                        "key": key_a,
                        "name": valid_units[i].name,
                        "raw_type": valid_units[i].raw_type,
                        "severity": "Warning",
                        "action": "Pair skipped",
                        "geometry_type": geom.geom_type,
                        "other_key": key_b,
                        "other_name": valid_units[j].name,
                        "error": f"TOUCHES/tolerance test failed: {exc}",
                    }
                )

    adjusted_pairs = exact_pairs | tolerance_pairs
    return adjusted_pairs, exact_pairs, tolerance_pairs, rejected_pairs, diagnostics

def geometry_ua_ward_pairs(
    uas: list[Unit],
    wards: list[Unit],
) -> tuple[set[tuple[str, str]], list[dict[str, Any]]]:
    """Compute all geometry-contained UA -> Ward pairs efficiently."""
    valid_uas, ua_geoms, ua_failures = prepare_geometries(uas)
    valid_wards, ward_geoms, ward_failures = prepare_geometries(wards)
    failures = [
        {**row, "level": "UnitaryAuthority"} for row in ua_failures
    ] + [{**row, "level": "Ward"} for row in ward_failures]

    if not ua_geoms or not ward_geoms:
        return set(), failures

    ward_tree = STRtree(ward_geoms)
    pairs: set[tuple[str, str]] = set()

    for ua_idx, ua_geom in enumerate(ua_geoms):
        ua_key = valid_uas[ua_idx].key
        for candidate in ward_tree.query(ua_geom):
            j = int(candidate)
            ward_geom = ward_geoms[j]
            if ua_geom.covers(ward_geom) or ward_geom.within(ua_geom):
                pairs.add((ua_key, valid_wards[j].key))

    return pairs, failures


def native_touch_pairs(
    session,
    allowed_types: set[str],
    scope: str,
) -> set[tuple[str, str]]:
    if scope == "Cardiff":
        query = """
        MATCH (a:AdminUnit)-[:WITHIN*1..3]->(ua:AdminUnit)
        MATCH (b:AdminUnit)-[:WITHIN*1..3]->(ua)
        WHERE ua.os_id = $cardiff_os_id
          AND ua.type = 'UnitaryAuthority'
          AND a.type IN $types
          AND b.type IN $types
          AND a.uri < b.uri
          AND (a)-[:TOUCHES]-(b)
        RETURN DISTINCT a.uri AS a_uri, a.os_id AS a_os_id,
                        b.uri AS b_uri, b.os_id AS b_os_id
        """
        params = {"cardiff_os_id": CARDIFF_OS_ID, "types": sorted(allowed_types)}

    elif scope == "Wales":
        # Both endpoints are taken from the three-layer membership set. The
        # earlier form required each endpoint to reach a Welsh authority in
        # three WITHIN hops, which excluded 192 of the 396 Welsh community
        # wards and therefore also every pair they belong to.
        query = """
        MATCH (a:AdminUnit)-[:TOUCHES]-(b:AdminUnit)
        WHERE a.uri IN $welsh_uris
          AND b.uri IN $welsh_uris
          AND a.type IN $types
          AND b.type IN $types
          AND a.uri < b.uri
        RETURN DISTINCT a.uri AS a_uri, a.os_id AS a_os_id,
                        b.uri AS b_uri, b.os_id AS b_os_id
        """
        params = {
            "welsh_uris": sorted(fetch_welsh_uris(session)),
            "types": sorted(allowed_types),
        }

    else:
        query = """
        MATCH (a:AdminUnit)-[:TOUCHES]-(b:AdminUnit)
        WHERE a.type IN $types
          AND b.type IN $types
          AND a.uri < b.uri
        RETURN DISTINCT a.uri AS a_uri, a.os_id AS a_os_id,
                        b.uri AS b_uri, b.os_id AS b_os_id
        """
        params = {"types": sorted(allowed_types)}

    pairs: set[tuple[str, str]] = set()
    for row in session.run(query, **params):
        # FIX: key by URI only - os_id is not unique across units.
        a = f"uri:{row['a_uri']}"
        b = f"uri:{row['b_uri']}"
        pairs.add(tuple(sorted((a, b))))
    return pairs


def native_ua_ward_pairs(session, scope: str) -> set[tuple[str, str]]:
    if scope == "Cardiff":
        query = """
        MATCH (w:AdminUnit)-[:WITHIN]->(ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority'
          AND ua.os_id = $cardiff_os_id
          AND w.type IN $ward_types
        RETURN DISTINCT ua.uri AS ua_uri, ua.os_id AS ua_os_id,
                        w.uri AS w_uri, w.os_id AS w_os_id
        """
        params = {
            "cardiff_os_id": CARDIFF_OS_ID,
            "ward_types": sorted(TYPE_GROUPS["Ward"]),
        }
    elif scope == "Wales":
        # Containment is asserted directly against the authority, so this
        # filter is the right one here and is left as it was.
        query = """
        MATCH (w:AdminUnit)-[:WITHIN]->(ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority'
          AND ua.os_id IN $welsh_os_ids
          AND w.type IN $ward_types
        RETURN DISTINCT ua.uri AS ua_uri, ua.os_id AS ua_os_id,
                        w.uri AS w_uri, w.os_id AS w_os_id
        """
        params = {
            "welsh_os_ids": sorted(WELSH_UA_OS_IDS),
            "ward_types": sorted(TYPE_GROUPS["Ward"]),
        }
    else:
        query = """
        MATCH (w:AdminUnit)-[:WITHIN]->(ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority'
          AND w.type IN $ward_types
        RETURN DISTINCT ua.uri AS ua_uri, ua.os_id AS ua_os_id,
                        w.uri AS w_uri, w.os_id AS w_os_id
        """
        params = {"ward_types": sorted(TYPE_GROUPS["Ward"])}

    pairs: set[tuple[str, str]] = set()
    for row in session.run(query, **params):
        # FIX: key by URI only - os_id is not unique across units.
        ua = f"uri:{row['ua_uri']}"
        ward = f"uri:{row['w_uri']}"
        pairs.add((ua, ward))
    return pairs


def native_within_pairs_generic(
    session,
    child_types: set[str],
    parent_types: set[str],
    scope: str,
) -> set[tuple[str, str]]:
    """Directly asserted child-[:WITHIN]->parent pairs for any level pair.

    Returned as (parent_key, child_key) so the ordering matches the
    UnitaryAuthority-to-Ward row that already exists.
    """
    where_scope = ""
    params: dict[str, Any] = {
        "child_types": sorted(child_types),
        "parent_types": sorted(parent_types),
    }
    if scope == "Wales":
        where_scope = "AND c.uri IN $welsh_uris AND p.uri IN $welsh_uris"
        params["welsh_uris"] = sorted(fetch_welsh_uris(session))

    records = session.run(
        f"""
        MATCH (c:AdminUnit)-[:WITHIN]->(p:AdminUnit)
        WHERE c.type IN $child_types
          AND p.type IN $parent_types
          {where_scope}
        RETURN DISTINCT p.uri AS p_uri, p.os_id AS p_os_id,
                        c.uri AS c_uri, c.os_id AS c_os_id
        """,
        **params,
    )
    pairs: set[tuple[str, str]] = set()
    for record in records:
        parent_key = f"uri:{record['p_uri']}"
        child_key = f"uri:{record['c_uri']}"
        pairs.add((parent_key, child_key))
    return pairs


def containment_row(
    session,
    scope: str,
    parent_label: str,
    child_label: str,
    parents: list[Unit],
    children: list[Unit],
    parent_types: set[str],
    child_types: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], set, set]:
    """Score one containment level pair the same way UA-to-Ward is scored.

    The original report audited only UnitaryAuthority to Ward, which covers
    204 of the 2,489 asserted WITHIN relations inside Wales - 8.2%. Every
    other level pair, including the European Region parent that carries more
    than half of the Welsh hierarchy, went untested. This builds a row for
    any pair of levels so the table can cover them all.
    """
    reference, failures = geometry_ua_ward_pairs(parents, children)
    native = native_within_pairs_generic(
        session, child_types, parent_types, scope
    )
    matched = reference & native
    missing = reference - native
    extra = native - reference

    denominator = len(reference)
    score = len(matched) / denominator if denominator else None
    row = {
        "domain": parent_label,
        "range": child_label,
        "relation": "CONTAINS / WITHIN inverse",
        "normalised_nodes": len(parents) + len(children),
        "reference_instances": denominator,
        "native_instances": len(native),
        "matched_instances": len(matched),
        "missing_instances": len(missing),
        "extra_instances": len(extra),
        "rejected_duplicate": None,
        "rejected_detached_part": None,
        "rejected_partial_overlap": None,
        "exact_touch_instances": None,
        "tolerance_added": None,
        "rejected_overlap_or_containment": None,
        "completeness_ratio": score,
        "completeness_percent": score * 100 if score is not None else None,
        "status": "Complete" if denominator and not missing else (
            "Gap" if denominator else "Cannot score"
        ),
    }
    return row, failures, missing, extra


def fetch_scope_units(session, scope: str) -> dict[str, list[Unit]]:
    target_types = sorted(TYPE_GROUPS["Community"] | TYPE_GROUPS["Ward"])

    if scope == "Cardiff":
        rows = list(
            session.run(
                """
                MATCH (n:AdminUnit)-[:WITHIN*1..3]->(ua:AdminUnit)
                WHERE ua.type = 'UnitaryAuthority'
                  AND ua.os_id = $cardiff_os_id
                  AND n.type IN $types
                RETURN DISTINCT n.uri AS uri, n.os_id AS os_id,
                       n.name AS name, n.type AS type, n.raw_type AS db_raw_type, n.wkt AS wkt
                """,
                cardiff_os_id=CARDIFF_OS_ID,
                types=target_types,
            )
        )
        ua_rows = list(
            session.run(
                """
                MATCH (ua:AdminUnit)
                WHERE ua.type = 'UnitaryAuthority'
                  AND ua.os_id = $cardiff_os_id
                RETURN DISTINCT ua.uri AS uri, ua.os_id AS os_id,
                       ua.name AS name, ua.type AS type, ua.raw_type AS db_raw_type, ua.wkt AS wkt
                """,
                cardiff_os_id=CARDIFF_OS_ID,
            )
        )

    elif scope == "Wales":
        # Selected from the three-layer membership set rather than from a
        # 3-hop WITHIN path, which reached only 204 of the 396 Welsh
        # community wards.
        welsh_uris = sorted(fetch_welsh_uris(session))
        rows = list(
            session.run(
                """
                MATCH (n:AdminUnit)
                WHERE n.uri IN $welsh_uris
                  AND n.type IN $types
                RETURN DISTINCT n.uri AS uri, n.os_id AS os_id,
                       n.name AS name, n.type AS type, n.raw_type AS db_raw_type, n.wkt AS wkt
                """,
                welsh_uris=welsh_uris,
                types=target_types,
            )
        )
        ua_rows = list(
            session.run(
                """
                MATCH (ua:AdminUnit)
                WHERE ua.type = 'UnitaryAuthority'
                  AND ua.os_id IN $welsh_os_ids
                RETURN DISTINCT ua.uri AS uri, ua.os_id AS os_id,
                       ua.name AS name, ua.type AS type, ua.raw_type AS db_raw_type, ua.wkt AS wkt
                """,
                welsh_os_ids=sorted(WELSH_UA_OS_IDS),
            )
        )

    else:
        rows = list(
            session.run(
                """
                MATCH (n:AdminUnit)
                WHERE n.type IN $types
                RETURN DISTINCT n.uri AS uri, n.os_id AS os_id,
                       n.name AS name, n.type AS type, n.raw_type AS db_raw_type, n.wkt AS wkt
                """,
                types=target_types,
            )
        )
        ua_rows = list(
            session.run(
                """
                MATCH (ua:AdminUnit)
                WHERE ua.type = 'UnitaryAuthority'
                RETURN DISTINCT ua.uri AS uri, ua.os_id AS os_id,
                       ua.name AS name, ua.type AS type, ua.raw_type AS db_raw_type, ua.wkt AS wkt
                """
            )
        )

    # The European Region is the parent of more than half of the Welsh WITHIN
    # relations, so it has to be loaded even though it was never normalised.
    region_rows = list(
        session.run(
            """
            MATCH (r:AdminUnit)
            WHERE r.type IN $parent_types AND r.wkt IS NOT NULL
            RETURN DISTINCT r.uri AS uri, r.os_id AS os_id,
                   r.name AS name, r.type AS type,
                   r.raw_type AS db_raw_type, r.wkt AS wkt
            """,
            parent_types=sorted(UNNORMALISED_PARENT_TYPES),
        )
    )

    all_units = [unit_from_record(row) for row in rows]
    uas = [unit_from_record(row) for row in ua_rows]
    regions = [unit_from_record(row) for row in region_rows]
    if scope == "Wales":
        regions = [r for r in regions if r.os_id == WALES_EURO_REGION_OS_ID]
    # Unit.raw_type carries the NORMALISED type despite its name, and the
    # six unnormalised classes keep their source name there, which is exactly
    # what is needed to group them.
    parents_by_type: dict[str, list[Unit]] = {}
    for region in regions:
        parents_by_type.setdefault(str(region.raw_type), []).append(region)

    communities, community_dups = deduplicate(
        u for u in all_units if u.raw_type in TYPE_GROUPS["Community"]
    )
    wards, ward_dups = deduplicate(
        u for u in all_units if u.raw_type in TYPE_GROUPS["Ward"]
    )
    uas, ua_dups = deduplicate(uas)

    regions, region_dups = deduplicate(regions)

    return {
        "Community": communities,
        "Ward": wards,
        "UnitaryAuthority": uas,
        "EuropeanRegion": [
            r for r in regions if r.raw_type == "OS_EuropeanRegion"
        ],
        "parents_by_type": parents_by_type,
        "duplicates": community_dups + ward_dups + ua_dups + region_dups,
        "raw_units": all_units,
    }

def boundary_gap_metres(unit_a: Unit | None, unit_b: Unit | None) -> str:
    """Gap between the two boundaries, in metres.

    Returns a formatted number when both geometries parse, otherwise "-".
    Reading the value:
      0        -> boundaries meet exactly (a true TOUCHES)
      <= 1     -> sub-metre gap, i.e. a digitisation artefact
      large    -> the units are genuinely apart; the assertion is unsupported
      overlap  -> the polygons overlap, which is not TOUCHES at all
    """
    if unit_a is None or unit_b is None:
        return "-"
    try:
        geom_a = parse_geometry(unit_a.wkt_text)
        geom_b = parse_geometry(unit_b.wkt_text)
    except Exception:
        return "-"

    try:
        if not geom_a.disjoint(geom_b) and not geom_a.touches(geom_b):
            return "overlap"
        boundary_a = geom_a.boundary
        boundary_b = geom_b.boundary
        if (
            boundary_a is None
            or boundary_b is None
            or boundary_a.is_empty
            or boundary_b.is_empty
        ):
            return "-"
        gap = boundary_a.distance(boundary_b)
    except Exception:
        return "-"

    if gap < 0.05:
        return "0"
    if gap < 1000:
        return f"{gap:,.1f}"
    return f"{gap / 1000:,.1f} km"


import re as _re_classify

_NAME_STRIP_PATTERN = _re_classify.compile(
    r"[\s_-]*(community|wcwr|cp|ward|\(det\))[\s_-]*\d*$",
    _re_classify.IGNORECASE,
)


def base_name(raw_name: str | None) -> str:
    """Strip trailing type/source suffixes (Community, WCWR123, CP, (DET))
    and digits so two records for the same real-world place normalise to
    the same string, e.g. "Adamsdown Community" and "Adamsdown" -> "adamsdown".
    """
    if not raw_name:
        return ""
    text = raw_name
    # repeatedly strip one trailing qualifier at a time (names can have
    # more than one, e.g. "X Community 18987")
    for _ in range(3):
        stripped = _NAME_STRIP_PATTERN.sub("", text).strip()
        stripped = _re_classify.sub(r"\d+$", "", stripped).strip()
        if stripped == text:
            break
        text = stripped
    return text.lower().strip()


def classify_overlap_pair(
    name_a: str | None, name_b: str | None
) -> str:
    """Best-effort automatic label for a REJECTED_NOT_TOUCHES pair.

    'duplicate' - base names match after stripping source/type suffixes
    (Community/WCWR/CP/Ward); almost certainly the same real-world place
    recorded twice under two naming schemes.
    'detached_part' - one raw name is the other plus a "(DET)" marker;
    an Ordnance Survey detached-parcel record for the same unit, not a
    cross-source duplicate.
    'partial_overlap' - base names differ; a genuine geometric overlap
    between two different administrative units.

    This is a heuristic on names only, not a geometric proof; borderline
    cases should still be checked by hand.
    """
    raw_a = (name_a or "").strip()
    raw_b = (name_b or "").strip()
    if raw_a and raw_b:
        stripped_a = _re_classify.sub(
            r"\s*\(det\)\s*$", "", raw_a, flags=_re_classify.IGNORECASE
        ).strip()
        stripped_b = _re_classify.sub(
            r"\s*\(det\)\s*$", "", raw_b, flags=_re_classify.IGNORECASE
        ).strip()
        det_a = raw_a.lower().endswith("(det)")
        det_b = raw_b.lower().endswith("(det)")
        if (det_a or det_b) and stripped_a.lower() == stripped_b.lower():
            return "detached_part"

    a = base_name(name_a)
    b = base_name(name_b)
    if a and b and a == b:
        return "duplicate"
    return "partial_overlap"


def overlap_area_pct(unit_a: Unit | None, unit_b: Unit | None) -> str:
    """The actual geometric intersection area as a percentage of the
    smaller polygon's area.

    IMPORTANT CORRECTION (discovered via independent verification against
    raw source WKT): the previous version of this function computed
    min(area_a, area_b) / max(area_a, area_b) — i.e. how similar the two
    polygons are in SIZE, regardless of whether they actually overlap in
    space. Two same-sized polygons on opposite sides of the country would
    have scored 100% under that formula despite zero real overlap. This
    version computes the TRUE intersection area instead, which is what
    "overlap percentage" should mean.

    For 'detached_part' pairs: a small ratio (e.g. under 20%) supports the
    "detached parcel" reading (a small separate piece of the same unit);
    a ratio near 100% suggests a fuller duplicate instead.

    For 'partial_overlap' pairs: a small ratio means the overlap affects
    only a sliver of each polygon (a minor boundary-drawing discrepancy);
    a large ratio means the two candidate polygons overlap substantially,
    which is a more significant boundary problem worth flagging.

    Returns "-" if either geometry cannot be parsed, or if the polygons
    do not actually intersect (0.0% is returned as "0.0%", not "-", so a
    non-touching pair that still landed in the rejected-overlap table for
    another reason is visibly distinguishable from a parse failure).
    """
    if unit_a is None or unit_b is None:
        return "-"
    try:
        geom_a = parse_geometry(unit_a.wkt_text)
        geom_b = parse_geometry(unit_b.wkt_text)
        area_a = geom_a.area
        area_b = geom_b.area
    except Exception:
        return "-"
    if not area_a or not area_b:
        return "-"
    try:
        intersection = geom_a.intersection(geom_b)
        intersection_area = intersection.area
    except Exception:
        return "-"
    smaller = min(area_a, area_b)
    ratio = (intersection_area / smaller * 100) if smaller else 0.0
    return f"{ratio:.1f}%"


def overlap_precision_metrics(
    unit_a: Unit | None, unit_b: Unit | None
) -> dict[str, Any]:
    """Absolute-scale diagnostics for the intersection, finer-grained than
    the percentage above. A percentage near 0.0% can still hide a genuine
    difference between "no real overlap at all" and "a sliver measured in
    square metres" — this returns the raw intersection area (m^2) and an
    estimated average sliver width (converted to centimetres), which is
    intersection_area / shared_boundary_length. A narrow, long sliver
    (width a few cm, length hundreds of metres) is the signature of a
    boundary-precision mismatch between two independently-digitised
    boundaries that are meant to coincide — not a genuine spatial overlap
    between two distinct regions.

    Returns {"intersection_area_m2": float | None,
             "sliver_width_cm": float | None,
             "is_precision_sliver": bool | None}
    "is_precision_sliver" is True when the estimated width is under 50cm,
    which is well within realistic OS boundary digitisation tolerance.
    """
    if unit_a is None or unit_b is None:
        return {"intersection_area_m2": None, "sliver_width_cm": None,
                "is_precision_sliver": None}
    try:
        geom_a = parse_geometry(unit_a.wkt_text)
        geom_b = parse_geometry(unit_b.wkt_text)
        intersection = geom_a.intersection(geom_b)
        intersection_area = intersection.area
        boundary_a = geom_a.boundary
        boundary_b = geom_b.boundary
        shared_boundary = boundary_a.intersection(boundary_b)
        shared_length = shared_boundary.length
    except Exception:
        return {"intersection_area_m2": None, "sliver_width_cm": None,
                "is_precision_sliver": None}
    if shared_length and shared_length > 0:
        width_m = intersection_area / shared_length
        width_cm = width_m * 100
    else:
        width_cm = None
    is_sliver = (width_cm is not None and width_cm < 50) or (
        width_cm is None and intersection_area < 1.0
    )
    return {
        "intersection_area_m2": round(intersection_area, 2),
        "sliver_width_cm": round(width_cm, 1) if width_cm is not None else None,
        "is_precision_sliver": is_sliver,
    }


_WELSH_URI_CACHE: set[str] | None = None


def fetch_welsh_uris(session) -> set[str]:
    """Every unit that belongs to Wales, decided in three layers.

    Layer 1 - a WITHIN path to one of the 22 Welsh unitary authorities.
    Layer 2 - a WITHIN path to the Wales Euro Region, for the units that skip
              the authority level entirely.
    Layer 3 - membership of a source class that exists only in Wales, for the
              units that carry no WITHIN edge at all.

    Layer 1 alone reaches 204 of the 396 Welsh community wards. The three
    layers together reach all of them.
    """
    # Membership does not change during a run and the query is asked by every
    # level pair, so it is computed once and reused.
    global _WELSH_URI_CACHE
    if _WELSH_URI_CACHE is not None:
        return _WELSH_URI_CACHE

    welsh: set[str] = set()

    for record in session.run(
        """
        MATCH (a:AdminUnit)-[:WITHIN*1..5]->(ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority' AND ua.os_id IN $ids
        RETURN DISTINCT a.uri AS uri
        """,
        ids=sorted(WELSH_UA_OS_IDS),
    ):
        welsh.add(record["uri"])
    by_authority = len(welsh)

    for record in session.run(
        """
        MATCH (a:AdminUnit)-[:WITHIN*1..5]->(r:AdminUnit)
        WHERE r.os_id = $wales
        RETURN DISTINCT a.uri AS uri
        """,
        wales=WALES_EURO_REGION_OS_ID,
    ):
        welsh.add(record["uri"])
    by_region = len(welsh)

    for record in session.run(
        """
        MATCH (a:AdminUnit)
        WHERE a.raw_type IN $raw
           OR a.os_id IN $ids
           OR a.os_id = $wales
        RETURN a.uri AS uri
        """,
        raw=sorted(WELSH_ONLY_RAW_TYPES),
        ids=sorted(WELSH_UA_OS_IDS),
        wales=WALES_EURO_REGION_OS_ID,
    ):
        welsh.add(record["uri"])

    print(
        f"    Welsh units: {by_authority:,} by authority, "
        f"{by_region - by_authority:,} added by region, "
        f"{len(welsh) - by_region:,} added by source class "
        f"= {len(welsh):,} total"
    )
    _WELSH_URI_CACHE = welsh
    return welsh


def fetch_welsh_membership(
    session, keys: set[str]
) -> dict[str, tuple[bool, str | None, str | None]]:
    """Batch-check which of the given unit keys (uri:<uri> strings) have a
    WITHIN path to a Welsh unitary authority (same list used throughout
    this script). Returns key -> (in_wales, authority_name, authority_os_id).
    Units with no such path map to (False, None, None).
    """
    uris = [k[len("uri:"):] for k in keys if k.startswith("uri:")]
    if not uris:
        return {}
    # Membership comes from the same three-layer set used to select the Wales
    # scope. The authority name is still looked up where a path exists, but a
    # unit without such a path is no longer treated as being outside Wales.
    welsh_uris = fetch_welsh_uris(session)

    records = session.run(
        """
        UNWIND $uris AS u
        MATCH (a:AdminUnit {uri: u})
        OPTIONAL MATCH (a)-[:WITHIN*1..5]->(ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority' AND ua.os_id IN $welsh_ids
        WITH a, ua
        ORDER BY ua.name
        RETURN a.uri AS uri,
               collect(ua.name)[0] AS authority_name,
               collect(ua.os_id)[0] AS authority_os_id
        """,
        uris=uris,
        welsh_ids=sorted(WELSH_UA_OS_IDS),
    )
    result: dict[str, tuple[bool, str | None, str | None]] = {}
    for record in records:
        uri = record["uri"]
        key = f"uri:{uri}"
        name = record["authority_name"]
        os_id = record["authority_os_id"]
        in_wales = uri in welsh_uris
        result[key] = (
            in_wales,
            name if name is not None else ("Wales" if in_wales else None),
            os_id,
        )
    return result


def pair_details(
    pairs: set[tuple[str, str]],
    lookup: dict[str, Unit],
    relation: str,
    welsh_membership: dict[str, tuple[bool, str | None, str | None]]
    | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for a, b in sorted(pairs):
        ua = lookup.get(a)
        ub = lookup.get(b)
        rows.append(
            {
                "relation": relation,
                "a_key": a,
                "a_name": ua.name if ua else None,
                "a_type": ua.raw_type if ua else None,
                "b_key": b,
                "b_name": ub.name if ub else None,
                "b_type": ub.raw_type if ub else None,
                "boundary_gap_m": boundary_gap_metres(ua, ub),
                **(
                    _rejected_extra_fields(
                        ua, ub, a, b, welsh_membership
                    )
                    if relation == "REJECTED_NOT_TOUCHES"
                    else {}
                ),
            }
        )
    return rows


def normalisation_source_family(unit: Unit | None) -> str:
    """The unit's EXACT pre-normalisation raw type, read directly from
    the a.raw_type property (added by load_to_neo4j.py). This replaces
    the earlier WCWR-tag approximation with a certain, no-guessing
    answer straight from the database.

    Returns the raw type string itself (e.g. "OS_COMMUNITY",
    "OS_CivilParishorCommunity", "OS_CCOMMUNITY", "OS_COMMUNITYWARD"),
    or "unknown" if the unit is missing or the database has not been
    reloaded since the raw_type property was added (db_raw_type is None).
    """
    if unit is None or unit.db_raw_type is None:
        return "unknown"
    return unit.db_raw_type


def _rejected_extra_fields(
    ua: Unit | None,
    ub: Unit | None,
    key_a: str,
    key_b: str,
    welsh_membership: dict[str, tuple[bool, str | None, str | None]]
    | None,
) -> dict[str, Any]:
    cause = classify_overlap_pair(
        ua.name if ua else None, ub.name if ub else None
    )
    fields: dict[str, Any] = {}
    if cause in ("duplicate", "detached_part", "partial_overlap"):
        precision = overlap_precision_metrics(ua, ub)

        if cause in ("duplicate", "detached_part"):
            # For these two categories, the classification already rests
            # on NAME matching, not on overlap magnitude — and near-total
            # geometric overlap is the EXPECTED, unremarkable outcome
            # (that's what "duplicate" means). Showing the raw million-m²
            # figure here doesn't add information, it just looks alarming
            # next to the tiny sliver figures elsewhere in the same
            # column — so show a plain descriptive label instead of the
            # number. The underlying area is still computed (nothing is
            # hidden), just not printed as a raw figure that invites a
            # misleading side-by-side comparison with genuine slivers.
            area = precision["intersection_area_m2"]
            if area is None:
                fields["intersection_area_m2"] = "-"
            elif area > 1000:
                fields["intersection_area_m2"] = "Full match (large shared area)"
            else:
                fields["intersection_area_m2"] = f"{area:,.2f}"
        else:
            fields["intersection_area_m2"] = (
                f"{precision['intersection_area_m2']:,.2f}"
                if precision["intersection_area_m2"] is not None else "-"
            )

        # Overlap width in metres (not a percentage): this is the actual
        # linear scale of the overlap — intersection_area / shared
        # boundary length — expressed to centimetre precision (2 decimal
        # places in metres). This replaces the old percentage metric,
        # which measured relative polygon SIZE, not the true magnitude of
        # spatial overlap. A width of 0.03 m immediately reads as a
        # negligible precision artifact; a width of 250 m immediately
        # reads as a substantial, policy-relevant boundary problem —
        # neither is obscured by a percentage that depends on the
        # (irrelevant) size of the larger polygon.
        fields["overlap_width_m"] = (
            f"{precision['sliver_width_cm'] / 100:,.2f}"
            if precision["sliver_width_cm"] is not None else "-"
        )
        # RELABEL: a "partial_overlap" pair whose actual overlap is a
        # sub-50cm-wide sliver is a boundary-precision artifact between
        # two independently-digitised boundaries meant to coincide — not
        # a genuine spatial overlap between distinct regions. Duplicate
        # and detached_part keep their original label regardless (their
        # classification rests on name-matching, not overlap magnitude).
        if cause == "partial_overlap" and precision["is_precision_sliver"]:
            cause = "precision_sliver"
    fields["overlap_classification"] = cause

    # Show the exact raw types side by side, straight from the database
    # (populated by load_to_neo4j.py's raw_type property).
    fields["a_raw_type"] = ua.db_raw_type if ua and ua.db_raw_type else "-"
    fields["b_raw_type"] = ub.db_raw_type if ub and ub.db_raw_type else "-"

    # Welsh-membership columns: a pair counts as "in Wales" only if BOTH
    # sides have a WITHIN path to a Welsh unitary authority. If either
    # side's membership could not be determined, the columns show "-".
    if welsh_membership is not None:
        mem_a = welsh_membership.get(key_a)
        mem_b = welsh_membership.get(key_b)
        if mem_a is None or mem_b is None:
            fields["in_wales"] = "-"
            fields["welsh_authority"] = "-"
            fields["welsh_authority_os_id"] = "-"
        else:
            in_wales_a, name_a, id_a = mem_a
            in_wales_b, name_b, id_b = mem_b
            both_welsh = in_wales_a and in_wales_b
            fields["in_wales"] = "Yes" if both_welsh else "No"
            if both_welsh:
                # a and b are normally in the same authority; show a's,
                # falling back to b's if a's lookup came back empty.
                fields["welsh_authority"] = name_a or name_b or "-"
                fields["welsh_authority_os_id"] = id_a or id_b or "-"
            else:
                fields["welsh_authority"] = "-"
                fields["welsh_authority_os_id"] = "-"
    return fields


def verification_sample(
    pairs: set[tuple[str, str]],
    lookup: dict[str, Unit],
    relation: str,
    limit: int = VERIFICATION_SAMPLE_SIZE,
    welsh_membership: dict[str, tuple[bool, str | None, str | None]]
    | None = None,
) -> list[dict[str, Any]]:
    """Return a deterministic, reproducible verification sample."""
    selected = sorted(pairs)[:limit]
    return pair_details(set(selected), lookup, relation, welsh_membership)


CONTAINMENT_AUDIT: dict[str, dict[str, Any]] = {}


def containment_audit(session) -> dict[str, Any]:
    """TS3 containment audit (read-only).

    TS3 requires every region to lie inside one parent region.
    This audit counts, per normalised type, units with at least one
    WITHIN parent versus orphans with no WITHIN relation at all, for
    the UK-wide model and the Welsh WCWR subset, and breaks the WCWR
    subset into: path to a UnitaryAuthority, level-skip (parent exists
    but no UnitaryAuthority path), and true orphans.
    """
    summary: list[dict[str, Any]] = []

    def add_rows(scope: str, extra_where: str) -> None:
        for unit_type in ("Ward", "Community"):
            record = session.run(
                f"""
                MATCH (a:AdminUnit)
                WHERE a.type = $t {extra_where}
                OPTIONAL MATCH (a)-[:WITHIN]->(p:AdminUnit)
                WITH a, count(p) AS parents
                RETURN count(a) AS total,
                       sum(CASE WHEN parents > 0 THEN 1 ELSE 0 END)
                           AS with_parent,
                       sum(CASE WHEN parents = 0 THEN 1 ELSE 0 END)
                           AS orphans
                """,
                t=unit_type,
            ).single()
            total = record["total"]
            orphans = record["orphans"]
            summary.append(
                {
                    "scope": scope,
                    "unit_type": unit_type,
                    "total_units": total,
                    "with_parent": record["with_parent"],
                    "orphans_no_parent": orphans,
                    "orphan_percent": (
                        f"{orphans / total * 100:.2f}%" if total else "-"
                    ),
                }
            )

    add_rows("UK-wide", "")
    add_rows("Wales (WCWR)", "AND a.uri CONTAINS 'WCWR'")

    pathway_record = session.run(
        """
        MATCH (a:AdminUnit) WHERE a.uri CONTAINS 'WCWR'
        OPTIONAL MATCH (a)-[:WITHIN*1..3]->
            (ua:AdminUnit {type:'UnitaryAuthority'})
        WITH a, count(DISTINCT ua) AS ua_paths
        OPTIONAL MATCH (a)-[:WITHIN]->(p:AdminUnit)
        WITH a, ua_paths, count(p) AS parents
        RETURN count(a) AS total,
               sum(CASE WHEN ua_paths > 0 THEN 1 ELSE 0 END)
                   AS via_unitary_authority,
               sum(CASE WHEN ua_paths = 0 AND parents > 0 THEN 1 ELSE 0 END)
                   AS level_skip,
               sum(CASE WHEN parents = 0 THEN 1 ELSE 0 END)
                   AS true_orphans
        """
    ).single()
    pathway = [
        {
            "wcwr_total": pathway_record["total"],
            "path_to_unitary_authority":
                pathway_record["via_unitary_authority"],
            "level_skip_parent_not_ua": pathway_record["level_skip"],
            "true_orphans_no_parent": pathway_record["true_orphans"],
        }
    ]

    samples = [
        {
            "name": row["name"],
            "type": row["type"],
            "uri": row["uri"],
        }
        for row in session.run(
            """
            MATCH (a:AdminUnit)
            WHERE a.type IN ['Ward', 'Community']
              AND NOT (a)-[:WITHIN]->(:AdminUnit)
            RETURN a.name AS name, a.type AS type, a.uri AS uri
            ORDER BY a.uri CONTAINS 'WCWR' DESC, a.name
            LIMIT 20
            """
        )
    ]

    # Geometry-inferred reattachment: for every orphan, find which Welsh
    # unitary authority covers it (or overlaps it most). This shows what
    # the missing WITHIN link should have been, so each row can be
    # verified manually by URI.
    orphan_records = list(
        session.run(
            """
            MATCH (a:AdminUnit)
            WHERE a.type IN ['Ward', 'Community']
              AND NOT (a)-[:WITHIN]->(:AdminUnit)
            RETURN a.uri AS uri, a.os_id AS os_id, a.name AS name,
                   a.type AS type, a.wkt AS wkt
            ORDER BY a.name
            """
        )
    )
    ua_records = list(
        session.run(
            """
            MATCH (ua:AdminUnit {type: 'UnitaryAuthority'})
            WHERE ua.os_id IN $welsh_ids
            RETURN ua.uri AS uri, ua.os_id AS os_id, ua.name AS name,
                   ua.wkt AS wkt
            """,
            welsh_ids=sorted(WELSH_UA_OS_IDS),
        )
    )
    ua_geoms: list[tuple[Any, BaseGeometry]] = []
    for ua_record in ua_records:
        try:
            ua_geoms.append((ua_record, parse_geometry(ua_record["wkt"])))
        except Exception:
            continue

    reattachment: list[dict[str, Any]] = []
    for orphan in orphan_records:
        inferred_name = "no Welsh UA match"
        inferred_id = "-"
        method = "-"
        try:
            orphan_geom = parse_geometry(orphan["wkt"])
        except Exception:
            orphan_geom = None
            inferred_name = "geometry unavailable"
        if orphan_geom is not None:
            best_area = 0.0
            for ua_record, ua_geom in ua_geoms:
                try:
                    if ua_geom.covers(orphan_geom):
                        inferred_name = str(ua_record["name"])
                        inferred_id = str(ua_record["os_id"])
                        method = "covers"
                        break
                    overlap = ua_geom.intersection(orphan_geom).area
                    if overlap > best_area:
                        best_area = overlap
                        inferred_name = str(ua_record["name"])
                        inferred_id = str(ua_record["os_id"])
                        method = "max overlap"
                except Exception:
                    continue
            if method == "max overlap" and orphan_geom.area > 0:
                share = best_area / orphan_geom.area * 100
                method = f"max overlap ({share:.0f}% of unit area)"
        reattachment.append(
            {
                "orphan_name": orphan["name"],
                "orphan_type": orphan["type"],
                "orphan_os_id": orphan["os_id"],
                "inferred_parent": inferred_name,
                "parent_os_id": inferred_id,
                "method": method,
                "orphan_uri": orphan["uri"],
            }
        )

    return {
        "summary": summary,
        "pathway": pathway,
        "samples": samples,
        "reattachment": reattachment,
    }


def render_containment(label: str) -> str:
    data = CONTAINMENT_AUDIT.get(label)
    if not data:
        return ""
    key = label.replace(" ", "-").lower()
    return f"""
    <section class="scope">
      <h2>TS3 containment audit - orphan units</h2>
      <p>TS3 requires every region to lie inside one parent region.
         Orphan units below have no WITHIN relation at all.
         Read-only audit; nothing was modified.</p>
      <h3>Summary by scope and type</h3>
      {html_table(data["summary"], f"containment-summary-{key}")}
      <h3>Welsh WCWR pathway breakdown</h3>
      {html_table(data["pathway"], f"containment-pathway-{key}")}
      <h3>Sample orphan units (first 20, WCWR first)</h3>
      {html_table(data["samples"], f"containment-samples-{key}")}
      <h3>Orphan reattachment by geometry — inferred parents</h3>
      <p>Every orphan unit tested against the 22 Welsh unitary
         authority polygons: "covers" means the authority fully
         covers the unit; "max overlap" gives the largest partial
         overlap. Verify any row in Neo4j with:
         MATCH (a:AdminUnit {{uri: '...orphan_uri...'}})
         RETURN a.name, a.type.</p>
      {html_table(data["reattachment"], f"containment-reattach-{key}")}
    </section>
    """


def evaluate_scope(session, scope: str) -> dict[str, Any]:
    started = time.time()
    data = fetch_scope_units(session, scope)
    communities = data["Community"]
    wards = data["Ward"]
    uas = data["UnitaryAuthority"]
    regions = data.get("EuropeanRegion", [])

    lookup = {u.key: u for u in communities + wards + uas + regions}
    raw_type_counts = Counter(u.raw_type for u in data["raw_units"])

    rows_tolerance: list[dict[str, Any]] = []
    rows_exact: list[dict[str, Any]] = []
    detail_sections: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []

    for level, units in (
        ("Ward", wards),
        ("Community", communities),
        ("Ward-Community", wards + communities),
    ):
        adjusted, exact, tolerance_pairs, rejected_pairs, failures = geometry_touch_pairs(units)

        if level == "Ward-Community":
            # geometry_touch_pairs() compared ALL pairs within the combined
            # list (Ward-Ward + Community-Community + Ward-Community) — we
            # only want the genuinely CROSS-type pairs here, since Ward-Ward
            # and Community-Community are already covered by the two
            # dedicated same-type passes above. Filter using each unit's
            # normalised type (stored, despite the field's name, in
            # unit.raw_type — see the Unit dataclass note).
            def is_cross_type(pair: tuple[str, str]) -> bool:
                ua_ = lookup.get(pair[0])
                ub_ = lookup.get(pair[1])
                if ua_ is None or ub_ is None:
                    return False
                return ua_.raw_type != ub_.raw_type

            adjusted = {p for p in adjusted if is_cross_type(p)}
            exact = {p for p in exact if is_cross_type(p)}
            tolerance_pairs = {p for p in tolerance_pairs if is_cross_type(p)}
            rejected_pairs = {p for p in rejected_pairs if is_cross_type(p)}

        rejected_keys: set[str] = set()
        for key_a, key_b in rejected_pairs:
            rejected_keys.add(key_a)
            rejected_keys.add(key_b)
        welsh_membership = fetch_welsh_membership(session, rejected_keys)
        native = native_touch_pairs(session, TYPE_GROUPS[level], scope)

        if level == "Ward-Community":
            # Same cross-type filter applied to the native-asserted set,
            # so "Native asserted" only counts genuine Ward<->Community
            # relations, not the Ward-Ward/Community-Community ones that
            # TYPE_GROUPS["Ward-Community"] (the union) would otherwise
            # also match.
            native = {p for p in native if is_cross_type(p)}

        for mode, reference, target_rows in (
            ("Exact only", exact, rows_exact),
            (f"Tolerance ≤ {TOUCH_TOLERANCE_METRES:g} m", adjusted, rows_tolerance),
        ):
            matched = reference & native
            missing = reference - native
            extra = native - reference
            denominator = len(reference)
            numerator = len(matched)
            score = numerator / denominator if denominator else None

            rejected_duplicate = 0
            rejected_detached = 0
            rejected_partial = 0
            rejected_precision_sliver = 0
            for key_a, key_b in rejected_pairs:
                unit_a = lookup.get(key_a)
                unit_b = lookup.get(key_b)
                label = classify_overlap_pair(
                    unit_a.name if unit_a else None,
                    unit_b.name if unit_b else None,
                )
                if label == "partial_overlap":
                    precision = overlap_precision_metrics(unit_a, unit_b)
                    if precision["is_precision_sliver"]:
                        label = "precision_sliver"

                if label == "duplicate":
                    rejected_duplicate += 1
                elif label == "detached_part":
                    rejected_detached += 1
                elif label == "precision_sliver":
                    rejected_precision_sliver += 1
                else:
                    rejected_partial += 1

            domain_label, range_label = (
                ("Ward", "Community") if level == "Ward-Community" else (level, level)
            )
            target_rows.append(
                {
                    "domain": domain_label,
                    "range": range_label,
                    "relation": "TOUCHES",
                    "normalised_nodes": len(units),
                    "reference_instances": denominator,
                    "native_instances": len(native),
                    "matched_instances": numerator,
                    "missing_instances": len(missing),
                    "extra_instances": len(extra),
                    "exact_touch_instances": len(exact),
                    "tolerance_added": len(tolerance_pairs) if mode != "Exact only" else 0,
                    "rejected_overlap_or_containment": len(rejected_pairs),
                    "rejected_duplicate": rejected_duplicate,
                    "rejected_detached_part": rejected_detached,
                    "rejected_partial_overlap": rejected_partial,
                    "completeness_ratio": score,
                    "completeness_percent": score * 100 if score is not None else None,
                    "status": "Complete" if denominator and not missing else (
                        "Gap" if denominator else "Cannot score"
                    ),
                }
            )

            detail_sections.append(
                {
                    "mode": mode,
                    "title": f"{domain_label} → {range_label}: missing native TOUCHES",
                    "description": (
                        f"Under {mode}, geometry includes these reference pairs, "
                        "but Neo4j has no native TOUCHES assertion."
                    ),
                    "rows": pair_details(missing, lookup, "TOUCHES"),
                    "sample_rows": verification_sample(missing, lookup, "TOUCHES"),
                }
            )
            detail_sections.append(
                {
                    "mode": mode,
                    "title": f"{domain_label} → {range_label}: native extras",
                    "description": (
                        f"Under {mode}, Neo4j asserts these TOUCHES pairs but the "
                        "selected geometry reference does not reproduce them."
                    ),
                    "rows": pair_details(extra, lookup, "TOUCHES"),
                    "sample_rows": verification_sample(extra, lookup, "TOUCHES"),
                }
            )

        detail_sections.append(
            {
                "mode": "Both",
                "title": f"{domain_label} → {range_label}: tolerance-added reference pairs",
                "description": (
                    "These polygons are disjoint, do not exactly touch, and their "
                    f"boundary gap is ≤ {TOUCH_TOLERANCE_METRES:g} metre(s)."
                ),
                "rows": pair_details(tolerance_pairs, lookup, "TOLERANCE_TOUCH"),
                "sample_rows": verification_sample(
                    tolerance_pairs, lookup, "TOLERANCE_TOUCH"
                ),
            }
        )
        detail_sections.append(
            {
                "mode": "Both",
                "title": f"{domain_label} → {range_label}: rejected overlap/containment pairs",
                "description": (
                    "These candidate polygons intersect internally, overlap, or contain "
                    "one another. They are deliberately rejected from TOUCHES even when "
                    "their boundary distance is zero."
                ),
                "rows": pair_details(
                    rejected_pairs,
                    lookup,
                    "REJECTED_NOT_TOUCHES",
                    welsh_membership,
                ),
                "sample_rows": verification_sample(
                    rejected_pairs,
                    lookup,
                    "REJECTED_NOT_TOUCHES",
                    welsh_membership=welsh_membership,
                ),
                "cause_counts": {
                    "duplicate": rejected_duplicate,
                    "detached_part": rejected_detached,
                    "partial_overlap": rejected_partial,
                    "precision_sliver": rejected_precision_sliver,
                },
            }
        )
        all_failures.extend(
            [{**f, "relation_row": f"{domain_label}-{range_label}"} for f in failures]
        )

    ref_within, within_failures = geometry_ua_ward_pairs(uas, wards)
    native_within = native_ua_ward_pairs(session, scope)
    matched_within = ref_within & native_within
    missing_within = ref_within - native_within
    extra_within = native_within - ref_within

    denominator = len(ref_within)
    numerator = len(matched_within)
    score = numerator / denominator if denominator else None
    within_row = {
        "domain": "UnitaryAuthority",
        "range": "Ward",
        "relation": "CONTAINS / WITHIN inverse",
        "normalised_nodes": len(uas) + len(wards),
        "reference_instances": denominator,
        "native_instances": len(native_within),
        "matched_instances": numerator,
        "missing_instances": len(missing_within),
        "extra_instances": len(extra_within),
        "rejected_duplicate": None,
        "rejected_detached_part": None,
        "rejected_partial_overlap": None,
        "exact_touch_instances": None,
        "tolerance_added": None,
        "rejected_overlap_or_containment": None,
        "completeness_ratio": score,
        "completeness_percent": score * 100 if score is not None else None,
        "status": "Complete" if denominator and not missing_within else (
            "Gap" if denominator else "Cannot score"
        ),
    }
    rows_exact.append(dict(within_row))
    rows_tolerance.append(dict(within_row))

    for title, description, pairs in (
        (
            "Unitary Authority → Ward: missing native WITHIN",
            "Geometry places these wards inside a unitary authority, but the direct "
            "native ward-[:WITHIN]->authority assertion is absent.",
            missing_within,
        ),
        (
            "Unitary Authority → Ward: native extras",
            "Direct native WITHIN assertions not reproduced by the geometry reference.",
            extra_within,
        ),
    ):
        detail_sections.append(
            {
                "mode": "Both",
                "title": title,
                "description": description,
                "rows": pair_details(pairs, lookup, "WITHIN"),
                "sample_rows": verification_sample(pairs, lookup, "WITHIN"),
            }
        )

    all_failures.extend(
        [{**f, "relation_row": "UnitaryAuthority-Ward"} for f in within_failures]
    )

    # Every remaining containment level pair. Without these the audit covered
    # one row of six inside Wales; with them it covers the whole hierarchy.
    empty_level_pairs: list[str] = []
    containment_jobs: list[tuple[str, str, list[Unit], list[Unit], set, set]] = [
        ("UnitaryAuthority", "Community",
         uas, communities, UA_TYPES, TYPE_GROUPS["Community"]),
        ("Community", "Ward",
         communities, wards, TYPE_GROUPS["Community"], TYPE_GROUPS["Ward"]),
    ]
    # Every unnormalised parent class that has instances in this scope, against
    # each of the three normalised levels beneath it.
    for parent_type, parent_units in sorted(
        data.get("parents_by_type", {}).items()
    ):
        label = parent_type.replace("OS_", "")
        for child_label, children_units, child_types in (
            ("UnitaryAuthority", uas, UA_TYPES),
            ("Ward", wards, TYPE_GROUPS["Ward"]),
            ("Community", communities, TYPE_GROUPS["Community"]),
        ):
            containment_jobs.append(
                (label, child_label, parent_units, children_units,
                 {parent_type}, child_types)
            )

    for parent_label, child_label, parents, children, p_types, c_types in (
        containment_jobs
    ):
        if not parents or not children:
            continue
        extra_row, extra_failures, extra_missing, extra_extra = containment_row(
            session, scope, parent_label, child_label,
            parents, children, p_types, c_types,
        )
        # The loop pairs every unnormalised parent class with every level
        # beneath it, which produces some combinations that do not exist in
        # this geography at all: a unitary authority is not inside a county,
        # so both the geometry reference and the assertions are empty. There
        # is nothing to score there, and a row of dashes only makes the table
        # harder to read, so the pair is recorded in a note instead.
        if (
            not extra_row["reference_instances"]
            and not extra_row["native_instances"]
        ):
            empty_level_pairs.append(f"{parent_label} \u2192 {child_label}")
            continue
        rows_exact.append(dict(extra_row))
        rows_tolerance.append(dict(extra_row))
        all_failures.extend(
            [
                {**f, "relation_row": f"{parent_label}-{child_label}"}
                for f in extra_failures
            ]
        )
        for title, description, pairs in (
            (
                f"{parent_label} \u2192 {child_label}: missing native WITHIN",
                "Geometry places the child inside the parent, but the direct "
                "native assertion is absent.",
                extra_missing,
            ),
            (
                f"{parent_label} \u2192 {child_label}: native extras",
                "Direct native WITHIN assertions not reproduced by the "
                "geometry reference.",
                extra_extra,
            ),
        ):
            if not pairs:
                continue
            detail_sections.append(
                {
                    "mode": "Both",
                    "title": title,
                    "description": description,
                    "rows": pair_details(pairs, lookup, "WITHIN"),
                    "sample_rows": verification_sample(
                        pairs, lookup, "WITHIN"
                    ),
                }
            )

    def totals(rows: list[dict[str, Any]]) -> tuple[int, int, float | None]:
        den = sum(r["reference_instances"] for r in rows)
        num = sum(r["matched_instances"] for r in rows)
        return den, num, (num / den if den else None)

    exact_den, exact_num, exact_spcom = totals(rows_exact)
    tol_den, tol_num, tol_spcom = totals(rows_tolerance)

    return {
        "scope": scope,
        "empty_level_pairs": empty_level_pairs,
        # Exact mode is the primary/default evaluation.
        "rows": rows_exact,
        "rows_tolerance": rows_tolerance,
        "spcom_ratio": exact_spcom,
        "spcom_percent": exact_spcom * 100 if exact_spcom is not None else None,
        "spcom_tolerance_ratio": tol_spcom,
        "spcom_tolerance_percent": tol_spcom * 100 if tol_spcom is not None else None,
        "total_reference_instances": exact_den,
        "total_matched_instances": exact_num,
        "total_tolerance_reference_instances": tol_den,
        "total_tolerance_matched_instances": tol_num,
        "raw_type_counts": dict(sorted(raw_type_counts.items(), key=lambda x: str(x[0]))),
        "duplicate_audit": data["duplicates"],
        "geometry_failures": all_failures,
        "details": detail_sections,
        "elapsed_seconds": round(time.time() - started, 2),
    }

def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def fmt_num(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}" if isinstance(value, int) else esc(value)


_CAUSE_LABELS = {
    "duplicate": "Likely duplicate (dual naming scheme)",
    "detached_part": "Detached parcel (same OS unit)",
    "partial_overlap": "Genuine partial overlap (different entities)",
    "precision_sliver": "Boundary-precision sliver (near-touch, not real overlap)",
}
_CAUSE_STYLES = {
    "duplicate": "color:#1e40af;font-weight:600;",
    "detached_part": "color:#7c2d12;font-weight:600;",
    "partial_overlap": "color:#b91c1c;font-weight:600;",
    "precision_sliver": "color:#0891b2;font-weight:600;",
}


def html_table(rows: list[dict[str, Any]], table_id: str) -> str:
    if not rows:
        return '<p class="empty">No records.</p>'
    # Union of keys across all rows, in first-seen order — some rows
    # (e.g. detached_part) carry an extra column others don't have.
    columns: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)
    head = "".join(f"<th>{esc(c.replace('_', ' ').title())}</th>" for c in columns)
    body = []
    for row in rows:
        cells_html = []
        for c in columns:
            value = row.get(c)
            if c == "overlap_classification" and value in _CAUSE_STYLES:
                style = _CAUSE_STYLES[value]
                label = _CAUSE_LABELS.get(value, value)
                cells_html.append(f'<td style="{style}">{esc(label)}</td>')
            else:
                cells_html.append(f"<td>{esc(value)}</td>")
        cells = "".join(cells_html)
        in_wales_row = row.get("in_wales") == "Yes"
        row_style = ' style="background:#fff7ed;"' if in_wales_row else ""
        body.append(f"<tr{row_style}>{cells}</tr>")
    payload = html.escape(json.dumps(rows, ensure_ascii=False))
    return f"""
    <div class="table-actions">
      <button onclick='downloadRows({json.dumps(table_id)}, JSON.parse(this.dataset.rows))'
              data-rows="{payload}">Download CSV</button>
    </div>
    <div class="table-wrap">
      <table id="{esc(table_id)}"><thead><tr>{head}</tr></thead>
      <tbody>{''.join(body)}</tbody></table>
    </div>
    """


def summary_table(rows: list[dict[str, Any]], css_class: str = "") -> str:
    body = []
    for row in rows:
        pct = row["completeness_percent"]
        pct_text = "—" if pct is None else f"{pct:.2f}%"
        status_class = "complete" if row["status"] == "Complete" else "gap"
        body.append(
            f"""
            <tr>
              <td>{esc(row['domain'])}</td>
              <td>{esc(row['range'])}</td>
              <td>{esc(row['relation'])}</td>
              <td>{fmt_num(row['normalised_nodes'])}</td>
              <td>{fmt_num(row['reference_instances'])}</td>
              <td>{fmt_num(row['native_instances'])}</td>
              <td>{fmt_num(row['matched_instances'])}</td>
              <td>{fmt_num(row['missing_instances'])}</td>
              <td>{fmt_num(row['extra_instances'])}</td>
              <td>{fmt_num(row.get('exact_touch_instances'))}</td>
              <td>{fmt_num(row.get('rejected_overlap_or_containment'))}</td>
              <td><b>{pct_text}</b></td>
              <td><span class="pill {status_class}">{esc(row['status'])}</span></td>
            </tr>
            """
        )
    return f"""
    <div class="table-wrap mode-block {esc(css_class)}">
    <table>
      <thead><tr>
        <th>Domain</th><th>Range</th><th>Relation</th><th>Normalised nodes</th>
        <th>Reference (Ω)</th><th>Native asserted</th><th>Matched</th>
        <th>Missing</th><th>Extra</th><th>Exact TOUCHES</th>
        <th>Rejected overlap</th>
        <th>Completeness</th><th>Status</th>
      </tr></thead>
      <tbody>{''.join(body)}</tbody>
    </table>
    </div>
    """


def render_cause_breakdown(cause_counts: dict[str, int] | None) -> str:
    if not cause_counts:
        return ""
    dup = cause_counts.get("duplicate", 0)
    det = cause_counts.get("detached_part", 0)
    part = cause_counts.get("partial_overlap", 0)
    sliver = cause_counts.get("precision_sliver", 0)

    return f"""
    <p class="cause-breakdown">
      <b>Automatic classification (name-based heuristic):</b><br>
      <span style="color:#1e40af;font-weight:600;">Duplicate (dual naming scheme): {dup:,}</span> &nbsp;|&nbsp;
      <span style="color:#7c2d12;font-weight:600;">Detached parcel (same OS unit): {det:,}</span> &nbsp;|&nbsp;
      <span style="color:#b91c1c;font-weight:600;">Genuine partial overlap: {part:,}</span> &nbsp;|&nbsp;
      <span style="color:#0891b2;font-weight:600;">Boundary-precision sliver (near-touch, not real overlap): {sliver:,}</span>
    </p>
    """


def render_scope(scope_result: dict[str, Any], index: int) -> str:
    scope = scope_result["scope"]
    exact_pct = scope_result["spcom_percent"]
    tol_pct = scope_result["spcom_tolerance_percent"]
    exact_pct_text = "—" if exact_pct is None else f"{exact_pct:.2f}%"
    tol_pct_text = "—" if tol_pct is None else f"{tol_pct:.2f}%"
    detail_html = []

    for i, section in enumerate(scope_result["details"]):
        mode = section.get("mode", "Both")
        if mode == "Exact only":
            mode_class = "exact-mode"
        elif mode.startswith("Tolerance"):
            mode_class = "tolerance-mode"
        else:
            mode_class = "both-mode"

        sample_html = html_table(
            section.get("sample_rows", []), f"sample_{index}_{i}"
        )
        detail_html.append(
            f"""
            <details class="mode-detail {mode_class}">
              <summary>{esc(section['title'])}
                <span class="count">{len(section['rows'])}</span>
              </summary>
              <p><b>Mode:</b> {esc(mode)}</p>
              <p>{esc(section['description'])}</p>
              {render_cause_breakdown(section.get('cause_counts'))}
              <h4>Verification sample (first {VERIFICATION_SAMPLE_SIZE}, reproducible)</h4>
              {sample_html}
              <h4>All records</h4>
              {html_table(section['rows'], f"detail_{index}_{i}")}
            </details>
            """
        )

    audit_rows = [
        {"raw_type": k, "count": v}
        for k, v in scope_result["raw_type_counts"].items()
    ]

    return f"""
    <section class="scope" id="scope_{index}">
      <div class="scope-head">
        <div>
          <h2>{esc(scope)}</h2>
          <p>Three-row native instance-completeness evaluation.</p>
        </div>
        <div class="score-card exact-mode">
          <span>Relation-instance completeness</span>
          <strong>{exact_pct_text}</strong>
          <small>{scope_result['total_matched_instances']:,} matched /
                 {scope_result['total_reference_instances']:,} definable</small>
        </div>
      </div>

      <div class="formula">
        <b>Applied equation:</b>
        Relation-instance completeness = Σ matched native relation instances ÷ Σ geometry-definable relation instances (distinct from the model-level SpCom scorecard over the eight SCQs)
      </div>

      {summary_table(scope_result["rows"], "exact-mode")}
      {(
          "<p style='font-size:13px;opacity:.75;margin:.4rem 0 0'>"
          "<b>Level pairs with nothing to score:</b> "
          + ", ".join(esc(p) for p in scope_result.get("empty_level_pairs", []))
          + ". Neither the geometry nor the ontology places one inside the "
          "other, so the pair does not exist in this administrative "
          "structure and is recorded here rather than as an empty row."
          "</p>"
      ) if scope_result.get("empty_level_pairs") else ""}

      <div class="notes-grid">
        <div class="note">
          <b>Touch modes</b><br>
          <b>Exact mode is the default.</b> It uses only <code>geom.touches</code>.
          Tolerance mode is optional and additionally
          accepts only <b>disjoint</b> polygons whose boundary gap is ≤
          {TOUCH_TOLERANCE_METRES:g} metre(s). Overlap/containment is rejected.
        </div>
        <div class="note">
          <b>Geometry diagnostics</b><br>
          {len(scope_result['geometry_failures']):,} issue(s) recorded without
          stopping the report.
        </div>
        <div class="note">
          <b>Runtime</b><br>{scope_result['elapsed_seconds']} seconds.
        </div>
      </div>

      <h3>Evidence and diagnostics</h3>
      {''.join(detail_html)}

      <details>
        <summary>Raw type audit <span class="count">{len(audit_rows)}</span></summary>
        <p>This shows the source type names before canonical grouping.</p>
        {html_table(audit_rows, f"types_{index}")}
      </details>

      <details>
        <summary>Deduplication audit
          <span class="count">{len(scope_result['duplicate_audit'])}</span>
        </summary>
        <p>Duplicate representations detected by stable OS ID or URI.</p>
        {html_table(scope_result['duplicate_audit'], f"dups_{index}")}
      </details>

      <details>
        <summary>Geometry issues and failures
          <span class="count">{len(scope_result['geometry_failures'])}</span>
        </summary>
        <p>
          Records marked <b>Excluded</b> were omitted from the geometry denominator.
          Records marked <b>Retained</b> remained usable. The full report continues.
        </p>
        {html_table(scope_result['geometry_failures'], f"failures_{index}")}
      </details>
    </section>
    """

def comparison_rows(local_results, cloud_results):
    local_map = {
        (scope["scope"], row["domain"], row["range"], row["relation"]): row
        for scope in local_results for row in scope["rows"]
    }
    cloud_map = {
        (scope["scope"], row["domain"], row["range"], row["relation"]): row
        for scope in cloud_results for row in scope["rows"]
    }

    output = []
    for key in sorted(set(local_map) | set(cloud_map)):
        local = local_map.get(key, {})
        cloud = cloud_map.get(key, {})
        fields = [
            "reference_instances", "native_instances", "matched_instances",
            "missing_instances", "extra_instances"
        ]
        same = all(local.get(f) == cloud.get(f) for f in fields)
        lp = local.get("completeness_percent")
        cp = cloud.get("completeness_percent")
        output.append({
            "scope": key[0],
            "domain": key[1],
            "range": key[2],
            "relation": key[3],
            "local_reference": local.get("reference_instances"),
            "cloud_reference": cloud.get("reference_instances"),
            "local_native": local.get("native_instances"),
            "cloud_native": cloud.get("native_instances"),
            "local_missing": local.get("missing_instances"),
            "cloud_missing": cloud.get("missing_instances"),
            "local_completeness": None if lp is None else f"{lp:.2f}%",
            "cloud_completeness": None if cp is None else f"{cp:.2f}%",
            "match_status": "Match" if same else "Different",
        })
    return output


def render_database(label, summary, results, database_index):
    scopes = "".join(
        render_scope(scope, database_index * 10 + i)
        for i, scope in enumerate(results)
    )
    return f"""
    <section class="database-block">
      {scopes}
      {render_containment(label)}
    </section>
    """


def build_html(local_results, cloud_results, local_summary, cloud_summary):
    generated = time.strftime("%Y-%m-%d %H:%M:%S")
    comparison = comparison_rows(local_results, cloud_results)
    local_block = render_database("Local Neo4j", local_summary, local_results, 0)
    cloud_block = render_database("Cloud Neo4j", cloud_summary, cloud_results, 1)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YAGO2geo Local and Cloud Completeness Report</title>
<style>
:root {{
  --ink:#172033; --muted:#64748b; --line:#dbe4ef; --blue:#2563eb;
  --orange:#c2410c; --soft:#f7faff;
}}
* {{box-sizing:border-box}}
body {{margin:0;background:linear-gradient(180deg,#f8fbff,#fff);
      color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}}
main {{max-width:1500px;margin:auto;padding:32px 22px 70px}}
.hero {{background:linear-gradient(135deg,#172554,#1d4ed8 65%,#0ea5e9);
        color:#fff;border-radius:22px;padding:28px 30px;
        box-shadow:0 18px 45px rgba(30,64,175,.20)}}
.hero h1 {{margin:0 0 9px;font-size:30px}} .hero p {{margin:5px 0;opacity:.93}}
.database-block {{margin-top:30px}}
.database-title {{background:linear-gradient(135deg,#fff7ed,#fff);
  border:1px solid #fed7aa;border-left:7px solid var(--orange);
  border-radius:18px;padding:20px 24px;margin-bottom:15px}}
.database-title h2 {{margin:2px 0 4px;font-size:28px;color:#7c2d12}}
.database-title p {{margin:0;color:var(--muted)}}
.database-kicker {{text-transform:uppercase;letter-spacing:.12em;font-size:12px;
  font-weight:850;color:var(--orange)}}
.scope,.comparison {{background:#fff;border:1px solid var(--line);border-radius:20px;
  margin-top:18px;padding:24px;box-shadow:0 10px 28px rgba(15,23,42,.05)}}
.scope-head {{display:flex;justify-content:space-between;gap:20px;align-items:center}}
.scope h2 {{margin:0;font-size:25px}} .scope h3 {{margin-top:28px}}
.score-card {{min-width:255px;background:var(--soft);border:1px solid #bfdbfe;
  border-radius:16px;padding:15px 18px;text-align:right}}
.score-card span,.score-card small {{display:block;color:var(--muted)}}
.score-card strong {{font-size:31px;color:#1d4ed8}}
.formula {{margin:17px 0;background:#eff6ff;border-left:5px solid var(--blue);
  padding:13px 16px;border-radius:10px}}
.table-wrap {{overflow:auto;border:1px solid var(--line);border-radius:13px}}
table {{border-collapse:collapse;width:100%;font-size:13px;background:#fff}}
th {{background:#eef4fb;text-align:left;position:sticky;top:0}}
th,td {{padding:10px 11px;border-bottom:1px solid #e8eef5;white-space:nowrap}}
tr:hover td {{background:#fafcff}}
.pill {{display:inline-block;padding:4px 9px;border-radius:999px;font-weight:700}}
.pill.complete {{background:#dcfce7;color:#166534}}
.pill.gap {{background:#fee2e2;color:#991b1b}}
.notes-grid {{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin:15px 0}}
.note {{background:#f8fafc;border:1px solid var(--line);padding:13px;border-radius:12px}}
details {{border:1px solid var(--line);border-radius:13px;margin:10px 0;padding:0 14px 14px}}
summary {{cursor:pointer;font-weight:750;padding:14px 0}}
.count {{background:#e2e8f0;border-radius:999px;padding:2px 8px;margin-left:6px}}
.table-actions {{display:flex;justify-content:flex-end;margin:5px 0}}
button {{border:0;background:#1d4ed8;color:#fff;padding:7px 11px;
  border-radius:8px;cursor:pointer;font-weight:700}}
.empty {{color:var(--muted);font-style:italic}}
.toggle-label {{display:inline-flex;align-items:center;gap:9px;margin-top:12px;
  font-weight:750;cursor:pointer}}
.toggle-label input {{width:19px;height:19px}}
[hidden] {{display:none !important}}
.footer {{color:var(--muted);margin-top:22px;text-align:center}}
@media(max-width:760px) {{
  .scope-head {{display:block}} .score-card {{margin-top:14px;text-align:left}}
  .notes-grid {{grid-template-columns:1fr}}
}}
</style>
<script>
function setToleranceMode(scopeId, enabled) {{
  const scope = document.getElementById(scopeId);
  scope.querySelectorAll('.tolerance-mode').forEach(
    el => el.hidden = !enabled
  );
  scope.querySelectorAll('.exact-mode').forEach(
    el => el.hidden = enabled
  );
  scope.querySelectorAll('.both-mode').forEach(
    el => el.hidden = false
  );
}}
function downloadRows(name, rows) {{
  if (!rows || rows.length === 0) return;
  const cols = Object.keys(rows[0]);
  const q = v => '"' + String(v ?? '').replaceAll('"','""') + '"';
  const csv = [cols.map(q).join(','), ...rows.map(r => cols.map(c => q(r[c])).join(',') )].join('\\n');
  const blob = new Blob([csv], {{type:'text/csv;charset=utf-8'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name + '.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}}
</script>
</head>
<body>
<main>
  <section class="comparison">
    <h2>Local vs Cloud — direct comparison</h2>
    <p>“Match” means the reference, native, matched, missing and extra counts
       are identical for that row.</p>
    {html_table(comparison, "local_cloud_comparison")}
  </section>

  {local_block}
  {cloud_block}

  <p class="footer">
    Canonical grouping is restricted to declared Ward and Community variants.
  </p>
</main>
</body>
</html>"""



def build_single_html(database_label, results, connection_summary):
    generated = time.strftime("%Y-%m-%d %H:%M:%S")
    database_block = render_database(database_label, connection_summary, results, 0)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YAGO2geo Completeness Report — {esc(database_label)}</title>
<style>
:root {{
  --ink:#172033; --muted:#64748b; --line:#dbe4ef; --blue:#2563eb;
  --orange:#c2410c; --soft:#f7faff;
}}
* {{box-sizing:border-box}}
body {{margin:0;background:linear-gradient(180deg,#f8fbff,#fff);
      color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}}
main {{max-width:1500px;margin:auto;padding:32px 22px 70px}}
.hero {{background:linear-gradient(135deg,#172554,#1d4ed8 65%,#0ea5e9);
        color:#fff;border-radius:22px;padding:28px 30px;
        box-shadow:0 18px 45px rgba(30,64,175,.20)}}
.hero h1 {{margin:0 0 9px;font-size:30px}} .hero p {{margin:5px 0;opacity:.93}}
.database-block {{margin-top:30px}}
.database-title {{background:linear-gradient(135deg,#fff7ed,#fff);
  border:1px solid #fed7aa;border-left:7px solid var(--orange);
  border-radius:18px;padding:20px 24px;margin-bottom:15px}}
.database-title h2 {{margin:2px 0 4px;font-size:28px;color:#7c2d12}}
.database-title p {{margin:0;color:var(--muted)}}
.database-kicker {{text-transform:uppercase;letter-spacing:.12em;font-size:12px;
  font-weight:850;color:var(--orange)}}
.scope {{background:#fff;border:1px solid var(--line);border-radius:20px;
  margin-top:18px;padding:24px;box-shadow:0 10px 28px rgba(15,23,42,.05)}}
.scope-head {{display:flex;justify-content:space-between;gap:20px;align-items:center}}
.scope h2 {{margin:0;font-size:25px}} .scope h3 {{margin-top:28px}}
.score-card {{min-width:255px;background:var(--soft);border:1px solid #bfdbfe;
  border-radius:16px;padding:15px 18px;text-align:right}}
.score-card span,.score-card small {{display:block;color:var(--muted)}}
.score-card strong {{font-size:31px;color:#1d4ed8}}
.formula {{margin:17px 0;background:#eff6ff;border-left:5px solid var(--blue);
  padding:13px 16px;border-radius:10px}}
.table-wrap {{overflow:auto;border:1px solid var(--line);border-radius:13px}}
table {{border-collapse:collapse;width:100%;font-size:13px;background:#fff}}
th {{background:#eef4fb;text-align:left;position:sticky;top:0}}
th,td {{padding:10px 11px;border-bottom:1px solid #e8eef5;white-space:nowrap}}
tr:hover td {{background:#fafcff}}
.pill {{display:inline-block;padding:4px 9px;border-radius:999px;font-weight:700}}
.pill.complete {{background:#dcfce7;color:#166534}}
.pill.gap {{background:#fee2e2;color:#991b1b}}
.notes-grid {{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin:15px 0}}
.note {{background:#f8fafc;border:1px solid var(--line);padding:13px;border-radius:12px}}
details {{border:1px solid var(--line);border-radius:13px;margin:10px 0;padding:0 14px 14px}}
summary {{cursor:pointer;font-weight:750;padding:14px 0}}
.count {{background:#e2e8f0;border-radius:999px;padding:2px 8px;margin-left:6px}}
.table-actions {{display:flex;justify-content:flex-end;margin:5px 0}}
button {{border:0;background:#1d4ed8;color:#fff;padding:7px 11px;
  border-radius:8px;cursor:pointer;font-weight:700}}
.empty {{color:var(--muted);font-style:italic}}
.toggle-label {{display:inline-flex;align-items:center;gap:9px;margin-top:12px;
  font-weight:750;cursor:pointer}}
.toggle-label input {{width:19px;height:19px}}
[hidden] {{display:none !important}}
.footer {{color:var(--muted);margin-top:22px;text-align:center}}
@media(max-width:760px) {{
  .scope-head {{display:block}} .score-card {{margin-top:14px;text-align:left}}
  .notes-grid {{grid-template-columns:1fr}}
}}
</style>
<script>
function setToleranceMode(scopeId, enabled) {{
  const scope = document.getElementById(scopeId);
  scope.querySelectorAll('.tolerance-mode').forEach(
    el => el.hidden = !enabled
  );
  scope.querySelectorAll('.exact-mode').forEach(
    el => el.hidden = enabled
  );
  scope.querySelectorAll('.both-mode').forEach(
    el => el.hidden = false
  );
}}
function downloadRows(name, rows) {{
  if (!rows || rows.length === 0) return;
  const cols = Object.keys(rows[0]);
  const q = v => '"' + String(v ?? '').replaceAll('"','""') + '"';
  const csv = [cols.map(q).join(','), ...rows.map(r => cols.map(c => q(r[c])).join(','))].join('\\n');
  const blob = new Blob([csv], {{type:'text/csv;charset=utf-8'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name + '.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}}
</script>
</head>
<body>
<main>
  {database_block}

  <p class="footer">
    Canonical grouping is restricted to declared Ward and Community variants.
  </p>
</main>
</body>
</html>"""



def evaluate_database(
    label: str,
    config: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Connect to one Neo4j database and evaluate all requested scopes.

    The connection is always closed, including when evaluation raises an error.
    """
    print(f"\nConnecting to {label}...")
    print(f"  URI: {config['uri']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")

    driver = GraphDatabase.driver(
        config["uri"],
        auth=(config["user"], config["password"]),
    )

    try:
        driver.verify_connectivity()
        print("  Connection successful.")

        with driver.session(database=config["database"]) as session:
            results: list[dict[str, Any]] = []

            # Two scopes in one report: the UK-wide model, and the same
            # measure restricted to Wales. The Wales rows are the ones that
            # bear on the SpCom scorecard; the UK rows give the baseline the
            # Welsh figures should be read against.
            # Wales first: it is the scope the SpCom scorecard is built on.
            # The UK-wide rows follow as the baseline to read it against.
            for scope in (
                "Wales",
                "UK-wide available model",
            ):
                print(f"  Evaluating {scope}...")

                result = evaluate_scope(
                    session,
                    scope,
                )

                results.append(result)

                score = result.get("spcom_percent")
                score_text = (
                    "Cannot score"
                    if score is None
                    else f"{score:.2f}%"
                )

                print(
                    f"    Completed {scope}: "
                    f"{result['total_matched_instances']:,} matched / "
                    f"{result['total_reference_instances']:,} reference "
                    f"({score_text})"
                )

            print("  Running TS3 containment (orphan) audit...")
            CONTAINMENT_AUDIT[label] = containment_audit(session)
            uk_orphans = sum(
                row["orphans_no_parent"]
                for row in CONTAINMENT_AUDIT[label]["summary"]
                if row["scope"] == "UK-wide"
            )
            print(
                f"    UK-wide orphan units (no parent): {uk_orphans:,}"
            )
            print(
                "    Orphan reattachment rows: "
                f"{len(CONTAINMENT_AUDIT[label]['reattachment']):,}"
            )

            return results

    finally:
        driver.close()
        print(f"  Closed connection to {label}.")


def safe_connection_summary(
    label: str,
    config: dict[str, str],
) -> str:
    """
    Return connection information safe to display in the HTML report.

    The password is deliberately never included.
    """
    return (
        f"{label}: URI={config['uri']} · "
        f"database={config['database']} · "
        f"user={config['user']}"
    )


def validate_config(
    label: str,
    config: dict[str, str],
) -> None:
    """
    Validate the selected database configuration before connecting.
    """
    required_fields = (
        "uri",
        "user",
        "password",
        "database",
    )

    missing = [
        field
        for field in required_fields
        if not str(config.get(field, "")).strip()
    ]

    if missing:
        raise ValueError(
            f"{label} configuration is missing: "
            + ", ".join(missing)
        )

    placeholder_values = {
        "PUT_LOCAL_PASSWORD_HERE",
        "PUT_CLOUD_PASSWORD_HERE",
        "YOUR_PASSWORD",
        "PASSWORD_HERE",
    }

    if config["password"].strip() in placeholder_values:
        raise ValueError(
            f"{label} password has not been entered. "
            "Replace the password placeholder near the top of the script."
        )


def main() -> int:
    """
    Run the report according to DATABASE_MODE.

    No PowerShell runner and no environment variables are required.
    """
    mode = DATABASE_MODE.strip().upper()

    allowed_modes = {
        "LOCAL",
        "CLOUD",
        "BOTH",
    }

    if mode not in allowed_modes:
        raise ValueError(
            'DATABASE_MODE must be "LOCAL", "CLOUD", or "BOTH". '
            f"Current value: {DATABASE_MODE!r}"
        )

    output_html = Path(
        OUTPUT_FILES[mode]
    )

    print("=" * 70)
    print(
        "YAGO2geo native relation-instance "
        "completeness report"
    )
    print("=" * 70)
    print(f"Database mode: {mode}")
    print(
        f"Touch tolerance: "
        f"{TOUCH_TOLERANCE_METRES:g} metre(s)"
    )
    print(f"Output file: {output_html}")
    print(
        "Read-only analysis: "
        "no Neo4j data will be modified."
    )

    if mode == "LOCAL":
        validate_config(
            "Local Neo4j",
            LOCAL_CONFIG,
        )

        local_results = evaluate_database(
            "Local Neo4j",
            LOCAL_CONFIG,
        )

        report = build_single_html(
            "Local Neo4j",
            local_results,
            safe_connection_summary(
                "Local",
                LOCAL_CONFIG,
            ),
        )

    elif mode == "CLOUD":
        validate_config(
            "Cloud Neo4j",
            CLOUD_CONFIG,
        )

        cloud_results = evaluate_database(
            "Cloud Neo4j",
            CLOUD_CONFIG,
        )

        report = build_single_html(
            "Cloud Neo4j",
            cloud_results,
            safe_connection_summary(
                "Cloud",
                CLOUD_CONFIG,
            ),
        )

    else:
        validate_config(
            "Local Neo4j",
            LOCAL_CONFIG,
        )

        validate_config(
            "Cloud Neo4j",
            CLOUD_CONFIG,
        )

        local_results = evaluate_database(
            "Local Neo4j",
            LOCAL_CONFIG,
        )

        cloud_results = evaluate_database(
            "Cloud Neo4j",
            CLOUD_CONFIG,
        )

        report = build_html(
            local_results,
            cloud_results,
            safe_connection_summary(
                "Local",
                LOCAL_CONFIG,
            ),
            safe_connection_summary(
                "Cloud",
                CLOUD_CONFIG,
            ),
        )

    output_html.write_text(
        report,
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("Report created successfully")
    print("=" * 70)
    print(output_html.resolve())
    print("Open this HTML file in your browser.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except KeyboardInterrupt:
        print(
            "\nExecution cancelled by the user.",
            file=sys.stderr,
        )
        raise SystemExit(130)

    except Exception as exc:
        print(
            f"\nERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise
