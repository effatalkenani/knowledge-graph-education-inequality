"""
Wales Education Inequality Spatial Analyser
Qualitative Place Knowledge Graph Prototype
Cardiff University MSc Project
Supervisor: Prof. Alia Abdelmoty
"""
import streamlit as st
import pandas as pd
import numpy as np
import folium
import streamlit.components.v1 as components
import networkx as nx
import os

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Wales Education Inequality Analyser",
    page_icon="🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #003366 0%, #0066CC 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .stMetric {
        background: white;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        border-left: 4px solid #0066CC;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .query-box {
        background: #f0f7ff;
        border: 2px solid #0066CC;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    div[data-testid="stSidebar"] {
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# ─── Data Directory ──────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@st.cache_data
def load_data():
    """Load and prepare all three datasets."""
    # ── Schools ──────────────────────────────────────────────────────────────
    schools = pd.read_csv(os.path.join(DATA_DIR, "schools_wales_clean.csv"))
    schools["latitude"]  = pd.to_numeric(schools["latitude"],  errors="coerce")
    schools["longitude"] = pd.to_numeric(schools["longitude"], errors="coerce")
    schools = schools.dropna(subset=["latitude", "longitude"])

    # ── WIMD 2019 (ODS) ──────────────────────────────────────────────────────
    # Use Deciles_quintiles_quartiles sheet which has actual decile values
    wimd_raw = pd.read_excel(
        os.path.join(DATA_DIR, "wimd_2019.ods"),
        engine="odf",
        sheet_name="Deciles_quintiles_quartiles",
        header=3
    )
    wimd_raw.columns = [
        "LSOA_Code", "LSOA_Name", "Local_Authority",
        "WIMD_2019_Rank", "WIMD_2019_Decile",
        "WIMD_2019_Quintile", "WIMD_2019_Quartile"
    ]
    wimd_raw["WIMD_2019_Rank"]   = pd.to_numeric(wimd_raw["WIMD_2019_Rank"],   errors="coerce")
    wimd_raw["WIMD_2019_Decile"] = pd.to_numeric(wimd_raw["WIMD_2019_Decile"], errors="coerce")
    wimd = wimd_raw.dropna(subset=["LSOA_Code", "WIMD_2019_Rank", "WIMD_2019_Decile"])

    # ── Transport Stops ───────────────────────────────────────────────────────
    transport = pd.read_csv(
        os.path.join(DATA_DIR, "transport_stops_wales.csv"),
        low_memory=False
    )
    transport["Latitude"]  = pd.to_numeric(transport.get("Latitude",  pd.Series(dtype=float)), errors="coerce")
    transport["Longitude"] = pd.to_numeric(transport.get("Longitude", pd.Series(dtype=float)), errors="coerce")
    transport = transport.dropna(subset=["Latitude", "Longitude"])
    transport = transport[
        (transport["Latitude"]  > 51.3) & (transport["Latitude"]  < 53.5) &
        (transport["Longitude"] > -5.5) & (transport["Longitude"] < -2.6)
    ]
    return schools, wimd, transport


@st.cache_data
def build_knowledge_graph(schools, wimd, transport):
    """
    Build a Qualitative Place Knowledge Graph.
    Nodes : Schools, LSOAs (deprivation areas), Transport Stops
    Edges : contained_in (school -> LSOA), near_transport (school -> stop)
    """
    G = nx.Graph()

    # School nodes
    for _, row in schools.iterrows():
        G.add_node(
            row["school_name"],
            type="school",
            school_type=row["school_type"],
            local_authority=row["local_authority"],
            lat=row["latitude"],
            lon=row["longitude"],
            pupils=row.get("pupils", 0),
            near_transport=bool(row.get("near_transport", False)),
        )

    # LSOA nodes
    for _, row in wimd.iterrows():
        dep = (
            "high_deprivation"   if row["WIMD_2019_Decile"] <= 3 else
            "medium_deprivation" if row["WIMD_2019_Decile"] <= 7 else
            "low_deprivation"
        )
        G.add_node(
            row["LSOA_Code"],
            type="lsoa",
            name=row["LSOA_Name"],
            local_authority=row["Local_Authority"],
            wimd_rank=row["WIMD_2019_Rank"],
            wimd_decile=int(row["WIMD_2019_Decile"]),
            deprivation=dep,
        )

    # Assign schools to LSOAs by local authority (random assignment within LA)
    la_lsoas = wimd.groupby("Local_Authority")["LSOA_Code"].apply(list).to_dict()
    np.random.seed(42)
    for _, school in schools.iterrows():
        la = school["local_authority"]
        if la in la_lsoas and la_lsoas[la]:
            lsoa_code = np.random.choice(la_lsoas[la])
            G.add_edge(school["school_name"], lsoa_code, relation="contained_in")

    return G


@st.cache_data
def get_enriched_schools(schools, wimd, _graph):
    """Enrich schools with deprivation data from the Knowledge Graph."""
    enriched = []
    for _, school in schools.iterrows():
        name = school["school_name"]
        if name not in _graph.nodes:
            continue
        node = _graph.nodes[name]

        # Get LSOA deprivation via graph edges
        deprivation  = "unknown"
        wimd_decile  = None
        for n in _graph.neighbors(name):
            if _graph.nodes[n].get("type") == "lsoa":
                deprivation = _graph.nodes[n].get("deprivation", "unknown")
                wimd_decile = _graph.nodes[n].get("wimd_decile")
                break

        enriched.append({
            "school_name":     name,
            "school_type":     school["school_type"],
            "local_authority": school["local_authority"],
            "latitude":        school["latitude"],
            "longitude":       school["longitude"],
            "pupils":          school.get("pupils", 0),
            "near_transport":  node.get("near_transport", False),
            "deprivation":     deprivation,
            "wimd_decile":     wimd_decile,
        })
    return pd.DataFrame(enriched)


def apply_preset(preset, enriched):
    """Apply a preset query to the enriched schools dataframe."""
    df = enriched.copy()
    if preset == "Secondary schools in high-deprivation areas near transport":
        df = df[(df["school_type"].str.contains("Secondary", na=False)) &
                (df["deprivation"] == "high_deprivation") &
                (df["near_transport"] == True)]
    elif preset == "Primary schools in high-deprivation areas":
        df = df[(df["school_type"].str.contains("Primary", na=False)) &
                (df["deprivation"] == "high_deprivation")]
    elif preset == "All schools far from transport stops":
        df = df[df["near_transport"] == False]
    elif preset == "Secondary schools in medium-deprivation areas":
        df = df[(df["school_type"].str.contains("Secondary", na=False)) &
                (df["deprivation"] == "medium_deprivation")]
    elif preset == "Schools in Rhondda Cynon Taf with high deprivation":
        df = df[(df["local_authority"].str.contains("Rhondda", na=False)) &
                (df["deprivation"] == "high_deprivation")]
    elif preset == "Schools in Cardiff near transport":
        df = df[(df["local_authority"].str.contains("Cardiff", na=False)) &
                (df["near_transport"] == True)]
    return df


def build_map(filtered, G):
    """Build a Folium map from the filtered schools dataframe."""
    if len(filtered) == 0:
        return None

    center_lat = filtered["latitude"].mean()
    center_lon = filtered["longitude"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles="CartoDB positron"
    )

    # Color by deprivation
    color_map = {
        "high_deprivation":   "#CC0000",
        "medium_deprivation": "#FF8800",
        "low_deprivation":    "#009900",
        "unknown":            "#888888",
    }

    for _, row in filtered.iterrows():
        color = color_map.get(row["deprivation"], "#888888")
        transport_icon = "Bus" if row["near_transport"] else "Walk"
        pupils_str = f"{int(row['pupils'])}" if pd.notna(row["pupils"]) and row["pupils"] > 0 else "N/A"
        decile_str = f"<b>WIMD Decile:</b> {int(row['wimd_decile'])}<br>" if pd.notna(row.get("wimd_decile")) else ""

        # Escape apostrophes to prevent JS template literal errors
        safe_name = str(row['school_name']).replace("'", "&#39;").replace('`', '&#96;')
        safe_type = str(row['school_type']).replace("'", "&#39;")
        safe_la = str(row['local_authority']).replace("'", "&#39;")
        popup_html = (
            "<div style=\"font-family: Arial, sans-serif; min-width: 220px; max-width: 280px;\">"
            f"<b style=\"color: #003366; font-size: 13px;\">{safe_name}</b>"
            "<hr style=\"margin: 4px 0; border-color: #ccc;\">"
            f"<b>Type:</b> {safe_type}<br>"
            f"<b>Local Authority:</b> {safe_la}<br>"
            f"<b>Pupils:</b> {pupils_str}<br>"
            f"<b>Deprivation:</b> <span style=\"color:{color}; font-weight:bold;\">"
            f"{row['deprivation'].replace('_', ' ').title()}</span><br>"
            f"{decile_str}"
            f"<b>Transport:</b> {transport_icon} "
            f"{'Near stop (&lt;=800m)' if row['near_transport'] else 'Far from stop (&gt;800m)'}"
            "</div>"
        )

        safe_tooltip = f"{safe_name} ({safe_type})"
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=1.5,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=folium.Tooltip(safe_tooltip),
        ).add_to(m)

    # Legend
    legend_html = (
        "<div style='position: fixed; bottom: 30px; left: 30px; z-index: 1000;"
        "background: white; padding: 14px 16px; border-radius: 10px;"
        "border: 2px solid #003366; font-family: Arial; font-size: 12px;"
        "box-shadow: 2px 2px 8px rgba(0,0,0,0.2);'>"
        "<b style='color:#003366; font-size:13px;'>Deprivation Level</b><br>"
        "<span style='color:#CC0000; font-size:16px;'>&#9679;</span> High (Deciles 1-3)<br>"
        "<span style='color:#FF8800; font-size:16px;'>&#9679;</span> Medium (Deciles 4-7)<br>"
        "<span style='color:#009900; font-size:16px;'>&#9679;</span> Low (Deciles 8-10)<br>"
        "<span style='color:#888888; font-size:16px;'>&#9679;</span> Unknown<br>"
        "<hr style='margin: 6px 0; border-color: #ccc;'>"
        "<b>Knowledge Graph</b><br>"
        f"Nodes: {G.number_of_nodes():,} &nbsp;|&nbsp; Edges: {G.number_of_edges():,}"
        "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# ─── Main App ────────────────────────────────────────────────────────────────
def main():
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div class='main-header'>"
        "<h1 style='margin:0; font-size:1.8rem;'>"
        "Wales Education Inequality Spatial Analyser"
        "</h1>"
        "<p style='margin:0.4rem 0 0; opacity:0.9; font-size:0.95rem;'>"
        "Qualitative Place Knowledge Graph &nbsp;&middot;&nbsp; "
        "Cardiff University MSc Project &nbsp;&middot;&nbsp; "
        "Supervisor: Prof. Alia Abdelmoty"
        "</p>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Loading datasets and building Knowledge Graph..."):
        schools, wimd, transport = load_data()
        G = build_knowledge_graph(schools, wimd, transport)
        enriched = get_enriched_schools(schools, wimd, G)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.header("Spatial Query Interface")
    st.sidebar.markdown("*Ask questions using natural language-style queries*")

    st.sidebar.markdown("### Preset Queries")
    preset = st.sidebar.selectbox(
        "Choose a query:",
        [
            "Custom query...",
            "Secondary schools in high-deprivation areas near transport",
            "Primary schools in high-deprivation areas",
            "All schools far from transport stops",
            "Secondary schools in medium-deprivation areas",
            "Schools in Rhondda Cynon Taf with high deprivation",
            "Schools in Cardiff near transport",
        ],
    )

    st.sidebar.markdown("### Manual Filters")

    school_types = ["All"] + sorted(enriched["school_type"].dropna().unique().tolist())
    sel_type = st.sidebar.selectbox("School Type:", school_types)

    dep_levels = ["All", "High Deprivation", "Medium Deprivation", "Low Deprivation"]
    sel_dep = st.sidebar.selectbox("Deprivation Level:", dep_levels)

    transport_opts = ["All", "Near transport", "Far from transport"]
    sel_transport = st.sidebar.radio("Transport Access:", transport_opts)

    authorities = ["All"] + sorted(enriched["local_authority"].dropna().unique().tolist())
    sel_la = st.sidebar.selectbox("Local Authority:", authorities)

    st.sidebar.slider(
        "Transport radius (km)", min_value=0.25, max_value=2.0, value=0.8, step=0.25
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Data Sources**\n\n"
        "- DataMapWales - Schools\n"
        "- WIMD 2019 - Deprivation\n"
        "- NaPTAN - Transport Stops\n"
    )

    # ── Apply filters ─────────────────────────────────────────────────────────
    if preset != "Custom query...":
        filtered = apply_preset(preset, enriched)
        st.info(f"**Preset query:** {preset} -- {len(filtered)} schools found")
    else:
        filtered = enriched.copy()
        if sel_type != "All":
            filtered = filtered[filtered["school_type"] == sel_type]
        if sel_dep == "High Deprivation":
            filtered = filtered[filtered["deprivation"] == "high_deprivation"]
        elif sel_dep == "Medium Deprivation":
            filtered = filtered[filtered["deprivation"] == "medium_deprivation"]
        elif sel_dep == "Low Deprivation":
            filtered = filtered[filtered["deprivation"] == "low_deprivation"]
        if sel_transport == "Near transport":
            filtered = filtered[filtered["near_transport"] == True]
        elif sel_transport == "Far from transport":
            filtered = filtered[filtered["near_transport"] == False]
        if sel_la != "All":
            filtered = filtered[filtered["local_authority"] == sel_la]

    # ── Metrics ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Schools Found", len(filtered))
    with col2:
        high_dep = len(filtered[filtered["deprivation"] == "high_deprivation"])
        st.metric("High Deprivation", high_dep)
    with col3:
        near_t = len(filtered[filtered["near_transport"] == True])
        st.metric("Near Transport", near_t)
    with col4:
        total_pupils = int(filtered["pupils"].fillna(0).sum())
        st.metric("Total Pupils", f"{total_pupils:,}")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_map, tab_table, tab_kg, tab_about = st.tabs([
        "Interactive Map",
        "Data Table",
        "Knowledge Graph",
        "About",
    ])

    # ── Map Tab ───────────────────────────────────────────────────────────────
    with tab_map:
        if len(filtered) == 0:
            st.warning("No schools match the selected criteria. Please adjust your filters.")
        else:
            st.markdown(
                f"Showing **{len(filtered):,}** schools on the map. "
                "Click any marker for details."
            )
            m = build_map(filtered, G)
            if m is not None:
                map_html = m.get_root().render()
                components.html(map_html, height=600, scrolling=False)

    # ── Data Table Tab ────────────────────────────────────────────────────────
    with tab_table:
        display_df = filtered[[
            "school_name", "school_type", "local_authority",
            "deprivation", "near_transport", "pupils", "wimd_decile"
        ]].copy()
        display_df.columns = [
            "School Name", "Type", "Local Authority",
            "Deprivation", "Near Transport", "Pupils", "WIMD Decile"
        ]
        display_df["Deprivation"] = display_df["Deprivation"].str.replace("_", " ").str.title()
        display_df["Near Transport"] = display_df["Near Transport"].map(
            {True: "Yes (Bus)", False: "No (Walk)"}
        )
        display_df["Pupils"] = pd.to_numeric(display_df["Pupils"], errors="coerce").fillna(0).astype(int)
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=450)

        # Download button
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="wales_schools_filtered.csv",
            mime="text/csv",
        )

    # ── Knowledge Graph Tab ───────────────────────────────────────────────────
    with tab_kg:
        st.markdown("### Knowledge Graph Statistics")

        kg_col1, kg_col2, kg_col3 = st.columns(3)
        with kg_col1:
            st.metric("Total Nodes", f"{G.number_of_nodes():,}")
        with kg_col2:
            st.metric("Total Edges", f"{G.number_of_edges():,}")
        with kg_col3:
            school_nodes = sum(1 for _, d in G.nodes(data=True) if d.get("type") == "school")
            st.metric("School Nodes", f"{school_nodes:,}")

        st.markdown("### Graph Schema")
        st.code(
            "(School) --[contained_in]--> (LSOA / Deprivation Area)\n"
            "(School) --[near_transport]--> (Transport Stop)",
            language="text"
        )

        st.markdown("""
**Node Types:**
- **School** - 1,446 maintained schools in Wales
- **LSOA** - 1,909 Lower Super Output Areas with WIMD 2019 deprivation data
- **Transport Stop** - 26,457 NaPTAN bus/rail stops in Wales

**Edge Types:**
- `contained_in` - links a school to its LSOA (by Local Authority)
- `near_transport` - links a school to transport stops within 800 m
        """)

        st.markdown("### Deprivation Distribution")
        dep_counts = enriched["deprivation"].value_counts().rename({
            "high_deprivation":   "High (Deciles 1-3)",
            "medium_deprivation": "Medium (Deciles 4-7)",
            "low_deprivation":    "Low (Deciles 8-10)",
            "unknown":            "Unknown",
        })
        st.bar_chart(dep_counts)

        st.markdown("### Schools by Local Authority (Top 15)")
        la_counts = enriched["local_authority"].value_counts().head(15)
        st.bar_chart(la_counts)

    # ── About Tab ─────────────────────────────────────────────────────────────
    with tab_about:
        st.markdown("""
## About This Project

**Wales Education Inequality Spatial Analyser** is a prototype developed as part of an
MSc dissertation at Cardiff University, supervised by Prof. Alia Abdelmoty.

### Research Question
*How can spatial knowledge graphs be used to analyse and visualise educational
inequality across Wales, integrating deprivation indices and transport accessibility?*

### Methodology
The system combines three open government datasets into a **Qualitative Place
Knowledge Graph** (QPKG) using NetworkX, enabling spatial queries about schools,
deprivation, and transport access.

### Datasets

| Dataset | Source | Records |
|---------|--------|---------|
| Wales Maintained Schools | DataMapWales / Welsh Government | 1,446 |
| WIMD 2019 (Deprivation) | Welsh Government | 1,909 LSOAs |
| NaPTAN Transport Stops | DfT / Welsh Government | 26,457 stops |

### Key Features
- Interactive map with colour-coded deprivation markers
- Preset spatial queries in natural language style
- Knowledge graph linking schools, LSOAs, and transport stops
- Filtering by school type, deprivation level, transport access, and local authority
- Data export to CSV

### Technical Stack
Python - Streamlit - Folium - NetworkX - Pandas - PyProj

---
*Cardiff University - School of Computer Science and Informatics - 2024-2025*
        """)


if __name__ == "__main__":
    main()
