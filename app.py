"""
Education Inequality Analysis with a Geospatial Knowledge Graph
Task-aligned Streamlit demonstrator for the Wales YAGO2geo + LSOA project.

This app is deliberately structured around the supervisor task plan:
Task 0  Evaluation instrument
Task 1  YAGO2geo administrative hierarchy
Task 2  LSOA and statistics integration
Task 3  Policy questions mapped to SCQs
Task 4  SCQ demonstrator
Task 5  Evaluation / coverage scorecards
Task 6  Cross-hierarchy seam
Task 7  Dissertation writing (not implemented in the app)
"""

import json
from html import escape
from typing import Any, Dict, List, Tuple

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Wales Education KG — Task-Aligned Demonstrator",
    page_icon="🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem;}
.hero {
  background: linear-gradient(135deg,#003366,#0055AA,#0077CC);
  color: white; padding: 1.4rem 1.7rem; border-radius: 14px; margin-bottom: 1.1rem;
  box-shadow: 0 5px 18px rgba(0,51,102,.18);
}
.hero h1 {font-size:1.45rem; margin:0 0 .35rem 0;}
.hero p {margin:.18rem 0; opacity:.92; font-size:.88rem;}
.task-card {
  border:1px solid #dbe3ef; border-left:5px solid #0066cc; border-radius:12px;
  background:#ffffff; padding:1rem 1.05rem; margin:.55rem 0; box-shadow:0 2px 9px rgba(15,23,42,.04);
}
.task-card h3 {margin:0 0 .4rem 0; font-size:1.03rem; color:#0f172a;}
.task-key {font-weight:700; color:#003366;}
.subtask {background:#f8fafc; border-radius:9px; padding:.55rem .7rem; margin:.3rem 0; border:1px solid #e6edf5;}
.badge {display:inline-block; padding:.2rem .55rem; border-radius:999px; font-size:.78rem; font-weight:700; margin-right:.25rem;}
.done {background:#e8f7ee; color:#12672f;}
.current {background:#fff7db; color:#946200;}
.next {background:#eef2ff; color:#3730a3;}
.native {background:#e8f7ee; color:#166534;}
.geometry {background:#fff3d6; color:#b45309;}
.derived {background:#eaf2ff; color:#1d4ed8;}
.warningbox {background:#fffbe6; border-left:5px solid #f59e0b; padding:.75rem 1rem; border-radius:9px;}
.successbox {background:#ecfdf5; border-left:5px solid #10b981; padding:.75rem 1rem; border-radius:9px;}
.solutionbox {background:#eef6ff; border-left:5px solid #2563eb; padding:.85rem 1rem; border-radius:10px; margin:.7rem 0;}
.solutionbox b {color:#003366;}
.codebox {background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:.9rem; font-size:.84rem;}
.small-muted {font-size:.84rem; color:#64748b;}

/* ======================= Evaluator-ready visual system ======================= */
.visual-card {
  background:#ffffff; border:1px solid #dbe7f3; border-radius:18px;
  padding:1.05rem 1.15rem; margin:.9rem 0; box-shadow:0 10px 26px rgba(15,23,42,.06);
}
.visual-card h3 {margin:.1rem 0 .45rem 0; color:#0b2a5b; font-size:1.08rem;}
.visual-note {background:#f0f7ff; border:1px solid #bfdbfe; border-left:5px solid #2563eb; border-radius:12px; padding:.75rem .9rem; color:#17324d; margin:.6rem 0;}
.grid {display:grid; gap:.75rem;}
.grid-2 {grid-template-columns:repeat(2,minmax(0,1fr));}
.grid-3 {grid-template-columns:repeat(3,minmax(0,1fr));}
.grid-4 {grid-template-columns:repeat(4,minmax(0,1fr));}
.grid-5 {grid-template-columns:repeat(5,minmax(0,1fr));}
@media(max-width: 900px){.grid-2,.grid-3,.grid-4,.grid-5{grid-template-columns:1fr;}}
.task-step {background:linear-gradient(180deg,#ffffff,#f8fbff); border:1px solid #dbe7f3; border-radius:16px; padding:.85rem; text-align:center; min-height:118px;}
.step-num {width:44px; height:44px; border-radius:14px; margin:0 auto .45rem; display:flex; align-items:center; justify-content:center; font-weight:900; color:white; font-size:1.05rem;}
.step-blue{background:#2563eb}.step-green{background:#16a34a}.step-orange{background:#f97316}.step-purple{background:#7c3aed}.step-teal{background:#0891b2}.step-pink{background:#db2777}
.step-title2{font-weight:900;color:#0b2a5b;font-size:.9rem}.step-text{font-size:.76rem;color:#526174;line-height:1.22rem;margin-top:.25rem}
.flow-box{background:#ffffff;border:1px solid #dbe7f3;border-radius:14px;padding:.72rem;text-align:center;min-height:92px;position:relative}
.flow-box b{color:#0b2a5b}.flow-box small{color:#526174}
.flow-row{display:flex; gap:.45rem; align-items:center; justify-content:center; flex-wrap:wrap}.flow-arrow{color:#2563eb;font-weight:900;font-size:1.35rem}
.coverage-card{background:linear-gradient(180deg,#ffffff,#f7fbff);border:1px solid #dbe7f3;border-radius:16px;padding:1rem}.big-score{font-size:2.05rem;font-weight:900;color:#0b2a5b}.score-label{font-size:.82rem;color:#526174}.bar-track{height:16px;background:#e5e7eb;border-radius:999px;overflow:hidden;margin:.55rem 0}.bar-native{height:100%;width:50%;background:linear-gradient(90deg,#f59e0b,#fb923c)}.bar-demo{height:100%;width:100%;background:linear-gradient(90deg,#22c55e,#86efac)}
.scq-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:.5rem}@media(max-width:1100px){.scq-grid{grid-template-columns:repeat(4,minmax(0,1fr));}}@media(max-width:700px){.scq-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
.scq-tile{border-radius:15px;padding:.75rem .45rem;text-align:center;border:1px solid #dbe7f3;background:#fff;box-shadow:0 4px 14px rgba(15,23,42,.04)}.scq-tile h4{margin:.05rem 0;color:#0b2a5b}.scq-tile p{margin:.2rem 0;font-size:.74rem;color:#526174;line-height:1.12rem}.native-border{border-top:5px solid #16a34a}.geo-border{border-top:5px solid #f97316}.derived-border{border-top:5px solid #2563eb}.mix-border{border-top:5px solid #7c3aed}
.bridge-wrap{display:grid;grid-template-columns:1fr 130px 1fr;gap:.75rem;align-items:center}.bridge-side{border:1px solid #bfdbfe;border-radius:16px;background:#eff6ff;padding:.95rem;text-align:center}.bridge-side.right{border-color:#bbf7d0;background:#f0fdf4}.bridge-mid-light{text-align:center;color:#0b2a5b;font-weight:900}.bridge-mid-light div{background:#fff7ed;border:1px solid #fed7aa;border-radius:999px;padding:.25rem .45rem;margin:.25rem 0;color:#c2410c}
.pyramid-light{display:flex;flex-direction:column;align-items:center;gap:5px;margin:.6rem auto;max-width:520px}.pyr{height:54px;color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:900;border-radius:10px;line-height:1.1rem}.pyr small{font-weight:700;opacity:.95}.p1{width:42%;background:#22c55e}.p2{width:60%;background:#3b82f6}.p3{width:78%;background:#8b5cf6}.p4{width:96%;background:#f97316}
.final-box{background:linear-gradient(135deg,#0f766e,#16a34a);color:#fff;border-radius:18px;padding:1rem 1.1rem;margin:.8rem 0;box-shadow:0 8px 22px rgba(22,163,74,.18)}.final-box b{color:#fef9c3}.mini-legend span{display:inline-block;margin:.15rem .35rem .15rem 0;padding:.22rem .55rem;border-radius:999px;font-size:.76rem;font-weight:800}.lg-native{background:#dcfce7;color:#166534}.lg-geo{background:#ffedd5;color:#9a3412}.lg-derived{background:#dbeafe;color:#1d4ed8}.lg-missing{background:#f1f5f9;color:#475569}

/* ======================= Policy page: clean evaluator visuals ======================= */
.clean-title {font-size:1.55rem; font-weight:900; color:#0b1f49; margin:.2rem 0 .15rem;}
.clean-subtitle {font-size:.95rem; color:#334155; margin-bottom:.8rem;}
.evaluator-panel {background:#ffffff;border:1px solid #dbeafe;border-radius:20px;padding:1rem 1.15rem;margin:.85rem 0;box-shadow:0 10px 28px rgba(15,23,42,.055);}
.evaluator-panel h3 {margin:.05rem 0 .25rem;color:#0b2a5b;font-size:1.08rem;}
.path-grid {display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:.62rem;align-items:stretch;}
@media(max-width:1100px){.path-grid{grid-template-columns:repeat(3,minmax(0,1fr));}} @media(max-width:750px){.path-grid{grid-template-columns:1fr;}}
.path-step {border:1px solid #dbe7f3;border-radius:18px;background:linear-gradient(180deg,#fff,#f8fbff);padding:.85rem;text-align:center;min-height:124px;position:relative;}
.path-step:after {content:'→';position:absolute;right:-.53rem;top:45%;font-weight:900;color:#2563eb;background:#fff;border-radius:99px;padding:.05rem .2rem;}
.path-step:last-child:after {content:'';}
.path-num {width:30px;height:30px;border-radius:999px;margin:0 auto .45rem;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:.86rem;}
.path-step b {color:#0b2a5b;font-size:.88rem;display:block;}.path-step small {color:#475569;font-size:.75rem;line-height:1.08rem;display:block;margin-top:.22rem;}
.scq-principle {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin-top:.7rem;} @media(max-width:900px){.scq-principle{grid-template-columns:1fr;}}
.principle-card {border:1px solid #e2e8f0;border-radius:16px;padding:.78rem .85rem;background:#fff;min-height:110px;}
.principle-card b{display:block;color:#0b2a5b;margin-bottom:.25rem}.principle-card p{margin:0;color:#475569;font-size:.8rem;line-height:1.2rem;}
.graph-panel {display:grid;grid-template-columns:1fr 1fr 0.9fr;gap:.75rem;align-items:stretch;} @media(max-width:1100px){.graph-panel{grid-template-columns:1fr;}}
.graph-card {background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:.75rem;min-height:330px;}
.graph-card h4{margin:.2rem 0 .25rem;color:#0b2a5b}.graph-note{border-radius:13px;padding:.6rem .7rem;margin-top:.45rem;font-size:.8rem;line-height:1.2rem;}
.note-red{background:#fff1f2;border:1px solid #fecdd3;color:#7f1d1d}.note-blue{background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a}.note-green{background:#ecfdf5;border:1px solid #bbf7d0;color:#14532d}
.relation-list{display:grid;gap:.35rem;margin-top:.7rem}.relation-row{display:grid;grid-template-columns:1.5fr 60px 60px;gap:.4rem;align-items:center;border-bottom:1px solid #edf2f7;padding:.34rem 0;font-size:.82rem}.rel-line{display:inline-block;width:36px;height:4px;border-radius:99px;margin-right:.45rem}.rel-native{background:#16a34a}.rel-geo{background:#2563eb}.rel-derived{background:#f97316}.rel-missing{background:#94a3b8;border-top:2px dashed #94a3b8;height:0}.policy-table-wrap .stDataFrame{border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;}
.final-strip {background:linear-gradient(135deg,#ecfdf5,#f0f9ff);border:1px solid #bfdbfe;border-left:6px solid #10b981;border-radius:16px;padding:.9rem 1rem;margin:.85rem 0;color:#17324d;font-size:.92rem;}
.final-strip b{color:#065f46}.warning-strip{background:#fff7ed;border:1px solid #fed7aa;border-left:6px solid #f97316;border-radius:16px;padding:.82rem 1rem;margin:.75rem 0;color:#7c2d12;font-size:.9rem;}


/* ======================= Warm evaluator skin override ======================= */
.stApp {background:linear-gradient(180deg,#fffaf4 0%,#ffffff 42%,#fff7ed 100%);} 
.block-container {max-width: 1450px; padding-top: 1.25rem;}
.hero {background:linear-gradient(135deg,#2830a6,#128fd6 55%,#ff4f79); color:white; border:0; border-radius:8px; box-shadow:0 8px 20px rgba(40,48,166,.14);} 
.hero h1 {color:white;} .hero p {color:white; opacity:.94;}
div[data-testid="stSidebar"] {background:#f2f4f8; border-right:1px solid #d9dde7;}
div[data-testid="stSidebar"] button {
  border-radius:14px !important; border:1px solid #fed7aa !important;
  font-weight:800 !important; color:#431407 !important; background:#fffaf4 !important;
  min-height:2.5rem; transition:all .12s ease-in-out;
}
div[data-testid="stSidebar"] button:hover {transform:translateY(-1px); border-color:#fb923c !important; color:#9a3412 !important; box-shadow:0 5px 14px rgba(249,115,22,.12);}
div[data-testid="stSidebar"] button[kind="primary"] {background:linear-gradient(135deg,#ff4f79,#ff8a00) !important; border-color:#ff4f79 !important; color:white !important; box-shadow:0 6px 16px rgba(255,79,121,.16);} 

.nav-card{display:block;text-decoration:none;border:1px solid #fed7aa;border-radius:13px;background:#fff;padding:.58rem .65rem;margin:.35rem 0;color:#431407;font-size:.84rem;font-weight:760;box-shadow:0 4px 12px rgba(234,88,12,.045);}
.nav-card-active{background:linear-gradient(135deg,#ff4f79,#ff8a00);color:white!important;border-color:#ff4f79;box-shadow:0 7px 18px rgba(255,79,121,.16);}
.nav-card:hover{border-color:#fb923c;background:#fff7ed;}
.nav-card-active:hover{background:linear-gradient(135deg,#ff4f79,#ff8a00);}
.nav-emoji{display:inline-block;width:1.45rem;text-align:center;margin-right:.2rem;}
.stMetric {
  background:#ffffff;
  border:1px solid #e5e7eb;
  border-radius:10px;
  box-shadow:0 3px 10px rgba(15,23,42,.035);
}
.evaluator-panel,.visual-card,.graph-card,.coverage-card,.task-card {
  border-color:#e5e7eb;
  border-radius:12px;
  box-shadow:0 4px 14px rgba(15,23,42,.04);
}
.evaluator-panel h3,.graph-card h4,.visual-card h3,.clean-title {color:#7c2d12 !important;}
.task-card,.solutionbox,.warningbox,.successbox,.visual-note,.final-strip,.warning-strip {
  border-left-width:1px !important;
}
.solutionbox {background:#fff7ed; border:1px solid #e5e7eb;}
.warningbox {background:#fffbeb; border:1px solid #e5e7eb;}
.successbox {background:#f0fdf4; border:1px solid #e5e7eb;}
.final-strip {background:linear-gradient(135deg,#fff7ed,#f0fdf4); border:1px solid #e5e7eb;}
.warning-strip {background:#fff7ed; border:1px solid #e5e7eb;}

</style>
""",
    unsafe_allow_html=True,
)

DEFAULT_URI = "neo4j://127.0.0.1:7687"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "UTHT5389utht@"
DEFAULT_DATABASE = "wales-education-kg"


# =============================================================================
# TASK REGISTER: this is shown in the app, not hidden in code.
# =============================================================================
TASKS = [
    {
        "id": "Task 0",
        "title": "Evaluation Instrument",
        "keyword_sentence": "Internalise the spatial evaluation instrument: SCQ1–SCQ8, within-hierarchy vs cross-hierarchy questions, SpCom, CQCov, and graph-based proximity reasoning.",
        "subtasks": [
            ("0.1", "SCQ Framework", "Define what SCQ1–SCQ8 ask."),
            ("0.2", "Hierarchy Distinction", "Separate within-hierarchy SCQ1–SCQ6 from cross-hierarchy SCQ7–SCQ8."),
            ("0.3", "Completeness Metrics", "Use SpCom and CQCov as the evaluation vocabulary."),
            ("0.4", "Graph Proximity", "Explain near/between through traversal over touches, not raw distance."),
        ],
        "status": "Done",
    },
    {
        "id": "Task 1",
        "title": "YAGO2geo Administrative Hierarchy",
        "keyword_sentence": "Acquire YAGO2geo and confirm that the Ordnance Survey administrative hierarchy loads into Neo4j as a queryable graph.",
        "subtasks": [
            ("1.1", "YAGO2geo Acquisition", "Use the OS/YAGO2geo administrative files as the model baseline."),
            ("1.2", "Administrative Hierarchy", "Represent Unitary Authority, Ward, and Community as AdminUnit nodes."),
            ("1.3", "Native Topology", "Preserve native WITHIN and TOUCHES relations for model-level coverage."),
            ("1.4", "Neo4j Confirmation", "Expose node and relationship counts in the app for verification."),
        ],
        "status": "Done",
    },
    {
        "id": "Task 2",
        "title": "LSOA and Statistics Integration",
        "keyword_sentence": "Integrate statistical geography and education-inequality data by adding LSOA, WIMD, schools, FSM, and transport access to the graph.",
        "subtasks": [
            ("2.1", "LSOA Statistical Geography", "Add LSOA as the ONS statistical hierarchy absent from YAGO2geo."),
            ("2.2", "WIMD Attachment", "Attach deprivation rank/decile/category to LSOA."),
            ("2.3", "School Integration", "Load schools and connect each school to an LSOA."),
            ("2.4", "FSM Integration", "Attach verified FSM values to schools when available."),
            ("2.5", "Transport Access", "Represent school proximity to transport stops using DISTANCE_NEAR."),
            ("2.6", "Provenance Labelling", "Record Native, Geometry-origin, or Derived origin for relationships."),
        ],
        "status": "Closed in artifact",
    },
    {
        "id": "Task 3",
        "title": "Policy Questions mapped to SCQs",
        "keyword_sentence": "Translate education-policy questions into the standard SCQ forms so the use case is evaluated with the same instrument as the paper.",
        "subtasks": [
            ("3.1", "Policy Question Library", "Keep real policy-style questions visible and traceable."),
            ("3.2", "SCQ Mapping", "Map each policy question to SCQ1–SCQ8."),
            ("3.3", "No Forced Fit", "Mark SCQ3 as weak/optional for this use case rather than manufacturing evidence."),
            ("3.4", "Reclassification", "Move Ward–LSOA containment-style questions away from SCQ5/SCQ6 into SCQ7/SCQ8."),
        ],
        "status": "Closed in artifact",
    },
    {
        "id": "Task 4",
        "title": "SCQ Demonstrator",
        "keyword_sentence": "Build a demonstrator that answers SCQ1–SCQ8 over the integrated Neo4j graph and shows Cypher, results, and provenance for each answer.",
        "subtasks": [
            ("4.1", "SCQ Query Runner", "Run SCQ1–SCQ8 from the interface."),
            ("4.2", "Cypher Transparency", "Display the executed query and parameters."),
            ("4.3", "Result Evidence", "Show returned rows and counts."),
            ("4.4", "Provenance Panel", "Show Native, Geometry-origin, or Derived for the relation used."),
            ("4.5", "Map Support", "Keep only a lightweight map that supports the demonstrator."),
        ],
        "status": "Closed in artifact",
    },
    {
        "id": "Task 5",
        "title": "Evaluation and Coverage",
        "keyword_sentence": "Evaluate model coverage separately from geometry-assisted demonstrator coverage using one consistent eight-SCQ scorecard.",
        "subtasks": [
            ("5.1", "Native Model Coverage", "Score YAGO2geo only on what it natively asserts or derives from native relations."),
            ("5.2", "Demonstrator Coverage", "Report what the app can answer using computed geometry and traversal."),
            ("5.3", "SpCom/CQCov Consistency", "Use one scorecard over all eight SCQs."),
            ("5.4", "Geometry Attribution", "Do not count geometry-origin relations as model completeness."),
            ("5.5", "Compute-once Reasoning", "Compare geometry-on-demand with compute-once-then-reason."),
        ],
        "status": "Closed in artifact",
    },
    {
        "id": "Task 6",
        "title": "Cross-hierarchy Seam",
        "keyword_sentence": "Evaluate the seam between the administrative hierarchy and statistical hierarchy, especially Ward/Community/AdminUnit ↔ LSOA intersect and near relations.",
        "subtasks": [
            ("6.1", "Administrative ↔ Statistical Seam", "Use INTERSECTS to relate AdminUnit and LSOA."),
            ("6.2", "Cross-hierarchy Intersect", "Answer SCQ7 as geometry-origin spatial join."),
            ("6.3", "Cross-hierarchy Near", "Answer SCQ8 as geometry-origin plus derived traversal."),
            ("6.4", "Finding not Gap", "Report missing native seam as the research finding, not as a defect to hide."),
        ],
        "status": "Closed in artifact",
    },
    {
        "id": "Task 7",
        "title": "Dissertation Writing",
        "keyword_sentence": "Write the methodology, implementation, evaluation, and findings in your own words after the demonstrator tasks are closed.",
        "subtasks": [
            ("7.1", "Methodology", "Explain data, modelling, provenance, and query design."),
            ("7.2", "Evaluation", "Write model vs demonstrator coverage findings."),
            ("7.3", "Related Work", "Expand policy and literature question evidence."),
        ],
        "status": "Next / Not in app scope",
    },
]


TASK_SOLUTIONS = {
    "Task 0": {
        "answer": "The evaluation instrument is operationalised through SCQ1–SCQ8, SpCom/CQCov vocabulary, and explicit provenance categories.",
        "evidence": "SCQ Demonstrator + Evaluation scorecards",
        "app_section": "Evaluation / SCQ Demonstrator",
    },
    "Task 1": {
        "answer": "YAGO2geo's OS administrative hierarchy is loaded as AdminUnit nodes with native WITHIN and TOUCHES relations preserved for model-level coverage.",
        "evidence": "AdminUnit, WITHIN and TOUCHES counts",
        "app_section": "Task Overview / Evaluation",
    },
    "Task 2": {
        "answer": "LSOA, WIMD, schools, FSM and transport access are integrated into the graph and connected through LOCATED_IN and DISTANCE_NEAR where appropriate.",
        "evidence": "LSOA, School, TransportStop, LOCATED_IN and DISTANCE_NEAR counts",
        "app_section": "Task Overview / Map",
    },
    "Task 3": {
        "answer": "Policy-style education questions are mapped to SCQ forms; SCQ3 is marked as weak/optional and Ward–LSOA containment is reclassified to SCQ7/SCQ8.",
        "evidence": "Policy question library with SCQ, relation and provenance columns",
        "app_section": "Policy Questions",
    },
    "Task 4": {
        "answer": "The demonstrator runs SCQ1–SCQ8, displays Cypher and parameters, returns result rows, and states relation provenance for every answer.",
        "evidence": "Live SCQ query runner",
        "app_section": "SCQ Demonstrator",
    },
    "Task 5": {
        "answer": "The app separates native model coverage from geometry-assisted demonstrator coverage and keeps geometry-origin relations out of the model score.",
        "evidence": "Native model table, SCQ scorecard, demonstrator coverage, compute-once comparison",
        "app_section": "Evaluation",
    },
    "Task 6": {
        "answer": "The administrative–statistical seam is evaluated through INTERSECTS and GRAPH_NEAR; SCQ7 and SCQ8 are answerable in the demonstrator but not native YAGO2geo coverage.",
        "evidence": "INTERSECTS, GRAPH_NEAR and LOCATED_IN counts plus sample SCQ7/SCQ8 answers",
        "app_section": "Cross-hierarchy",
    },
    "Task 7": {
        "answer": "Deferred: writing starts after the artifact is closed.",
        "evidence": "Not implemented in the app",
        "app_section": "Dissertation document",
    },
}

# =============================================================================
# SCQ QUERY DEFINITIONS — supervisor-aligned implementation notes
# =============================================================================
# 1. SCQ1, SCQ2, SCQ4, SCQ7, and SCQ8 expose scraped school metrics
#    (FSM, attendance, and secondary performance where available). This makes
#    the demonstrator visibly education-policy oriented rather than purely
#    topological.
# 2. Secondary performance fields are intentionally nullable because the
#    My Local School scrape provides capped/literacy/numeracy/science scores
#    for secondary or middle schools, not for ordinary primary schools.
# 3. SCQ3 is implemented as bounded simple-path reasoning over LSOA_TOUCHES.
#    The app does not define "between" as shortest path only.
# 4. SCQ5 and SCQ6 remain native administrative-hierarchy comparisons only.
#    They are not counted as independent Education Use Case answers because
#    Ward-LSOA containment-style questions were reclassified to SCQ7/SCQ8.
SCQ_META = {
    "SCQ1": {
        "label": "SCQ1 — LSOA borders / touches",
        "question": (
            "Which neighbouring LSOAs directly border the selected LSOA, "
            "and what school FSM / attendance / performance evidence is "
            "visible in those neighbouring areas?"
        ),
        "task": "Task 4.1 + Task 5.4",
        "keyword_sentence": (
            "The demonstrator answers LSOA adjacency using the computed "
            "LSOA_TOUCHES relation. This is Geometry-origin capability and "
            "does not count as native YAGO2geo model completeness."
        ),
        "relation": "LSOA_TOUCHES",
        "provenance": "Geometry-origin",
        "param_type": "lsoa_touch",
        "result_label": "Bordering LSOAs found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": """
MATCH (x:LSOA {code:$lsoa})-[:LSOA_TOUCHES]-(y:LSOA)
OPTIONAL MATCH (y)<-[:LOCATED_IN]-(s:School)
WITH
    y,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score,
    count(CASE WHEN s.capped9_score IS NOT NULL THEN s END)
        AS secondary_performance_school_count
RETURN DISTINCT
    y.code AS lsoa_code,
    coalesce(y.name, y.LSOA_Name, y.code) AS lsoa_name,
    y.wimd_decile AS wimd_decile,
    y.deprivation AS deprivation,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score,
    secondary_performance_school_count
ORDER BY avg_school_fsm_pct DESC, lsoa_code
LIMIT $limit
""",
    },

    "SCQ2": {
        "label": "SCQ2 — LSOA near",
        "question": (
            "Which LSOAs are qualitatively near the selected LSOA, "
            "and do nearby school indicators show FSM / attendance / "
            "secondary-performance pressure?"
        ),
        "task": "Task 4.1 + Task 5.4",
        "keyword_sentence": (
            "Near is represented by GRAPH_NEAR, which is derived through "
            "graph traversal over the computed LSOA neighbourhood. It is "
            "qualitative graph proximity, not a raw distance threshold."
        ),
        "relation": "GRAPH_NEAR",
        "provenance": "Derived from geometry-origin",
        "param_type": "lsoa_near",
        "result_label": "Nearby LSOAs found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": """
MATCH (x:LSOA {code:$lsoa})-[:GRAPH_NEAR]-(y:LSOA)
OPTIONAL MATCH (y)<-[:LOCATED_IN]-(s:School)
WITH
    y,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score,
    count(CASE WHEN s.capped9_score IS NOT NULL THEN s END)
        AS secondary_performance_school_count
RETURN DISTINCT
    y.code AS lsoa_code,
    coalesce(y.name, y.LSOA_Name, y.code) AS lsoa_name,
    y.wimd_decile AS wimd_decile,
    y.deprivation AS deprivation,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score,
    secondary_performance_school_count
ORDER BY avg_school_fsm_pct DESC, lsoa_code
LIMIT $limit
""",
    },

    "SCQ3": {
        "label": "SCQ3 — LSOA between",
        "question": "Which LSOAs lie between two selected LSOAs?",
        "task": "Task 4.1 + Task 3.3",
        "keyword_sentence": (
            "Between is demonstrated as bounded simple-path reasoning "
            "over LSOA_TOUCHES. The app returns candidate paths rather "
            "than defining between as only the shortest path. Its "
            "education-policy fit is reported as weak or optional unless "
            "clusters are formally defined."
        ),
        "relation": "LSOA_TOUCHES path",
        "provenance": "Derived from geometry-origin",
        "param_type": "lsoa_pair",
        "result_label": "Candidate between paths returned",
        "evaluation_note": (
            "Demonstrator reasoning pattern: Implemented. "
            "Education-policy fit: Weak / optional."
        ),
        "cypher": """
MATCH
    (a:LSOA {code:$lsoa_a}),
    (b:LSOA {code:$lsoa_b})

MATCH p = (a)-[:LSOA_TOUCHES*2..6]-(b)

WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))

RETURN
    length(p) AS hops,
    [
        n IN nodes(p)[1..-1] |
        {
            code: n.code,
            name: coalesce(
                n.name,
                n.LSOA_Name,
                n.code
            ),
            deprivation: n.deprivation,
            wimd_decile: n.wimd_decile
        }
    ] AS between_lsoas
ORDER BY hops
LIMIT $limit
""",
    },

    "SCQ4": {
        "label": "SCQ4 — LSOA not-adjacent",
        "question": (
            "Which non-adjacent LSOAs show school FSM / attendance / "
            "secondary-performance pressure compared with the selected "
            "LSOA?"
        ),
        "task": "Task 4.1 + Task 5.3",
        "keyword_sentence": (
            "Not-adjacent is evaluated as the complement of the computed "
            "LSOA_TOUCHES relation. Its provenance therefore remains "
            "Derived from geometry-origin."
        ),
        "relation": "NOT LSOA_TOUCHES",
        "provenance": "Derived from geometry-origin",
        "param_type": "lsoa_any",
        "result_label": "Non-adjacent LSOAs found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": """
MATCH (x:LSOA {code:$lsoa})
MATCH (y:LSOA)

WHERE y.code <> x.code
  AND NOT (x)-[:LSOA_TOUCHES]-(y)

OPTIONAL MATCH (y)<-[:LOCATED_IN]-(s:School)
WITH
    y,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score,
    count(CASE WHEN s.capped9_score IS NOT NULL THEN s END)
        AS secondary_performance_school_count
RETURN
    y.code AS lsoa_code,
    coalesce(y.name, y.LSOA_Name, y.code) AS lsoa_name,
    y.wimd_decile AS wimd_decile,
    y.deprivation AS deprivation,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score,
    secondary_performance_school_count
ORDER BY avg_school_fsm_pct DESC, lsoa_code
LIMIT $limit
""",
    },

    "SCQ5": {
        "label": "SCQ5 — Administrative contains",
        "question": (
            "Which administrative parent units contain the selected "
            "administrative unit?"
        ),
        "task": "Task 1.3 + Task 5.1",
        "keyword_sentence": (
            "This query demonstrates the SCQ5 form within the native "
            "administrative hierarchy by traversing WITHIN upward. "
            "For the LSOA-based education use case, containment is "
            "reclassified to the cross-hierarchy evaluation."
        ),
        "relation": "WITHIN upward traversal",
        "provenance": "Native",
        "param_type": "admin_child",
        "result_label": "Containing administrative units found",
        "evaluation_note": (
            "Native administrative comparison: Yes. "
            "Education-use-case scorecard: Reclassified / n/a."
        ),
        "cypher": """
MATCH (child:AdminUnit)
WHERE child.uri = $admin

MATCH (child)-[:WITHIN*1..3]->(parent:AdminUnit)

RETURN DISTINCT
    coalesce(parent.name, parent.uri) AS containing_unit,
    parent.type AS administrative_type,
    parent.uri AS uri
ORDER BY containing_unit
LIMIT $limit
""",
    },

    "SCQ6": {
        "label": "SCQ6 — Administrative inside",
        "question": (
            "Which administrative units are contained inside the selected "
            "administrative unit?"
        ),
        "task": "Task 1.3 + Task 5.1",
        "keyword_sentence": (
            "This query demonstrates the SCQ6 form within the native "
            "administrative hierarchy by traversing WITHIN downward. "
            "It must not be presented as Ward–LSOA containment."
        ),
        "relation": "WITHIN downward traversal",
        "provenance": "Native",
        "param_type": "admin_parent",
        "result_label": "Contained administrative units found",
        "evaluation_note": (
            "Native administrative comparison: Yes. "
            "Education-use-case scorecard: Reclassified / n/a."
        ),
        "cypher": """
MATCH (parent:AdminUnit)
WHERE parent.uri = $admin

MATCH (child:AdminUnit)-[:WITHIN*1..3]->(parent)

RETURN DISTINCT
    coalesce(child.name, child.uri) AS contained_unit,
    child.type AS administrative_type,
    child.uri AS uri
ORDER BY contained_unit
LIMIT $limit
""",
    },

    "SCQ7": {
        "label": "SCQ7 — Cross-hierarchy intersects",
        "question": (
            "Which wards or communities intersect the selected LSOA, "
            "and what school FSM / attendance / performance evidence is "
            "located in that LSOA?"
        ),
        "task": "Task 6.2 + Task 5.4",
        "keyword_sentence": (
            "SCQ7 is the correct reclassification target for Ward–LSOA "
            "containment-style questions. The relation crosses from the "
            "administrative hierarchy to statistical geography using "
            "computed INTERSECTS, so it is Geometry-origin rather than "
            "Native YAGO2geo coverage."
        ),
        "relation": "INTERSECTS",
        "provenance": "Geometry-origin",
        "param_type": "lsoa_intersects",
        "result_label": "Intersecting administrative units found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": """
MATCH (x:LSOA {code:$lsoa})
MATCH (admin:AdminUnit)-[:INTERSECTS]->(x)
WHERE admin.type IN ['Ward', 'Community']
OPTIONAL MATCH (x)<-[:LOCATED_IN]-(s:School)
WITH
    x,
    admin,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score,
    count(CASE WHEN s.capped9_score IS NOT NULL THEN s END)
        AS secondary_performance_school_count
RETURN DISTINCT
    coalesce(admin.name, admin.uri) AS administrative_unit,
    admin.type AS administrative_type,
    x.code AS lsoa_code,
    coalesce(x.name, x.LSOA_Name, x.code) AS lsoa_name,
    x.wimd_decile AS wimd_decile,
    x.deprivation AS deprivation,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score,
    secondary_performance_school_count
ORDER BY administrative_type, administrative_unit
LIMIT $limit
""",
    },

    "SCQ8": {
        "label": "SCQ8 — Cross-hierarchy near",
        "question": (
            "Which wards or communities intersect LSOAs that are graph-near "
            "the selected LSOA, and what school indicators are visible in "
            "those nearby LSOAs?"
        ),
        "task": "Task 6.3 + Task 5.4",
        "keyword_sentence": (
            "SCQ8 combines GRAPH_NEAR between LSOAs with INTERSECTS from "
            "nearby LSOAs to wards or communities. It is useful for the "
            "education demonstrator, but its provenance remains "
            "Geometry-origin plus Derived."
        ),
        "relation": "INTERSECTS + GRAPH_NEAR",
        "provenance": "Geometry-origin + Derived",
        "param_type": "lsoa_near_intersects",
        "result_label": "Nearby cross-hierarchy units found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": """
MATCH (x:LSOA {code:$lsoa})-[:GRAPH_NEAR]-(near_lsoa:LSOA)
MATCH (admin:AdminUnit)-[:INTERSECTS]->(near_lsoa)
WHERE admin.type IN ['Ward', 'Community']
OPTIONAL MATCH (near_lsoa)<-[:LOCATED_IN]-(s:School)
WITH
    near_lsoa,
    admin,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score,
    count(CASE WHEN s.capped9_score IS NOT NULL THEN s END)
        AS secondary_performance_school_count
RETURN DISTINCT
    coalesce(admin.name, admin.uri) AS administrative_unit,
    admin.type AS administrative_type,
    near_lsoa.code AS nearby_lsoa_code,
    coalesce(near_lsoa.name, near_lsoa.LSOA_Name, near_lsoa.code)
        AS nearby_lsoa_name,
    near_lsoa.wimd_decile AS nearby_wimd_decile,
    near_lsoa.deprivation AS nearby_deprivation,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score,
    secondary_performance_school_count
ORDER BY avg_school_fsm_pct DESC, administrative_type, administrative_unit
LIMIT $limit
""",
    },
}

# Policy mapping table shown on the Policy Questions page.
# The wording is deliberately conservative:
# - school metrics strengthen the education use case;
# - SCQ3 remains weak/optional unless clusters are formally defined;
# - SCQ5/SCQ6 are retained as administrative comparisons, not education rows.
POLICY_LIBRARY = [
    ["SCQ1", "Which LSOAs with visible school pressure border the selected LSOA?", "Use LSOA_TOUCHES and show school FSM, attendance, and secondary performance indicators for neighbouring LSOAs.", "Task 3.2 + Task 4.1", "LSOA_TOUCHES + School metrics", "Geometry-origin"],
    ["SCQ2", "Which graph-near LSOAs show school pressure?", "Use GRAPH_NEAR as qualitative proximity and summarise school FSM, attendance, and secondary performance indicators.", "Task 3.2 + Task 4.1", "GRAPH_NEAR + School metrics", "Derived from geometry-origin"],
    ["SCQ3", "Which LSOAs lie between two selected LSOAs?", "Use bounded simple paths over LSOA_TOUCHES; label the education-policy fit as weak/optional unless clusters are formally defined.", "Task 3.3 + Task 4.1", "LSOA_TOUCHES bounded paths", "Derived from geometry-origin"],
    ["SCQ4", "Which non-adjacent LSOAs show school pressure?", "Use the complement of LSOA_TOUCHES and rank/display school FSM, attendance, and secondary performance indicators.", "Task 5.3 + Task 4.1", "NOT LSOA_TOUCHES + School metrics", "Derived from geometry-origin"],
    ["SCQ5", "Which administrative parent contains this ward/community?", "Use native WITHIN upward traversal inside the administrative hierarchy.", "Task 1.3 + Task 5.1", "WITHIN inverse", "Native"],
    ["SCQ6", "Which wards/communities are contained in this authority?", "Use native WITHIN downward traversal inside the administrative hierarchy only.", "Task 1.3 + Task 5.1", "WITHIN", "Native"],
    ["SCQ7", "Which wards or communities intersect LSOAs with school pressure?", "Use stored spatial-join INTERSECTS and display school metrics from the intersected LSOA.", "Task 6.2 + Task 5.4", "INTERSECTS + School metrics", "Geometry-origin"],
    ["SCQ8", "Which wards or communities are near LSOAs with school pressure?", "Combine GRAPH_NEAR with INTERSECTS and display school metrics from nearby LSOAs.", "Task 6.3 + Task 5.4", "INTERSECTS + GRAPH_NEAR + School metrics", "Geometry-origin + Derived"],
    ["School query", "Which schools with high FSM are located in highly deprived LSOAs?", "Use School–LOCATED_IN–LSOA and verified FSM properties where available.", "Task 2.3 + Task 2.4", "LOCATED_IN", "Geometry-origin"],
    ["School query", "Which schools in high deprivation are far from public transport?", "Use absence of DISTANCE_NEAR after School–LSOA deprivation filtering.", "Task 2.5", "DISTANCE_NEAR absence", "Geometry-origin"],
]

# Native model completeness table.
# This table evaluates what the original YAGO2geo-style administrative model
# can represent natively or by traversal over native administrative relations.
MODEL_COMPLETENESS = pd.DataFrame([
    ["Ward", "Ward", "Touches, near/far/between", "TOUCHES native; near/far/between by traversal", "Complete (model)"],
    ["Community", "Community", "Touches, near/far/between", "TOUCHES native; rest by traversal", "Complete (model)"],
    ["Unitary Authority", "Ward", "Contains, inside", "WITHIN native; contains by inverse", "Complete (model)"],
    ["LSOA", "LSOA", "Touches, near, far, between", "None native in YAGO2geo", "Missing — report"],
    ["Ward", "LSOA", "Intersect, near", "None native in YAGO2geo", "Missing — report"],
    ["Community", "LSOA", "Intersect, near", "None native in YAGO2geo", "Missing — report"],
], columns=["Domain", "Range", "Relations needed", "Native or derivable from native", "Status"])

# Education Use Case scorecard.
# "No" here does not mean the app cannot answer the question; it means the
# original native model does not contain the required LSOA or cross-hierarchy
# relation. Geometry-origin and derived answers are reported separately.
SCQ_SCORECARD = pd.DataFrame([
    ["SCQ1", "LSOA borders LSOA", "No", "Geometry: computed LSOA_TOUCHES", "No"],
    ["SCQ2", "LSOA near a cluster", "No", "Traversal over computed LSOA_TOUCHES / GRAPH_NEAR", "No"],
    ["SCQ3", "LSOA between clusters", "No", "Path query over computed LSOA_TOUCHES", "No"],
    ["SCQ4", "LSOA not-adjacent", "No", "Complement of computed LSOA_TOUCHES", "No"],
    ["SCQ5", "Reclassified for Ward–LSOA", "n/a", "Use only for administrative hierarchy", "n/a"],
    ["SCQ6", "Reclassified for Ward–LSOA", "n/a", "Use only for administrative hierarchy", "n/a"],
    ["SCQ7", "Ward/Community intersects LSOA", "No", "Geometry: spatial join INTERSECTS", "No"],
    ["SCQ8", "Ward/Community near LSOA", "No", "Geometry-origin + traversal", "No"],
], columns=["SCQ", "Education-use-case question", "Native model answer?", "How the demonstrator answers", "Counts toward model completeness"])

# Demonstrator coverage table.
# This records what the Streamlit/Neo4j artifact can execute after the project
# has added computed LSOA, INTERSECTS, GRAPH_NEAR, and school metric evidence.
DEMO_COVERAGE = pd.DataFrame([
    ["SCQ1", "Yes", "LSOA_TOUCHES", "Geometry-origin"],
    ["SCQ2", "Yes", "GRAPH_NEAR", "Derived from geometry-origin"],
    ["SCQ3", "Yes if path exists", "LSOA_TOUCHES path", "Derived from geometry-origin"],
    ["SCQ4", "Yes", "NOT LSOA_TOUCHES", "Derived from geometry-origin"],
    ["SCQ5", "Yes for administrative hierarchy only", "WITHIN inverse", "Native"],
    ["SCQ6", "Yes for administrative hierarchy only", "WITHIN", "Native"],
    ["SCQ7", "Yes", "INTERSECTS", "Geometry-origin"],
    ["SCQ8", "Yes", "INTERSECTS + GRAPH_NEAR", "Geometry-origin + Derived"],
], columns=["SCQ", "Demonstrator answer?", "Relation/query", "Provenance"])


# =============================================================================
# NEO4J HELPERS
# =============================================================================
def sidebar_config() -> Dict[str, str]:
    # Connection is fixed in the code to keep the evaluator-facing UI clean.
    cfg = {
        "uri": DEFAULT_URI,
        "user": DEFAULT_USER,
        "password": DEFAULT_PASSWORD,
        "database": DEFAULT_DATABASE,
    }

    st.sidebar.markdown("""
    <div style="padding:.35rem 0 .9rem 0;">
      <div style="font-size:1.3rem;font-weight:900;color:#7c2d12;line-height:1.15;">Wales Education KG</div>
      <div style="font-size:.82rem;color:#64748b;margin-top:.25rem;">Task-aligned demonstrator</div>
    </div>
    """, unsafe_allow_html=True)
    cfg["dark_theme"] = st.sidebar.toggle(
        "Dark theme",
        value=st.session_state.get("dark_theme", False),
        help="Switch the dashboard background and map tiles between light and deep-blue themes.",
    )
    st.session_state.dark_theme = cfg["dark_theme"]

    try:
        # Lightweight connection status; no URI/user/password shown to the examiner.
        _ = scalar(cfg, "RETURN 1", default=1)
        st.sidebar.markdown("""
        <div class="side-card">
          <div class="side-title">System status</div>
          <div class="side-ok">● Neo4j connected</div>
          <div class="side-muted">wales-education-kg</div>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.sidebar.markdown("""
        <div class="side-card">
          <div class="side-title">System status</div>
          <div class="side-alert">● Neo4j not connected</div>
        </div>
        """, unsafe_allow_html=True)

    pages = ["Task Overview", "Visual Story", "Policy Questions", "SCQ Demonstrator", "Evaluation", "Cross-hierarchy", "Map"]
    labels = {
        "Task Overview": "Overview",
        "Visual Story": "Visual Story",
        "Policy Questions": "Policy Questions",
        "SCQ Demonstrator": "SCQ Demonstrator",
        "Evaluation": "Evaluation",
        "Cross-hierarchy": "Cross-hierarchy",
        "Map": "Map Explorer",
    }
    icons = {
        "Task Overview": "Overview",
        "Visual Story": "Visual Story",
        "Policy Questions": "Policy Questions",
        "SCQ Demonstrator": "SCQ Demonstrator",
        "Evaluation": "Evaluation",
        "Cross-hierarchy": "Cross-hierarchy",
        "Map": "Map Explorer",
    }
    if "page" not in st.session_state:
        st.session_state.page = "Task Overview"

    def _set_page(page_name: str) -> None:
        st.session_state.page = page_name

    st.sidebar.markdown("<div style='font-size:.78rem;color:#9a3412;font-weight:800;margin:.9rem 0 .35rem;'>NAVIGATION</div>", unsafe_allow_html=True)
    for p in pages:
        active = st.session_state.page == p
        label = icons[p]
        # one click only: the callback updates session state before the rerun
        st.sidebar.button(label, key=f"nav_{p}", type="primary" if active else "secondary", use_container_width=True, on_click=_set_page, args=(p,))
    st.sidebar.divider()

    try:
        counts = cached_counts(cfg["uri"], cfg["user"], cfg["password"], cfg["database"])
        st.sidebar.markdown("<div style='font-size:.78rem;color:#9a3412;font-weight:800;margin:.2rem 0 .35rem;'>GRAPH SUMMARY</div>", unsafe_allow_html=True)
        for name in ["AdminUnit", "LSOA", "School", "TransportStop"]:
            st.sidebar.markdown(f"<div style='display:flex;justify-content:space-between;font-size:.82rem;margin:.28rem 0;'><span>{name}</span><b>{counts.get(name,0):,}</b></div>", unsafe_allow_html=True)
    except Exception:
        pass

    st.sidebar.markdown("""
    <div class="side-card">
      <div class="side-title">Evaluation principle</div>
      <div class="side-copy"><b class="native-word">Native</b> counts toward model completeness.<br>
      <b class="geo-word">Geometry-origin</b> supports demonstrator capability.<br>
      <b class="derived-word">Derived</b> depends on its origin.</div>
    </div>
    """, unsafe_allow_html=True)
    cfg["page"] = st.session_state.page
    return cfg


def apply_dashboard_theme(dark_theme: bool) -> None:
    """Apply a compact infographic-inspired light/dark skin."""
    if dark_theme:
        app_bg = "linear-gradient(180deg,#11166f 0%,#2025a8 48%,#17228f 100%)"
        sidebar_bg = "linear-gradient(180deg,#12186f 0%,#1c2497 100%)"
        panel_bg = "rgba(255,255,255,.08)"
        panel_border = "rgba(255,255,255,.14)"
        text = "#f8fafc"
        muted = "#dbeafe"
        sidebar_text = "#f8fafc"
        metric_bg = "rgba(255,255,255,.10)"
        hero = "linear-gradient(135deg,#ff4f79 0%,#ff4f79 54%,#20c6d7 54%,#20c6d7 100%)"
        nav_bg = "rgba(255,255,255,.10)"
        nav_active = "linear-gradient(135deg,#ff4f79,#ff8a00)"
        map_tiles = "dark"
        ok_color = "#86efac"
        geo_color = "#ffb454"
        derived_color = "#c4b5fd"
    else:
        app_bg = "linear-gradient(180deg,#ffffff 0%,#f8fbff 48%,#ffffff 100%)"
        sidebar_bg = "#f2f4f8"
        panel_bg = "#ffffff"
        panel_border = "#e5e7eb"
        text = "#303443"
        muted = "#596273"
        sidebar_text = "#303443"
        metric_bg = "#ffffff"
        hero = "linear-gradient(135deg,#ff4f79 0%,#ff4f79 54%,#20c6d7 54%,#20c6d7 100%)"
        nav_bg = "#ffffff"
        nav_active = "linear-gradient(135deg,#ff4f79,#ff8a00)"
        map_tiles = "light"
        ok_color = "#15803d"
        geo_color = "#ea580c"
        derived_color = "#7c3aed"

    st.session_state.map_tiles = map_tiles
    st.markdown(
        f"""
<style>
.stApp {{ background:{app_bg} !important; color:{text} !important; }}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
div[data-testid="stSidebar"] {{
  background:{sidebar_bg} !important;
  border-right:1px solid {panel_border} !important;
}}
section[data-testid="stSidebar"] *::-webkit-scrollbar {{
  width:10px;
}}
section[data-testid="stSidebar"] *::-webkit-scrollbar-track {{
  background:rgba(255,255,255,.08);
}}
section[data-testid="stSidebar"] *::-webkit-scrollbar-thumb {{
  background:rgba(255,255,255,.36);
  border-radius:999px;
}}
section[data-testid="stSidebar"] [data-testid="collapsedControl"],
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {{
  color:{sidebar_text} !important;
}}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] *,
div[data-testid="stSidebar"],
div[data-testid="stSidebar"] * {{
  color:{sidebar_text} !important;
}}
.hero {{
  background:{hero} !important;
  color:white !important;
  border:0 !important;
  border-radius:6px !important;
  box-shadow:0 8px 18px rgba(17,24,39,.10) !important;
}}
.hero h1,.hero p {{ color:white !important; }}
.stMetric {{
  background:{metric_bg} !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  box-shadow:none !important;
}}
.stMetric label,.stMetric [data-testid="stMetricLabel"] {{
  color:{muted} !important;
}}
.stMetric [data-testid="stMetricValue"] {{
  color:{text} !important;
}}
.task-card,.visual-card,.evaluator-panel,.graph-card,.coverage-card,
.solutionbox,.warningbox,.successbox,.final-strip,.warning-strip,
.subtask,.visual-note,.bridge-side,.bridge-mid-light div,.side-card {{
  background:{panel_bg} !important;
  border:1px solid {panel_border} !important;
  border-left-width:1px !important;
  border-radius:6px !important;
  box-shadow:none !important;
  color:{text} !important;
}}
.task-step,.path-step,.principle-card,.scq-tile,.flow-box {{
  background:{panel_bg} !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  color:{text} !important;
  box-shadow:none !important;
}}
.task-card h3,.visual-card h3,.evaluator-panel h3,.graph-card h4,
.clean-title,.solutionbox b,.task-key,.step-title2,.path-step b,
.principle-card b,.scq-tile h4,.flow-box b,.bridge-side b,
.bridge-mid-light,.big-score,.final-box b,.side-title {{ color:{text} !important; }}
.small-muted,.step-text,.clean-subtitle,.path-step small,
.principle-card p,.scq-tile p,.flow-box small,.score-label,
.bridge-side span,.visual-note,.subtask,.side-copy,.side-muted {{
  color:{muted} !important;
}}
.side-card {{
  padding:.75rem .85rem !important;
  margin:.55rem 0 1rem 0 !important;
}}
.side-title {{
  font-weight:900 !important;
  margin-bottom:.45rem !important;
}}
.side-ok,.native-word {{
  color:{ok_color} !important;
  font-weight:800 !important;
}}
.side-alert {{
  color:#fecdd3 !important;
  font-weight:800 !important;
}}
.geo-word {{
  color:{geo_color} !important;
  font-weight:800 !important;
}}
.derived-word {{
  color:{derived_color} !important;
  font-weight:800 !important;
}}
.side-copy {{
  font-size:.78rem !important;
  line-height:1.35rem !important;
}}
.bar-track {{
  background:rgba(255,255,255,.22) !important;
}}
.final-box {{
  background:linear-gradient(135deg,#0f9f8f,#13a85f) !important;
  border-radius:6px !important;
  color:white !important;
}}
.nav-card {{
  background:{nav_bg} !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  box-shadow:none !important;
  color:{text} !important;
}}
.nav-card-active {{
  background:{nav_active} !important;
  border-color:transparent !important;
  color:white !important;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] span {{
  color:{sidebar_text} !important;
}}
section[data-testid="stSidebar"] button,
div[data-testid="stSidebar"] button {{
  background:{nav_bg} !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  color:{sidebar_text} !important;
  box-shadow:none !important;
}}
section[data-testid="stSidebar"] button[kind="primary"],
div[data-testid="stSidebar"] button[kind="primary"] {{
  background:{nav_active} !important;
  border-color:transparent !important;
  color:white !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] input,
div[data-testid="stSidebar"] div[data-baseweb="select"] > div,
div[data-testid="stSidebar"] input {{
  background:rgba(255,255,255,.94) !important;
  border-color:transparent !important;
  color:#303443 !important;
  border-radius:6px !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] *,
div[data-testid="stSidebar"] div[data-baseweb="select"] * {{
  color:#303443 !important;
}}
div[data-testid="stButton"] button[kind="secondary"] {{
  background:{panel_bg} !important;
  border:1px solid {panel_border} !important;
  color:{text} !important;
  border-radius:6px !important;
  box-shadow:none !important;
}}
div[data-testid="stButton"] button[kind="secondary"]:hover {{
  border-color:#20c6d7 !important;
  color:{text} !important;
}}
div[data-testid="stButton"] button[kind="primary"] {{
  background:{nav_active} !important;
  border-color:transparent !important;
  color:white !important;
  border-radius:6px !important;
}}
.result-table-wrap {{
  overflow:auto !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  background:{panel_bg} !important;
  margin:.55rem 0 1rem 0 !important;
}}
.result-table-wrap table {{
  width:100% !important;
  border-collapse:collapse !important;
  font-size:.78rem !important;
  color:{text} !important;
}}
.result-table-wrap th {{
  background:rgba(255,255,255,.12) !important;
  color:{text} !important;
  font-weight:800 !important;
  text-align:left !important;
  padding:.48rem .55rem !important;
  border-bottom:1px solid {panel_border} !important;
}}
.result-table-wrap td {{
  padding:.42rem .55rem !important;
  border-bottom:1px solid {panel_border} !important;
  color:{text} !important;
}}
div[data-testid="stCodeBlock"] pre,
div[data-testid="stCodeBlock"] code {{
  background:{panel_bg} !important;
  color:{text} !important;
  border-color:{panel_border} !important;
}}
.map-note {{
  background:{panel_bg} !important;
  border:1px solid {panel_border} !important;
  border-radius:6px !important;
  color:{muted} !important;
  padding:.65rem .8rem !important;
  margin:.5rem 0 .65rem 0 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )

def get_driver(cfg: Dict[str, str]):
    return GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))


def run_cypher(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None) -> pd.DataFrame:
    params = params or {}
    driver = get_driver(cfg)
    try:
        with driver.session(database=cfg["database"]) as session:
            rows = [dict(r) for r in session.run(cypher, params)]
        return pd.DataFrame(rows)
    finally:
        driver.close()


def scalar(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None, default: Any = 0) -> Any:
    df = run_cypher(cfg, cypher, params)
    if df.empty:
        return default
    return df.iloc[0, 0]


def safe_options(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None) -> List[Tuple[str, str]]:
    df = run_cypher(cfg, cypher, params)
    if df.empty:
        return []
    return [(str(r["value"]), str(r["label"])) for _, r in df.iterrows()]


@st.cache_data(ttl=20)
def cached_counts(uri: str, user: str, password: str, database: str) -> Dict[str, int]:
    cfg = {"uri": uri, "user": user, "password": password, "database": database}
    return {
        "AdminUnit": int(scalar(cfg, "MATCH (n:AdminUnit) RETURN count(n)", default=0)),
        "LSOA": int(scalar(cfg, "MATCH (n:LSOA) RETURN count(n)", default=0)),
        "School": int(scalar(cfg, "MATCH (n:School) RETURN count(n)", default=0)),
        "TransportStop": int(scalar(cfg, "MATCH (n:TransportStop) RETURN count(n)", default=0)),
        "WITHIN": int(scalar(cfg, "MATCH ()-[r:WITHIN]->() RETURN count(r)", default=0)),
        "TOUCHES": int(scalar(cfg, "MATCH ()-[r:TOUCHES]->() RETURN count(r)", default=0)),
        "LSOA_TOUCHES": int(scalar(cfg, "MATCH ()-[r:LSOA_TOUCHES]->() RETURN count(r)", default=0)),
        "GRAPH_NEAR": int(scalar(cfg, "MATCH ()-[r:GRAPH_NEAR]->() RETURN count(r)", default=0)),
        "INTERSECTS": int(scalar(cfg, "MATCH ()-[r:INTERSECTS]->() RETURN count(r)", default=0)),
        "LOCATED_IN": int(scalar(cfg, "MATCH ()-[r:LOCATED_IN]->() RETURN count(r)", default=0)),
        "DISTANCE_NEAR": int(scalar(cfg, "MATCH ()-[r:DISTANCE_NEAR]->() RETURN count(r)", default=0)),
    }

def lsoa_options(
    cfg: Dict[str, str],
    option_type: str,
) -> List[Tuple[str, str]]:
    """
    Return LSOAs that can genuinely answer the selected SCQ.

    Each option is returned as:
        (LSOA code, "LSOA code | LSOA name")
    """

    if option_type == "lsoa_touch":
        query = """
        MATCH (l:LSOA)
        WHERE l.code IS NOT NULL
          AND EXISTS {
              MATCH (l)-[:LSOA_TOUCHES]-(:LSOA)
          }
        RETURN DISTINCT
            l.code AS code,
            l.name AS name
        ORDER BY name, code
        """

    elif option_type == "lsoa_near":
        query = """
        MATCH (l:LSOA)
        WHERE l.code IS NOT NULL
          AND EXISTS {
              MATCH (l)-[:GRAPH_NEAR]-(:LSOA)
          }
        RETURN DISTINCT
            l.code AS code,
            l.name AS name
        ORDER BY name, code
        """

    elif option_type == "lsoa_intersects":
        query = """
        MATCH (l:LSOA)
        WHERE l.code IS NOT NULL
          AND EXISTS {
              MATCH (w:AdminUnit)-[:INTERSECTS]->(l)
              WHERE w.type IN ['Ward', 'Community']
          }
        RETURN DISTINCT
            l.code AS code,
            l.name AS name
        ORDER BY name, code
        """

    elif option_type == "lsoa_near_intersects":
        query = """
        MATCH (l:LSOA)
        WHERE l.code IS NOT NULL
          AND EXISTS {
              MATCH (l)-[:GRAPH_NEAR]-(near_lsoa:LSOA)
              MATCH (w:AdminUnit)-[:INTERSECTS]->(near_lsoa)
              WHERE w.type IN ['Ward', 'Community']
          }
        RETURN DISTINCT
            l.code AS code,
            l.name AS name
        ORDER BY name, code
        """

    else:
        query = """
        MATCH (l:LSOA)
        WHERE l.code IS NOT NULL
        RETURN DISTINCT
            l.code AS code,
            l.name AS name
        ORDER BY name, code
        """

    df = run_cypher(cfg, query)

    if df.empty:
        return []

    options: List[Tuple[str, str]] = []

    for _, row in df.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()

        if not code:
            continue

        label = f"{code} | {name}" if name else code
        options.append((code, label))

    return options

def admin_options(
    cfg: Dict[str, str],
    mode: str,
) -> List[Tuple[str, str]]:
    """
    Return administrative units that can answer SCQ5 or SCQ6.
    """

    if mode == "admin_child":
        relationship_filter = """
        WHERE (a)-[:WITHIN]->(:AdminUnit)
        """
    else:
        relationship_filter = """
        WHERE (:AdminUnit)-[:WITHIN]->(a)
        """

    query = f"""
    MATCH (a:AdminUnit)
    {relationship_filter}

    WITH
        a.uri AS uri,
        coalesce(a.name, a.uri) AS name,
        a.type AS type

    WHERE uri IS NOT NULL

    RETURN DISTINCT
        uri AS value,
        name + coalesce(' | ' + type, '') AS label

    ORDER BY label
    LIMIT 500
    """

    return safe_options(cfg, query)

def choose_lsoa_pair(cfg: Dict[str, str]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    opts = lsoa_options(cfg, "lsoa_touch")
    return opts, opts


def scq3_pair_options(cfg: Dict[str, str]) -> List[Tuple[Tuple[str, str], str]]:
    """Return LSOA pairs that are guaranteed to have at least one intermediate LSOA."""
    df = run_cypher(cfg, """
    MATCH (a:LSOA)-[:LSOA_TOUCHES]-(mid:LSOA)-[:LSOA_TOUCHES]-(b:LSOA)
    WHERE a.code < b.code AND NOT (a)-[:LSOA_TOUCHES]-(b)
    RETURN DISTINCT a.code AS a_code,
           a.code + ' | ' + coalesce(a.name, a.LSOA_Name, '') AS a_label,
           b.code AS b_code,
           b.code + ' | ' + coalesce(b.name, b.LSOA_Name, '') AS b_label
    ORDER BY a_code, b_code
    LIMIT 200
    """)
    if df.empty:
        return []
    return [((str(r["a_code"]), str(r["b_code"])), f"{r['a_label']}  →  {r['b_label']}") for _, r in df.iterrows()]


# =============================================================================
# UI COMPONENTS
# =============================================================================
def hero() -> None:
    st.markdown(
        """
<div class="hero">
  <h1>Education Inequality Analysis with a Geospatial Knowledge Graph</h1>
  <p><b>Wales YAGO2geo + LSOA Demonstrator</b> — task-aligned to the supervisor work plan.</p>
  <p><b>Core evaluation rule:</b> Native model coverage is not the same as geometry-assisted demonstrator coverage.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def task_badge(task: str, keyword_sentence: str, status: str = "Done") -> None:
    cls = "done" if "Done" in status or "Complete" in status else "current" if "Current" in status else "next"
    st.markdown(
        f"""
<div class="task-card">
  <span class="badge {cls}">{status}</span>
  <h3>{task}</h3>
  <div><span class="task-key">Keyword sentence:</span> {keyword_sentence}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_task_card(t: Dict[str, Any]) -> None:
    status = t["status"]
    cls = "done" if "Done" in status or "Closed" in status else "current" if "Current" in status else "next"
    solution = TASK_SOLUTIONS.get(t["id"], {})
    subtasks = "".join(
        [f"<div class='subtask'><b>{num} — {name}:</b> {desc}</div>" for num, name, desc in t["subtasks"]]
    )
    st.markdown(
        f"""
<div class="task-card">
  <span class="badge {cls}">{status}</span>
  <h3>{t['id']} — {t['title']}</h3>
  <p><span class="task-key">Target sentence:</span> {t['keyword_sentence']}</p>
  <div class="solutionbox"><b>Implemented answer:</b> {solution.get('answer','')}<br>
  <b>Evidence in this app:</b> {solution.get('evidence','')}<br>
  <b>Where to verify:</b> {solution.get('app_section','')}</div>
  {subtasks}
</div>
""",
        unsafe_allow_html=True,
    )


def provenance_badge(provenance: str) -> str:
    p = provenance.lower()
    cls = "native" if "native" in p and "geometry" not in p else "geometry" if "geometry" in p else "derived"
    return f"<span class='badge {cls}'>{provenance}</span>"


def display_df(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No rows returned for the selected parameter. Try another LSOA/AdminUnit from the dropdown.")
    else:
        if st.session_state.get("dark_theme"):
            st.markdown(
                "<div class='result-table-wrap'>"
                + df.fillna("").to_html(index=False, escape=True)
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)


def school_outline_points(df: pd.DataFrame, bins: int = 34) -> List[Dict[str, float]]:
    """Approximate a Wales outline from available school coordinates."""
    pts = df[["longitude", "latitude"]].dropna().copy()
    if len(pts) < 8:
        return []
    pts["bin"] = pd.cut(pts["longitude"], bins=bins, labels=False, duplicates="drop")
    grouped = (
        pts.dropna(subset=["bin"])
        .groupby("bin", as_index=False)
        .agg(
            longitude=("longitude", "mean"),
            upper_latitude=("latitude", "max"),
            lower_latitude=("latitude", "min"),
        )
        .sort_values("longitude")
    )
    if grouped.empty:
        return []
    upper = [
        {"longitude": float(r.longitude), "latitude": float(r.upper_latitude)}
        for r in grouped.itertuples()
    ]
    lower = [
        {"longitude": float(r.longitude), "latitude": float(r.lower_latitude)}
        for r in grouped.iloc[::-1].itertuples()
    ]
    outline = upper + lower
    if outline:
        outline.append(outline[0])
    return outline


def render_school_map(map_df: pd.DataFrame, selected_school: Tuple[str, str]) -> None:
    """Render the Wales school map with Folium and click-to-open school cards."""
    chart_df = map_df.copy()
    dep_labels = {
        "high_deprivation": "High",
        "medium_deprivation": "Medium",
        "low_deprivation": "Low",
        "unknown": "Unknown",
    }
    chart_df["deprivation"] = chart_df["deprivation"].fillna("unknown").astype(str)
    chart_df["deprivation_label"] = chart_df["deprivation"].map(dep_labels).fillna("Unknown")
    chart_df["fsm_label"] = chart_df["fsm_pct"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}%"
    )
    chart_df["attendance_label"] = chart_df["attendance_pct"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}%"
    )
    chart_df["capped9_label"] = chart_df["capped9_score"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )
    chart_df["nearest_stop_label"] = chart_df["nearest_stop_distance_m"].apply(
        lambda v: "No stop within 800m" if pd.isna(v) else f"{float(v):.0f}m"
    )
    chart_df["wimd_label"] = chart_df["wimd_decile"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{int(float(v))}"
    )
    chart_df["pupils_label"] = chart_df["pupils"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{int(float(v)):,}"
    )
    chart_df["ptr_label"] = chart_df["pupil_teacher_ratio"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )
    chart_df["budget_label"] = chart_df["budget_per_pupil_gbp"].apply(
        lambda v: "N/A" if pd.isna(v) else f"£{float(v):,.0f}"
    )
    chart_df["literacy_label"] = chart_df["literacy_score"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )
    chart_df["numeracy_label"] = chart_df["numeracy_score"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )
    chart_df["science_label"] = chart_df["science_score"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )
    chart_df["welsh_bacc_label"] = chart_df["welsh_bacc_score"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{float(v):.1f}"
    )

    st.markdown(
        "<div class='map-note'>"
        "School locations map over Wales. Click a school point to open its metrics card."
        "</div>",
        unsafe_allow_html=True,
    )

    lat_min, lat_max = chart_df["latitude"].min(), chart_df["latitude"].max()
    lon_min, lon_max = chart_df["longitude"].min(), chart_df["longitude"].max()
    center = [float(chart_df["latitude"].mean()), float(chart_df["longitude"].mean())]
    m = folium.Map(
        location=center,
        zoom_start=7,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
    )
    if float(lat_min) == float(lat_max) and float(lon_min) == float(lon_max):
        # A single selected school has identical min/max coordinates.
        # Give Folium a small local envelope so the map still opens cleanly.
        m.fit_bounds(
            [
                [float(lat_min) - 0.015, float(lon_min) - 0.015],
                [float(lat_max) + 0.015, float(lon_max) + 0.015],
            ],
            padding=(28, 28),
        )
    else:
        m.fit_bounds(
            [[float(lat_min), float(lon_min)], [float(lat_max), float(lon_max)]],
            padding=(28, 28),
        )

    colour_lookup = {
        "high_deprivation": "#ff4f79",
        "medium_deprivation": "#ff8a00",
        "low_deprivation": "#20c6d7",
        "unknown": "#94a3b8",
    }

    def card_row(label: str, value: Any) -> str:
        clean_value = "N/A" if pd.isna(value) or str(value).strip() in {"", "None", "nan"} else str(value)
        return (
            "<div style='background:#f8fafc;border:1px solid #e5e7eb;"
            "border-radius:12px;padding:8px 10px;'>"
            f"<div style='font-size:10px;color:#64748b;font-weight:800;"
            f"text-transform:uppercase;letter-spacing:.03em;'>{escape(label)}</div>"
            f"<div style='font-size:14px;color:#111827;font-weight:900;"
            f"margin-top:2px;'>{escape(clean_value)}</div>"
            "</div>"
        )

    focused = selected_school[0] != "All"
    def clean_text_value(value: Any) -> str:
        if pd.isna(value) or str(value).strip() in {"", "None", "nan"}:
            return "N/A"
        return str(value)

    for _, r in chart_df.iterrows():
        dep_val = str(r.get("deprivation", "unknown"))
        marker_colour = colour_lookup.get(dep_val, "#94a3b8")
        school_name = escape(clean_text_value(r.get("school", "Unknown school")))
        local_authority = escape(clean_text_value(r.get("local_authority", "N/A")))
        school_type = escape(clean_text_value(r.get("school_type", "N/A")))
        gender_mix = escape(clean_text_value(r.get("gender_mix", "N/A")))
        language_medium = escape(clean_text_value(r.get("language_medium", "N/A")))
        address = escape(clean_text_value(r.get("address", "N/A")))
        postcode = escape(clean_text_value(r.get("postcode", "N/A")))
        popup_html = f"""
        <div style="font-family:Segoe UI,Arial,sans-serif;width:310px;color:#111827;">
          <div style="background:linear-gradient(135deg,#ff4f79,#ff8a00);
                      color:white;border-radius:16px 16px 10px 10px;
                      padding:14px 15px;margin:-1px -1px 12px -1px;">
            <div style="font-size:18px;font-weight:900;line-height:1.2;">{school_name}</div>
            <div style="font-size:12px;opacity:.95;margin-top:4px;">{local_authority}</div>
          </div>
          <div style="font-size:12px;color:#475569;margin-bottom:10px;">
            <b>Type:</b> {school_type}<br>
            <b>Language:</b> {language_medium}<br>
            <b>Gender:</b> {gender_mix}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;">
            {card_row("Deprivation", r.get("deprivation_label", "N/A"))}
            {card_row("WIMD decile", r.get("wimd_label", "N/A"))}
            {card_row("FSM", r.get("fsm_label", "N/A"))}
            {card_row("Attendance", r.get("attendance_label", "N/A"))}
            {card_row("Pupils", r.get("pupils_label", "N/A"))}
            {card_row("PTR", r.get("ptr_label", "N/A"))}
            {card_row("Budget / pupil", r.get("budget_label", "N/A"))}
            {card_row("Transport", r.get("nearest_stop_label", "N/A"))}
          </div>
          <div style="margin-top:11px;padding-top:10px;border-top:1px solid #e5e7eb;">
            <div style="font-size:12px;font-weight:900;color:#334155;margin-bottom:7px;">
              Secondary performance
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;">
              {card_row("Capped 9", r.get("capped9_label", "N/A"))}
              {card_row("Literacy", r.get("literacy_label", "N/A"))}
              {card_row("Numeracy", r.get("numeracy_label", "N/A"))}
              {card_row("Science", r.get("science_label", "N/A"))}
              {card_row("Welsh Bac", r.get("welsh_bacc_label", "N/A"))}
            </div>
          </div>
          <div style="margin-top:11px;font-size:11px;line-height:1.35;color:#64748b;">
            <b>Address:</b> {address}<br>
            <b>Postcode:</b> {postcode}
          </div>
        </div>
        """
        folium.CircleMarker(
            location=[float(r["latitude"]), float(r["longitude"])],
            radius=8 if focused else 5.5,
            color="#ffffff",
            weight=1.6,
            fill=True,
            fill_color=marker_colour,
            fill_opacity=0.86,
            tooltip=folium.Tooltip(str(r.get("school", "")), sticky=True),
            popup=folium.Popup(popup_html, max_width=350),
        ).add_to(m)

    legend_html = """
    <div style="
      position: fixed; bottom: 24px; left: 24px; z-index: 9999;
      background: rgba(255,255,255,.94); border: 1px solid #d1d5db;
      border-radius: 12px; padding: 10px 13px; color: #1f2937;
      font-family: Segoe UI, Arial, sans-serif; font-size: 13px;
      box-shadow: 0 6px 18px rgba(15,23,42,.18);">
      <div style="font-weight:900;margin-bottom:6px;">Deprivation</div>
      <div><span style="color:#ff4f79;font-size:18px;">●</span> High</div>
      <div><span style="color:#ff8a00;font-size:18px;">●</span> Medium</div>
      <div><span style="color:#20c6d7;font-size:18px;">●</span> Low</div>
      <div><span style="color:#94a3b8;font-size:18px;">●</span> Unknown</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    components.html(m._repr_html_(), height=790, scrolling=False)

    if selected_school[0] != "All" and not chart_df.empty:
        r = chart_df.iloc[0]
        st.markdown(
            f"""
            <div class="solutionbox">
              <b>Selected school:</b> {r.get('school', '')}<br>
              <b>Local authority:</b> {r.get('local_authority', '')}<br>
              <b>Deprivation:</b> {r.get('deprivation_label', '')} |
              <b>WIMD decile:</b> {r.get('wimd_label', '')}<br>
              <b>FSM:</b> {r.get('fsm_label', '')} |
              <b>Attendance:</b> {r.get('attendance_label', '')} |
              <b>Capped 9:</b> {r.get('capped9_label', '')}<br>
              <b>Nearest transport:</b> {r.get('nearest_stop_label', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )




# =============================================================================
# EVALUATOR-READY VISUAL COMPONENTS — concise, task-serving, light UI
# =============================================================================
def visual_project_pipeline() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>Project Pipeline — each visual block supports a supervisor task</h3>
  <div class="grid grid-5">
    <div class="task-step"><div class="step-num step-blue">1</div><div class="step-title2">Task 1<br>Administrative Hierarchy</div><div class="step-text">YAGO2geo baseline: AdminUnit, WITHIN, TOUCHES.</div></div>
    <div class="task-step"><div class="step-num step-green">2</div><div class="step-title2">Task 2<br>LSOA + Statistics</div><div class="step-text">Add LSOA, WIMD, schools, FSM, transport.</div></div>
    <div class="task-step"><div class="step-num step-orange">3</div><div class="step-title2">Task 3<br>Policy → SCQ</div><div class="step-text">Translate policy questions into SCQ1–SCQ8 patterns.</div></div>
    <div class="task-step"><div class="step-num step-purple">4</div><div class="step-title2">Task 4<br>Demonstrator</div><div class="step-text">Run Cypher, show rows, parameters and provenance.</div></div>
    <div class="task-step"><div class="step-num step-teal">5–6</div><div class="step-title2">Evaluation + Seam</div><div class="step-text">Separate native coverage from geometry-assisted capability.</div></div>
  </div>
  <div class="visual-note"><b>Purpose:</b> this pipeline tells the examiner where each implementation decision is evidenced in the app, without adding decorative content.</div>
</div>
""", unsafe_allow_html=True)


def visual_policy_to_answer() -> None:
    """Task 3 visual: only one purposeful infographic, not decoration."""
    st.markdown("""
<div class="evaluator-panel">
  <h3>One Policy Question → One Evaluated Graph Answer</h3>
  <div class="clean-subtitle">This is the path used for every row in the table below.</div>
  <div class="path-grid">
    <div class="path-step"><div class="path-num step-blue">1</div><b>Policy Question</b><small>Real education-inequality need.</small></div>
    <div class="path-step"><div class="path-num step-green">2</div><b>SCQ Mapping</b><small>Convert into SCQ1–SCQ8.</small></div>
    <div class="path-step"><div class="path-num step-orange">3</div><b>Cypher Pattern</b><small>Executable graph query.</small></div>
    <div class="path-step"><div class="path-num step-purple">4</div><b>Graph Relation</b><small>WITHIN, INTERSECTS, LSOA_TOUCHES, GRAPH_NEAR.</small></div>
    <div class="path-step"><div class="path-num step-teal">5</div><b>Provenance</b><small>Native, Geometry-origin, or Derived.</small></div>
    <div class="path-step"><div class="path-num step-pink">6</div><b>Evaluation</b><small>Model coverage or demonstrator capability.</small></div>
  </div>
  <div class="visual-note"><b>Why this matters:</b> every policy question is not just listed; it is translated, executed, traced, and evaluated.</div>
</div>
""", unsafe_allow_html=True)


def visual_policy_scq_principles() -> None:
    """Small evaluator explanation: why the SCQ table exists."""
    st.markdown("""
<div class="evaluator-panel">
  <h3>Why the SCQ Framework is used here</h3>
  <div class="scq-principle">
    <div class="principle-card"><b>Standardised</b><p>Different policy questions become comparable spatial competency questions.</p></div>
    <div class="principle-card"><b>Executable</b><p>Each SCQ is tied to a Cypher query over the Neo4j knowledge graph.</p></div>
    <div class="principle-card"><b>Explainable</b><p>Every answer reports whether it is Native, Geometry-origin, or Derived.</p></div>
    <div class="principle-card"><b>Evaluated</b><p>Coverage is measured consistently rather than judged informally.</p></div>
  </div>
</div>
""", unsafe_allow_html=True)


def visual_policy_completeness_graphs() -> None:
    """Evaluator visual with no overlap: compact SVGs + score panel, focused on Task 3 and Task 5."""
    html = """
    <style>
      *{box-sizing:border-box} body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#1f2937;background:transparent;overflow:hidden;}
      .panel{width:100%;background:#fff;border:1px solid #fed7aa;border-radius:18px;padding:18px;box-shadow:0 8px 24px rgba(234,88,12,.06)}
      h3{margin:0 0 6px;color:#7c2d12;font-size:20px}.sub{color:#64748b;font-size:13px;margin-bottom:14px}
      .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.card{border:1px solid #fed7aa;border-radius:16px;background:#fff;padding:14px;min-height:360px;overflow:hidden}.score-card{grid-column:1/-1;min-height:auto}.card h4{margin:0 0 8px;color:#7c2d12;font-size:18px}.note{border-radius:12px;padding:10px 12px;margin-top:8px;font-size:13px;line-height:1.45}.green{background:#ecfdf5;border:1px solid #bbf7d0;color:#14532d}.blue{background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a}.amber{background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12}
      .score-grid{display:grid;grid-template-columns:1.25fr .9fr;gap:14px;align-items:stretch}.row{display:grid;grid-template-columns:1.7fr 52px 86px;gap:8px;align-items:center;border-bottom:1px solid #f1f5f9;padding:9px 0;font-size:13px}.line{display:inline-block;width:36px;height:4px;border-radius:99px;margin-right:8px;vertical-align:middle}.native{background:#16a34a}.geo{background:#2563eb}.derived{background:#f97316}.missing{height:0;border-top:3px dashed #94a3b8}.score{background:#fffaf4;border:1px solid #fed7aa;border-radius:14px;padding:14px}.big{font-size:34px;font-weight:900;color:#7c2d12}.bar{height:16px;background:#e5e7eb;border-radius:99px;overflow:hidden;margin:8px 0 12px}.fill1{height:100%;width:0%;background:linear-gradient(90deg,#f59e0b,#fb923c)}.fill2{height:100%;width:100%;background:linear-gradient(90deg,#22c55e,#86efac)}.final{margin-top:14px;background:linear-gradient(135deg,#fff7ed,#f0fdf4);border:1px solid #fed7aa;border-left:6px solid #f97316;border-radius:14px;padding:12px 14px;color:#17324d;font-size:14px}
      svg{display:block;margin:0 auto;max-width:100%;height:230px}.mini{font-size:11px;fill:#334155}.lbl{font-size:12px;font-weight:900}.edge{font-size:10.5px;font-weight:900}
      @media(max-width:900px){.grid,.score-grid{grid-template-columns:1fr}.card{min-height:auto}.score-card{grid-column:auto}}
    </style>
    <div class="panel">
      <h3>SCQ Evaluation Visual — what the table is proving</h3>
      <div class="sub">A focused visual for Task 3 and Task 5: what is native, what was added, and how this affects coverage.</div>
      <div class="grid">
        <div class="card">
          <h4>1) Native administrative backbone</h4>
          <svg viewBox="0 0 500 285" aria-label="Native administrative backbone">
            <defs><marker id="n" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#16a34a"/></marker><marker id="t" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ef4444"/></marker></defs>
            <rect x="40" y="22" width="420" height="230" rx="22" fill="#fffaf4" stroke="#fed7aa"/>
            <rect x="185" y="42" width="130" height="54" rx="18" fill="#ffedd5" stroke="#f97316" stroke-width="3"/><text x="250" y="64" text-anchor="middle" class="lbl">Unitary</text><text x="250" y="81" text-anchor="middle" class="lbl">Authority</text>
            <rect x="82" y="155" width="110" height="54" rx="18" fill="#dcfce7" stroke="#16a34a" stroke-width="3"/><text x="137" y="187" text-anchor="middle" class="lbl">Ward</text>
            <rect x="308" y="155" width="110" height="54" rx="18" fill="#dcfce7" stroke="#16a34a" stroke-width="3"/><text x="363" y="187" text-anchor="middle" class="lbl">Community</text>
            <path d="M220,96 C190,125 165,142 148,154" fill="none" stroke="#16a34a" stroke-width="4" marker-end="url(#n)"/><text x="170" y="128" class="edge" fill="#166534">WITHIN</text>
            <path d="M280,96 C313,126 336,143 352,154" fill="none" stroke="#16a34a" stroke-width="4" marker-end="url(#n)"/><text x="325" y="128" class="edge" fill="#166534">WITHIN</text>
            <path d="M190,205 C244,245 294,245 342,205" fill="none" stroke="#ef4444" stroke-width="4" marker-end="url(#t)"/><text x="250" y="244" text-anchor="middle" class="edge" fill="#991b1b">TOUCHES inside administrative hierarchy</text>
          </svg>
          <div class="note green"><b>Meaning:</b> YAGO2geo is strong for native administrative hierarchy relations. These count toward model-level coverage.</div>
        </div>
        <div class="card">
          <h4>2) Knowledge extension in this project</h4>
          <svg viewBox="0 0 500 285" aria-label="Knowledge extension graph">
            <defs><marker id="g" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#f97316"/></marker><marker id="d" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#7c3aed"/></marker><marker id="b" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2563eb"/></marker></defs>
            <rect x="36" y="22" width="428" height="230" rx="22" fill="#fffaf4" stroke="#fed7aa"/>
            <rect x="60" y="54" width="150" height="50" rx="16" fill="#ffedd5" stroke="#f97316" stroke-width="2"/><text x="135" y="75" text-anchor="middle" class="lbl" fill="#9a3412">AdminUnit</text><text x="135" y="91" text-anchor="middle" class="mini">administrative hierarchy</text>
            <rect x="300" y="54" width="145" height="50" rx="16" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/><text x="372" y="77" text-anchor="middle" class="lbl" fill="#1e3a8a">LSOA</text><text x="372" y="93" text-anchor="middle" class="mini">statistical area</text>
            <rect x="300" y="145" width="145" height="50" rx="16" fill="#dcfce7" stroke="#16a34a" stroke-width="2"/><text x="372" y="176" text-anchor="middle" class="lbl" fill="#166534">School</text>
            <rect x="300" y="225" width="145" height="45" rx="16" fill="#fef3c7" stroke="#f59e0b" stroke-width="2"/><text x="372" y="252" text-anchor="middle" class="lbl" fill="#92400e">Transport Stop</text>
            <path d="M210,79 L300,79" stroke="#f97316" stroke-width="4" marker-end="url(#g)"/><text x="255" y="60" text-anchor="middle" class="edge" fill="#c2410c">INTERSECTS</text>
            <path d="M372,104 L372,145" stroke="#f97316" stroke-width="4" marker-end="url(#g)"/><text x="390" y="130" class="edge" fill="#c2410c">LOCATED_IN</text>
            <path d="M372,195 L372,225" stroke="#7c3aed" stroke-width="4" marker-end="url(#d)"/><text x="390" y="218" class="edge" fill="#6d28d9">DISTANCE_NEAR</text>
            <path d="M372,54 C420,32 455,50 458,82 C456,113 424,125 394,110" fill="none" stroke="#2563eb" stroke-width="3" stroke-dasharray="6 5" marker-end="url(#b)"/>
            <text x="426" y="39" text-anchor="middle" class="edge" fill="#1d4ed8">GRAPH_NEAR</text><text x="426" y="53" text-anchor="middle" class="mini" fill="#1d4ed8">LSOA neighbourhood</text>
          </svg>
          <div class="note blue"><b>Meaning:</b> the demonstrator adds the statistical seam and education data, then labels each answer by provenance.</div>
        </div>
        <div class="card score-card">
          <h4>3) Coverage summary by relation type</h4>
          <div class="score-grid">
            <div>
              <div class="row"><span><i class="line native"></i>WITHIN / contains</span><b>✓</b><b>Native</b></div>
              <div class="row"><span><i class="line native"></i>TOUCHES inside admin</span><b>✓</b><b>Native</b></div>
              <div class="row"><span><i class="line geo"></i>LSOA_TOUCHES</span><b>✓</b><b>Geo</b></div>
              <div class="row"><span><i class="line geo"></i>Admin–LSOA INTERSECTS</span><b>✓</b><b>Geo</b></div>
              <div class="row"><span><i class="line derived"></i>GRAPH_NEAR / traversal</span><b>✓</b><b>Derived</b></div>
              <div class="row"><span><i class="line missing"></i>Native Admin–LSOA seam</span><b>✗</b><b>Missing</b></div>
            </div>
            <div class="score"><div>Education native LSOA coverage</div><div class="big">0 native</div><div class="bar"><div class="fill1"></div></div><div>Implemented forms</div><div class="big" style="color:#15803d">8 mixed</div><div class="bar"><div class="fill2"></div></div></div>
          </div>
        </div>
      </div>
      <div class="final"><b>Reading:</b> the app answers the implemented questions, but several answers require geometry-origin or derived relations; therefore they support the demonstrator rather than native YAGO2geo model completeness.</div>
    </div>
    """
    if st.session_state.get("dark_theme"):
        dark_component_css = """
      .panel,.card,.score{background:rgba(255,255,255,.08)!important;border-color:rgba(255,255,255,.18)!important;box-shadow:none!important;color:#f8fafc!important}
      h3,.card h4,.big{color:#f8fafc!important}.sub,.row,.score div{color:#dbeafe!important}
      .row{border-bottom-color:rgba(255,255,255,.15)!important}
      .final,.note{background:rgba(255,255,255,.10)!important;border-color:rgba(255,255,255,.18)!important;color:#f8fafc!important}
      .green,.blue,.amber{background:rgba(255,255,255,.10)!important;color:#f8fafc!important}
      .mini{fill:#334155!important}.lbl{fill:#0f172a!important}
      .bar{background:rgba(255,255,255,.22)!important}
"""
        html = html.replace("</style>", dark_component_css + "    </style>", 1)
    components.html(html, height=895, scrolling=False)

def visual_scq_runner_flow() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>SCQ Demonstrator Execution — what happens when a question runs</h3>
  <div class="grid grid-4">
    <div class="task-step"><div class="step-num step-blue">A</div><div class="step-title2">Select SCQ</div><div class="step-text">Choose one of the eight spatial competency questions.</div></div>
    <div class="task-step"><div class="step-num step-orange">B</div><div class="step-title2">Run Cypher</div><div class="step-text">The app shows the exact query and parameters.</div></div>
    <div class="task-step"><div class="step-num step-green">C</div><div class="step-title2">Return evidence</div><div class="step-text">Rows and counts prove the answer is not just text.</div></div>
    <div class="task-step"><div class="step-num step-purple">D</div><div class="step-title2">Interpret coverage</div><div class="step-text">The app states whether it is Native, Geometry-origin, or Derived.</div></div>
  </div>
</div>
""", unsafe_allow_html=True)


def visual_coverage_summary() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>Coverage Summary — the key result of Task 5</h3>
  <div class="grid grid-2">
    <div class="coverage-card">
      <div class="score-label">Education-use-case native coverage</div>
      <div class="big-score">0 <span style="font-size:1rem;color:#64748b">native LSOA answers</span></div>
      <div class="bar-track"><div style="height:100%;width:0%;background:#f97316"></div></div>
      <p class="step-text">SCQ5 and SCQ6 are reclassified / n/a for the education use case, while LSOA and cross-hierarchy answers rely on geometry-origin or derived relations.</p>
    </div>
    <div class="coverage-card">
      <div class="score-label">Implemented demonstrator forms</div>
      <div class="big-score">8 <span style="font-size:1rem;color:#64748b">mixed-scope SCQs</span></div>
      <div class="bar-track"><div class="bar-demo"></div></div>
      <p class="step-text">Shows what the application can run using native administrative, geometry-origin, and derived graph reasoning.</p>
    </div>
  </div>
  <div class="visual-note"><b>Core rule:</b> geometry-origin relations improve the demonstrator, but they do not increase native YAGO2geo model completeness.</div>
</div>
""", unsafe_allow_html=True)


def visual_scq_matrix() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>SCQ Coverage Matrix — concise provenance view</h3>
  <div class="scq-grid">
    <div class="scq-tile geo-border"><h4>SCQ1</h4><p>Neighbours / touches</p><p><b>Geometry-origin</b></p></div>
    <div class="scq-tile derived-border"><h4>SCQ2</h4><p>Near</p><p><b>Derived</b></p></div>
    <div class="scq-tile derived-border"><h4>SCQ3</h4><p>Between</p><p><b>Derived / weak fit</b></p></div>
    <div class="scq-tile derived-border"><h4>SCQ4</h4><p>Not neighbours</p><p><b>Derived</b></p></div>
    <div class="scq-tile native-border"><h4>SCQ5</h4><p>Contains (Admin only)</p><p><b>Native admin / n/a education</b></p></div>
    <div class="scq-tile native-border"><h4>SCQ6</h4><p>Inside (Admin only)</p><p><b>Native admin / n/a education</b></p></div>
    <div class="scq-tile geo-border"><h4>SCQ7</h4><p>Admin–LSOA intersect</p><p><b>Geometry-origin</b></p></div>
    <div class="scq-tile mix-border"><h4>SCQ8</h4><p>Admin–LSOA near</p><p><b>Geometry + Derived</b></p></div>
  </div>
  <div class="mini-legend" style="margin-top:.65rem"><span class="lg-native">Native model</span><span class="lg-geo">Geometry-origin</span><span class="lg-derived">Derived reasoning</span><span class="lg-missing">Not native in YAGO2geo</span></div>
</div>
""", unsafe_allow_html=True)


def visual_knowledge_pyramid() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>Knowledge Extension Pyramid — why capability increases</h3>
  <div class="pyramid-light">
    <div class="pyr p1">Education Questions<br><small>SCQ1–SCQ8</small></div>
    <div class="pyr p2">Graph Reasoning<br><small>GRAPH_NEAR · paths · NOT TOUCHES</small></div>
    <div class="pyr p3">Geometry Processing<br><small>INTERSECTS · LSOA_TOUCHES · LOCATED_IN</small></div>
    <div class="pyr p4">Native YAGO2geo<br><small>Admin hierarchy · WITHIN · TOUCHES</small></div>
  </div>
</div>
""", unsafe_allow_html=True)


def visual_cross_hierarchy_bridge() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>Cross-hierarchy Bridge — the main Task 6 finding</h3>
  <div class="bridge-wrap">
    <div class="bridge-side"><b>Administrative geography</b><br><span class="step-text">Unitary Authority<br>Ward<br>Community</span></div>
    <div class="bridge-mid-light"><div>INTERSECTS</div><div>GRAPH_NEAR</div></div>
    <div class="bridge-side right"><b>Statistical geography</b><br><span class="step-text">LSOA<br>WIMD<br>Rank / Decile</span></div>
  </div>
  <div class="visual-note"><b>Finding:</b> AdminUnit–LSOA relations are not native in YAGO2geo. The app reconstructs this seam using geometry-origin INTERSECTS and derived GRAPH_NEAR, so SCQ7 and SCQ8 are answerable in the demonstrator but not counted as native model coverage.</div>
</div>
""", unsafe_allow_html=True)


def visual_final_finding() -> None:
    st.markdown("""
<div class="final-box">
  <b>Final research contribution:</b> The demonstrator does not claim that YAGO2geo becomes complete. It shows, with executable evidence, which spatial knowledge is native, which is computed from geometry, and how graph reasoning extends the model to answer education policy questions.
  <br><br><b>Native Coverage ≠ Demonstrator Capability.</b>
</div>
""", unsafe_allow_html=True)


def page_visual_story() -> None:
    hero()
    st.header("Evaluator-ready visual summary")
    st.caption("Only the visuals that directly support the supervisor tasks are shown here: pipeline, question translation, execution evidence, coverage, and cross-hierarchy finding.")
    visual_project_pipeline()
    c1, c2 = st.columns([1,1])
    with c1:
        visual_policy_to_answer()
    with c2:
        visual_scq_runner_flow()
    c3, c4 = st.columns([1,1])
    with c3:
        visual_coverage_summary()
    with c4:
        visual_cross_hierarchy_bridge()
    visual_scq_matrix()
    visual_knowledge_pyramid()
    visual_final_finding()

# =============================================================================
# PAGES
# =============================================================================
def page_task_overview(cfg: Dict[str, str]) -> None:
    hero()
    st.header("Task-aligned implemented answers")
    st.caption("This page is not only progress tracking: each task shows the implemented answer, the evidence, and where the supervisor can verify it in the app.")
    cols = st.columns(4)
    try:
        counts = cached_counts(cfg["uri"], cfg["user"], cfg["password"], cfg["database"])
        cols[0].metric("AdminUnit", f"{counts['AdminUnit']:,}")
        cols[1].metric("LSOA", f"{counts['LSOA']:,}")
        cols[2].metric("School", f"{counts['School']:,}")
        cols[3].metric("TransportStop", f"{counts['TransportStop']:,}")
    except Exception as e:
        st.warning(f"Neo4j connection check failed: {e}")

    visual_project_pipeline()
    visual_coverage_summary()
    visual_final_finding()

    for t in TASKS:
        render_task_card(t)


def page_policy_questions() -> None:
    hero()
    task_badge(
        "Task 3 — Policy Questions mapped to SCQs",
        "Translate education-policy questions into standard spatial competency question forms so the use case is evaluated through SCQ1–SCQ8 rather than ad-hoc queries.",
        "Closed in artifact / Expand with literature later",
    )
    st.markdown(
        "<div class='solutionbox'><b>Implemented answer:</b> This page gives the examiner a direct evidence path: policy question → SCQ form → Cypher-ready relation → provenance → coverage decision. It supports Task 3 and prepares the scoring logic used in Task 5.</div>",
        unsafe_allow_html=True,
    )
    tab1, tab2 = st.tabs(["SCQ overview", "Question table"])
    with tab1:
        visual_policy_to_answer()
        visual_policy_scq_principles()
        visual_policy_completeness_graphs()
        st.markdown(
            "<div class='final-strip'><b>Final finding:</b> Education policy questions naturally span both administrative and statistical geography. Therefore, the demonstrator must combine native relations, geometry-origin relations, and derived graph reasoning rather than relying on one relation type only.</div>",
            unsafe_allow_html=True,
        )
    with tab2:
        df = pd.DataFrame(POLICY_LIBRARY, columns=["SCQ", "Policy question pattern", "Implemented graph answer", "Task link", "Relation used", "Provenance"])
        df["Counts toward native model completeness?"] = df["Provenance"].map(lambda p: "Yes" if p == "Native" else ("n/a" if "Weak" in p else "No"))
        st.markdown("<div class='clean-title'>Implemented Policy Question Library</div>", unsafe_allow_html=True)
        st.markdown("<div class='clean-subtitle'>Each row is intentionally task-linked and provenance-backed.</div>", unsafe_allow_html=True)
        st.markdown("<div class='policy-table-wrap'>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='warning-strip'><b>Evaluation note:</b> SCQ3 is retained as a weak/optional competency form for transparency. Ward–LSOA containment-style questions are reclassified to SCQ7/SCQ8 because the administrative and statistical hierarchies do not nest cleanly.</div>",
            unsafe_allow_html=True,
        )

def page_scq_demonstrator(
    cfg: Dict[str, str],
) -> None:
    hero()

    task_badge(
        "Task 4 — SCQ Demonstrator",
        (
            "Run SCQ1–SCQ8 over the integrated Neo4j graph while "
            "showing the query, parameters, results, and provenance "
            "of the relation used."
        ),
        "Current / Closing",
    )

    visual_scq_runner_flow()

    scq_key = st.selectbox(
        "Select SCQ",
        list(SCQ_META.keys()),
        format_func=lambda key: SCQ_META[key]["label"],
    )

    meta = SCQ_META[scq_key]

    left, right = st.columns([2.2, 1])

    with left:
        st.subheader(meta["question"])
        st.write(meta["keyword_sentence"])
        st.caption(f"Task link: {meta['task']}")

    with right:
        st.markdown(
            f"**Relation used**\n\n`{meta['relation']}`"
        )
        st.markdown(
            (
                "**Provenance**\n\n"
                f"{provenance_badge(meta['provenance'])}"
            ),
            unsafe_allow_html=True,
        )

    limit = st.slider(
        "Result limit",
        min_value=1,
        max_value=200,
        value=30,
    )

    params: Dict[str, Any] = {
        "limit": limit,
    }

    param_type = meta["param_type"]

    if (
        param_type.startswith("lsoa")
        and param_type != "lsoa_pair"
    ):
        options = lsoa_options(
            cfg,
            param_type,
        )

        if not options:
            options = lsoa_options(
                cfg,
                "lsoa_any",
            )

        if not options:
            st.error(
                "No suitable LSOA options were found in Neo4j."
            )
            return

        selected_lsoa = st.selectbox(
            "LSOA",
            options,
            format_func=lambda option: option[1],
            key=f"{scq_key}_lsoa",
        )

        params["lsoa"] = selected_lsoa[0]

    elif param_type == "lsoa_pair":
        pair_options = scq3_pair_options(cfg)

        if pair_options:
            selected_pair = st.selectbox(
                (
                    "Connected LSOA pair with at least one "
                    "intermediate region"
                ),
                pair_options,
                format_func=lambda option: option[1],
                key="scq3_pair",
            )

            (
                params["lsoa_a"],
                params["lsoa_b"],
            ) = selected_pair[0]

        else:
            options_a, options_b = choose_lsoa_pair(cfg)

            if len(options_a) < 2:
                st.error(
                    "Not enough connected LSOAs were found for SCQ3."
                )
                return

            selected_a = st.selectbox(
                "LSOA A",
                options_a,
                format_func=lambda option: option[1],
                index=0,
                key="scq3_lsoa_a",
            )

            selected_b = st.selectbox(
                "LSOA B",
                options_b,
                format_func=lambda option: option[1],
                index=1 if len(options_b) > 1 else 0,
                key="scq3_lsoa_b",
            )

            params["lsoa_a"] = selected_a[0]
            params["lsoa_b"] = selected_b[0]

    elif param_type.startswith("admin"):
        admin_units = admin_options(
            cfg,
            param_type,
        )

        if not admin_units:
            st.error(
                "No suitable administrative units were found "
                "for this query."
            )
            return

        selected_admin = st.selectbox(
            "Administrative unit",
            admin_units,
            format_func=lambda option: option[1],
            key=f"{scq_key}_admin",
        )

        params["admin"] = selected_admin[0]

    run_query = st.button(
        "Run SCQ query",
        type="primary",
    )

    st.markdown("### Cypher used")
    st.code(
        meta["cypher"].strip(),
        language="cypher",
    )

    st.markdown("### Parameters")
    st.json(params)

    if not run_query:
        return

    try:
        result_df = run_cypher(
            cfg,
            meta["cypher"],
            params,
        )

        strong_answers = {
            "SCQ1": (
                "SCQ1 is answered using the computed "
                "<b>LSOA_TOUCHES</b> relation. It retrieves LSOAs "
                "that directly border the selected LSOA and summarises "
                "school FSM, attendance, and secondary-performance "
                "evidence where School nodes are already linked to those "
                "LSOAs. Because the adjacency relation was computed from "
                "geometry, it supports demonstrator capability but not "
                "native model coverage."
            ),
            "SCQ2": (
                "SCQ2 is answered using <b>GRAPH_NEAR</b>. This "
                "represents qualitative proximity derived from graph "
                "traversal over the stored LSOA neighbourhood, rather "
                "than a raw distance threshold. The returned LSOAs also "
                "show school FSM, attendance, and secondary-performance "
                "summaries where scraped school metrics are available."
            ),
            "SCQ3": (
                "SCQ3 is implemented as bounded simple-path reasoning "
                "over <b>LSOA_TOUCHES</b>. The app returns candidate "
                "between paths rather than defining between as only the "
                "shortest path. Its fit to the education-policy use case "
                "is reported honestly as weak or optional unless clusters "
                "are formally defined."
            ),
            "SCQ4": (
                "SCQ4 is answered as the complement of "
                "<b>LSOA_TOUCHES</b>. It returns LSOAs that do not "
                "share the stored adjacency relation with the selected "
                "LSOA, with school FSM, attendance, and secondary "
                "performance summaries to make the policy evidence "
                "visible."
            ),
            "SCQ5": (
                "SCQ5 demonstrates native administrative containment "
                "by traversing <b>WITHIN</b> upward from a selected "
                "administrative unit to its parent units. This is a "
                "native administrative comparison; it is not treated "
                "as Ward–LSOA containment in the education use case."
            ),
            "SCQ6": (
                "SCQ6 demonstrates native administrative containment "
                "by traversing <b>WITHIN</b> downward from a selected "
                "parent unit to its contained administrative units. "
                "This remains inside the administrative hierarchy."
            ),
            "SCQ7": (
                "SCQ7 answers the Ward–LSOA cross-hierarchy question "
                "using computed <b>INTERSECTS</b>. It is operationally "
                "answerable and displays school indicators from the "
                "intersected LSOA, but its provenance is Geometry-origin, "
                "not Native."
            ),
            "SCQ8": (
                "SCQ8 combines <b>GRAPH_NEAR</b> between LSOAs with "
                "<b>INTERSECTS</b> to reach nearby wards or communities. The answer "
                "shows school indicators from nearby LSOAs. It uses "
                "Geometry-origin and Derived relations and does not "
                "increase native model completeness."
            ),
        }

        st.markdown("### Implemented answer")

        st.markdown(
            (
                "<div class='solutionbox'>"
                f"<b>Implemented answer:</b> "
                f"{strong_answers[scq_key]}"
                "<br><br>"
                f"<b>Evaluation status:</b> "
                f"{meta.get('evaluation_note', 'See provenance above.')}"
                "<br>"
                f"<b>Evidence:</b> The query returned "
                f"<b>{len(result_df)}</b> result row(s) for the "
                "selected parameter."
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        st.markdown("### Results")

        result_label = meta.get(
            "result_label",
            "Result rows returned",
        )

        st.metric(
            result_label,
            len(result_df),
        )

        display_df(result_df)

        if scq_key in {
            "SCQ1",
            "SCQ2",
            "SCQ3",
            "SCQ4",
            "SCQ7",
            "SCQ8",
        }:
            st.markdown(
                (
                    "<div class='warningbox'>"
                    "<b>Evaluation interpretation:</b> "
                    "This answer is available in the demonstrator, "
                    "but it does not increase native YAGO2geo model "
                    "completeness because its spatial basis is computed "
                    "from geometry or derived from a geometry-origin "
                    "relation."
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        else:
            st.markdown(
                (
                    "<div class='successbox'>"
                    "<b>Evaluation interpretation:</b> "
                    "This query demonstrates the equivalent SCQ form "
                    "inside the native administrative hierarchy. "
                    "For the LSOA-based education-use-case scorecard, "
                    "SCQ5 and SCQ6 remain reclassified rather than "
                    "being claimed as Ward–LSOA containment."
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    except Exception as error:
        st.error(
            f"Query failed: {error}"
        )

def page_evaluation() -> None:
    # Evaluation page rule:
    # keep the native Education Use Case scorecard separate from the
    # administrative comparison and from the broader demonstrator capability.
    # This directly addresses the supervisor note that SCQ5/SCQ6 should be
    # reclassified for Ward-LSOA questions rather than counted as independent
    # education-use-case answers.
    hero()

    task_badge(
        "Task 5 — Evaluation and Coverage",
        (
            "Evaluate native model coverage separately from "
            "geometry-assisted demonstrator coverage using one "
            "consistent eight-SCQ scorecard."
        ),
        "Closed in artifact",
    )

    st.markdown(
        (
            "<div class='solutionbox'>"
            "<b>Implemented answer:</b> The education-use-case scorecard "
            "is separated from the native administrative comparison. "
            "For the LSOA-based education questions, YAGO2geo has no "
            "native LSOA↔LSOA or AdminUnit↔LSOA coverage; SCQ5 and SCQ6 "
            "are therefore reclassified / n/a rather than counted as "
            "independent education answers. The demonstrator still runs "
            "the implemented SCQ forms using geometry-origin and derived "
            "relations, while <b>SpCom = 3/6 = 0.50</b> records the "
            "corrected native model baseline."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # Three equal-sized metric cards
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            label="Education native coverage",
            value="0 native LSOA answers",
        )

    with m2:
        st.metric(
            label="Native SpCom",
            value="3/6 = 0.50",
        )

    with m3:
        st.metric(
            label="Implemented forms",
            value="8 mixed-scope SCQs",
        )

    # Formal IJGI SpCom equation
    st.latex(
        r"SpCom(O)"
        r"=\frac{SR_s}{Size_{R_s}(\Omega)}"
        r"=\frac{3}{6}"
        r"=0.50"
    )

    st.markdown(
        (
            "<div class='warningbox'>"
            "<b>Core rule:</b> Geometry-origin relations stored in Neo4j "
            "help the demonstrator, but they do not raise the original "
            "YAGO2geo native model score."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if "eval_tab" not in st.session_state:
        st.session_state.eval_tab = "Visual evaluation"

    ctab1, ctab2, _ = st.columns([1.15, 1.05, 5])

    with ctab1:
        if st.button(
            "Visual evaluation",
            type=(
                "primary"
                if st.session_state.eval_tab == "Visual evaluation"
                else "secondary"
            ),
            use_container_width=True,
        ):
            st.session_state.eval_tab = "Visual evaluation"
            st.rerun()

    with ctab2:
        if st.button(
            "Evidence tables",
            type=(
                "primary"
                if st.session_state.eval_tab == "Evidence tables"
                else "secondary"
            ),
            use_container_width=True,
        ):
            st.session_state.eval_tab = "Evidence tables"
            st.rerun()

    if st.session_state.eval_tab == "Visual evaluation":
        visual_policy_completeness_graphs()
        visual_scq_matrix()
        visual_cross_hierarchy_bridge()
        visual_final_finding()

    else:
        st.subheader("5.1 Native model completeness table — native only")
        st.dataframe(
            MODEL_COMPLETENESS,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("5.2 SCQ scorecard for the education use case")
        st.dataframe(
            SCQ_SCORECARD,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("5.3 Demonstrator coverage")
        st.dataframe(
            DEMO_COVERAGE,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(
            "5.4 Geometry-on-demand vs Compute-once-then-reason"
        )

        comparison_table = pd.DataFrame(
            [
                [
                    "Geometry-on-demand",
                    "Run polygon relations at query time",
                    "High every query",
                    "No",
                    "Baseline",
                ],
                [
                    "Compute-once-then-reason",
                    (
                        "Compute base relations once, store them, "
                        "then traverse"
                    ),
                    "Paid once",
                    "Yes",
                    "Shows what representation buys",
                ],
            ],
            columns=[
                "Mode",
                "What happens",
                "Geometric cost",
                "Stored?",
                "Role in evaluation",
            ],
        )

        st.dataframe(
            comparison_table,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(
        (
            "<div class='successbox'>"
            "<b>Final finding:</b> The native YAGO2geo model is strong "
            "for administrative hierarchy questions, but the education "
            "use case lives at the LSOA and cross-hierarchy seam. "
            "The demonstrator answers the implemented SCQ patterns by "
            "adding geometry-origin relations and derived graph reasoning "
            "while preserving a strict distinction between model completeness "
            "and operational capability."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

def page_cross_hierarchy(cfg: Dict[str, str]) -> None:
    hero()

    task_badge(
        "Task 6 — Cross-hierarchy Seam",
        (
            "Evaluate the seam between administrative hierarchy and "
            "statistical hierarchy using INTERSECTS and near relations "
            "between AdminUnit and LSOA."
        ),
        "Current / Closing",
    )

    visual_cross_hierarchy_bridge()

    # ------------------------------------------------------------------
    # Current Neo4j relationship counts
    # Direction is specified to avoid counting every relationship twice.
    # ------------------------------------------------------------------
    try:
        intersects_count = int(
            scalar(
                cfg,
                """
                MATCH (:AdminUnit)-[r:INTERSECTS]->(:LSOA)
                RETURN count(r)
                """,
                default=0,
            )
        )

        graph_near_count = int(
            scalar(
                cfg,
                """
                MATCH (:LSOA)-[r:GRAPH_NEAR]->(:LSOA)
                RETURN count(r)
                """,
                default=0,
            )
        )

        unique_graph_near_pairs = int(
            scalar(
                cfg,
                """
                MATCH (a:LSOA)-[:GRAPH_NEAR]->(b:LSOA)
                RETURN count(
                    DISTINCT CASE
                        WHEN a.code < b.code
                        THEN a.code + '|' + b.code
                        ELSE b.code + '|' + a.code
                    END
                )
                """,
                default=0,
            )
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "AdminUnit–LSOA INTERSECTS",
            f"{intersects_count:,}",
        )

        c2.metric(
            "Stored LSOA GRAPH_NEAR",
            f"{graph_near_count:,}",
        )

        c3.metric(
            "Unique GRAPH_NEAR pairs",
            f"{unique_graph_near_pairs:,}",
        )

    except Exception as exc:
        st.warning(
            f"Could not load cross-hierarchy counts: {exc}"
        )

    st.markdown(
        (
            "<div class='solutionbox'>"
            "<b>Implemented answer:</b> Cross-hierarchy relations are "
            "not native in YAGO2geo. The app demonstrates the solution "
            "using stored Geometry-origin INTERSECTS for SCQ7 and "
            "Derived GRAPH_NEAR followed by INTERSECTS for SCQ8. "
            "Both are reported as demonstrator capability rather than "
            "native model completeness."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Parameterised SCQ7 query:
    # selected LSOA -> directly intersecting administrative units
    # ------------------------------------------------------------------

    scq7_query = """
    MATCH (admin:AdminUnit)-[:INTERSECTS]->(l:LSOA {code:$lsoa})
    WHERE admin.type IN ['Ward', 'Community']
    OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
    WITH
        admin,
        l,
        count(DISTINCT s) AS school_count,
        avg(s.fsm_pct) AS avg_fsm_pct,
        avg(s.attendance_pct) AS avg_attendance_pct,
        avg(s.capped9_score) AS avg_capped9_score
    RETURN
        coalesce(admin.name, admin.uri) AS administrative_unit,
        admin.type AS administrative_type,
        admin.uri AS administrative_uri,
        l.code AS lsoa_code,
        l.name AS lsoa_name,
        school_count,
        round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
        round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
        round(avg_capped9_score, 1) AS avg_secondary_capped9_score
    ORDER BY administrative_type, administrative_unit
    LIMIT $limit
    """

    

    # ------------------------------------------------------------------
    # Parameterised SCQ8 query:
    # selected LSOA -> GRAPH_NEAR LSOAs -> intersecting AdminUnits
    #
    # Each AdminUnit is returned once. All supporting nearby LSOAs
    # are collected in the same result row.
    # ------------------------------------------------------------------


    scq8_query = """
    MATCH (x:LSOA {code:$lsoa})
        -[:GRAPH_NEAR]-(near_lsoa:LSOA)

    MATCH (admin:AdminUnit)-[:INTERSECTS]->(near_lsoa)
    WHERE admin.type IN ['Ward', 'Community']
    OPTIONAL MATCH (near_lsoa)<-[:LOCATED_IN]-(s:School)

    WITH
        admin,
        collect(DISTINCT near_lsoa.code) AS via_near_lsoas,
        collect(DISTINCT near_lsoa.name) AS via_near_lsoa_names,
        count(DISTINCT s) AS school_count,
        avg(s.fsm_pct) AS avg_fsm_pct,
        avg(s.attendance_pct) AS avg_attendance_pct,
        avg(s.capped9_score) AS avg_capped9_score

    RETURN
        coalesce(admin.name, admin.uri) AS administrative_unit,
        admin.type AS administrative_type,
        admin.uri AS administrative_uri,
        via_near_lsoas,
        via_near_lsoa_names,
        size(via_near_lsoas) AS supporting_lsoas,
        school_count,
        round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
        round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
        round(avg_capped9_score, 1) AS avg_secondary_capped9_score

    ORDER BY avg_school_fsm_pct DESC, administrative_type, administrative_unit
    LIMIT $limit
    """ 

    opts7 = lsoa_options(cfg, "lsoa_intersects")
    opts8 = lsoa_options(cfg, "lsoa_near_intersects")

    # Use Cardiff 018B as the default documented example when available.
    example_code = "W01001770"

    default7 = next(
        (
            index
            for index, option in enumerate(opts7)
            if option[0] == example_code
        ),
        0,
    )

    default8 = next(
        (
            index
            for index, option in enumerate(opts8)
            if option[0] == example_code
        ),
        0,
    )

    c7, c8 = st.columns(2)

    # ------------------------------------------------------------------
    # SCQ7
    # ------------------------------------------------------------------
    with c7:
        st.subheader(
            "6.2 SCQ7 — Cross-hierarchy intersects"
        )

        if opts7:
            selected7 = st.selectbox(
                "LSOA for SCQ7",
                opts7,
                index=default7,
                format_func=lambda option: option[1],
                key="cross7",
            )

            df7 = run_cypher(
                cfg,
                scq7_query,
                {
                    "lsoa": selected7[0],
                    "limit": 30,
                },
            )

            st.metric(
                "Intersecting administrative units found",

                len(df7),
            )

            if df7.empty:
                st.info(
                    "No directly intersecting administrative units were returned "
                    "for this LSOA."
                )               
            else:
                display_df(df7)

        else:
            st.warning(
                "No LSOAs are currently available for SCQ7."
            )

        with st.expander(
            "Show SCQ7 Cypher query"
        ):
            st.code(
                scq7_query.strip(),
                language="cypher",
            )

    # ------------------------------------------------------------------
    # SCQ8
    # ------------------------------------------------------------------
    with c8:
        st.subheader(
            "6.3 SCQ8 — Cross-hierarchy near"
        )

        if opts8:
            selected8 = st.selectbox(
                "LSOA for SCQ8",
                opts8,
                index=default8,
                format_func=lambda option: option[1],
                key="cross8",
            )

            df8 = run_cypher(
                cfg,
                scq8_query,
                {
                    "lsoa": selected8[0],
                    "limit": 30,
                },
            )

            st.metric(
                "Nearby administrative units found",

                len(df8),
            )

            if df8.empty:
                st.info(
                    "No cross-hierarchy proximity results were "
                    "returned for this LSOA."
                )
            else:
                display_df(df8)

        else:
            st.warning(
                "No LSOAs are currently available for SCQ8."
            )

        with st.expander(
            "Show SCQ8 Cypher query"
        ):
            st.code(
                scq8_query.strip(),
                language="cypher",
            )

    st.markdown(
        (
            "<div class='successbox'>"
            "<b>Final finding:</b> Native YAGO2geo contains no explicit "
            "AdminUnit–LSOA seam. Geometry-origin INTERSECTS reconstructs "
            "the bridge, while Derived GRAPH_NEAR extends it into "
            "cross-hierarchy qualitative proximity. This makes SCQ7 and "
            "SCQ8 answerable in the demonstrator without increasing native "
            "model completeness."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    visual_final_finding()

def page_map(cfg: Dict[str, str]) -> None:
    hero()
    task_badge(
        "Task 4.5 — Lightweight Map Support",
        (
            "Keep a School–LSOA–Transport explorer to support the "
            "demonstrator; scraped FSM, attendance and secondary "
            "performance metrics are shown where verified fields are "
            "available."
        ),
        "Support",
    )
    visual_scq_runner_flow()

    la_opts = safe_options(cfg, """
    MATCH (s:School)
    WITH DISTINCT coalesce(s.local_authority_name, s.local_authority, s.la) AS la
    WHERE la IS NOT NULL AND la <> ''
    RETURN la AS value, la AS label
    ORDER BY label
    LIMIT 100
    """)
    phase_opts = safe_options(cfg, """
    MATCH (s:School)
    WITH DISTINCT coalesce(s.phase_group, s.phase, s.school_type) AS phase
    WHERE phase IS NOT NULL AND phase <> ''
    RETURN phase AS value, phase AS label
    ORDER BY label
    LIMIT 100
    """)
    las = [("All", "All")] + la_opts
    phases = [("All", "All")] + phase_opts

    dep_options = [
        ("All", "All"),
        ("high_deprivation", "High"),
        ("medium_deprivation", "Medium"),
        ("low_deprivation", "Low"),
        ("unknown", "Unknown"),
    ]
    dep_choice = st.sidebar.selectbox(
        "Deprivation",
        dep_options,
        format_func=lambda x: x[1],
    )
    dep = dep_choice[0]
    dep_label = dep_choice[1]
    transport = st.sidebar.selectbox(
        "Transport access",
        [
            "All",
            "Near transport",
            "No transport stop within 800m",
        ],
        index=0,
        help=(
            "Near transport means at least one TransportStop is within "
            "800m. No transport stop within 800m means no stored "
            "DISTANCE_NEAR relation inside that threshold."
        ),
    )
    la = st.sidebar.selectbox("Local authority", las, format_func=lambda x: x[1])
    phase = st.sidebar.selectbox("School phase", phases, format_func=lambda x: x[1])
    st.sidebar.markdown("### School filters")
    school_option_filters = []
    school_option_params: Dict[str, Any] = {}
    if la[0] != "All":
        school_option_filters.append(
            "toLower(coalesce(s.local_authority_name, s.local_authority, '')) "
            "CONTAINS toLower($option_la)"
        )
        school_option_params["option_la"] = la[0]
    if phase[0] != "All":
        school_option_filters.append(
            "coalesce(s.phase_group, s.phase, s.school_type) = $option_phase"
        )
        school_option_params["option_phase"] = phase[0]
    school_option_where = (
        "WHERE " + " AND ".join(school_option_filters)
        if school_option_filters
        else ""
    )
    school_options = [("All", "All matching schools")]
    school_options += safe_options(
        cfg,
        f"""
        MATCH (s:School)
        {school_option_where}
        RETURN
            s.code AS value,
            coalesce(s.name, s.school_name, s.code)
            + coalesce(" | " + s.local_authority_name, "") AS label
        ORDER BY label
        LIMIT 1600
        """,
        school_option_params,
    )
    selected_school = st.sidebar.selectbox(
        "School",
        school_options,
        format_func=lambda x: x[1],
        help=(
            "Open the list and type part of the school name to search, "
            "or keep All matching schools."
        ),
    )
    with st.sidebar.expander("More filters: school metrics", expanded=False):
        fsm_min_text = st.text_input(
            "FSM minimum %",
            value="All",
            placeholder="All, or e.g. 30",
            help=(
                "Available FSM values in the loaded school data range from "
                "0.0% to 71.8%. Keep All for no FSM filter."
            ),
        )
        st.caption("Loaded range: 0.0%–71.8%. Use All for no FSM filter.")
        attendance_max_text = st.text_input(
            "Attendance maximum %",
            value="All",
            placeholder="All, or e.g. 90",
            help=(
                "Available attendance values in the loaded school data range "
                "from 79.1% to 98.1%. Keep All for no attendance filter."
            ),
        )
        st.caption("Loaded range: 79.1%–98.1%. Use All for no attendance filter.")
        capped9_max_text = st.text_input(
            "Capped 9 points maximum",
            value="All",
            placeholder="All, or e.g. 350",
            help=(
                "Capped 9 is a secondary-school points score, not a "
                "0-100 percentage. Available values range from 245.1 "
                "to 453.1. Keep All for no Capped 9 filter."
            ),
        )
        st.caption("Loaded range: 245.1–453.1 points. Use All for no Capped 9 filter.")

    def parse_optional_float(
        raw_value: str,
        field_name: str,
        minimum: float,
        maximum: float,
        unit: str,
    ) -> Tuple[float | None, bool]:
        text = str(raw_value).strip()
        if not text or text.lower() == "all":
            return None, True
        try:
            value = float(text)
        except ValueError:
            st.sidebar.error(f"{field_name}: enter a number or leave it blank for All.")
            return None, False
        if value < minimum or value > maximum:
            st.sidebar.error(
                f"{field_name}: {value:g}{unit} is outside the loaded data range "
                f"({minimum:g}{unit}–{maximum:g}{unit})."
            )
            return None, False
        return value, True

    fsm_min, fsm_ok = parse_optional_float(
        fsm_min_text,
        "FSM minimum",
        0.0,
        71.8,
        "%",
    )
    attendance_max, attendance_ok = parse_optional_float(
        attendance_max_text,
        "Attendance maximum",
        79.1,
        98.1,
        "%",
    )
    capped9_max, capped9_ok = parse_optional_float(
        capped9_max_text,
        "Capped 9 points maximum",
        245.1,
        453.1,
        "",
    )
    if not (fsm_ok and attendance_ok and capped9_ok):
        st.info("Fix the red metric filter message in the sidebar, or type All to remove that filter.")
        return

    conditions = ["s.latitude IS NOT NULL", "s.longitude IS NOT NULL"]
    params: Dict[str, Any] = {}
    if selected_school[0] != "All":
        conditions.append("s.code = $school_code")
        params["school_code"] = selected_school[0]
    if dep != "All":
        conditions.append("coalesce(l.deprivation, s.deprivation) = $dep")
        params["dep"] = dep
    if la[0] != "All":
        conditions.append("toLower(coalesce(s.local_authority_name, s.local_authority, l.local_authority, '')) CONTAINS toLower($la)")
        params["la"] = la[0]
    if phase[0] != "All":
        conditions.append("coalesce(s.phase_group, s.phase, s.school_type) = $phase")
        params["phase"] = phase[0]
    if fsm_min is not None:
        conditions.append("s.fsm_pct IS NOT NULL AND s.fsm_pct >= $min_fsm")
        params["min_fsm"] = fsm_min
    if attendance_max is not None and attendance_max < 100:
        conditions.append(
            "s.attendance_pct IS NOT NULL "
            "AND s.attendance_pct <= $max_attendance"
        )
        params["max_attendance"] = attendance_max
    if capped9_max is not None:
        conditions.append(
            "s.capped9_score IS NOT NULL "
            "AND s.capped9_score <= $max_capped9"
        )
        params["max_capped9"] = capped9_max
    if transport == "Near transport":
        conditions.append(
            "EXISTS { "
            "MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) "
            "}"
        )
    elif transport == "No transport stop within 800m":
        conditions.append(
            "NOT EXISTS { "
            "MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) "
            "}"
        )
    where = " AND ".join(conditions)

    count_cypher = f"""
    MATCH (s:School)
    OPTIONAL MATCH (s)-[:LOCATED_IN]->(l:LSOA)
    WITH s, l
    WHERE {where}
    RETURN
        count(DISTINCT s) AS total_schools,
        count(DISTINCT CASE
            WHEN EXISTS {{
                MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop)
            }}
            THEN s
        END) AS near_transport_schools,
        avg(s.fsm_pct) AS avg_fsm_pct,
        avg(s.attendance_pct) AS avg_attendance_pct
    """

    cypher = f"""
    MATCH (s:School)
    OPTIONAL MATCH (s)-[:LOCATED_IN]->(l:LSOA)
    WITH s, l
    WHERE {where}
    OPTIONAL MATCH (s)-[near_rel:DISTANCE_NEAR]->(:TransportStop)
    WITH
        s,
        l,
        min(near_rel.distance_m) AS nearest_stop_distance_m
    RETURN coalesce(s.name, s.school_name, s.code) AS school,
           coalesce(s.phase, s.school_type) AS school_type,
           coalesce(s.local_authority_name, s.local_authority, l.local_authority) AS local_authority,
           s.gender_mix AS gender_mix,
           s.language_medium AS language_medium,
           s.address AS address,
           s.postcode AS postcode,
           s.latitude AS latitude,
           s.longitude AS longitude,
           coalesce(s.pupils_2025, s.pupils) AS pupils,
           coalesce(l.deprivation, s.deprivation, 'unknown') AS deprivation,
           coalesce(l.wimd_decile, s.wimd_decile) AS wimd_decile,
           s.fsm_pct AS fsm_pct,
           s.attendance_pct AS attendance_pct,
           s.pupil_teacher_ratio AS pupil_teacher_ratio,
           s.budget_per_pupil_gbp AS budget_per_pupil_gbp,
           s.capped9_score AS capped9_score,
           s.literacy_score AS literacy_score,
           s.numeracy_score AS numeracy_score,
           s.science_score AS science_score,
           s.welsh_bacc_score AS welsh_bacc_score,
           nearest_stop_distance_m,
           nearest_stop_distance_m IS NOT NULL AS near_transport
    ORDER BY coalesce(s.fsm_pct, -1) DESC, school
    """
    try:
        summary_df = run_cypher(cfg, count_cypher, params)
        df = run_cypher(cfg, cypher, params)
    except Exception as e:
        st.error(f"Map query failed: {e}")
        return

    summary = (
        summary_df.iloc[0].to_dict()
        if not summary_df.empty
        else {}
    )
    c1, c2, c3, c4 = st.columns(4)
    total_schools = int(summary.get("total_schools") or 0)
    c1.metric("Schools matching filters", f"{total_schools:,}")
    c2.metric("Deprivation", dep_label)
    near_transport_count = int(summary.get("near_transport_schools") or 0)
    if transport == "No transport stop within 800m":
        transport_value = total_schools - near_transport_count
    elif transport == "Near transport":
        transport_value = total_schools
    else:
        transport_value = near_transport_count
    c3.metric("Transport", f"{transport_value:,}")
    avg_fsm = summary.get("avg_fsm_pct")
    c4.metric("Average FSM", f"{avg_fsm:.1f}%" if pd.notna(avg_fsm) else "N/A")

    if df.empty:
        st.info("No rows with coordinates after filtering.")
        st.code(cypher, language="cypher")
        return

    map_df = df.copy()
    map_df["latitude"] = pd.to_numeric(map_df["latitude"], errors="coerce")
    map_df["longitude"] = pd.to_numeric(map_df["longitude"], errors="coerce")
    map_df = map_df.dropna(subset=["latitude", "longitude"])
    if map_df.empty:
        st.info("No rows with valid map coordinates after filtering.")
        st.code(cypher, language="cypher")
        return

    render_school_map(map_df, selected_school)
    with st.expander("Map Cypher"):
        st.code(cypher, language="cypher")
        st.json(params)


def main() -> None:
    cfg = sidebar_config()
    apply_dashboard_theme(bool(cfg.get("dark_theme")))
    page = cfg.pop("page")
    if page == "Task Overview":
        page_task_overview(cfg)
    elif page == "Visual Story":
        page_visual_story()
    elif page == "Policy Questions":
        page_policy_questions()
    elif page == "SCQ Demonstrator":
        page_scq_demonstrator(cfg)
    elif page == "Evaluation":
        page_evaluation()
    elif page == "Cross-hierarchy":
        page_cross_hierarchy(cfg)
    elif page == "Map":
        page_map(cfg)


if __name__ == "__main__":
    main()
