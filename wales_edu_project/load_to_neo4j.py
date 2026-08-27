"""
Project: Education Inequality Analysis with a Geospatial Knowledge Graph
Student: Afaf Alhajjaji
Student Number: 24106532
Supervisor: Dr Alia Abdelmoty
"""


import os
import re
import pandas as pd
from neo4j import GraphDatabase
from rdflib import Graph, URIRef
from rdflib.namespace import RDF
from shapely import wkt
from shapely.strtree import STRtree
from shapely.geometry import Point
from shapely.ops import transform
from pyproj import Transformer
from shapely.validation import make_valid

import time 

import geopandas as gpd
from dotenv import load_dotenv

load_dotenv()

# --- CONNECTION SETTINGS ---
MODE = "CLOUD"  # Change to "LOCAL" when testing locally

if MODE == "CLOUD":
    URI = os.environ["NEO4J_URI"]
    AUTH = (
        os.environ["NEO4J_USER"],
        os.environ["NEO4J_PASSWORD"],
    )
    DATABASE = os.environ["NEO4J_DATABASE"]

elif MODE == "LOCAL":
    URI = os.environ["LOCAL_NEO4J_URI"]
    AUTH = (
        os.environ["LOCAL_NEO4J_USER"],
        os.environ["LOCAL_NEO4J_PASSWORD"],
    )
    DATABASE = os.environ["LOCAL_NEO4J_DATABASE"]

else:
    raise ValueError("MODE must be either CLOUD or LOCAL")

DATA_DIR = "./data"



OS_NEW_FILE = os.path.join(DATA_DIR, "OS_new.ttl")
OS_EXTENDED_FILE = os.path.join(DATA_DIR, "OS_extended.ttl")
LSOA_FILE = os.path.join(DATA_DIR, "lsoa_wales_2011.xls")
WIMD_FILE = os.path.join(DATA_DIR, "wimd_2019.xlsx")
SCHOOLS_FILE = os.path.join(DATA_DIR, "schools_wales.csv")
FSM_FILE = os.path.join(DATA_DIR, "FSM.csv")
SCHOOL_METRICS_FILE = os.path.join(DATA_DIR, "welsh_schools_data_full.csv")
TRANSPORT_FILE = os.path.join(DATA_DIR, "transport_stops_wales.csv")
OS_TOPOLOGICAL_FILE = os.path.join(DATA_DIR, "OS_topological.nt")

LSOA_GPKG_FILE = os.path.join(
    DATA_DIR,
    "lsoa_wales_2011.gpkg"
)

RUN_OS_NEW_ENRICHMENT = False   
RUN_LSOA_LOAD = False           
RUN_WIMD_LOAD = False
RUN_STOP_LSOA_LINKS = False           
RUN_SCHOOLS_LOAD = False        
RUN_FSM_LOAD = False            
RUN_SCRAPED_SCHOOL_METRICS_LOAD = False 
RUN_TRANSPORT_LOAD = False      

RUN_LSOA_GEOMETRY_REPAIR = False   
RUN_ADMIN_LSOA_INTERSECTS = False
  
RUN_LSOA_TOUCHES = False           
RUN_LSOA_GRAPH_NEAR = False        
RUN_SCHOOL_LSOA_LINK = False       
RUN_SCHOOL_TRANSPORT_NEAR = False  
RUN_RELATION_ORIGIN_TAGGING = False
RUN_UNLINKED_LSOA_DIAGNOSTICS = False




TRANSPORT_NEAR_METRES = 800
# Allow for minor boundary-precision differences between source geometries.
TOUCH_TOLERANCE_METRES = 1

WELSH_UA_OS_IDS = {
    "25492", "25494", "25502", "25484", "25496", "44426",
    "25498", "25493", "25483", "25497", "25495", "25491",
    "25500", "25490", "25485", "25487", "25489", "25486",
    "25482", "25776", "44425", "25831"
}
# Transform WGS84 coordinates to British National Grid.
WGS84_TO_BNG = Transformer.from_crs(
    "EPSG:4326", "EPSG:27700", always_xy=True
).transform

HAS_OS_ID = URIRef("http://kr.di.uoa.gr/yago2geo/ontology/hasOS_ID")
HAS_OS_NAME = URIRef("http://kr.di.uoa.gr/yago2geo/ontology/hasOS_Name")
HAS_GEOMETRY = URIRef("http://www.opengis.net/ont/geosparql#hasGeometry")
AS_WKT = URIRef("http://www.opengis.net/ont/geosparql#asWKT")


SF_WITHIN = URIRef("http://www.opengis.net/ont/geosparql#sfWithin" )
SF_TOUCHES = URIRef("http://www.opengis.net/ont/geosparql#sfTouches" )

SF_WITHIN_ALT = URIRef("http://www.opengis.net/ont/geosparql#within" )
SF_TOUCHES_ALT = URIRef("http://www.opengis.net/ont/geosparql#touches" )

# Create a Neo4j driver using the selected environment configuration.
def driver():
    return GraphDatabase.driver(URI, auth=AUTH)


def clean_wkt(value):
    if value is None:
        return None
    text = str(value).strip()
    
    text = text.replace("<http://www.opengis.net/def/crs/EPSG/0/4326>", ""  )
    text = text.replace("<HTTP://WWW.OPENGIS.NET/DEF/CRS/EPSG/0/4326>", "")
    text = text.strip()
    
    if text.upper().startswith("DATA TRUNCATED "):
        text = text[len("DATA TRUNCATED "):].strip()
        
    return text





def clean_text(value):
    """Return a stripped string or None for empty / NaN values."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    return text


def clean_metric_number(value):
    """
    Convert scraped metric strings to floats.

    The My Local School scrape stores values such as "16.70%", "£5,470",
    and blank cells. This helper standardises them before Neo4j loading.
    """
    text = clean_text(value)
    if text is None:
        return None

    text = (
        text.replace("%", "")
        .replace("£", "")
        .replace(",", "")
        .replace("\u00a0", "")
        .strip()
    )

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def clean_metric_int(value):
    """Convert a scraped numeric field to an integer where possible."""
    number = clean_metric_number(value)
    if number is None:
        return None
    return int(round(number))


def normalise_school_phase(school_type):
    """
    Reduce the detailed school type into a policy-friendly phase group.

    Secondary performance columns are expected mainly for secondary and
    middle schools. Primary rows keep those fields as null.
    """
    text = (school_type or "").lower()
    if "secondary" in text:
        return "secondary"
    if "middle" in text:
        return "middle"
    if "special" in text:
        return "special"
    if any(token in text for token in ["nursery", "infants", "juniors", "primary"]):
        return "primary"
    return "other"


def first_available(*values):
    """Return the first non-null metric value from a priority list."""
    for value in values:
        if value is not None:
            return value
    return None


def local_name(uri):
    return str(uri).split("/")[-1]


def map_os_type(type_uri):
    t = local_name(type_uri)
    t_lower = t.lower()

    # Check Ward first because OS_COMMUNITYWARD
    # contains both "community" and "ward".
    if "ward" in t_lower:
        return "Ward"

    if "civilparish" in t_lower or "community" in t_lower:
        return "Community"

    if "unitaryauthority" in t_lower:
        return "UnitaryAuthority"

    return t


def extract_lon_lat(point_text):
    m = re.search(r"POINT\s*\(([-\d.]+)\s+([-\d.]+)\)", str(point_text))
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def confidence_from_distance(distance_m):
    if distance_m <= 100:
        return "high"
    if distance_m <= 1000:
        return "medium"
    return "low"

def parse_os_file(file_path):
    g = Graph()
    g.parse(file_path, format="turtle")
    rows = []
    relations = []

    for subject in set(g.subjects()):
        uri = str(subject)
        if "/osentity_" not in uri and "yago-knowledge.org/resource" not in uri:
            continue

        geom = g.value(subject, HAS_GEOMETRY)
        geom_uri = str(geom) if geom else None
        geom_wkt = clean_wkt(g.value(geom, AS_WKT)) if geom else None

        os_type = None
        raw_type = None
        for type_uri in g.objects(subject, RDF.type):
            candidate = map_os_type(type_uri)
            if candidate:
                os_type = candidate
                # Preserve the original RDF type alongside its normalised form.
                raw_type = local_name(type_uri)
                break

        name_value = g.value(subject, HAS_OS_NAME)
        os_id_value = g.value(subject, HAS_OS_ID)

        rows.append({
            "uri": uri,
            "name": str(name_value) if name_value else None,
            "os_id": str(os_id_value) if os_id_value else None,
            "type": os_type,
            "raw_type": raw_type,
            "geometry_uri": geom_uri,
            "wkt": geom_wkt,
        })

        # Read sfWithin predicates, including the alternative local name.
        for p in [SF_WITHIN, URIRef("http://www.opengis.net/ont/geosparql#within" )]:
            for obj in g.objects(subject, p):
                relations.append({"from": uri, "to": str(obj), "type": "WITHIN"})
        
        # Read sfTouches predicates, including the alternative local name.
        for p in [SF_TOUCHES, URIRef("http://www.opengis.net/ont/geosparql#touches" )]:
            for obj in g.objects(subject, p):
                relations.append({"from": uri, "to": str(obj), "type": "TOUCHES"})

    return rows, relations


def enrich_admin_units():
    print("Parsing OS_extended.ttl and OS_new.ttl for nodes...")
    extended_rows, _ = parse_os_file(OS_EXTENDED_FILE)
    new_rows, _ = parse_os_file(OS_NEW_FILE)

    # Merge node records from both Turtle source files.
    merged = {}
    for row in extended_rows + new_rows:
        uri = row["uri"]
        if uri not in merged: merged[uri] = row
        else:
            for key, value in row.items():
                if value is not None: merged[uri][key] = value
    rows = list(merged.values())

    # Read official topological relationships from OS_topological.nt.
    print("Parsing OS_topological.nt for official relations...")
    all_rels = []
    g_topo = Graph()
    g_topo.parse(OS_TOPOLOGICAL_FILE, format="nt")
    
    for s, p, o in g_topo:
        rel_uri = str(p)
        rel_type = None
        if "sfWithin" in rel_uri: rel_type = "WITHIN"
        elif "sfTouches" in rel_uri: rel_type = "TOUCHES"
        
        if rel_type:
            all_rels.append({"from": str(s), "to": str(o), "type": rel_type})

    print("Nodes to enrich:", len(rows))
    print("Official relations found:", len(all_rels))

    d = driver()
    
    # Load nodes before creating their relationships.
    with d.session(database=DATABASE) as s:
        for row in rows:
            s.run("""
            MERGE (n:AdminUnit {uri:$uri})
            SET n.name = coalesce($name, n.name),
                n.os_id = coalesce($os_id, n.os_id),
                n.type = coalesce($type, n.type),
                n.raw_type = coalesce($raw_type, n.raw_type),
                n.geometry_uri = coalesce($geometry_uri, n.geometry_uri),
                n.wkt = coalesce($wkt, n.wkt)
            """, **row)
    
    # Load relationships in batches with retry handling.
    print("Loading official relations to Neo4j (with auto-retry)...")
    batch_size = 1000
    for i in range(0, len(all_rels), batch_size):
        batch = all_rels[i : i + batch_size]
        
        # Preserve the source WITHIN and TOUCHES relationship types.
        retry_count = 0
        success = False
        while retry_count < 5 and not success:
            try:
                with d.session(database=DATABASE) as s:
                    s.run("""
                    UNWIND $batch AS rel
                    MATCH (a:AdminUnit {uri: rel.from})
                    MATCH (b:AdminUnit {uri: rel.to})
                    FOREACH (_ IN CASE WHEN rel.type = "WITHIN" THEN [1] ELSE [] END |
                        MERGE (a)-[r:WITHIN]->(b)
                        SET r.origin = "official_os_source",
                            r.method = "native_ttl_import"
                    )
                    FOREACH (_ IN CASE WHEN rel.type = "TOUCHES" THEN [1] ELSE [] END |
                        MERGE (a)-[r:TOUCHES]->(b)
                        SET r.origin = "official_os_source",
                            r.method = "native_ttl_import"
                    )
                    RETURN count(*)
                    """, batch=batch)
                success = True
            except Exception as e:
                retry_count += 1
                print(f"\nConnection lost at relation {i}, retrying ({retry_count}/5)... Error: {str(e)}")
                time.sleep(5)  # Brief delay before retrying.
        
        if not success:
            print(f"Failed to load batch starting at {i} after 5 attempts. Skipping...")

        if (i + batch_size) % 10000 == 0 or (i + batch_size) >= len(all_rels):
            print(f"Progress: {min(i + batch_size, len(all_rels))}/{len(all_rels)} relations loaded...")

    d.close()
    print("Official relationships loaded")

def load_lsoa():
    df = pd.read_excel(LSOA_FILE)
    print("Loading LSOA rows:", len(df))

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("""
        CREATE CONSTRAINT lsoa_code_unique IF NOT EXISTS
        FOR (l:LSOA) REQUIRE l.code IS UNIQUE
        """)

        for _, r in df.iterrows():
            s.run("""
            MERGE (l:LSOA {code:$code})
            SET l.name=$name,
                l.wkt=$wkt,
                l.source="ONS LSOA 2011"
            """,
            code=str(r["LSOA11Code"]),
            name=str(r["lsoa11name"]),
            wkt=str(r["wkb_geometry"]))

    d.close()
    print("LSOA loaded")


def load_wimd():
    df = pd.read_excel(WIMD_FILE)
    df.columns = [str(c).strip() for c in df.columns]
    print("Loading WIMD rows:", len(df))

    d = driver()
    with d.session(database=DATABASE) as s:
        for _, r in df.iterrows():
            rank = pd.to_numeric(r.get("WIMD 2019"), errors="coerce")
            if pd.isna(rank):
                continue

            rank = int(rank)
            decile = min(10, ((rank - 1) // 191) + 1)
            deprivation = (
                "high_deprivation" if decile <= 3
                else "medium_deprivation" if decile <= 7
                else "low_deprivation"
            )

            s.run("""
            MATCH (l:LSOA {code:$code})
            SET l.local_authority=$la,
                l.wimd_rank=$rank,
                l.wimd_decile=$decile,
                l.deprivation=$deprivation,
                l.education_rank=$education_rank,
                l.income_rank=$income_rank,
                l.employment_rank=$employment_rank,
                l.health_rank=$health_rank,
                l.access_rank=$access_rank,
                l.housing_rank=$housing_rank,
                l.safety_rank=$safety_rank,
                l.environment_rank=$environment_rank
            """,
            code=str(r["LSOA code"]),
            la=str(r["Local Authority name (Eng)"]),
            rank=rank,
            decile=decile,
            deprivation=deprivation,
            education_rank=int(r["Education"]) if pd.notna(r.get("Education")) else None,
            income_rank=int(r["Income"]) if pd.notna(r.get("Income")) else None,
            employment_rank=int(r["Employment"]) if pd.notna(r.get("Employment")) else None,
            health_rank=int(r["Health"]) if pd.notna(r.get("Health")) else None,
            access_rank=int(r["Access to Services"]) if pd.notna(r.get("Access to Services")) else None,
            housing_rank=int(r["Housing"]) if pd.notna(r.get("Housing")) else None,
            safety_rank=int(r["Community Safety"]) if pd.notna(r.get("Community Safety")) else None,
            environment_rank=int(r["Physical Environment"]) if pd.notna(r.get("Physical Environment")) else None)

    d.close()
    print("WIMD attached")


def load_schools():
    df = pd.read_csv(SCHOOLS_FILE)
    print("Loading School rows:", len(df))

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("""
        CREATE CONSTRAINT school_code_unique IF NOT EXISTS
        FOR (sch:School) REQUIRE sch.code IS UNIQUE
        """)

        for _, r in df.iterrows():
            lon, lat = extract_lon_lat(r.get("geom"))

            s.run("""
            MERGE (sch:School {code:$code})
            SET sch.name=$name,
                sch.local_authority=$la,
                sch.school_type=$school_type,
                sch.sector=$sector,
                sch.governance=$governance,
                sch.postcode=$postcode,
                sch.pupils=$pupils,
                sch.longitude=$lon,
                sch.latitude=$lat,
                sch.geom=$geom
            """,
            code=str(r.get("school_code")),
            name=str(r.get("school_name")),
            la=str(r.get("local_authority")),
            school_type=str(r.get("school_type")),
            sector=str(r.get("sector")),
            governance=str(r.get("governance")),
            postcode=str(r.get("postcode")),
            pupils=int(r.get("pupils")) if pd.notna(r.get("pupils")) else None,
            lon=lon,
            lat=lat,
            geom=str(r.get("geom")))

    d.close()
    print("Schools loaded")


def load_fsm():
    df = pd.read_csv(FSM_FILE)
    print("Loading FSM rows:", len(df))

    # Remove thousands separators before numeric conversion.
    df["value_numeric"] = pd.to_numeric(
        df["Data values"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce"
    )

    # Separate pupil counts from official percentages.
    count_rows = df[
        df["Data description_reference"].astype(str).str.upper() == "NUM"
    ].copy()

    percentage_rows = df[
        df["Data description_reference"].astype(str).str.upper() == "PCT"
    ].copy()

    count_pivot = count_rows.pivot_table(
        index="School_reference",
        columns="Category_reference",
        values="value_numeric",
        aggfunc="first"
    ).reset_index()

    percentage_pivot = percentage_rows.pivot_table(
        index="School_reference",
        columns="Category_reference",
        values="value_numeric",
        aggfunc="first"
    ).reset_index()

    # Rename columns clearly before merging.
    count_pivot = count_pivot.rename(columns={
        "fsm": "fsm_count",
        "fsmtp": "fsmtp_count",
        "all": "all_pupils"
    })

    percentage_pivot = percentage_pivot.rename(columns={
        "fsm": "fsm_pct",
        "fsmtp": "fsmtp_pct"
    })

    merged = count_pivot.merge(
        percentage_pivot[
            ["School_reference", "fsm_pct", "fsmtp_pct"]
        ],
        on="School_reference",
        how="left"
    )

    print("FSM schools available in source:", len(merged))

    d = driver()
    updated = 0

    with d.session(database=DATABASE) as s:
        for _, r in merged.iterrows():
            result = s.run("""
            MATCH (sch:School {code:$code})
            SET sch.fsm_count = $fsm_count,
                sch.fsmtp_count = $fsmtp_count,
                sch.fsm_all_pupils = $all_pupils,
                sch.fsm_pct = $fsm_pct,
                sch.fsmtp_pct = $fsmtp_pct,
                sch.fsm_source = "StatsWales",
                sch.fsm_value_method = "official_NUM_and_PCT_rows"
            RETURN count(sch) AS c
            """,
            code=str(int(r["School_reference"])),
            fsm_count=(
                float(r["fsm_count"])
                if pd.notna(r.get("fsm_count")) else None
            ),
            fsmtp_count=(
                float(r["fsmtp_count"])
                if pd.notna(r.get("fsmtp_count")) else None
            ),
            all_pupils=(
                float(r["all_pupils"])
                if pd.notna(r.get("all_pupils")) else None
            ),
            fsm_pct=(
                float(r["fsm_pct"])
                if pd.notna(r.get("fsm_pct")) else None
            ),
            fsmtp_pct=(
                float(r["fsmtp_pct"])
                if pd.notna(r.get("fsmtp_pct")) else None
            ))

            updated += result.single()["c"]

    d.close()
    print("FSM attached to schools:", updated)


def load_scraped_school_metrics():
    """
    Attach My Local School Wales scraped metrics to existing School nodes.

    Supervisor alignment:
    - This enriches the Education Use Case with school-level evidence
      required for SCQ1, SCQ2, SCQ4, SCQ7 and SCQ8.
    - Primary schools usually have FSM, PTR, attendance and budget fields.
    - Secondary / middle schools additionally expose performance metrics
      such as capped 9, literacy, numeracy, science and Welsh Bacc scores.
    - The function updates School nodes by their existing School.code value,
      so it does not replace the main geography loader or rebuild spatial
      relationships such as LOCATED_IN and DISTANCE_NEAR.
    """
    if not os.path.exists(SCHOOL_METRICS_FILE):
        print("School metrics file not found:", SCHOOL_METRICS_FILE)
        return

    df = pd.read_csv(SCHOOL_METRICS_FILE, low_memory=False)
    print("Loading scraped school metric rows:", len(df))

    primary_fsm = "Free school meals (FSM) - 3 year average (Primary)"
    primary_ptr = "Pupil Teacher Ratio (PTR) (Primary)"
    primary_attendance = "% Attendance during the year (Primary only)"

    secondary_fsm = "Free school meals (FSM) - 3 year average (Secondary)"
    secondary_ptr = "Pupil Teacher Ratio (PTR) (Secondary)"
    secondary_attendance = "% Attendance during the year (Secondary only)"

    capped9 = "Capped 9 points score (interim measures version)"
    literacy = "Literacy points score"
    numeracy = "Numeracy points score"
    science = "Science points score"
    welsh_bacc = (
        "Welsh Baccalaureate Skills Challenge Certificate points score"
    )

    d = driver()
    updated = 0
    secondary_performance_rows = 0

    with d.session(database=DATABASE) as s:
        for _, r in df.iterrows():
            school_code = clean_text(r.get("ref")) or clean_text(r.get("_key"))
            if school_code is None:
                continue

            school_type = clean_text(r.get("Type"))
            phase_group = normalise_school_phase(school_type)

            fsm_primary_pct = clean_metric_number(r.get(primary_fsm))
            fsm_secondary_pct = clean_metric_number(r.get(secondary_fsm))
            ptr_primary = clean_metric_number(r.get(primary_ptr))
            ptr_secondary = clean_metric_number(r.get(secondary_ptr))
            attendance_primary_pct = clean_metric_number(
                r.get(primary_attendance)
            )
            attendance_secondary_pct = clean_metric_number(
                r.get(secondary_attendance)
            )

            if phase_group == "secondary":
                fsm_pct = first_available(fsm_secondary_pct, fsm_primary_pct)
                pupil_teacher_ratio = first_available(ptr_secondary, ptr_primary)
                attendance_pct = first_available(
                    attendance_secondary_pct,
                    attendance_primary_pct
                )
            elif phase_group == "primary":
                fsm_pct = first_available(fsm_primary_pct, fsm_secondary_pct)
                pupil_teacher_ratio = first_available(ptr_primary, ptr_secondary)
                attendance_pct = first_available(
                    attendance_primary_pct,
                    attendance_secondary_pct
                )
            else:
                fsm_pct = first_available(fsm_secondary_pct, fsm_primary_pct)
                pupil_teacher_ratio = first_available(ptr_secondary, ptr_primary)
                attendance_pct = first_available(
                    attendance_secondary_pct,
                    attendance_primary_pct
                )

            capped9_score = clean_metric_number(r.get(capped9))
            literacy_score = clean_metric_number(r.get(literacy))
            numeracy_score = clean_metric_number(r.get(numeracy))
            science_score = clean_metric_number(r.get(science))
            welsh_bacc_score = clean_metric_number(r.get(welsh_bacc))

            has_secondary_performance = any([
                capped9_score is not None,
                literacy_score is not None,
                numeracy_score is not None,
                science_score is not None,
                welsh_bacc_score is not None,
            ])

            if has_secondary_performance:
                secondary_performance_rows += 1

            result = s.run("""
            MERGE (sch:School {code:$code})
            SET sch.school_id = $code,
                sch.ref = $code,
                sch.url = $url,
                sch.name = coalesce($name, sch.name),
                sch.local_authority_name = $local_authority_name,
                sch.phase = $phase,
                sch.phase_group = $phase_group,
                sch.gender_mix = $gender_mix,
                sch.language_medium = $language_medium,
                sch.pupils_2025 = $pupils_2025,
                sch.fsm_primary_pct = $fsm_primary_pct,
                sch.fsm_secondary_pct = $fsm_secondary_pct,
                sch.fsm_pct = $fsm_pct,
                sch.pupil_teacher_ratio_primary = $ptr_primary,
                sch.pupil_teacher_ratio_secondary = $ptr_secondary,
                sch.pupil_teacher_ratio = $pupil_teacher_ratio,
                sch.attendance_primary_pct = $attendance_primary_pct,
                sch.attendance_secondary_pct = $attendance_secondary_pct,
                sch.attendance_pct = $attendance_pct,
                sch.budget_per_pupil_gbp = $budget_per_pupil_gbp,
                sch.capped9_score = $capped9_score,
                sch.literacy_score = $literacy_score,
                sch.numeracy_score = $numeracy_score,
                sch.science_score = $science_score,
                sch.welsh_bacc_score = $welsh_bacc_score,
                sch.has_secondary_performance = $has_secondary_performance,
                sch.address = $address,
                sch.postcode = coalesce($postcode, sch.postcode),
                sch.telephone = $telephone,
                sch.metrics_source = "mylocalschool.gov.wales",
                sch.metrics_loaded = true
            WITH sch
            OPTIONAL MATCH (la:AdminUnit)
            WHERE $local_authority_name IS NOT NULL
              AND toLower(coalesce(la.name, "")) =
                  toLower($local_authority_name)
            FOREACH (_ IN CASE WHEN la IS NULL THEN [] ELSE [1] END |
                MERGE (sch)-[:IN_LOCAL_AUTHORITY]->(la)
            )
            RETURN count(sch) AS c
            """,
            code=school_code,
            url=clean_text(r.get("url")),
            name=clean_text(r.get("school_name")),
            local_authority_name=clean_text(r.get("Local Authority")),
            phase=school_type,
            phase_group=phase_group,
            gender_mix=clean_text(r.get("Gender Mix")),
            language_medium=clean_text(r.get("Language")),
            pupils_2025=clean_metric_int(r.get("Number of pupils, 2025")),
            fsm_primary_pct=fsm_primary_pct,
            fsm_secondary_pct=fsm_secondary_pct,
            fsm_pct=fsm_pct,
            ptr_primary=ptr_primary,
            ptr_secondary=ptr_secondary,
            pupil_teacher_ratio=pupil_teacher_ratio,
            attendance_primary_pct=attendance_primary_pct,
            attendance_secondary_pct=attendance_secondary_pct,
            attendance_pct=attendance_pct,
            budget_per_pupil_gbp=clean_metric_number(
                r.get("School budget per pupil")
            ),
            capped9_score=capped9_score,
            literacy_score=literacy_score,
            numeracy_score=numeracy_score,
            science_score=science_score,
            welsh_bacc_score=welsh_bacc_score,
            has_secondary_performance=has_secondary_performance,
            address=clean_text(r.get("Address")),
            postcode=clean_text(r.get("postcode")),
            telephone=clean_text(r.get("Telephone")))

            updated += result.single()["c"]

    d.close()
    print("Scraped school metrics attached:", updated)
    print(
        "Rows with secondary performance metrics:",
        secondary_performance_rows
    )


def load_transport():
    df = pd.read_csv(TRANSPORT_FILE, low_memory=False)
    print("Loading TransportStop rows:", len(df))

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("""
        CREATE CONSTRAINT transport_code_unique IF NOT EXISTS
        FOR (t:TransportStop) REQUIRE t.code IS UNIQUE
        """)

        for _, r in df.iterrows():
            lat = pd.to_numeric(r.get("Latitude"), errors="coerce")
            lon = pd.to_numeric(r.get("Longitude"), errors="coerce")

            if pd.isna(lat) or pd.isna(lon):
                continue

            s.run("""
            MERGE (t:TransportStop {code:$code})
            SET t.name=$name,
                t.locality=$locality,
                t.stop_type=$stop_type,
                t.status=$status,
                t.latitude=$lat,
                t.longitude=$lon
            """,
            code=str(r.get("ATCOCode")),
            name=str(r.get("CommonName")),
            locality=str(r.get("LocalityName")),
            stop_type=str(r.get("StopType")),
            status=str(r.get("Status")),
            lat=float(lat),
            lon=float(lon))

    d.close()
    print("Transport loaded")

def get_lsoa_geoms():
    """
    Read LSOA geometries from Neo4j, validate each geometry,
    and report any WKT values that cannot be parsed.

    Returns:
        list[dict]: Successfully parsed LSOA geometry records.
    """

    d = driver()

    with d.session(database=DATABASE) as s:
        rows = s.run("""
        MATCH (l:LSOA)
        RETURN
            l.code AS code,
            l.wkt AS wkt,
            l.local_authority AS local_authority
        """).data()

    d.close()

    out = []
    failed = []

    for r in rows:
        try:
            raw_wkt = r.get("wkt")

            if raw_wkt is None or not str(raw_wkt).strip():
                raise ValueError("Missing WKT")

            cleaned_wkt = clean_wkt(raw_wkt)

            if cleaned_wkt is None or not str(cleaned_wkt).strip():
                raise ValueError("Empty WKT after cleaning")

            geom = wkt.loads(cleaned_wkt)
            geom = make_valid(geom)

            if geom.is_empty:
                raise ValueError("Empty geometry after make_valid")

            out.append({
                "code": r["code"],
                "geometry": geom,
                "local_authority": r["local_authority"]
            })

        except Exception as exc:
            failed.append({
                "code": r.get("code"),
                "local_authority": r.get("local_authority"),
                "error": str(exc),
                "wkt_length": (
                    len(str(r.get("wkt")))
                    if r.get("wkt") is not None
                    else 0
                ),
                "wkt_sample": (
                    str(r.get("wkt"))[:300]
                    if r.get("wkt") is not None
                    else ""
                )
            })

    print("LSOA nodes read from Neo4j:", len(rows))
    print("LSOA geometries parsed successfully:", len(out))
    print("LSOA geometries failed:", len(failed))

    if failed:
        failed_df = pd.DataFrame(failed)

        print("\nFailed geometry error summary:")
        print(
            failed_df["error"]
            .value_counts()
            .head(20)
        )

        print("\nFailed WKT length summary:")
        print(
            failed_df["wkt_length"]
            .describe()
        )

        failed_file = os.path.join(
            DATA_DIR,
            "failed_lsoa_geometries.csv"
        )

        failed_df.to_csv(
            failed_file,
            index=False
        )

        print(
            "Failed geometry details written to:",
            failed_file
        )

    return out


def build_lsoa_touches():
    print("Computing LSOA_TOUCHES...")

    lsoas = get_lsoa_geoms()
    codes = [x["code"] for x in lsoas]
    polygons = [x["geometry"] for x in lsoas]
    # Use a spatial index to reduce geometry comparisons.
    tree = STRtree(polygons)
    pairs = set()

    for i, geom in enumerate(polygons):
        code = codes[i]

        for j in tree.query(geom.buffer(TOUCH_TOLERANCE_METRES)):
            j = int(j)

            if i == j:
                continue

            other = polygons[j]
            other_code = codes[j]

            if code >= other_code:
                continue

            if geom.touches(other) or geom.boundary.distance(other.boundary) <= TOUCH_TOLERANCE_METRES:
                pairs.add((code, other_code))

    print("LSOA_TOUCHES pairs:", len(pairs))

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("MATCH (:LSOA)-[r:LSOA_TOUCHES]->(:LSOA) DELETE r")

        for a, b in pairs:
            s.run("""
            MATCH (a:LSOA {code:$a})
            MATCH (b:LSOA {code:$b})
            MERGE (a)-[r:LSOA_TOUCHES]->(b)
            SET r.origin = "geometry",
                r.method = "polygon_touches",
                r.tolerance_m = $tolerance
            """, a=a, b=b, tolerance=TOUCH_TOLERANCE_METRES)

    d.close()
    print("LSOA_TOUCHES loaded")


def build_lsoa_graph_near():
    print("Computing GRAPH_NEAR for LSOA...")

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("MATCH (:LSOA)-[r:GRAPH_NEAR]->(:LSOA) DELETE r")
        # Derive graph proximity from two LSOA_TOUCHES hops, not distance.
        s.run("""
        MATCH (a:LSOA)-[:LSOA_TOUCHES]-(mid:LSOA)-[:LSOA_TOUCHES]-(b:LSOA)
        WHERE a.code <> b.code
          AND NOT (a)-[:LSOA_TOUCHES]-(b)
        MERGE (a)-[r:GRAPH_NEAR]->(b)
        SET r.origin = "derived",
            r.method = "two_hop_lsoa_touches",
            r.hops = 2
        """)

    d.close()
    print("GRAPH_NEAR loaded")


def get_admin_geoms():
    d = driver()
    with d.session(database=DATABASE) as s:
        rows = s.run("""
        MATCH (a:AdminUnit)
        WHERE a.wkt IS NOT NULL
          AND a.type IN ["Ward","Community","UnitaryAuthority"]
        RETURN a.uri AS uri, a.name AS name, a.type AS type, a.wkt AS wkt
        """).data()
    d.close()

    out = []
    for r in rows:
        try:
            geom_wgs84 = make_valid(
                wkt.loads(clean_wkt(r["wkt"]))
            )

            geom_bng = make_valid(
                transform(WGS84_TO_BNG, geom_wgs84)
            )
            out.append({
                "uri": r["uri"],
                "type": r["type"],
                "name": r["name"],
                "geometry": geom_bng
            })
        except Exception:
            pass

    return out


def repair_lsoa_wkt_from_geopackage():
    print("Reading official LSOA GeoPackage...")
    gdf = gpd.read_file(LSOA_GPKG_FILE)
    code_column = "LSOA11Code" if "LSOA11Code" in gdf.columns else "lsoa11code"
    if str(gdf.crs).upper() != "EPSG:27700":
        gdf = gdf.to_crs("EPSG:27700")

    updates = []
    for _, row in gdf.iterrows():
        code = str(row[code_column]).strip()
        geom = make_valid(row.geometry)
        if not geom.is_empty:
            updates.append({"code": code, "wkt": geom.wkt})

    print(f"Valid official geometries prepared: {len(updates)}")
    
    d = driver()
    updated_total = 0
    batch_size = 20
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        try:
            with d.session(database=DATABASE) as s:
                result = s.run("""
                UNWIND $rows AS row
                MATCH (l:LSOA {code: row.code})
                SET l.wkt = row.wkt,
                    l.geometry_source = 'DataMapWales LSOA Wales 2011',
                    l.geometry_repaired = true
                RETURN count(l) AS updated
                """, rows=batch)
                updated_total += result.single()["updated"]
            print(f"Progress: {min(i + batch_size, len(updates))}/{len(updates)} repaired...")
            time.sleep(0.5)  # Brief pause between update batches.
        except Exception as e:
            print(f"Error in batch {i}: {e}. Retrying next batch...")
            continue
    
    d.close()
    print(f"Truncated LSOA geometries repaired: {updated_total}")

def build_admin_lsoa_intersects():
    print("Computing AdminUnit INTERSECTS LSOA...")
    lsoas = get_lsoa_geoms()
    admins = get_admin_geoms()
    lsoa_codes = [x["code"] for x in lsoas]
    lsoa_polygons = [x["geometry"] for x in lsoas]
    lsoa_tree = STRtree(lsoa_polygons)
    rels = []

    for admin in admins:
        admin_geom = make_valid(admin["geometry"])
        for j in lsoa_tree.query(admin_geom):
            lsoa_geom = make_valid(lsoa_polygons[int(j)])
            if admin_geom.intersects(lsoa_geom):
                rels.append({"admin_uri": admin["uri"], "lsoa_code": lsoa_codes[int(j)], "admin_type": admin["type"]})

    print(f"Admin-LSOA INTERSECTS pairs found: {len(rels)}")

    d = driver()
    batch_size = 500
    with d.session(database=DATABASE) as s:
        s.run("MATCH (:AdminUnit)-[r:INTERSECTS]->(:LSOA) DELETE r")
        
        for i in range(0, len(rels), batch_size):
            batch = rels[i : i + batch_size]
            s.run("""
            UNWIND $rows AS row
            MATCH (a:AdminUnit {uri: row.admin_uri})
            MATCH (l:LSOA {code: row.lsoa_code})
            MERGE (a)-[r:INTERSECTS]->(l)
            SET r.origin = 'geometry', r.method = 'polygon_intersects', r.admin_type = row.admin_type
            """, rows=batch)
            print(f"Progress: {min(i + batch_size, len(rels))}/{len(rels)} relationships loaded...")

    d.close()
    print("AdminUnit-LSOA INTERSECTS loaded successfully")

def diagnose_unlinked_lsoas():
    print("Diagnosing LSOAs without Welsh UA INTERSECTS...")

    lsoas = get_lsoa_geoms()
    d = driver()

    with d.session(database=DATABASE) as s:
        linked_codes = {
            row["code"]
            for row in s.run("""
            MATCH (ua:AdminUnit)-[:INTERSECTS]->(l:LSOA)
            WHERE ua.type = 'UnitaryAuthority'
              AND ua.os_id IN $welsh_ids
            RETURN DISTINCT l.code AS code
            """, welsh_ids=list(WELSH_UA_OS_IDS)).data()
        }

        ua_rows = s.run("""
        MATCH (ua:AdminUnit)
        WHERE ua.type = 'UnitaryAuthority'
          AND ua.os_id IN $welsh_ids
          AND ua.wkt IS NOT NULL
        RETURN ua.name AS name,
               ua.uri AS uri,
               ua.os_id AS os_id,
               ua.wkt AS wkt
        """, welsh_ids=list(WELSH_UA_OS_IDS)).data()

    authorities = []

    for row in ua_rows:
        try:
            geom_wgs84 = make_valid(
                wkt.loads(clean_wkt(row["wkt"]))
            )

            geom_bng = make_valid(
                transform(WGS84_TO_BNG, geom_wgs84)
            )

            authorities.append({
                "name": row["name"],
                "uri": row["uri"],
                "os_id": row["os_id"],
                "geometry": geom_bng
            })
        except Exception as exc:
            print(
                "Skipped authority geometry:",
                row["name"],
                exc
            )

    authority_geometries = [
        item["geometry"] for item in authorities
    ]
    tree = STRtree(authority_geometries)

    results = []



    for lsoa in lsoas:
        if lsoa["code"] in linked_codes:
            continue

        lsoa_geom = make_valid(lsoa["geometry"])
        point = lsoa_geom.representative_point()

        res = tree.nearest(point)
        if res is not None:
            nearest_index = int(res)
            authority = authorities[nearest_index]
        else:
            continue 



        distance_m = float(
            point.distance(authority["geometry"])
        )

        results.append({
            "lsoa_code": lsoa["code"],
            "local_authority": lsoa["local_authority"],
            "nearest_authority": authority["name"],
            "nearest_authority_os_id": authority["os_id"],
            "distance_m": distance_m
        })

    df = pd.DataFrame(results)

    output_file = os.path.join(
        DATA_DIR,
        "unlinked_lsoa_diagnostics.csv"
    )

    df.to_csv(output_file, index=False)

    print("\nUnlinked LSOA count:", len(df))

    if not df.empty:
        print("\nDistance summary:")
        print(df["distance_m"].describe())

        print("\nDistance bands:")
        print(pd.cut(
            df["distance_m"],
            bins=[-1, 100, 1000, 5000, float("inf")],
            labels=[
                "0-100 m",
                "101-1000 m",
                "1-5 km",
                "over 5 km"
            ]
        ).value_counts().sort_index())

    print(
        "\nDiagnostics written to:",
        output_file
    )

    d.close()

def load_stop_lsoa_links():
    """
    Link each TransportStop to the LSOA whose polygon contains it, creating
    (:TransportStop)-[:LOCATED_IN]->(:LSOA).

    Transport-stop coordinates are stored in WGS84 (EPSG:4326), while the
    recovered LSOA polygons use British National Grid (EPSG:27700).
    Each stop point is therefore transformed before point-in-polygon matching.

    Gated by RUN_STOP_LSOA_LINKS.
    """

    print("Computing TransportStop LOCATED_IN LSOA...")

    lsoas = get_lsoa_geoms()
    lsoa_codes = [x["code"] for x in lsoas]
    lsoa_polygons = [x["geometry"] for x in lsoas]
    tree = STRtree(lsoa_polygons)

    made = 0
    unmatched = 0

    d = driver()

    with d.session(database=DATABASE) as s:
        s.run(
            "MATCH (:TransportStop)-[r:LOCATED_IN]->(:LSOA) DELETE r"
        )

        stops = s.run("""
            MATCH (t:TransportStop)
            WHERE t.latitude IS NOT NULL
              AND t.longitude IS NOT NULL
            RETURN
                t.code AS code,
                t.latitude AS lat,
                t.longitude AS lon
        """).data()

        print("Transport stops with coordinates:", len(stops))

        for st in stops:
            # Convert the WGS84 stop coordinates to British National Grid
            # before comparison with the LSOA polygons.
            p = transform(
                WGS84_TO_BNG,
                Point(
                    float(st["lon"]),
                    float(st["lat"])
                )
            )

            placed = False

            for j in tree.query(p):
                j = int(j)
                polygon = lsoa_polygons[j]

                # covers() includes points inside the polygon and points
                # located exactly on its boundary.
                if polygon.covers(p):
                    s.run("""
                        MATCH (t:TransportStop {code:$stop_code})
                        MATCH (l:LSOA {code:$lsoa_code})
                        MERGE (t)-[r:LOCATED_IN]->(l)
                        SET r.origin = "geometry",
                            r.method = "point_in_polygon",
                            r.distance_m = 0.0,
                            r.confidence = "high"
                    """,
                    stop_code=st["code"],
                    lsoa_code=lsoa_codes[j])

                    made += 1
                    placed = True
                    break

            if not placed:
                unmatched += 1

    d.close()

    print("TransportStop LOCATED_IN LSOA created:", made)
    print("Transport stops not matched to an LSOA:", unmatched)

def build_school_lsoa_links():
    print("Computing School LOCATED_IN LSOA with quality metadata...")

    lsoas = get_lsoa_geoms()
    lsoa_codes = [x["code"] for x in lsoas]
    lsoa_las = [x["local_authority"] for x in lsoas]
    lsoa_polygons = [x["geometry"] for x in lsoas]

    tree = STRtree(lsoa_polygons)

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("MATCH (:School)-[r:LOCATED_IN]->(:LSOA) DELETE r")

        schools = s.run("""
        MATCH (sch:School)
        WHERE sch.latitude IS NOT NULL AND sch.longitude IS NOT NULL
        RETURN sch.code AS code,
               sch.latitude AS lat,
               sch.longitude AS lon,
               sch.local_authority AS local_authority
        """).data()

        linked_inside = 0
        linked_nearest = 0

        for sch in schools:
            p = transform(WGS84_TO_BNG, Point(float(sch["lon"]), float(sch["lat"])))
            school_la = sch["local_authority"]

            found = False

            # First: direct point-in-polygon link
            for j in tree.query(p):
                j = int(j)
                poly = lsoa_polygons[j]

                if poly.covers(p) or poly.intersects(p):
                    lsoa_code = lsoa_codes[j]
                    lsoa_la = lsoa_las[j]
                    la_match = (school_la == lsoa_la)

                    s.run("""
                    MATCH (sch:School {code:$school_code})
                    MATCH (l:LSOA {code:$lsoa_code})
                    MERGE (sch)-[r:LOCATED_IN]->(l)
                    SET r.origin = "geometry",
                        r.method = "point_in_polygon",
                        r.distance_m = 0.0,
                        r.confidence = "high",
                        r.la_match = $la_match
                    """,
                    school_code=sch["code"],
                    lsoa_code=lsoa_code,
                    la_match=la_match)

                    linked_inside += 1
                    found = True
                    break

            # Second: nearest LSOA fallback with quality metadata
            if not found:
                nearest_index = int(tree.nearest(p))
                nearest_poly = lsoa_polygons[nearest_index]
                nearest_code = lsoa_codes[nearest_index]
                nearest_la = lsoa_las[nearest_index]

                distance_m = float(p.distance(nearest_poly))
                la_match = (school_la == nearest_la)
                confidence = confidence_from_distance(distance_m)

                s.run("""
                MATCH (sch:School {code:$school_code})
                MATCH (l:LSOA {code:$lsoa_code})
                MERGE (sch)-[r:LOCATED_IN]->(l)
                SET r.origin = "geometry",
                    r.method = "nearest_lsoa",
                    r.distance_m = $distance_m,
                    r.confidence = $confidence,
                    r.la_match = $la_match
                """,
                school_code=sch["code"],
                lsoa_code=nearest_code,
                distance_m=distance_m,
                confidence=confidence,
                la_match=la_match)

                linked_nearest += 1

    d.close()

    print("Schools linked by point-in-polygon:", linked_inside)
    print("Schools linked by nearest LSOA:", linked_nearest)
    print("Schools linked total:", linked_inside + linked_nearest)


def build_school_transport_near():
    print("Computing School DISTANCE_NEAR TransportStop...")

    radius = TRANSPORT_NEAR_METRES

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("MATCH (:School)-[r:DISTANCE_NEAR]->(:TransportStop) DELETE r")

        stops = s.run("""
        MATCH (t:TransportStop)
        WHERE t.latitude IS NOT NULL AND t.longitude IS NOT NULL
        RETURN t.code AS code, t.latitude AS lat, t.longitude AS lon
        """).data()

        stop_codes = []
        stop_points = []

        for t in stops:
            p = transform(WGS84_TO_BNG, Point(float(t["lon"]), float(t["lat"])))
            stop_codes.append(t["code"])
            stop_points.append(p)

        tree = STRtree(stop_points)

        schools = s.run("""
        MATCH (sch:School)
        WHERE sch.latitude IS NOT NULL AND sch.longitude IS NOT NULL
        RETURN sch.code AS code, sch.latitude AS lat, sch.longitude AS lon
        """).data()

        rels = 0

        for sch in schools:
            p = transform(WGS84_TO_BNG, Point(float(sch["lon"]), float(sch["lat"])))

            for j in tree.query(p.buffer(radius)):
                j = int(j)
                stop_point = stop_points[j]
                distance_m = float(p.distance(stop_point))

                if distance_m <= radius:
                    s.run("""
                    MATCH (sch:School {code:$school_code})
                    MATCH (t:TransportStop {code:$stop_code})
                    MERGE (sch)-[r:DISTANCE_NEAR]->(t)
                    SET r.origin = "geometry",
                        r.method = "point_distance",
                        r.threshold_m = $threshold_m,
                        r.distance_m = $distance_m
                    """,
                    school_code=sch["code"],
                    stop_code=stop_codes[j],
                    threshold_m=TRANSPORT_NEAR_METRES,
                    distance_m=distance_m)

                    rels += 1

    d.close()
    print("School-Transport DISTANCE_NEAR loaded:", rels)


def tag_existing_relation_origins():
    print("Tagging existing native and derived relationship origins...")

    d = driver()
    with d.session(database=DATABASE) as s:
        s.run("""
        MATCH ()-[r:TOUCHES]->()
        SET r.origin = "native_yago",
            r.method = "asserted_in_yago2geo"
        """)

        s.run("""
        MATCH ()-[r:WITHIN]->()
        SET r.origin = "native_yago",
            r.method = "asserted_in_yago2geo"
        """)

        s.run("""
        MATCH ()-[r:LSOA_TOUCHES]->()
        SET r.origin = coalesce(r.origin, "geometry")
        """)

        s.run("""
        MATCH ()-[r:GRAPH_NEAR]->()
        SET r.origin = coalesce(r.origin, "derived")
        """)

        s.run("""
        MATCH ()-[r:INTERSECTS]->()
        SET r.origin = coalesce(r.origin, "geometry")
        """)

        s.run("""
        MATCH ()-[r:DISTANCE_NEAR]->()
        SET r.origin = coalesce(r.origin, "geometry")
        """)

    d.close()
    print("Relationship origins tagged")


def verify():
    d = driver()
    # Open a session on the configured database.
    with d.session(database=DATABASE) as s:
        print("\nNode counts:")
        for r in s.run("""
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN label, count(*) AS count
        ORDER BY label
        """).data():
            print(f"  {r['label']}: {r['count']}")

        print("\nRelationship counts:")
        for r in s.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
        """).data():
            print(f"  {r['type']}: {r['count']}")

        print("\nAdmin-LSOA INTERSECTS by admin type:")
        for r in s.run("""
        MATCH (:AdminUnit)-[rel:INTERSECTS]->(:LSOA)
        RETURN rel.admin_type AS type, count(*) AS count
        ORDER BY count DESC
        """).data():
            print(f"  {r['type']}: {r['count']}")

        print("\nSchool-LSOA link methods:")
        for r in s.run("""
        MATCH (:School)-[rel:LOCATED_IN]->(:LSOA)
        RETURN rel.method AS method, count(*) AS count
        ORDER BY count DESC
        """).data():
            print(f"  {r['method']}: {r['count']}")

        print("\nNearest LSOA confidence:")
        for r in s.run("""
        MATCH (:School)-[rel:LOCATED_IN {method:"nearest_lsoa"}]->(:LSOA)
        RETURN rel.confidence AS confidence, count(*) AS count
        ORDER BY count DESC
        """).data():
            print(f"  {r['confidence']}: {r['count']}")

        print("\nNearest LSOA Local Authority match:")
        for r in s.run("""
        MATCH (:School)-[rel:LOCATED_IN {method:"nearest_lsoa"}]->(:LSOA)
        RETURN rel.la_match AS la_match, count(*) AS count
        ORDER BY count DESC
        """).data():
            print(f"  {r['la_match']}: {r['count']}")

        print("\nFSM schools:")
        print(s.run("""
        MATCH (sch:School)
        WHERE sch.fsm_pct IS NOT NULL
        RETURN count(sch) AS c
        """).single()["c"])

    d.close()

if __name__ == "__main__":
    if RUN_OS_NEW_ENRICHMENT:
        enrich_admin_units()

    if RUN_LSOA_LOAD:
        load_lsoa()

    if RUN_WIMD_LOAD:
        load_wimd()

    if RUN_STOP_LSOA_LINKS:
        load_stop_lsoa_links()

    if RUN_SCHOOLS_LOAD:
        load_schools()

    if RUN_FSM_LOAD:
        load_fsm()

    if RUN_SCRAPED_SCHOOL_METRICS_LOAD:
        load_scraped_school_metrics()

    if RUN_TRANSPORT_LOAD:
        load_transport()

    if RUN_LSOA_TOUCHES:
        build_lsoa_touches()

    if RUN_LSOA_GRAPH_NEAR:
        build_lsoa_graph_near()
        
    if RUN_LSOA_GEOMETRY_REPAIR:
        repair_lsoa_wkt_from_geopackage()

    if RUN_ADMIN_LSOA_INTERSECTS:
        build_admin_lsoa_intersects()

    if RUN_SCHOOL_LSOA_LINK:
        build_school_lsoa_links()

    if RUN_SCHOOL_TRANSPORT_NEAR:
        build_school_transport_near()

    if RUN_RELATION_ORIGIN_TAGGING:
        tag_existing_relation_origins()

    if RUN_UNLINKED_LSOA_DIAGNOSTICS:
        diagnose_unlinked_lsoas()

    verify()
