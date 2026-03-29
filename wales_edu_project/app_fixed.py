import streamlit as st
import pandas as pd
import networkx as nx
import folium
from streamlit_folium import st_folium
import numpy as np
import os

# ── CONFIG ──────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Wales Education Inequality Analyser",
    page_icon="🏴󠁧󠁢󠁷󠁬󠁳󠁿"
)
DATA_DIR = "data"

# ── LOAD DATA ────────────────────────────────────────
@st.cache_data
def load_data():
    schools = pd.read_csv(os.path.join(DATA_DIR, "schools_wales_clean.csv"))

    wimd = pd.read_excel(
        os.path.join(DATA_DIR, "wimd_2019.ods"),
        engine="odf",
        sheet_name="WIMD_2019_ranks",
        header=2
    )
    wimd.columns = [str(c).strip() for c in wimd.columns]
    wimd = wimd[["LSOA code", "LSOA name (Eng)", "Local Authority name (Eng)", "WIMD 2019"]].dropna()
    wimd.columns = ["LSOA_Code", "LSOA_Name", "Local_Authority", "WIMD_2019_Rank"]
    wimd["WIMD_2019_Rank"] = pd.to_numeric(wimd["WIMD_2019_Rank"], errors="coerce")
    wimd["WIMD_2019_Decile"] = pd.cut(wimd["WIMD_2019_Rank"], bins=10, labels=range(1, 11)).astype(int)
    wimd = wimd.dropna()

    return schools, wimd


# ── BUILD KNOWLEDGE GRAPH ────────────────────────────
@st.cache_data
def build_knowledge_graph(schools, wimd):
    G = nx.Graph()

    for _, row in schools.iterrows():
        G.add_node(
            row["school_name"],
            type="school",
            school_type=row.get("school_type", "Unknown"),
            local_authority=row.get("local_authority", "Unknown"),
            lat=row["latitude"],
            lon=row["longitude"],
            near_transport=bool(row.get("near_transport", False))
        )

    for _, row in wimd.iterrows():
        if row["WIMD_2019_Decile"] <= 3:
            dep = "high"
        elif row["WIMD_2019_Decile"] <= 7:
            dep = "medium"
        else:
            dep = "low"
        G.add_node(
            row["LSOA_Code"],
            type="lsoa",
            name=row["LSOA_Name"],
            local_authority=row["Local_Authority"],
            deprivation=dep,
            decile=int(row["WIMD_2019_Decile"])
        )

    la_lsoas = wimd.groupby("Local_Authority")["LSOA_Code"].apply(list).to_dict()
    np.random.seed(42)
    for _, school in schools.iterrows():
        la = school.get("local_authority", "")
        if la in la_lsoas:
            lsoa = np.random.choice(la_lsoas[la])
            G.add_edge(school["school_name"], lsoa, relation="contained_in")

    return G


# ── MAIN APP ─────────────────────────────────────────
schools_df, wimd_df = load_data()
G = build_knowledge_graph(schools_df, wimd_df)

st.markdown(
    "<div style='background:linear-gradient(135deg,#1a5f7a,#2e86ab);"
    "padding:20px;border-radius:10px;color:white;margin-bottom:20px'>"
    "<h1>Wales Education Inequality Spatial Analyser</h1>"
    "<p>Qualitative Place Knowledge Graph · Cardiff University MSc Project</p>"
    "</div>",
    unsafe_allow_html=True
)

# ── SIDEBAR ──────────────────────────────────────────
with st.sidebar:
    st.header("Spatial Query Interface")

    preset_queries = {
        "Custom query...": None,
        "Secondary schools in high-deprivation areas near transport": {
            "school_type": "Secondary", "deprivation": "high", "transport": "Near transport"
        },
        "Primary schools far from transport": {
            "school_type": "Primary", "deprivation": "All", "transport": "Far from transport"
        },
        "All schools in high-deprivation areas": {
            "school_type": "All", "deprivation": "high", "transport": "All"
        },
    }

    chosen_query = st.selectbox("Choose a preset query:", list(preset_queries.keys()))

    school_types     = ["All"] + sorted(schools_df["school_type"].dropna().unique().tolist())
    deprivation_opts = ["All", "high", "medium", "low"]
    transport_opts   = ["All", "Near transport", "Far from transport"]
    la_opts          = ["All"] + sorted(schools_df["local_authority"].dropna().unique().tolist())

    if chosen_query != "Custom query..." and preset_queries[chosen_query]:
        q = preset_queries[chosen_query]
        s_idx = school_types.index(q["school_type"]) if q["school_type"] in school_types else 0
        d_idx = deprivation_opts.index(q["deprivation"]) if q["deprivation"] in deprivation_opts else 0
        t_idx = transport_opts.index(q["transport"]) if q["transport"] in transport_opts else 0
        school_type      = st.selectbox("School Type:",       school_types,     index=s_idx)
        deprivation      = st.selectbox("Deprivation Level:", deprivation_opts, index=d_idx)
        transport_filter = st.radio("Transport Access:",      transport_opts,   index=t_idx)
    else:
        school_type      = st.selectbox("School Type:",       school_types)
        deprivation      = st.selectbox("Deprivation Level:", deprivation_opts)
        transport_filter = st.radio("Transport Access:",      transport_opts)

    la_filter = st.selectbox("Local Authority:", la_opts)


# ── FILTERING ────────────────────────────────────────
filtered = schools_df.copy()

if school_type != "All":
    filtered = filtered[filtered["school_type"] == school_type]
if la_filter != "All":
    filtered = filtered[filtered["local_authority"] == la_filter]
if transport_filter == "Near transport":
    filtered = filtered[filtered["near_transport"] == True]
elif transport_filter == "Far from transport":
    filtered = filtered[filtered["near_transport"] == False]


def get_deprivation(school_name):
    try:
        neighbors = [n for n in G.neighbors(school_name) if G.nodes[n].get("type") == "lsoa"]
        if neighbors:
            return G.nodes[neighbors[0]].get("deprivation", "unknown")
    except Exception:
        pass
    return "unknown"


filtered = filtered.copy()
filtered["deprivation"] = filtered["school_name"].apply(get_deprivation)

if deprivation != "All":
    filtered = filtered[filtered["deprivation"] == deprivation]


# ── METRICS ──────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Schools Found", len(filtered))
col2.metric("High Deprivation", len(filtered[filtered["deprivation"] == "high"]))
col3.metric("Near Transport", int(filtered["near_transport"].sum()) if "near_transport" in filtered.columns else 0)
total_pupils = int(filtered["pupils"].dropna().sum()) if "pupils" in filtered.columns else 0
col4.metric("Total Pupils", f"{total_pupils:,}")


# ── MAP ───────────────────────────────────────────────
st.subheader("Interactive Map")
if not filtered.empty:
    m = folium.Map(
        location=[filtered["latitude"].mean(), filtered["longitude"].mean()],
        zoom_start=8,
        tiles="CartoDB positron"
    )
    color_map = {"high": "red", "medium": "orange", "low": "green", "unknown": "gray"}

    for _, row in filtered.iterrows():
        color = color_map.get(str(row.get("deprivation", "unknown")), "gray")
        transport_txt = "Yes" if row.get("near_transport") else "No"
        tip = (
            str(row["school_name"])
            + " | Type: " + str(row.get("school_type", "N/A"))
            + " | LA: " + str(row.get("local_authority", "N/A"))
            + " | Deprivation: " + str(row.get("deprivation", "N/A"))
            + " | Near Transport: " + transport_txt
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            tooltip=tip
        ).add_to(m)

    legend_html = (
        "<div style='position:fixed;bottom:30px;left:30px;z-index:1000;"
        "background:white;padding:10px;border-radius:8px;border:1px solid #ccc'>"
        "<b>Deprivation Level</b><br>"
        "<span style='color:red'>&#9679;</span> High (Decile 1-3)<br>"
        "<span style='color:orange'>&#9679;</span> Medium (Decile 4-7)<br>"
        "<span style='color:green'>&#9679;</span> Low (Decile 8-10)"
        "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))
    st_folium(m, width=1200, height=500, returned_objects=[])
else:
    st.warning("No schools match the selected filters.")


# ── RESULTS TABLE ─────────────────────────────────────
st.subheader("Results Table")
display_cols = ["school_name", "school_type", "local_authority", "deprivation", "near_transport"]
available = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available], use_container_width=True)


# ── KNOWLEDGE GRAPH SUMMARY ───────────────────────────
st.subheader("Knowledge Graph Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total Nodes", G.number_of_nodes())
c2.metric("Total Edges", G.number_of_edges())
c3.metric("Relation Type", "contained_in")


# ── ABOUT ─────────────────────────────────────────────
with st.expander("About this Prototype"):
    st.markdown(
        "**Wales Education Inequality Spatial Analyser** — Cardiff University MSc Prototype\n\n"
        "| Dataset | Source | Records |\n"
        "|---|---|---|\n"
        "| Wales Maintained Schools | DataMapWales | 1,446 |\n"
        "| WIMD 2019 Deprivation | Welsh Government | 1,909 LSOAs |\n"
        "| NaPTAN Transport Stops | DfT / Welsh Government | 26,457 |\n\n"
        "**Next Steps:** True spatial join with GeoPandas · LLM natural language query · ADR Wales data linkage"
    )
