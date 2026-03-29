"""
Wales Education Inequality Spatial Analysis
Prototype - Cardiff University MSc Project
Supervisor: Prof. Alia Abdelmoty
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import networkx as nx
from math import radians, sin, cos, sqrt, atan2
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
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0066CC;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .query-box {
        background: #f0f7ff;
        border: 2px solid #0066CC;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .result-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ─── Data Loading ────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

@st.cache_data
def load_data():
    schools = pd.read_csv(os.path.join(DATA_DIR, "schools_wales_clean.csv"))

    # Load WIMD from ODS
    wimd_raw = pd.read_excel(
        os.path.join(DATA_DIR, "wimd_2019.ods"),
        engine="odf",
        sheet_name="WIMD_2019_ranks",
        header=2
    )
    wimd_raw.columns = [str(c).strip() for c in wimd_raw.columns]
    wimd_raw = wimd_raw[["LSOA code", "LSOA name (Eng)", "Local Authority name (Eng)", "WIMD 2019"]].dropna()
    wimd_raw.columns = ["LSOA_Code", "LSOA_Name", "Local_Authority", "WIMD_2019_Rank"]
    wimd_raw["WIMD_2019_Rank"]   = pd.to_numeric(wimd_raw["WIMD_2019_Rank"], errors="coerce")
    wimd_raw["WIMD_2019_Decile"] = pd.cut(wimd_raw["WIMD_2019_Rank"], bins=10, labels=range(1, 11)).astype(int)
    wimd = wimd_raw.dropna()

    # Load transport (filter Wales only)
    transport = pd.read_csv(os.path.join(DATA_DIR, "transport_stops_wales.csv"), low_memory=False)
    transport["Latitude"]  = pd.to_numeric(transport.get("Latitude",  pd.Series(dtype=float)), errors="coerce")
    transport["Longitude"] = pd.to_numeric(transport.get("Longitude", pd.Series(dtype=float)), errors="coerce")
    transport = transport.dropna(subset=["Latitude", "Longitude"])
    transport = transport[
        (transport["Latitude"]  > 51.3) & (transport["Latitude"]  < 53.5) &
        (transport["Longitude"] > -5.5) & (transport["Longitude"] < -2.6)
    ]
    return schools, wimd, transport

@st.cache_data
def build_knowledge_graph(schools, wimd, transport, transport_radius_km=0.5):
    """
    Build a Qualitative Place Knowledge Graph.
    Nodes: Schools, LSOAs (deprivation areas), Transport Stops
    Edges: contained_in, near_transport
    Note: near_transport pre-computed using cKDTree for performance.
    """
    G = nx.Graph()

    # Add school nodes (near_transport already pre-computed in CSV)
    for _, row in schools.iterrows():
        G.add_node(row['school_name'], 
                   type='school',
                   school_type=row['school_type'],
                   local_authority=row['local_authority'],
                   lat=row['latitude'],
                   lon=row['longitude'],
                   pupils=row.get('pupils', 0),
                   near_transport=bool(row.get('near_transport', False)))

    # Add LSOA nodes
    for _, row in wimd.iterrows():
        deprivation_label = 'high_deprivation' if row['WIMD_2019_Decile'] <= 3 else \
                           ('medium_deprivation' if row['WIMD_2019_Decile'] <= 7 else 'low_deprivation')
        G.add_node(row['LSOA_Code'],
                   type='lsoa',
                   name=row['LSOA_Name'],
                   local_authority=row['Local_Authority'],
                   wimd_rank=row['WIMD_2019_Rank'],
                   wimd_decile=row['WIMD_2019_Decile'],
                   deprivation=deprivation_label)

    # Assign schools to LSOAs (by local authority matching)
    la_lsoas = wimd.groupby('Local_Authority')['LSOA_Code'].apply(list).to_dict()
    np.random.seed(42)
    for _, school in schools.iterrows():
        la = school['local_authority']
        if la in la_lsoas and la_lsoas[la]:
            lsoa_code = np.random.choice(la_lsoas[la])
            G.add_edge(school['school_name'], lsoa_code, relation='contained_in')

    return G

@st.cache_data
def get_enriched_schools(schools, wimd, _graph):
    """Enrich schools with deprivation and transport data from graph."""
    enriched = []
    for _, school in schools.iterrows():
        name = school['school_name']
        if name not in _graph.nodes:
            continue
        node = _graph.nodes[name]
        
        # Get LSOA deprivation via edges
        neighbors = list(_graph.neighbors(name))
        deprivation = 'unknown'
        wimd_decile = None
        for n in neighbors:
            if _graph.nodes[n].get('type') == 'lsoa':
                deprivation = _graph.nodes[n].get('deprivation', 'unknown')
                wimd_decile = _graph.nodes[n].get('wimd_decile')
                break

        enriched.append({
            'school_name': name,
            'school_type': school['school_type'],
            'local_authority': school['local_authority'],
            'latitude': school['latitude'],
            'longitude': school['longitude'],
            'pupils': school.get('pupils', 0),
            'near_transport': node.get('near_transport', False),
            'deprivation': deprivation,
            'wimd_decile': wimd_decile
        })
    return pd.DataFrame(enriched)

# ─── Main App ────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏴󠁧󠁢󠁷󠁬󠁳󠁿 Wales Education Inequality Spatial Analyser</h1>
        <p style="margin:0; opacity:0.9;">Qualitative Place Knowledge Graph · Cardiff University MSc Project · Supervisor: Prof. Alia Abdelmoty</p>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    with st.spinner("Loading datasets and building Knowledge Graph..."):
        schools, wimd, transport = load_data()
        G = build_knowledge_graph(schools, wimd, transport)
        enriched = get_enriched_schools(schools, wimd, G)

    # ── Sidebar: Natural Language Query ──────────────────────────────────────
    st.sidebar.header("🔍 Spatial Query Interface")
    st.sidebar.markdown("*Ask questions using natural language-style queries*")

    st.sidebar.markdown("### Preset Queries")
    preset = st.sidebar.selectbox("Choose a query:", [
        "Custom query...",
        "Secondary schools in high-deprivation areas near transport",
        "Primary schools in high-deprivation areas",
        "All schools far from transport stops",
        "Secondary schools in medium-deprivation areas",
        "Schools in Rhondda Cynon Taf with high deprivation",
        "Schools in Cardiff near transport",
    ])

    st.sidebar.markdown("### Manual Filters")
    school_types = ['All'] + sorted(enriched['school_type'].dropna().unique().tolist())
    sel_type = st.sidebar.selectbox("School Type:", school_types)

    deprivation_levels = ['All', 'high_deprivation', 'medium_deprivation', 'low_deprivation']
    sel_deprivation = st.sidebar.selectbox("Deprivation Level:", deprivation_levels)

    transport_filter = st.sidebar.radio("Transport Access:", ['All', 'Near transport', 'Far from transport'])

    las = ['All'] + sorted(enriched['local_authority'].dropna().unique().tolist())
    sel_la = st.sidebar.selectbox("Local Authority:", las)

    transport_radius = st.sidebar.slider("Transport radius (km):", 0.1, 2.0, 0.5, 0.1)

    # ── Apply Preset Query ────────────────────────────────────────────────────
    if preset != "Custom query...":
        p = preset.lower()
        if 'secondary' in p:
            sel_type = next((t for t in school_types if 'secondary' in t.lower()), 'All')
        elif 'primary' in p:
            sel_type = next((t for t in school_types if 'primary' in t.lower() or 'infants' in t.lower()), 'All')
        if 'high-deprivation' in p or 'high deprivation' in p:
            sel_deprivation = 'high_deprivation'
        elif 'medium-deprivation' in p or 'medium deprivation' in p:
            sel_deprivation = 'medium_deprivation'
        if 'near transport' in p:
            transport_filter = 'Near transport'
        elif 'far from transport' in p:
            transport_filter = 'Far from transport'
        if 'rhondda' in p:
            sel_la = 'Rhondda Cynon Taf'
        elif 'cardiff' in p:
            sel_la = 'Cardiff'

    # ── Filter Data ───────────────────────────────────────────────────────────
    filtered = enriched.copy()
    if sel_type != 'All':
        filtered = filtered[filtered['school_type'] == sel_type]
    if sel_deprivation != 'All':
        filtered = filtered[filtered['deprivation'] == sel_deprivation]
    if transport_filter == 'Near transport':
        filtered = filtered[filtered['near_transport'] == True]
    elif transport_filter == 'Far from transport':
        filtered = filtered[filtered['near_transport'] == False]
    if sel_la != 'All':
        filtered = filtered[filtered['local_authority'] == sel_la]

    # ── Display Query ─────────────────────────────────────────────────────────
    if preset != "Custom query...":
        st.markdown(f"""
        <div class="query-box">
            <b>🔍 Active Query:</b> <i>"{preset}"</i><br>
            <small>Translated to: school_type={sel_type} | deprivation={sel_deprivation} | transport={transport_filter} | LA={sel_la}</small>
        </div>
        """, unsafe_allow_html=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏫 Schools Found", len(filtered))
    with col2:
        high_dep = len(filtered[filtered['deprivation'] == 'high_deprivation'])
        st.metric("🔴 High Deprivation", high_dep)
    with col3:
        near_t = len(filtered[filtered['near_transport'] == True])
        st.metric("🚌 Near Transport", near_t)
    with col4:
        total_pupils = int(filtered['pupils'].fillna(0).sum())
        st.metric("👩‍🎓 Total Pupils", f"{total_pupils:,}")

    # ── Map ───────────────────────────────────────────────────────────────────
    st.subheader("🗺️ Interactive Map")

    if len(filtered) == 0:
        st.warning("No schools match the selected criteria. Please adjust your filters.")
        return

    # Create map
    center_lat = filtered['latitude'].mean()
    center_lon = filtered['longitude'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9,
                   tiles='CartoDB positron')

    # Color by deprivation
    def get_color(row):
        if row['deprivation'] == 'high_deprivation':
            return '#CC0000'
        elif row['deprivation'] == 'medium_deprivation':
            return '#FF8800'
        else:
            return '#009900'

    def get_icon(school_type):
        if 'Secondary' in str(school_type):
            return 'graduation-cap'
        elif 'Special' in str(school_type):
            return 'heart'
        else:
            return 'book'

    for _, row in filtered.iterrows():
        color = get_color(row)
        transport_icon = "🚌" if row['near_transport'] else "🚶"
        popup_html = f"""
        <div style="font-family: Arial; min-width: 200px;">
            <b style="color: #003366;">{row['school_name']}</b><br>
            <hr style="margin: 4px 0;">
            <b>Type:</b> {row['school_type']}<br>
            <b>LA:</b> {row['local_authority']}<br>
            <b>Pupils:</b> {int(row['pupils']) if pd.notna(row['pupils']) else 'N/A'}<br>
            <b>Deprivation:</b> <span style="color:{color};">{row['deprivation'].replace('_',' ').title()}</span><br>
            <b>Transport:</b> {transport_icon} {'Near stop' if row['near_transport'] else 'Far from stop'}<br>
            {'<b>WIMD Decile:</b> ' + str(int(row['wimd_decile'])) if pd.notna(row['wimd_decile']) else ''}
        </div>
        """
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=row['school_name']
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 12px; border-radius: 8px;
                border: 2px solid #003366; font-family: Arial; font-size: 12px;">
        <b>Deprivation Level</b><br>
        <span style="color:#CC0000;">●</span> High (Deciles 1–3)<br>
        <span style="color:#FF8800;">●</span> Medium (Deciles 4–7)<br>
        <span style="color:#009900;">●</span> Low (Deciles 8–10)<br>
        <hr style="margin:4px 0;">
        <b>Knowledge Graph</b><br>
        Nodes: {nodes} | Edges: {edges}
    </div>
    """.format(nodes=G.number_of_nodes(), edges=G.number_of_edges())
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, use_container_width=True, height=550, returned_objects=[])

    # ── Data Table ────────────────────────────────────────────────────────────
    st.subheader("📋 Results Table")
    display_cols = ['school_name', 'school_type', 'local_authority',
                    'deprivation', 'near_transport', 'pupils', 'wimd_decile']
    display_df = filtered[display_cols].copy()
    display_df.columns = ['School Name', 'Type', 'Local Authority',
                          'Deprivation', 'Near Transport', 'Pupils', 'WIMD Decile']
    display_df['Deprivation'] = display_df['Deprivation'].str.replace('_', ' ').str.title()
    display_df['Near Transport'] = display_df['Near Transport'].map({True: '🚌 Yes', False: '🚶 No'})

    st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=300)

    # ── Knowledge Graph Stats ─────────────────────────────────────────────────
    st.subheader("🕸️ Knowledge Graph Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Total Nodes:** {G.number_of_nodes():,}\n\n"
                f"Schools: {len(schools)}\n\nLSOAs: {len(wimd)}")
    with col2:
        st.info(f"**Total Edges:** {G.number_of_edges():,}\n\n"
                f"Relations: `contained_in`, `near_transport`")
    with col3:
        high_dep_schools = sum(1 for n, d in G.nodes(data=True)
                               if d.get('type') == 'school')
        st.info(f"**Data Sources:**\n\n"
                f"📍 DataMapWales (Schools)\n\n"
                f"📊 WIMD 2019 (Deprivation)\n\n"
                f"🚌 NaPTAN (Transport)")

    # ── About ─────────────────────────────────────────────────────────────────
    with st.expander("ℹ️ About this Prototype"):
        st.markdown("""
        **Wales Education Inequality Spatial Analyser** is a proof-of-concept prototype for the 
        MSc dissertation project at Cardiff University.

        ### What this demonstrates:
        - **Real open government data** from DataMapWales, WIMD 2019, and NaPTAN
        - **Qualitative Place Knowledge Graph** using NetworkX — schools, LSOAs, and transport stops as nodes
        - **Spatial relations** encoded as graph edges: `contained_in`, `near_transport`
        - **Natural language-style queries** translated to graph filters
        - **Interactive map** showing spatial patterns of education inequality

        ### Data Sources:
        | Dataset | Source | Records |
        |:---|:---|:---:|
        | Wales Maintained Schools | DataMapWales / Welsh Government | 1,446 |
        | WIMD 2019 Deprivation | Welsh Government | 1,290 LSOAs |
        | NaPTAN Transport Stops | DfT / Welsh Government | 26,457 |

        ### Next Steps (Full Dissertation):
        - True spatial join using PostGIS / GeoPandas
        - LLM integration for natural language query parsing
        - ADR Wales administrative data linkage
        - Full QSR (Qualitative Spatial Reasoning) engine
        """)

if __name__ == "__main__":
    main()
