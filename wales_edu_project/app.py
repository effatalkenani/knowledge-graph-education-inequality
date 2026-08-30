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

import base64
import json
import math
import os
import re
from html import escape
from typing import Any, Dict, List, Tuple

import pydeck as pdk
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================
# One switch for the whole app: when False, no Cypher query text, parameter
# dump, or query expander renders anywhere in the UI. The queries still run
# and still live in the code and the research log; this only controls display.
# Flip to True during development when the query text is needed on screen.
SHOW_QUERIES = False


APP_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Wales Education KG",
    page_icon=str(APP_DIR / "wales_education_kg.png"),
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem;}
.hero {
  background: linear-gradient(135deg,#5e0d1c,#9e1b32 55%,#b8283f);
  color: white; padding: 1.4rem 1.7rem; border-radius: 14px; margin-bottom: 1.1rem;
  box-shadow: 0 5px 18px rgba(94,13,28,.20);
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
.hero {background:linear-gradient(135deg,#5e0d1c,#9e1b32 55%,#b8283f); color:white; border:0; border-radius:14px; box-shadow:0 8px 20px rgba(94,13,28,.18);} 
.hero h1 {color:white;} .hero p {color:white; opacity:.94;}
div[data-testid="stSidebar"] {background:#f2f4f8; border-right:1px solid #d9dde7;}
div[data-testid="stSidebar"] button {
  border-radius:14px !important; border:1px solid #fed7aa !important;
  font-weight:800 !important; color:#431407 !important; background:#fffaf4 !important;
  min-height:2.5rem; transition:all .12s ease-in-out;
}
div[data-testid="stSidebar"] button:hover {transform:translateY(-1px); border-color:#fb923c !important; color:#9a3412 !important; box-shadow:0 5px 14px rgba(249,115,22,.12);}
div[data-testid="stSidebar"] button[kind="primary"] {background:linear-gradient(135deg,#ff4f79,#ff8a00) !important; border-color:#ff4f79 !important; color:white !important; box-shadow:0 6px 16px rgba(255,79,121,.16);} 

/* Range pairs (From/To) in the sidebar: force the two columns to sit side
   by side instead of wrapping, and slim the number inputs so they fit. */
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important; gap: .55rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
  min-width: 0 !important; flex: 1 1 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
  display: none !important;               /* hide +/- steppers: typing only */
}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
  padding: .3rem .5rem !important; font-size: .86rem !important;
}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] label {
  font-size: .74rem !important; margin-bottom: .12rem !important;
}

/* Sidebar radio groups (Search for, Cluster view): clean rectangular card.
   Overrides the segmented-pill CSS, which is meant for the horizontal
   language/direction toggles in the main area only. */
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
  display: flex !important; flex-direction: column !important;
  gap: 4px !important; width: 100%;
  background: var(--field-bg) !important;
  border: 1px solid var(--field-border) !important;
  border-radius: 10px !important; padding: 6px !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
  width: 100%; display: flex !important; align-items: center;
  border-radius: 7px !important; padding: .34rem .65rem !important;
  margin: 0 !important; cursor: pointer;
  transition: background .15s ease;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
  background: var(--option-hover) !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
  background: var(--accent-grad) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p {
  color: #ffffff !important; font-weight: 700;
}

/* Warmer field styling: amber-tinted borders and darker warm labels so the
   sidebar controls read as part of the theme rather than cold grey. */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div,
section[data-testid="stSidebar"] [data-testid="stNumberInput"] > div > div,
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div,
section[data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
  border: 1px solid var(--field-border) !important;
  border-radius: 8px !important;
  background: var(--field-bg) !important;
}
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div:focus-within,
section[data-testid="stSidebar"] [data-testid="stNumberInput"] > div > div:focus-within,
section[data-testid="stSidebar"] [data-testid="stTextInput"] > div > div:focus-within {
  border-color: var(--field-focus) !important;
  box-shadow: 0 0 0 2px var(--field-glow) !important;
}
section[data-testid="stSidebar"] label p {
  color: var(--field-label) !important; font-weight: 650 !important;
}
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background: var(--accent-grad) !important;
  color: #fff !important; border-radius: 6px !important;
}

/* Orange interactive details: carets, expander arrows, dropdown highlights,
   and switch tracks pick up the theme instead of default grey. */
section[data-testid="stSidebar"] [data-baseweb="select"] svg {
  color: var(--field-focus) !important; fill: var(--field-focus) !important;
}
[data-testid="stExpander"] summary svg {
  color: var(--field-focus) !important; fill: var(--field-focus) !important;
}
[data-testid="stExpander"] summary:hover {
  color: #9a3412 !important;
}
[data-baseweb="popover"] [role="option"]:hover {
  background: var(--option-hover) !important;
  color: var(--option-hover-text) !important;
}
[data-baseweb="popover"] [role="option"][aria-selected="true"] {
  background: var(--accent-grad) !important;
  color: #ffffff !important;
}
section[data-testid="stSidebar"] [role="switch"][aria-checked="true"] {
  background: var(--field-focus) !important;
}
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div:hover,
section[data-testid="stSidebar"] [data-testid="stNumberInput"] > div > div:hover,
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] > div > div:hover {
  border-color: var(--field-focus) !important;
}

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

def get_setting(name, default=None):
    value = os.getenv(name)

    if value:
        return value

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    return value or default

APP_MODE = os.getenv("APP_MODE", "CLOUD").upper()

if APP_MODE == "LOCAL":
    DEFAULT_URI = get_setting("LOCAL_NEO4J_URI")
    DEFAULT_USER = get_setting("LOCAL_NEO4J_USER")
    DEFAULT_PASSWORD = get_setting("LOCAL_NEO4J_PASSWORD")
    DEFAULT_DATABASE = get_setting("LOCAL_NEO4J_DATABASE")

elif APP_MODE == "CLOUD":
    DEFAULT_URI = get_setting("NEO4J_URI")
    DEFAULT_USER = get_setting("NEO4J_USER")
    DEFAULT_PASSWORD = get_setting("NEO4J_PASSWORD")
    DEFAULT_DATABASE = get_setting("NEO4J_DATABASE")

else:
    raise ValueError("APP_MODE must be either CLOUD or LOCAL")
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Complete",
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
        "status": "Dissertation phase",
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
# 3. SCQ3 implements the paper's cycle-free path definition of between over
#    LSOA_TOUCHES. The paper sets no numeric bound; unbounded enumeration is
#    intractable, so a hop bound is applied and reported as a tractability
#    necessity rather than a definitional choice.
# 4. SCQ5 and SCQ6 remain native administrative-hierarchy comparisons only.
#    They are not counted as independent Education Use Case answers because
#    Ward-LSOA containment-style questions were reclassified to SCQ7/SCQ8.

# =============================================================================
# BILINGUAL UI LABELS (English / Cymraeg)
# =============================================================================
# Coverage: sidebar controls, the SCQ7/SCQ8 direction toggle, and the labels
# of the Cross-hierarchy and SCQ Demonstrator tabs. Extend by adding keys to
# both dictionaries below; t() falls back to English for any missing key.
UI_TEXT: Dict[str, Dict[str, str]] = {
    "English": {
        "language": "Language / Iaith",
        "dark_theme": "Dark theme",
        "start_from": "Start comparison from",
        "dir_lsoa": "LSOA \u2192 results are Wards / Communities",
        "dir_admin": "Ward / Community \u2192 results are LSOAs",
        "direction_caption": (
            "The stored INTERSECTS relation is symmetric: both directions "
            "read the same facts, only the fixed side changes."
        ),
        "scq7_select_lsoa": "Select LSOA \u2014 returns intersecting wards/communities",
        "scq8_select_lsoa": "Select LSOA \u2014 returns nearby wards/communities",
        "scq7_select_admin": "Select Ward or Community \u2014 returns intersecting LSOAs",
        "scq8_select_admin": "Select Ward or Community \u2014 returns nearby LSOAs",
        "scq7_metric_admin": "Intersecting administrative units found",
        "scq8_metric_admin": "Nearby administrative units found",
        "scq7_metric_lsoa": "Intersecting LSOAs found",
        "scq8_metric_lsoa": "Nearby LSOAs found",
        "scq8_caption": (
            "Units that directly intersect the selected LSOA are "
            "excluded: near requires disjoint regions "
            "(IJGI 2024 definition)."
        ),
        "scq8_caption_admin": (
            "LSOAs that the selected unit directly intersects are "
            "excluded: near requires disjoint regions "
            "(IJGI 2024 definition)."
        ),
        "select_scq": "Select SCQ",
        "result_limit": "Result limit",
        "run_query": "Run SCQ query",
        "cypher_used": "Cypher used",
        "parameters": "Parameters",
        "admin_unit_label": "Administrative unit",
        "lsoa_label": "LSOA",
        "no_results_7": "No directly intersecting results were returned.",
        "no_results_8": "No cross-hierarchy proximity results were returned.",
        "tab_answer": "Answer \u2014 official result",
        "tab_evidence": "Evidence \u2014 pairs",
        "metric_pairs": "Evidence pairs found",
        "lsoa_a": "LSOA A",
        "lsoa_b": "LSOA B",
        "max_hops": "Maximum hops",
        "max_hops_note": (
            "Tractability bound chosen for this implementation \u2014 "
            "the paper sets no numeric limit."
        ),
        "scq3_interp": (
            "Between follows the IJGI 2024 definition: cycle-free paths "
            "over LSOA_TOUCHES. The hop bound is a tractability necessity, "
            "not part of the definition. 'Between clusters' still has no "
            "formal definition here, so the education-policy fit remains "
            "weak / optional."
        ),
        "no_path_note": (
            "No cycle-free path was found within the chosen hop bound "
            "\u2014 try two closer LSOAs."
        ),
        "guaranteed_example": "Guaranteed example:",
        "results_h": "Results",
        "relation_used": "Relation used",
        "provenance_h": "Provenance",
        "task_link": "Task link",
        "implemented_answer": "Implemented answer",
        "eval_status": "Evaluation status",
        "evidence_h": "Evidence",
        "eval_interp": "Evaluation interpretation",
        "show_query": "Show Cypher query",
        "q_SCQ1": "Which neighbouring LSOAs directly border the selected LSOA, and what school FSM / attendance / performance evidence is visible in those neighbouring areas?",
        "q_SCQ2": "Which LSOAs are qualitatively near the selected LSOA, and do nearby school indicators show FSM / attendance / secondary-performance pressure?",
        "q_SCQ3": "Which LSOAs lie between two selected LSOAs?",
        "q_SCQ4": "Which non-adjacent LSOAs show school FSM / attendance / secondary-performance pressure compared with the selected LSOA?",
        "q_SCQ5": "Which administrative parent units contain the selected administrative unit?",
        "q_SCQ6": "Which administrative units are contained inside the selected administrative unit?",
        "q_SCQ7": "Which wards or communities intersect the selected LSOA, and what school FSM / attendance / performance evidence is located in that LSOA?",
        "q_SCQ8": "Which wards or communities intersect LSOAs that are graph-near the selected LSOA, and what school indicators are visible in those nearby LSOAs?",
    },
    "Cymraeg": {
        "language": "Language / Iaith",
        "dark_theme": "Thema dywyll",
        "start_from": "Dechrau'r gymhariaeth o",
        "dir_lsoa": "LSOA \u2192 y canlyniadau yw Wardiau / Cymunedau",
        "dir_admin": "Ward / Cymuned \u2192 y canlyniadau yw LSOAs",
        "direction_caption": (
            "Mae'r berthynas INTERSECTS sydd wedi'i storio yn gymesur: "
            "mae'r ddau gyfeiriad yn darllen yr un ffeithiau."
        ),
        "scq7_select_lsoa": "Dewiswch LSOA \u2014 yn dychwelyd wardiau/cymunedau sy'n croestorri",
        "scq8_select_lsoa": "Dewiswch LSOA \u2014 yn dychwelyd wardiau/cymunedau cyfagos",
        "scq7_select_admin": "Dewiswch Ward neu Gymuned \u2014 yn dychwelyd LSOAs sy'n croestorri",
        "scq8_select_admin": "Dewiswch Ward neu Gymuned \u2014 yn dychwelyd LSOAs cyfagos",
        "scq7_metric_admin": "Unedau gweinyddol sy'n croestorri a ganfuwyd",
        "scq8_metric_admin": "Unedau gweinyddol cyfagos a ganfuwyd",
        "scq7_metric_lsoa": "LSOAs sy'n croestorri a ganfuwyd",
        "scq8_metric_lsoa": "LSOAs cyfagos a ganfuwyd",
        "scq8_caption": (
            "Mae unedau sy'n croestorri'n uniongyrchol \u00e2'r LSOA a "
            "ddewiswyd wedi'u heithrio: mae 'agos' yn gofyn am ranbarthau "
            "ar wah\u00e2n (diffiniad IJGI 2024)."
        ),
        "scq8_caption_admin": (
            "Mae LSOAs y mae'r uned a ddewiswyd yn croestorri \u00e2 nhw'n "
            "uniongyrchol wedi'u heithrio: mae 'agos' yn gofyn am "
            "ranbarthau ar wah\u00e2n (diffiniad IJGI 2024)."
        ),
        "select_scq": "Dewiswch SCQ",
        "result_limit": "Terfyn canlyniadau",
        "run_query": "Rhedeg ymholiad SCQ",
        "cypher_used": "Cypher a ddefnyddiwyd",
        "parameters": "Paramedrau",
        "admin_unit_label": "Uned weinyddol",
        "lsoa_label": "LSOA",
        "no_results_7": "Ni ddychwelwyd unrhyw ganlyniadau croestorri uniongyrchol.",
        "no_results_8": "Ni ddychwelwyd unrhyw ganlyniadau agosrwydd traws-hierarchaeth.",
        "tab_answer": "Ateb \u2014 y canlyniad swyddogol",
        "tab_evidence": "Tystiolaeth \u2014 parau",
        "metric_pairs": "Parau tystiolaeth a ganfuwyd",
        "lsoa_a": "LSOA A",
        "lsoa_b": "LSOA B",
        "max_hops": "Uchafswm naid",
        "max_hops_note": (
            "Ffin hydrinedd a ddewiswyd ar gyfer y gweithrediad hwn \u2014 "
            "nid yw'r papur yn gosod terfyn rhifiadol."
        ),
        "scq3_interp": (
            "Gweithredir 'rhwng' fel llwybrau syml di-gylch wedi'u ffinio "
            "dros LSOA_TOUCHES (llacio wedi'i ddogfennu); nid oes "
            "diffiniad ffurfiol o 'rhwng clystyrau' yma, felly adroddir "
            "bod y ffit polisi addysg yn wan / dewisol."
        ),
        "no_path_note": (
            "Ni chanfuwyd llwybr di-gylch o fewn y ffin naid a ddewiswyd "
            "\u2014 rhowch gynnig ar ddwy LSOA agosach."
        ),
        "guaranteed_example": "Enghraifft warantedig:",
        "results_h": "Canlyniadau",
        "relation_used": "Y berthynas a ddefnyddiwyd",
        "provenance_h": "Tarddiad",
        "task_link": "Cyswllt tasg",
        "implemented_answer": "Ateb a weithredwyd",
        "eval_status": "Statws gwerthuso",
        "evidence_h": "Tystiolaeth",
        "eval_interp": "Dehongliad gwerthuso",
        "show_query": "Dangos ymholiad Cypher",
        "q_SCQ1": "Pa LSOAs cyfagos sy'n ffinio'n uniongyrchol \u00e2'r LSOA a ddewiswyd, a pha dystiolaeth ysgolion (FSM / presenoldeb / perfformiad) sydd i'w gweld yn yr ardaloedd cyfagos hynny?",
        "q_SCQ2": "Pa LSOAs sy'n ansoddol agos at yr LSOA a ddewiswyd, ac a yw dangosyddion ysgolion cyfagos yn dangos pwysau FSM / presenoldeb / perfformiad uwchradd?",
        "q_SCQ3": "Pa LSOAs sy'n gorwedd rhwng dwy LSOA a ddewiswyd?",
        "q_SCQ4": "Pa LSOAs nad ydynt yn gyfagos sy'n dangos pwysau FSM / presenoldeb / perfformiad uwchradd o'u cymharu \u00e2'r LSOA a ddewiswyd?",
        "q_SCQ5": "Pa unedau gweinyddol rhiant sy'n cynnwys yr uned weinyddol a ddewiswyd?",
        "q_SCQ6": "Pa unedau gweinyddol sydd wedi'u cynnwys y tu mewn i'r uned weinyddol a ddewiswyd?",
        "q_SCQ7": "Pa wardiau neu gymunedau sy'n croestorri \u00e2'r LSOA a ddewiswyd, a pha dystiolaeth ysgolion sydd wedi'i lleoli yn yr LSOA honno?",
        "q_SCQ8": "Pa wardiau neu gymunedau sy'n croestorri ag LSOAs sy'n graff-agos at yr LSOA a ddewiswyd, a pha ddangosyddion ysgolion sydd i'w gweld yn yr LSOAs cyfagos hynny?",
    },
}

def t(key: str) -> str:
    """Return the UI label for the active language, falling back to English."""
    lang = st.session_state.get("ui_lang", "English")
    table = UI_TEXT.get(lang, UI_TEXT["English"])
    return table.get(key, UI_TEXT["English"].get(key, key))

def scq_question(scq_key: str, meta: Dict[str, Any]) -> str:
    """Return the SCQ question in the active language."""
    if st.session_state.get("ui_lang") == "Cymraeg":
        return UI_TEXT["Cymraeg"].get(f"q_{scq_key}", meta["question"])
    return meta["question"]

# Segmented-pill styling shared by the language switch and direction toggle.
_SEGMENTED_CSS = """
<style>
div[data-testid="stRadio"] > div[role="radiogroup"]{
    display:inline-flex; gap:4px;
    background:rgba(120,113,108,.14);
    border:1px solid rgba(120,113,108,.20);
    border-radius:999px; padding:4px 6px;
}
div[data-testid="stRadio"] label{
    border-radius:999px; padding:.28rem 1rem; margin:0 !important;
    transition:background .25s ease, box-shadow .25s ease;
    cursor:pointer;
}
div[data-testid="stRadio"] label > div:first-child{ display:none; }
div[data-testid="stRadio"] label:has(input:checked){
    background:linear-gradient(135deg,#9a3412,#c2410c);
    box-shadow:0 2px 8px rgba(154,52,18,.35);
}
div[data-testid="stRadio"] label:has(input:checked) p{
    color:#ffffff !important; font-weight:700;
}
</style>
"""

def inject_segmented_css() -> None:
    st.markdown(_SEGMENTED_CSS, unsafe_allow_html=True)

def direction_toggle(widget_key: str) -> str:
    """
    Sleek two-option segmented control for SCQ7/SCQ8.
    Returns "lsoa" (default) or "admin". Both directions read the same
    stored INTERSECTS facts; only the fixed side of the pair changes.
    """
    inject_segmented_css()
    return st.radio(
        t("start_from"),
        options=["lsoa", "admin"],
        format_func=lambda v: t("dir_lsoa") if v == "lsoa" else t("dir_admin"),
        horizontal=True,
        key=widget_key,
    )

# =============================================================================
# CROSS-HIERARCHY REVERSED QUERIES (single source of truth for BOTH tabs)
# =============================================================================
SCQ7_REVERSE_CYPHER = """
MATCH (admin:AdminUnit {uri:$admin})-[:INTERSECTS]->(l:LSOA)
OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
WITH
    admin,
    l,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score
RETURN
    l.code AS lsoa_code,
    coalesce(l.name, l.LSOA_Name, l.code) AS lsoa_name,
    l.wimd_decile AS wimd_decile,
    l.deprivation AS deprivation,
    coalesce(admin.name, admin.uri) AS administrative_unit,
    admin.type AS administrative_type,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score
ORDER BY lsoa_code
LIMIT $limit
"""

SCQ8_REVERSE_CYPHER = """
MATCH (admin:AdminUnit {uri:$admin})-[:INTERSECTS]->(base:LSOA)
MATCH (base)-[:GRAPH_NEAR]-(near_lsoa:LSOA)
// Near requires disjoint regions (IJGI 2024 definition):
// exclude LSOAs that the selected unit directly intersects.
WHERE NOT (admin)-[:INTERSECTS]->(near_lsoa)
OPTIONAL MATCH (near_lsoa)<-[:LOCATED_IN]-(s:School)
WITH
    near_lsoa,
    collect(DISTINCT base.code) AS via_base_lsoas,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score
RETURN
    near_lsoa.code AS lsoa_code,
    coalesce(near_lsoa.name, near_lsoa.LSOA_Name, near_lsoa.code)
        AS lsoa_name,
    near_lsoa.wimd_decile AS wimd_decile,
    near_lsoa.deprivation AS deprivation,
    via_base_lsoas,
    size(via_base_lsoas) AS supporting_lsoas,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score
ORDER BY avg_school_fsm_pct DESC, lsoa_code
LIMIT $limit
"""

# SCQ3: cycle-free paths over LSOA_TOUCHES, per the paper's definition. The
# hop bound is a tractability necessity, not part of the definition.
SCQ3_CYPHER_TEMPLATE = """
// Between, per the IJGI 2024 definition (Section 3.4): a region lies between
// two others when it sits on a path linking them, where the path contains no
// cycles or parts of cycles. The cycle-free condition is the WHERE clause.
// The paper sets no numeric bound, but enumerating unbounded simple paths in
// a 1,909-node / 5,255-edge graph is combinatorially intractable, so a hop
// bound is applied as a tractability necessity and reported as such.
MATCH
    (a:LSOA {code:$lsoa_a}),
    (b:LSOA {code:$lsoa_b})

MATCH p = (a)-[:LSOA_TOUCHES*2..__MAXHOPS__]-(b)

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
"""

# The same definition over the administrative hierarchy. The only changes are
# the node label, the key property and the relationship: TOUCHES between
# AdminUnit nodes is asserted by YAGO2geo itself, so this variant answers the
# identical question through a NATIVE relation, while the LSOA variant above
# has to walk adjacency that was computed from geometry. Running one form over
# both hierarchies is what makes the provenance contrast visible.
SCQ3_ADMIN_CYPHER_TEMPLATE = """
MATCH
    (a:AdminUnit {uri:$lsoa_a}),
    (b:AdminUnit {uri:$lsoa_b})

MATCH p = (a)-[:TOUCHES*2..__MAXHOPS__]-(b)

WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))

RETURN
    length(p) AS hops,
    [
        n IN nodes(p)[1..-1] |
        {
            code: n.uri,
            name: coalesce(n.name, n.uri),
            deprivation: null,
            wimd_decile: null
        }
    ] AS between_lsoas
ORDER BY hops
"""


# SCQ8 official ANSWER (grouped per administrative unit) and its
# pair-level EVIDENCE, in both directions. Single source of truth for
# the Cross-hierarchy page AND the SCQ Demonstrator.
SCQ8_ANSWER_CYPHER = """
MATCH (x:LSOA {code:$lsoa})
    -[:GRAPH_NEAR]-(near_lsoa:LSOA)

MATCH (admin:AdminUnit)-[:INTERSECTS]->(near_lsoa)
WHERE admin.type IN ['Ward', 'Community']
  // Near requires disjoint regions (IJGI 2024 definition):
  // exclude units that directly intersect the selected LSOA.
  AND NOT (admin)-[:INTERSECTS]->(x)
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

SCQ8_EVIDENCE_CYPHER = """
MATCH (x:LSOA {code:$lsoa})-[:GRAPH_NEAR]-(near_lsoa:LSOA)
MATCH (admin:AdminUnit)-[:INTERSECTS]->(near_lsoa)
WHERE admin.type IN ['Ward', 'Community']
  // Near requires disjoint regions (IJGI 2024 definition):
  // exclude units that directly intersect the selected LSOA.
  AND NOT (admin)-[:INTERSECTS]->(x)
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
"""

SCQ8_REVERSE_EVIDENCE_CYPHER = """
MATCH (admin:AdminUnit {uri:$admin})-[:INTERSECTS]->(base:LSOA)
MATCH (base)-[:GRAPH_NEAR]-(near_lsoa:LSOA)
// Near requires disjoint regions (IJGI 2024 definition):
// exclude LSOAs that the selected unit directly intersects.
WHERE NOT (admin)-[:INTERSECTS]->(near_lsoa)
OPTIONAL MATCH (near_lsoa)<-[:LOCATED_IN]-(s:School)
WITH
    base,
    near_lsoa,
    count(DISTINCT s) AS school_count,
    avg(s.fsm_pct) AS avg_fsm_pct,
    avg(s.attendance_pct) AS avg_attendance_pct,
    avg(s.capped9_score) AS avg_capped9_score
RETURN DISTINCT
    near_lsoa.code AS lsoa_code,
    coalesce(near_lsoa.name, near_lsoa.LSOA_Name, near_lsoa.code)
        AS lsoa_name,
    near_lsoa.wimd_decile AS wimd_decile,
    near_lsoa.deprivation AS deprivation,
    base.code AS via_lsoa_code,
    coalesce(base.name, base.LSOA_Name, base.code) AS via_lsoa_name,
    school_count,
    round(avg_fsm_pct, 1) AS avg_school_fsm_pct,
    round(avg_attendance_pct, 1) AS avg_school_attendance_pct,
    round(avg_capped9_score, 1) AS avg_secondary_capped9_score
ORDER BY avg_school_fsm_pct DESC, lsoa_code
LIMIT $limit
"""

# Supervisor's baseline table applied per question: the answering MODE and its
# geometric cost, kept separate from the provenance triad. Provenance answers
# "where did the relation come from"; mode answers "how was it computed and
# what did it cost". Only Native counts toward model completeness.
def hl(text: str) -> str:
    """Mark the words in a quotation that carry the warrant.

    Highlighting is a reading aid, not an edit: the quotation stays verbatim
    and only its decisive terms are picked out, so a reader can see at a
    glance which words justify the question.
    """
    return (
        "<mark style='background:rgba(234,88,12,.22);"
        "padding:0 3px;border-radius:3px;'>" + text + "</mark>"
    )


# Literature grounding, quoted verbatim with page numbers, so each question
# shows the published finding that makes it a real analyst question rather
# than a template fitted to the instrument. Sandu et al. supply the WARRANT
# for asking; their statistical method (Moran's I, hot-spot analysis, GWR)
# is a different
# notion of proximity and is deliberately NOT imported.
SCQ_WARRANT = {
    "SCQ1": {
        "quote": (
            "Moran's I value (0.30, p &lt; 0.001) confirmed "
            + hl("spatial clustering")
            + " of educational outcomes."
        ),
        "page": "2026, p. 8",
        "quote2": (
            hl("10% higher eFSM")
            + " corresponds to CSI achievement rates being "
            + hl("2.96% lower") + "."
        ),
        "page2": "2026, p. 7, Table 3",
        "why": (
            "The question is <b>derived from</b> these findings rather than "
            "quoted from them: the paper reports results, not question "
            "forms. The first warrants the <b>form</b> — because outcomes "
            "cluster spatially, adjacency is a meaningful unit of "
            "analysis, so asking which areas adjoin a given area follows "
            "from the literature even though it is not posed there in "
            "these terms. The second warrants the <b>content</b> — free "
            "school meal eligibility is the strongest negative predictor "
            "in that analysis, which is why FSM is the evidence surfaced "
            "for each neighbouring area."
        ),
        "method_note": (
            "Sandu et al. (2026) measure the strength of that clustering "
            "statistically; this demonstrator asks only whether the graph "
            "can identify the neighbours at all, so their spatial-weights "
            "proximity is a third notion of nearness and stays outside the "
            "completeness scoring. Their analysis also uses pupil-level "
            "CSI attainment, which this graph does not hold, so "
            "school-level indicators stand in — the authors state that "
            "school-level characteristics were excluded from their "
            "small-area measures because they are recorded at a different "
            "granularity (2026, p. 4), so the two levels are complementary "
            "rather than equivalent."
        ),
    },
    "SCQ2": {
        "quote": (
            hl("Statistically significant clusters")
            + " of low proportions (cold spots shown in blue) and high "
            + "proportions (hot spots shown in red) are "
            + hl("evident across the country") + "."
        ),
        "page": "2026, p. 8",
        "why": (
            "This finding warrants only part of the question. It "
            "establishes that clusters of low and high attainment exist "
            "across Wales, so a question about clusters is about something "
            "real rather than hypothetical. It does <b>not</b> warrant the "
            "proximity element: the paper classifies areas as inside or "
            "outside a cluster and never asks what lies near one."
        ),
        "method_note": (
            "The near relation comes from the evaluation instrument, not "
            "from this paper: two regions are near when they are disjoint "
            "and joined by a path of two touches edges. Their clusters are "
            "statistical, from hot-spot analysis of the Gi* statistic; the "
            "clusters here are connected components of adjacency — the "
            "same word, a different construct, and their spatial-weights "
            "proximity stays outside the completeness scoring."
        ),
    },
    "SCQ4": {
        "quote": (
            hl("10% higher deprivation")
            + " corresponding to achievement rates being "
            + hl("1.94% lower") + "."
        ),
        "page": "2026, p. 7, Table 3",
        "why": (
            "This finding warrants the <b>content</b> only: deprivation is "
            "associated with attainment, so the deprivation profile of the "
            "areas returned is what makes the answer informative. The "
            "<b>form</b> is not warranted by this paper — a "
            "non-adjacency question is not posed there. It comes from the "
            "evaluation instrument, where not-touches is the complement of "
            "touches and is included so that all eight forms are exercised."
        ),
        "method_note": (
            "The complement of a small neighbour set is almost the whole "
            "country: for a typical LSOA the answer is about 1,900 of "
            "1,909 areas. The count is therefore reported in full while "
            "the map draws a sample, and the result is read as a property "
            "of the form rather than as a policy finding."
        ),
    },
    "SCQ7": {
        "quote": (
            hl("10% higher eFSM")
            + " corresponds to CSI achievement rates being "
            + hl("2.96% lower") + "."
        ),
        "page": "2026, p. 7, Table 3",
        "quote2": (
            hl("All four forms of household deprivation")
            + " as measured by the Census dataset were "
            + hl("negatively associated")
            + " with pupils' achieving the CSI."
        ),
        "page2": "2026, p. 7",
        "why": (
            "Derived from, not quoted from, these findings. The first "
            "warrants the <b>form</b>: free-school-meal eligibility is the "
            "strongest negative predictor at LSOA level, so linking a "
            "school to the statistical area it sits in is central to the "
            "use case. The second warrants the <b>content</b>: deprivation acts through several dimensions "
            "at once, which is why the intersected area's WIMD profile is "
            "returned alongside the school indicators."
        ),
        "method_note": (
            "Their analysis is OLS regression at LSOA level; this asks "
            "only whether the graph can make the cross-hierarchy link."
        ),
    },
    "SCQ8": {
        "quote": (
            "10% higher ... SEN ... related to achievement rates being "
            "2.93% lower."
        ),
        "page": "2026, p. 7, Table 3",
        "quote2": (
            "The spatial analysis highlights "
            + hl("significant variations")
            + " in how these factors impact attainment "
            + hl("across Wales") + "."
        ),
        "page2": "2026, p. 1",
        "why": (
            "Derived from, not quoted from, these findings. The first "
            "warrants the <b>form</b>: disadvantage indicators vary across "
            "small geographies, so reaching nearby administrative units "
            "from a statistical one is a genuine analytical need. The "
            "second warrants the <b>content</b>: "
            "because the effect of those factors is not uniform across "
            "Wales, the indicators of nearby areas — not national averages "
            "— are what an analyst needs to see."
        ),
        "method_note": (
            "SEN is not held in this graph, so school-level indicators "
            "stand in. The warrant is the spatial variation of "
            "disadvantage, not the SEN measure itself."
        ),
    },
}

# Three SCQ forms carry no warrant from the education-inequality
# literature. They are recorded here with the reason left visible rather
# than filled with a manufactured question, because an honest empty cell is
# itself a finding about the fit between the instrument and the domain.
SCQ_NO_WARRANT = {
    "SCQ3": {
        "status": "No natural question in this domain",
        "reason": (
            "Sandu et al. pose no \"between\" question, and the wider "
            "education-inequality literature for Wales frames disadvantage "
            "in terms of concentration and gradient rather than "
            "betweenness. An analyst asks where disadvantage clusters, not "
            "which area lies between two others."
        ),
        "consequence": (
            "The form is implemented and executable, so the instrument is "
            "exercised in full, but its policy fit is recorded as weak "
            "rather than manufactured into a question the literature does "
            "not ask."
        ),
    },
    "SCQ5": {
        "status": "Not applicable to the education use case",
        "reason": (
            "Containment questions in this use case would run from ward to "
            "LSOA, but LSOAs do not nest inside wards — they intersect "
            "them. The form is therefore reclassified to SCQ7 rather than "
            "answered here."
        ),
        "consequence": (
            "SCQ5 is demonstrated over the native administrative hierarchy "
            "instead, where containment genuinely holds. It stays in the "
            "eight-question denominator; dropping it would flatter the "
            "score."
        ),
    },
    "SCQ6": {
        "status": "Not applicable to the education use case",
        "reason": (
            "The inverse of SCQ5, and reclassified for the same reason: "
            "statistical geography does not nest inside administrative "
            "geography."
        ),
        "consequence": (
            "Demonstrated over the native administrative hierarchy and "
            "retained in the denominator."
        ),
    },
}


SANDU_REFERENCE = (
    "Sandu, A. et al. 2026. Mapping educational inequalities in Wales: "
    "spatial and socio-economic determinants of pupils' attainment. "
    "<i>Population, Space and Place</i> 32(2), e70225. "
    "doi: 10.1002/psp.70225"
)


# =============================================================================
# TASK 3 EVIDENCE — the warrant document, per question
# =============================================================================
# One entry per SCQ, holding exactly what the Task 3 document holds: the
# instantiated question, the warrant rows with their verbatim quotations and
# pages, the critical assessment, and the analyst questions the relation
# supports. Kept as data rather than prose so the demonstrator and the
# document cannot drift apart.
#
# Only two sources meet the scope set by the supervisor — Welsh and concerned
# with educational attainment. Where a row reads NO WARRANT FOUND the source
# was examined and nothing supporting was located; the cell stays empty rather
# than being filled with an adjacent concept.

SCQ_EVIDENCE: Dict[str, Dict[str, Any]] = {
    "SCQ1": {
        "short": "Touches",
        "instantiation": (
            "Which LSOAs directly border a selected LSOA, and what WIMD / "
            "school FSM / attendance / performance evidence is visible in "
            "those neighbouring areas?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "implying that "
                    + hl("neighbouring areas")
                    + " are more likely to have similar educational outcomes"
                ),
                "page": "p. 11",
                "warrant": (
                    "<b>FORM:</b> warrants the analytical significance of "
                    "neighbouring areas (direct adjacency). "
                    "<b>CONTENT:</b> identifies educational outcomes as the "
                    "relevant variable."
                ),
                "verdict": "Partial",
                "verdict_note": (
                    "Warrants general adjacency, not the specific "
                    "topological touches boundary"
                ),
            },
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "Moran&rsquo;s I value (0.30, p &lt; 0.001) confirmed "
                    + hl("spatial clustering")
                    + " of educational outcomes."
                ),
                "page": "p. 8",
                "warrant": (
                    "<b>FORM:</b> statistical warrant for spatial clustering, "
                    "which implies that adjacent regions share "
                    "characteristics. <b>CONTENT:</b> warrants educational "
                    "outcomes."
                ),
                "verdict": "Partial",
                "verdict_note": (
                    "Clustering and autocorrelation are a statistical proxy "
                    "for adjacency"
                ),
            },
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    hl("eFSM")
                    + " demonstrates substantial spatial variation "
                    "(GWR: &minus;0.55 to 0.01; OLS: &minus;0.30)"
                ),
                "page": "p. 9",
                "warrant": (
                    "<b>CONTENT:</b> warrants the use of eFSM as a critical "
                    "variable for spatial analysis."
                ),
                "verdict": "Partial",
                "verdict_note": "Warrants the content variable only",
            },
        ],
        "assessment": (
            "The literature provides strong warrants for the analytical "
            "importance of neighbouring areas and for variables such as eFSM "
            "and educational outcomes. The support is partial because the "
            "paper works through statistical clustering, or through "
            "neighbouring areas in a general sense, rather than the specific "
            "topological touches relation the SCQ framework defines."
        ),
        "questions": [
            "Which LSOAs directly border the selected LSOA?",
            "What are the deprivation levels of the directly neighbouring "
            "LSOAs?",
            "Which neighbouring LSOAs have the highest school FSM levels?",
            "Which neighbouring LSOAs have low school attendance?",
            "How does secondary-school performance differ across directly "
            "neighbouring LSOAs?",
            "Do directly neighbouring LSOAs have similar or contrasting WIMD "
            "profiles?",
        ],
    },
    "SCQ2": {
        "short": "Near",
        "instantiation": (
            "Which LSOAs are near a selected LSOA \u2014 disjoint but joined "
            "by a path of two touches edges \u2014 and what are the WIMD / "
            "FSM / attendance / performance profiles of these extended "
            "neighbours?"
        ),
        "rows": [
            {
                "source": "Bandyopadhyay et al. (2023)",
                "quote": (
                    "higher " + hl("access to services")
                    + ", were more likely to achieve PLP than their peers"
                ),
                "page": "p. 1",
                "warrant": (
                    "<b>CONTENT:</b> an ADR Wales study of 159,131 Welsh "
                    "pupils finding access to services significantly "
                    "associated with attainment for FSM children "
                    "(aOR 1.26, 95% CI 1.07&ndash;1.48; p. 8, Table 4). "
                    "Proximity is warranted as a variable that matters for "
                    "educational outcomes in Wales. The measure is a "
                    "composite accessibility index, not a topological "
                    "relation, so the <b>FORM</b> remains unwarranted."
                ),
                "verdict": "Partial",
                "verdict_note": "Warrants content only",
            },
        ],
        "assessment": (
            "The content of this question is warranted and its form is not. "
            "Bandyopadhyay et al. establish that accessibility matters for "
            "attainment in Wales, which is what makes the profiles returned "
            "here worth reading. Their measure, however, is a composite "
            "accessibility index built from travel times, while this question "
            "asks which regions are reachable in two touches-steps. The same "
            "word, near, carries a metric meaning in that literature and a "
            "topological one in the instrument."
        ),
        "questions": [
            "Which LSOAs are graph-near the selected LSOA?",
            "Which graph-near LSOAs are highly deprived?",
            "Which graph-near LSOAs show high FSM levels?",
            "Do graph-near LSOAs show low attendance or low secondary "
            "performance?",
            "How do the educational profiles of graph-near LSOAs compare with "
            "the selected LSOA?",
        ],
    },
    "SCQ3": {
        "short": "Between",
        "instantiation": (
            "Which LSOA lies on a cycle-free path between LSOA X and LSOA Y, "
            "and what are the WIMD / FSM / attendance / performance profiles "
            "of these intermediate LSOAs?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": None,
                "warrant": "No betweenness relation is defined.",
                "verdict": "None",
            },
            {
                "source": "Bandyopadhyay et al. (2023)",
                "quote": None,
                "warrant": "No betweenness relation is defined.",
                "verdict": "None",
            },
        ],
        "assessment": (
            "Neither source poses a question about a region lying between "
            "two others."
        ),
        "questions": [
            "Which LSOAs lie between LSOA X and LSOA Y?",
            "What is the shortest cycle-free path between two selected "
            "LSOAs?",
            "Which intermediate LSOAs on the path are highly deprived?",
            "Does the path between two areas pass through contrasting "
            "deprivation contexts?",
        ],
    },
    "SCQ4": {
        "short": "Not-adjacent",
        "instantiation": (
            "Which LSOAs do NOT share a boundary with a selected LSOA, and "
            "what are the WIMD / FSM / attendance / performance profiles of "
            "these non-adjacent LSOAs?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": None,
                "warrant": "No non-adjacency relation is defined.",
                "verdict": "None",
            },
            {
                "source": "Bandyopadhyay et al. (2023)",
                "quote": None,
                "warrant": "No non-adjacency relation is defined.",
                "verdict": "None",
            },
        ],
        "assessment": (
            "Neither source attaches analytical meaning to the complement of "
            "adjacent areas."
        ),
        "questions": [
            "Which LSOAs are not adjacent to the selected LSOA?",
            "Which non-adjacent LSOAs have high FSM levels?",
            "Which non-adjacent LSOAs have low attendance?",
            "Which non-adjacent LSOAs have similar deprivation profiles to "
            "the selected LSOA?",
            "Are there non-adjacent areas with worse secondary performance "
            "than the selected area?",
        ],
    },
    "SCQ5": {
        "short": "Contains",
        "instantiation": (
            "Which LSOAs are contained within a selected administrative unit "
            "\u2014 a Ward or a Unitary Authority \u2014 and what are the "
            "WIMD / FSM / attendance / performance profiles of these LSOAs?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "spatial analysis is undertaken at the "
                    + hl("LSOA level")
                ),
                "page": "p. 4",
                "warrant": (
                    "<b>FORM:</b> implies LSOAs are the small-area units "
                    "within the study area."
                ),
                "verdict": "Partial",
                "verdict_note": (
                    "Warrants the scale, not the specific hierarchical "
                    "containment"
                ),
            },
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "the final linked dataset consisted of data on 31,295 "
                    "pupils, and 1,625 LSOAs."
                ),
                "page": "p. 4",
                "warrant": (
                    "<b>CONTENT:</b> warrants the use of LSOAs as the primary "
                    "unit for measuring pupil data."
                ),
                "verdict": "Partial",
                "verdict_note": "Warrants content only",
            },
        ],
        "assessment": (
            "Containment is used here to define the scope of the study and "
            "the scale of analysis rather than to warrant a strict "
            "hierarchical query. LSOAs in any case intersect administrative "
            "units more often than they nest inside them, which makes strict "
            "containment difficult to warrant from this source."
        ),
        "questions": [
            "Which administrative parent contains the selected Ward?",
            "Which administrative parent contains the selected Community?",
            "Which Unitary Authority contains this Ward?",
            "What is the administrative parent chain of the selected unit?",
        ],
    },
    "SCQ6": {
        "short": "Within",
        "instantiation": (
            "Which administrative units \u2014 Wards or Unitary Authorities "
            "\u2014 contain a selected LSOA, and what are the WIMD / FSM / "
            "attendance / performance profiles of those containing units?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "revealed that schools in more "
                    + hl("affluent areas")
                    + " often outperformed"
                ),
                "page": "p. 2",
                "warrant": (
                    "<b>FORM:</b> implies schools, and by extension LSOAs, "
                    "are within areas. <b>CONTENT:</b> warrants school "
                    "performance and affluence."
                ),
                "verdict": "Partial",
                "verdict_note": "Within is used loosely here",
            },
        ],
        "assessment": (
            "Where within appears it is approximate regional belonging rather "
            "than topological nesting \u2014 consistent with LSOAs being "
            "statistical units that do not follow administrative boundaries."
        ),
        "questions": [
            "Which Wards are contained within the selected Unitary Authority?",
            "Which Communities are contained within the selected "
            "administrative unit?",
            "What administrative units are nested inside this authority?",
            "How is the selected administrative unit decomposed into "
            "lower-level units?",
        ],
    },
    "SCQ7": {
        "short": "Intersects",
        "instantiation": (
            "Which administrative units \u2014 Wards or Communities \u2014 "
            "intersect a selected LSOA, and how do the administrative-level "
            "variables compare to the LSOA-level WIMD / FSM / attendance / "
            "performance?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "school-level characteristics &hellip; recorded at a "
                    + hl("different granularity")
                    + " were not included into these small-area measures."
                ),
                "page": "p. 4",
                "warrant": (
                    "<b>FORM:</b> warrants the analytical challenge of "
                    "different granularity, which is what justifies a "
                    "cross-hierarchy query. <b>CONTENT:</b> warrants "
                    "small-area variables."
                ),
                "verdict": "Partial",
                "verdict_note": (
                    "Warrants the need to cross levels, not the intersect "
                    "relation itself"
                ),
            },
            {
                "source": "Sandu et al. (2026)",
                "quote": (
                    "Relying solely on administrative units such as school "
                    "districts or LSOAs may therefore "
                    + hl("obscure fine-grained variations")
                ),
                "page": "p. 3",
                "warrant": (
                    "<b>FORM:</b> warrants the need to move between "
                    "administrative units and LSOAs."
                ),
                "verdict": "Partial",
                "verdict_note": "Warrants cross-hierarchy enquiry",
            },
            {
                "source": "Bandyopadhyay et al. (2023)",
                "quote": (
                    hl("multilevel modelling")
                    + " at various levels such as &ndash; LSOA, household "
                    "and school"
                ),
                "page": "Discussion",
                "warrant": (
                    "<b>FORM:</b> identifies aggregated single-level analysis "
                    "as a limitation of its own design and calls explicitly "
                    "for modelling across LSOA, household and school. The "
                    "specific intersect relation between administrative and "
                    "statistical units is not named."
                ),
                "verdict": "Partial",
                "verdict_note": (
                    "Warrants cross-level integration, not the intersect "
                    "relation"
                ),
            },
        ],
        "assessment": (
            "This is the strongest warranted form. The two quotations from "
            "Sandu et al. work as a pincer: the first shows that folding one "
            "level of data into another at a different granularity fails, "
            "which is a technical necessity, while the second argues that "
            "relying on a single hierarchy obscures critical variation, which "
            "is an analytical one. The third row adds a second, independent "
            "ADR Wales study naming the same need as a limitation of its own "
            "work, so the requirement this question addresses is one the "
            "field states about itself. What the literature warrants is the "
            "need to work across levels; the intersect relation that meets "
            "that need is supplied by geometry. The sources give the reason, "
            "the knowledge graph gives the mechanism."
        ),
        "questions": [
            "Which Wards or Communities intersect the selected LSOA?",
            "Which LSOAs intersect the selected Ward or Community?",
            "Which administrative units intersect highly deprived LSOAs?",
            "Which Wards or Communities intersect LSOAs with high school FSM?",
            "Which administrative units intersect LSOAs with low attendance?",
            "Which administrative units intersect LSOAs with low "
            "secondary-school performance?",
            "How do school indicators vary across LSOAs intersecting the same "
            "administrative unit?",
        ],
    },
    "SCQ8": {
        "short": "Cross-near",
        "instantiation": (
            "Which administrative units are near, but disjoint from, a "
            "selected LSOA, and what are their WIMD / FSM / attendance / "
            "performance profiles compared to the LSOA?"
        ),
        "rows": [
            {
                "source": "Sandu et al. (2026)",
                "quote": None,
                "warrant": (
                    "No nearness relation between areas is defined."
                ),
                "verdict": "None",
            },
            {
                "source": "Bandyopadhyay et al. (2023)",
                "quote": None,
                "warrant": (
                    "No nearness relation between areas is defined."
                ),
                "verdict": "None",
            },
        ],
        "assessment": (
            "Neither source defines a proximity relation between "
            "administrative and statistical units."
        ),
        "questions": [
            "Which Wards or Communities are near, but do not intersect, the "
            "selected LSOA?",
            "Which LSOAs are near, but do not intersect, the selected Ward or "
            "Community?",
            "Which nearby administrative units are connected to highly "
            "deprived LSOAs?",
            "Which nearby administrative units are associated with LSOAs "
            "showing high FSM?",
            "Which nearby areas show low attendance or low secondary "
            "performance?",
            "Do nearby but non-intersecting administrative areas show similar "
            "or contrasting education profiles?",
        ],
    },
}


TASK3_REFERENCES = [
    "Sandu, A., Huxley, K., Keating, J., Whiffen, T., &amp; French, R. "
    "(2026). Mapping Educational Inequalities in Wales: Spatial and "
    "Socio-Economic Determinants of Pupils&rsquo; Attainment. "
    "<i>Population, Space and Place</i> 32:e70225. doi: 10.1002/psp.70225",
    "Bandyopadhyay, A., Whiffen, T., Fry, R., &amp; Brophy, S. (2023). How "
    "does the local area deprivation influence life chances for children in "
    "poverty in Wales: a record linkage cohort study. "
    "<i>SSM &ndash; Population Health</i> 22, 101370. "
    "doi: 10.1016/j.ssmph.2023.101370",
]


# =============================================================================
# NATURAL-LANGUAGE QUERY ENGINE
# =============================================================================
# Rule-based rather than model-backed, and deliberately so. A spatial
# competency question has an exact definition, and the scorecard measures that
# definition; a parser that sometimes reads "near" as distance and sometimes
# as two touches-steps would put noise inside the instrument. A rule table is
# also deterministic, needs no API key, runs offline, and can be inspected by
# a marker who has no credentials of ours.
#
# The engine reports what it matched, so the reader can see the reasoning
# rather than trust it: which relation was recognised, on what evidence, and
# what was left undecided.

# Order matters. Negations and compound forms are tested before the simple
# forms they contain: "not adjacent" before "adjacent", "near but not
# intersecting" before "near", "intersect" before everything that mentions an
# administrative unit.
NL_RELATION_RULES: List[Tuple[str, List[str], str]] = [
    (
        "SCQ8",
        [
            "near but do not intersect", "near, but do not intersect",
            "near but not intersect", "cross-near", "cross near",
            "nearby administrative", "nearby but non-intersecting",
            "nearby areas", "agos ond heb groestorri",
        ],
        "near(AdminUnit) AND NOT intersects",
    ),
    (
        "SCQ4",
        [
            "not adjacent", "non-adjacent", "not share a boundary",
            "do not share", "not border", "not touching", "nid yw'n ffinio",
            "heb ffinio",
        ],
        "NOT touches(LSOA)",
    ),
    (
        "SCQ7",
        [
            "intersect", "intersects", "intersecting", "cross-hierarchy",
            "cross hierarchy", "croestorri",
        ],
        "intersects(AdminUnit, LSOA)",
    ),
    (
        "SCQ3",
        [
            "between", "path between", "lie between", "lies between",
            "shortest cycle-free", "cycle-free path", "rhwng",
        ],
        "between(LSOA, LSOA)",
    ),
    (
        "SCQ6",
        [
            "contained within", "nested inside", "nested within",
            "inside", "within", "what is in", "y tu mewn i",
            "decomposed into", "which wards are contained",
            "which communities are contained", "units inside",
            "wedi'u cynnwys",
        ],
        "contains(AdminUnit -> child)",
    ),
    (
        "SCQ5",
        [
            "parent contains", "administrative parent", "parent chain",
            "which unitary authority contains", "which authority contains",
            "contains the selected ward", "contains the selected community",
            "rhiant gweinyddol",
        ],
        "within(child -> AdminUnit)",
    ),
    (
        "SCQ2",
        [
            "graph-near", "graph near", "two steps", "two touches-steps",
            "extended neighbour", "near the selected", "near a selected",
            "yn agos at",
        ],
        "near(LSOA) = two touches-steps",
    ),
    (
        "SCQ1",
        [
            "directly border", "direct adjacency", "border the selected",
            "bordering", "adjacent", "neighbouring", "neighbours",
            "touches", "next to", "yn ffinio", "cyfagos",
        ],
        "touches(LSOA, LSOA)",
    ),
]

# What the question is asking ABOUT, once the relation is known. These do not
# change which query runs - every SCQ answer already carries all four
# variables - but they tell the reader which column to look at, and they are
# what the warrant document calls the CONTENT half of a question.
NL_FOCUS_RULES: List[Tuple[str, List[str], str]] = [
    ("fsm", ["fsm", "free school meal", "prydau ysgol am ddim"],
     "School FSM %"),
    ("attendance", ["attendance", "absence", "presenoldeb"],
     "School attendance %"),
    ("performance", ["performance", "capped 9", "capped9", "attainment",
                     "gcse", "secondary performance", "perfformiad"],
     "Capped 9 (secondary only)"),
    ("deprivation", ["deprivation", "deprived", "wimd", "poverty",
                     "amddifadedd", "tlodi"],
     "WIMD deprivation"),
]

_NL_CODE = re.compile(r"\bW\d{8}\b", re.IGNORECASE)


# Which lens mode a phrase asks for. Order matters: the longest and most
# specific phrases are tested first, so "not near" never matches "near".
# Education thresholds are read SEPARATELY from the spatial form. A sentence
# can carry both ("schools near Cathays with attendance below 90"), and the
# two halves are answered by different machinery: the eight SCQ forms hold no
# filter control at all, while the lens keys do. Reading them apart means a
# threshold is never silently dropped and never silently invented.
# Both languages are matched, because an Arabic sentence that is understood
# and then routed to a form that cannot hold it is worse than one refused.
_EDU_FILTER_RULES = [
    ("Low attendance", (
        r"attendance\s*(?:is\s*)?(?:be?llow|below|under|less than|<=?)\s*\d+",
        r"low attendance", r"poor attendance", r"persistent absence",
        r"حضور[\u0600-\u06ff\s]*(?:اقل|أقل|تحت|دون)[^0-9]{0,10}\d+",
        r"(?:ضعف|انخفاض)\s*(?:ال)?حضور",
        r"حضور\s*(?:منخفض|ضعيف)",
    )),
    ("High FSM", (
        r"(?:fsm|free school meals?)\s*(?:is\s*)?(?:above|over|greater than|>=?)\s*\d+",
        r"high fsm", r"high free school meals?", r"most fsm",
        r"وجبات[\u0600-\u06ff\s]*مجاني",
    )),
    ("High deprivation", (
        r"high(?:ly)? deprived", r"high deprivation", r"most deprived",
        r"deprived areas?",
        r"حرمان", r"محروم",
    )),
]


# Negation reverses a question's meaning, and matching only the positive
# phrase inside it would return the exact opposite of what was asked. Any
# sentence carrying one of these is refused rather than half-understood.
_NEGATION_WORDS = (
    "not near", "not adjacent", "not touching", "not bordering",
    "non-adjacent", "not neighbour", "not neighbor", "far from",
    "outside", "except", "other than",
    "\u0644\u064a\u0633", "\u063a\u064a\u0631", "\u0628\u0639\u064a\u062f",
    "\u062e\u0627\u0631\u062c", "\u0645\u0627\u0639\u062f\u0627",
)


def has_negation(text):
    low = (text or "").lower()
    return any(w in low for w in _NEGATION_WORDS)


def parse_threshold_value(text):
    """The number the sentence actually names, if it names one.

    Without this the app recognised "attendance below 85" and then applied
    its own default of 90 \u2014 an answer to a question nobody asked.
    """
    m = re.search(
        r"(?:below|under|less than|above|over|greater than|<=?|>=?|"
        r"\u0627\u0642\u0644|\u0623\u0642\u0644|\u062a\u062d\u062a|"
        r"\u0627\u0643\u062b\u0631|\u0623\u0643\u062b\u0631|"
        r"\u0641\u0648\u0642)[^0-9]{0,12}(\d{1,3})",
        (text or "").lower(),
    )
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return v if 0 < v <= 100 else None


# School phase is a THIRD condition, independent of the spatial relation and
# of the education threshold. It used to be dropped in silence: a question
# asking for secondary schools got every phase back and said nothing.
_PHASE_WORDS = {
    "Secondary": ("secondary", "\u062b\u0627\u0646\u0648"),
    "Primary": ("primary", "\u0627\u0628\u062a\u062f\u0627\u0626"),
    "Special": ("special school", "\u062e\u0627\u0635"),
    "All-age": ("all-age", "all age"),
}


def parse_school_phase(text):
    low = (text or "").lower()
    for label, words in _PHASE_WORDS.items():
        if any(w in low for w in words):
            return label
    return None


def parse_education_filter(text):
    """Return the filter a sentence names, or None. Never guesses."""
    low = (text or "").lower()
    for label, patterns in _EDU_FILTER_RULES:
        for pat in patterns:
            if re.search(pat, low):
                return label
    return None


# The eight spatial forms take no education filter; only the lens keys do.
_FILTERABLE_FORMS = ("LENS", "SCHOOL_LENS")


_LENS_MODE_PHRASES = [
    ("not_touches", ("not touch", "does not touch", "do not touch",
                     "not touching", "not adjacent", "non-adjacent",
                     "does not border", "do not border")),
    ("near",     ("near", "nearby", "close to", "two steps",
                  "قريب", "القريب", "قريبة")),
    ("touches",  ("touch", "touching", "border", "bordering", "adjacent",
                  "neighbour", "neighbor", "next to",
                  "بجوار", "مجاور", "المجاور", "المجاورة", "تلامس")),
    ("inside",   ("inside", "within", "contained in", "in this", "in the",
                  "داخل", "ضمن")),
    ("contains", ("contains", "parent of", "which authority", "belongs to")),
]


# School markers in both languages. Testing only the English word sent
# every Arabic question to an LSOA-anchored form that could not hold it.
_SCHOOL_WORDS = ("school", "مدرسة", "مدارس", "المدارس", "المدرسة")


# The kind-word a reader writes beside a place name ("Cathays community")
# names the type of THAT place. Without reading it, the ranking below fell
# back to a blanket preference for Ward, so a question about a Community was
# answered for the Ward of the same name -- correct figures for a place the
# reader never asked about. The same word must therefore not be reused as the
# type of the NEIGHBOUR, which is the second half of the same defect.
_UNIT_TYPE_WORDS = [
    ("UnitaryAuthority", ("unitary authority", "unitary authorities",
                          "county borough", "\u0633\u0644\u0637\u0629",
                          "\u0645\u062d\u0627\u0641\u0638\u0629")),
    ("Community", ("community", "communities",
                   "\u0645\u062c\u062a\u0645\u0639",
                   "\u0645\u062c\u062a\u0645\u0639\u0627\u062a")),
    ("Ward", ("ward", "wards", "\u062f\u0627\u0626\u0631\u0629",
              "\u062f\u0648\u0627\u0626\u0631")),
]


def _name_tokens(raw_name: str) -> List[str]:
    """Each half of a bilingual name, so "Caerdydd - Cardiff" matches either.

    Module level rather than nested, because the lens reads the same tokens
    when deciding which kind-word belongs to the anchor.
    """
    pieces = re.split(r"[-/\u2013,]", raw_name)
    return [
        p.strip().lower()
        for p in pieces
        if len(p.strip()) >= 4
    ] or [raw_name.strip().lower()]


def _beside_patterns(name: str, word: str) -> Tuple[str, str]:
    """The two orders a reader writes: "Cathays community", "community of Cathays"."""
    esc, w = re.escape(name), re.escape(word)
    return (
        rf"\b{esc}\b[\s\-,'\u2019]*{w}\b",
        rf"\b{w}\b[\s\-,'\u2019]*(?:of\s+|the\s+)?{esc}\b",
    )


def type_word_beside(low: str, name: str) -> str | None:
    """The unit type named immediately beside `name`, or None.

    Nothing is inferred from a kind-word elsewhere in the sentence, because
    that one usually describes what is being asked FOR.
    """
    for utype, words in _UNIT_TYPE_WORDS:
        for word in words:
            if any(re.search(pat, low) for pat in _beside_patterns(name, word)):
                return utype
    return None


def strip_anchor_type_words(low: str, tokens: List[str]) -> str:
    """Remove only the kind-word attached to the anchor's own name.

    Banning the whole type instead would lose the second, genuine mention:
    "which communities touch Cathays community" names Community twice, once
    for the anchor and once for what is being asked for.
    """
    out = low
    for tok in tokens:
        for _utype, words in _UNIT_TYPE_WORDS:
            for word in words:
                for pat in _beside_patterns(tok, word):
                    out = re.sub(pat, tok, out, count=1)
    return out


def parse_lens_intent(text, admin_pair, require_school=True):
    """Route a school question anchored on an administrative unit.

    Returns a dict of pending lens settings, or None. It fires only when the
    sentence asks about SCHOOLS and names an administrative unit, because
    those are exactly the questions the eight spatial forms cannot hold: they
    are anchored on LSOAs and carry no filter. Nothing here guesses a unit or
    a relation that the sentence did not contain.
    """
    low = (text or "").lower()
    if not admin_pair:
        return None
    if require_school and not any(w in low for w in _SCHOOL_WORDS):
        return None
    label = str(admin_pair[1])
    parts = [p.strip() for p in label.split("|")]
    atype = parts[1] if len(parts) > 1 else None
    if not atype:
        return None
    mode = None
    for name, phrases in _LENS_MODE_PHRASES:
        if any(p in low for p in phrases):
            mode = name
            break
    if mode is None:
        mode = "direct"

    # Any kind-word standing beside the anchor's own name describes the
    # anchor. Reading it as the neighbour type was what turned "schools near
    # Cathays community" into anchor=Ward with neighbour=Community, a pair no
    # row can satisfy.
    rest = strip_anchor_type_words(low, _name_tokens(parts[0]))

    ntype = None
    for utype, words in _UNIT_TYPE_WORDS:
        if any(
            re.search(r"\b" + re.escape(w) + r"\b", rest) for w in words
        ):
            ntype = utype
            break

    # Near is defined in the paper inside ONE division: disjoint regions
    # joined by a path of two touches edges between regions of the same kind.
    # A neighbour type different from the anchor's cannot be satisfied, so it
    # is dropped here and reported, rather than silently returning nothing.
    dropped = None
    if mode == "near" and ntype and ntype != atype:
        dropped, ntype = ntype, None

    return {
        "atype": atype,
        "uri": admin_pair[0],
        "mode": mode,
        "ntype": ntype,
        "dropped_ntype": dropped,
    }


def parse_spatial_question(
    text: str,
    lsoa_options: List[Tuple[str, str]] | None = None,
    admin_options: List[Tuple[str, str]] | None = None,
) -> Dict[str, Any]:
    """Read one question and return what could be identified in it.

    Nothing is guessed. A field the sentence does not determine is returned
    empty, and the caller leaves the corresponding control untouched rather
    than filling it with a default that the reader did not ask for.
    """
    raw = (text or "").strip()
    low = raw.lower()
    found: Dict[str, Any] = {
        "text": raw,
        "scq": None,
        "relation": None,
        "matched_phrase": None,
        "focus": [],
        "focus_labels": [],
        "areas": [],
        "admin": None,
        "steps": [],
        "unmatched": [],
    }
    if not raw:
        return found

    for scq_key, phrases, relation in NL_RELATION_RULES:
        hit = next((p for p in phrases if p in low), None)
        if hit:
            found["scq"] = scq_key
            found["relation"] = relation
            found["matched_phrase"] = hit
            found["steps"].append(
                f"Recognised \u201c{hit}\u201d as the spatial form "
                f"{scq_key}: {relation}."
            )
            break
    if not found["scq"]:
        found["unmatched"].append(
            "No spatial relation was recognised. Name one of: border, near, "
            "between, not adjacent, contains, within, intersect."
        )

    for key, phrases, label in NL_FOCUS_RULES:
        if any(p in low for p in phrases):
            found["focus"].append(key)
            found["focus_labels"].append(label)
    if found["focus_labels"]:
        found["steps"].append(
            "Reading focus: " + ", ".join(found["focus_labels"]) + "."
        )

    # An explicit LSOA code always wins over a name match.
    codes = [c.upper() for c in _NL_CODE.findall(raw)]
    for option in lsoa_options or []:
        code, label = option[0], str(option[1])
        if code in codes and code not in [a[0] for a in found["areas"]]:
            found["areas"].append((code, label))
    if not found["areas"]:
        for option in lsoa_options or []:
            code, label = option[0], str(option[1])
            name = label.split("|")[-1].strip().lower()
            if len(name) > 5 and name in low:
                found["areas"].append((code, label))
                if len(found["areas"]) == 2:
                    break
    if found["areas"]:
        found["steps"].append(
            "Area: " + "; ".join(a[1] for a in found["areas"]) + "."
        )

    # Taking the first name that appears anywhere in the sentence was wrong:
    # "Cardiff" matched a community in an English district before it reached
    # the unitary authority, so the question ran against a unit the reader
    # never named. Candidates are now ranked, and a tie is reported rather
    # than resolved silently.
    # Welsh units carry bilingual names such as "Caerdydd - Cardiff", so
    # requiring the whole name to appear in the sentence never matched: a
    # reader writes "Cardiff", not both halves. Each half is tested on its
    # own, as a whole word.
    # Only the two containment forms use an administrative unit. Reporting a
    # match for the others put "Blaenau Gwent | UnitaryAuthority" beside a
    # question about neighbouring LSOAs, which reads as though the unit had
    # been used when it had not.
    admin_relevant = found["scq"] in {None, "SCQ5", "SCQ6"}

    candidates: List[Tuple[int, str, Tuple[str, str]]] = []
    for option in (admin_options or []) if admin_relevant else []:
        uri, label = option[0], str(option[1])
        parts = [p.strip() for p in label.split("|")]
        name = parts[0].lower()
        unit_type = (parts[1] if len(parts) > 1 else "").lower()
        tokens = _name_tokens(parts[0])
        hit_token = next(
            (
                tok for tok in tokens
                if re.search(r"\b" + re.escape(tok) + r"\b", low)
            ),
            None,
        )
        if not hit_token:
            continue
        name = hit_token
        # A kind-word written beside the name settles the type outright; the
        # blanket preference below applies only when the reader gave none.
        # Cardiff has a Ward, a Community and a Unitary Authority of the same
        # name, so guessing here silently answers a different question.
        score = 40
        beside = type_word_beside(low, name)
        if beside:
            score += 80 if beside.lower() == unit_type else -40
        elif "unitaryauthority" in unit_type:
            score += 20
        elif "ward" in unit_type:
            score += 10
        score += min(len(name), 20)
        candidates.append((score, name, (uri, label)))

    if not candidates and found["scq"] in {"SCQ5", "SCQ6"}:
        found["unmatched"].append(
            "No administrative unit in the question was recognised, so the "
            "unit selected below was left as it was. Name the unit, or "
            "choose it from the list."
        )
    if candidates:
        candidates.sort(key=lambda item: -item[0])
        best = candidates[0]
        rivals = [c for c in candidates[1:] if c[0] == best[0]]
        found["admin"] = best[2]
        found["steps"].append(f"Administrative unit: {best[2][1]}.")
        if rivals:
            found["unmatched"].append(
                "More than one unit matches that name equally well ("
                + ", ".join(str(c[2][1]) for c in [best] + rivals[:3])
                + "). The first was used; choose it from the list below to "
                "be certain."
            )

    return found


# The project description registered in PATS names "potential LLM integration
# for query understanding", so a model path belongs in the system. It is not
# the default: the rule table is deterministic, needs no key and runs offline,
# which are the properties an instrument needs. The model is offered as a
# comparison so the choice can be evidenced rather than asserted.

NL_LLM_MODEL = "gemini-3.6-flash"
NL_LLM_CALL_CAP = 500         # per browser session; the prepaid credit and
                              # the project spend cap are the real ceiling,
                              # this only stops a runaway loop on one tab


def nl_llm_available() -> bool:
    """True when a key is configured. Absence is a normal state, not an error."""
    try:
        if st.secrets.get("OPENAI_API_KEY"):
            return True
    except Exception:
        pass
    return bool(os.environ.get("OPENAI_API_KEY"))


def _nl_llm_key() -> str | None:
    try:
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return str(key)
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY")


def _nl_json(payload: str) -> Dict[str, Any]:
    """Read the JSON object out of a model reply.

    Replies arrive wrapped in fences, prefaced with a sentence, or cut short
    when the model spends its budget before finishing. Taking the outermost
    braces recovers the usable cases; the rest raise and fall back to the
    rule table.
    """
    text = (payload or "").replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError(
        "the model returned no complete JSON object "
        f"({text[:80]!r})"
    )


def _nl_llm_base_url() -> str | None:
    """Any OpenAI-compatible endpoint, so the provider is a setting.

    Several providers, including Google's Gemini, expose an OpenAI-compatible
    URL. Leaving this configurable means the parser can be pointed at a free
    tier without touching the code.
    """
    try:
        url = st.secrets.get("OPENAI_BASE_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return os.environ.get("OPENAI_BASE_URL") or None


def _nl_llm_model() -> str:
    try:
        name = st.secrets.get("OPENAI_MODEL")
        if name:
            return str(name)
    except Exception:
        pass
    return os.environ.get("OPENAI_MODEL", NL_LLM_MODEL)


def _nl_llm_error(exc: Exception) -> str:
    """Return a clear message when the model request fails."""
    text = str(exc)
    text_lower = text.lower()

    if (
        "503" in text
        or "unavailable" in text_lower
        or "high demand" in text_lower
    ):
        return (
            "Gemini is temporarily unavailable because of high demand. "
            "The rule-based parser was used instead."
        )

    if (
        "429" in text
        or "resource_exhausted" in text_lower
        or "quota" in text_lower
    ):
        return (
            "The Gemini request allowance has been reached. "
            "The rule-based parser was used instead."
        )

    return (
        "Gemini could not be reached. "
        "The rule-based parser was used instead."
    )

def llm_parse_question(
    text: str,
    lsoa_options: List[Tuple[str, str]] | None = None,
    admin_options: List[Tuple[str, str]] | None = None,
) -> Dict[str, Any]:
    """Ask a model for the same structure the rule table produces.

    The model is constrained to the eight forms and asked for JSON only, and
    its answer is validated against the same vocabulary; anything outside it
    is discarded rather than trusted. On any failure the rule table answers,
    so the interface never depends on the network.
    """
    used = st.session_state.get("nl_llm_calls", 0)
    if used >= NL_LLM_CALL_CAP:
        fallback = parse_spatial_question(text, lsoa_options, admin_options)
        fallback["parser"] = "rule-based (LLM call cap reached)"
        return fallback
    try:
        from openai import OpenAI

        client = OpenAI(api_key=_nl_llm_key(), base_url=_nl_llm_base_url())
        system = (
            "You map an education-geography question onto exactly one of "
            "eight spatial competency forms and return JSON only, with no "
            "prose and no code fence.\n"
            "SCQ1 touches: which regions directly border a region.\n"
            "SCQ2 near: regions reachable in two touches-steps, disjoint.\n"
            "SCQ3 between: regions on a cycle-free path linking two regions.\n"
            "SCQ4 not-adjacent: regions that share no boundary.\n"
            "SCQ5 contains: which administrative parent contains a unit.\n"
            "SCQ6 within: which units are inside an administrative unit.\n"
            "SCQ7 intersects: administrative units intersecting an LSOA.\n"
            "SCQ8 cross-near: administrative units near but not intersecting.\n"
            'Return {"scq": "SCQ1".."SCQ8" or null, '
            '"focus": subset of ["fsm","attendance","performance",'
            '"deprivation"], "codes": [LSOA codes like W01001440], '
            '"place": free text place name or null, '
            '"reason": one short sentence}.'
        )
        response = client.chat.completions.create(
            model=_nl_llm_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=1200,
        )
        st.session_state["nl_llm_calls"] = used + 1
        payload = response.choices[0].message.content or ""
        data = _nl_json(payload)
    except Exception as exc:
        fallback = parse_spatial_question(text, lsoa_options, admin_options)
        fallback["parser"] = "rule-based (model unavailable)"
        fallback["unmatched"].append(_nl_llm_error(exc))
        return fallback

    valid = {f"SCQ{i}" for i in range(1, 9)}
    scq = data.get("scq") if data.get("scq") in valid else None
    focus = [
        f for f in (data.get("focus") or [])
        if f in {"fsm", "attendance", "performance", "deprivation"}
    ]
    labels = {
        "fsm": "School FSM %", "attendance": "School attendance %",
        "performance": "Capped 9 (secondary only)",
        "deprivation": "WIMD deprivation",
    }
    result: Dict[str, Any] = {
        "text": text,
        "parser": f"LLM ({_nl_llm_model()})",
        "scq": scq,
        "relation": (
            dict((k, r) for k, _p, r in NL_RELATION_RULES).get(scq)
            if scq else None
        ),
        "matched_phrase": None,
        "focus": focus,
        "focus_labels": [labels[f] for f in focus],
        "areas": [],
        "admin": None,
        "steps": [],
        "unmatched": [],
        "raw_model_output": data,
    }
    if data.get("reason"):
        result["steps"].append(str(data["reason"]))
    if not scq:
        result["unmatched"].append("The model returned no recognised form.")

    # Names and codes are resolved locally, and by the same ranked matcher
    # the rule table uses. The model only says which form the question takes;
    # letting it also choose the unit put "Ashchurch with Walton Cardiff
    # Ward" in place of Cardiff, because that name contains the word.
    resolver_text = " ".join(
        [text, str(data.get("place") or "")]
        + [str(c) for c in (data.get("codes") or [])]
    )
    resolved = parse_spatial_question(
        resolver_text, lsoa_options, admin_options
    )
    result["areas"] = resolved["areas"]
    if scq in {"SCQ5", "SCQ6"}:
        result["admin"] = resolved["admin"]
    result["steps"].extend(resolved["steps"][1:] if resolved["steps"] else [])
    result["unmatched"].extend(
        u for u in resolved["unmatched"]
        if "No spatial relation" not in u
    )

    return result


NL_EXAMPLES = [
    "Which LSOAs directly border Blaenau Gwent 001A?",
    "Which neighbouring LSOAs have the highest school FSM levels?",
    "Which LSOAs are graph-near the selected LSOA?",
    "Which LSOAs lie between W01001840 and W01001777?",
    "Which LSOAs are not adjacent to the selected LSOA?",
    "Which administrative parent contains the selected Ward?",
    "Which Wards are contained within Cardiff?",
    "Which Wards or Communities intersect the selected LSOA?",
    "Which Wards are near, but do not intersect, the selected LSOA?",
]


def render_nl_search(
    lsoa_options: List[Tuple[str, str]] | None,
    admin_options: List[Tuple[str, str]] | None,
) -> None:
    """A question box that drives the controls below it.

    The box sets the selectors rather than running its own query, so the
    answer a reader sees is always produced by the same code path as the
    manual route. Nothing is hidden behind the sentence.
    """
    st.markdown("### Search in your own words")

    col_input, col_go = st.columns([6, 1])
    with col_input:
        question = st.text_input(
            "Question",
            key="nl_question",
            placeholder=(
                "Try: Which Communities touch Cathays Community?"
            ),
            label_visibility="collapsed",
        )
    with col_go:
        asked = st.button("Search", type="primary", use_container_width=True)

    if st.session_state.pop("nl_autorun", False):
        asked = True

    mode = "Rule-based"

    if not (asked and question):
        return

    rule_parsed = parse_spatial_question(question, lsoa_options, admin_options)
    rule_parsed["parser"] = "rule-based"

    if mode == "LLM":
        parsed = llm_parse_question(question, lsoa_options, admin_options)
    else:
        parsed = rule_parsed

    st.session_state.nl_last = parsed

    # Setting the widget state before the widget is drawn is what makes the
    # sentence move the controls; the query itself is left to the normal path.
    changed = []
    if parsed["scq"]:
        st.session_state["scq_select"] = parsed["scq"]
        changed.append(parsed["scq"])
    scq = parsed["scq"]
    if scq and parsed["areas"]:
        if scq == "SCQ3" and len(parsed["areas"]) >= 2:
            # SCQ3 names its two endpoint widgets in lower case.
            st.session_state["scq3_lsoa_a"] = parsed["areas"][0]
            st.session_state["scq3_lsoa_b"] = parsed["areas"][1]
            changed.append("both endpoints")
        else:
            st.session_state[f"{scq}_lsoa"] = parsed["areas"][0]
            changed.append(parsed["areas"][0][1])
    if scq and parsed["admin"]:
        st.session_state[f"{scq}_admin"] = parsed["admin"]
        changed.append(parsed["admin"][1])

    # A cross-hierarchy question that names an administrative unit and no
    # LSOA has to start from the administrative side. Without this the form
    # opens on its LSOA direction and then asks for an LSOA the sentence
    # never mentioned, which reads as a failure even though the answer was
    # available from the other direction over the same stored facts.
    if scq in ("SCQ7", "SCQ8"):
        if parsed["admin"] and not parsed["areas"]:
            st.session_state[f"{scq}_direction"] = "admin"
            changed.append("started from the administrative unit")
        elif parsed["areas"]:
            st.session_state[f"{scq}_direction"] = "lsoa"
    # A threshold in the sentence is carried to the controls that can hold
    # one, and reported plainly when the chosen form cannot. Dropping it in
    # silence would let a reader believe a filter had been applied.
    edu = parse_education_filter(parsed.get("text", ""))
    if edu:
        st.session_state["LENS_filter"] = edu
        st.session_state["SLENS_filter"] = edu
        if scq in _FILTERABLE_FORMS:
            changed.append(f"education filter: {edu}")
        else:
            changed.append(
                f"education filter recognised ({edu}) but this form has no "
                f"filter \u2014 it is ready in Education lens and From a school"
            )

    # A school question anchored on an administrative unit belongs to the
    # lens, not to one of the eight forms: the eight are LSOA-anchored and
    # hold no filter, so answering there would answer a different question.
    # The settings are parked rather than written, because the option lists
    # they must match are only known once the branch queries the graph.
    # The question's own answer is parked here, complete and independent of
    # the manual panel. It carries everything the query needs, so the answer
    # can be produced without a single widget being created.
    _question_low = (parsed.get("text") or "").lower()
    _lens = parse_lens_intent(parsed.get("text", ""), parsed.get("admin"))
    if not _lens and has_negation(parsed.get("text", "")):
        _candidate_lens = parse_lens_intent(
            parsed.get("text", ""), parsed.get("admin"),
            require_school=False,
        )
        if (_candidate_lens or {}).get("mode") == "not_touches":
            _lens = _candidate_lens
    if (
        has_negation(parsed.get("text", ""))
        and (_lens or {}).get("mode") != "not_touches"
    ):
        st.session_state["nl_answer"] = {"kind": None}
        st.session_state["nl_negated"] = True
        changed.append(
            "the sentence is negated, so no form was run \u2014 the eight "
            "forms match a relation, not its complement, and answering the "
            "positive half would invert your question"
        )
        st.session_state["nl_controls_set"] = changed
        st.rerun()

    # A question that names an administrative unit and no LSOA cannot be
    # answered by an LSOA-anchored form: SCQ1, SCQ2 and SCQ4 all require a
    # statistical anchor and there is no administrative variant of them.
    # The lens holds the same relations over the administrative graph, so
    # the question goes there instead of dying in a form that cannot take
    # it. Whether the answer is units or schools is decided by the sentence.
    _want_units = bool(
        _lens and not any(w in _question_low for w in _SCHOOL_WORDS)
    )
    if (
        not _lens
        and parsed.get("admin")
        and not parsed.get("areas")
        and scq in (None, "SCQ1", "SCQ2", "SCQ3", "SCQ4")
    ):
        # A question that names a unit and no LSOA cannot be answered by an
        # LSOA-anchored form, and a question that names a unit but matches no
        # form at all used to produce nothing whatever. Both go to the lens,
        # read by the same rules as a school question so that the anchor type
        # and the neighbour type are separated identically.
        _lens = parse_lens_intent(
            parsed.get("text", ""), parsed.get("admin"), require_school=False
        )
        _want_units = not any(
            w in (parsed.get("text") or "").lower() for w in _SCHOOL_WORDS
        )

    st.session_state["nl_answer"] = {
        "want": "units" if _want_units else "schools",
        "kind": "LENS" if _lens else scq,
        "mode": (_lens or {}).get("mode"),
        "ntype": (_lens or {}).get("ntype"),
        "admin": (
            (_lens or {}).get("uri")
            or (parsed["admin"][0] if parsed.get("admin") else None)
        ),
        "areas": [a[0] for a in (parsed.get("areas") or [])],
        "filter": edu,
        "value": parse_threshold_value(parsed.get("text", "")),
        "phase": parse_school_phase(parsed.get("text", "")),
        "text": parsed.get("text", ""),
        "admin_label": (parsed["admin"][1] if parsed.get("admin") else None),
    }
    if _lens:
        _lens["filter"] = edu or "None"
        st.session_state["LENS_pending"] = _lens
        st.session_state["scq_select"] = "LENS"
        scq = "LENS"
        changed = [
            c for c in changed
            if not str(c).startswith("SCQ")
        ]
        changed.insert(0, "Education lens")
        changed.append(f"start from {_lens['atype']}")
        changed.append(f"relation: {LENS_MODES[_lens['mode']][0]}")
        if _lens["ntype"]:
            changed.append(f"related unit type: {_lens['ntype']}")
        if _lens.get("dropped_ntype"):
            changed.append(
                f"the kind you named ({_lens['dropped_ntype']}) was not "
                "applied \u2014 near is defined inside one division"
            )

    if scq:
        st.session_state[f"scq_ran_{scq}"] = True

    st.session_state["nl_controls_set"] = changed
    _resolved = bool(parsed.get("areas")) or bool(parsed.get("admin"))
    if changed and not _resolved:
        # A form was matched but no place in the sentence could be resolved.
        # Opening the panel here would demand a value the reader never gave
        # and make a naming problem look like a broken question.
        st.session_state["nl_unresolved"] = True
    if changed:
        st.rerun()


def render_nl_understanding() -> None:
    """Show what the last question was read as, beneath the controls."""
    parsed = st.session_state.get("nl_last")
    if not parsed or not parsed.get("text"):
        return

    chips = []
    if parsed["relation"]:
        chips.append(
            f"<span class='nl-chip nl-chip-rel'>{escape(parsed['relation'])}"
            "</span>"
        )
    for label in parsed["focus_labels"]:
        chips.append(
            f"<span class='nl-chip nl-chip-focus'>{escape(label)}</span>"
        )
    for _code, label in parsed["areas"]:
        chips.append(f"<span class='nl-chip nl-chip-area'>{escape(label)}</span>")
    if parsed["admin"]:
        chips.append(
            f"<span class='nl-chip nl-chip-area'>"
            f"{escape(str(parsed['admin'][1]))}</span>"
        )

    steps = "".join(f"<li>{escape(s)}</li>" for s in parsed["steps"])
    warn = "".join(
        f"<div class='nl-warn'>{escape(u)}</div>" for u in parsed["unmatched"]
    )
    # Which engine read the sentence is part of the answer, not a detail: a
    # reader should never have to guess whether a model was involved.
    source = str(parsed.get("parser") or "rule-based")
    badge_class = "nl-src-llm" if source.startswith("LLM") else "nl-src-rule"
    detail = (
        "deterministic, offline, no key"
        if badge_class == "nl-src-rule"
        else "model output validated against the same vocabulary"
    )
    st.markdown(
        "<div class='nl-read'>"
        f"<div class='nl-src {badge_class}'>Parsed by {escape(source)} "
        f"&middot; {detail}</div>"
        "<div class='nl-read-title'>Read as</div>"
        f"<div class='nl-chips'>{''.join(chips) or '&mdash;'}</div>"
        + (f"<ol class='nl-steps'>{steps}</ol>" if steps else "")
        + warn
        + "</div>",
        unsafe_allow_html=True,
    )


def render_scq_evidence(scq_key: str) -> None:
    """Show the Task 3 warrant for one question, then the questions it answers.

    Colours come from theme variables rather than fixed hex values, so the
    block reads correctly in both the light and the dark skin.
    """
    ev = SCQ_EVIDENCE.get(scq_key)
    if not ev:
        return

    st.markdown(
        "<div class='ev-inst'><span class='ev-inst-label'>Instantiation"
        "</span>" + ev["instantiation"] + "</div>",
        unsafe_allow_html=True,
    )

    tab_warrant, tab_questions = st.tabs(
        ["Literature warrant", "Questions this relation answers"]
    )

    cards = []
    for row in ev["rows"]:
        verdict = row.get("verdict", "None")
        cls = {"Full": "ev-full", "Partial": "ev-partial"}.get(
            verdict, "ev-none"
        )
        if row.get("quote"):
            quote_html = (
                "<div class='ev-quote'>&ldquo;" + row["quote"]
                + "&rdquo;</div>"
                + "<div class='ev-page'>" + str(row.get("page", "")) + "</div>"
            )
        else:
            quote_html = "<div class='ev-empty'>NO WARRANT FOUND</div>"
        note = row.get("verdict_note")
        cards.append(
            f"<div class='ev-card {cls}'>"
            "<div class='ev-head'>"
            f"<span class='ev-source'>{row['source']}</span>"
            f"<span class='ev-verdict {cls}'>{verdict}</span></div>"
            + quote_html
            + f"<div class='ev-warrant'>{row['warrant']}</div>"
            + (f"<div class='ev-note'>{note}</div>" if note else "")
            + "</div>"
        )

    with tab_warrant:
        st.markdown(
            "<div class='ev-block'>"
            + "".join(cards)
            + "<div class='ev-assess'><b>Critical assessment.</b> "
            + ev["assessment"]
            + "</div></div>",
            unsafe_allow_html=True,
        )

    with tab_questions:
        items = "".join(f"<li>{q}</li>" for q in ev["questions"])
        st.markdown(
            "<div class='ev-qs'><ol>" + items + "</ol></div>",
            unsafe_allow_html=True,
        )


SCQ_ANSWER_MODE = {
    "SCQ1": ("Computed-then-stored", "Paid once", "No"),
    "SCQ2": ("Computed-then-stored", "Paid once", "No"),
    "SCQ3": ("Computed-then-stored", "Paid once", "No"),
    "SCQ4": ("Computed-then-stored", "Paid once", "No"),
    "SCQ5": ("Not applicable", "—", "n/a"),
    "SCQ6": ("Not applicable", "—", "n/a"),
    "SCQ7": ("Computed-then-stored", "Paid once", "No"),
    "SCQ8": ("Computed-then-stored", "Paid once", "No"),
}

MODE_NOTE = {
    "Native": (
        "Inherited from YAGO2geo, or traversal over an inherited relation. "
        "This is the only mode that counts as model coverage."
    ),
    "Geometry-on-demand": (
        "The polygon relation is recomputed at every query. This is the "
        "baseline against which stored relations are compared."
    ),
    "Computed-then-stored": (
        "Base touches computed once and stored, then traversed for near, "
        "far, between and chains. Same answers as on-demand, so the two tie "
        "on completeness; the difference is cost, composability and "
        "explainability."
    ),
    "Not applicable": (
        "Reclassified: this form belongs to the cross-hierarchy questions."
    ),
}


# ---------------------------------------------------------------------------
# EDUCATION LENS — schools reached through any relation the graph already has
#
# Not a ninth SCQ form. Each variant composes relations with DIFFERENT
# provenances in one answer, which is the thing the integration made possible:
#
#   anchor --INTERSECTS--> LSOA <--LOCATED_IN-- School     (Geometry-origin)
#   anchor --TOUCHES-->    unit --INTERSECTS--> LSOA ...   (Native, then Geometry-origin)
#   anchor <--WITHIN--     unit --INTERSECTS--> LSOA ...   (Native, then Geometry-origin)
#   anchor --WITHIN-->     unit --INTERSECTS--> LSOA ...   (Native, then Geometry-origin)
#
# A direct INTERSECTS count confirmed all three anchor types carry the
# relation: Community 8,423, UnitaryAuthority 2,407, Ward 2,344. The
# neighbour type is a free parameter, so Community->Ward, Ward->Community and
# every other pair the data actually holds can be asked for.
# ---------------------------------------------------------------------------
_LENS_TAIL = """
MATCH (l)<-[:LOCATED_IN]-(s:School)
WHERE ($fsm_min IS NULL OR s.fsm_pct >= $fsm_min)
  AND ($att_max IS NULL OR s.attendance_pct <= $att_max)
  AND ($dep IS NULL OR l.deprivation = $dep)\n  AND ($phase IS NULL OR s.phase_group = $phase)
RETURN DISTINCT
    coalesce(s.school_name, s.name, s.code) AS school,
    s.phase_group                           AS phase,
    __VIA__                                 AS via_unit,
    __VIATYPE__                             AS via_type,
    l.code                                  AS lsoa_code,
    coalesce(l.name, l.LSOA_Name, l.code)   AS lsoa_name,
    l.deprivation                           AS deprivation,
    l.wimd_decile                           AS wimd_decile,
    s.fsm_pct                               AS fsm_pct,
    s.attendance_pct                        AS attendance_pct,
    s.capped9_score                         AS capped9_score
ORDER BY fsm_pct DESC
LIMIT $limit
"""

_LENS_SELF = "coalesce(anchor.name, anchor.uri)"
_LENS_NBR = "coalesce(nbr.name, nbr.uri)"

LENS_CYPHER = {
    "direct": (
        "MATCH (anchor:AdminUnit {uri:$admin})-[:INTERSECTS]->(l:LSOA)\n"
        + _LENS_TAIL.replace("__VIA__", _LENS_SELF).replace("__VIATYPE__", "anchor.type")
    ),
    "touches": (
        "MATCH (anchor:AdminUnit {uri:$admin})-[:TOUCHES]-(nbr:AdminUnit)\n"
        "WHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n"
        "MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\n"
        + _LENS_TAIL.replace("__VIA__", _LENS_NBR).replace("__VIATYPE__", "nbr.type")
    ),
    "inside": (
        "MATCH (anchor:AdminUnit {uri:$admin})<-[:WITHIN]-(nbr:AdminUnit)\n"
        "WHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n"
        "MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\n"
        + _LENS_TAIL.replace("__VIA__", _LENS_NBR).replace("__VIATYPE__", "nbr.type")
    ),
    "contains": (
        "MATCH (anchor:AdminUnit {uri:$admin})-[:WITHIN]->(nbr:AdminUnit)\n"
        "WHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n"
        "MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\n"
        + _LENS_TAIL.replace("__VIA__", _LENS_NBR).replace("__VIATYPE__", "nbr.type")
    ),
}

LENS_MODES = {
    "direct": (
        "Schools inside this unit",
        "AdminUnit --INTERSECTS--> LSOA <--LOCATED_IN-- School",
        "Geometry-origin, then Project-integrated",
    ),
    "touches": (
        "Schools in units that TOUCH this one",
        "AdminUnit --TOUCHES--> AdminUnit --INTERSECTS--> LSOA "
        "<--LOCATED_IN-- School",
        "Native YAGO2geo, then Geometry-origin, then Project-integrated",
    ),
    "inside": (
        "Schools in units INSIDE this one",
        "AdminUnit <--WITHIN-- AdminUnit --INTERSECTS--> LSOA "
        "<--LOCATED_IN-- School",
        "Native YAGO2geo, then Geometry-origin, then Project-integrated",
    ),
    "contains": (
        "Schools in the unit that CONTAINS this one",
        "AdminUnit --WITHIN--> AdminUnit --INTERSECTS--> LSOA "
        "<--LOCATED_IN-- School",
        "Native YAGO2geo, then Geometry-origin, then Project-integrated",
    ),
}


# School-anchored lens. This travels the COMPUTED side of the graph:
# LSOA_TOUCHES is geometry-origin, GRAPH_NEAR is derived from it. "Which
# schools are near my school" is answered through statistical geography,
# not administrative geography, and the provenance line says so.
SCHOOL_LENS_CYPHER = {
    "same": ("MATCH (me:School {code:$school})-[:LOCATED_IN]->(l:LSOA)\n" + '\nMATCH (l)<-[:LOCATED_IN]-(s:School)\nWHERE s <> me\n  AND ($fsm_min IS NULL OR s.fsm_pct >= $fsm_min)\n  AND ($att_max IS NULL OR s.attendance_pct <= $att_max)\n  AND ($dep IS NULL OR l.deprivation = $dep)\n  AND ($phase IS NULL OR s.phase_group = $phase)\nRETURN DISTINCT\n    coalesce(s.school_name, s.name, s.code) AS school,\n    s.phase_group                           AS phase,\n    l.code                                  AS lsoa_code,\n    coalesce(l.name, l.LSOA_Name, l.code)   AS lsoa_name,\n    l.deprivation                           AS deprivation,\n    l.wimd_decile                           AS wimd_decile,\n    s.fsm_pct                               AS fsm_pct,\n    s.attendance_pct                        AS attendance_pct,\n    s.capped9_score                         AS capped9_score\nORDER BY fsm_pct DESC\nLIMIT $limit\n'),
    "touch": ("MATCH (me:School {code:$school})-[:LOCATED_IN]->(home:LSOA)\n"
              "MATCH (home)-[:LSOA_TOUCHES]-(l:LSOA)\n" + '\nMATCH (l)<-[:LOCATED_IN]-(s:School)\nWHERE s <> me\n  AND ($fsm_min IS NULL OR s.fsm_pct >= $fsm_min)\n  AND ($att_max IS NULL OR s.attendance_pct <= $att_max)\n  AND ($dep IS NULL OR l.deprivation = $dep)\n  AND ($phase IS NULL OR s.phase_group = $phase)\nRETURN DISTINCT\n    coalesce(s.school_name, s.name, s.code) AS school,\n    s.phase_group                           AS phase,\n    l.code                                  AS lsoa_code,\n    coalesce(l.name, l.LSOA_Name, l.code)   AS lsoa_name,\n    l.deprivation                           AS deprivation,\n    l.wimd_decile                           AS wimd_decile,\n    s.fsm_pct                               AS fsm_pct,\n    s.attendance_pct                        AS attendance_pct,\n    s.capped9_score                         AS capped9_score\nORDER BY fsm_pct DESC\nLIMIT $limit\n'),
    "near": ("MATCH (me:School {code:$school})-[:LOCATED_IN]->(home:LSOA)\n"
             "MATCH (home)-[:GRAPH_NEAR]-(l:LSOA)\n" + '\nMATCH (l)<-[:LOCATED_IN]-(s:School)\nWHERE s <> me\n  AND ($fsm_min IS NULL OR s.fsm_pct >= $fsm_min)\n  AND ($att_max IS NULL OR s.attendance_pct <= $att_max)\n  AND ($dep IS NULL OR l.deprivation = $dep)\n  AND ($phase IS NULL OR s.phase_group = $phase)\nRETURN DISTINCT\n    coalesce(s.school_name, s.name, s.code) AS school,\n    s.phase_group                           AS phase,\n    l.code                                  AS lsoa_code,\n    coalesce(l.name, l.LSOA_Name, l.code)   AS lsoa_name,\n    l.deprivation                           AS deprivation,\n    l.wimd_decile                           AS wimd_decile,\n    s.fsm_pct                               AS fsm_pct,\n    s.attendance_pct                        AS attendance_pct,\n    s.capped9_score                         AS capped9_score\nORDER BY fsm_pct DESC\nLIMIT $limit\n'),
}
SCHOOL_LENS_MODES = {
    "same": ("Schools in the same LSOA",
             "School --LOCATED_IN--> LSOA <--LOCATED_IN-- School",
             "Project-integrated"),
    "touch": ("Schools in LSOAs that touch mine",
              "School --LOCATED_IN--> LSOA --LSOA_TOUCHES--> LSOA <--LOCATED_IN-- School",
              "Project-integrated, then Geometry-origin"),
    "near": ("Schools in LSOAs graph-near mine (two touches-steps)",
             "School --LOCATED_IN--> LSOA --GRAPH_NEAR--> LSOA <--LOCATED_IN-- School",
             "Project-integrated, then Derived from Geometry-origin"),
}


def school_lens_options(cfg):
    """Schools placed in an LSOA, so a spatial answer is possible."""
    return safe_options(cfg, """
    MATCH (s:School)-[:LOCATED_IN]->(l:LSOA)
    WHERE s.code IS NOT NULL
    RETURN DISTINCT s.code AS value,
           coalesce(s.school_name, s.name, s.code)
             + ' | ' + coalesce(l.name, l.code) AS label
    ORDER BY label
    LIMIT 20000
    """)


def types_with_intersects(cfg):
    """Administrative types that can reach an LSOA, and therefore schools.

    A verified count returned Community 8,423, UnitaryAuthority 2,407,
    Ward 2,344 and nothing else. Types outside this set can still be asked
    about as units; they simply cannot carry a school answer, and saying so
    is part of the result rather than a failure of the interface.
    """
    return {
        str(v) for v, _ in safe_options(cfg, """
        MATCH (a:AdminUnit)-[:INTERSECTS]->(:LSOA)
        RETURN DISTINCT a.type AS value, a.type AS label
        """)
    }


def nl_admin_options(cfg):
    """Every named administrative unit the question box should recognise.

    Scoped to units that intersect an LSOA. Every LSOA in this graph is
    Welsh, so this is the Welsh administrative geography and nothing else.
    Without the scope the list carried the whole of Great Britain, and a
    question about Cathays resolved to a ward in Devon because a naive
    substring match had 19,000 more chances to be wrong.

    The box previously resolved names against `admin_options(cfg,
    "admin_parent")`, which returns only units that HAVE a child. A Community
    such as Cathays has none, so it was never recognised, `admin` came back
    empty, and every school question fell through to an LSOA-anchored form
    that then asked for an LSOA the sentence never named. This list is the
    three types that can anchor a question, whether or not they are parents.
    """
    return safe_options(cfg, """
    MATCH (a:AdminUnit)
    WHERE a.type IN ['Ward', 'Community', 'UnitaryAuthority']
      AND a.uri IS NOT NULL
      AND EXISTS { MATCH (a)-[:INTERSECTS]->(:LSOA) }
    RETURN DISTINCT
        a.uri AS value,
        coalesce(a.name, a.uri) + ' | ' + a.type AS label
    ORDER BY label
    LIMIT 25000
    """)


def lens_anchor_options(cfg, unit_type):
    """Administrative units of one type that can reach an LSOA at all."""
    return safe_options(cfg, f"""
    MATCH (a:AdminUnit)
    WHERE a.type = '{unit_type}'
      AND (
        EXISTS {{ MATCH (a)-[:INTERSECTS]->(:LSOA) }}
        OR EXISTS {{ MATCH (a)-[:TOUCHES]-(:AdminUnit)-[:INTERSECTS]->(:LSOA) }}
        OR EXISTS {{ MATCH (a)<-[:WITHIN]-(:AdminUnit)-[:INTERSECTS]->(:LSOA) }}
      )
    RETURN DISTINCT a.uri AS value,
           coalesce(a.name, a.uri) + ' | {unit_type}' AS label
    ORDER BY label
    LIMIT 20000
    """)


def lens_unit_types(cfg):
    """Every administrative type present, most numerous first."""
    return [
        str(v) for v, _ in safe_options(cfg, """
        MATCH (a:AdminUnit)
        RETURN a.type AS value, a.type + ' (' + toString(count(*)) + ')' AS label
        ORDER BY count(*) DESC
        """)
    ]


# Units-as-answer variants. The same relation heads as the school lens, but
# returning the administrative units themselves. "Which communities are near
# Cathays" is a question ABOUT communities: answering it with schools would
# answer a different question. Near follows the IJGI 2024 definition exactly:
# disjoint, with a path of two touches edges.
LENS_UNIT_CYPHER = {
    'not_touches': (
        'MATCH (anchor:AdminUnit {uri:$admin})\nMATCH (nbr:AdminUnit)\n'
        'WHERE nbr <> anchor\n'
        '  AND nbr.type = coalesce($nbr_type, anchor.type)\n'
        '  AND NOT (anchor)-[:TOUCHES]-(nbr)\n'
        '  AND EXISTS { MATCH (nbr)-[:INTERSECTS]->(:LSOA) }\n'
        '\nWITH DISTINCT nbr\nOPTIONAL MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\nOPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\nRETURN\n    nbr.uri AS unit_uri,\n    coalesce(nbr.name, nbr.uri) AS unit,\n    nbr.type AS unit_type,\n    count(DISTINCT l) AS lsoas,\n    collect(DISTINCT l.code)[0..60] AS lsoa_codes,\n    count(DISTINCT s) AS schools,\n    round(avg(s.fsm_pct), 1) AS avg_fsm_pct,\n    round(avg(s.attendance_pct),1) AS avg_attendance_pct\nORDER BY unit\nLIMIT $limit\n'
    ),
    'touches': (
        'MATCH (anchor:AdminUnit {uri:$admin})-[:TOUCHES]-(nbr:AdminUnit)\nWHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n'
        '\nWITH DISTINCT nbr\nOPTIONAL MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\nOPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\nRETURN\n    nbr.uri                       AS unit_uri,\n    coalesce(nbr.name, nbr.uri)   AS unit,\n    nbr.type                      AS unit_type,\n    count(DISTINCT l)             AS lsoas,\n    collect(DISTINCT l.code)[0..60] AS lsoa_codes,\n    count(DISTINCT s)             AS schools,\n    round(avg(s.fsm_pct), 1)      AS avg_fsm_pct,\n    round(avg(s.attendance_pct),1) AS avg_attendance_pct\nORDER BY unit\nLIMIT $limit\n'
    ),
    'near': (
        'MATCH (anchor:AdminUnit {uri:$admin})-[:TOUCHES]-(mid:AdminUnit)-[:TOUCHES]-(nbr:AdminUnit)\nWHERE mid.type = anchor.type\n  AND nbr.type = anchor.type\n  AND nbr <> anchor\n  AND NOT (anchor)-[:TOUCHES]-(nbr)\n  AND ($nbr_type IS NULL OR nbr.type = $nbr_type)\n'
        '\nWITH DISTINCT nbr\nOPTIONAL MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\nOPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\nRETURN\n    nbr.uri                       AS unit_uri,\n    coalesce(nbr.name, nbr.uri)   AS unit,\n    nbr.type                      AS unit_type,\n    count(DISTINCT l)             AS lsoas,\n    collect(DISTINCT l.code)[0..60] AS lsoa_codes,\n    count(DISTINCT s)             AS schools,\n    round(avg(s.fsm_pct), 1)      AS avg_fsm_pct,\n    round(avg(s.attendance_pct),1) AS avg_attendance_pct\nORDER BY unit\nLIMIT $limit\n'
    ),
    'inside': (
        'MATCH (anchor:AdminUnit {uri:$admin})<-[:WITHIN]-(nbr:AdminUnit)\nWHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n'
        '\nWITH DISTINCT nbr\nOPTIONAL MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\nOPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\nRETURN\n    nbr.uri                       AS unit_uri,\n    coalesce(nbr.name, nbr.uri)   AS unit,\n    nbr.type                      AS unit_type,\n    count(DISTINCT l)             AS lsoas,\n    collect(DISTINCT l.code)[0..60] AS lsoa_codes,\n    count(DISTINCT s)             AS schools,\n    round(avg(s.fsm_pct), 1)      AS avg_fsm_pct,\n    round(avg(s.attendance_pct),1) AS avg_attendance_pct\nORDER BY unit\nLIMIT $limit\n'
    ),
    'contains': (
        'MATCH (anchor:AdminUnit {uri:$admin})-[:WITHIN]->(nbr:AdminUnit)\nWHERE ($nbr_type IS NULL OR nbr.type = $nbr_type)\n'
        '\nWITH DISTINCT nbr\nOPTIONAL MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\nOPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\nRETURN\n    nbr.uri                       AS unit_uri,\n    coalesce(nbr.name, nbr.uri)   AS unit,\n    nbr.type                      AS unit_type,\n    count(DISTINCT l)             AS lsoas,\n    collect(DISTINCT l.code)[0..60] AS lsoa_codes,\n    count(DISTINCT s)             AS schools,\n    round(avg(s.fsm_pct), 1)      AS avg_fsm_pct,\n    round(avg(s.attendance_pct),1) AS avg_attendance_pct\nORDER BY unit\nLIMIT $limit\n'
    )
}

LENS_MODES["near"] = (
    "Units two touches-steps away (near)",
    "AdminUnit --TOUCHES--> AdminUnit --TOUCHES--> AdminUnit "
    "--INTERSECTS--> LSOA <--LOCATED_IN-- School",
    "Derived from Native, then Geometry-origin, then Project-integrated",
)
LENS_MODES["not_touches"] = (
    "Units of the same division that do NOT TOUCH this one",
    "AdminUnit --NOT TOUCHES-- AdminUnit --INTERSECTS--> LSOA",
    "Query-derived DISJOINT complement of Native TOUCHES",
)
LENS_CYPHER["near"] = (
    'MATCH (anchor:AdminUnit {uri:$admin})-[:TOUCHES]-(mid:AdminUnit)-[:TOUCHES]-(nbr:AdminUnit)\nWHERE mid.type = anchor.type\n  AND nbr.type = anchor.type\n  AND nbr <> anchor\n  AND NOT (anchor)-[:TOUCHES]-(nbr)\n  AND ($nbr_type IS NULL OR nbr.type = $nbr_type)\n'
    + _LENS_TAIL.replace("__VIA__", _LENS_NBR).replace("__VIATYPE__", "nbr.type")
)
LENS_CYPHER["not_touches"] = (
    'MATCH (anchor:AdminUnit {uri:$admin})\nMATCH (nbr:AdminUnit)\n'
    'WHERE nbr <> anchor\n'
    '  AND nbr.type = coalesce($nbr_type, anchor.type)\n'
    '  AND NOT (anchor)-[:TOUCHES]-(nbr)\n'
    '  AND EXISTS { MATCH (nbr)-[:INTERSECTS]->(:LSOA) }\n'
    'MATCH (nbr)-[:INTERSECTS]->(l:LSOA)\n'
    + _LENS_TAIL.replace("__VIA__", _LENS_NBR).replace("__VIATYPE__", "nbr.type")
)

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
            "Between is demonstrated as cycle-free paths over "
            "LSOA_TOUCHES, following the paper's definition. The hop bound "
            "is a tractability necessity, not a definitional choice, and "
            "is reported with the result. Its education-policy fit is "
            "still weak or optional, because the paper poses no between "
            "question for this domain."
        ),
        "relation": "LSOA_TOUCHES path",
        "provenance": "Derived from geometry-origin",
        "param_type": "lsoa_pair",
        "result_label": "Cycle-free paths found",
        "evaluation_note": (
            "Demonstrator reasoning pattern: Implemented. "
            "Education-policy fit: Weak / optional."
        ),
        "cypher": SCQ3_CYPHER_TEMPLATE.replace("__MAXHOPS__", "6"),
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
        "param_type_reverse": "admin_intersects",
        "cypher_reverse": SCQ7_REVERSE_CYPHER,
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
        "param_type_reverse": "admin_intersects",
        "cypher_reverse": SCQ8_REVERSE_CYPHER,
        "result_label": "Nearby cross-hierarchy units found",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No."
        ),
        "cypher": SCQ8_ANSWER_CYPHER,
        "cypher_evidence": SCQ8_EVIDENCE_CYPHER,
        "cypher_reverse_evidence": SCQ8_REVERSE_EVIDENCE_CYPHER,
    },

    "LENS": {
        "label": "Education lens \u2014 schools through any stored relation (not an SCQ form)",
        "question": (
            "Which schools are reachable from the selected administrative "
            "unit through the relation you choose?"
        ),
        "task": "Integration demonstration",
        "keyword_sentence": (
            "This is not a ninth spatial form. It lets one question travel "
            "along any relation the graph already holds \u2014 native "
            "TOUCHES or WITHIN between administrative units, then the "
            "geometry-origin INTERSECTS into statistical geography, then the "
            "School data join \u2014 and reports the provenance of every "
            "link separately. It demonstrates composition; it raises no "
            "coverage score."
        ),
        "relation": "chosen at run time",
        "provenance": "mixed \u2014 shown per link",
        "param_type": "education_lens",
        "result_label": "Schools reached",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No. "
            "Counts toward model completeness: No."
        ),
        "cypher": LENS_CYPHER["direct"],
    },

    "SCHOOL_LENS": {
        "label": "From a school \u2014 nearby schools through computed LSOA relations (not an SCQ form)",
        "question": "Which schools are near the selected school, through the computed LSOA adjacency?",
        "task": "Integration demonstration",
        "keyword_sentence": (
            "This travels the computed statistical side of the graph rather "
            "than the native administrative one: LSOA_TOUCHES is "
            "geometry-origin and GRAPH_NEAR is derived from it. YAGO2geo "
            "asserts neither, which is why this question is unanswerable "
            "from the original model and answerable after integration."
        ),
        "relation": "LOCATED_IN + LSOA_TOUCHES / GRAPH_NEAR",
        "provenance": "Project-integrated, then Geometry-origin",
        "param_type": "school_lens",
        "result_label": "Nearby schools",
        "evaluation_note": (
            "Demonstrator answer: Yes. "
            "Native education-use-case model answer: No. "
            "Counts toward model completeness: No."
        ),
        "cypher": SCHOOL_LENS_CYPHER["touch"],
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

    inject_segmented_css()
    st.session_state["ui_lang"] = "English"

    # One deliberately light visual system. The former dark-mode toggle was
    # removed because it split the demonstrator into two partly matched skins.
    cfg["dark_theme"] = False
    st.session_state.dark_theme = False

    try:
        # Connection is only surfaced when it FAILS. A healthy connection is
        # the expected state and needs no permanent badge; an unhealthy one
        # explains why pages look empty.
        _ = scalar(cfg, "RETURN 1", default=1)
    except Exception:
        st.warning("Database not connected")

    # "Task Overview" and "Visual Story" were development-time learning aids
    # and are intentionally removed from the submission navigation. Their
    # page functions remain below, uncalled: to restore one for a supervision
    # demo, add its name back to this list.
    # Two pages were removed from the delivered site on purpose:
    #   Cross-hierarchy — merged into the demonstrator, where its seam
    #     diagram and counts now sit directly under SCQ7 and SCQ8.
    #   Policy Questions — the derivation of the eight questions from the
    #     education-inequality literature is an argument made in the
    #     dissertation text, not a screen to click through.
    # Both page functions remain in the code, uncalled.
    # The Evaluation page was used during development and dissertation
    # analysis, but is not exposed in the delivered demonstrator.  Its page
    # function remains below for reproducibility, while the SCQ mapping stays
    # available through the SCQ Demonstrator.
    pages = ["SCQ Demonstrator", "Map"]
    if "page" not in st.session_state or st.session_state.page not in pages:
        st.session_state.page = "SCQ Demonstrator"

    cfg["page"] = st.session_state.page
    return cfg


def set_page(page_name: str) -> None:
    """Switch between the two public experiences before the next rerun."""
    if page_name == "Map" and st.session_state.get("page") != "Map":
        st.session_state["map_has_run"] = False
    st.session_state.page = page_name


def edit_map_search() -> None:
    """Return from the map result to its two search routes."""
    st.session_state["map_has_run"] = False


def render_page_switcher(page: str) -> None:
    """Two centred tabs for the public SCQ and Map experiences."""
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button{
          border-radius:14px!important;
          min-height:3rem!important;
          font-weight:800!important;
          letter-spacing:.005em!important;
          transition:transform .16s ease,box-shadow .16s ease,
                     border-color .16s ease,filter .16s ease!important;
          will-change:transform;
        }
        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stDownloadButton"] button[kind="primary"]{
          color:#fff!important;
          background:linear-gradient(135deg,#ff6575 0%,#ff8b6d 55%,#ffad63 100%)!important;
          border:1px solid rgba(190,70,54,.28)!important;
          border-bottom:4px solid #cf5548!important;
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,.48),
            inset 0 -8px 16px rgba(190,70,54,.08),
            0 9px 18px rgba(219,84,65,.22),
            0 2px 4px rgba(87,45,37,.14)!important;
          text-shadow:0 1px 1px rgba(91,42,34,.18)!important;
        }
        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stDownloadButton"] button[kind="secondary"]{
          color:#4b302a!important;
          background:linear-gradient(180deg,#fffdfa 0%,#fff5ee 100%)!important;
          border:1px solid #edc9bb!important;
          border-bottom:4px solid #ddb09f!important;
          box-shadow:
            inset 0 1px 0 #fff,
            inset 0 -7px 14px rgba(193,112,84,.045),
            0 7px 14px rgba(91,48,38,.10),
            0 2px 3px rgba(91,48,38,.08)!important;
        }
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover{
          transform:translateY(-2px)!important;
          filter:saturate(1.04) brightness(1.015)!important;
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,.7),
            0 12px 22px rgba(157,76,58,.18),
            0 4px 7px rgba(91,48,38,.10)!important;
        }
        div[data-testid="stButton"] button:active,
        div[data-testid="stDownloadButton"] button:active{
          transform:translateY(2px)!important;
          border-bottom-width:1px!important;
          box-shadow:inset 0 3px 7px rgba(103,47,37,.16),
                     0 2px 4px rgba(91,48,38,.10)!important;
        }
        div[data-testid="stButton"] button:focus-visible,
        div[data-testid="stDownloadButton"] button:focus-visible{
          outline:3px solid rgba(255,143,105,.34)!important;
          outline-offset:3px!important;
        }
        div[data-testid="stButton"] button:disabled{
          transform:none!important;filter:grayscale(.15)!important;
          opacity:.58!important;box-shadow:none!important;
        }
        html{scroll-behavior:smooth}
        .st-key-page_scq_demonstrator,
        .st-key-page_map{
          animation:page-enter .34s cubic-bezier(.22,.75,.24,1) both;
          transform-origin:50% 0;
        }
        .guided-hero,.map-search-hero{
          position:relative;isolation:isolate;overflow:hidden;
          transform:perspective(1200px) translateZ(0);
          animation:hero-settle .55s cubic-bezier(.2,.8,.2,1) both;
          border:1px solid rgba(255,255,255,.38)!important;
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,.52),
            inset 0 -18px 35px rgba(186,71,52,.07),
            0 28px 58px rgba(143,68,50,.18),
            0 7px 16px rgba(95,49,39,.08)!important;
        }
        .guided-hero:after,.map-search-hero:after{
          content:"";position:absolute;z-index:-1;inset:-35% -12% auto auto;
          width:58%;height:115%;border-radius:50%;
          background:radial-gradient(circle,rgba(255,255,255,.28),transparent 66%);
          transform:rotate(-12deg);pointer-events:none;
        }
        div[data-testid="stSelectbox"]>div>div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stMetric"],
        div[data-testid="stDataFrame"],
        div[data-testid="stExpander"]{
          transition:transform .2s cubic-bezier(.2,.75,.25,1),
                     box-shadow .2s ease,border-color .2s ease!important;
        }
        div[data-testid="stSelectbox"]>div>div:hover,
        div[data-testid="stTextInput"] input:hover,
        div[data-testid="stNumberInput"] input:hover{
          transform:translateY(-2px)!important;
          border-color:#ee9e82!important;
          box-shadow:0 12px 24px rgba(118,60,46,.12)!important;
        }
        div[data-testid="stMetric"]:hover,
        div[data-testid="stExpander"]:hover{
          transform:translateY(-3px)!important;
          box-shadow:0 17px 34px rgba(103,53,41,.12)!important;
        }
        div[data-testid="stDeckGlJsonChart"]{
          animation:result-rise .48s cubic-bezier(.2,.8,.2,1) both;
          transform-origin:50% 20%;
        }
        div[data-testid="stDataFrame"]{
          animation:result-rise .55s .06s cubic-bezier(.2,.8,.2,1) both;
        }
        button[data-baseweb="tab"]{
          transition:color .18s ease,background .18s ease,
                     transform .18s ease!important;
          border-radius:12px 12px 0 0!important;
        }
        button[data-baseweb="tab"]:hover{
          background:#fff4ed!important;transform:translateY(-1px)!important;
        }
        @keyframes page-enter{
          from{opacity:0;transform:translateY(10px) scale(.995)}
          to{opacity:1;transform:translateY(0) scale(1)}
        }
        @keyframes hero-settle{
          from{opacity:0;transform:perspective(1200px) rotateX(2.5deg) translateY(14px)}
          to{opacity:1;transform:perspective(1200px) rotateX(0) translateY(0)}
        }
        @keyframes result-rise{
          from{opacity:0;transform:translateY(18px) scale(.992)}
          to{opacity:1;transform:translateY(0) scale(1)}
        }
        @media (prefers-reduced-motion:reduce){
          html{scroll-behavior:auto}
          *,*:before,*:after{
            animation-duration:.01ms!important;
            animation-iteration-count:1!important;
            transition-duration:.01ms!important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    pad_left, scq, map_col, pad_right = st.columns([1, 2.2, 2.2, 1])
    with scq:
        st.button("SCQ Search", key="nav_tab_scq", use_container_width=True,
                  type="primary" if page == "SCQ Demonstrator" else "secondary",
                  on_click=set_page, args=("SCQ Demonstrator",))
    with map_col:
        st.button("Map Explorer", key="nav_tab_map", use_container_width=True,
                  type="primary" if page == "Map" else "secondary",
                  on_click=set_page, args=("Map",))


def apply_dashboard_theme(dark_theme: bool) -> None:
    """Apply a compact infographic-inspired light/dark skin."""
    if dark_theme:
        # A calm dark slate rather than saturated blue: long reading sessions
        # need low chroma. Accents are desaturated to sit on it without
        # vibrating, which is what made red text on blue hard to read.
        app_bg = "linear-gradient(180deg,#141821 0%,#191d28 50%,#12161e 100%)"
        sidebar_bg = "linear-gradient(180deg,#1a1f2b 0%,#141821 100%)"
        panel_bg = "rgba(255,255,255,.055)"
        panel_border = "rgba(255,255,255,.10)"
        text = "#e8eaf0"
        muted = "#a3abbb"
        sidebar_text = "#e8eaf0"
        metric_bg = "rgba(255,255,255,.07)"
        hero = "#D73648"
        nav_bg = "rgba(255,255,255,.06)"
        nav_active = "linear-gradient(135deg,#9a3412,#c2410c)"
        map_tiles = "dark"
        ok_color = "#7ddba1"
        geo_color = "#f0a868"
        derived_color = "#b7a6f0"
        field_bg = "rgba(255,255,255,.06)"
        field_border = "rgba(255,255,255,.15)"
        field_focus = "#f0a868"
        field_glow = "rgba(240,168,104,.18)"
        field_label = "#cbd3e1"
        option_hover = "rgba(255,255,255,.09)"
        option_hover_text = "#f5d0b0"
        accent_grad = "linear-gradient(135deg,#7a1224,#9e1b32)"
        # The search frame and its magnifier: white on the dark skin.
        search_ink = "#ffffff"
        search_icon = "%23ffffff"
        ev_bg = "rgba(255,255,255,.045)"
        ev_border = "rgba(255,255,255,.12)"
        ev_quote_bg = "rgba(255,255,255,.06)"
        ev_full = "#7ddba1"
        ev_partial = "#f0a868"
        ev_none = "#9aa4b5"
        ev_full_bg = "rgba(125,219,161,.14)"
        ev_partial_bg = "rgba(240,168,104,.14)"
        ev_none_bg = "rgba(154,164,181,.14)"
    else:
        # Cardiff University red, used as a soft warm tint rather than grey.
        app_bg = "#ffffff"
        sidebar_bg = "#ffffff"
        panel_bg = "#ffffff"
        panel_border = "#e5e7eb"
        text = "#303443"
        muted = "#596273"
        sidebar_text = "#303443"
        metric_bg = "#ffffff"
        hero = "#D73648"
        nav_bg = "#ffffff"
        nav_active = "linear-gradient(135deg,#D73648,#b8283f)"
        map_tiles = "light"
        ok_color = "#15803d"
        geo_color = "#ea580c"
        derived_color = "#7c3aed"
        field_bg = "#ffffff"
        field_border = "#eccace"
        field_focus = "#D73648"
        field_glow = "rgba(215,54,72,.16)"
        field_label = "#8a1e2b"
        option_hover = "#fdeef1"
        option_hover_text = "#8a1e2b"
        accent_grad = "linear-gradient(135deg,#D73648,#b8283f)"
        # Cardiff red, sampled from the crest, so the box reads as a search
        # field at a glance rather than as one more input.
        search_ink = "#D73648"
        search_icon = "%23D73648"
        ev_bg = "#ffffff"
        ev_border = "#e8d5cf"
        ev_quote_bg = "#faf7f5"
        ev_full = "#15803d"
        ev_partial = "#a8620a"
        ev_none = "#5f6875"
        ev_full_bg = "rgba(21,128,61,.10)"
        ev_partial_bg = "rgba(168,98,10,.10)"
        ev_none_bg = "rgba(95,104,117,.10)"

    st.session_state.map_tiles = map_tiles
    st.markdown(
        f"""
<style>
:root {{
  --field-bg:{field_bg};
  --field-border:{field_border};
  --field-focus:{field_focus};
  --field-glow:{field_glow};
  --field-label:{field_label};
  --option-hover:{option_hover};
  --option-hover-text:{option_hover_text};
  --accent-grad:{accent_grad};
}}
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
.hero {{ position:relative; }}
.hero {{
  display:flex;
  align-items:center;
  gap:1.4rem;
}}
.hero-main {{ flex:1 1 auto; min-width:0; }}
/* Height is fixed and the width follows the artwork, so any silhouette of
   Wales sits at the same optical weight as the title block beside it. */
.hero-wales {{
  flex:0 0 auto;
  height:240px;          /* the one number to change if you want it bigger */
  width:auto;
  max-width:42%;
  object-fit:contain;
  align-self:center;
  margin:-.6rem -.4rem -.6rem 0;
  filter:drop-shadow(0 4px 12px rgba(0,0,0,.22));
}}
@media (max-width: 820px) {{
  .hero {{ display:block; }}
  .hero-wales {{ display:none; }}
}}
.hero-logo {{
  display:block;
  height:52px;
  width:auto;
  margin:0 0 .85rem 0;
  background:#fff;
  border-radius:8px;
  padding:6px 10px;
  box-shadow:0 3px 10px rgba(0,0,0,.14);
}}
.hero-inst {{
  font-size:.72rem; font-weight:800; letter-spacing:.16em;
  text-transform:uppercase; opacity:.85; margin-bottom:.35rem;
}}
.hero-people {{
  display:flex; flex-wrap:wrap; gap:1.6rem;
  margin:.75rem 0 .5rem; font-size:.82rem; line-height:1.35rem;
}}
.hero-people b {{
  font-size:.68rem; letter-spacing:.1em; text-transform:uppercase;
  opacity:.85;
}}
.hero-rule {{ margin-top:.35rem; }}

/* Selected radio and tab labels kept legible on the dark skin, where the
   accent fill is dark enough to swallow dark text. */
div[role="radiogroup"] label[data-baseweb="radio"] div {{
  color:{text} !important;
}}
.stTabs [aria-selected="true"] p {{ color:{text} !important; }}
.stRadio label p, .stSelectbox label p, .stTextInput label p {{
  color:{muted} !important;
}}

/* ---- natural-language search ---- */
.nl-wrap {{
  background:{accent_grad};
  border-radius:14px 14px 0 0;
  padding:.85rem 1.1rem .7rem;
  color:#fff;
  margin-top:1.7rem;
}}
.nl-title {{ font-size:1.02rem; font-weight:800; letter-spacing:.01em; }}
.nl-sub {{ font-size:.8rem; opacity:.92; margin-top:.15rem; line-height:1.35rem; }}

/* The two question boxes are the only text inputs in the app, so they can be
   framed directly. A Cardiff-red rule and an inline magnifier make the field
   read as a search engine instead of another form control. The glyph is an
   SVG data URI recoloured per theme, so nothing is fetched over the network
   and it stays crisp at any zoom. */
div[data-testid="stTextInput"] input {{
  border:2px solid {search_ink} !important;
  border-radius:12px !important;
  padding-left:2.6rem !important;
  font-size:.95rem !important;
  background-color:{field_bg} !important;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{search_icon}' stroke-width='2.1' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><line x1='16.2' y1='16.2' x2='21' y2='21'/></svg>") !important;
  background-repeat:no-repeat !important;
  background-position:left .8rem center !important;
  background-size:17px 17px !important;
  transition:box-shadow .15s ease, border-color .15s ease;
}}
div[data-testid="stTextInput"] input:focus {{
  box-shadow:0 0 0 3px {field_glow} !important;
}}
.nl-read {{
  background:{ev_bg};
  border:1px solid {ev_border};
  border-radius:12px;
  padding:.75rem .95rem;
  margin:.55rem 0 .9rem;
  color:{text};
}}
.nl-read-title {{
  font-size:.66rem; font-weight:800; letter-spacing:.13em;
  text-transform:uppercase; color:{muted}; margin-bottom:.45rem;
}}
.nl-chips {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
.nl-chip {{
  font-size:.76rem; font-weight:700; padding:.2rem .6rem;
  border-radius:999px; border:1px solid {ev_border};
}}
.nl-chip-rel {{ color:{field_focus}; background:{ev_quote_bg}; font-family:ui-monospace,Consolas,monospace; }}
.nl-chip-focus {{ color:{ev_partial}; background:{ev_partial_bg}; }}
.nl-chip-area {{ color:{ev_full}; background:{ev_full_bg}; }}
.nl-steps {{ margin:.6rem 0 0; padding-left:1.15rem; }}
.nl-steps li {{ font-size:.83rem; line-height:1.5rem; color:{muted}; }}
.ql-head {{
  border-radius:10px;
  padding:.55rem .8rem;
  margin:.3rem 0 .6rem;
  border-left:5px solid currentColor;
  background:{ev_quote_bg};
}}
.ql-rel {{
  display:block; font-size:.72rem; font-weight:800;
  letter-spacing:.12em; text-transform:uppercase;
}}
.ql-inst {{
  display:block; font-size:.84rem; line-height:1.45rem;
  color:{text}; opacity:.86; margin-top:.2rem;
}}
.ql-scq1 {{ color:#2563eb; }}
.ql-scq2 {{ color:#0d9488; }}
.ql-scq3 {{ color:#7c3aed; }}
.ql-scq4 {{ color:#64748b; }}
.ql-scq5 {{ color:#c2410c; }}
.ql-scq6 {{ color:#b45309; }}
.ql-scq7 {{ color:#15803d; }}
.ql-scq8 {{ color:#be185d; }}
[data-testid="stExpander"] .stButton button {{
  border-radius:999px !important;
  text-align:left !important;
  font-size:.82rem !important;
  padding:.35rem .85rem !important;
  white-space:normal !important;
  line-height:1.35rem !important;
}}

.nl-driven {{
  background:{ev_quote_bg};
  border:1px solid {ev_border};
  border-left:4px solid {field_focus};
  border-radius:10px;
  padding:.5rem .8rem;
  font-size:.85rem;
  line-height:1.45rem;
  color:{text};
  margin:.2rem 0 .5rem;
}}
.nl-src {{
  display:inline-block; font-size:.72rem; font-weight:700;
  padding:.2rem .65rem; border-radius:999px; margin-bottom:.5rem;
  border:1px solid {ev_border};
}}
.nl-src-rule {{ color:{ev_full}; background:{ev_full_bg}; }}
.nl-src-llm {{ color:{ev_partial}; background:{ev_partial_bg}; }}
.nl-warn {{
  margin-top:.5rem; font-size:.82rem; color:{ev_partial};
  background:{ev_partial_bg}; border-radius:8px; padding:.4rem .6rem;
}}

/* ---- Task 3 evidence block ---- */
.ev-inst {{
  background:{ev_quote_bg};
  border:1px solid {ev_border};
  border-left:4px solid {field_focus};
  border-radius:10px;
  padding:.7rem .9rem;
  margin:.5rem 0 .8rem;
  font-size:.94rem;
  line-height:1.55rem;
  color:{text};
}}
.ev-inst-label {{
  display:block;
  font-size:.66rem;
  font-weight:800;
  letter-spacing:.12em;
  text-transform:uppercase;
  color:{field_focus};
  margin-bottom:.25rem;
}}
.ev-block, .ev-qs {{
  background:{ev_bg};
  border:1px solid {ev_border};
  border-radius:12px;
  padding:.85rem 1rem;
  margin:.55rem 0;
  color:{text};
}}
.ev-title {{
  font-size:.68rem;
  font-weight:800;
  letter-spacing:.12em;
  text-transform:uppercase;
  color:{muted};
  margin-bottom:.6rem;
}}
.ev-card {{
  border:1px solid {ev_border};
  border-left:4px solid {ev_none};
  border-radius:10px;
  padding:.65rem .8rem;
  margin-bottom:.55rem;
}}
.ev-card.ev-full {{ border-left-color:{ev_full}; }}
.ev-card.ev-partial {{ border-left-color:{ev_partial}; }}
.ev-head {{
  display:flex; align-items:center; gap:.6rem;
  flex-wrap:wrap; margin-bottom:.4rem;
}}
.ev-source {{ font-weight:800; font-size:.86rem; color:{text}; }}
.ev-verdict {{
  margin-left:auto;
  font-size:.68rem; font-weight:800;
  letter-spacing:.06em; text-transform:uppercase;
  padding:.15rem .55rem; border-radius:999px;
}}
.ev-verdict.ev-full {{ color:{ev_full}; background:{ev_full_bg}; }}
.ev-verdict.ev-partial {{ color:{ev_partial}; background:{ev_partial_bg}; }}
.ev-verdict.ev-none {{ color:{ev_none}; background:{ev_none_bg}; }}
.ev-quote {{
  font-style:italic;
  background:{ev_quote_bg};
  border-radius:8px;
  padding:.45rem .65rem;
  font-size:.9rem;
  line-height:1.5rem;
  color:{text};
}}
.ev-page {{ font-size:.74rem; color:{muted}; margin:.25rem 0 .45rem; }}
.ev-empty {{
  display:inline-block;
  font-size:.7rem; font-weight:800; letter-spacing:.1em;
  color:{ev_none}; background:{ev_none_bg};
  border:1px dashed {ev_border};
  padding:.28rem .6rem; border-radius:6px;
  margin-bottom:.45rem;
}}
.ev-warrant {{ font-size:.88rem; line-height:1.5rem; color:{text}; }}
.ev-note {{ font-size:.78rem; color:{muted}; margin-top:.3rem; }}
.ev-assess {{
  background:{ev_quote_bg};
  border-radius:10px;
  padding:.65rem .8rem;
  font-size:.88rem;
  line-height:1.55rem;
  color:{text};
}}
.ev-qs ol {{ margin:0; padding-left:1.2rem; }}
.ev-qs li {{ font-size:.9rem; line-height:1.6rem; margin-bottom:.2rem; color:{text}; }}
.ev-qs li::marker {{ color:{field_focus}; font-weight:800; }}
mark {{ color:inherit; }}

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

# PERFORMANCE NOTE
# The previous version opened a brand-new Neo4j driver for every single query
# and closed it again in a finally block. Each page render fires several
# queries, so the app paid a full connection handshake many times per click,
# which is the main reason the interface felt sluggish. The driver is designed
# to be created once and reused, so it is cached as a Streamlit resource and
# the per-query close is removed. Sessions are still opened and closed per
# query, which is the correct unit of work.
@st.cache_resource(show_spinner=False)
def _cached_driver(uri: str, user: str, password: str):
    return GraphDatabase.driver(uri, auth=(user, password))


def get_driver(cfg: Dict[str, str]):
    return _cached_driver(cfg["uri"], cfg["user"], cfg["password"])


def run_cypher(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None) -> pd.DataFrame:
    params = params or {}
    driver = get_driver(cfg)
    with driver.session(database=cfg["database"]) as session:
        rows = [dict(r) for r in session.run(cypher, params)]
    return pd.DataFrame(rows)


def scalar(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None, default: Any = 0) -> Any:
    df = run_cypher(cfg, cypher, params)
    if df.empty:
        return default
    return df.iloc[0, 0]


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_options(uri: str, user: str, password: str, database: str,
                    cypher: str) -> List[Tuple[str, str]]:
    """Dropdown contents cached for an hour.

    Streamlit re-executes the whole script on every widget interaction, so an
    uncached DISTINCT scan over every School node ran again on each keystroke
    and on every Clear. The option lists change only when the graph is
    reloaded, so an hour-long cache is safe and removes those round trips.
    """
    cfg = {"uri": uri, "user": user, "password": password, "database": database}
    df = run_cypher(cfg, cypher)
    if df.empty:
        return []
    return [(str(r["value"]), str(r["label"])) for _, r in df.iterrows()]


def safe_options(cfg: Dict[str, str], cypher: str, params: Dict[str, Any] | None = None) -> List[Tuple[str, str]]:
    if not params:
        return _cached_options(cfg["uri"], cfg["user"], cfg["password"],
                               cfg["database"], cypher)
    df = run_cypher(cfg, cypher, params)
    if df.empty:
        return []
    return [(str(r["value"]), str(r["label"])) for _, r in df.iterrows()]


@st.cache_data(ttl=3600, show_spinner=False)
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

    if mode == "admin_intersects":
        query = """
        MATCH (a:AdminUnit)
        WHERE a.type IN ['Ward', 'Community']
          AND EXISTS {
              MATCH (a)-[:INTERSECTS]->(:LSOA)
          }
        RETURN DISTINCT
            a.uri AS value,
            coalesce(a.name, a.uri) + ' | ' + a.type AS label
        ORDER BY label
        LIMIT 2000
        """
        return safe_options(cfg, query)

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
    LIMIT 20000
    """

    # The former cap of 500 silently truncated an alphabetically sorted list
    # of roughly 19,000 units, so anything past the early letters could not
    # be selected at all. The selectbox is type-to-search, so the full list
    # is usable.
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
@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def _image_data_uri(filename: str) -> str:
    """An image beside app.py as an inline data URI.

    Read from disk and embedded rather than linked, so the header renders
    identically offline and on a marker's machine with no network. A missing
    file returns an empty string and the header simply omits the image.
    """
    import base64

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    try:
        with open(path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""


def _logo_data_uri() -> str:
    return _image_data_uri("cardiff_logo.png")


def hero() -> None:
    logo = _logo_data_uri()
    crest = (
        f"<img class='hero-logo' src='{logo}' "
        "alt='Cardiff University' />" if logo else ""
    )
    # Drop wales_education_kg.png beside app.py and it appears on the right of
    # the header. If the file is absent the header keeps its old single-column
    # shape, so a missing image never breaks the page.
    wales_uri = _image_data_uri("wales_education_kg.png")
    wales = (
        f"<img class='hero-wales' src='{wales_uri}' alt='Wales' />"
        if wales_uri else ""
    )
    st.markdown(
        """
<div class="hero">
  <div class="hero-main">
  """
        + crest
        + """
  <div class="hero-inst">Cardiff University &middot; School of Computer Science and Informatics</div>
  <h1>Education Inequality Analysis with a Geospatial Knowledge Graph</h1>
  <div class="hero-people">
    <span><b>Student</b><br/>Afaf Alhajjaji &middot; MSc Computing</span>
    <span><b>Supervisor</b><br/>Dr Alia Abdelmoty</span>
    <span><b>Module</b><br/>CMT403 Dissertation</span>
  </div>
  </div>
  """
        + wales
        + """
</div>
""",
        unsafe_allow_html=True,
    )


def task_badge(task: str, keyword_sentence: str, status: str = "") -> None:
    """Page header. The status argument is accepted but no longer shown:
    progress labels belong in the research log, not on a delivered site."""
    st.markdown(
        f"""
<div class="task-card">
  <h3>{task}</h3>
  <div>{keyword_sentence}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_task_card(t: Dict[str, Any]) -> None:
    status = t["status"]
    cls = (
        "done" if ("Complete" in status or "Done" in status or "Closed" in status)
        else "current" if ("In progress" in status or "Current" in status)
        else "next"
    )
    solution = TASK_SOLUTIONS.get(t["id"], {})
    subtasks = "".join(
        [f"<div class='subtask'><b>{num} — {name}:</b> {desc}</div>" for num, name, desc in t["subtasks"]]
    )
    st.markdown(
        f"""
<div class="task-card">
  <span class="badge {cls}">{status}</span>
  <h3>{t['id']} — {t['title']}</h3>
  <p>{t['keyword_sentence']}</p>
  <div class="solutionbox"><b>Outcome:</b> {solution.get('answer','')}<br>
  <b>Evidence:</b> {solution.get('evidence','')}<br>
  <b>In the app:</b> {solution.get('app_section','')}</div>
  {subtasks}
</div>
""",
        unsafe_allow_html=True,
    )


# Card colour key, shared by every map card: each label keeps its own accent
# colour and its value inherits the same colour, so cards stay scannable.
C_HEAD = "#0b2a5b"
C_MUTED = "#64748b"
C_DEP = "#ff4f79"
C_WIMD = "#7c3aed"
C_FSM = "#ea580c"
C_ATT = "#0891b2"
C_PUP = "#0f766e"
C_PTR = "#b45309"
C_BUD = "#15803d"
C_PERF = "#2563eb"
C_TRAN = "#db2777"


def _school_card_fields(summary: Dict[str, Any]) -> Dict[str, str]:
    """Hover-card strings for one LSOA's schools, fixed in number.

    The card never lists school names: it would grow with the number of
    schools and cover the region it describes. Names live in the panel
    opened by clicking the region.
    """
    if not summary:
        return {
            "schools_n": "0",
            "fsm_txt": "N/A",
            "fsm_basis": "no school in this LSOA",
            "att_txt": "N/A",
            "att_basis": "no school in this LSOA",
            "cap_txt": "N/A",
            "cap_basis": "no school in this LSOA",
        }
    return {
        "schools_n": str(int(summary.get("school_count") or 0)),
        "fsm_txt": _fmt_mean(summary.get("fsm_avg"), summary.get("fsm_n"), "%"),
        "fsm_basis": _mean_basis(summary.get("fsm_n")),
        "att_txt": _fmt_mean(summary.get("att_avg"), summary.get("att_n"), "%"),
        "att_basis": _mean_basis(summary.get("att_n")),
        "cap_txt": _fmt_mean(summary.get("cap_avg"), summary.get("cap_n")),
        "cap_basis": _mean_basis(summary.get("cap_n")),
    }


def _school_tooltip_block() -> str:
    """The schools half of a region hover card: four fixed cells."""
    def cell(label: str, value_key: str, basis_key: str, colour: str) -> str:
        return (
            "<div style='background:rgba(248,250,252,.75);border-radius:8px;"
            "padding:5px 7px;'>"
            f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
            "text-transform:uppercase;letter-spacing:.05em;'>"
            f"{label}</div>"
            f"<div style='font-size:13px;font-weight:800;color:{colour};'>"
            "{" + value_key + "}</div>"
            f"<div style='font-size:8.5px;color:{C_MUTED};'>"
            "{" + basis_key + "}</div></div>"
        )

    return (
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:5px;'>"
        + "<div style='background:rgba(248,250,252,.75);border-radius:8px;"
          "padding:5px 7px;'>"
        + f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
          "text-transform:uppercase;letter-spacing:.05em;'>Schools</div>"
        + f"<div style='font-size:13px;font-weight:800;color:{C_HEAD};'>"
          "{schools_n}</div></div>"
        + cell("FSM", "fsm_txt", "fsm_basis", C_FSM)
        + cell("Attendance", "att_txt", "att_basis", C_ATT)
        + cell("Capped 9", "cap_txt", "cap_basis", C_PERF)
        + "</div>"
        + f"<div style='font-size:9.5px;color:{C_MUTED};margin-top:7px;'>"
          "Click the region to see the schools by name.</div>"
    )


# LSOA boundaries are stored in the graph as WKT in British National Grid
# (EPSG:27700) because load_to_neo4j.py reprojects everything to BNG before
# doing point-in-polygon. deck.gl needs lon/lat, so grid metres are converted
# here. Self-contained on purpose: no pyproj dependency in the deployed app.
# Accuracy is a few metres without OSTN15, which is far finer than an LSOA.
def bng_to_wgs84(east, north):
    a, b = 6377563.396, 6356256.909
    F0 = 0.9996012717
    lat0 = math.radians(49.0); lon0 = math.radians(-2.0)
    N0, E0 = -100000.0, 400000.0
    e2 = 1 - (b*b)/(a*a)
    n = (a-b)/(a+b); n2=n*n; n3=n2*n
    lat = lat0; M = 0.0
    while True:
        lat = (north - N0 - M)/(a*F0) + lat
        Ma = (1+n+1.25*n2+1.25*n3)*(lat-lat0)
        Mb = (3*n+3*n2+2.625*n3)*math.sin(lat-lat0)*math.cos(lat+lat0)
        Mc = (1.875*n2+1.875*n3)*math.sin(2*(lat-lat0))*math.cos(2*(lat+lat0))
        Md = (35.0/24.0)*n3*math.sin(3*(lat-lat0))*math.cos(3*(lat+lat0))
        M = b*F0*(Ma-Mb+Mc-Md)
        if abs(north - N0 - M) < 1e-5:
            break
    cosLat, sinLat = math.cos(lat), math.sin(lat)
    nu = a*F0/math.sqrt(1-e2*sinLat*sinLat)
    rho = a*F0*(1-e2)*pow(1-e2*sinLat*sinLat, -1.5)
    eta2 = nu/rho - 1
    tanLat = math.tan(lat); t2 = tanLat*tanLat; t4 = t2*t2; t6 = t4*t2
    secLat = 1.0/cosLat
    VII = tanLat/(2*rho*nu)
    VIII = tanLat/(24*rho*nu**3)*(5+3*t2+eta2-9*t2*eta2)
    IX = tanLat/(720*rho*nu**5)*(61+90*t2+45*t4)
    X = secLat/nu
    XI = secLat/(6*nu**3)*(nu/rho+2*t2)
    XII = secLat/(120*nu**5)*(5+28*t2+24*t4)
    XIIA = secLat/(5040*nu**7)*(61+662*t2+1320*t4+720*t6)
    dE = east - E0; dE2=dE*dE
    latA = lat - VII*dE2 + VIII*dE2*dE2 - IX*dE2*dE2*dE2
    lonA = lon0 + X*dE - XI*dE*dE2 + XII*dE*dE2*dE2 - XIIA*dE*dE2*dE2*dE2
    # Helmert OSGB36 -> WGS84
    H = 0.0
    sinP, cosP = math.sin(latA), math.cos(latA)
    sinL, cosL = math.sin(lonA), math.cos(lonA)
    nu2 = a/math.sqrt(1-e2*sinP*sinP)
    x1 = (nu2+H)*cosP*cosL; y1 = (nu2+H)*cosP*sinL
    z1 = ((1-e2)*nu2+H)*sinP
    tx, ty, tz = 446.448, -125.157, 542.060
    s = -20.4894e-6
    rx = math.radians(0.1502/3600); ry = math.radians(0.2470/3600); rz = math.radians(0.8421/3600)
    x2 = tx + x1*(1+s) - y1*rz + z1*ry
    y2 = ty + x1*rz + y1*(1+s) - z1*rx
    z2 = tz - x1*ry + y1*rx + z1*(1+s)
    a2, b2 = 6378137.0, 6356752.3142
    e22 = 1 - (b2*b2)/(a2*a2)
    p = math.sqrt(x2*x2+y2*y2)
    phi = math.atan2(z2, p*(1-e22))
    for _ in range(12):
        nu3 = a2/math.sqrt(1-e22*math.sin(phi)**2)
        phi = math.atan2(z2 + e22*nu3*math.sin(phi), p)
    return math.degrees(math.atan2(y2, x2)), math.degrees(phi)


def _wkt_rings(wkt_text: str) -> List[List[List[float]]]:
    """Turn a POLYGON / MULTIPOLYGON WKT string into deck.gl ring lists.

    Written without shapely so the deployed app needs no extra dependency.
    Only exterior rings are kept: holes are rare in LSOA boundaries and
    deck.gl renders the outline faithfully enough for a choropleth.
    """
    if not wkt_text:
        return []
    text = str(wkt_text).strip().upper()
    body = wkt_text[wkt_text.find("(") :] if "(" in wkt_text else ""
    if not body:
        return []
    rings: List[List[List[float]]] = []
    depth = 0
    current = ""
    for ch in body:
        if ch == "(":
            depth += 1
            if depth >= 2 if text.startswith("MULTIPOLYGON") else depth >= 1:
                current = ""
            continue
        if ch == ")":
            if current.strip():
                pts: List[List[float]] = []
                for pair in current.split(","):
                    bits = pair.strip().split()
                    if len(bits) >= 2:
                        try:
                            x, y = float(bits[0]), float(bits[1])
                        except ValueError:
                            continue
                        # Grid metres are always far outside lon/lat range,
                        # so magnitude is a safe discriminator.
                        if abs(x) > 180.0 or abs(y) > 90.0:
                            x, y = bng_to_wgs84(x, y)
                        pts.append([x, y])
                if len(pts) >= 3:
                    rings.append(pts)
                current = ""
            depth -= 1
            continue
        current += ch
    return rings


def _point_in_ring(longitude: float, latitude: float,
                   ring: List[List[float]]) -> bool:
    """Ray-casting containment for one WGS84 polygon ring."""
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        crosses = ((yi > latitude) != (yj > latitude))
        if crosses:
            boundary_x = (xj - xi) * (latitude - yi) / (yj - yi) + xi
            if longitude < boundary_x:
                inside = not inside
        j = i
    return inside


def _point_in_admin_wkts(longitude: Any, latitude: Any,
                         admin_wkts: List[str]) -> bool:
    """True when a school point is inside at least one target admin unit."""
    rings = [
        ring
        for wkt_text in admin_wkts
        for ring in _wkt_rings(wkt_text)
    ]
    return _point_in_admin_rings(longitude, latitude, rings)


def _point_in_admin_rings(longitude: Any, latitude: Any,
                          admin_rings: List[List[List[float]]]) -> bool:
    """Containment against administrative rings parsed only once per query."""
    try:
        lon, lat = float(longitude), float(latitude)
    except (TypeError, ValueError):
        return False
    return any(_point_in_ring(lon, lat, ring) for ring in admin_rings)


@st.cache_data(show_spinner=False, ttl=1800)
def cluster_polygons(
    cfg_key: Tuple[str, str, str, str], codes: Tuple[str, ...]
) -> pd.DataFrame:
    """Fetch LSOA boundary polygons (l.wkt) for the given LSOA codes."""
    cfg = {
        "uri": cfg_key[0],
        "user": cfg_key[1],
        "password": cfg_key[2],
        "database": cfg_key[3],
    }
    rows = run_cypher(
        cfg,
        """
        MATCH (l:LSOA)
        WHERE l.code IN $codes AND l.wkt IS NOT NULL
        RETURN l.code AS code, l.name AS name, l.wkt AS wkt,
               coalesce(l.deprivation, 'unknown') AS deprivation,
               l.wimd_decile AS wimd_decile
        """,
        {"codes": list(codes)},
    )
    return rows


# ---------------------------------------------------------------------------
# Per-LSOA school detail
# ---------------------------------------------------------------------------
# The hover card stays a fixed size and reports only counts and means, because
# it must not grow with the number of schools. School identities live in a
# panel below the map, opened by selecting a region. Wales-wide the maximum is
# five schools in one LSOA, so the panel never needs paging.
@st.cache_data(show_spinner=False, ttl=600)
def schools_in_lsoas(
    cfg_key: Tuple[str, str, str, str], codes: Tuple[str, ...]
) -> pd.DataFrame:
    """Every school located in the given LSOAs, one row per school."""
    cfg = {
        "uri": cfg_key[0], "user": cfg_key[1],
        "password": cfg_key[2], "database": cfg_key[3],
    }
    return run_cypher(
        cfg,
        """
        MATCH (l:LSOA)<-[:LOCATED_IN]-(s:School)
        WHERE l.code IN $codes
        RETURN l.code AS lsoa_code,
               coalesce(l.name, l.LSOA_Name, l.code) AS lsoa_name,
               coalesce(l.deprivation, 'unknown') AS deprivation,
               l.wimd_decile AS wimd_decile,
               coalesce(s.name, s.school_name, s.code) AS school,
               coalesce(s.phase_group, s.phase, s.school_type) AS phase,
               s.language_medium AS language_medium,
               coalesce(s.pupils_2025, s.pupils) AS pupils,
               s.fsm_pct AS fsm_pct,
               s.attendance_pct AS attendance_pct,
               s.capped9_score AS capped9_score
        ORDER BY lsoa_code, coalesce(s.fsm_pct, -1) DESC, school
        """,
        {"codes": list(codes)},
    )


def _detail_metric(label: str, value: str, colour: str, note: str = "") -> str:
    note_html = (
        f"<div style='font-size:9.5px;color:{C_MUTED};margin-top:1px;'>"
        f"{escape(note)}</div>" if note else ""
    )
    return (
        "<div style='background:#f8fafc;border:1px solid #eef2f7;"
        "border-radius:9px;padding:6px 8px;'>"
        f"<div style='color:{colour};font-weight:800;font-size:9.5px;"
        "text-transform:uppercase;letter-spacing:.04em;'>"
        f"{escape(label)}</div>"
        f"<div style='color:{colour};font-weight:900;font-size:13px;"
        f"margin-top:1px;'>{escape(value)}</div>{note_html}</div>"
    )


def render_lsoa_school_panel(
    cfg: Dict[str, str], lsoa_code: str
) -> None:
    """Open one LSOA: its own figures, then a card per school inside it.

    Deliberately below the map rather than inside the hover card. A card that
    grew with the number of schools would cover the region it describes; a
    panel can be as tall as it needs to be.
    """
    if not lsoa_code:
        return
    try:
        rows = schools_in_lsoas(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            (str(lsoa_code),),
        )
    except Exception as exc:
        st.warning(f"Could not load the schools for {lsoa_code}: {exc}")
        return

    DEP_LABEL = {
        "high_deprivation": "High",
        "medium_deprivation": "Medium",
        "low_deprivation": "Low",
        "unknown": "Unknown",
    }
    DEP_COLOUR = {
        "high_deprivation": "#e11d48",
        "medium_deprivation": "#ff8a00",
        "low_deprivation": "#22c55e",
        "unknown": "#94a3b8",
    }

    if rows.empty:
        st.markdown(
            "<div style='background:#fff;border:1px solid #e5e7eb;"
            "border-radius:14px;padding:14px 16px;margin:.5rem 0;'>"
            f"<div style='font-weight:900;color:{C_HEAD};font-size:15px;'>"
            f"{escape(str(lsoa_code))}</div>"
            f"<div style='color:{C_MUTED};font-size:12.5px;margin-top:4px;'>"
            "No school is located inside this LSOA. Its deprivation figures "
            "still count in the answer; only school indicators are absent."
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    head = rows.iloc[0]
    dep_key = str(head.get("deprivation") or "unknown")
    dep_colour = DEP_COLOUR.get(dep_key, "#94a3b8")
    decile = head.get("wimd_decile")
    decile_txt = (
        f"decile {int(float(decile))}" if pd.notna(decile) else "decile N/A"
    )

    def mean_of(col: str) -> Tuple[str, int]:
        vals = pd.to_numeric(rows.get(col, pd.Series(dtype=float)),
                             errors="coerce").dropna()
        if vals.empty:
            return "N/A", 0
        return f"{vals.mean():.1f}", int(len(vals))

    fsm_mean, fsm_n = mean_of("fsm_pct")
    att_mean, att_n = mean_of("attendance_pct")
    cap_mean, cap_n = mean_of("capped9_score")
    total = len(rows)

    # A mean over one school is not a mean, and 73% of Welsh LSOAs hold
    # exactly one school, so the number behind every figure is stated.
    def basis(n: int) -> str:
        if n == 0:
            return "no value recorded"
        if n == 1:
            return "one school"
        return f"mean of {n} schools"

    header = (
        "<div style='background:#fff;border:1px solid #e5e7eb;"
        "border-radius:16px;padding:14px 16px;margin:.6rem 0 .5rem;"
        "box-shadow:0 6px 18px rgba(15,23,42,.05);'>"
        "<div style='display:flex;align-items:baseline;gap:10px;"
        "flex-wrap:wrap;'>"
        f"<div style='font-size:16px;font-weight:900;color:{C_HEAD};'>"
        f"{escape(str(head.get('lsoa_name') or lsoa_code))}</div>"
        f"<div style='font-size:11.5px;color:{C_MUTED};'>"
        f"{escape(str(lsoa_code))}</div>"
        f"<div style='margin-left:auto;font-size:11.5px;font-weight:800;"
        f"color:#fff;background:{dep_colour};border-radius:999px;"
        f"padding:2px 10px;'>"
        f"{escape(DEP_LABEL.get(dep_key, 'Unknown'))} &middot; "
        f"{escape(decile_txt)}</div></div>"
        "<div style='display:grid;grid-template-columns:repeat(4,1fr);"
        "gap:6px;margin-top:10px;'>"
        + _detail_metric("Schools", str(total), C_HEAD)
        + _detail_metric(
            "FSM", "N/A" if fsm_mean == "N/A" else f"{fsm_mean}%",
            C_FSM, basis(fsm_n))
        + _detail_metric(
            "Attendance", "N/A" if att_mean == "N/A" else f"{att_mean}%",
            C_ATT, basis(att_n))
        + _detail_metric("Capped 9", cap_mean, C_PERF, basis(cap_n))
        + "</div></div>"
    )
    st.markdown(header, unsafe_allow_html=True)

    def val(v: Any, suffix: str = "") -> str:
        return "N/A" if pd.isna(v) else f"{float(v):.1f}{suffix}"

    cards = []
    for _, r in rows.iterrows():
        pupils = r.get("pupils")
        pupils_txt = "N/A" if pd.isna(pupils) else f"{int(float(pupils)):,}"
        sub = " · ".join(
            str(x) for x in [r.get("phase"), r.get("language_medium")]
            if x and str(x) != "nan"
        )
        cards.append(
            "<div style='background:#fff;border:1px solid #e5e7eb;"
            "border-left:4px solid " + dep_colour + ";border-radius:14px;"
            "padding:12px 13px;'>"
            f"<div style='font-size:13.5px;font-weight:900;color:{C_HEAD};"
            f"line-height:1.3;'>{escape(str(r.get('school') or ''))}</div>"
            f"<div style='font-size:10.5px;color:{C_MUTED};"
            f"margin:2px 0 8px;'>{escape(sub) or '&nbsp;'}</div>"
            "<div style='display:grid;grid-template-columns:1fr 1fr;"
            "gap:5px;'>"
            + _detail_metric("FSM", val(r.get("fsm_pct"), "%"), C_FSM)
            + _detail_metric(
                "Attendance", val(r.get("attendance_pct"), "%"), C_ATT)
            + _detail_metric("Capped 9", val(r.get("capped9_score")), C_PERF)
            + _detail_metric("Pupils", pupils_txt, C_PUP)
            + "</div></div>"
        )

    columns = 3 if total >= 3 else max(1, total)
    st.markdown(
        f"<div style='display:grid;grid-template-columns:repeat({columns},"
        "minmax(0,1fr));gap:10px;margin-bottom:.6rem;'>"
        + "".join(cards)
        + "</div>",
        unsafe_allow_html=True,
    )
    if cap_n == 0:
        st.caption(
            "Capped 9 is published for secondary schools only, so it is "
            "absent here rather than missing."
        )


def deck_chart_with_click(deck: Any, key: str) -> Dict[str, Any] | None:
    """Render a deck and return the object the reader clicked, if any.

    Selection events on pydeck charts arrived in a later Streamlit release
    than the one this app was first written against, so the call is guarded:
    on an older runtime the chart still renders and the click simply does
    nothing, with one line on screen saying why.
    """
    try:
        event = st.pydeck_chart(
            deck,
            use_container_width=True,
            height=720 if key == "standard_school_map" else 520,
            on_select="rerun",
            selection_mode="single-object",
            key=key,
        )
    except TypeError:
        st.pydeck_chart(deck, use_container_width=True)
        st.caption(
            "Clicking a region needs Streamlit 1.39 or later. Add "
            "`streamlit>=1.39` to requirements.txt to enable it."
        )
        return None
    try:
        objects = event.selection["objects"]
    except Exception:
        return None
    for _layer_id, picked in (objects or {}).items():
        if picked:
            return dict(picked[0])
    return None


@st.cache_data(show_spinner=False, ttl=600)
def lsoa_school_summary(
    cfg_key: Tuple[str, str, str, str], codes: Tuple[str, ...]
) -> pd.DataFrame:
    """School count and metric means per LSOA, with the basis of each mean.

    The count of schools carrying a value is returned alongside the mean
    because 802 of the 1,094 Welsh LSOAs that hold a school hold exactly
    one: a "mean" there is a single value, and the card says so.
    """
    cfg = {
        "uri": cfg_key[0], "user": cfg_key[1],
        "password": cfg_key[2], "database": cfg_key[3],
    }
    return run_cypher(
        cfg,
        """
        MATCH (l:LSOA) WHERE l.code IN $codes
        OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
        RETURN l.code AS code,
               count(DISTINCT s) AS school_count,
               round(avg(s.fsm_pct), 1) AS fsm_avg,
               count(s.fsm_pct) AS fsm_n,
               round(avg(s.attendance_pct), 1) AS att_avg,
               count(s.attendance_pct) AS att_n,
               round(avg(s.capped9_score), 1) AS cap_avg,
               count(s.capped9_score) AS cap_n
        """,
        {"codes": list(codes)},
    )


def _fmt_mean(value: Any, n: Any, suffix: str = "") -> str:
    if pd.isna(value) or not n:
        return "N/A"
    return f"{float(value):.1f}{suffix}"


def _mean_basis(n: Any) -> str:
    n = int(n or 0)
    if n == 0:
        return "no value recorded"
    if n == 1:
        return "one school"
    return f"mean of {n} schools"


def provenance_badge(provenance: str) -> str:
    p = provenance.lower()
    cls = "native" if "native" in p and "geometry" not in p else "geometry" if "geometry" in p else "derived"
    return f"<span class='badge {cls}'>{provenance}</span>"


def _readable_regions(value: Any) -> Any:
    """Flatten a list of region dicts into a readable arrow-joined string."""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        parts = []
        for item in value:
            name = item.get("name") or item.get("code") or "?"
            code = item.get("code", "")
            decile = item.get("wimd_decile")
            label = f"{name} [{code}]"
            if decile is not None:
                label = f"{label} (D{decile})"
            parts.append(label)
        return "  \u2192  ".join(parts)
    return value


def display_df(df: pd.DataFrame) -> None:
    if not df.empty:
        df = df.copy()
        for col in df.columns:
            if df[col].map(
                lambda v: isinstance(v, list)
                and len(v) > 0
                and isinstance(v[0], dict)
            ).any():
                df[col] = df[col].map(_readable_regions)
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


def warm_table(df: pd.DataFrame) -> Any:
    """Give evaluator-facing result grids the same warm visual hierarchy."""
    return (
        df.style
        .set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("background-color", "#ffad78"),
                    ("color", "#3f241f"),
                    ("font-weight", "800"),
                    ("border-color", "#efbba8"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("color", "#2f2422"),
                    ("border-color", "#f1ddd5"),
                ],
            },
            {
                "selector": "tbody tr:nth-child(even) td",
                "props": [("background-color", "#fff8f3")],
            },
            {
                "selector": "tbody tr:nth-child(odd) td",
                "props": [("background-color", "#fffdfb")],
            },
        ])
        .format(na_rep="—", precision=1)
    )


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


# ---------------------------------------------------------------------------
# Map pins
# ---------------------------------------------------------------------------
# REJECTED ALTERNATIVE — icon atlas
# The obvious optimisation is a single sprite sheet passed as the layer's
# iconAtlas prop, with one short key per row. It was implemented and had to be
# reverted: Streamlit passes layer props through a deck.gl expression parser,
# which tries to evaluate the atlas string and fails on the data URI with
# "Unexpected ':' at character 4" (the colon in "data:image/..."). Row DATA is
# not passed through that parser, so the icon object must travel per row.
# The four SVGs are therefore minified and built once at import time; the
# repeated strings compress well over the websocket, and the real cause of the
# earlier sluggishness was the per-query Neo4j driver, fixed separately above.
#
# Pin design: a filled teardrop with a darker outline of the same hue, and a
# hollow white centre carrying the same darker ring, so the marker reads as a
# real location pin. mask=False is required: a mask would flatten the outline
# and fill the hollow centre.
def _pin_icon(fill: str, stroke: str) -> Dict[str, Any]:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='60' height='80' "
        "viewBox='0 0 60 80'>"
        "<path d='M30 4C18.4 4 9 13.4 9 25c0 15.1 21 47 21 47s21-31.9 21-47"
        f"C51 13.4 41.6 4 30 4z' fill='{fill}' stroke='{stroke}' "
        "stroke-width='4' stroke-linejoin='round'/>"
        f"<circle cx='30' cy='25' r='9' fill='#fff' stroke='{stroke}' "
        "stroke-width='3.4'/></svg>"
    )
    return {
        "url": "data:image/svg+xml;base64,"
               + base64.b64encode(svg.encode("utf-8")).decode("ascii"),
        "width": 60,
        "height": 80,
        "anchorY": 80,
        "mask": False,
    }


PIN_ICONS = {
    "high_deprivation": _pin_icon("#e11d48", "#881337"),
    "medium_deprivation": _pin_icon("#ff8a00", "#a34f00"),
    "low_deprivation": _pin_icon("#22c55e", "#166534"),
    "unknown": _pin_icon("#94a3b8", "#475569"),
}

# Traffic-light icons for the all-bands cluster view: red = worst band on the
# clustered variable, green = best, grey = the LSOA has no value to band on.
BAND_PIN_ICONS = {
    "band_red": _pin_icon("#e11d48", "#881337"),
    "band_mid": _pin_icon("#ff8a00", "#a34f00"),
    "band_green": _pin_icon("#22c55e", "#166534"),
    "band_none": _pin_icon("#94a3b8", "#475569"),
}


# The deck.gl tooltip is absolutely positioned inside the chart wrapper, so a
# pin near the bottom edge would have its card clipped. Two things are needed:
# the wrapper must be allowed to overflow, AND the chart's element container
# must sit above the elements that follow it (legend, Map Cypher expander),
# otherwise the escaped card renders behind them.
PYDECK_TOOLTIP_CSS = """
<style>
div[data-testid="stElementContainer"]:has(div[data-testid="stDeckGlJsonChart"]) {
  position: relative !important;
  z-index: 9990 !important;
}
div[data-testid="stDeckGlJsonChart"],
div[data-testid="stDeckGlJsonChart"] > div,
div[data-testid="stDeckGlJsonChart"] #deckgl-wrapper,
div[data-testid="stDeckGlJsonChart"] #view-default-view,
div[data-testid="stDeckGlJsonChart"] canvas + div {
  overflow: visible !important;
}
.deck-tooltip {
  overflow: visible !important;
  z-index: 9999 !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  pointer-events: none !important;
}
/* Only the card itself is capped here. Forcing overflow:visible on the page
   containers collapsed the layout and blanked everything below the map until
   a zoom forced a reflow, so those rules are deliberately not present. */
.deck-tooltip > div {
  max-width: 320px !important;
  white-space: normal !important;
}
</style>
"""


def render_school_map(
    map_df: pd.DataFrame,
    selected_school: Tuple[str, str],
    polygon_df: pd.DataFrame | None = None,
    polygons_only: bool = False,
    admin_polygon_df: pd.DataFrame | None = None,
) -> str | None:
    """Render the Wales school map with pydeck (deck.gl).

    Why pydeck and not Folium: pydeck ships inside Streamlit itself, so no
    third-party JavaScript is fetched from an external CDN at render time.
    Folium and streamlit-folium both failed silently on this machine, which
    is the signature of a locked-down network blocking the map assets.

    Design notes:
      * Schools are drawn as location pins (IconLayer), one pin image per
        deprivation category, each with a darker outline and hollow centre.
      * Pin images are base64 data URIs, so no icon CDN is required either.
      * The deck canvas is cleared to a light colour instead of the deck.gl
        default black, so the map reads as a light dashboard surface even
        when background tiles are switched off.
      * No outline polygon is drawn: the approximate hull around the points
        looked like a false administrative boundary and was removed.
      * The hover card is laid out in two compact columns and the chart
        wrapper is allowed to overflow, so the card is never clipped by the
        bottom edge of the map box.
    """
    chart_df = map_df.copy()
    dep_labels = {
        "high_deprivation": "High",
        "medium_deprivation": "Medium",
        "low_deprivation": "Low",
        "unknown": "Unknown",
    }
    chart_df["deprivation"] = chart_df["deprivation"].fillna("unknown").astype(str)
    chart_df["deprivation_label"] = chart_df["deprivation"].map(dep_labels).fillna("Unknown")

    def pct(v: Any) -> str:
        return "N/A" if pd.isna(v) else f"{float(v):.1f}%"

    def num(v: Any) -> str:
        return "N/A" if pd.isna(v) else f"{float(v):.1f}"

    chart_df["fsm_label"] = chart_df["fsm_pct"].apply(pct)
    chart_df["attendance_label"] = chart_df["attendance_pct"].apply(pct)
    chart_df["capped9_label"] = chart_df["capped9_score"].apply(num)
    chart_df["literacy_label"] = chart_df["literacy_score"].apply(num)
    chart_df["numeracy_label"] = chart_df["numeracy_score"].apply(num)
    chart_df["science_label"] = chart_df["science_score"].apply(num)
    chart_df["welsh_bacc_label"] = chart_df["welsh_bacc_score"].apply(num)
    chart_df["nearest_stop_label"] = chart_df["nearest_stop_distance_m"].apply(
        lambda v: "No stop within 800m" if pd.isna(v) else f"{float(v):.0f}m"
    )
    chart_df["wimd_label"] = chart_df["wimd_decile"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{int(float(v))}"
    )
    chart_df["pupils_label"] = chart_df["pupils"].apply(
        lambda v: "N/A" if pd.isna(v) else f"{int(float(v)):,}"
    )
    chart_df["ptr_label"] = chart_df["pupil_teacher_ratio"].apply(num)
    chart_df["budget_label"] = chart_df["budget_per_pupil_gbp"].apply(
        lambda v: "N/A" if pd.isna(v) else f"GBP {float(v):,.0f}"
    )
    # Capped 9 is recorded for secondary schools only, so on roughly six in
    # seven pins the performance block was four N/A boxes and a heading. That
    # is what pushed the card past the height the map can show. The block is
    # now built per row and left empty when there is nothing to report.
    _perf_cols = ["capped9_score", "literacy_score", "numeracy_score",
                  "science_score"]
    def _perf_summary(row) -> str:
        if not row[_perf_cols].notna().any():
            return "Not recorded for this school"
        return (
            f"Capped 9 {row['capped9_label']} \u00b7 "
            f"Literacy {row['literacy_label']} \u00b7 "
            f"Numeracy {row['numeracy_label']} \u00b7 "
            f"Science {row['science_label']}"
        )

    chart_df["perf_summary"] = (
        chart_df.apply(_perf_summary, axis=1) if len(chart_df)
        else "Not recorded for this school"
    )

    for col in ["school", "local_authority", "school_type", "language_medium",
                "gender_mix", "address", "postcode"]:
        chart_df[col] = chart_df[col].fillna("N/A").astype(str)

    st.markdown(PYDECK_TOOLTIP_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='map-note'>"
        "School locations across Wales. Hover a pin to open its metrics card."
        "</div>",
        unsafe_allow_html=True,
    )

    band_mode = (
        "cluster_band" in chart_df.columns
        and chart_df["cluster_band"].notna().any()
    )
    if band_mode:
        chart_df["icon"] = chart_df["cluster_band"].apply(
            lambda b: BAND_PIN_ICONS.get(str(b), BAND_PIN_ICONS["band_none"])
        )
    else:
        chart_df["icon"] = chart_df["deprivation"].apply(
            lambda d: PIN_ICONS.get(str(d), PIN_ICONS["unknown"])
        )

    focused = selected_school[0] != "All"

    icon_cols = [
        "longitude", "latitude", "icon", "school", "local_authority",
        "school_type", "language_medium", "gender_mix", "address", "postcode",
        "deprivation_label", "wimd_label", "fsm_label", "attendance_label",
        "capped9_label", "literacy_label", "numeracy_label", "science_label",
        "welsh_bacc_label", "pupils_label", "ptr_label", "budget_label",
        "nearest_stop_label", "perf_summary",
    ]
    pin_layer = pdk.Layer(
        "IconLayer",
        data=chart_df[icon_cols],
        get_icon="icon",
        get_position=["longitude", "latitude"],
        get_size=5.2 if focused else 3.4,
        size_scale=10,
        size_min_pixels=18 if focused else 13,
        size_max_pixels=74,
        pickable=True,
        # alphaCutoff = -1 turns off alpha-based picking, so the whole pin
        # rectangle is hoverable instead of only the opaque middle of the
        # teardrop. Without this, the card only appeared near the centre.
        alpha_cutoff=-1,
    )

    lat_min, lat_max = chart_df["latitude"].min(), chart_df["latitude"].max()
    lon_min, lon_max = chart_df["longitude"].min(), chart_df["longitude"].max()
    span = max(float(lat_max - lat_min), float(lon_max - lon_min) * .62, .002)
    if focused or len(chart_df) == 1:
        map_zoom = 13.0
    elif span < .025:
        map_zoom = 12.0
    elif span < .07:
        map_zoom = 10.8
    elif span < .22:
        map_zoom = 9.5
    elif span < .65:
        map_zoom = 8.2
    else:
        map_zoom = 6.8
    view_state = pdk.ViewState(
        latitude=float((lat_min + lat_max) / 2),
        longitude=float((lon_min + lon_max) / 2),
        zoom=map_zoom,
        pitch=0,
        bearing=0,
    )

    def cell(label: str, value_key: str, colour: str) -> str:
        return (
            "<div style='background:#f8fafc;border:1px solid #eef2f7;"
            "border-radius:9px;padding:5px 7px;'>"
            f"<div style='color:{colour};font-weight:800;font-size:9.5px;"
            "text-transform:uppercase;letter-spacing:.04em;'>"
            f"{label}</div>"
            f"<div style='color:{colour};font-weight:900;font-size:12.5px;"
            "margin-top:1px;'>{" + value_key + "}</div>"
            "</div>"
        )

    grid_open = (
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:5px;'>"
    )
    tooltip = {
        "html": (
            "<div style='font-family:Segoe UI,Arial,sans-serif;width:310px;"
            "background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;"
            "padding:11px 12px;box-shadow:0 12px 30px rgba(15,23,42,.18);'>"
            f"<div style='font-size:14px;font-weight:900;color:{C_HEAD};"
            "line-height:1.25;'>{school}</div>"
            f"<div style='font-size:11px;color:{C_MUTED};margin:2px 0 8px;'>"
            "{local_authority} &middot; {school_type} &middot; "
            "{language_medium}</div>"
            + grid_open
            + cell("Deprivation", "deprivation_label", C_DEP)
            + cell("WIMD decile", "wimd_label", C_WIMD)
            + cell("FSM", "fsm_label", C_FSM)
            + cell("Attendance", "attendance_label", C_ATT)
            + cell("Pupils", "pupils_label", C_PUP)
            + cell("PTR", "ptr_label", C_PTR)
            + cell("Budget / pupil", "budget_label", C_BUD)
            + cell("Transport", "nearest_stop_label", C_TRAN)
            + "</div>"
            + f"<div style='margin-top:8px;font-size:9.5px;font-weight:800;"
              f"color:{C_PERF};text-transform:uppercase;"
              "letter-spacing:.04em;'>Secondary performance</div>"
            + f"<div style='font-size:11px;font-weight:700;color:{C_PERF};"
              "margin-top:2px;line-height:1.35;'>{perf_summary}</div>"
            + f"<div style='margin-top:8px;font-size:10px;color:{C_MUTED};"
              "line-height:1.35;'>{address} &mdash; {postcode}</div>"
            "</div>"
        ),
        "style": {
            "backgroundColor": "transparent",
            "color": "#0f172a",
            "boxShadow": "none",
            "padding": "0",
            "zIndex": "9999",
        },
    }

    layers = []
    # Administrative boundaries are a second, deliberately unfilled layer.
    # They explain the graph path without replacing the LSOA deprivation
    # polygons underneath or obscuring the school pins above them.
    admin_fill_layer = None
    admin_line_layer = None
    if admin_polygon_df is not None and not admin_polygon_df.empty:
        admin_rows = []
        for _, arow in admin_polygon_df.iterrows():
            role = str(arow.get("role") or "result")
            for ring in _wkt_rings(arow.get("wkt")):
                admin_rows.append({
                    "polygon": ring,
                    "name": arow.get("name") or arow.get("uri"),
                    "unit_type": arow.get("unit_type") or "AdminUnit",
                    "role": role,
                    # The deck uses one tooltip template for every layer.
                    # Populate its school-card fields with administrative
                    # labels so hovering the blue boundary reports the unit
                    # itself rather than the LSOA drawn underneath it.
                    "school": arow.get("name") or arow.get("uri"),
                    "local_authority": "Administrative boundary",
                    "school_type": arow.get("unit_type") or "AdminUnit",
                    "language_medium": (
                        "Chosen area" if role == "anchor"
                        else "Related administrative unit"
                    ),
                    "deprivation_label": "Not applicable",
                    "wimd_label": "N/A",
                    "fsm_label": "N/A",
                    "attendance_label": "N/A",
                    "pupils_label": "N/A",
                    "ptr_label": "N/A",
                    "budget_label": "N/A",
                    "nearest_stop_label": "N/A",
                    "perf_summary": "Administrative boundary",
                    "address": str(role).replace("_", " ").title(),
                    "postcode": "",
                    "line": [124, 58, 237, 245] if role == "anchor"
                            else [14, 116, 144, 220],
                    "fill": [124, 58, 237, 42] if role == "anchor"
                            else [14, 116, 144, 24],
                })
        if admin_rows:
            # The filled administrative polygon is deliberately not
            # pickable. If it captures the whole interior, the LSOA beneath
            # can never receive hover/click events. Its boundary is a
            # separate pickable path, so the three objects remain reachable:
            # school pin, LSOA interior, administrative boundary.
            admin_fill_layer = pdk.Layer(
                "PolygonLayer", id="administrative-scope",
                data=admin_rows, get_polygon="polygon",
                get_fill_color="fill", get_line_color="line",
                line_width_min_pixels=0, stroked=False, filled=True,
                pickable=False,
            )
            admin_line_layer = pdk.Layer(
                "PathLayer", id="administrative-scope-boundaries",
                data=admin_rows, get_path="polygon", get_color="line",
                get_width=5, width_min_pixels=4, pickable=True,
            )
    if polygon_df is not None and not polygon_df.empty:
        DEP_FILL = {
            "high_deprivation": [225, 29, 72],
            "medium_deprivation": [255, 138, 0],
            "low_deprivation": [34, 197, 94],
            "unknown": [148, 163, 184],
        }
        DEP_LABEL = {
            "high_deprivation": "High",
            "medium_deprivation": "Medium",
            "low_deprivation": "Low",
            "unknown": "Unknown",
        }
        lsoa_summary: Dict[str, Dict[str, Any]] = {}
        if "lsoa_code" in chart_df.columns:
            for code, group in chart_df.groupby(
                chart_df["lsoa_code"].fillna("").astype(str)
            ):
                if not code:
                    continue
                def _avg(column: str, suffix: str = "") -> str:
                    vals = pd.to_numeric(
                        group.get(column, pd.Series(dtype=float)),
                        errors="coerce",
                    ).dropna()
                    return (
                        f"{vals.mean():.1f}{suffix}" if not vals.empty else "N/A"
                    )
                pupils = pd.to_numeric(
                    group.get("pupils", pd.Series(dtype=float)),
                    errors="coerce",
                ).dropna()
                lsoa_summary[code] = {
                    "schools": int(len(group)),
                    "fsm": _avg("fsm_pct", "%"),
                    "attendance": _avg("attendance_pct", "%"),
                    "performance": _avg("capped9_score"),
                    "pupils": (
                        f"{int(pupils.sum()):,}" if not pupils.empty else "N/A"
                    ),
                    "ptr": _avg("pupil_teacher_ratio"),
                    "budget": _avg("budget_per_pupil_gbp"),
                }
        poly_rows = []
        for _, prow in polygon_df.iterrows():
            dep_key = str(prow.get("deprivation") or "unknown")
            base = DEP_FILL.get(dep_key, DEP_FILL["unknown"])
            summary = lsoa_summary.get(str(prow.get("code")), {})
            for ring in _wkt_rings(prow.get("wkt")):
                # Deeper red for bigger clusters, in the manner of a
                # choropleth: the shade encodes cluster size.
                poly_rows.append(
                    {
                        "polygon": ring,
                        "name": prow.get("name") or prow.get("code"),
                        "code": prow.get("code"),
                        "cluster_size": int(prow.get("cluster_size", 0)),
                        "schools_count": prow.get("schools_count", 0),
                        "schools_basis": prow.get(
                            "schools_basis", "Open the area below for its "
                            "schools"
                        ),
                        "fsm_avg": prow.get("fsm_avg", "N/A"),
                        "att_avg": prow.get("att_avg", "N/A"),
                        "deprivation_label": DEP_LABEL.get(
                            dep_key, "Unknown"
                        ),
                        "wimd_label": (
                            f"decile {int(prow['wimd_decile'])}"
                            if pd.notna(prow.get("wimd_decile"))
                            else "N/A"
                        ),
                        "fill": base + [150],
                        "school": prow.get("name") or prow.get("code"),
                        "local_authority": "LSOA statistical area",
                        "school_type": prow.get("code"),
                        "language_medium": "Click for LSOA and school details",
                        "fsm_label": summary.get("fsm", prow.get("fsm_avg", "N/A")),
                        "attendance_label": summary.get(
                            "attendance", prow.get("att_avg", "N/A")
                        ),
                        "pupils_label": summary.get("pupils", "N/A"),
                        "ptr_label": summary.get("ptr", "N/A"),
                        "budget_label": summary.get("budget", "N/A"),
                        "nearest_stop_label": (
                            f"{summary.get('schools', 0)} schools in this answer"
                        ),
                        "perf_summary": (
                            "Mean Capped 9 " + summary.get("performance", "N/A")
                        ),
                        "address": "LSOA boundary",
                        "postcode": "",
                    }
                )
        if poly_rows:
            layers.append(
                pdk.Layer(
                    "PolygonLayer",
                    id="cluster-regions",
                    data=poly_rows,
                    get_polygon="polygon",
                    get_fill_color="fill",
                    get_line_color=[136, 19, 55, 170],
                    line_width_min_pixels=1,
                    stroked=True,
                    filled=True,
                    pickable=True,
                    auto_highlight=True,
                    highlight_color=[124, 58, 237, 190],
                )
            )
    # Put the administrative outline above the filled LSOA layer and below
    # the pins, otherwise the LSOA fill can hide the explanation boundary.
    if admin_fill_layer is not None:
        layers.append(admin_fill_layer)
    if admin_line_layer is not None:
        layers.append(admin_line_layer)
    if not polygons_only:
        layers.append(pin_layer)

    if polygons_only:
        tooltip = {
            "html": (
                "<div style='font-family:Segoe UI,Arial,sans-serif;"
                "width:250px;background:rgba(255,255,255,.82);"
                "backdrop-filter:blur(3px);border:1px solid rgba(136,19,55,.35);"
                "border-radius:14px;padding:10px 12px;"
                "box-shadow:0 10px 26px rgba(15,23,42,.16);'>"
                f"<div style='font-size:13.5px;font-weight:900;color:{C_HEAD};"
                "line-height:1.3;'>{name}</div>"
                f"<div style='font-size:10.5px;color:{C_MUTED};"
                "margin:2px 0 8px;'>{code} &middot; cluster of "
                "{cluster_size} LSOAs</div>"
                f"<div style='background:rgba(248,250,252,.75);"
                "border-radius:8px;padding:5px 7px;margin-bottom:5px;'>"
                f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
                "text-transform:uppercase;letter-spacing:.05em;'>"
                "Deprivation</div>"
                f"<div style='font-size:13px;font-weight:800;color:{C_DEP};'>"
                "{deprivation_label} &middot; {wimd_label}</div></div>"
                "<div style='display:grid;grid-template-columns:1fr 1fr;"
                "gap:5px;'>"
                f"<div style='background:rgba(248,250,252,.75);"
                "border-radius:8px;padding:5px 7px;'>"
                f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
                "text-transform:uppercase;letter-spacing:.05em;'>Schools"
                "</div><div style='font-size:13px;font-weight:800;'>"
                "{schools_count}</div></div>"
                f"<div style='background:rgba(248,250,252,.75);"
                "border-radius:8px;padding:5px 7px;'>"
                f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
                "text-transform:uppercase;letter-spacing:.05em;'>Mean FSM"
                f"</div><div style='font-size:13px;font-weight:800;"
                f"color:{C_FSM};'>{{fsm_avg}}</div></div>"
                f"<div style='grid-column:1 / span 2;"
                "background:rgba(248,250,252,.75);border-radius:8px;"
                "padding:5px 7px;'>"
                f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
                "text-transform:uppercase;letter-spacing:.05em;'>"
                "Mean attendance</div>"
                f"<div style='font-size:13px;font-weight:800;"
                f"color:{C_ATT};'>{{att_avg}}</div></div>"
                "</div>"
                f"<div style='font-size:10px;color:{C_MUTED};"
                "margin-top:7px;line-height:1.4;'>{schools_basis}<br>"
                "Click the region to see the schools by name.</div>"
                "</div>"
            ),
            "style": {
                "backgroundColor": "transparent",
                "color": "#0f172a",
                "zIndex": "9999",
            },
        }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        # No external basemap: tiles are fetched from a third-party service
        # and are blocked on this network. The pins carry the information, and
        # the light clearColor below keeps the canvas readable without them.
        map_style=None,
        tooltip=tooltip,
        # Light canvas instead of the deck.gl default black background.
        parameters={"clearColor": [0.972, 0.980, 0.992, 1]},
    )
    picked_region = deck_chart_with_click(
        deck,
        key="cluster_map" if polygons_only else "standard_school_map",
    )

    if admin_polygon_df is not None and not admin_polygon_df.empty:
        has_results = (admin_polygon_df.get("role") == "result").any()
        st.markdown(
            "<div class='map-note'><b>Administrative-scope legend:</b> "
            "<span style='color:#7c3aed;font-size:18px;'>&#9632;</span> "
            "selected source unit"
            + (
                " &nbsp; <span style='color:#0e7490;font-size:18px;'>"
                "&#9632;</span> related target units"
                if has_results else ""
            )
            + " &nbsp;&middot;&nbsp; red / orange / green polygons are "
              "intersecting LSOAs, and pins are matching schools.</div>",
            unsafe_allow_html=True,
        )

    if polygons_only:
        st.markdown(
            "<div class='map-note'>"
            "<b>Cluster regions by deprivation level:</b> "
            "<span style='color:#e11d48;font-size:16px;'>&#9679;</span> High "
            "&nbsp; <span style='color:#ff8a00;font-size:16px;'>&#9679;</span>"
            " Medium &nbsp; "
            "<span style='color:#22c55e;font-size:16px;'>&#9679;</span> Low "
            "&nbsp; <span style='color:#94a3b8;font-size:16px;'>&#9679;</span>"
            " Unknown &nbsp;&middot;&nbsp; hover a region for its figures."
            "</div>",
            unsafe_allow_html=True,
        )
    elif band_mode:
        st.markdown(
            "<div class='map-note'>"
            "<b>Severity bands on the clustered variable:</b> "
            "<span style='color:#e11d48;font-size:16px;'>&#9679;</span>"
            " Worst band &nbsp; "
            "<span style='color:#ff8a00;font-size:16px;'>&#9679;</span>"
            " Middle band &nbsp; "
            "<span style='color:#22c55e;font-size:16px;'>&#9679;</span>"
            " Best band &nbsp; "
            "<span style='color:#94a3b8;font-size:16px;'>&#9679;</span>"
            " No value to band on"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='map-note'>"
            "<b>Deprivation legend:</b> "
            "<span style='color:#e11d48;font-size:16px;'>&#9679;</span> High &nbsp; "
            "<span style='color:#ff8a00;font-size:16px;'>&#9679;</span> Medium &nbsp; "
            "<span style='color:#22c55e;font-size:16px;'>&#9679;</span> Low &nbsp; "
            "<span style='color:#94a3b8;font-size:16px;'>&#9679;</span> Unknown"
            "</div>",
            unsafe_allow_html=True,
        )

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

    picked_code = picked_region.get("code") if picked_region else None
    return str(picked_code) if picked_code else None




# =============================================================================
# EVALUATOR-READY VISUAL COMPONENTS — concise, task-serving, light UI
# =============================================================================
def visual_project_pipeline() -> None:
    st.markdown("""
<div class="visual-card">
  <h3>Project Pipeline — each visual block supports a supervisor task</h3>
  <div class="grid grid-5">
    <div class="task-step"><div class="step-num step-blue">1</div><div class="step-title2">Administrative Hierarchy</div><div class="step-text">YAGO2geo baseline: AdminUnit, WITHIN, TOUCHES.</div></div>
    <div class="task-step"><div class="step-num step-green">2</div><div class="step-title2">LSOA + Statistics</div><div class="step-text">Add LSOA, WIMD, schools, FSM, transport.</div></div>
    <div class="task-step"><div class="step-num step-orange">3</div><div class="step-title2">Policy → SCQ</div><div class="step-text">Translate policy questions into SCQ1–SCQ8 patterns.</div></div>
    <div class="task-step"><div class="step-num step-purple">4</div><div class="step-title2">Demonstrator</div><div class="step-text">Run Cypher, show rows, parameters and provenance.</div></div>
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
  <h3>Cross-hierarchy Bridge — the main finding</h3>
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
    st.header("Project overview")
    st.caption("The project by task: what each task set out to do, what was built, and where to see it working in this app.")
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
        "Policy Questions mapped to SCQs",
        "Translate education-policy questions into standard spatial competency question forms so the use case is evaluated through SCQ1–SCQ8 rather than ad-hoc queries.",
        "In progress",
    )
    st.markdown(
        "<div class='solutionbox'>Each education policy question is mapped to "
        "its SCQ form, the graph relation that answers it, and the provenance "
        "of that relation — the basis of the coverage scoring in the "
        "Evaluation page.</div>",
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
        df = df.drop(columns=["Task link"])
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

NATIONAL_SPREAD_CYPHER = {
    "deprivation": """
MATCH (l:LSOA)-[:LSOA_TOUCHES]-(n:LSOA)
WHERE l.wimd_decile IS NOT NULL AND n.wimd_decile IS NOT NULL
WITH l, max(n.wimd_decile) - min(n.wimd_decile) AS spread
RETURN round(avg(spread),2) AS avg_spread, max(spread) AS max_spread,
       count(l) AS lsoas
""",
    "fsm": """
MATCH (l:LSOA)-[:LSOA_TOUCHES]-(n:LSOA)
OPTIONAL MATCH (n)<-[:LOCATED_IN]-(s:School)
WITH l, n, avg(s.fsm_pct) AS n_fsm
WITH l, max(n_fsm) - min(n_fsm) AS spread
WHERE spread IS NOT NULL
RETURN round(avg(spread),2) AS avg_spread,
       round(max(spread),1) AS max_spread, count(l) AS lsoas
""",
    "attendance": """
MATCH (l:LSOA)-[:LSOA_TOUCHES]-(n:LSOA)
OPTIONAL MATCH (n)<-[:LOCATED_IN]-(s:School)
WITH l, n, avg(s.attendance_pct) AS n_att
WITH l, max(n_att) - min(n_att) AS spread
WHERE spread IS NOT NULL
RETURN round(avg(spread),2) AS avg_spread,
       round(max(spread),1) AS max_spread, count(l) AS lsoas
""",
}


@st.cache_data(show_spinner=False, ttl=3600)
def national_spread(cfg_key: Tuple[str, str, str, str], measure: str) -> Dict[str, Any]:
    """Wales-wide neighbour spread for one measure, so a single result can be
    read against the national pattern instead of in isolation."""
    cfg = {
        "uri": cfg_key[0], "user": cfg_key[1],
        "password": cfg_key[2], "database": cfg_key[3],
    }
    rows = run_cypher(cfg, NATIONAL_SPREAD_CYPHER[measure], {})
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


def render_result_reading(
    result_df: pd.DataFrame,
    scq_key: str,
    cfg: Dict[str, str] | None = None,
) -> None:
    """Read the returned rows against the Wales-wide pattern.

    A single neighbourhood means little on its own, so each measure is shown
    twice: the spread among the areas just returned, and the mean spread
    across all 1,909 LSOAs. The comparison is what turns an example into
    evidence.
    """
    if result_df is None or result_df.empty:
        return

    def series(*names: str) -> pd.Series:
        for name in names:
            if name in result_df.columns:
                return pd.to_numeric(result_df[name], errors="coerce").dropna()
        return pd.Series(dtype=float)

    measures = [
        ("Deprivation decile", series("wimd_decile"), "deprivation", "", 0),
        ("School FSM", series("avg_school_fsm_pct", "fsm_pct"), "fsm", "%", 1),
        (
            "Attendance",
            series("avg_school_attendance_pct", "attendance_pct"),
            "attendance",
            "%",
            1,
        ),
    ]
    rows = [m for m in measures if len(m[1]) >= 2]
    if not rows:
        return

    st.markdown(
        f"<div style='font-weight:800;margin:14px 0 6px;'>"
        f"{len(result_df)} areas returned — this neighbourhood against Wales"
        f"</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(rows))
    for col, (label, values, key, unit, dp) in zip(cols, rows):
        spread = float(values.max() - values.min())
        national = {}
        if cfg is not None:
            try:
                national = national_spread(
                    (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
                    key,
                )
            except Exception:
                national = {}
        nat = national.get("avg_spread")
        delta = None
        if nat is not None:
            diff = spread - float(nat)
            delta = f"{diff:+.{dp}f} vs Wales mean {float(nat):.2f}"
        with col:
            st.metric(
                f"{label} spread",
                f"{spread:.{dp}f}{unit}",
                delta=delta,
                delta_color="off",
            )
            st.caption(
                f"here {values.min():.{dp}f}–{values.max():.{dp}f}{unit} "
                f"(mean {values.mean():.{dp}f}{unit})"
            )

    dec = series("wimd_decile")
    if len(dec) >= 2:
        spread = int(dec.max()) - int(dec.min())
        if spread >= 6:
            st.info(
                "This neighbourhood sits on a sharp social boundary: its "
                "neighbours span six or more deprivation deciles. Across "
                "Wales 792 of 1,909 areas (41.5%) do the same."
            )
        elif spread <= 2:
            st.info(
                "This neighbourhood is internally consistent: its neighbours "
                "sit within a narrow deprivation band, which is what local "
                "clustering of disadvantage looks like."
            )

    with st.expander("How these figures are calculated"):
        st.caption(
            "Left figure: the range among the areas returned above. Right "
            "figure: the mean of that same range computed for every LSOA in "
            "Wales, so one result can be read against the national pattern."
        )
        for label, _values, key, _unit, _dp in rows:
            st.markdown(f"**{label} — Wales-wide**")
            st.code(NATIONAL_SPREAD_CYPHER[key].strip(), language="cypher")


def admin_touch_options(
    cfg: Dict[str, str], unit_type: str
) -> List[Tuple[str, str]]:
    """Administrative units of one type that have at least one TOUCHES edge."""
    return safe_options(cfg, f"""
    MATCH (a:AdminUnit)
    WHERE a.type = '{unit_type}' AND EXISTS {{ MATCH (a)-[:TOUCHES]-() }}
    RETURN DISTINCT a.uri AS value,
           coalesce(a.name, a.uri) + ' | {unit_type}' AS label
    ORDER BY label
    LIMIT 20000
    """)


@st.cache_data(show_spinner=False, ttl=600)
def lsoa_hop_distance(
    cfg_key: Tuple[str, str, str, str], code_a: str, code_b: str,
    kind: str = "LSOA",
) -> int | None:
    """Shortest LSOA_TOUCHES distance between two LSOAs, or None if unlinked.

    SCQ3 only means anything for a pair that is neither the same area nor
    directly adjacent: two touching regions are joined by a single edge, so
    nothing lies between them and every path the enumerator returns is a
    detour. Knowing the distance also lets the hop bound be suggested rather
    than guessed.
    """
    if not code_a or not code_b or code_a == code_b:
        return 0
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    if kind == "LSOA":
        pattern = ("MATCH (a:LSOA {code:$a}), (b:LSOA {code:$b}) "
                   "MATCH p = shortestPath((a)-[:LSOA_TOUCHES*..12]-(b))")
    else:
        pattern = ("MATCH (a:AdminUnit {uri:$a}), (b:AdminUnit {uri:$b}) "
                   "MATCH p = shortestPath((a)-[:TOUCHES*..12]-(b))")
    df = run_cypher(cfg, pattern + " RETURN length(p) AS hops",
                    {"a": code_a, "b": code_b})
    if df.empty or pd.isna(df.iloc[0]["hops"]):
        return None
    return int(df.iloc[0]["hops"])


def render_answer_map(
    cfg: Dict[str, str],
    result_df: pd.DataFrame,
    focus_code: Any = None,
    key: str = "answer_map",
    focus_admin: str | None = None,
    show_gap: bool = False,
    show_excluded_neighbours: bool = False,
    selected_codes: Any = None,
) -> str | None:
    """Draw the LSOAs in an SCQ answer as coloured regions.

    Answer regions are shaded by deprivation level; the LSOA the question
    was asked about is outlined so the spatial relation is visible. Nothing
    is filtered here: the map shows exactly the rows the question returned.
    """
    if result_df is None or result_df.empty:
        return None

    code_pattern = re.compile(r"^W\d{8}$")

    def harvest(value: Any, sink: List[str]) -> None:
        """Pull LSOA codes out of scalars, lists and maps alike.

        SCQ3 returns a list of node maps per path rather than a plain code
        column, so a recursive walk is needed to find the codes at all.
        """
        if value is None:
            return
        if isinstance(value, str):
            if code_pattern.match(value):
                sink.append(value)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                harvest(item, sink)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                harvest(item, sink)

    codes: List[str] = []
    for col in result_df.columns:
        for value in result_df[col].tolist():
            harvest(value, codes)
    focus_set = {
        str(c)
        for c in (
            focus_code if isinstance(focus_code, (list, tuple, set)) else [focus_code]
        )
        if c
    }
    selected_set = {
        str(c) for c in (
            selected_codes
            if isinstance(selected_codes, (list, tuple, set))
            else [selected_codes]
        ) if c
    }
    codes.extend(focus_set)

    # For a complement answer the meaning sits in what is MISSING, so the
    # excluded neighbours are fetched too and drawn in outline only. Without
    # them the gap reads as a rendering fault rather than as the answer.
    excluded: set[str] = set()
    if focus_set and show_excluded_neighbours:
        try:
            neighbour_rows = run_cypher(
                cfg,
                "MATCH (x:LSOA)-[:LSOA_TOUCHES]-(y:LSOA) "
                "WHERE x.code IN $focus RETURN DISTINCT y.code AS code",
                {"focus": sorted(focus_set)},
            )
            neighbours = {str(c) for c in neighbour_rows["code"].tolist()}
            if neighbours and not neighbours.issubset(set(codes)):
                excluded = neighbours - set(codes)
                codes.extend(excluded)
        except Exception:
            excluded = set()
    codes = sorted(set(codes))
    if not codes:
        return None

    # The answer itself is never truncated — only the drawing is. A question
    # like "not adjacent" returns nearly every LSOA in Wales, and rendering
    # all of them would stall the browser without adding meaning.
    MAP_DRAW_CAP = 2000
    drawn_note = ""
    if len(codes) > MAP_DRAW_CAP:
        drawn_note = (
            f"Showing {MAP_DRAW_CAP:,} of {len(codes):,} answer regions on "
            "the map for speed. The count above and the table below are the "
            "full answer."
        )
        keep = [c for c in codes if c in focus_set]
        rest = [c for c in codes if c not in focus_set]
        # Even stride, not the first N: taking the first N by code would
        # show only one corner of Wales and misrepresent the answer.
        stride = max(1, len(rest) // max(1, MAP_DRAW_CAP - len(keep)))
        keep += rest[::stride][: MAP_DRAW_CAP - len(keep)]
        codes = keep

    try:
        polys = cluster_polygons(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            tuple(codes),
        )
    except Exception:
        return None
    if polys.empty:
        return None

    # School figures for every drawn region, so the hover card carries the
    # education evidence and not only the deprivation label.
    school_by_code: Dict[str, Dict[str, Any]] = {}
    try:
        sdf = lsoa_school_summary(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            tuple(codes),
        )
        for _, srow in sdf.iterrows():
            school_by_code[str(srow["code"])] = srow.to_dict()
    except Exception:
        school_by_code = {}

    DEP_FILL = {
        "high_deprivation": [225, 29, 72],
        "medium_deprivation": [255, 138, 0],
        "low_deprivation": [34, 197, 94],
        "unknown": [148, 163, 184],
    }
    DEP_LABEL = {
        "high_deprivation": "High",
        "medium_deprivation": "Medium",
        "low_deprivation": "Low",
        "unknown": "Unknown",
    }
    rows = []
    lats: List[float] = []
    lons: List[float] = []
    heavy = len(polys) > 250
    focus_lats: List[float] = []
    focus_lons: List[float] = []
    for _, prow in polys.iterrows():
        dep = str(prow.get("deprivation") or "unknown")
        base = DEP_FILL.get(dep, DEP_FILL["unknown"])
        is_focus = str(prow["code"]) in focus_set
        is_excluded = str(prow["code"]) in excluded
        is_selected = str(prow["code"]) in selected_set
        has_selection = bool(selected_set)
        if is_focus:
            # Keep the selected LSOA visually independent from the answer
            # palette so it remains obvious on every SCQ map.
            fill = [250, 204, 21, 225]
        elif is_selected:
            fill = base + [225]
        elif is_excluded:
            fill = [255, 255, 255, 40]
        else:
            fill = base + ([34] if has_selection else [120])
        for ring in _wkt_rings(prow.get("wkt")):
            # With hundreds of regions on screen the browser chokes on full
            # boundary detail, so rings are decimated. Shape is preserved at
            # national zoom; the underlying answer is untouched.
            if heavy and len(ring) > 60:
                step = len(ring) // 60 + 1
                ring = ring[::step] + [ring[-1]]
            for pt in ring:
                lons.append(pt[0])
                lats.append(pt[1])
                if is_focus:
                    focus_lons.append(pt[0])
                    focus_lats.append(pt[1])
            rows.append(
                {
                    "polygon": ring,
                    "fill": fill,
                    "line": (
                        [17, 24, 39, 255]
                        if is_focus
                        else [255, 255, 255, 255] if is_selected
                        else [124, 58, 237, 235] if is_excluded
                        else base + ([75] if has_selection else [200])
                    ),
                    "width": 4 if is_focus else 5 if is_selected else 3 if is_excluded else 1,
                    "name": prow.get("name") or prow.get("code"),
                    "code": prow.get("code"),
                    "dep_label": DEP_LABEL.get(dep, "Unknown"),
                    "wimd_label": (
                        f"decile {int(prow['wimd_decile'])}"
                        if pd.notna(prow.get("wimd_decile"))
                        else "N/A"
                    ),
                    "role": (
                        "Selected domain"
                        if is_focus
                        else "Selected answer area" if is_selected
                        else "Excluded — it borders your LSOA"
                        if is_excluded
                        else "In the answer"
                    ),
                    **_school_card_fields(
                        school_by_code.get(str(prow["code"]), {})
                    ),
                }
            )
    if not rows or not lats:
        return None

    layer = pdk.Layer(
        "PolygonLayer",
        id="answer-regions",
        data=rows,
        get_polygon="polygon",
        get_fill_color="fill",
        get_line_color="line",
        get_line_width="width",
        line_width_min_pixels=1,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
        highlight_color=[124, 58, 237, 190],
    )
    # Framing rule: when the answer is large (a complement question colours
    # nearly all of Wales) the useful view is the neighbourhood of the LSOA
    # that was asked about, not the whole country — otherwise the gap that
    # carries the meaning is invisible. Small answers are framed whole.
    if focus_lats and len(rows) > 60:
        centre_lat = (max(focus_lats) + min(focus_lats)) / 2
        centre_lon = (max(focus_lons) + min(focus_lons)) / 2
        zoom = 11.2
    else:
        span = max(max(lats) - min(lats), (max(lons) - min(lons)) * 0.6, 0.004)
        zoom = 12.4 if span < 0.02 else 11.0 if span < 0.06 else (
            9.8 if span < 0.2 else 8.6 if span < 0.6 else 7.2
        )
        centre_lat = (max(lats) + min(lats)) / 2
        centre_lon = (max(lons) + min(lons)) / 2
    view = pdk.ViewState(
        latitude=centre_lat,
        longitude=centre_lon,
        zoom=zoom,
        pitch=0,
        bearing=0,
    )
    answer_tooltip = {
        "html": (
            "<div style='font-family:Segoe UI,Arial,sans-serif;width:225px;"
            "background:rgba(255,255,255,.82);backdrop-filter:blur(3px);"
            "border:1px solid rgba(136,19,55,.35);border-radius:14px;"
            "padding:10px 12px;box-shadow:0 10px 26px rgba(15,23,42,.16);'>"
            f"<div style='font-size:13.5px;font-weight:900;color:{C_HEAD};"
            "line-height:1.3;'>{name}</div>"
            f"<div style='font-size:10.5px;color:{C_MUTED};"
            "margin:2px 0 8px;'>{code} &middot; {role}</div>"
            "<div style='background:rgba(248,250,252,.75);border-radius:8px;"
            "padding:5px 7px;margin-bottom:5px;'>"
            f"<div style='font-size:9px;font-weight:800;color:{C_MUTED};"
            "text-transform:uppercase;letter-spacing:.05em;'>Deprivation"
            "</div>"
            f"<div style='font-size:13px;font-weight:800;color:{C_DEP};'>"
            "{dep_label} &middot; {wimd_label}</div></div>"
            + _school_tooltip_block()
            + "</div>"
        ),
        "style": {
            "backgroundColor": "transparent",
            "color": "#0f172a",
            "zIndex": "9999",
        },
    }
    st.markdown(PYDECK_TOOLTIP_CSS, unsafe_allow_html=True)
    # SCQ7 and SCQ8 fix the administrative side, so the anchor is a ward or
    # community rather than an LSOA and never appeared on this map: the focus
    # list only ever held LSOA codes. It is drawn on top, dark and outlined,
    # so the unit the question was asked about is visible beside its answer.
    map_layers = [layer]

    # Schools are evidence attached to the spatial answer, not a condition
    # for deciding which LSOAs belong to it.  Fetch them only after the full
    # answer set has been resolved, then draw them above the polygons.  This
    # restores the school pins without dropping answer regions that contain
    # no school.
    try:
        school_points = run_cypher(
            cfg,
            """
            MATCH (l:LSOA)<-[:LOCATED_IN]-(s:School)
            WHERE l.code IN $codes
              AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL
            OPTIONAL MATCH (s)-[near:DISTANCE_NEAR]->(:TransportStop)
            WITH l, s, min(near.distance_m) AS nearest_stop_distance_m
            RETURN DISTINCT
                   coalesce(s.name, s.school_name, s.code) AS school,
                   s.code AS school_code,
                   s.latitude AS latitude,
                   s.longitude AS longitude,
                   l.code AS lsoa_code,
                   coalesce(l.deprivation, s.deprivation, 'unknown') AS deprivation,
                   l.wimd_decile AS wimd_decile,
                   coalesce(s.phase_group, s.phase, s.school_type) AS school_type,
                   coalesce(s.local_authority_name, s.local_authority,
                            l.local_authority) AS local_authority,
                   s.fsm_pct AS fsm_pct,
                   s.attendance_pct AS attendance_pct,
                   s.capped9_score AS capped9_score,
                   coalesce(s.pupils_2025, s.pupils) AS pupils,
                   nearest_stop_distance_m
            ORDER BY school
            """,
            {"codes": sorted(selected_set) if selected_set else codes},
        )
    except Exception:
        school_points = pd.DataFrame()

    school_pin_layer = None
    if not school_points.empty:
        school_points = school_points.copy()
        school_points["deprivation"] = (
            school_points["deprivation"].fillna("unknown").astype(str)
        )
        school_points["icon"] = school_points["deprivation"].map(
            lambda d: PIN_ICONS.get(d, PIN_ICONS["unknown"])
        )
        school_points["name"] = school_points["school"]
        school_points["code"] = school_points["school_code"].fillna(
            school_points["lsoa_code"]
        )
        school_points["role"] = (
            "School in answer area " + school_points["lsoa_code"].astype(str)
        )
        school_points["dep_label"] = school_points["deprivation"].map(
            DEP_LABEL
        ).fillna("Unknown")
        school_points["wimd_label"] = school_points["wimd_decile"].map(
            lambda v: "N/A" if pd.isna(v) else f"decile {int(float(v))}"
        )
        for field, source in (
            ("school_count", None), ("fsm_avg", "fsm_pct"),
            ("att_avg", "attendance_pct"), ("cap_avg", "capped9_score"),
        ):
            school_points[field] = (
                1 if source is None else school_points[source]
            )
        school_points["fsm_n"] = school_points["fsm_pct"].notna().astype(int)
        school_points["att_n"] = school_points["attendance_pct"].notna().astype(int)
        school_points["cap_n"] = school_points["capped9_score"].notna().astype(int)
        school_pin_layer = pdk.Layer(
            "IconLayer",
            id="answer-schools",
            data=school_points,
            get_icon="icon",
            get_position=["longitude", "latitude"],
            get_size=3.7,
            size_scale=10,
            size_min_pixels=15,
            size_max_pixels=58,
            pickable=True,
            alpha_cutoff=-1,
        )
    if focus_admin:
        try:
            anchor = admin_polygons(
                (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
                (str(focus_admin),),
            )
        except Exception:
            anchor = pd.DataFrame()
        anchor_rows: List[Dict[str, Any]] = []
        for _, arow in anchor.iterrows():
            for ring in _wkt_rings(arow.get("wkt")):
                if len(ring) > 400:
                    ring = ring[:: len(ring) // 400 + 1] + [ring[-1]]
                anchor_rows.append({
                    "polygon": ring,
                    # Yellow identifies the area chosen by the user. The
                    # answer regions retain their existing evidence colours.
                    "fill": [250, 204, 21, 105],
                    "line": [17, 24, 39, 255],
                    "width": 6,
                    "name": arow.get("name") or str(focus_admin),
                    "code": str(arow.get("type") or "Administrative unit"),
                    "dep_label": "Not applicable",
                    "wimd_label": "N/A",
                    "role": "Chosen area",
                    **_school_card_fields({}),
                })
        # SCQ8 excludes the LSOAs the unit touches directly, because near
        # requires disjoint regions. Those excluded areas were simply absent
        # from the picture, so the answer looked as though it began at the
        # unit's edge. Drawing them hollow makes the gap visible, which is the
        # whole difference between near and intersects.
        # Only a near question leaves a gap. For SCQ7 the LSOAs the unit
        # intersects ARE the answer, so outlining them as excluded was wrong
        # and produced the hollow shapes over coloured regions.
        skipped: Tuple[str, ...] = ()
        try:
            skipped = () if not show_gap else admin_direct_lsoas(
                (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
                str(focus_admin),
            )
            # Some GRAPH_NEAR pairs also touch, through triangles in the
            # adjacency graph, so a code can be both a neighbour and a
            # genuine answer. Anything the query returned stays in the
            # answer and is never outlined as excluded.
            # Only the answer column counts. Scanning every column also
            # swept up via_base_lsoas, which lists the unit's OWN areas, so
            # the excluded ring was being cancelled by the very codes it was
            # meant to draw.
            answered = set()
            for col in ("lsoa_code", "code"):
                if col in result_df.columns:
                    answered = {
                        str(v) for v in result_df[col].dropna().tolist()
                    }
                    break
            skipped = tuple(c for c in skipped if c not in answered)
            gap_polys = (
                cluster_polygons(
                    (cfg["uri"], cfg["user"], cfg["password"],
                     cfg["database"]),
                    skipped,
                ) if skipped else pd.DataFrame()
            )
        except Exception:
            gap_polys = pd.DataFrame()
        gap_rows: List[Dict[str, Any]] = []
        for _, grow in gap_polys.iterrows():
            for ring in _wkt_rings(grow.get("wkt")):
                if len(ring) > 300:
                    ring = ring[:: len(ring) // 300 + 1] + [ring[-1]]
                gap_rows.append({
                    "polygon": ring,
                    "fill": [255, 255, 255, 30],
                    "line": [124, 58, 237, 235],
                    "width": 3,
                    "name": grow.get("name") or grow.get("code"),
                    "code": grow.get("code"),
                    "dep_label": "Not in the answer",
                    "wimd_label": "N/A",
                    "role": "Not near \u2014 it is the unit's own area or touches it",
                    **_school_card_fields({}),
                })

        if gap_rows:
            map_layers.append(pdk.Layer(
                "PolygonLayer",
                id="answer-excluded",
                data=gap_rows,
                get_polygon="polygon",
                get_fill_color="fill",
                get_line_color="line",
                get_line_width="width",
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                highlight_color=[124, 58, 237, 190],
            ))
        if anchor_rows:
            map_layers.append(pdk.Layer(
                "PolygonLayer",
                id="answer-anchor",
                data=anchor_rows,
                get_polygon="polygon",
                get_fill_color="fill",
                get_line_color="line",
                get_line_width="width",
                line_width_min_pixels=2,
                stroked=True,
                filled=False,
                # Pickable so the hover card explicitly identifies the
                # yellow polygon as the selected area.
                pickable=True,
            ))

    # Pins must be last: deck.gl resolves hover/click from the topmost layer.
    # Administrative polygons drawn after them would otherwise make the pins
    # visible but impossible to inspect.
    if school_pin_layer is not None:
        map_layers.append(school_pin_layer)

    picked = deck_chart_with_click(
        pdk.Deck(
            layers=map_layers,
            initial_view_state=view,
            map_style="light",
            tooltip=answer_tooltip,
            parameters={"clearColor": [0.98, 0.97, 0.97, 1]},
        ),
        key=key,
    )
    st.markdown(
        "<div class='map-note'>"
        "<b>Answer regions by deprivation level:</b> "
        "<span style='color:#e11d48;font-size:16px;'>&#9679;</span> High &nbsp; "
        "<span style='color:#ff8a00;font-size:16px;'>&#9679;</span> Medium &nbsp; "
        "<span style='color:#22c55e;font-size:16px;'>&#9679;</span> Low &nbsp; "
        "<span style='color:#94a3b8;font-size:16px;'>&#9679;</span> Unknown"
        "&nbsp;&middot;&nbsp; the yellow region is the selected area; "
        "regions outlined in purple and left unfilled are excluded from the "
        "answer. School pins are drawn above the complete spatial result; "
        "they do not filter it. Hover a pin or region for details."
        "</div>",
        unsafe_allow_html=True,
    )
    if drawn_note:
        st.caption(drawn_note)
    return str(picked.get("code")) if picked else None


@st.cache_data(show_spinner=False, ttl=600)
def admin_direct_lsoas(
    cfg_key: Tuple[str, str, str, str], uri: str
) -> Tuple[str, ...]:
    """LSOA codes the unit intersects directly — the ones near excludes."""
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    # Two rings are left out of a near answer, not one. The unit's own LSOAs
    # are excluded because near requires disjoint regions, and their direct
    # neighbours are excluded because they touch rather than lie near. Drawing
    # only the first ring left the answer looking as though it began at the
    # unit's edge, which is what made near read like intersects.
    df = run_cypher(cfg, """
    MATCH (a:AdminUnit {uri:$uri})-[:INTERSECTS]->(own:LSOA)
    OPTIONAL MATCH (own)-[:LSOA_TOUCHES]-(ring:LSOA)
    WITH collect(DISTINCT own.code) + collect(DISTINCT ring.code) AS codes
    UNWIND codes AS code
    RETURN DISTINCT code
    """, {"uri": uri})
    if df.empty:
        return ()
    return tuple(str(c) for c in df["code"].dropna().tolist())


@st.cache_data(show_spinner=False, ttl=1800)
def admin_polygons_by_name(
    cfg_key: Tuple[str, str, str, str], names: Tuple[str, ...]
) -> pd.DataFrame:
    """Boundary polygons for administrative units, looked up by name.

    The SCQ7 answer returns unit names and types but no URI, so there was
    nothing for the map to resolve. Names are not guaranteed unique across
    Wales, so this is a fallback: every match is drawn.
    """
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    return run_cypher(cfg, """
    MATCH (a:AdminUnit)
    WHERE a.name IN $names AND a.wkt IS NOT NULL
    RETURN a.uri AS uri, a.name AS name, a.type AS type, a.wkt AS wkt
    """, {"names": list(names)})


@st.cache_data(show_spinner=False, ttl=1800)
def admin_polygons(
    cfg_key: Tuple[str, str, str, str], uris: Tuple[str, ...]
) -> pd.DataFrame:
    """Boundary polygons for administrative units, by URI."""
    cfg = {
        "uri": cfg_key[0], "user": cfg_key[1],
        "password": cfg_key[2], "database": cfg_key[3],
    }
    return run_cypher(
        cfg,
        """
        MATCH (a:AdminUnit)
        WHERE a.uri IN $uris AND a.wkt IS NOT NULL
        RETURN a.uri AS uri,
               coalesce(a.name, a.uri) AS name,
               coalesce(a.type, 'Unknown') AS type,
               a.wkt AS wkt
        """,
        {"uris": list(uris)},
    )


# Containment reads at a glance only if the container is lighter than the
# thing it contains: the contained unit is drawn on top, so a dark container
# would simply hide it. Hue carries the administrative level, lightness
# carries the role in the answer.
# One hue, three depths. Hue told you the level but said nothing about the
# nesting, so where a Ward and a Community overlapped the two colours simply
# competed. Depth carries the level instead: the smaller the unit, the darker
# it sits, and an overlap reads as one shape shading into another.
ADMIN_FILL = {
    "Community": [14, 116, 144],
    "Ward": [79, 70, 229],
    "CommunityWard": [5, 150, 105],
    "CivilParishorCommunity": [225, 29, 72],
    "UnitaryAuthority": [234, 88, 12],
    "EuropeanRegion": [71, 85, 105],
    "Unknown": [148, 163, 184],
}
ADMIN_DEPTH = {
    "UnitaryAuthority": 70,
    "EuropeanRegion": 55,
    "Ward": 105,
    "CommunityWard": 120,
    "CivilParishorCommunity": 105,
    "Community": 95,
    "Unknown": 110,
}


@st.cache_data(show_spinner=False, ttl=600)
def admin_unit_school_counts(
    cfg_key: Tuple[str, str, str, str], uris: Tuple[str, ...]
) -> Dict[str, Dict[str, int]]:
    """How many schools sit inside each drawn unit, in a single round trip.

    One query for the whole map rather than one per polygon, because the
    containment map can draw hundreds of units at once.
    """
    if not uris:
        return {}
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    df = run_cypher(cfg, """
    MATCH (a:AdminUnit)-[:INTERSECTS]->(l:LSOA)
    WHERE a.uri IN $uris
    OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
    RETURN a.uri AS uri,
           count(DISTINCT l) AS lsoas,
           count(DISTINCT s) AS schools
    """, {"uris": list(uris)})
    if df.empty:
        return {}
    return {
        str(r["uri"]): {"lsoas": int(r["lsoas"]), "schools": int(r["schools"])}
        for _, r in df.iterrows()
    }


@st.cache_data(show_spinner=False, ttl=600)
def unit_school_detail(
    cfg_key: Tuple[str, str, str, str], uri: str
) -> pd.DataFrame:
    """Every school inside an administrative unit, one row each.

    The path is AdminUnit -[:INTERSECTS]-> LSOA <-[:LOCATED_IN]- School.
    Neither hop is native YAGO2geo: INTERSECTS is Geometry-origin and
    LOCATED_IN is Derived from the schools CSV. The card says so, because
    this page is where provenance is being measured.
    """
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    return run_cypher(cfg, """
    MATCH (a:AdminUnit {uri:$uri})-[:INTERSECTS]->(l:LSOA)
    OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
    WITH l, s WHERE s IS NOT NULL
    RETURN DISTINCT
        coalesce(s.name, s.school_name, s.code) AS school,
        coalesce(s.phase_group, s.phase, s.school_type) AS phase,
        l.code AS lsoa,
        coalesce(l.deprivation, s.deprivation) AS deprivation,
        s.fsm_pct AS fsm_pct,
        s.attendance_pct AS attendance_pct,
        coalesce(s.pupils_2025, s.pupils) AS pupils,
        s.latitude AS latitude,
        s.longitude AS longitude
    ORDER BY school
    """, {"uri": uri})


def render_unit_school_card(cfg: Dict[str, str], unit: Dict[str, Any]) -> None:
    """The clicked unit, its schools and their deprivation split."""
    uri = str(unit.get("uri") or "")
    if not uri:
        return
    name = str(unit.get("name") or uri)
    utype = str(unit.get("type") or "Administrative unit")
    try:
        df = unit_school_detail(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]), uri
        )
    except Exception:
        st.caption("The school detail for this unit could not be read.")
        return

    # INTERSECTS supplies candidate LSOAs only.  Confirm each school point is
    # inside the selected boundary so the card reports schools in the unit,
    # not schools in the outside portion of a boundary-crossing LSOA.
    try:
        boundary = admin_polygons(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            (uri,),
        )
        rings = []
        for _, boundary_row in boundary.iterrows():
            rings.extend(_wkt_rings(boundary_row.get("wkt")))
        if rings and not df.empty:
            df = df[
                df.apply(
                    lambda row: _point_in_admin_rings(
                        row.get("longitude"), row.get("latitude"), rings
                    ),
                    axis=1,
                )
            ].copy()
    except Exception:
        pass

    counts = (
        df["deprivation"].fillna("unknown").astype(str)
        .str.replace("_deprivation", "", regex=False).value_counts().to_dict()
        if not df.empty else {}
    )
    chips = "".join(
        f"<span style='display:inline-block;background:#f8fafc;"
        f"border:1px solid #eef2f7;border-radius:9px;padding:4px 9px;"
        f"margin:3px 5px 0 0;font-size:11px;font-weight:800;"
        f"color:{colour};'>{escape(label.title())} {counts.get(label, 0)}"
        "</span>"
        for label, colour in (
            ("high", "#e11d48"), ("medium", "#c2410c"),
            ("low", "#15803d"), ("unknown", "#64748b"),
        )
        if counts.get(label)
    )
    st.markdown(
        "<div style='font-family:Segoe UI,Arial,sans-serif;max-width:520px;"
        "background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;"
        "padding:12px 14px;box-shadow:0 10px 26px rgba(15,23,42,.10);"
        "margin-top:.6rem;'>"
        f"<div style='font-size:14px;font-weight:900;color:{C_HEAD};'>"
        f"{escape(name)}</div>"
        f"<div style='font-size:11px;color:{C_MUTED};margin:2px 0 8px;'>"
        f"{escape(utype)}</div>"
        f"<div style='font-size:22px;font-weight:900;color:{C_HEAD};"
        f"line-height:1;'>{int(df['lsoa'].nunique()) if not df.empty else 0}</div>"
        f"<div style='font-size:10px;font-weight:800;color:{C_MUTED};"
        "text-transform:uppercase;letter-spacing:.04em;'>"
        "LSOAs intersecting this unit</div>"
        f"<div style='margin-top:7px;font-size:12.5px;font-weight:700;"
        f"color:{C_HEAD};'>{len(df)} schools inside this boundary</div>"
        f"<div style='font-size:10px;color:{C_MUTED};margin-top:1px;"
        "line-height:1.45;'>School coordinates are checked against the "
        "selected administrative polygon after the intersecting LSOAs are "
        "used to find candidates.</div>"
        f"<div style='margin-top:7px;'>{chips}</div>"
        f"<div style='margin-top:9px;font-size:10px;color:{C_MUTED};"
        "line-height:1.45;'>Provenance: INTERSECTS (Geometry-origin) then "
        "LOCATED_IN (Derived); neither hop is asserted by native YAGO2geo. "
        "INTERSECTS supplies candidates; point-in-polygon confirms final "
        "school membership."
        "</div></div>",
        unsafe_allow_html=True,
    )
    if not df.empty:
        with st.expander(f"School detail for {name}", expanded=False):
            st.dataframe(
                df.drop(columns=["latitude", "longitude"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
            )


def render_admin_answer_map(
    cfg: Dict[str, str],
    result_df: pd.DataFrame,
    focus_lsoa: str | None,
    key: str = "admin_answer_map",
    focus_admin: str | None = None,
    selected_admin: str | None = None,
    selected_admins: Any = None,
) -> Dict[str, Any] | None:
    """Draw an answer whose rows are administrative units, not LSOAs.

    SCQ7 and SCQ8 read in both directions. When the fixed side is an LSOA the
    answer is a set of wards or communities, and the ordinary answer map had
    nothing to draw, because it only recognises LSOA codes. The selected LSOA
    is the dark anchor; the administrative units it reaches are drawn around
    it in the same depth palette the containment map uses, so the crossing
    from the statistical geography to the administrative one is visible.
    """
    if result_df is None or result_df.empty:
        return None
    # Column names differ between the SCQ7 and SCQ8 answers, so the column is
    # found by its contents rather than its label: any column whose values are
    # YAGO2geo resource URIs.
    uri_col = None
    for c in result_df.columns:
        series = result_df[c].dropna()
        if series.empty:
            continue
        if str(series.iloc[0]).startswith("http"):
            uri_col = c
            break

    if uri_col:
        keys = [str(u) for u in result_df[uri_col].dropna().unique().tolist()]
        by_name = False
    else:
        # SCQ7 returns unit names without URIs, so fall back to name lookup
        # rather than drawing nothing at all.
        name_col = next(
            (c for c in result_df.columns
             if str(c).lower() in ("administrative_unit", "unit", "name",
                                   "contained_unit")),
            None,
        )
        if not name_col:
            return None
        keys = [str(v) for v in result_df[name_col].dropna().unique().tolist()]
        by_name = True
    uris = keys
    if not uris:
        return None
    # DRAW_CAP is a local in the containment map, not a module constant; this
    # function needs its own ceiling.
    admin_draw_cap = 400
    if len(uris) > admin_draw_cap:
        st.caption(
            f"Showing {admin_draw_cap:,} of {len(uris):,} administrative "
            "units on the map. The table below holds every row."
        )
        uris = uris[:admin_draw_cap]

    cfg_key = (cfg["uri"], cfg["user"], cfg["password"], cfg["database"])
    try:
        polys = (
            admin_polygons_by_name(cfg_key, tuple(uris)) if by_name
            else admin_polygons(cfg_key, tuple(uris))
        )
    except Exception:
        return None
    if polys is None or polys.empty:
        return None

    selected_set = {
        str(u) for u in (
            selected_admins
            if isinstance(selected_admins, (list, tuple, set))
            else [selected_admin or selected_admins]
        ) if u
    }
    rows: List[Dict[str, Any]] = []
    answer_rings: Dict[str, List[List[List[float]]]] = {}
    lons: List[float] = []
    lats: List[float] = []
    for _, prow in polys.iterrows():
        polygon_uri = str(prow.get("uri") or "")
        utype = str(prow.get("type") or "Unknown")
        base = ADMIN_FILL.get(utype, ADMIN_FILL["Unknown"])
        depth = ADMIN_DEPTH.get(utype, ADMIN_DEPTH["Unknown"])
        is_selected = polygon_uri in selected_set
        has_selection = bool(selected_set)
        for ring in _wkt_rings(prow.get("wkt")):
            answer_rings.setdefault(polygon_uri, []).append(ring)
            if len(ring) > 400:
                ring = ring[:: len(ring) // 400 + 1] + [ring[-1]]
            for pt in ring:
                lons.append(pt[0]); lats.append(pt[1])
            rows.append({
                "polygon": ring,
                "fill": base + ([215] if is_selected else [32] if has_selection else [depth]),
                "line": (
                    [17, 24, 39, 255] if is_selected
                    else base + [85] if has_selection
                    else [17, 24, 39, 220]
                ),
                "width": 6 if is_selected else 1 if has_selection else 2,
                "uri": str(prow.get("uri") or ""),
                "name": prow.get("name") or prow.get("uri"),
                "type": utype,
                "role": "Selected answer area" if is_selected else "In the answer",
            })

    if focus_admin:
        try:
            source = admin_polygons(cfg_key, (str(focus_admin),))
        except Exception:
            source = pd.DataFrame()
        for _, arow in source.iterrows():
            for ring in _wkt_rings(arow.get("wkt")):
                if len(ring) > 400:
                    ring = ring[:: len(ring) // 400 + 1] + [ring[-1]]
                for pt in ring:
                    lons.append(pt[0]); lats.append(pt[1])
                rows.append({
                    "polygon": ring,
                    "fill": [124, 58, 237, 45],
                    "line": [124, 58, 237, 255],
                    "width": 6,
                    "uri": str(arow.get("uri") or ""),
                    "name": arow.get("name") or arow.get("uri"),
                    "type": arow.get("type") or "AdminUnit",
                    "role": "Chosen source unit",
                })

    if focus_lsoa:
        try:
            anchor = cluster_polygons(cfg_key, (str(focus_lsoa),))
        except Exception:
            anchor = pd.DataFrame()
        for _, arow in anchor.iterrows():
            for ring in _wkt_rings(arow.get("wkt")):
                if len(ring) > 400:
                    ring = ring[:: len(ring) // 400 + 1] + [ring[-1]]
                for pt in ring:
                    lons.append(pt[0]); lats.append(pt[1])
                rows.append({
                    "polygon": ring,
                    "fill": [250, 204, 21, 225],
                    "line": [17, 24, 39, 255],
                    "width": 5,
                    "uri": str(focus_lsoa),
                    "name": arow.get("name") or str(focus_lsoa),
                    "type": "LSOA",
                    "role": "Chosen area",
                })

    if not rows or not lats:
        return None

    # deck.gl picks whatever is drawn last, so a small unit sitting inside a
    # larger one was unreachable. Ordering by ring extent puts the smallest
    # shapes on top, which makes every unit clickable.
    def _extent(r: Dict[str, Any]) -> float:
        ring = r["polygon"]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    rows.sort(key=_extent, reverse=True)

    span = max(max(lats) - min(lats), (max(lons) - min(lons)) * 0.6, 0.004)
    view = pdk.ViewState(
        latitude=(max(lats) + min(lats)) / 2,
        longitude=(max(lons) + min(lons)) / 2,
        zoom=12.4 if span < 0.02 else 11.0 if span < 0.06 else (
            9.8 if span < 0.2 else 8.6 if span < 0.6 else 7.2
        ),
        pitch=0, bearing=0,
    )
    tooltip = {
        "html": (
            "<div style='font-family:Segoe UI,Arial,sans-serif;width:215px;"
            "background:rgba(255,255,255,.9);border-radius:13px;"
            "padding:10px 12px;box-shadow:0 10px 26px rgba(15,23,42,.16);'>"
            f"<div style='font-size:13.5px;font-weight:900;color:{C_HEAD};'>"
            "{name}</div>"
            f"<div style='font-size:10.5px;color:{C_MUTED};margin-top:2px;'>"
            "{type} &middot; {uri}</div>"
            f"<div style='font-size:12px;font-weight:700;color:{C_WIMD};"
            "margin-top:6px;'>{role}</div></div>"
        ),
        "style": {"backgroundColor": "transparent"},
    }
    st.markdown(PYDECK_TOOLTIP_CSS, unsafe_allow_html=True)
    admin_layers = [pdk.Layer(
        "PolygonLayer",
        id="admin-answer",
        data=rows,
        get_polygon="polygon",
        get_fill_color="fill",
        get_line_color="line",
        get_line_width="width",
        line_width_min_pixels=1,
        stroked=True, filled=True, pickable=True,
        auto_highlight=True,
        highlight_color=[124, 58, 237, 190],
    )]

    # Put school pins back on administrative answers too.  INTERSECTS finds
    # candidate LSOAs, then the point-in-polygon check prevents a school in
    # the outside part of a boundary-crossing LSOA being assigned to a unit.
    answer_uris = tuple(sorted(set(str(u) for u in polys["uri"].dropna())))
    if selected_set:
        # Once an authority is selected, its schools are the relevant detail.
        # Removing the other pins also makes the selected boundary readable.
        answer_uris = tuple(u for u in answer_uris if u in selected_set)
    try:
        school_points = run_cypher(cfg, """
        MATCH (u:AdminUnit)-[:INTERSECTS]->(l:LSOA)<-[:LOCATED_IN]-(s:School)
        WHERE u.uri IN $uris
          AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        RETURN DISTINCT u.uri AS unit_uri,
               coalesce(s.name, s.school_name, s.code) AS school,
               s.code AS school_code, s.latitude AS latitude,
               s.longitude AS longitude,
               coalesce(l.deprivation, s.deprivation, 'unknown') AS deprivation
        ORDER BY school
        """, {"uris": list(answer_uris)})
    except Exception:
        school_points = pd.DataFrame()
    if not school_points.empty:
        school_points = school_points[
            school_points.apply(
                lambda r: _point_in_admin_rings(
                    r.get("longitude"), r.get("latitude"),
                    answer_rings.get(str(r.get("unit_uri")), []),
                ),
                axis=1,
            )
        ].drop_duplicates(subset=["school_code", "latitude", "longitude"])
    if not school_points.empty:
        school_points = school_points.copy()
        school_points["icon"] = school_points["deprivation"].map(
            lambda d: PIN_ICONS.get(str(d), PIN_ICONS["unknown"])
        )
        school_points["name"] = school_points["school"]
        school_points["type"] = "School"
        school_points["role"] = "School inside an answer area"
        school_points["uri"] = ""
        admin_layers.append(pdk.Layer(
            "IconLayer", id="admin-answer-schools", data=school_points,
            get_icon="icon", get_position=["longitude", "latitude"],
            get_size=3.7, size_scale=10, size_min_pixels=15,
            size_max_pixels=48, pickable=False, alpha_cutoff=-1,
        ))

    picked = deck_chart_with_click(
        pdk.Deck(
            layers=admin_layers,
            initial_view_state=view,
            map_style="light",
            tooltip=tooltip,
            parameters={"clearColor": [0.98, 0.97, 0.97, 1]},
        ),
        key=key,
    )
    st.markdown(
        "<div class='small-muted' style='margin-top:.35rem'>"
        + (
            "The purple outline is the chosen administrative unit; "
            if focus_admin else
            "The yellow shape is the selected LSOA; "
        )
        + "the returned administrative units are the exact query answer. "
        "School pins are an information layer and do not filter the areas."
        "</div>",
        unsafe_allow_html=True,
    )
    return picked


def render_admin_containment_map(
    cfg: Dict[str, str],
    result_df: pd.DataFrame,
    focus_uri: str | None,
    focus_contains: bool,
    key: str = "admin_map",
) -> Dict[str, Any] | None:
    """Draw a containment answer: container pale, contained solid on top.

    focus_contains is True for SCQ6, where the selected unit is the parent
    and the answer rows are its children, and False for SCQ5, where the
    selected unit is the child and the answer rows are its parents.
    """
    if result_df is None or result_df.empty or "uri" not in result_df.columns:
        return

    row_uris = [str(u) for u in result_df["uri"].dropna().tolist()]
    if not row_uris:
        return

    # Rendering every child of a unitary authority would mean hundreds of
    # polygons; the table above is never truncated, only the drawing is.
    DRAW_CAP = 400
    drawn_note = ""
    if len(row_uris) > DRAW_CAP:
        drawn_note = (
            f"Showing {DRAW_CAP:,} of {len(row_uris):,} units on the map for "
            "speed. The count above and the table below are the full answer."
        )
        stride = max(1, len(row_uris) // DRAW_CAP)
        row_uris = row_uris[::stride][:DRAW_CAP]

    wanted = list(row_uris)
    if focus_uri:
        wanted.append(str(focus_uri))

    try:
        polys = admin_polygons(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            tuple(sorted(set(wanted))),
        )
    except Exception as exc:
        st.caption(f"Boundaries could not be loaded: {exc}")
        return
    if polys.empty:
        return

    try:
        school_counts = admin_unit_school_counts(
            (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
            tuple(sorted(set(wanted))),
        )
    except Exception:
        school_counts = {}

    row_set = set(row_uris)
    containers, contained = [], []
    lats: List[float] = []
    lons: List[float] = []

    for _, prow in polys.iterrows():
        uri = str(prow["uri"])
        is_focus = focus_uri is not None and uri == str(focus_uri)
        # Whoever does the containing is drawn pale, regardless of which
        # side of the question it sits on.
        is_container = is_focus if focus_contains else (uri in row_set)
        base = ADMIN_FILL.get(str(prow.get("type")), ADMIN_FILL["Unknown"])
        for ring in _wkt_rings(prow.get("wkt")):
            if len(ring) > 400:
                ring = ring[:: len(ring) // 400 + 1] + [ring[-1]]
            for pt in ring:
                lons.append(pt[0]); lats.append(pt[1])
            item = {
                "polygon": ring,
                # uri is what the click handler needs to look the unit up;
                # without it the panel below the map had nothing to open.
                "uri": uri,
                "lsoas": school_counts.get(uri, {}).get("lsoas", 0),
                "schools": school_counts.get(uri, {}).get("schools", 0),
                "name": prow.get("name"),
                "type": prow.get("type"),
                "role": (
                    "Contains the selected unit"
                    if (is_container and not is_focus)
                    else "Chosen area"
                    if is_focus
                    else "Inside the selected unit"
                ),
            }
            depth = ADMIN_DEPTH.get(
                str(prow.get("type")), ADMIN_DEPTH["Unknown"]
            )
            if is_focus:
                # The user's selection uses one consistent colour across
                # SCQ1-SCQ8, irrespective of its administrative level.
                item["fill"] = [250, 204, 21, 150]
                item["line"] = [17, 24, 39, 255]
                item["width"] = 6
                if is_container:
                    containers.append(item)
                else:
                    contained.append(item)
            elif is_container:
                # The container keeps its thick outline and stays faint, so
                # anything drawn inside it remains legible through the fill.
                item["fill"] = base + [max(30, depth // 3)]
                item["line"] = base + [255]
                item["width"] = 5
                containers.append(item)
            else:
                item["fill"] = base + [depth]
                item["line"] = [17, 24, 39, 220]
                item["width"] = 2
                contained.append(item)

    if not lats:
        return

    # The children of a unitary authority tile it completely, so a pale
    # container drawn underneath disappears entirely. Its boundary is
    # therefore redrawn, unfilled, on top of everything.
    outline_rows = [
        {**item, "fill": [0, 0, 0, 0], "width": 6}
        for item in containers
    ]

    layers = []
    # Containers first so the contained units sit on top of them. The outline
    # copy sits above everything and must NOT be pickable: deck.gl picks by
    # polygon area, not by stroke, so a transparent container drawn on top
    # would swallow every hover and report the parent for each child.
    for rows_, layer_id, pickable in (
        (containers, "admin-container", True),
        (contained, "admin-contained", True),
        (outline_rows, "admin-container-outline", False),
    ):
        if rows_:
            layers.append(
                pdk.Layer(
                    "PolygonLayer",
                    id=layer_id,
                    data=rows_,
                    get_polygon="polygon",
                    get_fill_color="fill",
                    get_line_color="line",
                    get_line_width="width",
                    line_width_min_pixels=1,
                    stroked=True,
                    filled=True,
                    pickable=pickable,
                    auto_highlight=pickable,
                    highlight_color=[251, 191, 36, 170],
                )
            )
    if not layers:
        return

    span = max(max(lats) - min(lats), (max(lons) - min(lons)) * 0.6, 0.004)
    zoom = 12.2 if span < 0.02 else 10.8 if span < 0.06 else (
        9.6 if span < 0.2 else 8.4 if span < 0.6 else 7.0
    )
    view = pdk.ViewState(
        latitude=(max(lats) + min(lats)) / 2,
        longitude=(max(lons) + min(lons)) / 2,
        zoom=zoom, pitch=0, bearing=0,
    )
    tooltip = {
        "html": (
            "<div style='font-family:Segoe UI,Arial,sans-serif;width:215px;"
            "background:rgba(255,255,255,.85);backdrop-filter:blur(3px);"
            "border:1px solid rgba(30,41,59,.28);border-radius:14px;"
            "padding:10px 12px;box-shadow:0 10px 26px rgba(15,23,42,.16);'>"
            f"<div style='font-size:13.5px;font-weight:900;color:{C_HEAD};"
            "line-height:1.3;'>{name}</div>"
            f"<div style='font-size:10.5px;color:{C_MUTED};"
            "margin:2px 0 6px;'>{type}</div>"
            f"<div style='font-size:12px;font-weight:700;color:{C_WIMD};'>"
            "{role}</div>"
            f"<div style='margin-top:6px;font-size:11.5px;font-weight:800;"
            f"color:{C_HEAD};'>{{lsoas}} LSOAs intersect this unit</div>"
            f"<div style='font-size:10.5px;font-weight:700;color:{C_MUTED};"
            "margin-top:1px;'>holding {schools} schools between them</div>"
            "</div>"
        ),
        "style": {"backgroundColor": "transparent", "color": "#0f172a",
                  "zIndex": "9999"},
    }

    st.markdown(PYDECK_TOOLTIP_CSS, unsafe_allow_html=True)
    picked_unit = deck_chart_with_click(
        pdk.Deck(
            layers=layers,
            initial_view_state=view,
            map_style="light",
            tooltip=tooltip,
            parameters={"clearColor": [0.98, 0.97, 0.97, 1]},
        ),
        key=key,
    )
    st.markdown(
        "<div class='map-note'>"
        "<b>Containment:</b> the selected area is yellow. The containing "
        "unit is drawn pale with a thick "
        "outline; the unit or units inside it are filled solid on top. "
        "Depth marks the level, so overlapping units stay readable \u2014 "
        "<span style='color:#94a3d6;font-size:16px;'>&#9679;</span> Unitary "
        "Authority &nbsp; "
        "<span style='color:#4f62a8;font-size:16px;'>&#9679;</span> Ward "
        "&nbsp; <span style='color:#1e2d69;font-size:16px;'>&#9679;</span> "
        "Community. Administrative units carry no WIMD value, so deprivation "
        "is not shown here."
        "</div>",
        unsafe_allow_html=True,
    )
    if drawn_note:
        st.caption(drawn_note)
    return picked_unit


GUIDED_TYPE_LABELS = {
    "LSOA": "LSOA (statistical area)",
    "Community": "Community",
    "Ward": "Community ward",
    "CommunityWard": "Community ward",
    "CivilParishorCommunity": "Civil parish or community",
    "UnitaryAuthority": "Unitary authority",
    "EuropeanRegion": "European region",
}

# The 22 Welsh principal councils from the OS data used by the loader.  This
# is the authoritative administrative seed for the public search.  Geometry
# alone is not enough to define the country at the border: an English area can
# legitimately touch or intersect a Welsh boundary and must not then become a
# selectable Welsh place.
WELSH_UA_OS_IDS = (
    "25492", "25494", "25502", "25484", "25496", "44426",
    "25498", "25493", "25483", "25497", "25495", "25491",
    "25500", "25490", "25485", "25487", "25489", "25486",
    "25482", "25776", "44425", "25831",
)

GUIDED_RELATION_LABELS = {
    "touches": "touches",
    "near": "is near",
    "not_touches": "does not touch",
    "within": "is within",
    "contains": "contains",
    "intersects": "intersects",
    "between": "lies between",
}


def clear_guided_result() -> None:
    """A changed input invalidates the answer until Search is pressed."""
    st.session_state.pop("guided_has_run", None)
    st.session_state.pop("guided_selected_admin", None)
    st.session_state.pop("guided_selected_admins", None)
    st.session_state.pop("guided_selected_lsoas", None)


def clear_guided_selection() -> None:
    """Clear map emphasis without discarding the query and its answer."""
    st.session_state.pop("guided_selected_admin", None)
    st.session_state.pop("guided_selected_admins", None)
    st.session_state.pop("guided_selected_lsoas", None)
    st.session_state.pop("guided_lsoa_results_table", None)
    st.session_state.pop("guided_admin_results_table", None)
    st.session_state["guided_selection_version"] = (
        int(st.session_state.get("guided_selection_version", 0)) + 1
    )


def guided_admin_kind_expr(alias: str) -> str:
    """Canonical administrative type from the actual YAGO2geo spelling."""
    raw = (
        # raw_type preserves the ontology class before the loader folds both
        # OS_COMMUNITY and OS_CivilParishorCommunity into `Community`.
        f"toLower(replace(replace(coalesce({alias}.raw_type, "
        f"{alias}.type, ''), '_', ''), ' ', ''))"
    )
    return (
        "CASE "
        f"WHEN {raw} CONTAINS 'civilparishorcommunity' "
        "THEN 'CivilParishorCommunity' "
        f"WHEN {raw} CONTAINS 'communityward' OR {raw} = 'ward' "
        "THEN 'CommunityWard' "
        f"WHEN {raw} CONTAINS 'unitaryauthority' "
        "THEN 'UnitaryAuthority' "
        f"WHEN {raw} CONTAINS 'europeanregion' "
        "THEN 'EuropeanRegion' "
        f"WHEN {raw} CONTAINS 'community' THEN 'Community' "
        f"ELSE coalesce({alias}.raw_type, {alias}.type, 'Unknown') END"
    )


def guided_wales_admin_predicate(alias: str) -> str:
    """True for a unit in, or above, the 22 Welsh unitary authorities."""
    ids = "[" + ",".join(repr(x) for x in WELSH_UA_OS_IDS) + "]"
    return (
        "(coalesce(toString(" + alias + ".os_id),'') IN " + ids + " "
        "OR EXISTS { MATCH (" + alias + ")-[:WITHIN*1..5]->(ua:AdminUnit) "
        "WHERE coalesce(toString(ua.os_id),'') IN " + ids + " } "
        "OR EXISTS { MATCH (ua:AdminUnit)-[:WITHIN*1..5]->(" + alias + ") "
        "WHERE coalesce(toString(ua.os_id),'') IN " + ids + " })"
    )


def guided_pair_supported(domain: str, range_: str, relation: str) -> bool:
    """Apply the dissertation table, plus the explicit SCQ8 composition."""
    possible = _possible_pair_relations(domain, range_)
    if relation == "near" and ((domain == "LSOA") != (range_ == "LSOA")):
        # Cross-geography near is not a direct edge. It is the SCQ8 path
        # INTERSECTS -> GRAPH_NEAR (or its reverse).
        return "intersects" in possible
    table_relation = {
        "near": "touches", "between": "touches",
        "not_touches": "disjoint",
    }.get(relation, relation)
    return table_relation in possible


@st.cache_data(show_spinner=False, ttl=600)
def guided_entity_types(
    cfg_key: Tuple[str, str, str, str]
) -> Tuple[str, ...]:
    """Only expose geographic types that actually exist in this graph."""
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    admin_kind = guided_admin_kind_expr("n")
    wales_admin = guided_wales_admin_predicate("n")
    rows = run_cypher(cfg, f"""
    MATCH (n)
    WHERE n:LSOA OR (n:AdminUnit AND {wales_admin})
    RETURN DISTINCT CASE WHEN n:LSOA THEN 'LSOA' ELSE {admin_kind} END AS kind
    ORDER BY kind
    """)
    if rows.empty:
        return ()
    preferred = [
        "LSOA", "Community", "CommunityWard",
        "CivilParishorCommunity", "UnitaryAuthority", "EuropeanRegion",
    ]
    found = {str(v) for v in rows["kind"].dropna().tolist()}
    return tuple(k for k in preferred if k in found)


@st.cache_data(show_spinner=False, ttl=300)
def guided_anchor_options(
    cfg_key: Tuple[str, str, str, str], kind: str
) -> Tuple[Tuple[str, str], ...]:
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    if kind == "LSOA":
        query = """
        MATCH (n:LSOA)
        RETURN n.code AS value,
               coalesce(n.name, n.code) + ' · ' + n.code AS label
        ORDER BY label
        """
    else:
        admin_kind = guided_admin_kind_expr("n")
        wales_admin = guided_wales_admin_predicate("n")
        query = f"""
        MATCH (n:AdminUnit)
        WHERE {admin_kind} = $kind AND {wales_admin}
        RETURN n.uri AS value, coalesce(n.name, n.uri) AS label
        ORDER BY label
        """
    rows = run_cypher(cfg, query, {"kind": kind})
    if rows.empty:
        return ()
    return tuple(
        (str(r["value"]), str(r["label"])) for _, r in rows.iterrows()
        if pd.notna(r.get("value"))
    )


@st.cache_data(show_spinner=False, ttl=180)
def guided_capabilities(
    cfg_key: Tuple[str, str, str, str], kind: str, anchor: str
) -> pd.DataFrame:
    """Relations and result types that return data for this exact anchor."""
    cfg = {"uri": cfg_key[0], "user": cfg_key[1],
           "password": cfg_key[2], "database": cfg_key[3]}
    if kind == "LSOA":
        unit_kind = guided_admin_kind_expr("u")
        query = """
        MATCH (a:LSOA {code:$anchor})
        CALL {
          WITH a MATCH (a)-[:LSOA_TOUCHES]-(b:LSOA)
          RETURN 'touches' AS relation, 'LSOA' AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:GRAPH_NEAR]-(b:LSOA)
          RETURN 'near' AS relation, 'LSOA' AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (b:LSOA)
          WHERE b <> a AND NOT (a)-[:LSOA_TOUCHES]-(b)
          RETURN 'not_touches' AS relation, 'LSOA' AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (u:AdminUnit)-[:INTERSECTS]->(a)
          RETURN 'intersects' AS relation, __UNIT_KIND__ AS result_type,
                 count(DISTINCT u) AS n
          UNION
          WITH a MATCH (a)-[:GRAPH_NEAR]-(b:LSOA)<-[:INTERSECTS]-(u:AdminUnit)
          WHERE NOT (u)-[:INTERSECTS]->(a)
          RETURN 'near' AS relation, __UNIT_KIND__ AS result_type,
                 count(DISTINCT u) AS n
          UNION
          WITH a MATCH (a)-[:LSOA_TOUCHES]-(:LSOA)
          RETURN 'between' AS relation, 'LSOA' AS result_type,
                 count(*) AS n
        }
        WITH relation, result_type, n WHERE n > 0
        RETURN relation, result_type, n
        """.replace("__UNIT_KIND__", unit_kind)
    else:
        a_kind = guided_admin_kind_expr("a")
        b_kind = guided_admin_kind_expr("b")
        b_wales = guided_wales_admin_predicate("b")
        m_wales = guided_wales_admin_predicate("m")
        query = """
        MATCH (a:AdminUnit {uri:$anchor})
        CALL {
          WITH a MATCH (a)-[:TOUCHES]-(b:AdminUnit)
          WHERE __B_WALES__
          RETURN 'touches' AS relation, __B_KIND__ AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:TOUCHES]-(m:AdminUnit)-[:TOUCHES]-(b:AdminUnit)
          WHERE b <> a AND __B_KIND__ = __A_KIND__
            AND __B_WALES__ AND __M_WALES__ AND NOT (a)-[:TOUCHES]-(b)
          RETURN 'near' AS relation, __B_KIND__ AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (b:AdminUnit)
          WHERE __B_KIND__ = __A_KIND__ AND __B_WALES__
            AND b <> a AND NOT (a)-[:TOUCHES]-(b)
          RETURN 'not_touches' AS relation, __B_KIND__ AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:WITHIN]->(b:AdminUnit)
          WHERE __B_WALES__
          RETURN 'within' AS relation, __B_KIND__ AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (b:AdminUnit)-[:WITHIN]->(a)
          WHERE __B_WALES__
          RETURN 'contains' AS relation, __B_KIND__ AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:INTERSECTS]->(b:LSOA)
          RETURN 'intersects' AS relation, 'LSOA' AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:INTERSECTS]->(base:LSOA)-[:GRAPH_NEAR]-(b:LSOA)
          WHERE NOT (a)-[:INTERSECTS]->(b)
          RETURN 'near' AS relation, 'LSOA' AS result_type,
                 count(DISTINCT b) AS n
          UNION
          WITH a MATCH (a)-[:TOUCHES]-(b:AdminUnit)
          WHERE __B_KIND__ = __A_KIND__ AND __B_WALES__
          RETURN 'between' AS relation, __A_KIND__ AS result_type,
                 count(DISTINCT b) AS n
        }
        WITH relation, result_type, n WHERE n > 0
        RETURN relation, result_type, n
        """.replace("__A_KIND__", a_kind).replace("__B_KIND__", b_kind) \
           .replace("__B_WALES__", b_wales).replace("__M_WALES__", m_wales)
    return run_cypher(cfg, query, {"anchor": anchor})


def guided_result_query(
    kind: str, relation: str, result_type: str
) -> str:
    """Cypher for one validated guided-search combination."""
    if kind == "LSOA":
        if relation == "near" and result_type != "LSOA":
            unit_kind = guided_admin_kind_expr("u")
            return """
                MATCH (a:LSOA {code:$anchor})-[:GRAPH_NEAR]-(b:LSOA)
                      <-[:INTERSECTS]-(u:AdminUnit)
                WHERE __UNIT_KIND__ = $result_type
                  AND NOT (u)-[:INTERSECTS]->(a)
                RETURN DISTINCT u.uri AS unit_uri,
                       coalesce(u.name,u.uri) AS unit_name,
                       __UNIT_KIND__ AS unit_type
                ORDER BY unit_name
            """.replace("__UNIT_KIND__", unit_kind)
        unit_kind = guided_admin_kind_expr("u")
        queries = {
            "touches": """
                MATCH (a:LSOA {code:$anchor})-[:LSOA_TOUCHES]-(b:LSOA)
                RETURN DISTINCT b.code AS lsoa_code,
                       coalesce(b.name,b.code) AS name, 'LSOA' AS result_type
                ORDER BY name""",
            "near": """
                MATCH (a:LSOA {code:$anchor})-[:GRAPH_NEAR]-(b:LSOA)
                RETURN DISTINCT b.code AS lsoa_code,
                       coalesce(b.name,b.code) AS name, 'LSOA' AS result_type
                ORDER BY name""",
            "not_touches": """
                MATCH (a:LSOA {code:$anchor}), (b:LSOA)
                WHERE b <> a AND NOT (a)-[:LSOA_TOUCHES]-(b)
                RETURN DISTINCT b.code AS lsoa_code,
                       coalesce(b.name,b.code) AS name, 'LSOA' AS result_type
                ORDER BY name""",
            "intersects": """
                MATCH (u:AdminUnit)-[:INTERSECTS]->(a:LSOA {code:$anchor})
                WHERE __UNIT_KIND__ = $result_type
                RETURN DISTINCT u.uri AS unit_uri, coalesce(u.name,u.uri) AS unit_name,
                       __UNIT_KIND__ AS unit_type ORDER BY unit_name""",
        }
        return queries[relation].replace("__UNIT_KIND__", unit_kind)

    b_kind = guided_admin_kind_expr("b")
    b_wales = guided_wales_admin_predicate("b")
    m_wales = guided_wales_admin_predicate("m")
    if relation == "near" and result_type == "LSOA":
        return """
            MATCH (a:AdminUnit {uri:$anchor})-[:INTERSECTS]->(base:LSOA)
                  -[:GRAPH_NEAR]-(b:LSOA)
            WHERE NOT (a)-[:INTERSECTS]->(b)
            RETURN DISTINCT b.code AS lsoa_code,
                   coalesce(b.name,b.code) AS name,
                   'LSOA' AS result_type
            ORDER BY name
        """
    queries = {
        "touches": """
            MATCH (a:AdminUnit {uri:$anchor})-[:TOUCHES]-(b:AdminUnit)
            WHERE __B_KIND__ = $result_type AND __B_WALES__
            RETURN DISTINCT b.uri AS unit_uri, coalesce(b.name,b.uri) AS unit_name,
                   __B_KIND__ AS unit_type ORDER BY unit_name""",
        "near": """
            MATCH (a:AdminUnit {uri:$anchor})-[:TOUCHES]-(m:AdminUnit)
                  -[:TOUCHES]-(b:AdminUnit)
            WHERE b <> a AND __B_KIND__ = $result_type
              AND __B_WALES__ AND __M_WALES__ AND NOT (a)-[:TOUCHES]-(b)
            RETURN DISTINCT b.uri AS unit_uri, coalesce(b.name,b.uri) AS unit_name,
                   __B_KIND__ AS unit_type ORDER BY unit_name""",
        "not_touches": """
            MATCH (a:AdminUnit {uri:$anchor}), (b:AdminUnit)
            WHERE __B_KIND__ = $result_type AND b <> a
              AND __B_WALES__ AND NOT (a)-[:TOUCHES]-(b)
            RETURN DISTINCT b.uri AS unit_uri, coalesce(b.name,b.uri) AS unit_name,
                   __B_KIND__ AS unit_type ORDER BY unit_name""",
        "within": """
            MATCH (a:AdminUnit {uri:$anchor})-[:WITHIN]->(b:AdminUnit)
            WHERE __B_KIND__ = $result_type AND __B_WALES__
            RETURN DISTINCT b.uri AS unit_uri, coalesce(b.name,b.uri) AS unit_name,
                   __B_KIND__ AS unit_type ORDER BY unit_name""",
        "contains": """
            MATCH (b:AdminUnit)-[:WITHIN]->(a:AdminUnit {uri:$anchor})
            WHERE __B_KIND__ = $result_type AND __B_WALES__
            RETURN DISTINCT b.uri AS unit_uri, coalesce(b.name,b.uri) AS unit_name,
                   __B_KIND__ AS unit_type ORDER BY unit_name""",
        "intersects": """
            MATCH (a:AdminUnit {uri:$anchor})-[:INTERSECTS]->(b:LSOA)
            RETURN DISTINCT b.code AS lsoa_code, coalesce(b.name,b.code) AS name,
                   'LSOA' AS result_type ORDER BY name""",
    }
    return queries[relation].replace("__B_KIND__", b_kind) \
        .replace("__B_WALES__", b_wales).replace("__M_WALES__", m_wales)


def render_guided_natural_search(cfg: Dict[str, str]) -> None:
    """Natural wording routed through the same spatial resolver as the map."""
    qcol, bcol = st.columns([7, 1.2])
    with qcol:
        text = st.text_input(
            "Place question",
            placeholder="Try: Which Communities touch Cathays Community?",
            label_visibility="collapsed",
            key="place_nl_question",
        )
    with bcol:
        asked = st.button(
            "Search", type="primary", use_container_width=True,
            key="place_nl_search",
        )
    if asked:
        st.session_state.pop("place_nl_scope", None)
        st.session_state.pop("place_nl_error", None)
        hint = _map_admin_hint(text)
        if not text.strip() or not hint or not hint.get("anchor_name"):
            st.session_state["place_nl_error"] = (
                "We could not identify the place, area type and spatial "
                "relationship. Try the example shown in the search box."
            )
        else:
            try:
                scope, _warnings = resolve_map_admin_scope(cfg, hint)
            except Exception:
                scope = None
            if scope is None:
                st.session_state["place_nl_error"] = (
                    "That relationship is not available for the place and "
                    "area types in your question."
                )
            else:
                st.session_state["place_nl_scope"] = scope

    error = st.session_state.get("place_nl_error")
    if error:
        st.info(error)
        return
    scope = st.session_state.get("place_nl_scope")
    if not scope:
        return

    anchor = scope.get("anchor") or {}
    relation = str(scope.get("relation") or "spatial relation")
    result_kind = str(scope.get("result_kind") or "AdminUnit")
    if result_kind == "Schools":
        st.info(
            "This page returns geographic areas. Use Schools map to search "
            "for individual schools and education indicators."
        )
        return
    if result_kind == "LSOA":
        codes = sorted(set(scope.get("lsoa_codes") or []))
        result = pd.DataFrame({"lsoa_code": codes})
        if result.empty:
            st.info("No LSOA satisfies this relationship for the selected place.")
            return
        st.metric("Areas found", len(result))
        clicked = render_answer_map(
            cfg, result, key="place_nl_lsoa_map",
            focus_admin=str(anchor.get("uri") or ""),
        )
        if clicked:
            render_lsoa_school_panel(cfg, clicked)
        display_df(result)
        return

    units = scope.get("units", pd.DataFrame())
    result = (
        units.dropna(subset=["unit_uri"]).drop_duplicates("unit_uri")
        if isinstance(units, pd.DataFrame) and not units.empty
        else pd.DataFrame()
    )
    if result.empty:
        st.info(
            f"No area satisfies {relation.replace('_', ' ')} for "
            f"{anchor.get('name', 'the selected place')}."
        )
        return
    st.metric("Areas found", len(result))
    picked = render_admin_answer_map(
        cfg, result, None, key="place_nl_admin_map",
        focus_admin=str(anchor.get("uri") or ""),
    )
    if picked:
        render_unit_school_card(cfg, picked)
    display_df(result)


def page_guided_spatial_search(cfg: Dict[str, str]) -> None:
    """Clean, progressive spatial search for a first-time user."""
    st.markdown("""
    <style>
    /* The SCQ landing page has no sidebar controls. Remove the empty brand
       rail so the search experience uses the full browser width. */
    section[data-testid="stSidebar"],
    div[data-testid="stSidebarCollapsedControl"],
    button[data-testid="stBaseButton-headerNoPadding"]{
      display:none!important}
    [data-testid="stAppViewContainer"]>.main{
      margin-left:0!important;width:100%!important}
    .guided-hero{max-width:980px;margin:1.1rem auto 1.45rem;text-align:center;
      padding:2.25rem 1.5rem;border-radius:28px;
      background:linear-gradient(125deg,#ff707c 0%,#ff9a72 52%,#ffc55c 100%);
      box-shadow:0 22px 55px rgba(185,76,55,.18)}
    .guided-hero h1{font-size:clamp(2rem,4vw,3.35rem);line-height:1.05;
      letter-spacing:-.045em;margin:0;color:#fff;font-weight:850}
    .guided-hero p{font-size:1.02rem;color:#fff7f2;margin:.65rem auto 0;
      max-width:620px;line-height:1.55}
    .guided-card{background:white;border:1px solid #e8eaf0;border-radius:22px;
      padding:1.1rem 1.25rem .35rem;box-shadow:0 12px 34px rgba(15,23,42,.07)}
    .guided-sentence{font-size:1.15rem;font-weight:750;color:#4a2b25;
      padding:.85rem 1rem;background:#fff3ec;border:1px solid #ffd9c8;
      border-radius:14px;margin:.6rem 0 1rem}
    div[data-testid="stSelectbox"] label p{
      color:#63372f!important;font-weight:800!important;letter-spacing:.01em}
    div[data-testid="stSelectbox"]>div>div{
      min-height:3.15rem;border-radius:15px!important;
      background:linear-gradient(180deg,#fffdfa 0%,#fff7f1 100%)!important;
      border:1px solid #f3cbbc!important;
      box-shadow:0 7px 18px rgba(117,58,43,.07)!important}
    div[data-testid="stSelectbox"]>div>div:hover{
      border-color:#ff9278!important;
      box-shadow:0 9px 22px rgba(255,112,124,.12)!important}
    div[data-testid="stSelectbox"] svg{color:#b35443!important}
    div[data-testid="stDataFrame"]{
      border:1px solid #f0cfc2!important;border-radius:18px!important;
      overflow:hidden!important;background:#fffdfa!important;
      box-shadow:0 14px 34px rgba(91,48,38,.09)!important;
      padding:5px!important}
    div[data-testid="stDataFrame"] [role="columnheader"]{
      background:#fff0e8!important;color:#65362e!important;
      font-weight:800!important}
    div[data-testid="stDataFrame"] [role="gridcell"]{
      border-color:#f5e5de!important}
    div[data-testid="stMetric"]{
      background:linear-gradient(135deg,#fffdfa,#fff3ec)!important;
      border:1px solid #f2d5ca!important;border-radius:16px!important;
      box-shadow:0 9px 24px rgba(91,48,38,.06)!important;
      padding:.65rem .9rem!important}
    div[data-testid="stMetric"] [data-testid="stMetricValue"]{
      color:#4c2b25!important;font-weight:850!important}
    button[data-baseweb="tab"]{color:#6d4a42!important;font-weight:750!important}
    button[data-baseweb="tab"][aria-selected="true"]{
      color:#d6534f!important;border-color:#ff776f!important}
    div[data-testid="stTextInput"] input{border-radius:999px!important;
      min-height:3.3rem;padding-left:1.25rem;border:1px solid #dfe3ea;
      box-shadow:0 10px 28px rgba(15,23,42,.06)}
    </style>
    <div class="guided-hero"><h1>Ask the Welsh place knowledge graph</h1>
    <p>Explore how LSOAs and administrative areas touch, intersect, contain
    or lie near one another. Schools appear in the areas returned.</p></div>
    """, unsafe_allow_html=True)

    cfg_key = (cfg["uri"], cfg["user"], cfg["password"], cfg["database"])
    try:
        kinds = guided_entity_types(cfg_key)
    except Exception:
        st.error("The place data could not be loaded. Please try again.")
        return
    if not kinds:
        st.info("No geographic areas are available in the current graph.")
        return

    guided, words = st.tabs(["Build a search", "Write in your own words"])
    with words:
        render_guided_natural_search(cfg)

    with guided:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kind = st.selectbox(
                "Area type", kinds,
                format_func=lambda k: GUIDED_TYPE_LABELS.get(k, k),
                key="guided_kind",
                on_change=clear_guided_result,
            )
        try:
            anchors = guided_anchor_options(cfg_key, kind)
        except Exception:
            st.error("Places for this area type could not be loaded.")
            return
        if not anchors:
            st.info("No places are available for this area type.")
            return
        with c2:
            anchor = st.selectbox(
                "Place", anchors, format_func=lambda x: x[1],
                key=f"guided_anchor_{kind}",
                on_change=clear_guided_result,
            )

        try:
            caps = guided_capabilities(cfg_key, kind, anchor[0])
        except Exception:
            st.error("Relationships for this place could not be loaded.")
            return
        if caps.empty:
            st.info(
                "No spatial relationship is currently represented for this "
                "place and area type."
            )
            return
        caps = caps[
            caps.apply(
                lambda row: guided_pair_supported(
                    kind, str(row["result_type"]), str(row["relation"])
                ),
                axis=1,
            )
        ].copy()
        if caps.empty:
            st.info("No valid spatial relationship is available for this selection.")
            return
        relations = [
            r for r in GUIDED_RELATION_LABELS
            if r in set(caps["relation"].astype(str))
        ]
        with c3:
            relation = st.selectbox(
                "Relationship", relations,
                format_func=lambda r: GUIDED_RELATION_LABELS[r],
                key="guided_relation",
                on_change=clear_guided_result,
            )
        valid_types = [
            str(v) for v in caps.loc[
                caps["relation"].astype(str) == relation, "result_type"
            ].dropna().drop_duplicates().tolist()
        ]
        with c4:
            result_type = st.selectbox(
                "Find", valid_types,
                format_func=lambda k: GUIDED_TYPE_LABELS.get(k, k),
                key="guided_result_type",
                on_change=clear_guided_result,
            )

        second = None
        if relation == "between":
            second_options = [x for x in anchors if x[0] != anchor[0]]
            second = st.selectbox(
                "Second place", second_options, format_func=lambda x: x[1],
                key=f"guided_second_{kind}",
                on_change=clear_guided_result,
            )

        result_label = GUIDED_TYPE_LABELS.get(result_type, result_type)
        if relation == "contains":
            sentence = f"Find {result_label} areas within {anchor[1]}"
        elif relation == "within":
            sentence = f"Find {result_label} areas that contain {anchor[1]}"
        elif relation == "near":
            sentence = f"Find {result_label} areas near {anchor[1]}"
        elif relation == "intersects":
            sentence = f"Find {result_label} areas that intersect {anchor[1]}"
        elif relation == "touches":
            sentence = f"Find {result_label} areas that touch {anchor[1]}"
        elif relation == "not_touches":
            sentence = f"Find {result_label} areas that do not touch {anchor[1]}"
        elif relation == "between":
            sentence = f"Find {result_label} areas between {anchor[1]} and {second[1]}"
        else:
            sentence = (
                f"Find {result_label} areas that "
                f"{GUIDED_RELATION_LABELS[relation]} {anchor[1]}"
                + (f" and {second[1]}" if second else "")
            )
        st.markdown(
            f"<div class='guided-sentence'>{escape(sentence)}</div>",
            unsafe_allow_html=True,
        )
        run = st.button("Search", type="primary", use_container_width=True,
                        key="guided_run")
        state_key = "guided_has_run"
        if run:
            st.session_state[state_key] = True
        if not st.session_state.get(state_key):
            return

        params = {"anchor": anchor[0], "result_type": result_type}
        if relation == "between":
            if not second:
                return
            edge = "LSOA_TOUCHES" if kind == "LSOA" else "TOUCHES"
            node = "LSOA" if kind == "LSOA" else "AdminUnit"
            key_prop = "code" if kind == "LSOA" else "uri"
            type_guard = "" if kind == "LSOA" else "AND b.type = $result_type"
            query = f"""
            MATCH (a:{node} {{{key_prop}:$anchor}}),
                  (b:{node} {{{key_prop}:$second}})
            WHERE a <> b {type_guard}
            MATCH p = shortestPath((a)-[:{edge}*..12]-(b))
            UNWIND CASE WHEN length(p) > 1 THEN nodes(p)[1..-1] ELSE [] END AS x
            RETURN DISTINCT x.{key_prop} AS {'lsoa_code' if kind == 'LSOA' else 'unit_uri'},
                   coalesce(x.name, x.{key_prop}) AS {'name' if kind == 'LSOA' else 'unit_name'},
                   {'\'LSOA\'' if kind == 'LSOA' else 'x.type'} AS {'result_type' if kind == 'LSOA' else 'unit_type'}
            """
            params["second"] = second[0]
        else:
            query = guided_result_query(kind, relation, result_type)
        try:
            result = run_cypher(cfg, query, params)
        except Exception:
            st.error(
                "We could not complete this search. Try another place or "
                "relationship."
            )
            if SHOW_QUERIES:
                st.code(query, language="cypher")
            return

        st.markdown("### Results")
        st.metric("Areas found", len(result))
        has_guided_selection = bool(
            st.session_state.get("guided_selected_lsoas")
            or st.session_state.get("guided_selected_admins")
        )
        if has_guided_selection:
            reset_left, reset_col, reset_right = st.columns([2.4, 1, 2.4])
            with reset_col:
                st.button(
                    "Clear selected areas", key="guided_reset_selection",
                    use_container_width=True, on_click=clear_guided_selection,
                )
        if result.empty:
            st.info(
                "No area satisfies this relationship for the selected place."
            )
            return
        if result_type == "LSOA":
            lsoa_col = next(
                (c for c in ("lsoa_code", "code") if c in result.columns),
                None,
            )
            selected_lsoas = set(st.session_state.get("guided_selected_lsoas", []))
            table_result = result.reset_index(drop=True)
            clicked = render_answer_map(
                cfg, result,
                focus_code=(
                    [anchor[0], second[0]]
                    if kind == "LSOA" and relation == "between" and second
                    else anchor[0] if kind == "LSOA" else None
                ),
                focus_admin=anchor[0] if kind != "LSOA" else None,
                show_excluded_neighbours=(relation == "not_touches"),
                selected_codes=selected_lsoas,
                key="guided_lsoa_map",
            )
            if clicked and re.match(r"^W\d{8}$", clicked):
                render_lsoa_school_panel(cfg, clicked)
            st.caption(
                "Select one or more rows to emphasise those answer areas. "
                "Select a row again to remove it from the selection."
            )
            if lsoa_col:
                try:
                    table_event = st.dataframe(
                        warm_table(table_result), use_container_width=True,
                        hide_index=True,
                        on_select="rerun", selection_mode="multi-row",
                        key=(
                            "guided_lsoa_results_table_"
                            f"{st.session_state.get('guided_selection_version', 0)}"
                        ),
                    )
                    selected_rows = list(table_event.selection.rows)
                    table_selected_lsoas = {
                        str(table_result.iloc[int(i)][lsoa_col])
                        for i in selected_rows
                    }
                    if table_selected_lsoas != selected_lsoas:
                        st.session_state["guided_selected_lsoas"] = sorted(
                            table_selected_lsoas
                        )
                        st.rerun()
                except TypeError:
                    display_df(table_result)
        else:
            selected_admins = set(
                st.session_state.get("guided_selected_admins", [])
            )
            valid_result_uris = set(
                str(v) for v in result.get("unit_uri", pd.Series(dtype=str)).dropna()
            )
            selected_admins &= valid_result_uris
            picked = render_admin_answer_map(
                cfg, result, anchor[0] if kind == "LSOA" else None,
                focus_admin=anchor[0] if kind != "LSOA" else None,
                selected_admins=selected_admins,
                key="guided_admin_map",
            )
            st.caption(
                "Select a row to focus that area. Its boundary stays strong, "
                "the other answers fade, and only its school pins remain."
            )
            table_result = result.reset_index(drop=True)
            visible_cols = [
                c for c in ("unit_name", "unit_type", "unit_uri")
                if c in table_result.columns
            ] or list(table_result.columns)
            try:
                table_event = st.dataframe(
                    warm_table(table_result[visible_cols]),
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=(
                        "guided_admin_results_table_"
                        f"{st.session_state.get('guided_selection_version', 0)}"
                    ),
                )
                selected_rows = list(table_event.selection.rows)
            except TypeError:
                # Older Streamlit versions keep the result usable through a
                # searchable selector instead of silently losing selection.
                selected_rows = []
                table_choice = st.selectbox(
                    "Explore an area",
                    list(range(len(table_result))),
                    format_func=lambda i: str(
                        table_result.iloc[i].get("unit_name")
                        or table_result.iloc[i].get("unit_uri")
                    ),
                    index=None,
                    placeholder="Choose an answer area",
                    key="guided_admin_result_fallback",
                )
                if table_choice is not None:
                    selected_rows = [int(table_choice)]
                display_df(table_result[visible_cols])
            table_selected_admins = {
                str(table_result.iloc[int(i)].get("unit_uri") or "")
                for i in selected_rows
            } - {""}
            if table_selected_admins != selected_admins:
                st.session_state["guided_selected_admins"] = sorted(
                    table_selected_admins
                )
                st.rerun()

            selected_admins = set(st.session_state.get("guided_selected_admins", []))
            for selected_admin in sorted(selected_admins):
                selected_row = table_result[
                    table_result["unit_uri"].astype(str) == selected_admin
                ]
                if not selected_row.empty:
                    chosen = selected_row.iloc[0].to_dict()
                    render_unit_school_card(
                        cfg,
                        {
                            **chosen,
                            "uri": chosen.get("unit_uri"),
                            "name": chosen.get("unit_name"),
                            "type": chosen.get("unit_type"),
                        },
                    )
        if result_type == "LSOA" and lsoa_col is None:
            display_df(result)
        if SHOW_QUERIES:
            with st.expander("Cypher"):
                st.code(query.strip(), language="cypher")
                st.json(params)


def page_scq_demonstrator(
    cfg: Dict[str, str],
) -> None:
    hero()

    task_badge(
        "SCQ Demonstrator",
        (
            "Run SCQ1–SCQ8 over the integrated Neo4j graph while "
            "showing the query, parameters, results, and provenance "
            "of the relation used."
        ),
        "Complete",
    )

    # The question box comes first: a reader who knows what they want to ask
    # should not have to work out which of eight forms it corresponds to.
    # Both helpers take a mode. The touch list is the widest LSOA set and the
    # parent list is the widest administrative one, which is all the parser
    # needs: it only has to recognise a name, not decide what can answer.
    try:
        nl_lsoas = lsoa_options(cfg, "lsoa_touch")
    except Exception:
        nl_lsoas = []
    try:
        nl_admin = nl_admin_options(cfg)
    except Exception:
        nl_admin = []
    # The deterministic panel is the instrument: every figure reported in
    # the dissertation was produced by it. The sentence box is a
    # demonstration of query understanding, and it misroutes often enough
    # that it should not be the first thing a reader meets. So it is folded,
    # and the eight forms are open.
    with st.expander("Ask a question in your own words", expanded=False):
        render_nl_search(nl_lsoas, nl_admin)
        render_nl_understanding()

    # The panel is the other route, so the sentence's answer is dropped
    # BEFORE it is drawn, not after. Clearing it afterwards left the old
    # answer on screen for one more run, which is why it took two clicks
    # to go away.
    if st.session_state.get("scq_manual_open"):
        st.session_state.pop("nl_answer", None)

    # The answer belongs directly under the question that produced it.
    _answered = render_question_answer(cfg)

    # The question and the controls are one path, not two. Without saying so,
    # a reader cannot tell whether a selector still holds a value from the
    # last question or one they chose themselves, which is exactly how a
    # result for the wrong unit gets read as an answer.
    _driven = st.session_state.get("nl_controls_set") or []
    # Once the reader changes the form themselves, the sentence no longer
    # describes what is on screen. Claiming otherwise would misreport the
    # provenance of the answer, so the notice is dropped instead.
    _nl_last = st.session_state.get("nl_last") or {}
    if _nl_last.get("scq") and st.session_state.get("scq_select") != _nl_last.get("scq"):
        _driven = []
    if st.session_state.get("nl_question") and _driven:
        col_note, col_clear = st.columns([5, 1])
        with col_note:
            st.markdown(
                "<div class='nl-driven'>The controls below were set by your "
                "question: <b>" + escape(", ".join(str(d) for d in _driven))
                + "</b>. Change any of them to override it.</div>",
                unsafe_allow_html=True,
            )
        with col_clear:
            if st.button("Clear question", use_container_width=True):
                st.session_state["nl_question"] = ""
                st.session_state.pop("nl_last", None)
                st.session_state.pop("nl_controls_set", None)
                st.rerun()

    # Nothing is pre-selected. A default would answer a question the reader
    # never asked, and once a question box sits above these controls there is
    # no way to tell a default apart from something the sentence set.
    # The manual route is folded away by default. The box above is the way
    # in; the eight forms and their selectors are the way to override it or
    # to work without a sentence. Keeping them closed until asked for stops
    # a reader wondering whether a selector holds a value they never set.
    # When a question drives the controls the panel opens itself, because
    # the reader has to be able to see what the sentence chose.
    if _answered:
        st.divider()

    _open = st.checkbox(
        "Choose the question yourself",
        value=True,
        key="scq_manual_open",
        help=(
            "Open this to pick one of the eight spatial forms, or either "
            "lens, and set its parameters by hand. A question typed above "
            "opens it automatically and fills it in."
        ),
    )
    if not _open:
        st.caption(
            "The eight spatial forms and the two lenses are folded away. "
            "Tick the box to choose one, or open the sentence box above."
        )
        return

    scq_key = st.selectbox(
        t("select_scq"),
        [""] + list(SCQ_META.keys()),
        format_func=lambda key: (
            "\u2014 choose a spatial question \u2014" if not key
            else SCQ_META[key]["label"]
        ),
        key="scq_select",
    )
    if not scq_key:
        st.info(
            "Choose one of the eight forms above, or ask a question in your "
            "own words and it will be chosen for you."
        )
        return

    meta = SCQ_META[scq_key]

    # SCQ7/SCQ8 support both starting points over the same stored facts.
    direction = "lsoa"
    if scq_key in ("SCQ7", "SCQ8"):
        direction = direction_toggle(f"{scq_key}_direction")
        st.caption(t("direction_caption"))

    left, right = st.columns([2.2, 1])

    with left:
        st.subheader(scq_question(scq_key, meta))
        st.write(meta["keyword_sentence"])
        with st.expander(
            "Literature warrant and the questions this relation answers",
            expanded=False,
        ):
            render_scq_evidence(scq_key)

        mode, cost, counts = SCQ_ANSWER_MODE.get(
            scq_key, ("Computed-then-stored", "Paid once", "No")
        )
        st.markdown(
            "<div class='solutionbox'>"
            f"<b>Answering mode:</b> {mode} &nbsp;·&nbsp; "
            f"<b>Geometric cost:</b> {cost} &nbsp;·&nbsp; "
            f"<b>Counts toward model completeness:</b> {counts}"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(MODE_NOTE.get(mode, ""))

    with right:
        shown_relation = meta["relation"]
        shown_provenance = meta["provenance"]
        if scq_key == "SCQ3":
            _kind = st.session_state.get("scq3_kind", "LSOA")
            if _kind != "LSOA":
                shown_relation = "TOUCHES path"
                shown_provenance = "Native"
        st.markdown(
            f"**{t('relation_used')}**\n\n`{shown_relation}`"
        )
        st.markdown(
            (
                f"**{t('provenance_h')}**\n\n"
                f"{provenance_badge(shown_provenance)}"
            ),
            unsafe_allow_html=True,
        )

    # No result-limit control: every SCQ returns its full answer so the
    # counts on screen are the real figures and can go straight into the
    # research log. The parameter is kept at a high internal ceiling only to
    # stop a pathological query from hanging the app.
    limit = 5000

    scq3_hops = 6

    params: Dict[str, Any] = {
        "limit": limit,
    }


    param_type = meta["param_type"]
    if scq_key in ("SCQ7", "SCQ8") and direction == "admin":
        param_type = meta["param_type_reverse"]

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

        # Landing on an empty state reads as a broken page to anyone who has
        # not been told to pick something first. Opening on the first Cardiff
        # LSOA means the demonstrator shows a worked answer on arrival, while
        # the placeholder stays in the list for anyone who wants it.
        lsoa_choices = [("", "\u2014 choose an LSOA \u2014")] + list(options)
        default_lsoa = next(
            (i for i, opt in enumerate(lsoa_choices)
             if str(opt[1]).lower().startswith("cardiff")),
            0,
        )
        selected_lsoa = st.selectbox(
            t("lsoa_label"),
            lsoa_choices,
            format_func=lambda option: option[1],
            index=default_lsoa,
            key=f"{scq_key}_lsoa",
        )
        if not selected_lsoa[0]:
            st.info(
                "Choose an LSOA, or name one in the question box above."
            )
            return

        params["lsoa"] = selected_lsoa[0]

    elif param_type == "lsoa_pair":
        # The paper's own worked example of between is over communities, not
        # statistical areas, and administrative TOUCHES is native while
        # LSOA_TOUCHES had to be computed. Offering both levels lets the same
        # question be asked through a native relation and a derived one.
        between_kind = st.radio(
            "Between over",
            ["LSOA", "Ward", "Community"],
            horizontal=True,
            key="scq3_kind",
            format_func=lambda k: (
                "LSOA \u2014 computed adjacency" if k == "LSOA"
                else f"{k} \u2014 native adjacency"
            ),
            help=(
                "The definition is identical at every level. What changes is "
                "where the adjacency came from: YAGO2geo asserts TOUCHES "
                "between administrative units, while adjacency between LSOAs "
                "had to be computed from boundary geometry."
            ),
        )
        if between_kind == "LSOA":
            pair_lsoas = lsoa_options(cfg, "lsoa_touch")
        else:
            pair_lsoas = admin_touch_options(cfg, between_kind)

        if len(pair_lsoas) < 2:
            st.error(
                f"Not enough connected {between_kind} units were found "
                "for SCQ3."
            )
            return

        col_a, col_b = st.columns(2)

        with col_a:
            selected_a = st.selectbox(
                t("lsoa_a"),
                pair_lsoas,
                index=0,
                format_func=lambda option: option[1],
                key="scq3_lsoa_a",
            )

        with col_b:
            selected_b = st.selectbox(
                t("lsoa_b"),
                pair_lsoas,
                index=1,
                format_func=lambda option: option[1],
                key="scq3_lsoa_b",
            )

        params["lsoa_a"] = selected_a[0]
        params["lsoa_b"] = selected_b[0]

        try:
            pair_hops = lsoa_hop_distance(
                (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
                selected_a[0], selected_b[0], between_kind,
            )
        except Exception:
            pair_hops = None

        if pair_hops == 0:
            st.warning(
                "Both selectors hold the same area. Between needs two "
                "different regions."
            )
        elif pair_hops == 1:
            st.warning(
                "These two areas touch. The paper defines between as lying "
                "on a cycle-free path linking the pair, and a touching pair "
                "is joined by a single edge, so nothing lies between them: "
                "every region returned reaches them by a detour, which is "
                "why the answer reads as a ring around the pair rather than "
                "a corridor. Pick a pair three or four steps apart."
            )
        elif pair_hops is None:
            st.warning(
                "No adjacency path links these two areas within 12 steps, "
                "so between has no answer for this pair."
            )
        else:
            st.success(
                f"These areas are {pair_hops} steps apart. A hop bound of "
                f"{pair_hops + 1} or {pair_hops + 2} keeps the answer to the "
                "corridor between them."
            )

        _hop_options = [2, 3, 4, 5, 6, 7, 8]
        _suggested = (
            min(8, max(2, pair_hops + 1)) if pair_hops else 6
        )
        scq3_hops = st.select_slider(
            t("max_hops"),
            options=_hop_options,
            value=_suggested,
            key="scq3_hops",
        )
        st.caption(
            "The paper defines between as any cycle-free path linking the "
            "two regions and sets no numeric bound. Enumerating unbounded "
            "simple paths here is combinatorially intractable, so this hop "
            "bound is a tractability necessity, not a definitional choice. "
            "Record the value used: the number of paths grows sharply with "
            "it."
        )
        st.caption(t("scq3_interp"))

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

        # Labels are "Name | Type", so the type can be filtered before the
        # list reaches the widget. This is also the single biggest speed win
        # on this page: the unfiltered list can carry ~19,000 options, and
        # every one of them is serialised to the browser on each rerun.
        unit_types = sorted({
            str(label).rsplit("|", 1)[-1].strip()
            for _value, label in admin_units
            if "|" in str(label)
        })
        chosen_type = st.selectbox(
            "Unit type",
            ["All types"] + unit_types,
            key=f"{scq_key}_admin_type",
            help=(
                "Narrows the list below to one level of the hierarchy. "
                "Typing in the unit box alone cannot do this, because it "
                "matches the whole label."
            ),
        )
        if chosen_type != "All types":
            admin_units = [
                (value, label) for value, label in admin_units
                if str(label).rsplit("|", 1)[-1].strip() == chosen_type
            ]

        admin_choices = (
            [("", "\u2014 choose an administrative unit \u2014")]
            + list(admin_units)
        )
        default_admin_idx = next(
            (i for i, opt in enumerate(admin_choices)
             if str(opt[1]).lower().startswith("cardiff")),
            0,
        )
        selected_admin = st.selectbox(
            t("admin_unit_label"),
            admin_choices,
            index=default_admin_idx,
            format_func=lambda option: option[1],
            key=f"{scq_key}_admin",
        )
        if not selected_admin[0]:
            st.info(
                "Choose an administrative unit, or name one in the question "
                "box above."
            )
            return

        params["admin"] = selected_admin[0]

    elif param_type == "education_lens":
        types = lens_unit_types(cfg)
        if not types:
            st.error("No administrative units were found in this database.")
            return

        # Settings parked by the question box are applied here, and only
        # when the value actually exists in the list the graph returned.
        _pend = st.session_state.pop("LENS_pending", None)
        if _pend:
            if _pend.get("atype") in types:
                st.session_state["LENS_atype"] = _pend["atype"]
            if _pend.get("mode") in LENS_MODES:
                st.session_state["LENS_mode"] = _pend["mode"]
            st.session_state["LENS_return"] = "Schools"
            if _pend.get("filter") in (
                "None", "High FSM", "Low attendance", "High deprivation"
            ):
                st.session_state["LENS_filter"] = _pend["filter"]
            if _pend.get("ntype") in types:
                st.session_state["LENS_ntype"] = _pend["ntype"]
            st.session_state["LENS_pending_uri"] = _pend.get("uri")

        c1, c2 = st.columns(2)
        with c1:
            anchor_type = st.selectbox(
                "Start from which kind of unit?", types, key="LENS_atype",
            )
        with c2:
            mode = st.selectbox(
                "Which relation?",
                list(LENS_MODES),
                format_func=lambda m: LENS_MODES[m][0],
                key="LENS_mode",
            )

        want = st.radio(
            "Return",
            ["Schools", "Administrative units"],
            horizontal=True,
            key="LENS_return",
            help=(
                "A question about communities is answered with communities. "
                "Choose Schools only when the question asks about schools."
            ),
        )

        anchors = lens_anchor_options(cfg, anchor_type)
        if not anchors:
            st.warning(
                f"No {anchor_type} in this graph can reach an LSOA by any "
                "stored relation, so no school can be attached to it. "
                "That absence is a result, not an error."
            )
            return

        choices = [("", "\u2014 choose a unit \u2014")] + list(anchors)
        _want = st.session_state.pop("LENS_pending_uri", None)
        if _want:
            _hit = next(
                (o for o in choices if o[0] == _want), None
            )
            if _hit is not None:
                st.session_state["LENS_unit"] = _hit
        selected = st.selectbox(
            "Unit", choices, format_func=lambda o: o[1], key="LENS_unit",
        )
        if not selected[0]:
            st.info("Choose a unit to start from.")
            return
        params["admin"] = selected[0]

        nbr_type = None
        if mode not in ("direct", "near"):
            nbr_choice = st.selectbox(
                "Which kind of related unit?", ["Any type"] + types,
                key="LENS_ntype",
                help=(
                    "Leave as Any to see every type the relation reaches, "
                    "or pick one to ask a specific pair such as Community "
                    "to Ward."
                ),
            )
            nbr_type = None if nbr_choice == "Any type" else nbr_choice
        elif mode == "near":
            # The control is withheld rather than disabled, because offering
            # a choice the definition cannot honour is what produced empty
            # answers with no reason attached.
            st.caption(
                "Near is defined inside one division: disjoint units of the "
                "same kind joined by a path of two touches edges (IJGI 2024, "
                "\u00a73.4). The related unit is therefore the same kind as "
                "the one you started from, and no type choice applies."
            )
        params["nbr_type"] = nbr_type

        # The school path needs INTERSECTS, which only some types carry.
        # Report that limit explicitly instead of returning an empty table.
        if want == "Schools":
            reachable = types_with_intersects(cfg)
            blocked = None
            if mode == "direct" and anchor_type not in reachable:
                blocked = anchor_type
            elif mode != "direct" and nbr_type and nbr_type not in reachable:
                blocked = nbr_type
            if blocked:
                st.warning(
                    f"This question cannot currently be answered from the "
                    f"represented relations. No stored relation connects "
                    f"{blocked} to LSOA, so no school can be attached to it. "
                    f"Only {', '.join(sorted(reachable))} carry INTERSECTS. "
                    f"Switch Return to Administrative units to ask about the "
                    f"units themselves."
                )
                return

        filt = st.radio(
            "Education filter",
            ["None", "High FSM", "Low attendance", "High deprivation"],
            horizontal=True, key="LENS_filter",
        )
        params["phase"] = None
        params["fsm_min"] = 30.0 if filt == "High FSM" else None
        params["att_max"] = 90.0 if filt == "Low attendance" else None
        params["dep"] = "High" if filt == "High deprivation" else None

        if want == "Administrative units" and mode in LENS_UNIT_CYPHER:
            st.session_state["LENS_active_cypher"] = LENS_UNIT_CYPHER[mode]
        elif want == "Administrative units":
            st.warning(
                "The direct relation returns the unit you already chose, "
                "so units are not a meaningful answer here. Showing "
                "schools instead."
            )
            st.session_state["LENS_active_cypher"] = LENS_CYPHER[mode]
        else:
            st.session_state["LENS_active_cypher"] = LENS_CYPHER[mode]
        label, chain, prov = LENS_MODES[mode]
        st.caption(
            f"Chain: {chain}  \u2014  Provenance: {prov}. "
            "This answer was possible because of relations added by this "
            "project. It does not raise the coverage of the original "
            "YAGO2geo model."
        )

    elif param_type == "school_lens":
        schools = school_lens_options(cfg)
        if not schools:
            st.warning(
                "No school in this graph is placed in an LSOA, so no "
                "school-anchored question can be answered. That absence is "
                "a result, not an error."
            )
            return
        s1, s2 = st.columns(2)
        with s1:
            picked = st.selectbox(
                "School",
                [("", "\u2014 choose a school \u2014")] + list(schools),
                format_func=lambda o: o[1],
                key="SLENS_school",
            )
        with s2:
            smode = st.selectbox(
                "Which relation?",
                list(SCHOOL_LENS_MODES),
                format_func=lambda m: SCHOOL_LENS_MODES[m][0],
                key="SLENS_mode",
            )
        if not picked[0]:
            st.info("Choose a school to start from.")
            return
        params["school"] = picked[0]
        sfilt = st.radio(
            "Education filter",
            ["None", "High FSM", "Low attendance", "High deprivation"],
            horizontal=True, key="SLENS_filter",
        )
        params["phase"] = None
        params["fsm_min"] = 30.0 if sfilt == "High FSM" else None
        params["att_max"] = 90.0 if sfilt == "Low attendance" else None
        params["dep"] = "High" if sfilt == "High deprivation" else None
        st.session_state["SLENS_active_cypher"] = SCHOOL_LENS_CYPHER[smode]
        _l, _c, _p = SCHOOL_LENS_MODES[smode]
        st.caption(
            f"Chain: {_c}  \u2014  Provenance: {_p}. "
            "This answer was possible because of relations added by this "
            "project. It does not raise the coverage of the original "
            "YAGO2geo model."
        )

    run_query = st.button(
        t("run_query"),
        type="primary",
    )

    active_cypher = (
        meta["cypher_reverse"]
        if (scq_key in ("SCQ7", "SCQ8") and direction == "admin")
        else meta["cypher"]
    )

    if param_type == "education_lens":
        active_cypher = st.session_state.get(
            "LENS_active_cypher", meta["cypher"]
        )

    if param_type == "school_lens":
        active_cypher = st.session_state.get(
            "SLENS_active_cypher", meta["cypher"]
        )

    if scq_key == "SCQ3":
        active_cypher = (
            SCQ3_CYPHER_TEMPLATE
            if st.session_state.get("scq3_kind", "LSOA") == "LSOA"
            else SCQ3_ADMIN_CYPHER_TEMPLATE
        ).replace(
            "__MAXHOPS__",
            str(scq3_hops),
        )

    if SHOW_QUERIES:
        st.markdown(f"### {t('cypher_used')}")
        st.code(
            active_cypher.strip(),
            language="cypher",
        )
        st.markdown(f"### {t('parameters')}")
        st.json(params)

    # Clicking a region fires a Streamlit rerun, and on a rerun a button
    # reports False again — which used to wipe the answer and send the page
    # back to its empty state. The fact that this question has been run is
    # therefore held in session state: once run, the answer survives reruns
    # and re-executes against whatever parameters are currently selected.
    run_state_key = f"scq_ran_{scq_key}"
    if run_query:
        st.session_state[run_state_key] = True

    if not st.session_state.get(run_state_key):
        return

    try:
        result_df = run_cypher(
            cfg,
            active_cypher,
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
                "SCQ3 implements the paper's definition of between over "
                "<b>LSOA_TOUCHES</b>: a region lies between two others when "
                "it sits on a cycle-free path linking them. The paper sets "
                "no numeric bound, but unbounded enumeration is intractable "
                "here, so the hop bound is applied as a tractability "
                "necessity and reported with the result. Its fit to the "
                "education-policy use case is still weak or optional, "
                "because the paper poses no between question for this "
                "domain."
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

        st.markdown(f"### {t('implemented_answer')}")

        st.markdown(
            (
                "<div class='solutionbox'>"
                f"<b>{t('implemented_answer')}:</b> "
                f"{strong_answers.get(scq_key, meta['keyword_sentence'])}"
                "<br><br>"
                f"<b>{t('eval_status')}:</b> "
                f"{meta.get('evaluation_note', 'See provenance above.')}"
                "<br>"
                f"<b>{t('evidence_h')}:</b> The query returned "
                f"<b>{len(result_df)}</b> result row(s) for the "
                "selected parameter."
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        st.markdown(f"### {t('results_h')}")

        if scq_key == "SCQ3" and result_df.empty:
            st.info(t("no_path_note"))
            example_pairs = scq3_pair_options(cfg)
            if example_pairs:
                st.caption(
                    f"{t('guaranteed_example')} {example_pairs[0][1]}"
                )

        if scq_key == "SCQ8":
            evidence_cypher = (
                meta["cypher_reverse_evidence"]
                if direction == "admin"
                else meta["cypher_evidence"]
            )
            evidence_df = run_cypher(cfg, evidence_cypher, params)

            answer_metric = (
                t("scq8_metric_lsoa")
                if direction == "admin"
                else t("scq8_metric_admin")
            )
            answer_caption = (
                t("scq8_caption_admin")
                if direction == "admin"
                else t("scq8_caption")
            )

            tab_answer, tab_evidence = st.tabs(
                [t("tab_answer"), t("tab_evidence")]
            )

            with tab_answer:
                st.metric(answer_metric, len(result_df))
                st.caption(answer_caption)
                # Which way the question was asked decides which map can
                # draw it: administrative rows need administrative polygons.
                if params.get("admin"):
                    clicked = render_answer_map(
                        cfg, result_df,
                        [params.get("lsoa"), params.get("lsoa_a"),
                         params.get("lsoa_b")],
                        key="map_SCQ8_answer",
                        focus_admin=params.get("admin"),
                        show_gap=True,
                    )
                    if clicked:
                        render_lsoa_school_panel(cfg, clicked)
                else:
                    picked_admin = render_admin_answer_map(
                        cfg, result_df, params.get("lsoa"),
                        key="map_SCQ8_answer",
                    )
                    if picked_admin:
                        render_unit_school_card(cfg, picked_admin)
                display_df(result_df)
                if SHOW_QUERIES:
                    with st.expander(t("show_query")):
                        st.code(active_cypher.strip(), language="cypher")

            with tab_evidence:
                st.metric(t("metric_pairs"), len(evidence_df))
                display_df(evidence_df)
                if SHOW_QUERIES:
                    with st.expander(t("show_query")):
                        st.code(evidence_cypher.strip(), language="cypher")

        else:
            result_label = meta.get(
                "result_label",
                "Result rows returned",
            )

            if scq_key == "SCQ3":
                # The question asks WHICH LSOAs lie between, so the answer is
                # a set of areas, not a count of routes. The same area recurs
                # across many paths, so the path count alone overstates the
                # size of the answer and reads as if the whole neighbourhood
                # were "between" the two endpoints.
                between_codes: List[str] = []
                min_hops_codes: List[str] = []
                if not result_df.empty and "between_lsoas" in result_df.columns:
                    try:
                        min_hops = int(
                            pd.to_numeric(result_df["hops"], errors="coerce").min()
                        )
                    except Exception:
                        min_hops = None
                    for _, prow in result_df.iterrows():
                        codes_here = [
                            str(item.get("code"))
                            for item in (prow.get("between_lsoas") or [])
                            if isinstance(item, dict) and item.get("code")
                        ]
                        between_codes.extend(codes_here)
                        if min_hops is not None and prow.get("hops") == min_hops:
                            min_hops_codes.extend(codes_here)
                distinct_between = sorted(set(between_codes))
                distinct_direct = sorted(set(min_hops_codes))

                m1, m2, m3 = st.columns(3)
                m1.metric(
                    "LSOAs lying between",
                    len(distinct_between),
                    help=(
                        "Distinct areas appearing on at least one cycle-free "
                        "path. This is the answer to the question as posed."
                    ),
                )
                m2.metric(
                    "On a shortest path",
                    len(distinct_direct),
                    help=(
                        "Of those, the areas that lie on the shortest route "
                        "between the two endpoints. The remainder sit on "
                        "longer detours, which is why the drawn region can "
                        "look as though it surrounds the endpoints rather "
                        "than lying between them."
                    ),
                )
                m3.metric(
                    result_label,
                    len(result_df),
                    help=(
                        "Routes, not areas. One area recurs across many "
                        "routes, so this count grows sharply with the hop "
                        "bound while the set of areas does not."
                    ),
                )
                st.caption(
                    "The paper's definition is any cycle-free path, so every "
                    "route is retained. The first figure is the answer; the "
                    "second shows how much of it lies on the direct route."
                )
            else:
                st.metric(
                    result_label,
                    len(result_df),
                )

            _scq3_admin = (
                scq_key == "SCQ3"
                and st.session_state.get("scq3_kind", "LSOA") != "LSOA"
            )
            if _scq3_admin:
                # The answer map colours LSOAs by deprivation, and
                # administrative units carry no WIMD value, so drawing them
                # there would either be blank or invent a figure. The path
                # table is the whole answer at this level.
                st.caption(
                    "Administrative level: the paths are listed below. No "
                    "map is drawn because administrative units carry no "
                    "WIMD value, so there is nothing for the deprivation "
                    "shading to show."
                )
            elif scq_key in ("SCQ5", "SCQ6"):
                # Containment inside the administrative hierarchy nests
                # cleanly, which is exactly the contrast with SCQ7 that the
                # reclassification rests on, so it is worth drawing.
                clicked_unit = render_admin_containment_map(
                    cfg,
                    result_df,
                    params.get("admin"),
                    focus_contains=(scq_key == "SCQ6"),
                    key=f"map_{scq_key}",
                )
                if clicked_unit:
                    render_unit_school_card(cfg, clicked_unit)
            elif scq_key == "SCQ7" and not params.get("admin"):
                picked_admin = render_admin_answer_map(
                    cfg, result_df, params.get("lsoa"),
                    key=f"map_{scq_key}",
                )
                if picked_admin:
                    render_unit_school_card(cfg, picked_admin)
            else:
                clicked = render_answer_map(
                    cfg,
                    result_df,
                    [
                        params.get("lsoa"),
                        params.get("lsoa_a"),
                        params.get("lsoa_b"),
                    ],
                    key=f"map_{scq_key}",
                    focus_admin=params.get("admin"),
                    show_excluded_neighbours=(scq_key == "SCQ4"),
                )
                if clicked:
                    render_lsoa_school_panel(cfg, clicked)
            render_result_reading(result_df, scq_key, cfg)
            display_df(result_df)

        if SCQ_EVIDENCE.get(scq_key):
            st.markdown("---")
            refs = "<br/>".join(TASK3_REFERENCES)
            st.markdown(
                "<div style='font-size:12.5px;opacity:.75;line-height:1.9'>"
                f"<b>References</b><br/>{refs}"
                "</div>",
                unsafe_allow_html=True,
            )

        if scq_key in {"SCQ7", "SCQ8"}:
            st.markdown("---")
            st.markdown("#### The cross-hierarchy seam behind this answer")
            st.caption(
                "SCQ7 and SCQ8 are the only questions that cross from the "
                "administrative hierarchy into the statistical one. "
                "YAGO2geo holds no relation across that boundary, so the "
                "answer above rests on a bridge built here from geometry. "
                "Its size and provenance are shown below — which is why "
                "these two questions are answerable in the demonstrator yet "
                "still count as native failures."
            )
            render_seam_context(cfg)

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
                    f"<b>{t('eval_interp')}:</b> "
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
                    f"<b>{t('eval_interp')}:</b> "
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

@st.cache_data(show_spinner=False)
def load_report_html(path: str) -> str:
    """Read the completeness report once per session.

    The file is ~20 MB, so it is cached and only read when the reader asks
    to see it rather than on every rerun of the page.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def page_evaluation() -> None:
    # Evaluation page rule:
    # keep the native Education Use Case scorecard separate from the
    # administrative comparison and from the broader demonstrator capability.
    # This directly addresses the supervisor note that SCQ5/SCQ6 should be
    # reclassified for Ward-LSOA questions rather than counted as independent
    # education-use-case answers.
    hero()

    task_badge(
        "Evaluation and Coverage",
        (
            "Evaluate native model coverage separately from "
            "geometry-assisted demonstrator coverage using one "
            "consistent eight-SCQ scorecard."
        ),
        "Complete",
    )

    st.markdown(
        (
            "<div class='solutionbox'>"
            "<b>Implemented answer:</b> The education-use-case scorecard "
            "is separated from the administrative-hierarchy comparison. "
            "For the LSOA-based education questions, YAGO2geo provides no "
            "native LSOA↔LSOA or AdminUnit↔LSOA relations. SCQ5 and SCQ6 "
            "are not applicable to the education use case, but they remain "
            "in the fixed eight-question benchmark to maintain a consistent "
            "denominator. Native education <b>CQCov = 0/8 = 0.00</b>. "
            "After geometry-origin and graph-derived augmentation, the "
            "demonstrator answers six of the eight questions, giving an "
            "augmented education <b>CQCov = 6/8 = 0.75</b>. The native or "
            "derivable administrative hierarchy also covers six of the "
            "eight questions, giving an administrative "
            "<b>CQCov = 6/8 = 0.75</b>. The difference between native "
            "education coverage and augmented demonstrator coverage "
            "identifies the cross-hierarchy limitation and the contribution "
            "of geometric augmentation."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # Four coverage cards
    st.markdown(
        """
<style>
.eval-cov-grid {
display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
gap:.7rem; margin:.4rem 0 .2rem 0;
}
@media (max-width:1150px){
.eval-cov-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media (max-width:640px){
.eval-cov-grid{grid-template-columns:1fr;}
}
.eval-cov-card {
position:relative; background:#ffffff; border:1px solid #e5e7eb;
border-radius:12px; padding:1rem .9rem .85rem .9rem; overflow:hidden;
box-shadow:0 3px 10px rgba(15,23,42,.035);
}
.eval-cov-card::before {
content:""; position:absolute; top:0; left:0; right:0; height:4px;
background:linear-gradient(90deg,#9e1b32,#b8283f);
}
.eval-cov-label {
font-size:.78rem; line-height:1.32; font-weight:700; color:#475569;
margin:.15rem 0 .5rem 0; min-height:3.1em;
}
.eval-cov-value {
font-size:1.65rem; font-weight:800; color:#9e1b32; line-height:1.05;
letter-spacing:-.01em;
}
.eval-cov-note {
font-size:.86rem; line-height:1.55; color:#3f4a5a;
background:#fdf2f4; border:1px solid #f3d3da;
border-left:4px solid #9e1b32; border-radius:10px;
padding:.7rem .85rem; margin:.6rem 0 .2rem 0;
}
@media (prefers-color-scheme: dark) {
.eval-cov-card {
background:#181b21; border-color:#2f3540; box-shadow:none;
}
.eval-cov-label {color:#b3bdca;}
.eval-cov-value {color:#f2879c;}
.eval-cov-note {
color:#d3dae4; background:#241a1e; border-color:#4a2b33;
border-left-color:#f2879c;
}
}
</style>

<div class="eval-cov-grid">

<div class="eval-cov-card"
title="All eight SCQs remain in the fixed benchmark. No education question is answered using native YAGO2geo relations.">
<div class="eval-cov-label">
Education — native question coverage (CQCov)
</div>
<div class="eval-cov-value">0 / 8</div>
</div>

<div class="eval-cov-card">
<div class="eval-cov-label">
Education — augmented question coverage (CQCov)
</div>
<div class="eval-cov-value">6 / 8</div>
</div>

<div class="eval-cov-card"
title="Six of the eight SCQs are covered by native or derivable relations in the administrative hierarchy.">
<div class="eval-cov-label">
Administrative — native or derivable question coverage (CQCov)
</div>
<div class="eval-cov-value">6 / 8</div>
</div>

<div class="eval-cov-card">
<div class="eval-cov-label">Native LSOA answers</div>
<div class="eval-cov-value">0</div>
</div>

</div>

<div class="eval-cov-note">
The demonstrator answers six of the eight questions for the education use
case using geometry-origin and graph-derived relations. SCQ5 and SCQ6 are
not applicable to this use case but remain in the fixed eight-question
benchmark. Augmented demonstrator coverage is reported separately from
native YAGO2geo coverage.
</div>
""",
        unsafe_allow_html=True,
    )

    # Competency-question coverage definition
    st.latex(
        r"CQCov(O)=\frac{N_{\mathrm{covered\ SCQs}}}"
        r"{N_{\mathrm{SCQs}}}"
    )

    native_col, augmented_col, administrative_col = st.columns(3)

    with native_col:
        st.metric(
            "Native education CQCov",
            "0 / 8 = 0.00",
        )

    with augmented_col:
        st.metric(
            "Augmented education CQCov",
            "6 / 8 = 0.75",
        )

    with administrative_col:
        st.metric(
            "Administrative CQCov",
            "6 / 8 = 0.75",
        )
        
    st.markdown(
        (
            "<div class='warningbox'>"
            "<b>Core rule:</b> Geometry-origin relations stored in Neo4j "
            "improve the demonstrator's question coverage, but they do not "
            "increase native YAGO2geo coverage."
            "</div>"
        ),
        unsafe_allow_html=True,
    )


    with st.expander(
        "Independent completeness audit of YAGO2geo — summary and full report",
        expanded=False,
    ):
        st.markdown(
            "This audit is run **outside** the demonstrator by a separate "
            "read-only script. It does not ask whether a question can be "
            "answered; it asks whether the relations YAGO2geo claims to hold "
            "are actually present and correct. Adjacency is recomputed from "
            "boundary geometry and compared against what YAGO2geo natively "
            "asserts, for the class pairs listed in the table below \u2014 "
            "not for the model as a whole."
        )
        a1, a2, a3, a4, a5 = st.columns(5)
        a1.metric(
            "Completeness \u2014 Wales",
            "100.00%",
            help=(
                "6,211 matched of 6,211 geometry-definable instances, over "
                "the nine Welsh domain-range rows the report evaluates. "
                "Every Welsh row closes at 100%."
            ),
        )
        a2.metric(
            "Completeness \u2014 UK-wide",
            "99.85%",
            help=(
                "134,747 matched of 134,946 definable, over every row of the "
                "UK-wide table: 199 instances short. The gap sits almost "
                "entirely in Community-to-Ward containment, at 90.44% "
                "(1,513 matched of 1,673); every other containment row is "
                "complete. Restricting the denominator to the four adjacency "
                "and UnitaryAuthority-Ward rows alone gives 84,309 of 84,348, "
                "which is the narrower subtotal this panel used to report."
            ),
        )
        a3.metric(
            "Welsh units with no WITHIN parent",
            "97 / 529",
            help=(
                "78 of 396 Welsh Wards (19.70%) and 19 of 133 Welsh "
                "Communities (14.29%) hold no WITHIN relation to any parent. "
                "A further 159 units do have a parent but skip a level, so "
                "273 of the 529 reach a Unitary Authority by a direct path. "
                "This is a limit of the stored hierarchy, not of geometry."
            ),
        )
        a4.metric(
            "Inexpressible overlaps",
            "12,639",
            help=(
                "Ward-Community pairs that genuinely overlap rather than "
                "touch, UK-wide. The ontology has no overlaps property "
                "between sibling classes, so these real relations cannot be "
                "stated: a limit of expressiveness. The Welsh figure is "
                "1,437."
            ),
        )
        a5.metric(
            "Dual representations",
            "1,131",
            help=(
                "A subset of the 12,639, classified by the report's "
                "name-based heuristic as the same real-world unit stored "
                "twice under two naming schemes. The remainder of that "
                "12,639 is 10,445 genuine partial overlaps and 1,063 "
                "boundary-precision slivers. A limit of identity."
            ),
        )
        st.caption(
            "Wales: 6,211 of 6,211 across nine class pairs, 0 missing and "
            "0 extra. UK-wide: 134,747 of 134,946 across nineteen, 199 "
            "short \u2014 39 in adjacency and 160 in Community-to-Ward "
            "containment. Every shortfall the audit records falls outside "
            "Wales."
        )
        st.markdown(
            "<div class='solutionbox'>"
            "<b>Why this matters for the evaluation:</b> completeness is not "
            "\"the relation type is present\" but \"all the instances that "
            "should exist do exist\". These figures separate three different "
            "kinds of limit — <b>coverage</b> (relations absent), "
            "<b>accuracy</b> (relations present but wrong) and "
            "<b>expressiveness</b> (real relations the ontology cannot "
            "state). Only the first is visible from inside the demonstrator."
            "</div>",
            unsafe_allow_html=True,
        )
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "yago2geo_completeness_cloud.html",
        )
        if os.path.exists(report_path):
            size_mb = os.path.getsize(report_path) / 1e6
            show_report = st.checkbox(
                f"Show the full report inline ({size_mb:.1f} MB)",
                value=False,
                help=(
                    "The report is large, so it loads only when you ask for "
                    "it. It is also downloadable and lives in the repository "
                    "beside the app."
                ),
            )
            if show_report:
                # The page is capped at a comfortable reading width for
                # prose, which is too narrow for the report's tables, so the
                # cap is lifted whenever the report is on screen. This used
                # to be a second checkbox; it was never a decision the reader
                # needed to make, since the wide setting is the only one that
                # renders the tables without a horizontal scrollbar.
                st.markdown(
                    "<style>.block-container{max-width:100% !important;"
                    "padding-left:1.2rem !important;"
                    "padding-right:1.2rem !important;}</style>",
                    unsafe_allow_html=True,
                )
                with st.spinner("Loading the completeness report..."):
                    report_html = load_report_html(report_path)
                components.html(report_html, height=1400, scrolling=True)
                st.download_button(
                    "Download the report",
                    data=report_html,
                    file_name="yago2geo_completeness_cloud.html",
                    mime="text/html",
                )
        else:
            st.markdown(
                "[Open the full report on GitHub]"
                "(https://github.com/effatalkenani/knowledge-graph-education-"
                "inequality/blob/main/wales_edu_project/"
                "yago2geo_completeness_cloud.html)"
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

def render_question_answer(cfg: Dict[str, str]) -> bool:
    """Answer the typed question directly, without the manual panel.

    The panel and the question box used to be one path: the sentence set the
    widgets and the widgets built the query, so an answer could not exist
    unless the panel was open. This function is the separation. It takes the
    intent parked by the parser, chooses an approved template, binds its
    parameters and renders the answer and its map on its own. The panel stays
    what it should be: a way to ask without a sentence.
    """
    intent = st.session_state.get("nl_answer")
    if not intent or not intent.get("kind"):
        return False
    kind = intent["kind"]
    areas = intent.get("areas") or []
    admin = intent.get("admin")

    params: Dict[str, Any] = {"limit": 5000}
    if areas:
        params["lsoa"] = areas[0]
        params["lsoa_a"] = areas[0]
        params["lsoa_b"] = areas[1] if len(areas) > 1 else areas[0]
    if admin:
        params["admin"] = admin

    if kind == "LENS":
        mode = intent.get("mode") or "direct"
        if intent.get("want") == "units" and mode in LENS_UNIT_CYPHER:
            cypher = LENS_UNIT_CYPHER[mode]
        else:
            cypher = LENS_CYPHER.get(mode)
        # Same rule as the panel: near cannot carry a neighbour type. A
        # model-parsed sentence can still propose one, so the guard lives
        # here as well as in the rule parser.
        params["nbr_type"] = None if mode == "near" else intent.get("ntype")
        if mode == "near" and intent.get("ntype"):
            st.caption(
                f"Your sentence named {intent['ntype']} as the kind of unit "
                "to return, but near is defined inside one division "
                "(IJGI 2024, \u00a73.4), so the answer is over units of the "
                "same kind as the one you started from."
            )
        chain = LENS_MODES.get(mode, ("", "", ""))
    else:
        meta = SCQ_META.get(kind)
        if not meta:
            return False
        cypher = meta["cypher"]
        # A cross-hierarchy question naming a unit and no LSOA has to run
        # from the administrative side, exactly as the toggle would set it.
        if kind in ("SCQ7", "SCQ8") and admin and not areas:
            cypher = meta.get("cypher_reverse", cypher)
        chain = ("", meta.get("relation", ""), meta.get("provenance", ""))

    if not cypher:
        return False
    _missing = None
    if "$admin" in cypher and "admin" in params:
        pass
    elif "$lsoa" in cypher and "lsoa" not in params:
        _missing = "an LSOA"
    elif "$admin" in cypher and "admin" not in params:
        _missing = "an administrative unit"
    # The sentence usually names the kind of thing it wants back, and that
    # is a different question from which relation to travel. "LSOAs inside
    # Cardiff" and "communities inside Cardiff" walk the same containment,
    # and differ only in what they return. Honouring the named output stops
    # the reader having to accept whatever the matched form happens to give.
    _lowq = str(intent.get("text") or "").lower()
    _wants_schools = any(w in _lowq for w in _SCHOOL_WORDS)
    _out = None
    if not _wants_schools and admin:
        if any(w in _lowq for w in ("lsoa", "lsoas",
                                    "\u0645\u0646\u0637\u0642\u0629 \u0625\u062d\u0635\u0627\u0626\u064a\u0629")):
            _out = "LSOA"
        elif any(w in _lowq for w in ("communities", "community",
                                      "\u0645\u062c\u062a\u0645\u0639")):
            _out = "Community"
        elif any(w in _lowq for w in ("wards", "ward",
                                      "\u062f\u0648\u0627\u0626\u0631",
                                      "\u062f\u0627\u0626\u0631\u0629")):
            _out = "Ward"

    if _out == "LSOA":
        cypher = """
MATCH (a:AdminUnit {uri:$admin})
MATCH (u:AdminUnit)
WHERE u = a OR (u)-[:WITHIN*1..3]->(a)
MATCH (u)-[:INTERSECTS]->(l:LSOA)
OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)
WITH l, count(DISTINCT s) AS schools,
     round(avg(s.fsm_pct),1) AS avg_fsm_pct,
     round(avg(s.attendance_pct),1) AS avg_attendance_pct
RETURN
    l.code AS lsoa_code,
    coalesce(l.name, l.LSOA_Name, l.code) AS lsoa_name,
    l.deprivation AS deprivation,
    l.wimd_decile AS wimd_decile,
    schools, avg_fsm_pct, avg_attendance_pct
ORDER BY lsoa_code
LIMIT $limit
"""
        chain = ("", "WITHIN downward, then INTERSECTS",
                 "Native, then Geometry-origin")
        _missing = None
    elif _out in ("Community", "Ward"):
        cypher = LENS_UNIT_CYPHER["inside"]
        params["nbr_type"] = _out
        chain = LENS_MODES["inside"]
        _missing = None

    # "Needs an LSOA" was only ever true of the eight forms, not of the
    # graph: TOUCHES and WITHIN between administrative units are stored and
    # audited, and the lens answers near and touches over them. Before
    # refusing, try to resolve the place as an administrative unit. Welsh
    # units are stored bilingually -- Cardiff is "Caerdydd - Cardiff" -- so
    # a plain name misses by a prefix, not by a spelling error.
    if _missing == "an LSOA" and not admin:
        # An Arabic sentence carries no Latin token to match against the
        # graph's English names, but the model's own reading of it does:
        # it writes out "Cathays" even when the reader typed the name in
        # Arabic script. Both sources are searched, so a question asked in
        # either language can still resolve a place.
        _src = str(intent.get("text") or "")
        try:
            _src += " " + " ".join(
                str(s) for s in (st.session_state.get("nl_last") or {}).get("steps", [])
            )
        except Exception:
            pass
        _w = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'\-]{3,}", _src)]
        _w += [
            w.strip(",.?!'\"").lower()
            for w in str(intent.get("text") or "").split()
            if len(w.strip(",.?!'\"")) >= 4
        ]
        _stop = {
            "near", "inside", "which", "what", "schools", "school", "areas",
            "regions", "units", "community", "communities", "ward", "wards",
            "with", "that", "from", "query", "asks", "form", "corresponding",
            "administrative", "attendance", "deprivation", "lsoa", "lsoas",
            "the", "and", "for", "unit", "region", "step", "steps", "maps",
        }
        _w = [w for w in dict.fromkeys(_w) if w not in _stop][:10]
        _cand = None
        if _w:
            try:
                _cand = run_cypher(cfg, """
UNWIND $words AS w
MATCH (a:AdminUnit)
WHERE a.name IS NOT NULL
  AND a.type IN ['Ward','Community','UnitaryAuthority']
  AND EXISTS { MATCH (a)-[:INTERSECTS]->(:LSOA) }
  AND toLower(a.name) CONTAINS w
RETURN DISTINCT a.uri AS uri, a.name AS name, a.type AS type
LIMIT 6
""", {"words": _w})
            except Exception:
                _cand = None
        if _cand is not None and not _cand.empty:
            # Requiring exactly one match was the root of this failure:
            # "Cathays" matches both "Cathays" and "Cathays Community", so
            # the recovery declined and the reader got nothing. Ties are
            # broken deterministically instead -- an exact word match first,
            # then the shortest name -- and the unit chosen is printed above
            # the answer, so the choice is visible rather than silent.
            _tied = len(_cand)
            if len(_cand) > 1:
                _wl = set(_w)
                _cand = _cand.assign(
                    _exact=[
                        0 if str(n).lower() in _wl else 1
                        for n in _cand["name"]
                    ],
                    _len=[len(str(n)) for n in _cand["name"]],
                ).sort_values(["_exact", "_len", "name"])
            admin = _cand.iloc[0]["uri"]
            params["admin"] = admin
            if _tied > 1:
                # A choice made among several matches must be declared. The
                # rule is deterministic, but the reader still has to be told
                # that a rule was applied and what it passed over.
                _others = ", ".join(
                    f"{r['name']} ({r['type']})"
                    for _, r in _cand.iloc[1:6].iterrows()
                )
                st.error(
                    f"**{_tied} units in the graph matched your wording.** "
                    f"The answer below uses "
                    f"**{_cand.iloc[0]['name']} ({_cand.iloc[0]['type']})**, "
                    f"chosen by an exact-word match first and the shorter "
                    f"name second. The others were: {_others}. "
                    f"If you meant one of them, open the panel below and "
                    f"choose it."
                )
            _low = str(intent.get("text") or "").lower()
            _m = "touches"
            for _name, _ph in _LENS_MODE_PHRASES:
                if any(p in _low for p in _ph):
                    _m = _name
                    break
            _units = not any(w in _low for w in _SCHOOL_WORDS)
            cypher = (
                LENS_UNIT_CYPHER.get(_m) if _units else None
            ) or LENS_CYPHER.get(_m) or LENS_CYPHER["touches"]
            params["nbr_type"] = None
            chain = LENS_MODES.get(_m, ("", "", ""))
            _missing = None
            st.caption(
                f"No LSOA was named, but \"{_cand.iloc[0]['name']}\" is an "
                f"administrative unit in the graph, and TOUCHES and WITHIN "
                f"between units are stored. The question was answered over "
                f"the administrative graph instead of the statistical one."
            )

    if _missing:
        # Silence here was the worst behaviour of all: the reader saw a form
        # chosen, a banner claiming the controls were set, and no answer and
        # no reason. Naming the missing piece is the minimum owed.
        st.warning(
            f"The eight spatial forms are anchored on {_missing}, and no "
            f"{_missing} in your sentence could be matched to a name in the "
            "graph. This is a limit of the form, not of the graph: TOUCHES "
            "and WITHIN between administrative units are stored, and the "
            "Education lens answers over them."
        )
        # Telling a reader their name was not found, without showing what the
        # graph does call it, leaves them guessing. Welsh units are stored
        # bilingually -- Cardiff is "Caerdydd - Cardiff" -- so a plain name
        # often misses by a prefix rather than by a spelling error.
        _words = [
            w.strip(",.?!'\"") for w in str(intent.get("text") or "").split()
            if len(w.strip(",.?!'\"")) >= 4
        ][:6]
        if _words:
            try:
                _near = run_cypher(cfg, """
UNWIND $words AS w
MATCH (a:AdminUnit)
WHERE a.name IS NOT NULL
  AND EXISTS { MATCH (a)-[:INTERSECTS]->(:LSOA) }
  AND toLower(a.name) CONTAINS toLower(w)
RETURN DISTINCT a.name AS name, a.type AS type
ORDER BY name
LIMIT 12
""", {"words": _words})
            except Exception:
                _near = None
            if _near is not None and not _near.empty:
                st.caption(
                    "Names in the graph that contain a word from your "
                    "question. Welsh units are stored bilingually, so the "
                    "graph's name is often longer than the one you typed:"
                )
                st.dataframe(_near, use_container_width=True, hide_index=True)
            else:
                st.caption(
                    "No administrative name in the graph contains any word "
                    "from your question. Open the panel below and pick one "
                    "from the list."
                )
        return True

    edu = intent.get("filter")
    _val = intent.get("value")
    params["fsm_min"] = (
        (_val if _val is not None else 30.0) if edu == "High FSM" else None
    )
    params["att_max"] = (
        (_val if _val is not None else 90.0) if edu == "Low attendance" else None
    )
    params["dep"] = "High" if edu == "High deprivation" else None
    params["phase"] = intent.get("phase")

    st.markdown("### Answer to your question")
    # The resolved unit is printed before the answer, not buried in the
    # parse trace. A name matched to the wrong unit produces figures that
    # are entirely correct for a place the reader never asked about, and
    # that is the one failure mode a reader cannot detect from the result.
    if intent.get("admin_label"):
        st.markdown(
            f"**Answered for: {intent['admin_label']}** \u2014 if that is not "
            "the place you meant, the name in your sentence matched a "
            "different unit. Open the panel below and choose the right one."
        )
    if edu and _val is None:
        st.caption(
            f"No number was found in the sentence, so the project default "
            f"was used for {edu.lower()}."
        )
    try:
        df = run_cypher(cfg, cypher, params)
    except Exception as exc:
        st.error(f"The question could not be run: {exc}")
        return True

    if df is None or df.empty:
        st.warning(
            "That question ran but returned nothing. The relation exists; "
            "no row in the graph satisfies it for the place and filter you "
            "named. An empty answer is a result, not a fault."
        )
        # An empty containment answer usually means the unit sits at the
        # bottom of the hierarchy, not that the question was wrong. Saying
        # which is which turns a blank into a finding.
        if admin:
            try:
                _d = run_cypher(cfg, """
MATCH (a:AdminUnit {uri:$admin})
OPTIONAL MATCH (c:AdminUnit)-[:WITHIN]->(a)
OPTIONAL MATCH (a)-[:WITHIN]->(p:AdminUnit)
OPTIONAL MATCH (a)-[:TOUCHES]-(n:AdminUnit)
RETURN coalesce(a.name, a.uri) AS name, a.type AS type,
       count(DISTINCT c) AS children,
       count(DISTINCT p) AS parents,
       count(DISTINCT n) AS neighbours
""", {"admin": admin})
            except Exception:
                _d = None
            if _d is not None and not _d.empty:
                r = _d.iloc[0]
                st.info(
                    f"{r['name']} is a {r['type']}. In this graph it has "
                    f"{int(r['children'])} unit(s) inside it, "
                    f"{int(r['parents'])} unit(s) containing it, and "
                    f"{int(r['neighbours'])} touching it. A Community rarely "
                    "contains anything: the Welsh audit records only 8 "
                    "community-to-ward containments in total. Ask what "
                    "CONTAINS it, what TOUCHES it, or what schools fall "
                    "inside it instead."
                )
        return True

    st.caption(
        f"{len(df):,} row(s). Relation chain: {chain[1] or chain[0]}  "
        f"\u2014  Provenance: {chain[2]}. "
        "Where a chain mixes provenances, the answer was possible because of "
        "relations added by this project and does not raise the coverage of "
        "the original YAGO2geo model."
    )
    # The map harvests LSOA codes, because LSOA polygons are the only
    # boundaries this graph stores. An answer made of administrative units
    # carries no such code, so nothing can be drawn — and saying that is
    # better than an empty space the reader has to interpret.
    import re as _re
    _has_lsoa = any(
        bool(_re.match(r"^W\d{8}$", str(v)))
        for col in df.columns for v in df[col].head(50).tolist()
    )
    _admin_unit_answer = (
        kind == "LENS"
        and intent.get("want") == "units"
        and "unit_uri" in df.columns
    )
    if _admin_unit_answer:
        # A LENS unit answer is already a set of administrative regions.
        # Draw those exact rows.  The old fallback instead queried the
        # selected anchor's LSOAs and therefore showed Cathays' statistical
        # footprint for a question whose answer was its touching Communities.
        picked_admin = render_admin_answer_map(
            cfg, df, None, key="nl_answer_admin_units"
        )
        if picked_admin:
            render_unit_school_card(cfg, picked_admin)
        st.caption(
            "The coloured polygons are the administrative units returned "
            "by the relation above. Hover a polygon for its name and type; "
            "click it for the schools reached through INTERSECTS then "
            "LOCATED_IN."
        )
    elif _has_lsoa:
        try:
            render_answer_map(
                cfg, df,
                focus_code=(areas[0] if areas else None),
                key="nl_answer_map",
                focus_admin=admin,
            )
        except Exception as exc:
            st.caption(f"The map could not be drawn for this answer: {exc}")
        if edu or intent.get("phase"):
            st.caption(
                "The figures in the hover card are for EVERY school in that "
                "LSOA, because the card is computed from the graph rather "
                "than from this answer. The table below is the filtered "
                "answer. Where the two differ, the table is the answer to "
                "your question and the card is the context around it."
            )
    elif admin:
        # An administrative answer carries no LSOA code, so the eight forms
        # cannot be mapped on their own. Rather than alter those queries --
        # their rows are reported figures -- a companion query fetches the
        # LSOAs the answer's units cover, through the computed INTERSECTS.
        # The table stays the answer; the map is a view of where it falls.
        try:
            _areas_df = run_cypher(cfg, """
MATCH (a:AdminUnit {uri:$admin})
MATCH (u:AdminUnit)
WHERE u = a OR (u)-[:WITHIN*1..3]->(a)
MATCH (u)-[:INTERSECTS]->(l:LSOA)
RETURN DISTINCT l.code AS lsoa_code
LIMIT 3000
""", {"admin": admin})
        except Exception:
            _areas_df = None
        if _areas_df is not None and not _areas_df.empty:
            st.caption(
                f"The map shows the {len(_areas_df):,} LSOAs that the units "
                "in this answer cover, drawn through the computed INTERSECTS "
                "relation \u2014 Geometry-origin, not native. Administrative "
                "polygons are stored too (`a.wkt`) and the panel below draws "
                "them directly for SCQ5 and SCQ6; this view shows the "
                "statistical extent instead. The table above is the answer."
            )
            try:
                render_answer_map(
                    cfg, _areas_df, focus_code=None,
                    key="nl_answer_map_admin", focus_admin=admin,
                )
            except Exception as exc:
                st.caption(f"The map could not be drawn: {exc}")
        else:
            st.info(
                "No map for this answer. The units it names reach no LSOA "
                "through any stored relation, so there is no extent to draw."
            )
    else:
        st.info(
            "No map for this answer. The map draws LSOA boundaries, which "
            "are the geometry this project loaded; this answer is a list of "
            "administrative units and carries no LSOA code. Ask the same "
            "question with schools in it, or use the Education lens with "
            "Return set to Schools, and the answer will map."
        )
    # lsoa_codes exists so the map can draw an administrative answer. It is
    # not part of the answer: a reader who asked for communities should see
    # communities, not a column of statistical codes that makes it look as
    # though the question was answered at the wrong level.
    _show = df.drop(columns=["lsoa_codes"]) if "lsoa_codes" in df.columns else df
    st.dataframe(_show, use_container_width=True, hide_index=True)
    return True


def render_seam_context(cfg: Dict[str, str]) -> None:
    """The cross-hierarchy seam: the bridge diagram, its live counts and
    the finding. Shown wherever SCQ7 or SCQ8 is being answered, so the
    question, its verdict and the bridge that carries it sit together."""
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


def page_cross_hierarchy(cfg: Dict[str, str]) -> None:
    hero()

    task_badge(
        "Cross-hierarchy Seam",
        (
            "Evaluate the seam between administrative hierarchy and "
            "statistical hierarchy using INTERSECTS and near relations "
            "between AdminUnit and LSOA."
        ),
        "Complete",
    )

    render_seam_context(cfg)

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


    scq8_query = SCQ8_ANSWER_CYPHER

    # ------------------------------------------------------------------
    # Direction toggle: the stored INTERSECTS relation is symmetric, so
    # both starting points read the same facts. Default = LSOA-first,
    # matching the education use case (deprivation and school data live
    # on LSOAs) and the supervisor's own example question.
    # ------------------------------------------------------------------
    direction = direction_toggle("cross_direction")
    st.caption(t("direction_caption"))

    if direction == "lsoa":
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
                    t("scq7_select_lsoa"),
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
                    t("scq7_metric_admin"),

                    len(df7),
                )

                if df7.empty:
                    st.info(
                        "No directly intersecting administrative units were returned "
                        "for this LSOA."
                    )               
                else:
                    clicked7 = render_answer_map(
                        cfg, df7, selected7[0], key="map_cross_scq7"
                    )
                    if clicked7:
                        render_lsoa_school_panel(cfg, clicked7)
                    display_df(df7)

            else:
                st.warning(
                    "No LSOAs are currently available for SCQ7."
                )

            if SHOW_QUERIES:
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
                    t("scq8_select_lsoa"),
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

                tab_a8, tab_e8 = st.tabs(
                    [t("tab_answer"), t("tab_evidence")]
                )

                with tab_a8:
                    st.metric(
                        t("scq8_metric_admin"),
                        len(df8),
                    )
                    st.caption(t("scq8_caption"))
                    if df8.empty:
                        st.info(t("no_results_8"))
                    else:
                        clicked8 = render_answer_map(
                            cfg, df8, selected8[0], key="map_cross_scq8"
                        )
                        if clicked8:
                            render_lsoa_school_panel(cfg, clicked8)
                        display_df(df8)
                    if SHOW_QUERIES:
                        with st.expander(t("show_query")):
                            st.code(
                                scq8_query.strip(),
                                language="cypher",
                            )

                with tab_e8:
                    df8_pairs = run_cypher(
                        cfg,
                        SCQ8_EVIDENCE_CYPHER,
                        {
                            "lsoa": selected8[0],
                            "limit": 30,
                        },
                    )
                    st.metric(
                        t("metric_pairs"),
                        len(df8_pairs),
                    )
                    if df8_pairs.empty:
                        st.info(t("no_results_8"))
                    else:
                        display_df(df8_pairs)
                    if SHOW_QUERIES:
                        with st.expander(t("show_query")):
                            st.code(
                                SCQ8_EVIDENCE_CYPHER.strip(),
                                language="cypher",
                            )

            else:
                st.warning(
                    "No LSOAs are currently available for SCQ8."
                )

    else:
        admin_units = admin_options(cfg, "admin_intersects")

        if not admin_units:
            st.warning(
                "No wards or communities with stored INTERSECTS "
                "relations were found in Neo4j."
            )
        else:
            # Default documented example: Cathays (Community), if present.
            default_admin = next(
                (
                    index
                    for index, option in enumerate(admin_units)
                    if "Cathays" in option[1]
                ),
                0,
            )

            ca7, ca8 = st.columns(2)

            # ----------------------------------------------------------
            # SCQ7 (reversed): Ward/Community -> intersecting LSOAs
            # ----------------------------------------------------------
            with ca7:
                st.subheader(
                    "6.2 SCQ7 \u2014 Cross-hierarchy intersects"
                )

                selected_a7 = st.selectbox(
                    t("scq7_select_admin"),
                    admin_units,
                    index=default_admin,
                    format_func=lambda option: option[1],
                    key="cross7_admin",
                )

                df7r = run_cypher(
                    cfg,
                    SCQ7_REVERSE_CYPHER,
                    {
                        "admin": selected_a7[0],
                        "limit": 30,
                    },
                )

                st.metric(
                    t("scq7_metric_lsoa"),
                    len(df7r),
                )

                if df7r.empty:
                    st.info(t("no_results_7"))
                else:
                    display_df(df7r)

                if SHOW_QUERIES:
                    with st.expander(
                        "Show SCQ7 Cypher query (reversed direction)"
                    ):
                        st.code(
                            SCQ7_REVERSE_CYPHER.strip(),
                            language="cypher",
                        )

            # ----------------------------------------------------------
            # SCQ8 (reversed): Ward/Community -> nearby LSOAs (disjoint)
            # ----------------------------------------------------------
            with ca8:
                st.subheader(
                    "6.3 SCQ8 \u2014 Cross-hierarchy near"
                )

                selected_a8 = st.selectbox(
                    t("scq8_select_admin"),
                    admin_units,
                    index=default_admin,
                    format_func=lambda option: option[1],
                    key="cross8_admin",
                )

                df8r = run_cypher(
                    cfg,
                    SCQ8_REVERSE_CYPHER,
                    {
                        "admin": selected_a8[0],
                        "limit": 30,
                    },
                )

                tab_ra8, tab_re8 = st.tabs(
                    [t("tab_answer"), t("tab_evidence")]
                )

                with tab_ra8:
                    st.metric(
                        t("scq8_metric_lsoa"),
                        len(df8r),
                    )
                    st.caption(t("scq8_caption_admin"))
                    if df8r.empty:
                        st.info(t("no_results_8"))
                    else:
                        display_df(df8r)
                    if SHOW_QUERIES:
                        with st.expander(t("show_query")):
                            st.code(
                                SCQ8_REVERSE_CYPHER.strip(),
                                language="cypher",
                            )

                with tab_re8:
                    df8r_pairs = run_cypher(
                        cfg,
                        SCQ8_REVERSE_EVIDENCE_CYPHER,
                        {
                            "admin": selected_a8[0],
                            "limit": 30,
                        },
                    )
                    st.metric(
                        t("metric_pairs"),
                        len(df8r_pairs),
                    )
                    if df8r_pairs.empty:
                        st.info(t("no_results_8"))
                    else:
                        display_df(df8r_pairs)
                    if SHOW_QUERIES:
                        with st.expander(t("show_query")):
                            st.code(
                                SCQ8_REVERSE_EVIDENCE_CYPHER.strip(),
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

# ---------------------------------------------------------------------------
# Map Explorer: a second engine, for school properties rather than relations
# ---------------------------------------------------------------------------
# Kept apart from the spatial engine on purpose. The demonstrator measures
# eight relation definitions and the scorecard depends on those definitions
# staying exact; property questions are exploration over the same graph and
# must not be able to move a measured answer.

MAP_NL_RULES: List[Tuple[str, List[str]]] = [
    ("dep_high", ["most deprived", "highly deprived", "high deprivation",
                  "high-deprivation", "deprived areas", "amddifadedd uchel"]),
    ("dep_low", ["least deprived", "low deprivation", "low-deprivation",
                 "affluent", "amddifadedd isel"]),
    ("dep_medium", ["medium deprivation", "medium-deprivation"]),
    ("primary", ["primary", "cynradd"]),
    ("secondary", ["secondary", "high school", "uwchradd"]),
    ("special", ["special school", "special schools"]),
    ("welsh_medium", ["welsh medium", "welsh-medium", "cyfrwng cymraeg"]),
    ("english_medium", ["english medium", "english-medium"]),
    ("transport_near", ["near transport", "close to transport",
                        "within 800", "has a transport stop",
                        "agos at drafnidiaeth"]),
    ("transport_far", ["no transport", "far from transport",
                       "without a transport stop"]),
]

_ADMIN_TYPE_WORDS = {
    "community ward": "CommunityWard",
    "civil parish or community": "CivilParishorCommunity",
    "civil parish": "CivilParishorCommunity",
    "european region": "EuropeanRegion",
    "community": "Community", "cymuned": "Community",
    "ward": "Ward", "electoral ward": "Ward",
    "unitary authority": "UnitaryAuthority", "county": "UnitaryAuthority",
    "local authority": "UnitaryAuthority",
}

_MAP_ADMIN_TYPES = {
    "Community", "Ward", "CommunityWard", "CivilParishorCommunity",
    "UnitaryAuthority", "EuropeanRegion",
}

# Possible topological relations in the dissertation's class-pair table.
# This governs semantic validity; it does not claim that YAGO2geo stores the
# relation. Provenance is decided separately (Native, Geometry-origin or
# Query-derived). Ward is the application's normalised COMMUNITYWARD label.
_PAIR_RELATIONS = {
    ("UnitaryAuthority", "UnitaryAuthority"): {"disjoint", "touches"},
    ("Community", "Community"): {"disjoint", "touches"},
    ("CommunityWard", "CommunityWard"): {"disjoint", "touches"},
    ("CivilParishorCommunity", "CivilParishorCommunity"): {"disjoint", "touches"},
    ("Community", "CommunityWard"): {"disjoint", "touches", "within", "contains"},
    ("Community", "UnitaryAuthority"): {"disjoint", "within", "contains"},
    ("CommunityWard", "UnitaryAuthority"): {"disjoint", "within", "contains"},
    ("CivilParishorCommunity", "UnitaryAuthority"): {"disjoint", "touches", "within", "contains"},
    ("CommunityWard", "CivilParishorCommunity"): {"disjoint", "within", "contains"},
    ("UnitaryAuthority", "EuropeanRegion"): {"disjoint", "within", "contains"},
    ("Community", "EuropeanRegion"): {"disjoint", "within", "contains"},
    ("CommunityWard", "EuropeanRegion"): {"disjoint", "within", "contains"},
    ("CivilParishorCommunity", "EuropeanRegion"): {"disjoint", "within", "contains"},
    ("LSOA", "LSOA"): {"disjoint", "touches"},
    ("LSOA", "UnitaryAuthority"): {"disjoint", "within", "contains"},
    ("LSOA", "CommunityWard"): {"disjoint", "intersects"},
    ("LSOA", "Community"): {"disjoint", "intersects"},
    ("LSOA", "CivilParishorCommunity"): {"disjoint", "intersects"},
}


def _eval_class(unit_type: str) -> str:
    return "CommunityWard" if unit_type == "Ward" else unit_type


def _possible_pair_relations(domain: str, range_: str) -> set[str]:
    d, r = _eval_class(domain), _eval_class(range_)
    return set(
        _PAIR_RELATIONS.get((d, r), _PAIR_RELATIONS.get((r, d), set()))
    )


def _map_requested_result(text: str) -> Tuple[str, str | None]:
    """Return the geography explicitly requested before the relation word."""
    low = (text or "").lower()
    prefix = re.split(
        r"\b(?:does\s+not|do\s+not|not)?\s*(?:touch(?:es|ing)?|"
        r"intersect(?:s|ing)?|inside|within|contains?|near)\b",
        low,
        maxsplit=1,
    )[0]
    if re.search(r"\blsoas?\b|lower layer super output areas?", prefix):
        return "LSOA", "LSOA"
    # Longer labels first so "community ward" is not read as Community.
    for phrase, utype in sorted(
        _ADMIN_TYPE_WORDS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        plural = phrase + "s" if not phrase.endswith("y") else phrase[:-1] + "ies"
        if re.search(rf"\b(?:{re.escape(phrase)}|{re.escape(plural)})\b", prefix):
            return "AdminUnit", utype
    return "Schools", None


def _map_explicit_relation(text: str) -> str:
    """Read relation words in precedence order; negation always wins."""
    low = (text or "").lower()
    if re.search(
        r"\b(?:not|does\s+not|do\s+not)\s+(?:touch|touches|border)\b|"
        r"\b(?:non[- ]adjacent|not\s+adjacent)\b", low
    ):
        return "not_touches"
    if re.search(r"\b(?:intersect|intersects|intersecting)\b", low):
        return "intersects"
    if re.search(r"\b(?:contains?|containing|parent\s+of)\b", low):
        return "contains"
    if re.search(r"\b(?:inside|within|contained\s+in)\b", low):
        return "inside"
    if (
        re.search(r"\b(?:graph[- ]?near|two\s+hops?|2\s+hops?)\b", low)
        or re.search(
            r"\b(?:wards?|communities|unitary\s+authorities|lsoas?)\s+near\b",
            low,
        )
    ):
        return "graph_near"
    if re.search(
        r"\b(?:touch|touches|touching|adjacent|neighbouring|neighboring)\b",
        low,
    ):
        return "touches"
    return "direct"


def _map_admin_hint(text: str) -> Dict[str, str] | None:
    """Read only explicit administrative wording in the offline parser."""
    low = (text or "").lower()
    unit_type = next(
        (v for k, v in sorted(
            _ADMIN_TYPE_WORDS.items(), key=lambda item: len(item[0]), reverse=True
        ) if k in low),
        None,
    )
    if not unit_type:
        return None
    relation = _map_explicit_relation(text)
    result_kind, requested_type = _map_requested_result(text)
    # Accept the common natural forms "in/near X community/ward". Resolution
    # against Neo4j below is authoritative; this is merely a candidate name.
    words = "|".join(re.escape(k) for k, v in _ADMIN_TYPE_WORDS.items() if v == unit_type)
    match = re.search(
        rf"(?:in|inside|within|near|around|touching|touch|touches|"
        rf"intersect|intersects|contains|not\s+touch|does\s+not\s+touch)"
        rf"\s+(.+?)\s+(?:{words})(?:\b|$)",
        text, re.IGNORECASE,
    )
    if not match:
        return {"anchor_name": "", "anchor_type": unit_type,
                "relation": relation,
                "target_type": requested_type or unit_type,
                "result_kind": result_kind,
                "spatial_only": result_kind != "Schools"}
    name = re.sub(r"^(?:the)\s+", "", match.group(1).strip(), flags=re.I)
    return {"anchor_name": name, "anchor_type": unit_type,
            "relation": relation,
            "target_type": requested_type or unit_type,
            "result_kind": result_kind,
            "spatial_only": result_kind != "Schools"}


def resolve_map_admin_scope(
    cfg: Dict[str, str], scope: Dict[str, str] | None
) -> Tuple[Dict[str, Any] | None, List[str]]:
    """Resolve one admin anchor and its target units through the LSOA bridge.

    TOUCHES selects adjacent administrative units. GRAPH_NEAR selects units
    at exactly two TOUCHES steps and excludes the anchor and its direct
    neighbours. All LSOAs intersecting the selected target units remain
    candidates; school-point containment performs the final disambiguation.
    """
    if not scope:
        return None, []
    name = str(scope.get("anchor_name") or "").strip()
    unit_type = str(scope.get("anchor_type") or "")
    relation = str(scope.get("relation") or "direct")
    target_type = str(scope.get("target_type") or unit_type)
    result_kind = str(scope.get("result_kind") or "Schools")
    spatial_only = bool(scope.get("spatial_only"))
    if not name or unit_type not in _MAP_ADMIN_TYPES:
        return None, ["Name the administrative unit as well as its type."]
    if target_type not in _MAP_ADMIN_TYPES and target_type != "LSOA":
        target_type = unit_type
    valid_relations = {
        "direct", "intersects", "touches", "not_touches", "graph_near",
        "inside", "contains",
    }
    if relation not in valid_relations:
        return None, [f"The relation {relation} is not supported by the map."]

    # Domain/range validation.  TOUCHES is defined within one geography;
    # AdminUnit--LSOA uses the geometry-origin INTERSECTS bridge instead.
    if result_kind == "LSOA" and relation in {
        "touches", "not_touches", "inside", "contains"
    }:
        return None, [
            f"{relation.replace('_', ' ').upper()} is not represented between "
            f"LSOA and {unit_type}. The available cross-geography relation "
            "is INTERSECTS; GRAPH_NEAR is available through INTERSECTS then "
            "LSOA GRAPH_NEAR. The question was not converted to TOUCHES."
        ]
    if result_kind == "LSOA" and relation == "direct":
        relation = "intersects"
    if result_kind == "AdminUnit" and relation == "intersects":
        return None, [
            "Administrative-to-administrative INTERSECTS is not stored in "
            "this graph. Use TOUCHES for adjacency or WITHIN/CONTAINS for "
            "the native hierarchy."
        ]

    domain_type = "LSOA" if result_kind == "LSOA" else target_type
    possible = _possible_pair_relations(domain_type, unit_type)
    table_relation = {
        "not_touches": "disjoint",
        "inside": "within",
    }.get(relation, relation)
    # NEAR is a graph-derived competency relation rather than a row in the
    # topological completeness table. It is valid only where same-level
    # TOUCHES supplies its two-hop graph.
    if relation == "graph_near":
        compatible = (
            _eval_class(domain_type) == _eval_class(unit_type)
            and "touches" in possible
        ) or result_kind == "LSOA"
    else:
        compatible = table_relation in possible
    if spatial_only and not compatible:
        available = ", ".join(sorted(possible)) or "none"
        return None, [
            f"{relation.replace('_', ' ').upper()} is not a possible "
            f"relationship for {domain_type} → {unit_type} in the "
            f"evaluated class-pair model. Available: {available}. The app "
            "did not replace it with another relationship."
        ]

    anchors = run_cypher(cfg, """
    MATCH (a:AdminUnit)
    WHERE a.type = $anchor_type
      AND toLower(coalesce(a.name, '')) = toLower($anchor_name)
    RETURN a.uri AS uri, a.name AS name, a.type AS unit_type, a.wkt AS wkt
    ORDER BY a.uri
    LIMIT 3
    """, {"anchor_type": unit_type, "anchor_name": name})
    if anchors.empty:
        alternatives = run_cypher(cfg, """
        MATCH (a:AdminUnit)
        WHERE toLower(coalesce(a.name, '')) = toLower($anchor_name)
          AND a.type IN $admin_types
        RETURN DISTINCT a.type AS unit_type ORDER BY unit_type
        """, {"anchor_name": name, "admin_types": sorted(_MAP_ADMIN_TYPES)})
        found = alternatives.get("unit_type", pd.Series(dtype=str)).dropna().astype(str).tolist()
        suffix = (
            " It exists as " + " / ".join(found) + "; the requested type "
            "was not changed automatically."
            if found else ""
        )
        return None, [
            f"No exact {unit_type} named {name} was found in the Welsh graph.{suffix}"
        ]
    if len(anchors) != 1:
        return None, [f"{name} is ambiguous for type {unit_type}; use a more specific name."]
    anchor_uri = str(anchors.iloc[0]["uri"])

    if relation in {"direct", "intersects"}:
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, a.uri AS unit_uri,
          a.name AS unit_name, a.type AS unit_type, a.wkt AS unit_wkt
        """
    elif relation == "touches":
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})-[:TOUCHES]-(u:AdminUnit)
        WHERE u.type = $target_type
        MATCH (u)-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, u.uri AS unit_uri,
          u.name AS unit_name, u.type AS unit_type, u.wkt AS unit_wkt
        """
    elif relation == "not_touches":
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})
        MATCH (u:AdminUnit)
        WHERE u.type = $target_type AND u <> a
          AND NOT (a)-[:TOUCHES]-(u)
          AND (
            EXISTS { MATCH (u)-[:INTERSECTS]->(:LSOA) }
            OR EXISTS {
              MATCH (u)-[:WITHIN*1..3]->(p:AdminUnit)-[:INTERSECTS]->(:LSOA)
            }
            OR EXISTS {
              MATCH (c:AdminUnit)-[:WITHIN*1..3]->(u)
              WHERE EXISTS { MATCH (c)-[:INTERSECTS]->(:LSOA) }
            }
          )
        OPTIONAL MATCH (u)-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, u.uri AS unit_uri,
          u.name AS unit_name, u.type AS unit_type, u.wkt AS unit_wkt
        """
    elif relation == "inside":
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})
        MATCH (u:AdminUnit)-[:WITHIN]->(a)
        WHERE u.type = $target_type
        OPTIONAL MATCH (u)-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, u.uri AS unit_uri,
          u.name AS unit_name, u.type AS unit_type, u.wkt AS unit_wkt
        """
    elif relation == "contains":
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})-[:WITHIN]->(u:AdminUnit)
        WHERE u.type = $target_type
        OPTIONAL MATCH (u)-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, u.uri AS unit_uri,
          u.name AS unit_name, u.type AS unit_type, u.wkt AS unit_wkt
        """
    elif result_kind == "LSOA":
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})-[:INTERSECTS]->(base:LSOA)
        MATCH (base)-[:GRAPH_NEAR]-(l:LSOA)
        WHERE NOT (a)-[:INTERSECTS]->(l)
        RETURN DISTINCT l.code AS lsoa_code, null AS unit_uri,
          null AS unit_name, 'LSOA' AS unit_type, null AS unit_wkt
        """
    else:
        path = """
        MATCH (a:AdminUnit {uri:$anchor_uri})-[:TOUCHES]-(m:AdminUnit)-[:TOUCHES]-(u:AdminUnit)
        WHERE m.type = $target_type AND u.type = $target_type
          AND u <> a AND NOT (a)-[:TOUCHES]-(u)
        MATCH (u)-[:INTERSECTS]->(l:LSOA)
        RETURN DISTINCT l.code AS lsoa_code, u.uri AS unit_uri,
          u.name AS unit_name, u.type AS unit_type, u.wkt AS unit_wkt
        """
    rows = run_cypher(cfg, path, {"anchor_uri": anchor_uri,
                                  "target_type": target_type})
    if rows.empty or (
        result_kind == "LSOA"
        and rows.get("lsoa_code", pd.Series(dtype=str)).dropna().empty
    ) or (
        result_kind == "AdminUnit"
        and rows.get("unit_uri", pd.Series(dtype=str)).dropna().empty
    ):
        return None, [
            f"No {relation.replace('_', ' ').upper()} relationship was found "
            f"from {name} ({unit_type}) to {target_type}. The graph was "
            "queried without substituting another relation."
        ]
    result = {
        "anchor": anchors.iloc[0].to_dict(), "relation": relation,
        "target_type": target_type,
        "result_kind": result_kind,
        "spatial_only": spatial_only,
        "provenance": {
            "touches": "Native YAGO2geo",
            "inside": "Native YAGO2geo WITHIN",
            "contains": "Inverse reading of Native YAGO2geo WITHIN",
            "not_touches": "Query-derived DISJOINT complement",
            "intersects": "Geometry-origin",
            "graph_near": "Graph-derived",
            "direct": "Geometry-origin INTERSECTS bridge",
        }.get(relation, "Represented graph relation"),
        "disjointness_applied": False,
        "lsoa_codes": sorted(set(rows.get("lsoa_code", pd.Series(dtype=str)).dropna().astype(str))),
        "units": rows,
    }
    return result, []


def resolve_map_admin_scopes(
    cfg: Dict[str, str], scopes: List[Dict[str, str]], operator: str = "AND"
) -> Tuple[Dict[str, Any] | None, List[str]]:
    """Resolve and combine one or more fixed administrative graph scopes."""
    clean_scopes = [s for s in scopes if isinstance(s, dict)]
    if not clean_scopes:
        return None, []
    resolved_components: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for scope in clean_scopes:
        resolved, component_warnings = resolve_map_admin_scope(cfg, scope)
        warnings.extend(component_warnings)
        if resolved is None:
            return None, warnings
        resolved_components.append(resolved)

    if len(resolved_components) == 1:
        return resolved_components[0], warnings

    logical_operator = operator if operator in {"AND", "OR"} else "AND"
    code_sets = [set(c.get("lsoa_codes", [])) for c in resolved_components]
    combined_codes = (
        set.intersection(*code_sets)
        if logical_operator == "AND"
        else set.union(*code_sets)
    )
    unit_frames = [
        c.get("units") for c in resolved_components
        if isinstance(c.get("units"), pd.DataFrame)
    ]
    return {
        "compound": True,
        "components": resolved_components,
        "operator": logical_operator,
        "relation": "compound",
        "lsoa_codes": sorted(combined_codes),
        "units": (
            pd.concat(unit_frames, ignore_index=True).drop_duplicates()
            if unit_frames else pd.DataFrame()
        ),
        "disjointness_applied": False,
    }, warnings


def _admin_component_target_wkts(component: Dict[str, Any]) -> List[str]:
    """Administrative geometries whose school points define one scope."""
    if component.get("relation") == "direct":
        value = str(component.get("anchor", {}).get("wkt") or "")
        return [value] if value else []
    units = component.get("units", pd.DataFrame())
    if not isinstance(units, pd.DataFrame) or units.empty:
        return []
    return (
        units.get("unit_wkt", pd.Series(dtype=str))
        .dropna().astype(str).drop_duplicates().tolist()
    )

_MAP_RANGE = re.compile(
    r"(fsm|free school meal|attendance|capped\s*9|capped9|performance|"
    r"budget|pupils?)[^0-9]{0,24}(between\s*)?(\d+(?:\.\d+)?)"
    r"\s*(?:%|)\s*(?:and|to|-|\u2013)\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_MAP_CMP = re.compile(
    r"(fsm|free school meal|attendance|capped\s*9|capped9|performance|"
    r"budget|pupils?)[^0-9]{0,24}(above|over|greater than|more than|>|"
    r"below|under|less than|fewer than|<)\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_MAP_FIELD = {
    "fsm": "s.fsm_pct", "free school meal": "s.fsm_pct",
    "attendance": "s.attendance_pct",
    "capped 9": "s.capped9_score", "capped9": "s.capped9_score",
    "performance": "s.capped9_score",
    "budget": "s.budget_per_pupil_gbp",
    "pupil": "coalesce(s.pupils_2025, s.pupils)",
    "pupils": "coalesce(s.pupils_2025, s.pupils)",
}


def parse_map_question(text: str) -> Dict[str, Any]:
    """Turn a school-property question into extra Cypher conditions.

    Every condition is parameterised. Nothing from the sentence is ever
    concatenated into the query text, so a question cannot become an
    injection.
    """
    raw = (text or "").strip()
    low = raw.lower()
    out: Dict[str, Any] = {
        "text": raw, "conditions": [], "params": {},
        "chips": [], "unmatched": [], "parser": "rule-based",
        "admin_scope": _map_admin_hint(raw),
        "spatial_relation_failed": False,
    }
    if not raw:
        return out

    # A same-level LSOA request with no named administrative anchor is still
    # validated against the class-pair table. This prevents phrases such as
    # "LSOA inside LSOA" from falling through to an all-schools map.
    if len(re.findall(r"\blsoas?\b", low)) >= 2:
        relation = _map_explicit_relation(raw)
        table_relation = {
            "not_touches": "disjoint", "inside": "within"
        }.get(relation, relation)
        possible = _possible_pair_relations("LSOA", "LSOA")
        if table_relation not in possible and relation != "graph_near":
            out["spatial_relation_failed"] = True
            out["unmatched"].append(
                f"{relation.replace('_', ' ').upper()} is not possible for "
                "LSOA → LSOA. Available topological relations are "
                "DISJOINT and TOUCHES; GRAPH_NEAR is additionally derived "
                "from two LSOA_TOUCHES steps."
            )
            return out

    hits = {name for name, phrases in MAP_NL_RULES
            if any(p in low for p in phrases)}

    dep = next(
        (d for d in ("dep_high", "dep_medium", "dep_low") if d in hits), None
    )
    if dep:
        level = dep.split("_")[1] + "_deprivation"
        out["conditions"].append(
            "coalesce(l.deprivation, s.deprivation) = $nl_dep"
        )
        out["params"]["nl_dep"] = level
        out["chips"].append(f"deprivation = {level.split('_')[0]}")

    phases = [p for p in ("primary", "secondary", "special") if p in hits]
    if phases:
        out["conditions"].append(
            "ANY(p IN $nl_phases WHERE "
            "toLower(coalesce(s.phase_group, s.phase, s.school_type)) "
            "CONTAINS p)"
        )
        out["params"]["nl_phases"] = phases
        out["chips"].append("phase = " + " / ".join(phases))

    if "welsh_medium" in hits or "english_medium" in hits:
        want = "welsh" if "welsh_medium" in hits else "english"
        out["conditions"].append(
            "toLower(coalesce(s.language_medium, '')) CONTAINS $nl_medium"
        )
        out["params"]["nl_medium"] = want
        out["chips"].append(f"language medium = {want}")

    if "transport_near" in hits:
        out["conditions"].append(
            "EXISTS { MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) }"
        )
        out["chips"].append("transport stop within 800m")
    elif "transport_far" in hits:
        out["conditions"].append(
            "NOT EXISTS { MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) }"
        )
        out["chips"].append("no transport stop within 800m")

    used = 0
    for match in _MAP_RANGE.finditer(low):
        field = _MAP_FIELD.get(match.group(1).strip().replace("  ", " "))
        if not field:
            continue
        lo, hi = float(match.group(3)), float(match.group(4))
        lo, hi = min(lo, hi), max(lo, hi)
        a, b = f"nl_lo{used}", f"nl_hi{used}"
        out["conditions"].append(f"{field} >= ${a} AND {field} <= ${b}")
        out["params"][a], out["params"][b] = lo, hi
        out["chips"].append(f"{match.group(1)} between {lo:g} and {hi:g}")
        used += 1

    for match in _MAP_CMP.finditer(low):
        field = _MAP_FIELD.get(match.group(1).strip().replace("  ", " "))
        if not field:
            continue
        op = ">=" if match.group(2) in {
            "above", "over", "greater than", "more than", ">"
        } else "<="
        name = f"nl_cmp{used}"
        out["conditions"].append(f"{field} {op} ${name}")
        out["params"][name] = float(match.group(3))
        out["chips"].append(f"{match.group(1)} {op} {match.group(3)}")
        used += 1

    if not out["conditions"] and not out.get("admin_scope"):
        out["unmatched"].append(
            "Nothing was recognised. Try naming a deprivation level, a "
            "phase, a language medium, transport access, or a metric range "
            "such as \u201cFSM between 20 and 40\u201d."
        )
    return out


# The map answers a different kind of question from the demonstrator: not
# which regions stand in a spatial relation, but which schools satisfy a
# description. Grouping by the property being described keeps that distinction
# visible, and mirrors the eight groups on the demonstrator without pretending
# the two libraries are interchangeable.
MAP_QUESTION_LIBRARY: Dict[str, Dict[str, Any]] = {
    "Deprivation": {
        "colour": "ql-scq1",
        "note": "The deprivation level of the LSOA each school sits in.",
        "questions": [
            "Which schools are in high-deprivation LSOAs?",
            "Which schools are in medium-deprivation LSOAs?",
            "Which schools are in low-deprivation LSOAs?",
            "Secondary schools in high-deprivation areas",
        ],
    },
    "School type": {
        "colour": "ql-scq5",
        "note": "Phase, language medium and other school characteristics.",
        "questions": [
            "Which primary schools are in high-deprivation areas?",
            "Which secondary schools are in low-deprivation areas?",
            "Which special schools are in high-deprivation areas?",
            "Welsh medium schools in low-deprivation areas",
            "English medium primary schools with FSM above 30",
        ],
    },
    "Free school meals": {
        "colour": "ql-scq7",
        "note": "FSM is the deprivation proxy used throughout the study.",
        "questions": [
            "Which schools have FSM between 30 and 60?",
            "Which schools have FSM above 40?",
            "Which schools have FSM below 10?",
            "Primary schools with FSM between 20 and 35",
        ],
    },
    "Attendance": {
        "colour": "ql-scq2",
        "note": "90% is the official persistent-absence line in Wales.",
        "questions": [
            "Which schools have attendance between 85 and 90?",
            "Which schools have attendance below 90?",
            "Which schools have attendance above 95?",
            "Secondary schools with attendance below 92",
        ],
    },
    "Performance": {
        "colour": "ql-scq6",
        "note": (
            "Capped 9 is recorded for secondary schools only, so these "
            "questions return a subset of 204 schools."
        ),
        "questions": [
            "Which secondary schools have Capped 9 between 300 and 380?",
            "Which secondary schools have Capped 9 above 380?",
            "Which secondary schools have Capped 9 below 320?",
        ],
    },
    "Transport": {
        "colour": "ql-scq3",
        "note": (
            "A metric threshold of 800m, and a third notion of proximity "
            "kept outside the completeness scoring."
        ),
        "questions": [
            "Which schools have a transport stop within 800m?",
            "Which schools have no transport stop within 800m?",
            "High-deprivation schools with no transport stop within 800m",
        ],
    },
}


def llm_parse_map_question(text: str) -> Dict[str, Any]:
    """Model reading of a school-property question, rebuilt locally.

    The model is asked only to name properties and numbers. Every condition
    is then constructed here from a fixed field map and bound as a parameter,
    so nothing the model writes reaches the query text. A model that invents
    a field simply produces no condition.
    """
    used = st.session_state.get("nl_llm_calls", 0)
    if used >= NL_LLM_CALL_CAP:
        out = parse_map_question(text)
        out["parser"] = "rule-based (LLM call cap reached)"
        return out
    try:
        from openai import OpenAI

        client = OpenAI(api_key=_nl_llm_key(), base_url=_nl_llm_base_url())
        system = (
            "You read a question about schools in Wales and return JSON "
            "only, no prose and no code fence. Fields, all optional:\n"
            '"deprivation": "high" | "medium" | "low"\n'
            '"phases": subset of ["primary","secondary","special"]\n'
            '"medium": "welsh" | "english"\n'
            '"authority": local authority or town name, e.g. "Cardiff"\n'
            '"anchor_name": exact administrative place name\n'
            '"anchor_type": "Community" | "Ward" | "CommunityWard" | '
            '"CivilParishorCommunity" | "UnitaryAuthority" | '
            '"EuropeanRegion"\n'
            '"relation": "direct" | "touches" | "not_touches" | '
            '"graph_near" | "intersects" | "inside" | "contains"\n'
            '"result_kind": "Schools" | "LSOA" | "AdminUnit"\n'
            '"target_type": one of the same administrative types or "LSOA"\n'
            '"admin_scopes": [{"anchor_name": place, "anchor_type": type, '
            '"relation": relation, "target_type": type}]\n'
            '"admin_operator": "AND" | "OR"\n'
            '"transport": "near" | "far"\n'
            '"ranges": [{"field": f, "min": n, "max": n}]\n'
            '"comparisons": [{"field": f, "op": ">=" or "<=", "value": n}]\n'
            'where f is one of "fsm", "attendance", "capped9", "budget", '
            '"pupils". Use nothing outside these values. Questions may be '
            'in any language; translate place names to their English form. '
            'Use authority only for an ordinary local-authority filter. If '
            'the user explicitly says community, ward, county or unitary '
            'authority, use the four administrative fields instead. direct '
            'means its intersecting LSOAs; touches means adjacent units; '
            'graph_near means units exactly two TOUCHES steps away. Schools '
            'are never directly assigned to an administrative unit: the '
            'application always crosses through AdminUnit INTERSECTS LSOA '
            'and School LOCATED_IN LSOA. For explicit administrative wording, '
            'near means graph_near (exactly two TOUCHES steps), while touch '
            'or touching means touches (one step). For one administrative '
            'condition, return both the legacy four fields and a one-item '
            'admin_scopes list. For compound administrative wording, return '
            'every condition in admin_scopes and preserve the explicit '
            'logical connector in admin_operator. AND/OR are Boolean '
            'connectors; INTERSECTS is a graph relation and never a connector.'
        )
        response = client.chat.completions.create(
            model=_nl_llm_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=1200,
        )
        st.session_state["nl_llm_calls"] = used + 1
        payload = (response.choices[0].message.content or "")
        data = _nl_json(payload)
    except Exception as exc:
        out = parse_map_question(text)
        out["parser"] = "rule-based (model unavailable)"
        out["unmatched"].append(_nl_llm_error(exc))
        return out

    fields = {
        "fsm": "s.fsm_pct",
        "attendance": "s.attendance_pct",
        "capped9": "s.capped9_score",
        "budget": "s.budget_per_pupil_gbp",
        "pupils": "coalesce(s.pupils_2025, s.pupils)",
    }
    out: Dict[str, Any] = {
        "text": text, "conditions": [], "params": {},
        "chips": [], "unmatched": [],
        "parser": f"LLM ({_nl_llm_model()})",
        "admin_scope": None, "admin_scopes": [], "admin_operator": "AND",
        "result_kind": "Schools", "spatial_only": False,
        "spatial_relation_failed": False,
    }

    anchor_type = str(data.get("anchor_type") or "")
    relation = str(data.get("relation") or "direct")
    # Administrative relation words are authoritative. This local correction
    # prevents the model from collapsing explicit NEAR into TOUCHES. Transport
    # proximity is excluded because it is a separate DISTANCE_NEAR condition.
    low_text = (text or "").lower()
    local_hint = _map_admin_hint(text)
    if local_hint:
        anchor_type = str(local_hint.get("anchor_type") or anchor_type)
        relation = str(local_hint.get("relation") or relation)
        out["result_kind"] = str(
            local_hint.get("result_kind") or "Schools"
        )
        out["spatial_only"] = bool(local_hint.get("spatial_only"))
    elif re.search(
        r"\b(?:wards?|communities|unitary authorities)\s+"
        r"(?:exactly\s+)?(?:graph[- ]?)?near\b",
        low_text,
    ):
        relation = "graph_near"
    elif re.search(
        r"\b(?:wards?|communities|unitary authorities)\s+"
        r"(?:touch|touches|touching|adjacent)\b",
        low_text,
    ):
        relation = "touches"
    target_type = str(
        (local_hint or {}).get("target_type")
        or data.get("target_type")
        or anchor_type
    )
    anchor_name = str(
        (local_hint or {}).get("anchor_name")
        or data.get("anchor_name")
        or ""
    ).strip()
    valid_admin_types = set(_MAP_ADMIN_TYPES)
    valid_relations = {
        "direct", "touches", "not_touches", "graph_near", "intersects",
        "inside", "contains",
    }
    for raw_scope in (data.get("admin_scopes") or []):
        if not isinstance(raw_scope, dict):
            continue
        scope_anchor_type = str(raw_scope.get("anchor_type") or "")
        scope_relation = str(raw_scope.get("relation") or "direct")
        scope_target_type = str(
            raw_scope.get("target_type") or scope_anchor_type
        )
        scope_anchor_name = str(raw_scope.get("anchor_name") or "").strip()
        if (
            scope_anchor_name
            and scope_anchor_type in valid_admin_types
            and scope_relation in valid_relations
        ):
            out["admin_scopes"].append({
                "anchor_name": scope_anchor_name,
                "anchor_type": scope_anchor_type,
                "relation": scope_relation,
                "target_type": (
                    scope_target_type
                    if scope_target_type in valid_admin_types
                    else scope_anchor_type
                ),
                "result_kind": out["result_kind"],
                "spatial_only": out["spatial_only"],
            })

    if anchor_type in valid_admin_types:
        out["admin_scope"] = {
            "anchor_name": anchor_name,
            "anchor_type": anchor_type, "relation": relation,
            "target_type": target_type,
            "result_kind": out["result_kind"],
            "spatial_only": out["spatial_only"],
        }
        if not out["admin_scopes"]:
            out["admin_scopes"] = [dict(out["admin_scope"])]
        elif len(out["admin_scopes"]) == 1:
            # The explicit local NEAR/TOUCH correction above is authoritative
            # for a single scope even if the model mislabeled that list item.
            out["admin_scopes"][0].update(out["admin_scope"])

    admin_operator = str(data.get("admin_operator") or "").upper()
    if admin_operator not in {"AND", "OR"}:
        admin_operator = "OR" if re.search(r"\bor\b", low_text) else "AND"
    out["admin_operator"] = admin_operator

    # Recover the common same-anchor form even if the model returned only one
    # relation. This is deterministic and does not invent a place or type.
    if out["admin_scope"] and len(out["admin_scopes"]) < 2:
        compound_relations: List[str] = []
        if re.search(r"\b(?:in|inside|within)\b", low_text):
            compound_relations.append("direct")
        if (
            relation != "not_touches"
            and re.search(r"\b(?:touch|touches|touching|adjacent)\b", low_text)
        ):
            compound_relations.append("touches")
        if re.search(r"\b(?:graph[- ]?near|near)\b", low_text) and not re.search(
            r"\b(?:near|close to)\s+transport\b", low_text
        ):
            compound_relations.append("graph_near")
        compound_relations = list(dict.fromkeys(compound_relations))
        if len(compound_relations) > 1:
            base_scope = out["admin_scope"]
            out["admin_scopes"] = [
                {**base_scope, "relation": rel} for rel in compound_relations
            ]

    dep = str(data.get("deprivation") or "").lower()
    if dep in {"high", "medium", "low"}:
        out["conditions"].append(
            "coalesce(l.deprivation, s.deprivation) = $nl_dep"
        )
        out["params"]["nl_dep"] = f"{dep}_deprivation"
        out["chips"].append(f"deprivation = {dep}")

    phases = [
        p for p in (data.get("phases") or [])
        if p in {"primary", "secondary", "special"}
    ]
    if phases:
        out["conditions"].append(
            "ANY(p IN $nl_phases WHERE "
            "toLower(coalesce(s.phase_group, s.phase, s.school_type)) "
            "CONTAINS p)"
        )
        out["params"]["nl_phases"] = phases
        out["chips"].append("phase = " + " / ".join(phases))

    # The manual sidebar has always had a Local authority filter; the parser
    # schema did not, so a question naming a place parsed to nothing and the
    # map fell back to all 1,444 schools. Bound as a parameter like the rest.
    authority = str(data.get("authority") or "").strip()
    if out["admin_scopes"]:
        authority = ""
    if authority:
        out["conditions"].append(
            "toLower(coalesce(s.local_authority_name, s.local_authority, "
            "l.local_authority, '')) CONTAINS toLower($nl_authority)"
        )
        out["params"]["nl_authority"] = authority
        out["chips"].append(f"local authority = {authority}")

    medium = str(data.get("medium") or "").lower()
    if medium in {"welsh", "english"}:
        out["conditions"].append(
            "toLower(coalesce(s.language_medium, '')) CONTAINS $nl_medium"
        )
        out["params"]["nl_medium"] = medium
        out["chips"].append(f"language medium = {medium}")

    transport = str(data.get("transport") or "").lower()
    if transport == "near":
        out["conditions"].append(
            "EXISTS { MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) }"
        )
        out["chips"].append("transport stop within 800m")
    elif transport == "far":
        out["conditions"].append(
            "NOT EXISTS { MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) }"
        )
        out["chips"].append("no transport stop within 800m")

    used_names = 0
    for item in (data.get("ranges") or []):
        field = fields.get(str(item.get("field", "")).lower())
        if not field:
            continue
        try:
            lo, hi = float(item["min"]), float(item["max"])
        except Exception:
            continue
        lo, hi = min(lo, hi), max(lo, hi)
        a, b = f"nl_lo{used_names}", f"nl_hi{used_names}"
        out["conditions"].append(f"{field} >= ${a} AND {field} <= ${b}")
        out["params"][a], out["params"][b] = lo, hi
        out["chips"].append(f"{item.get('field')} between {lo:g} and {hi:g}")
        used_names += 1

    for item in (data.get("comparisons") or []):
        field = fields.get(str(item.get("field", "")).lower())
        op = item.get("op")
        if not field or op not in {">=", "<="}:
            continue
        try:
            value = float(item["value"])
        except Exception:
            continue
        name = f"nl_cmp{used_names}"
        out["conditions"].append(f"{field} {op} ${name}")
        out["params"][name] = value
        out["chips"].append(f"{item.get('field')} {op} {value:g}")
        used_names += 1

    if not out["conditions"] and not out.get("admin_scopes"):
        out["unmatched"].append(
            "The model returned nothing that maps onto a school property."
        )
    return out


def render_map_nl(cfg: Dict[str, str]) -> Dict[str, Any]:
    """Question box for the map. Returns extra conditions for the query."""
    st.markdown("### Search in your own words")

    col_q, col_go, col_clear = st.columns([6, 1, 1])
    with col_q:
        question = st.text_input(
            "Map question",
            key="map_nl_question",
            placeholder="Try: Secondary schools in high-deprivation areas",
            label_visibility="collapsed",
        )
    with col_go:
        # The map already re-reads the question on every run, so this button
        # is a deliberate submit affordance rather than new behaviour: a
        # search field with no Search button reads as unfinished.
        asked = st.button(
            "Search", type="primary", use_container_width=True,
            key="map_nl_submit",
        )
    with col_clear:
        clear = st.button("Clear", use_container_width=True, key="map_nl_clear_button")
    if clear:
        # Raised as a plain flag and applied at the top of the next run,
        # before the text box is created. Writing to a widget's state after
        # the widget exists is refused by Streamlit.
        st.session_state["map_nl_clear"] = True
        st.rerun()

    # Keep parser mechanics out of the interface. The deterministic parser
    # is used here so temporary model demand or missing credentials can never
    # replace the user's result with a technical status message.
    parsed = parse_map_question(question)
    parsed["submitted"] = bool(asked)

    if len(re.findall(r"\blsoas?\b", question.lower())) >= 2:
        relation = _map_explicit_relation(question)
        table_relation = {
            "not_touches": "disjoint", "inside": "within"
        }.get(relation, relation)
        if (
            table_relation not in _possible_pair_relations("LSOA", "LSOA")
            and relation != "graph_near"
        ):
            parsed["spatial_relation_failed"] = True
            message = (
                f"{relation.replace('_', ' ').upper()} is not possible for "
                "LSOA → LSOA. Available: DISJOINT and TOUCHES; "
                "GRAPH_NEAR is derived from two LSOA_TOUCHES steps."
            )
            if message not in parsed["unmatched"]:
                parsed["unmatched"].append(message)

    # The model/rules identify only a constrained intent. Neo4j resolves the
    # exact unit and executes one of three fixed parameterised graph paths.
    parsed["resolved_admin_scope"] = None
    parsed["admin_scope_failed"] = False
    requested_scopes = parsed.get("admin_scopes") or (
        [parsed["admin_scope"]] if parsed.get("admin_scope") else []
    )
    if requested_scopes:
        try:
            resolved, scope_warnings = resolve_map_admin_scopes(
                cfg,
                requested_scopes,
                str(parsed.get("admin_operator") or "AND").upper(),
            )
            parsed["resolved_admin_scope"] = resolved
            parsed["admin_scope_failed"] = resolved is None
            parsed["unmatched"].extend(scope_warnings)
            if resolved and resolved.get("compound"):
                parsed["chips"].append(
                    f"administrative operator = {resolved['operator']}"
                )
                for component in resolved["components"]:
                    a = component["anchor"]
                    parsed["chips"].append(
                        f"{component['relation']} scope = "
                        f"{a.get('name')} ({a.get('unit_type')})"
                    )
            elif resolved:
                a = resolved["anchor"]
                parsed["chips"].extend([
                    f"anchor = {a.get('name')}",
                    f"anchor type = {a.get('unit_type')}",
                    f"relation = {resolved['relation']}",
                    f"target type = {resolved['target_type']}",
                    f"provenance = {resolved.get('provenance')}",
                ])
        except Exception as exc:
            parsed["admin_scope_failed"] = True
            parsed["unmatched"].append(f"Administrative path unavailable: {exc}")

    # School conditions have no effect in cluster search, which pools LSOAs
    # rather than schools, so a question that names any of them switches the
    # mode instead of returning a map that quietly ignored it.
    # The radio is drawn in the sidebar before this runs, and Streamlit
    # forbids writing to a widget's state once the widget exists. A plain
    # flag is raised instead and applied at the top of the next run, before
    # the radio is created.
    last_applied = st.session_state.get("map_nl_applied")
    if (
        (parsed["conditions"] or parsed.get("resolved_admin_scope"))
        and question != last_applied
        and st.session_state.get("map_search_mode") == "Cluster search"
    ):
        # Only when the question is new. Forcing on every rerun made cluster
        # search unreachable: the moment it was chosen, the standing question
        # switched it straight back.
        st.session_state["map_nl_applied"] = question
        st.session_state["map_force_standard"] = True
        st.rerun()
    st.session_state["map_nl_applied"] = question

    if (
        (parsed["conditions"] or parsed.get("resolved_admin_scope"))
        and st.session_state.get("map_search_mode") == "Cluster search"
    ):
        st.markdown(
            "<div class='nl-warn'>Cluster search pools LSOAs, not schools, "
            "so the conditions from your question do not apply here. Switch "
            "to Standard search to use them.</div>",
            unsafe_allow_html=True,
        )

    if (
        question
        and not parsed["conditions"]
        and not parsed.get("resolved_admin_scope")
        and not parsed.get("spatial_relation_failed")
    ):
        st.info(
            "We could not match that request to the available school or "
            "spatial filters. Try a place, school phase, deprivation level, "
            "FSM, attendance or transport condition."
        )
    return parsed


def page_map(cfg: Dict[str, str]) -> None:
    st.markdown(
        "<style>[data-testid='stMainBlockContainer']{max-width:1600px!important;"
        "padding-left:2.2rem!important;padding-right:2.2rem!important}"
        ".map-search-hero{max-width:1120px;margin:1rem auto 1.45rem;"
        "display:flex;align-items:center;gap:2rem;text-align:left;"
        "padding:1.8rem 2.2rem;border-radius:28px;"
        "background:linear-gradient(125deg,#ff707c 0%,#ff9a72 52%,#ffc55c 100%);"
        "box-shadow:0 22px 55px rgba(185,76,55,.18)}"
        ".map-search-hero h1{font-size:clamp(2rem,4vw,3.2rem);"
        "letter-spacing:-.04em;line-height:1.08;margin:0;color:#fff;"
        "font-weight:850}.map-search-hero p{font-size:1rem;color:#fff7f2;"
        "margin:.55rem 0 0}.map-hero-logo{width:190px;max-height:180px;"
        "object-fit:contain;flex:0 0 auto;filter:drop-shadow(0 12px 22px rgba(75,36,25,.18))}"
        ".map-hero-copy{flex:1;text-align:center}"
        "div[data-testid='stTextInput'] input,div[data-testid='stNumberInput'] input{"
        "border-radius:14px!important;min-height:3.15rem;padding-left:1rem;"
        "background:#fffdfa!important;border:1px solid #f3cbbc!important;"
        "box-shadow:0 7px 18px rgba(117,58,43,.07)!important}"
        "div[data-testid='stSelectbox']>div>div{background:#fffdfa!important;"
        "border:1px solid #f3cbbc!important;border-radius:14px!important;"
        "box-shadow:0 7px 18px rgba(117,58,43,.07)!important}"
        "div[data-testid='stExpander']{border:1px solid #f0cfc2!important;"
        "border-radius:18px!important;background:#fffaf7!important;"
        "box-shadow:0 10px 28px rgba(91,48,38,.06)!important}"
        "div[data-testid='stDeckGlJsonChart']{border:1px solid #f0cfc2;"
        "border-radius:24px;overflow:hidden;box-shadow:0 20px 48px rgba(91,48,38,.14)}"
        "div[data-testid='stDataFrame']{border:1px solid #f0cfc2!important;"
        "border-radius:20px!important;overflow:hidden!important;background:#fffdfa!important;"
        "box-shadow:0 14px 34px rgba(91,48,38,.10)!important;padding:6px!important}"
        "div[data-testid='stDataFrame'] [role='columnheader']{"
        "background:#fff0e8!important;color:#65362e!important;font-weight:800!important}"
        "div[data-testid='stMetric']{background:linear-gradient(135deg,#fffdfa,#fff3ec)!important;"
        "border:1px solid #f2d5ca!important;border-radius:17px!important;"
        "box-shadow:0 9px 24px rgba(91,48,38,.06)!important;padding:.7rem .9rem!important}"
        ".school-results-title{font-size:1.45rem;font-weight:850;color:#4c2b25;"
        "margin:1.4rem 0 .6rem}.results-basis{color:#76574f;font-size:.88rem;"
        "margin:.2rem 0 1rem}"
        "</style>",
        unsafe_allow_html=True,
    )
    hero_shell = st.container(key="map_search_hero")
    logo_path = Path(__file__).with_name("wales_education_kg.png")
    logo_html = ""
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        logo_html = (
            "<img class='map-hero-logo' alt='Wales Education KG' "
            f"src='data:image/png;base64,{logo_b64}'>"
        )
    hero_shell.markdown(
        "<div class='map-search-hero'>" + logo_html
        + "<div class='map-hero-copy'><h1>Explore Welsh schools by place</h1>"
        "<p>Search schools, compare local indicators and view the geographic "
        "areas connected to each result.</p></div></div>",
        unsafe_allow_html=True,
    )

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
      AND phase IN ['Primary', 'Secondary', 'Special', 'All-age']
    RETURN phase AS value, phase AS label
    ORDER BY label
    LIMIT 100
    """)
    if not phase_opts:
        # Fallback when phase_group values differ from the standard four:
        # show whatever distinct values exist rather than an empty list.
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

    search_shell = st.container(key="map_search_builder")
    search_tabs = search_shell.tabs(["Build a search", "Write in your own words"])
    controls = search_tabs[0].container()
    controls.markdown("## Find schools")
    controls.caption("Choose filters, then open the results on the map.")
    if st.session_state.pop("map_nl_clear", False):
        st.session_state["map_nl_question"] = ""
        st.session_state.pop("map_nl_applied", None)

    # This page has one job: find schools and show their pins.  The former
    # Standard/Cluster switch exposed an evaluation implementation detail to
    # a first-time user and made the ordinary map look like one of several
    # specialist modes.  Keep the implementation variable for the existing
    # query path, but do not present a redundant choice.
    st.session_state.pop("map_force_standard", None)
    st.session_state["map_search_mode"] = "Standard search"
    search_mode = "Standard search"

    # Property names match load_to_neo4j.py's load_wimd(); the last three
    # are added by the extended loader and need one RUN_WIMD_LOAD re-run.
    WIMD_DOMAIN_PROPS = {
        "Overall (WIMD 2019)": "wimd_rank",
        "Income": "income_rank",
        "Employment": "employment_rank",
        "Health": "health_rank",
        "Education": "education_rank",
        "Access to Services": "access_rank",
        "Housing": "housing_rank",
        "Community Safety": "safety_rank",
        "Physical Environment": "environment_rank",
    }
    CLUSTER_VARIABLES = [
        "Deprivation level",
        "Deprivation rank",
        "School FSM average",
        "School attendance average",
        "School Capped 9 average (secondary only)",
        "High FSM and low attendance (compound)",
    ]
    cluster_variable = "School FSM average"
    cluster_domain_label = "Overall (WIMD 2019)"
    cluster_dep_levels = ["High"]
    cluster_rank_min = cluster_rank_max = None
    cluster_fsm_min = cluster_fsm_max = None
    cluster_att_min = cluster_att_max = None
    cluster_cap_min = cluster_cap_max = None
    cluster_inputs_ok = True
    cluster_view = "Bounded pool"
    band_cut1 = band_cut2 = None
    cluster_depth = 4
    min_cluster_size = 3
    if search_mode == "Cluster search":
        controls.markdown("### Adjacency cluster")
        controls.caption(
            "Geometry-origin. LSOA_TOUCHES is computed from boundary "
            "geometry, not asserted by YAGO2geo, so cluster results do not "
            "count towards native model completeness. This is also not the "
            "statistical hot-spot cluster used by Sandu et al."
        )
        cluster_variable = controls.selectbox(
            "Cluster on",
            CLUSTER_VARIABLES,
            index=CLUSTER_VARIABLES.index("School FSM average"),
            help=(
                "Deprivation options use LSOA-level WIMD values. School "
                "options average the metric over the schools LOCATED_IN each "
                "LSOA, so LSOAs with no schools drop out of those pools. "
                "Capped 9 is deliberately not offered: it exists for 205 of "
                "1,453 schools (secondary only), so clustering on it would "
                "trace where secondary schools are, not where attainment "
                "clusters."
            ),
        )
        def cluster_bound(
            label: str,
            default_text: str,
            lo: float,
            hi: float,
            key: str,
            integer: bool = False,
        ) -> float | None:
            """Optional typed bound. Blank or All means no bound on this side."""
            raw = controls.text_input(
                label, value=default_text, placeholder="All", key=key
            )
            text = str(raw).strip()
            if not text or text.lower() == "all":
                return None
            try:
                value = float(text)
            except ValueError:
                controls.error(f"{label}: enter a number or All.")
                st.session_state["_cluster_input_error"] = True
                return None
            if value < lo or value > hi:
                controls.error(
                    f"{label}: {value:g} is outside the data range "
                    f"({lo:g}\u2013{hi:g})."
                )
                st.session_state["_cluster_input_error"] = True
                return None
            return float(int(value)) if integer else value

        st.session_state["_cluster_input_error"] = False
        controls.caption(
            "Type exact bounds; leave a box as All to drop that side. The "
            "exact values you type are what goes in the research log."
        )
        if cluster_variable == "Deprivation level":
            cluster_dep_levels = controls.multiselect(
                "Levels to include",
                ["High", "Medium", "Low"],
                default=["High"],
                help=(
                    "High = deciles 1-3 (most deprived 30%), Medium = 4-7, "
                    "Low = 8-10 — the same stored categories that colour the "
                    "map pins red / orange / green."
                ),
            )
            if not cluster_dep_levels:
                controls.error("Pick at least one deprivation level.")
                st.session_state["_cluster_input_error"] = True
        elif cluster_variable == "Deprivation rank":
            cluster_domain_label = controls.selectbox(
                "Which deprivation measure",
                list(WIMD_DOMAIN_PROPS.keys()),
                index=0,
                help=(
                    "Overall is the combined WIMD 2019 rank. The eight "
                    "domains break deprivation down by type: Income, "
                    "Employment, Health, Education, Access to Services, "
                    "Housing, Community Safety, Physical Environment."
                ),
            )
            cluster_rank_min = cluster_bound(
                "Domain rank from", "All", 1, 1909, "cl_rank_min", integer=True
            )
            cluster_rank_max = cluster_bound(
                "Domain rank to", "382", 1, 1909, "cl_rank_max", integer=True
            )
            controls.caption(
                "Rank 1 = most deprived of 1,909. 'to 382' is the most "
                "deprived quintile. Ranks come from wimd_2019.xlsx via "
                "load_wimd() (RUN_WIMD_LOAD = True)."
            )
        elif cluster_variable == "School FSM average":
            cluster_fsm_min = cluster_bound(
                "Mean school FSM % from", "30", 0.0, 71.8, "cl_fsm_min"
            )
            cluster_fsm_max = cluster_bound(
                "Mean school FSM % to", "All", 0.0, 71.8, "cl_fsm_max"
            )
            controls.caption(
                "Mean over the schools LOCATED_IN each LSOA; FSM coverage "
                "is 96.6% of schools."
            )
        elif cluster_variable == "School Capped 9 average (secondary only)":
            cluster_cap_min = cluster_bound(
                "Mean Capped 9 from", "All", 245.1, 453.1, "cl_cap_min"
            )
            cluster_cap_max = cluster_bound(
                "Mean Capped 9 to", "300", 245.1, 453.1, "cl_cap_max"
            )
            controls.warning(
                "Capped 9 exists for 205 of 1,453 schools (14.1%, secondary "
                "only), so very few LSOAs carry a value and even fewer touch "
                "each other. Expect small, scattered clusters. Report these "
                "as attainment clusters among secondary schools, never as "
                "attainment clusters across Wales."
            )
        elif cluster_variable == "School attendance average":
            cluster_att_min = cluster_bound(
                "Mean attendance % from", "All", 79.1, 98.1, "cl_att_min"
            )
            cluster_att_max = cluster_bound(
                "Mean attendance % to", "92", 79.1, 98.1, "cl_att_max"
            )
            controls.caption(
                "The official Welsh Government persistent-absence line is "
                "90%. Attendance coverage is 96.7% of schools."
            )
        else:
            cluster_fsm_min = cluster_bound(
                "Mean school FSM % from", "30", 0.0, 71.8, "cl_c_fsm_min"
            )
            cluster_fsm_max = cluster_bound(
                "Mean school FSM % to", "All", 0.0, 71.8, "cl_c_fsm_max"
            )
            cluster_att_min = cluster_bound(
                "Mean attendance % from", "All", 79.1, 98.1, "cl_c_att_min"
            )
            cluster_att_max = cluster_bound(
                "Mean attendance % to", "92", 79.1, 98.1, "cl_c_att_max"
            )
            controls.caption(
                "The compound pool needs both metrics inside their bounds "
                "at once: deprivation pressure (FSM) and low attendance."
            )
        for low, high, label in (
            (cluster_rank_min, cluster_rank_max, "Domain rank"),
            (cluster_fsm_min, cluster_fsm_max, "FSM"),
            (cluster_att_min, cluster_att_max, "Attendance"),
            (cluster_cap_min, cluster_cap_max, "Capped 9"),
        ):
            if low is not None and high is not None and low > high:
                controls.error(f"{label}: From is above To.")
                st.session_state["_cluster_input_error"] = True
        cluster_inputs_ok = not st.session_state.get(
            "_cluster_input_error", False
        )
        # Cluster search always builds bounded pools. The former
        # "All severity bands" whole-map view was removed as a second
        # control the user had to reason about: pin colours already carry
        # the traffic-light grading in every mode.
        cluster_view = "Bounded pool"
        # Cluster reach, named with the evaluation instrument's own
        # proximity vocabulary instead of a raw hop count: touches = 1 hop,
        # graph-near = 2 hops (the paper's near), far = more than 2.
        # Clusters are true connected components via APOC, so there is no
        # depth to choose. This value is only used by the fallback query if
        # APOC is unavailable on the target database.
        cluster_depth = 4
        min_cluster_size = controls.number_input(
            "Smallest cluster to show (LSOAs)",
            min_value=1,
            max_value=50,
            value=3,
            step=1,
            help=(
                "A cluster is reported only if it has at least this many "
                "connected LSOAs. 1 shows everything, including isolated "
                "single LSOAs; 3 hides singletons and pairs; a large value "
                "such as 20 keeps only the big contiguous belts."
            ),
        )

    dep_options = [
        ("All", "All"),
        ("high_deprivation", "High"),
        ("medium_deprivation", "Medium"),
        ("low_deprivation", "Low"),
        ("unknown", "Unknown"),
    ]
    if search_mode == "Cluster search":
        # In cluster mode the cluster itself defines the deprivation scope,
        # so the general filter is hidden to avoid two competing controls.
        dep_choice = dep_options[0]
    else:
        dep_choice = controls.selectbox(
            "Deprivation",
            dep_options,
            format_func=lambda x: x[1],
        )
    dep = dep_choice[0]
    dep_label = dep_choice[1]
    transport = controls.selectbox(
        "Transport access",
        [
            "All",
            "Distance-near (within 800m)",
            "Distance-far (no stop within 800m)",
        ],
        index=0,
        help=(
            "A metric threshold: whether a transport stop lies within 800m of "
            "the school. This is a planning proxy and a third notion of "
            "proximity, kept apart from the graph proximity the SCQ "
            "questions use, and deliberately outside the completeness "
            "scoring."
        ),
    )
    school_filters = controls.expander("More school filters", expanded=False)
    la = school_filters.selectbox(
        "Local authority", las, format_func=lambda x: x[1]
    )
    phase = school_filters.selectbox(
        "School phase", phases, format_func=lambda x: x[1]
    )
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
    selected_school = school_filters.selectbox(
        "School",
        school_options,
        format_func=lambda x: x[1],
        help=(
            "Open the list and type part of the school name to search, "
            "or keep All matching schools."
        ),
    )
    fsm_min = fsm_max = None
    attendance_min = attendance_max = None
    capped9_min = capped9_max = None
    with school_filters:
        st.markdown("---")
        metric_filter = st.selectbox(
            "Filter by a school measure",
            ["None", "FSM", "Attendance", "Capped 9"],
            help=(
                "Choose a measure first. Its available range will appear "
                "from the data currently loaded in the graph."
            ),
        )
        metric_specs = {
            "FSM": ("FSM %", 0.0, 71.8, 0.5, "m_fsm"),
            "Attendance": ("Attendance %", 79.1, 98.1, 0.1, "m_att"),
            "Capped 9": ("Capped 9 points", 245.1, 453.1, 1.0, "m_cap"),
        }
        if metric_filter in metric_specs:
            label, data_min, data_max, step, metric_key = metric_specs[metric_filter]
            st.caption(
                f"Available in this graph: {data_min:g}–{data_max:g}. "
                "Leave either side empty when no limit is needed."
            )
            low_col, high_col = st.columns(2)
            with low_col:
                low_value = st.number_input(
                    f"{label} from", min_value=data_min, max_value=data_max,
                    value=None, step=step, placeholder=f"Min {data_min:g}",
                    key=f"{metric_key}_from",
                )
            with high_col:
                high_value = st.number_input(
                    f"{label} to", min_value=data_min, max_value=data_max,
                    value=None, step=step, placeholder=f"Max {data_max:g}",
                    key=f"{metric_key}_to",
                )
            if metric_filter == "FSM":
                fsm_min, fsm_max = low_value, high_value
            elif metric_filter == "Attendance":
                attendance_min, attendance_max = low_value, high_value
            else:
                capped9_min, capped9_max = low_value, high_value
                st.caption(
                    "Capped 9 is a points score available for secondary "
                    "schools; it is not a percentage."
                )
        # Metric filters always require a value; how many schools were
        # removed for having no value is disclosed above the map, so the
        # exclusion is visible without an extra control here.
        include_missing_metrics = False

    # Bounds are enforced by the number inputs themselves; only the
    # From/To ordering can still be wrong.
    range_order_ok = True
    for low, high, label in (
        (fsm_min, fsm_max, "FSM"),
        (attendance_min, attendance_max, "Attendance"),
        (capped9_min, capped9_max, "Capped 9"),
    ):
        if low is not None and high is not None and low > high:
            controls.error(f"{label}: the From value is above the To value.")
            range_order_ok = False
    if not range_order_ok:
        st.info("Swap the From and To values marked in red above.")
        return

    build_run = controls.button(
        "Show results on map", type="primary", use_container_width=True,
        key="map_filter_submit",
    )
    with search_tabs[1]:
        st.markdown("## Ask for schools in your own words")
        st.caption(
            "Use a place, school phase, deprivation level, transport access, "
            "FSM, attendance or Capped 9 condition."
        )
        nl_map = render_map_nl(cfg)

    if build_run or nl_map.get("submitted"):
        st.session_state["map_has_run"] = True
        st.session_state["map_scroll_to_results"] = True
    if not st.session_state.get("map_has_run"):
        return
    st.markdown(
        "<style>.st-key-map_search_hero,.st-key-map_search_builder{"
        "display:none!important}</style>",
        unsafe_allow_html=True,
    )

    if nl_map.get("spatial_relation_failed"):
        st.info(
            "The map was not run because the requested Domain–Range pair "
            "does not support that spatial relationship. No alternative "
            "relationship or all-schools fallback was used."
        )
        return

    # A named administrative scope is part of the meaning of the question.
    # Falling back to every Welsh school after resolution fails would return
    # a confident-looking answer to a different question.
    if nl_map.get("admin_scope_failed"):
        st.info(
            "The map was not run because the requested administrative unit "
            "could not be resolved exactly. Change the name or type shown "
            "above and search again."
        )
        return

    conditions = ["s.latitude IS NOT NULL", "s.longitude IS NOT NULL"]
    params: Dict[str, Any] = {}
    # Sentence conditions sit alongside the sidebar filters rather than
    # replacing them, so the two can be combined and the reader can see
    # exactly what each contributed.
    conditions.extend(nl_map["conditions"])
    params.update(nl_map["params"])
    admin_scope = nl_map.get("resolved_admin_scope")
    if admin_scope and admin_scope.get("spatial_only"):
        anchor = admin_scope["anchor"]
        relation = str(admin_scope.get("relation") or "")
        result_kind = str(admin_scope.get("result_kind") or "")
        units = admin_scope.get("units", pd.DataFrame())
        if result_kind == "LSOA":
            codes = sorted(set(admin_scope.get("lsoa_codes") or []))
            spatial_df = pd.DataFrame({"lsoa_code": codes})
            st.metric("LSOAs returned", len(codes))
            st.caption(
                f"{relation.upper()} from {anchor.get('name')} "
                f"({anchor.get('unit_type')}). The map shows the spatial "
                "answer itself; click an LSOA for its code, deprivation and "
                "schools."
            )
            clicked_lsoa = render_answer_map(
                cfg,
                spatial_df,
                focus_code=None,
                key="map_spatial_lsoa_answer",
                focus_admin=str(anchor.get("uri") or ""),
            )
            if clicked_lsoa:
                render_lsoa_school_panel(cfg, clicked_lsoa)
            display_df(spatial_df)
        else:
            unit_df = (
                units.dropna(subset=["unit_uri"])
                .drop_duplicates(subset=["unit_uri"])
                if isinstance(units, pd.DataFrame) and not units.empty
                else pd.DataFrame()
            )
            st.metric("Administrative units returned", len(unit_df))
            st.caption(
                f"{relation.replace('_', ' ').upper()} from "
                f"{anchor.get('name')} ({anchor.get('unit_type')}). "
                "These polygons are the exact administrative answer; school "
                "pins are not substituted for the requested units."
            )
            picked_unit = render_admin_answer_map(
                cfg,
                unit_df,
                None,
                key="map_spatial_admin_answer",
                focus_admin=str(anchor.get("uri") or ""),
            )
            if picked_unit and picked_unit.get("uri") != anchor.get("uri"):
                render_unit_school_card(cfg, picked_unit)
            display_df(unit_df)
        return
    if admin_scope:
        conditions.append("l.code IN $nl_admin_lsoa_codes")
        params["nl_admin_lsoa_codes"] = admin_scope["lsoa_codes"]
    if selected_school[0] != "All" and search_mode == "Standard search":
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
    base_conditions = list(conditions)
    filtered_metric_props: List[str] = []

    def add_range_condition(prop: str, low: float | None, high: float | None) -> None:
        """Two-sided range on a School property, explicit about missing values."""
        parts: List[str] = []
        if low is not None:
            parts.append(f"s.{prop} >= $min_{prop}")
            params[f"min_{prop}"] = low
        if high is not None:
            parts.append(f"s.{prop} <= $max_{prop}")
            params[f"max_{prop}"] = high
        if not parts:
            return
        filtered_metric_props.append(prop)
        expression = " AND ".join(parts)
        if include_missing_metrics:
            conditions.append(f"(s.{prop} IS NULL OR ({expression}))")
        else:
            conditions.append(f"(s.{prop} IS NOT NULL AND {expression})")

    add_range_condition("fsm_pct", fsm_min, fsm_max)
    add_range_condition("attendance_pct", attendance_min, attendance_max)
    add_range_condition("capped9_score", capped9_min, capped9_max)
    if transport == "Distance-near (within 800m)":
        conditions.append(
            "EXISTS { "
            "MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) "
            "}"
        )
    elif transport == "Distance-far (no stop within 800m)":
        conditions.append(
            "NOT EXISTS { "
            "MATCH (s)-[:DISTANCE_NEAR]->(:TransportStop) "
            "}"
        )
    cluster_df = pd.DataFrame()
    cluster_exact = True
    cluster_codes: List[str] = []
    cluster_cypher = ""
    cluster_params: Dict[str, Any] = {"min_size": int(min_cluster_size)}
    cluster_pool_label = ""
    band_map: Dict[str, str] = {}
    band_label = ""
    band_cypher = ""
    if search_mode == "Cluster search":
        if not cluster_inputs_ok:
            st.info(
                "Fix the red cluster bound message in the sidebar, or type "
                "All to drop that bound."
            )
            return

        if cluster_view == "All severity bands":
            c1, c2 = float(band_cut1), float(band_cut2)
            if cluster_variable == "Deprivation level":
                band_cypher = (
                    "MATCH (l:LSOA)\n"
                    "WHERE l.deprivation IS NOT NULL\n"
                    "RETURN l.code AS code,\n"
                    "  CASE l.deprivation\n"
                    "       WHEN 'high_deprivation' THEN 'band_red'\n"
                    "       WHEN 'medium_deprivation' THEN 'band_mid'\n"
                    "       WHEN 'low_deprivation' THEN 'band_green'\n"
                    "       ELSE 'band_none' END AS band"
                )
                band_label = (
                    "stored deprivation category: high / medium / low"
                )
            elif cluster_variable == "Deprivation rank":
                domain_prop = WIMD_DOMAIN_PROPS[cluster_domain_label]
                band_cypher = (
                    "MATCH (l:LSOA)\n"
                    f"WHERE l.{domain_prop} IS NOT NULL\n"
                    "RETURN l.code AS code,\n"
                    f"  CASE WHEN l.{domain_prop} <= $c1 THEN 'band_red'\n"
                    f"       WHEN l.{domain_prop} <= $c2 THEN 'band_mid'\n"
                    "       ELSE 'band_green' END AS band"
                )
                band_label = (
                    f"{cluster_domain_label} rank bands: red <= {c1:g}, "
                    f"orange <= {c2:g}, green above"
                )
            elif cluster_variable == "School FSM average":
                band_cypher = (
                    "MATCH (l:LSOA)\n"
                    "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                    "WITH l, avg(s.fsm_pct) AS m\n"
                    "WHERE m IS NOT NULL\n"
                    "RETURN l.code AS code,\n"
                    "  CASE WHEN m >= $c2 THEN 'band_red'\n"
                    "       WHEN m >= $c1 THEN 'band_mid'\n"
                    "       ELSE 'band_green' END AS band"
                )
                band_label = (
                    f"mean school FSM bands: green < {c1:g}%, orange "
                    f"{c1:g}-{c2:g}%, red >= {c2:g}%"
                )
            else:
                band_cypher = (
                    "MATCH (l:LSOA)\n"
                    "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                    "WITH l, avg(s.attendance_pct) AS m\n"
                    "WHERE m IS NOT NULL\n"
                    "RETURN l.code AS code,\n"
                    "  CASE WHEN m <= $c1 THEN 'band_red'\n"
                    "       WHEN m <= $c2 THEN 'band_mid'\n"
                    "       ELSE 'band_green' END AS band"
                )
                band_label = (
                    f"mean attendance bands: red <= {c1:g}%, orange "
                    f"{c1:g}-{c2:g}%, green > {c2:g}%"
                )
            try:
                band_df = run_cypher(
                    cfg, band_cypher, {"c1": c1, "c2": c2}
                )
            except Exception as exc:
                st.error(f"Band query failed: {exc}")
                if SHOW_QUERIES:
                    st.code(band_cypher, language="cypher")
                return
            band_map = dict(
                zip(band_df["code"].astype(str), band_df["band"])
            )

        def range_clause(
            expr: str, low: float | None, high: float | None,
            p_low: str, p_high: str, as_int: bool = False,
        ) -> Tuple[str, str]:
            """WHERE fragment + human label for an optional two-sided bound."""
            parts, labels = [], []
            if low is not None:
                parts.append(f"{expr} >= ${p_low}")
                cluster_params[p_low] = int(low) if as_int else float(low)
                labels.append(f">= {low:g}")
            if high is not None:
                parts.append(f"{expr} <= ${p_high}")
                cluster_params[p_high] = int(high) if as_int else float(high)
                labels.append(f"<= {high:g}")
            return " AND ".join(parts), " and ".join(labels)

        if cluster_view == "All severity bands":
            pass
        elif cluster_variable == "Deprivation level":
            if not cluster_dep_levels:
                st.warning("Pick at least one deprivation level.")
                return
            level_values = [
                f"{lvl.lower()}_deprivation" for lvl in cluster_dep_levels
            ]
            cluster_params["dep_levels"] = level_values
            pool_match = (
                "MATCH (l:LSOA)\n"
                "WHERE l.deprivation IN $dep_levels\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                "deprivation level " + " / ".join(cluster_dep_levels)
            )
        elif cluster_variable == "Deprivation rank":
            domain_prop = WIMD_DOMAIN_PROPS[cluster_domain_label]
            loaded = int(
                scalar(
                    cfg,
                    f"MATCH (l:LSOA) WHERE l.{domain_prop} IS NOT NULL "
                    "RETURN count(l)",
                    default=0,
                )
                or 0
            )
            if loaded == 0:
                st.error(
                    f"No LSOA carries {domain_prop} on this database yet. "
                    "Set RUN_WIMD_LOAD = True in load_to_neo4j.py (extended "
                    "version) and run it against this database, then reload "
                    "this page. Housing, Community Safety and Physical "
                    "Environment need the extended loader; the other five "
                    "domains load with the original."
                )
                return
            if cluster_rank_min is None and cluster_rank_max is None:
                st.warning("Set at least one domain-rank bound.")
                return
            clause, lab = range_clause(
                f"l.{domain_prop}", cluster_rank_min, cluster_rank_max,
                "min_rank", "max_rank", as_int=True,
            )
            pool_match = (
                "MATCH (l:LSOA)\n"
                f"WHERE l.{domain_prop} IS NOT NULL AND {clause}\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                f"{cluster_domain_label} rank {lab} "
                f"(of 1,909; {loaded:,} LSOAs carry the rank)"
            )
        elif cluster_variable == "School FSM average":
            if cluster_fsm_min is None and cluster_fsm_max is None:
                st.warning("Set at least one FSM bound.")
                return
            clause, lab = range_clause(
                "pool_metric", cluster_fsm_min, cluster_fsm_max,
                "fsm_lo", "fsm_hi",
            )
            pool_match = (
                "MATCH (l:LSOA)\n"
                "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                "WITH l, avg(s.fsm_pct) AS pool_metric\n"
                f"WHERE pool_metric IS NOT NULL AND {clause}\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                f"mean school FSM {lab}% (LSOAs with no schools drop out)"
            )
        elif cluster_variable == "School Capped 9 average (secondary only)":
            if cluster_cap_min is None and cluster_cap_max is None:
                st.warning("Set at least one Capped 9 bound.")
                return
            cap_lsoas = int(
                scalar(
                    cfg,
                    "MATCH (l:LSOA)<-[:LOCATED_IN]-(s:School) "
                    "WHERE s.capped9_score IS NOT NULL "
                    "RETURN count(DISTINCT l)",
                    default=0,
                )
                or 0
            )
            clause, lab = range_clause(
                "pool_metric", cluster_cap_min, cluster_cap_max,
                "cap_lo", "cap_hi",
            )
            pool_match = (
                "MATCH (l:LSOA)\n"
                "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                "WITH l, avg(s.capped9_score) AS pool_metric\n"
                f"WHERE pool_metric IS NOT NULL AND {clause}\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                f"mean Capped 9 {lab} — secondary only, and only "
                f"{cap_lsoas:,} of 1,909 LSOAs carry any Capped 9 value"
            )
        elif cluster_variable == "School attendance average":
            if cluster_att_min is None and cluster_att_max is None:
                st.warning("Set at least one attendance bound.")
                return
            clause, lab = range_clause(
                "pool_metric", cluster_att_min, cluster_att_max,
                "att_lo", "att_hi",
            )
            pool_match = (
                "MATCH (l:LSOA)\n"
                "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                "WITH l, avg(s.attendance_pct) AS pool_metric\n"
                f"WHERE pool_metric IS NOT NULL AND {clause}\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                f"mean school attendance {lab}% "
                "(official persistent-absence line: 90%)"
            )
        else:
            fsm_set = (
                cluster_fsm_min is not None or cluster_fsm_max is not None
            )
            att_set = (
                cluster_att_min is not None or cluster_att_max is not None
            )
            if not (fsm_set and att_set):
                st.warning(
                    "The compound pool needs at least one bound on FSM AND "
                    "at least one on attendance."
                )
                return
            fsm_clause, fsm_lab = range_clause(
                "mean_fsm", cluster_fsm_min, cluster_fsm_max,
                "fsm_lo", "fsm_hi",
            )
            att_clause, att_lab = range_clause(
                "mean_att", cluster_att_min, cluster_att_max,
                "att_lo", "att_hi",
            )
            pool_match = (
                "MATCH (l:LSOA)\n"
                "OPTIONAL MATCH (l)<-[:LOCATED_IN]-(s:School)\n"
                "WITH l, avg(s.fsm_pct) AS mean_fsm, "
                "avg(s.attendance_pct) AS mean_att\n"
                "WHERE mean_fsm IS NOT NULL AND mean_att IS NOT NULL\n"
                f"AND {fsm_clause} AND {att_clause}\n"
                "WITH collect(l) AS pool_nodes, collect(l.code) AS pool_codes"
            )
            cluster_pool_label = (
                f"mean FSM {fsm_lab}% AND mean attendance {att_lab}%"
            )

        if cluster_view == "Bounded pool":
            # Exact connected components via APOC: no depth bound, so a
            # cluster is the full maximal set of touching pool members.
            cluster_cypher = f"""
// Adjacency cluster over the computed LSOA_TOUCHES graph.
// Pool: {cluster_pool_label}
// Geometry-origin: LSOA_TOUCHES is derived from boundary geometry and is not
// asserted by YAGO2geo, so this does not count towards model completeness.
// Clusters are exact connected components: apoc.path.subgraphNodes explores
// the whole component with traversal restricted to the pool, so there is no
// depth parameter and no truncation.
{pool_match}
UNWIND pool_nodes AS seed
CALL apoc.path.subgraphNodes(seed, {{
    relationshipFilter: 'LSOA_TOUCHES',
    whitelistNodes: pool_nodes
}}) YIELD node
WITH seed, collect(DISTINCT node.code) AS reach
WITH reach,
     reduce(smallest = head(reach), c IN reach |
            CASE WHEN c < smallest THEN c ELSE smallest END) AS cluster_id
WITH cluster_id, head(collect(reach)) AS members
WHERE size(members) >= $min_size
RETURN cluster_id,
       size(members) AS cluster_size,
       members
ORDER BY cluster_size DESC, cluster_id
"""

            fallback_cypher = f"""
// Fallback used only if APOC is unavailable: bounded expansion, which
// truncates large components at {int(cluster_depth)} steps.
{pool_match}
UNWIND pool_codes AS seed_code
MATCH (seed:LSOA {{code: seed_code}})
MATCH p = (seed)-[:LSOA_TOUCHES*0..{int(cluster_depth)}]-(m:LSOA)
WHERE all(n IN nodes(p) WHERE n.code IN pool_codes)
WITH seed_code, collect(DISTINCT m.code) AS reach
WITH seed_code,
     reduce(smallest = head(reach), c IN reach |
            CASE WHEN c < smallest THEN c ELSE smallest END) AS cluster_id
WITH cluster_id, collect(DISTINCT seed_code) AS members
WHERE size(members) >= $min_size
RETURN cluster_id,
       size(members) AS cluster_size,
       members
ORDER BY cluster_size DESC, cluster_id
"""
            cluster_exact = True
            try:
                with st.spinner("Finding connected clusters..."):
                    cluster_df = run_cypher(
                        cfg, cluster_cypher, cluster_params
                    )
            except Exception:
                cluster_exact = False
                try:
                    with st.spinner(
                        "APOC unavailable — using bounded expansion..."
                    ):
                        cluster_df = run_cypher(
                            cfg, fallback_cypher, cluster_params
                        )
                    st.warning(
                        "APOC is not available on this database, so clusters "
                        f"were built with a {int(cluster_depth)}-step bound "
                        "and very large components may be split. Record this "
                        "in the research log if these figures are used."
                    )
                    cluster_cypher = fallback_cypher
                except Exception as exc:
                    st.error(f"Cluster query failed: {exc}")
                    if SHOW_QUERIES:
                        st.code(cluster_cypher, language="cypher")
                    return
            if cluster_df.empty:
                st.warning(
                    "No cluster reached the smallest size you asked for "
                    f"({int(min_cluster_size)} LSOAs) with the current "
                    "settings, so there is nothing to draw. Lower "
                    "'Smallest cluster to show', or widen the pool — for "
                    "example add another deprivation level."
                )
                if SHOW_QUERIES:
                    st.code(cluster_cypher, language="cypher")
                return
            for member_list in cluster_df["members"]:
                cluster_codes.extend(list(member_list))
            cluster_codes = sorted(set(cluster_codes))
            conditions.append("l.code IN $cluster_codes")
            params["cluster_codes"] = cluster_codes

    non_metric_conditions = (
        base_conditions + conditions[len(base_conditions) + len(filtered_metric_props):]
    )
    missing_metric_schools = 0
    if filtered_metric_props:
        null_expression = " OR ".join(
            f"s.{prop} IS NULL" for prop in filtered_metric_props
        )
        missing_cypher = f"""
        MATCH (s:School)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(l:LSOA)
        WITH s, l
        WHERE {' AND '.join(non_metric_conditions)} AND ({null_expression})
        RETURN count(DISTINCT s) AS n
        """
        try:
            missing_metric_schools = int(
                scalar(cfg, missing_cypher, params, default=0) or 0
            )
        except Exception:
            missing_metric_schools = 0

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
           l.code AS lsoa_code,
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

    # INTERSECTS supplies the required AdminUnit-to-LSOA bridge and therefore
    # the candidate schools. The natural-language words in/inside, TOUCHES
    # and graph-near refer to administrative units, however, so retain only
    # school points contained by the selected target administrative geometry.
    # This prevents a school in the outside part of a crossing LSOA from being
    # reported as inside the administrative result.
    if admin_scope and not df.empty:
        scope_components = (
            admin_scope.get("components", [])
            if admin_scope.get("compound") else [admin_scope]
        )
        component_rings = [
            [
                ring
                for target_wkt in _admin_component_target_wkts(component)
                for ring in _wkt_rings(target_wkt)
            ]
            for component in scope_components
        ]
        if component_rings and all(component_rings):
            spatial_operator = admin_scope.get("operator", "AND")

            def row_matches_admin(row: pd.Series) -> bool:
                matches = [
                    _point_in_admin_rings(
                        row.get("longitude"), row.get("latitude"), rings
                    )
                    for rings in component_rings
                ]
                return any(matches) if spatial_operator == "OR" else all(matches)

            df = df[df.apply(row_matches_admin, axis=1)].copy()
            summary_df = pd.DataFrame([{
                "total_schools": int(len(df)),
                "near_transport_schools": int(
                    df.get("near_transport", pd.Series(dtype=bool))
                    .fillna(False).astype(bool).sum()
                ),
                "avg_fsm_pct": pd.to_numeric(
                    df.get("fsm_pct", pd.Series(dtype=float)), errors="coerce"
                ).mean(),
                "avg_attendance_pct": pd.to_numeric(
                    df.get("attendance_pct", pd.Series(dtype=float)),
                    errors="coerce",
                ).mean(),
            }])

    if admin_scope and admin_scope.get("compound"):
        operator = admin_scope.get("operator", "AND")
        component_lines: List[str] = []
        all_target_names: List[str] = []
        for component in admin_scope.get("components", []):
            component_anchor = component["anchor"]
            component_relation = component["relation"]
            component_target_type = escape(str(component["target_type"]))
            if component_relation == "direct":
                route = "→ INTERSECTS → LSOA ← LOCATED_IN ← School"
            elif component_relation == "touches":
                route = (
                    f"→ TOUCHES → neighbouring {component_target_type} "
                    "→ INTERSECTS → LSOA ← LOCATED_IN ← School"
                )
            else:
                route = (
                    f"→ TOUCHES → intermediate {component_target_type} "
                    f"→ TOUCHES → graph-near {component_target_type} "
                    "→ INTERSECTS → LSOA ← LOCATED_IN ← School"
                )
            component_lines.append(
                f"**{escape(component_relation)}:** "
                f"{escape(str(component_anchor.get('name')))} "
                f"({escape(str(component_anchor.get('unit_type')))}) {route} "
                "→ POINT_WITHIN → target administrative geometry"
            )
            component_units = component.get("units", pd.DataFrame())
            if isinstance(component_units, pd.DataFrame) and not component_units.empty:
                all_target_names.extend(
                    component_units.get("unit_name", pd.Series(dtype=str))
                    .dropna().astype(str).drop_duplicates().tolist()
                )
        st.markdown(
            f"{provenance_badge('Compound query')} "
            f"{provenance_badge('Geometry-on-demand')} "
            f"**Administrative scopes combined with {escape(operator)}:**<br>"
            + f"<br><b>{escape(operator)}</b><br>".join(component_lines),
            unsafe_allow_html=True,
        )
        st.caption(
            f"Boolean {operator} combines school membership in the resolved "
            "administrative scopes. INTERSECTS remains the LSOA bridge in "
            "each component; it is not the Boolean operator."
        )
        st.caption(
            f"{len(admin_scope.get('components', []))} administrative scopes; "
            f"{len(admin_scope.get('lsoa_codes', [])):,} candidate LSOAs after "
            f"the {operator} set operation."
        )
        if all_target_names:
            names = list(dict.fromkeys(all_target_names))
            st.caption(
                "Resolved target units: " + ", ".join(names[:10])
                + (f" … and {len(names) - 10} more" if len(names) > 10 else "")
            )
    elif admin_scope:
        anchor = admin_scope["anchor"]
        relation = admin_scope["relation"]
        target_type = escape(str(admin_scope["target_type"]))
        if relation == "direct":
            provenance = provenance_badge("Geometry-origin")
            relation_label = "→ INTERSECTS → LSOA ← LOCATED_IN ← School"
        elif relation == "touches":
            provenance = (
                provenance_badge("Native") + " "
                + provenance_badge("Geometry-origin")
            )
            relation_label = (
                f"→ TOUCHES → neighbouring {target_type} "
                "→ INTERSECTS → LSOA ← LOCATED_IN ← School"
            )
        else:
            provenance = (
                provenance_badge("Graph-derived") + " "
                + provenance_badge("Geometry-origin")
            )
            relation_label = (
                f"→ TOUCHES → intermediate {target_type} → TOUCHES → "
                f"graph-near {target_type} → INTERSECTS → LSOA "
                "← LOCATED_IN ← School"
            )
        provenance += " " + provenance_badge("Geometry-on-demand")
        relation_label += " → POINT_WITHIN → target administrative geometry"
        if any("DISTANCE_NEAR" in c for c in nl_map.get("conditions", [])):
            relation_label += " → DISTANCE_NEAR → TransportStop"

        units = admin_scope.get("units", pd.DataFrame())
        unique_units = (
            units[["unit_uri", "unit_name", "unit_type"]]
            .drop_duplicates("unit_uri")
            if isinstance(units, pd.DataFrame) and not units.empty
            else pd.DataFrame(columns=["unit_uri", "unit_name", "unit_type"])
        )
        unit_names = unique_units["unit_name"].dropna().astype(str).tolist()
        unit_count_label = (
            "1 selected administrative unit"
            if relation == "direct"
            else (
                f"{len(unique_units):,} target administrative unit"
                f"{'s' if len(unique_units) != 1 else ''}"
            )
        )
        scope_counts = (
            f"{unit_count_label}; "
            f"{len(admin_scope['lsoa_codes']):,} intersecting LSOAs."
        )
        st.markdown(
            f"{provenance} "
            f"**Cross-geography path:** {escape(str(anchor.get('name')))} "
            f"({escape(str(anchor.get('unit_type')))}) {relation_label}. "
            "INTERSECTS supplies the LSOA bridge; school points are then "
            "filtered to the target administrative geometry. This is not a "
            "claim that the administrative and statistical boundaries nest.",
            unsafe_allow_html=True,
        )
        st.caption(
            "Final spatial filter: school point must fall inside the selected "
            "target administrative unit. Schools in only the outside portion "
            "of an intersecting LSOA are excluded."
        )
        st.caption(scope_counts)
        if relation == "touches":
            st.caption(
                "Administrative scope: one TOUCHES step. Shared LSOAs remain "
                "bridge candidates; final membership is decided by the "
                "school point inside the touching target unit."
            )
        elif relation == "graph_near":
            st.caption(
                "Administrative scope: exactly two TOUCHES steps; the source "
                "and its direct neighbours are excluded. Shared LSOAs remain "
                "bridge candidates; final membership is decided by the "
                "school point inside the graph-near target unit."
            )
        if unit_names:
            shown = ", ".join(unit_names[:8])
            st.caption(
                "Target unit" + ("s" if len(unit_names) != 1 else "")
                + ": " + shown
                + (f" … and {len(unit_names) - 8} more" if len(unit_names) > 8 else "")
            )

    summary = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    total_schools = int(summary.get("total_schools") or 0)
    near_transport_count = int(summary.get("near_transport_schools") or 0)

    if filtered_metric_props:
        if include_missing_metrics:
            st.caption(
                f"Missing values kept: {missing_metric_schools:,} schools have "
                "no value for at least one filtered metric and are still shown."
            )
        elif missing_metric_schools:
            st.caption(
                f"Note: {missing_metric_schools:,} schools are not shown "
                "because they have no value for a filtered metric (special "
                "schools are usually in this group) — removed for a missing "
                "value, not for failing the range."
            )

    if search_mode == "Cluster search" and not cluster_df.empty:
        st.markdown(
            f"{provenance_badge('Geometry-origin')} "
            f"**{len(cluster_df):,} adjacency clusters** covering "
            f"**{len(cluster_codes):,} LSOAs** — pool: "
            f"{cluster_pool_label}"
            + (
                ", exact connected components."
                if cluster_exact
                else f", bounded at {int(cluster_depth)} steps."
            ),
            unsafe_allow_html=True,
        )

    if df.empty:
        st.info("No rows with coordinates after filtering.")
        if SHOW_QUERIES:
            st.code(cypher, language="cypher")
        return

    map_df = df.copy()
    map_df["latitude"] = pd.to_numeric(map_df["latitude"], errors="coerce")
    map_df["longitude"] = pd.to_numeric(map_df["longitude"], errors="coerce")
    map_df = map_df.dropna(subset=["latitude", "longitude"])
    if band_map:
        map_df["cluster_band"] = (
            map_df["lsoa_code"].astype(str).map(band_map).fillna("band_none")
        )
        band_counts = map_df["cluster_band"].value_counts()
        st.markdown(
            f"{provenance_badge('Geometry-origin')} "
            f"**All severity bands** — {band_label}. Schools: "
            f"<span style='color:#e11d48;font-weight:800'>"
            f"{int(band_counts.get('band_red', 0)):,} red</span> · "
            f"<span style='color:#ff8a00;font-weight:800'>"
            f"{int(band_counts.get('band_mid', 0)):,} orange</span> · "
            f"<span style='color:#22c55e;font-weight:800'>"
            f"{int(band_counts.get('band_green', 0)):,} green</span> · "
            f"{int(band_counts.get('band_none', 0)):,} without a value.",
            unsafe_allow_html=True,
        )
        if SHOW_QUERIES:
            with st.expander("Band Cypher"):
                st.code(band_cypher, language="cypher")
                st.json({"c1": float(band_cut1), "c2": float(band_cut2)})
    if map_df.empty:
        st.info("No rows with valid map coordinates after filtering.")
        if SHOW_QUERIES:
            st.code(cypher, language="cypher")
        return

    polygon_df = None
    admin_polygon_df = None
    if admin_scope:
        admin_rows: List[Dict[str, Any]] = []
        map_components = (
            admin_scope.get("components", [])
            if admin_scope.get("compound") else [admin_scope]
        )
        for component in map_components:
            component_anchor = component["anchor"]
            admin_rows.append({
                "uri": component_anchor.get("uri"),
                "name": component_anchor.get("name"),
                "unit_type": component_anchor.get("unit_type"),
                "wkt": component_anchor.get("wkt"),
                "role": "anchor",
            })
            units = component.get("units")
            if isinstance(units, pd.DataFrame) and not units.empty:
                for _, unit in units.drop_duplicates(subset=["unit_uri"]).iterrows():
                    if str(unit.get("unit_uri")) == str(component_anchor.get("uri")):
                        continue
                    admin_rows.append({
                        "uri": unit.get("unit_uri"),
                        "name": unit.get("unit_name"),
                        "unit_type": unit.get("unit_type"),
                        "wkt": unit.get("unit_wkt"),
                        "role": "result",
                    })
        admin_polygon_df = pd.DataFrame(admin_rows).drop_duplicates(
            subset=["uri", "role"]
        )
    if search_mode == "Standard search" and "lsoa_code" in map_df.columns:
        # The pins say where the schools are; the boundaries say what kind of
        # place each sits in. Drawn underneath and left unpickable, so the
        # pins keep their tooltips and the areas only supply the background.
        std_codes = sorted(
            {str(c) for c in map_df["lsoa_code"].dropna() if str(c)}
        )
        POLY_CAP = 600
        if std_codes:
            capped = std_codes[:POLY_CAP]
            try:
                polygon_df = cluster_polygons(
                    (cfg["uri"], cfg["user"], cfg["password"],
                     cfg["database"]),
                    tuple(capped),
                )
                if polygon_df is not None and not polygon_df.empty:
                    if "deprivation" not in polygon_df.columns:
                        dep_by_code = dict(
                            zip(
                                map_df["lsoa_code"].astype(str),
                                map_df.get(
                                    "deprivation",
                                    pd.Series(["unknown"] * len(map_df)),
                                ).astype(str),
                            )
                        )
                        polygon_df = polygon_df.assign(
                            deprivation=polygon_df["code"].astype(str).map(
                                dep_by_code
                            ).fillna("unknown")
                        )
                    if len(std_codes) > POLY_CAP:
                        st.caption(
                            f"Boundaries drawn for {POLY_CAP:,} of "
                            f"{len(std_codes):,} areas; the pins and the "
                            "table are the full answer."
                        )
                else:
                    polygon_df = None
            except Exception as exc:
                polygon_df = None
                st.caption(f"Area boundaries unavailable: {exc}")

    if search_mode == "Cluster search" and cluster_codes:
        size_by_code: Dict[str, int] = {}
        for _, crow in cluster_df.iterrows():
            for member in crow["members"]:
                size_by_code[str(member)] = int(crow["cluster_size"])
        try:
            polygon_df = cluster_polygons(
                (cfg["uri"], cfg["user"], cfg["password"], cfg["database"]),
                tuple(cluster_codes),
            )
            if not polygon_df.empty:
                summary_rows = []
                for code, grp in map_df.groupby(map_df["lsoa_code"].astype(str)):
                    # School names are no longer gathered here: the hover
                    # card must not grow with the number of schools, so
                    # identities live in the panel opened below the map.
                    fsm_vals = pd.to_numeric(
                        grp["fsm_pct"] if "fsm_pct" in grp.columns
                        else pd.Series(dtype=float),
                        errors="coerce",
                    )
                    att_vals = pd.to_numeric(
                        grp["attendance_pct"] if "attendance_pct" in grp.columns
                        else pd.Series(dtype=float),
                        errors="coerce",
                    )
                    n_fsm = int(fsm_vals.notna().sum())
                    n_att = int(att_vals.notna().sum())
                    # 73% of Welsh LSOAs hold exactly one school, so a
                    # "mean" is often a single value. The basis is stated
                    # rather than left to be assumed.
                    basis = (
                        f"FSM from {n_fsm} school"
                        + ("s" if n_fsm != 1 else "")
                        + f", attendance from {n_att}"
                        + " \u00b7 open the area below for the schools"
                    )
                    summary_rows.append(
                        {
                            "code": code,
                            "schools_count": int(len(grp)),
                            "schools_basis": basis,
                            "fsm_avg": (
                                f"{fsm_vals.mean():.1f}%"
                                if fsm_vals.notna().any()
                                else "N/A"
                            ),
                            "att_avg": (
                                f"{att_vals.mean():.1f}%"
                                if att_vals.notna().any()
                                else "N/A"
                            ),
                        }
                    )
                summary_df = pd.DataFrame(
                    summary_rows,
                    columns=[
                        "code",
                        "schools_count",
                        "schools_basis",
                        "fsm_avg",
                        "att_avg",
                    ],
                )
                polygon_df = polygon_df.assign(
                    cluster_size=polygon_df["code"].astype(str).map(size_by_code)
                ).merge(summary_df, on="code", how="left")
                polygon_df["schools_count"] = (
                    polygon_df["schools_count"].fillna(0).astype(int)
                )
                polygon_df["schools_basis"] = polygon_df[
                    "schools_basis"
                ].fillna("No school inside this LSOA")
                polygon_df["fsm_avg"] = polygon_df["fsm_avg"].fillna("N/A")
                polygon_df["att_avg"] = polygon_df["att_avg"].fillna("N/A")
        except Exception as exc:
            polygon_df = None
            st.warning(
                "Cluster regions could not be drawn, so school pins are "
                f"shown instead. Reason: {exc}"
            )

    cluster_only = bool(
        search_mode == "Cluster search"
        and polygon_df is not None
        and not polygon_df.empty
    )
    if search_mode == "Cluster search" and not cluster_only:
        wkt_count = int(
            scalar(
                cfg,
                "MATCH (l:LSOA) WHERE l.wkt IS NOT NULL RETURN count(l)",
                default=0,
            )
            or 0
        )
        if wkt_count == 0:
            st.error(
                "This database has no LSOA boundary geometry (l.wkt), so "
                "cluster regions cannot be drawn and school pins are shown "
                "instead. The boundary load ran on the other database — run "
                "the LSOA geometry step of load_to_neo4j.py against this one."
            )
        else:
            st.info(
                f"{wkt_count:,} LSOAs carry boundary geometry, but none of "
                "the current cluster members returned a polygon. Showing "
                "school pins instead."
            )
    if cluster_only:
        st.caption(
            "Cluster regions are shaded by deprivation level. Hover a region "
            "for its counts and averages, then click it to see the schools "
            "by name. School pins return in Standard search."
        )
    edit_left, edit_mid, edit_right = st.columns([5, 1.35, 5])
    with edit_mid:
        st.button(
            "Back to filters", key="map_edit_search", use_container_width=True,
            type="primary",
            on_click=edit_map_search,
        )
    st.markdown("<div id='school-map-results'></div>", unsafe_allow_html=True)
    if st.session_state.pop("map_scroll_to_results", False):
        components.html(
            """
            <script>
            let attempts = 0;
            const timer = setInterval(() => {
              const doc = window.parent.document;
              const target = doc.querySelector('[data-testid="stDeckGlJsonChart"]');
              attempts += 1;
              if (target) {
                target.scrollIntoView({behavior:'smooth', block:'start'});
                clearInterval(timer);
              } else if (attempts > 40) {
                clearInterval(timer);
              }
            }, 100);
            </script>
            """,
            height=0,
        )
    clicked_region = render_school_map(
        map_df, selected_school, polygon_df, cluster_only, admin_polygon_df
    )
    if clicked_region:
        render_lsoa_school_panel(cfg, clicked_region)

    def result_range(column: str, suffix: str = "") -> Tuple[str, int]:
        values = pd.to_numeric(
            map_df.get(column, pd.Series(dtype=float)), errors="coerce"
        ).dropna()
        if values.empty:
            return "N/A", 0
        return f"{values.min():.1f}–{values.max():.1f}{suffix}", int(len(values))

    fsm_range, fsm_basis = result_range("fsm_pct", "%")
    attendance_range, attendance_basis = result_range("attendance_pct", "%")
    capped_range, capped_basis = result_range("capped9_score", " points")
    st.markdown(
        "<div class='school-results-title'>Result summary</div>",
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Matching schools", f"{len(map_df):,}")
    m2.metric("FSM range", fsm_range)
    m3.metric("Attendance range", attendance_range)
    m4.metric("Capped 9 range", capped_range)
    st.markdown(
        "<div class='results-basis'>"
        f"FSM range uses {fsm_basis:,} of {len(map_df):,} schools · "
        f"attendance uses {attendance_basis:,} of {len(map_df):,} · "
        f"Capped 9 uses {capped_basis:,} of {len(map_df):,} and is a points "
        "score for secondary schools, not a percentage. "
        f"Deprivation filter: {escape(str(dep_label))} · "
        f"schools with a transport stop within 800m: {near_transport_count:,}."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='school-results-title'>Schools in this map</div>",
        unsafe_allow_html=True,
    )
    school_table_columns = [
        c for c in (
            "school", "school_type", "local_authority", "lsoa_code",
            "deprivation", "fsm_pct", "attendance_pct", "capped9_score",
            "nearest_stop_distance_m",
        ) if c in map_df.columns
    ]
    school_table = map_df[school_table_columns].rename(columns={
        "school": "School",
        "school_type": "Phase",
        "local_authority": "Local authority",
        "lsoa_code": "LSOA",
        "deprivation": "Deprivation",
        "fsm_pct": "FSM (%)",
        "attendance_pct": "Attendance (%)",
        "capped9_score": "Capped 9 (points)",
        "nearest_stop_distance_m": "Nearest stop (m)",
    })
    if "Deprivation" in school_table.columns:
        school_table["Deprivation"] = school_table["Deprivation"].map({
            "high_deprivation": "High",
            "medium_deprivation": "Medium",
            "low_deprivation": "Low",
            "unknown": "Unknown",
        }).fillna(school_table["Deprivation"])
    for numeric_column in (
        "FSM (%)", "Attendance (%)", "Capped 9 (points)", "Nearest stop (m)"
    ):
        if numeric_column in school_table.columns:
            school_table[numeric_column] = pd.to_numeric(
                school_table[numeric_column], errors="coerce"
            ).round(1)
    st.dataframe(
        warm_table(school_table), use_container_width=True, hide_index=True,
        height=min(560, 44 + 35 * min(len(school_table), 14)),
        key="map_school_results_table",
    )

    if search_mode == "Cluster search" and not cluster_df.empty:
        with st.expander(
            f"Cluster results — {len(cluster_df):,} clusters, "
            f"{len(cluster_codes):,} LSOAs",
            expanded=False,
        ):
            st.caption(
                "An adjacency cluster is a connected group of LSOAs that "
                "all meet the threshold and are joined by computed "
                "LSOA_TOUCHES edges. "
                + (
                    "Clusters are exact connected components — the whole "
                    "component is explored, with no depth limit. "
                    if cluster_exact
                    else f"APOC was unavailable, so a "
                    f"{int(cluster_depth)}-step bound was used. "
                )
                + "It is not the statistical cluster "
                "used by Sandu et al., which comes from a Moran's I "
                "spatial-weights matrix and stays outside the completeness "
                "scoring."
            )
            display_df(
                cluster_df.assign(
                    members=cluster_df["members"].apply(
                        lambda codes: ", ".join(list(codes)[:8])
                        + (" ..." if len(codes) > 8 else "")
                    )
                )
            )
            if SHOW_QUERIES:
                st.code(cluster_cypher, language="cypher")
                st.json(cluster_params)

    if SHOW_QUERIES:
        with st.expander("Map Cypher"):
            st.code(cypher, language="cypher")
            st.json(params)


def main() -> None:
    cfg = sidebar_config()
    apply_dashboard_theme(False)
    page = cfg.pop("page")
    # Each page is drawn inside its own keyed container. Without this the
    # pages share element slots, so a widget from the previous page
    # can survive the switch and paint over the new one -- which is what put
    # the Evaluation page's SpCom equation underneath the map search box.
    try:
        body = st.container(key=f"page_{page.replace(' ', '_').lower()}")
    except TypeError:
        # Older Streamlit builds take no key; the container still isolates
        # the subtree, only without the stable identity.
        body = st.container()
    with body:
        render_page_switcher(page)
        if page == "SCQ Demonstrator":
            page_guided_spatial_search(cfg)
        elif page == "Map":
            page_map(cfg)


if __name__ == "__main__":
    main()
