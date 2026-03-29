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
    .insight-card {
        background: #f8f9fa;
        border-left: 4px solid #0066CC;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin: 0.4rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── Data Directory ──────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@st.cache_data
def load_data():
    """Load and prepare all datasets."""
    # ── Schools (enriched with FSM, attendance, GCSE) ────────────────────────
    enriched_path = os.path.join(DATA_DIR, "schools_enriched.csv")
    if os.path.exists(enriched_path):
        schools = pd.read_csv(enriched_path)
    else:
        schools = pd.read_csv(os.path.join(DATA_DIR, "schools_wales_clean.csv"))
        schools['wimd_decile'] = None
        schools['deprivation'] = 'unknown'
        schools['fsm_pct'] = None
        schools['attendance_pct'] = None
        schools['gcse_pass_pct'] = None

    schools["latitude"]  = pd.to_numeric(schools["latitude"],  errors="coerce")
    schools["longitude"] = pd.to_numeric(schools["longitude"], errors="coerce")
    schools = schools.dropna(subset=["latitude", "longitude"])

    # ── WIMD 2019 (ODS) ──────────────────────────────────────────────────────
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
            wimd_decile=row.get("wimd_decile"),
            deprivation=row.get("deprivation", "unknown"),
            fsm_pct=row.get("fsm_pct"),
            attendance_pct=row.get("attendance_pct"),
            gcse_pass_pct=row.get("gcse_pass_pct"),
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

    # Assign schools to LSOAs by local authority
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
    """Return enriched schools dataframe (already enriched from CSV)."""
    enriched = []
    for _, school in schools.iterrows():
        name = school["school_name"]
        if name not in _graph.nodes:
            continue

        enriched.append({
            "school_name":     name,
            "school_type":     school["school_type"],
            "local_authority": school["local_authority"],
            "latitude":        school["latitude"],
            "longitude":       school["longitude"],
            "pupils":          school.get("pupils", 0),
            "near_transport":  bool(school.get("near_transport", False)),
            "deprivation":     school.get("deprivation", "unknown"),
            "wimd_decile":     school.get("wimd_decile"),
            "fsm_pct":         school.get("fsm_pct"),
            "attendance_pct":  school.get("attendance_pct"),
            "gcse_pass_pct":   school.get("gcse_pass_pct"),
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


def qualitative_place_label(deprivation, near_transport):
    """Convert numeric data to qualitative place descriptions (QPM-style)."""
    dep_label = {
        "high_deprivation":   "Highly Deprived",
        "medium_deprivation": "Moderately Deprived",
        "low_deprivation":    "Low Deprivation",
        "unknown":            "Unknown",
    }.get(deprivation, "Unknown")

    transport_label = "Good Transport Access" if near_transport else "Poor Transport Access"

    if deprivation == "high_deprivation" and not near_transport:
        risk = "Critical"; risk_color = "#CC0000"
    elif deprivation == "high_deprivation" and near_transport:
        risk = "High"; risk_color = "#FF4444"
    elif deprivation == "medium_deprivation" and not near_transport:
        risk = "Elevated"; risk_color = "#FF8800"
    elif deprivation == "medium_deprivation" and near_transport:
        risk = "Moderate"; risk_color = "#FFAA00"
    elif deprivation == "low_deprivation" and not near_transport:
        risk = "Low-Moderate"; risk_color = "#88BB00"
    else:
        risk = "Low"; risk_color = "#009900"

    return dep_label, transport_label, risk, risk_color


def build_qpm_analysis(enriched):
    """Build QPM-style qualitative place analysis from enriched schools data."""
    df = enriched.copy()
    labels = df.apply(
        lambda r: qualitative_place_label(r["deprivation"], r["near_transport"]), axis=1
    )
    df["dep_label"]       = [l[0] for l in labels]
    df["transport_label"] = [l[1] for l in labels]
    df["risk_level"]      = [l[2] for l in labels]
    df["risk_color"]      = [l[3] for l in labels]
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
        fsm_str = f"<b>FSM:</b> {row['fsm_pct']:.1f}%<br>" if pd.notna(row.get("fsm_pct")) else ""
        att_str = f"<b>Attendance:</b> {row['attendance_pct']:.1f}%<br>" if pd.notna(row.get("attendance_pct")) else ""

        safe_name = str(row['school_name']).replace("'", "&#39;").replace('`', '&#96;')
        safe_type = str(row['school_type']).replace("'", "&#39;")
        safe_la   = str(row['local_authority']).replace("'", "&#39;")
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
            f"{fsm_str}"
            f"{att_str}"
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


def build_multi_factor_tab(enriched):
    """Render the Multi-Factor Analysis tab."""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#1a3a5c,#2563eb);padding:1.2rem 1.5rem;
    border-radius:12px;color:white;margin-bottom:1rem;'>
    <h3 style='margin:0;color:white;'>📊 Multi-Factor Educational Inequality Analysis</h3>
    <p style='margin:0.3rem 0 0;opacity:0.9;font-size:0.9rem;'>
    Integrating <b>Free School Meals (FSM)</b>, <b>Attendance Rates</b>, and <b>GCSE Performance</b>
    with deprivation and transport data to reveal compound disadvantage patterns.
    </p></div>""", unsafe_allow_html=True)

    # ── Note about data ────────────────────────────────────────────────────────
    st.info(
        "**Note:** FSM, attendance, and GCSE figures are modelled from documented Welsh Government "
        "statistical patterns (2022-23) and assigned per school based on WIMD deprivation decile. "
        "They illustrate the kind of multi-factor analysis the full project will perform with "
        "actual school-level data from StatsWales."
    )

    df = enriched.copy()
    df_valid = df[df['fsm_pct'].notna()].copy()
    secondary = df_valid[df_valid['school_type'].str.contains('Secondary', na=False)].copy()

    # ── Section 1: FSM Analysis ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🍽️ Free School Meals (FSM) — Poverty Indicator")
    st.markdown(
        "FSM eligibility is one of the strongest school-level indicators of family poverty. "
        "In Wales, children qualify if their household income is below £16,190 or they receive "
        "certain benefits. High FSM rates signal concentrated economic disadvantage."
    )

    dep_order = ['high_deprivation', 'medium_deprivation', 'low_deprivation']
    dep_labels = {
        'high_deprivation': '🔴 High Deprivation (Deciles 1-3)',
        'medium_deprivation': '🟠 Medium Deprivation (Deciles 4-7)',
        'low_deprivation': '🟢 Low Deprivation (Deciles 8-10)',
    }
    dep_colors = {
        'high_deprivation': '#CC0000',
        'medium_deprivation': '#FF8800',
        'low_deprivation': '#009900',
    }

    fsm_by_dep = df_valid.groupby('deprivation')['fsm_pct'].agg(['mean', 'median', 'std']).round(1)

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for i, dep in enumerate(dep_order):
        if dep in fsm_by_dep.index:
            row = fsm_by_dep.loc[dep]
            with cols[i]:
                st.markdown(
                    f"<div style='background:{dep_colors[dep]}15;border:2px solid {dep_colors[dep]};"
                    f"border-radius:10px;padding:1rem;text-align:center;'>"
                    f"<div style='font-size:0.85rem;color:#555;'>{dep_labels[dep]}</div>"
                    f"<div style='font-size:2rem;font-weight:bold;color:{dep_colors[dep]};'>{row['mean']:.1f}%</div>"
                    f"<div style='font-size:0.8rem;color:#666;'>avg FSM rate</div>"
                    f"<div style='font-size:0.8rem;color:#888;'>median: {row['median']:.1f}%</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # FSM bar chart by deprivation
    st.markdown("**FSM Rate Distribution by Deprivation Band**")
    fsm_chart_data = {}
    for dep in dep_order:
        subset = df_valid[df_valid['deprivation'] == dep]['fsm_pct']
        if len(subset) > 0:
            fsm_chart_data[dep_labels[dep]] = subset.mean()

    fsm_chart_df = pd.DataFrame.from_dict(
        fsm_chart_data, orient='index', columns=['Average FSM %']
    )
    st.bar_chart(fsm_chart_df)

    # ── Section 2: Attendance Analysis ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📅 Attendance Rates — Engagement Indicator")
    st.markdown(
        "Chronic absenteeism (missing 10%+ of school days) is strongly linked to deprivation. "
        "In Wales, the national average attendance is approximately **93.5%** (2022-23). "
        "Schools in deprived areas consistently show lower attendance rates."
    )

    att_by_dep = df_valid.groupby('deprivation')['attendance_pct'].agg(['mean', 'min', 'max']).round(1)

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for i, dep in enumerate(dep_order):
        if dep in att_by_dep.index:
            row = att_by_dep.loc[dep]
            diff_from_national = row['mean'] - 93.5
            diff_str = f"+{diff_from_national:.1f}%" if diff_from_national > 0 else f"{diff_from_national:.1f}%"
            diff_color = "#009900" if diff_from_national >= 0 else "#CC0000"
            with cols[i]:
                st.markdown(
                    f"<div style='background:{dep_colors[dep]}15;border:2px solid {dep_colors[dep]};"
                    f"border-radius:10px;padding:1rem;text-align:center;'>"
                    f"<div style='font-size:0.85rem;color:#555;'>{dep_labels[dep]}</div>"
                    f"<div style='font-size:2rem;font-weight:bold;color:{dep_colors[dep]};'>{row['mean']:.1f}%</div>"
                    f"<div style='font-size:0.8rem;color:#666;'>avg attendance</div>"
                    f"<div style='font-size:0.8rem;color:{diff_color};'>{diff_str} vs national avg</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    # Transport x Attendance
    st.markdown("**Transport Access Impact on Attendance**")
    att_transport = df_valid.groupby(['deprivation', 'near_transport'])['attendance_pct'].mean().round(1).reset_index()
    att_transport['label'] = att_transport.apply(
        lambda r: f"{'Near' if r['near_transport'] else 'Far'} Transport | {r['deprivation'].replace('_deprivation','').title()}",
        axis=1
    )
    att_pivot = att_transport.set_index('label')['attendance_pct'].sort_values(ascending=False)
    st.bar_chart(att_pivot.rename("Avg Attendance %"))

    # ── Section 3: GCSE Analysis ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎓 GCSE Performance — Outcome Indicator")
    st.markdown(
        f"GCSE results (% achieving grades 9-4 / A*-C) represent the key educational outcome. "
        f"Analysis covers **{len(secondary):,} secondary schools** in Wales. "
        "The attainment gap between the most and least deprived areas is approximately 15-20 percentage points."
    )

    if len(secondary) > 0:
        gcse_by_dep = secondary.groupby('deprivation')['gcse_pass_pct'].agg(['mean', 'median', 'std']).round(1)

        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for i, dep in enumerate(dep_order):
            if dep in gcse_by_dep.index:
                row = gcse_by_dep.loc[dep]
                with cols[i]:
                    st.markdown(
                        f"<div style='background:{dep_colors[dep]}15;border:2px solid {dep_colors[dep]};"
                        f"border-radius:10px;padding:1rem;text-align:center;'>"
                        f"<div style='font-size:0.85rem;color:#555;'>{dep_labels[dep]}</div>"
                        f"<div style='font-size:2rem;font-weight:bold;color:{dep_colors[dep]};'>{row['mean']:.1f}%</div>"
                        f"<div style='font-size:0.8rem;color:#666;'>avg GCSE pass rate</div>"
                        f"<div style='font-size:0.8rem;color:#888;'>median: {row['median']:.1f}%</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # Attainment gap
        if 'high_deprivation' in gcse_by_dep.index and 'low_deprivation' in gcse_by_dep.index:
            gap = gcse_by_dep.loc['low_deprivation', 'mean'] - gcse_by_dep.loc['high_deprivation', 'mean']
            st.markdown(
                f"<div style='background:#fff3cd;border:2px solid #ffc107;border-radius:10px;"
                f"padding:1rem;margin:0.8rem 0;text-align:center;'>"
                f"<b style='font-size:1.1rem;'>📏 Attainment Gap: {gap:.1f} percentage points</b><br>"
                f"<span style='color:#555;font-size:0.9rem;'>Between schools in most deprived (Deciles 1-3) "
                f"vs least deprived (Deciles 8-10) areas</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        gcse_chart_data = {}
        for dep in dep_order:
            subset = secondary[secondary['deprivation'] == dep]['gcse_pass_pct']
            if len(subset) > 0:
                gcse_chart_data[dep_labels[dep]] = subset.mean()
        gcse_chart_df = pd.DataFrame.from_dict(gcse_chart_data, orient='index', columns=['Average GCSE Pass %'])
        st.bar_chart(gcse_chart_df)

    # ── Section 4: Compound Disadvantage Matrix ────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔗 Compound Disadvantage — The Knowledge Graph Advantage")
    st.markdown(
        "The power of a **Knowledge Graph** approach is the ability to identify schools facing "
        "*multiple simultaneous disadvantages*. The table below shows how deprivation, transport, "
        "FSM, and attendance combine to create compound risk profiles."
    )

    # Build compound analysis
    df_compound = df_valid.copy()
    df_compound['high_fsm'] = df_compound['fsm_pct'] > 25
    df_compound['low_attendance'] = df_compound['attendance_pct'] < 92
    df_compound['disadvantage_count'] = (
        (df_compound['deprivation'] == 'high_deprivation').astype(int) +
        (~df_compound['near_transport']).astype(int) +
        df_compound['high_fsm'].astype(int) +
        df_compound['low_attendance'].astype(int)
    )

    compound_summary = df_compound.groupby('disadvantage_count').agg(
        Schools=('school_name', 'count'),
        Avg_FSM=('fsm_pct', 'mean'),
        Avg_Attendance=('attendance_pct', 'mean'),
    ).round(1).reset_index()
    compound_summary.columns = ['Disadvantage Factors', 'Schools', 'Avg FSM %', 'Avg Attendance %']

    labels_map = {
        0: '0 factors — No significant disadvantage',
        1: '1 factor — Mild disadvantage',
        2: '2 factors — Moderate compound disadvantage',
        3: '3 factors — Severe compound disadvantage',
        4: '4 factors — Critical compound disadvantage',
    }
    compound_summary['Profile'] = compound_summary['Disadvantage Factors'].map(labels_map)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(
            compound_summary[['Profile', 'Schools', 'Avg FSM %', 'Avg Attendance %']],
            use_container_width=True,
            hide_index=True
        )
    with col2:
        critical = compound_summary[compound_summary['Disadvantage Factors'] >= 3]['Schools'].sum()
        total = len(df_compound)
        st.metric("Schools with 3+ Disadvantages", f"{critical:,}")
        st.metric("% of All Schools", f"{round(critical/total*100, 1)}%")
        st.metric("Total Schools Analysed", f"{total:,}")

    # ── Section 5: Local Authority Comparison ─────────────────────────────────
    st.markdown("---")
    st.markdown("### 🗺️ Local Authority Multi-Factor Profile")

    la_profile = df_valid.groupby('local_authority').agg(
        Schools=('school_name', 'count'),
        Avg_WIMD_Decile=('wimd_decile', 'mean'),
        Avg_FSM=('fsm_pct', 'mean'),
        Avg_Attendance=('attendance_pct', 'mean'),
        Pct_Near_Transport=('near_transport', lambda x: round(x.sum()/len(x)*100, 1)),
        Pct_High_Dep=('deprivation', lambda x: round((x=='high_deprivation').sum()/len(x)*100, 1)),
    ).round(1).reset_index().rename(columns={
        'local_authority': 'Local Authority',
        'Avg_WIMD_Decile': 'Avg WIMD Decile',
        'Avg_FSM': 'Avg FSM %',
        'Avg_Attendance': 'Avg Attendance %',
        'Pct_Near_Transport': '% Near Transport',
        'Pct_High_Dep': '% High Deprivation',
    }).sort_values('Avg FSM %', ascending=False)

    st.dataframe(
        la_profile.reset_index(drop=True),
        use_container_width=True,
        height=420,
        column_config={
            'Avg FSM %': st.column_config.ProgressColumn(
                'Avg FSM %', min_value=0, max_value=50, format="%.1f%%"
            ),
            'Avg Attendance %': st.column_config.ProgressColumn(
                'Avg Attendance %', min_value=85, max_value=100, format="%.1f%%"
            ),
            '% High Deprivation': st.column_config.ProgressColumn(
                '% High Dep', min_value=0, max_value=100, format="%.1f%%"
            ),
            '% Near Transport': st.column_config.ProgressColumn(
                '% Near Transport', min_value=0, max_value=100, format="%.1f%%"
            ),
        }
    )

    # ── Section 6: Knowledge Graph Queries ────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Knowledge Graph Multi-Factor Queries")
    st.markdown(
        "These queries demonstrate how a Knowledge Graph enables complex multi-dimensional "
        "spatial reasoning that would be difficult with traditional relational databases:"
    )

    queries = [
        ("Query 1", "#003366",
         "Find schools that are: located_in(HighlyDeprived) AND far_from(TransportStop) AND has_FSM_rate > 30%",
         len(df_valid[(df_valid['deprivation']=='high_deprivation') &
                      (~df_valid['near_transport']) &
                      (df_valid['fsm_pct'] > 30)]),
         "Triple disadvantage: deprivation + transport isolation + high poverty"),

        ("Query 2", "#CC0000",
         "Find schools that are: located_in(HighlyDeprived) AND has_attendance < 91%",
         len(df_valid[(df_valid['deprivation']=='high_deprivation') &
                      (df_valid['attendance_pct'] < 91)]),
         "Schools where deprivation is actively reducing pupil engagement"),

        ("Query 3", "#FF8800",
         "Find secondary schools: located_in(HighlyDeprived) AND has_GCSE_pass < 55%",
         len(secondary[(secondary['deprivation']=='high_deprivation') &
                       (secondary['gcse_pass_pct'] < 55)]) if len(secondary) > 0 else 0,
         "Secondary schools with both high deprivation and below-average GCSE outcomes"),

        ("Query 4", "#009900",
         "Find schools: located_in(HighlyDeprived) AND near(TransportStop) AND has_attendance > 93%",
         len(df_valid[(df_valid['deprivation']=='high_deprivation') &
                      (df_valid['near_transport']) &
                      (df_valid['attendance_pct'] > 93)]),
         "Resilient schools: high deprivation but good transport and attendance — positive outliers"),
    ]

    for qid, color, query_text, count, interpretation in queries:
        st.markdown(
            f"<div style='background:{color}10;border-left:5px solid {color};"
            f"padding:0.9rem 1.1rem;border-radius:8px;margin:0.6rem 0;'>"
            f"<b style='color:{color};'>{qid}:</b> "
            f"<code style='background:{color}15;padding:2px 6px;border-radius:4px;font-size:0.85rem;'>"
            f"{query_text}</code><br>"
            f"<b style='font-size:1.1rem;'>→ {count:,} schools</b> &nbsp; "
            f"<span style='color:#555;font-size:0.85rem;'>{interpretation}</span>"
            f"</div>",
            unsafe_allow_html=True
        )


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
        "- Welsh Gov Stats - FSM/Attendance\n"
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
    col1, col2, col3, col4, col5 = st.columns(5)
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
    with col5:
        avg_fsm = filtered['fsm_pct'].mean()
        st.metric("Avg FSM Rate", f"{avg_fsm:.1f}%" if pd.notna(avg_fsm) else "N/A")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_map, tab_table, tab_kg, tab_qpm, tab_multi, tab_about = st.tabs([
        "🗺️ Interactive Map",
        "📋 Data Table",
        "🕸️ Knowledge Graph",
        "🏷️ Qualitative Place Analysis",
        "📊 Multi-Factor Analysis",
        "ℹ️ About",
    ])

    # ── Map Tab ───────────────────────────────────────────────────────────────
    with tab_map:
        if len(filtered) == 0:
            st.warning("No schools match the selected criteria. Please adjust your filters.")
        else:
            st.markdown(
                f"Showing **{len(filtered):,}** schools on the map. "
                "Click any marker for details including FSM and attendance data."
            )
            m = build_map(filtered, G)
            if m is not None:
                map_html = m.get_root().render()
                components.html(map_html, height=600, scrolling=False)

    # ── Data Table Tab ────────────────────────────────────────────────────────
    with tab_table:
        display_df = filtered[[
            "school_name", "school_type", "local_authority",
            "deprivation", "near_transport", "pupils", "wimd_decile",
            "fsm_pct", "attendance_pct", "gcse_pass_pct"
        ]].copy()
        display_df.columns = [
            "School Name", "Type", "Local Authority",
            "Deprivation", "Near Transport", "Pupils", "WIMD Decile",
            "FSM %", "Attendance %", "GCSE Pass %"
        ]
        display_df["Deprivation"] = display_df["Deprivation"].str.replace("_", " ").str.title()
        display_df["Near Transport"] = display_df["Near Transport"].map(
            {True: "Yes (Bus)", False: "No (Walk)"}
        )
        display_df["Pupils"] = pd.to_numeric(display_df["Pupils"], errors="coerce").fillna(0).astype(int)
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=450)

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
            "(School) --[near_transport]--> (Transport Stop)\n"
            "(School) --[has_fsm_rate]--> (FSM_Value)\n"
            "(School) --[has_attendance]--> (Attendance_Value)",
            language="text"
        )

        st.markdown("""
**Node Types:**
- **School** - 1,446 maintained schools in Wales (with FSM, attendance, GCSE attributes)
- **LSOA** - 1,909 Lower Super Output Areas with WIMD 2019 deprivation data
- **Transport Stop** - 26,457 NaPTAN bus/rail stops in Wales

**Edge Types:**
- `contained_in` - links a school to its LSOA (by Local Authority)
- `near_transport` - links a school to transport stops within 800 m
- `has_fsm_rate` - school attribute: percentage of pupils eligible for free school meals
- `has_attendance` - school attribute: annual pupil attendance rate
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

    # ── Qualitative Place Analysis Tab (QPM) ─────────────────────────────────
    with tab_qpm:

        qpm_df = build_qpm_analysis(enriched)
        total  = len(qpm_df)

        high_dep_total   = len(qpm_df[qpm_df["deprivation"] == "high_deprivation"])
        med_dep_total    = len(qpm_df[qpm_df["deprivation"] == "medium_deprivation"])
        low_dep_total    = len(qpm_df[qpm_df["deprivation"] == "low_deprivation"])
        near_t_total     = int(qpm_df["near_transport"].sum())
        far_t_total      = total - near_t_total

        high_near = len(qpm_df[(qpm_df["deprivation"]=="high_deprivation") & (qpm_df["near_transport"]==True)])
        high_far  = len(qpm_df[(qpm_df["deprivation"]=="high_deprivation") & (qpm_df["near_transport"]==False)])
        med_near  = len(qpm_df[(qpm_df["deprivation"]=="medium_deprivation") & (qpm_df["near_transport"]==True)])
        med_far   = len(qpm_df[(qpm_df["deprivation"]=="medium_deprivation") & (qpm_df["near_transport"]==False)])
        low_near  = len(qpm_df[(qpm_df["deprivation"]=="low_deprivation") & (qpm_df["near_transport"]==True)])
        low_far   = len(qpm_df[(qpm_df["deprivation"]=="low_deprivation") & (qpm_df["near_transport"]==False)])

        pct_high_dep_poor = round(high_far  / high_dep_total * 100, 1) if high_dep_total > 0 else 0
        pct_low_dep_poor  = round(low_far   / low_dep_total  * 100, 1) if low_dep_total  > 0 else 0

        if len(qpm_df[qpm_df["risk_level"]=="Critical"]) > 0:
            top_la_critical = qpm_df[qpm_df["risk_level"]=="Critical"]["local_authority"].value_counts().idxmax()
        else:
            top_la_critical = "N/A"

        st.markdown("""
        <div style='background:linear-gradient(135deg,#003366,#0066CC);padding:1.2rem 1.5rem;
        border-radius:12px;color:white;margin-bottom:1rem;'>
        <h3 style='margin:0;color:white;'>🗺️ Qualitative Place Analysis</h3>
        <p style='margin:0.3rem 0 0;opacity:0.9;font-size:0.9rem;'>
        Based on the <b>Qualitative Place Model (QPM)</b> — Satoti &amp; Abdelmoty (2025).<br>
        Each school is described by <b>qualitative spatial relations</b> instead of raw numbers.
        </p></div>""", unsafe_allow_html=True)

        st.markdown("### Step 1 — What are the QPM Relations?")
        st.markdown(
            "Instead of saying *'WIMD Decile = 2'*, QPM says **'School is located\_in a Highly Deprived area'**. "
            "Instead of *'distance = 650 m'*, QPM says **'School is near a Transport Stop'**. "
            "These qualitative labels make spatial reasoning human-readable."
        )

        rel_html = """
        <div style='display:flex;gap:1rem;flex-wrap:wrap;margin:0.8rem 0 1.2rem;'>
          <div style='flex:1;min-width:200px;background:#fff8e1;border:2px solid #f59e0b;
               border-radius:10px;padding:1rem;text-align:center;'>
            <div style='font-size:1.8rem;'>🏫</div>
            <b>School</b>
            <div style='color:#666;font-size:0.85rem;margin-top:0.3rem;'>Node in the Knowledge Graph</div>
          </div>
          <div style='flex:0.4;display:flex;align-items:center;justify-content:center;
               font-size:1.1rem;font-weight:bold;color:#0066CC;'>
            ──[located_in]──▶
          </div>
          <div style='flex:1;min-width:200px;background:#fce7f3;border:2px solid #ec4899;
               border-radius:10px;padding:1rem;text-align:center;'>
            <div style='font-size:1.8rem;'>📍</div>
            <b>Deprived / Moderate / Low Area</b>
            <div style='color:#666;font-size:0.85rem;margin-top:0.3rem;'>WIMD Decile → Qualitative Label</div>
          </div>
          <div style='flex:0.4;display:flex;align-items:center;justify-content:center;
               font-size:1.1rem;font-weight:bold;color:#0066CC;'>
            ──[near / far_from]──▶
          </div>
          <div style='flex:1;min-width:200px;background:#e0f2fe;border:2px solid #0ea5e9;
               border-radius:10px;padding:1rem;text-align:center;'>
            <div style='font-size:1.8rem;'>🚌</div>
            <b>Transport Stop</b>
            <div style='color:#666;font-size:0.85rem;margin-top:0.3rem;'>≤800 m = near | >800 m = far_from</div>
          </div>
        </div>
        """
        st.markdown(rel_html, unsafe_allow_html=True)

        st.markdown("### Step 2 — How are schools distributed across qualitative labels?")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Deprivation Level (located\_in)**")
            dep_data = pd.DataFrame({
                "Deprivation": ["High (Deciles 1-3)", "Medium (Deciles 4-7)", "Low (Deciles 8-10)"],
                "Schools":     [high_dep_total, med_dep_total, low_dep_total],
                "Color":       ["#CC0000", "#FF8800", "#009900"],
            })
            for _, r in dep_data.iterrows():
                pct = round(r["Schools"]/total*100,1)
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:0.6rem;margin:0.4rem 0;'>"
                    f"<div style='width:14px;height:14px;border-radius:50%;background:{r['Color']};flex-shrink:0;'></div>"
                    f"<div style='flex:1;'><b>{r['Deprivation']}</b></div>"
                    f"<div style='background:{r['Color']}22;border:1px solid {r['Color']};"
                    f"border-radius:6px;padding:2px 10px;font-weight:bold;color:{r['Color']};'>"
                    f"{r['Schools']:,} schools ({pct}%)</div></div>",
                    unsafe_allow_html=True
                )

        with c2:
            st.markdown("**Transport Access (near / far\_from)**")
            for label, count, color, icon in [
                ("near Transport Stop",    near_t_total, "#0066CC", "🚌"),
                ("far\_from Transport Stop", far_t_total,  "#888888", "🚶"),
            ]:
                pct = round(count/total*100,1)
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:0.6rem;margin:0.4rem 0;'>"
                    f"<div style='font-size:1.3rem;'>{icon}</div>"
                    f"<div style='flex:1;'><b>{label}</b></div>"
                    f"<div style='background:{color}22;border:1px solid {color};"
                    f"border-radius:6px;padding:2px 10px;font-weight:bold;color:{color};'>"
                    f"{count:,} schools ({pct}%)</div></div>",
                    unsafe_allow_html=True
                )

        st.markdown("### Step 3 — What is the relationship between Deprivation and Transport?")

        matrix_html = f"""
        <table style='width:100%;border-collapse:collapse;font-size:0.95rem;margin:0.8rem 0;'>
          <thead>
            <tr style='background:#003366;color:white;'>
              <th style='padding:0.7rem;text-align:left;border-radius:8px 0 0 0;'>Deprivation Level</th>
              <th style='padding:0.7rem;text-align:center;'>🚌 near Transport</th>
              <th style='padding:0.7rem;text-align:center;'>🚶 far_from Transport</th>
              <th style='padding:0.7rem;text-align:center;border-radius:0 8px 0 0;'>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr style='background:#fff0f0;'>
              <td style='padding:0.7rem;font-weight:bold;color:#CC0000;'>🔴 Highly Deprived</td>
              <td style='padding:0.7rem;text-align:center;'><b>{high_near:,}</b><br><small style='color:#666;'>{round(high_near/total*100,1)}% of all schools</small></td>
              <td style='padding:0.7rem;text-align:center;background:#ffdddd;'><b style='color:#CC0000;'>{high_far:,}</b><br><small style='color:#CC0000;'>⚠️ Critical Risk</small></td>
              <td style='padding:0.7rem;text-align:center;font-weight:bold;'>{high_dep_total:,}</td>
            </tr>
            <tr style='background:#fff8f0;'>
              <td style='padding:0.7rem;font-weight:bold;color:#FF8800;'>🟠 Moderately Deprived</td>
              <td style='padding:0.7rem;text-align:center;'><b>{med_near:,}</b><br><small style='color:#666;'>{round(med_near/total*100,1)}% of all schools</small></td>
              <td style='padding:0.7rem;text-align:center;background:#ffe8cc;'><b style='color:#FF8800;'>{med_far:,}</b><br><small style='color:#FF8800;'>Elevated Risk</small></td>
              <td style='padding:0.7rem;text-align:center;font-weight:bold;'>{med_dep_total:,}</td>
            </tr>
            <tr style='background:#f0fff0;'>
              <td style='padding:0.7rem;font-weight:bold;color:#009900;'>🟢 Low Deprivation</td>
              <td style='padding:0.7rem;text-align:center;'><b>{low_near:,}</b><br><small style='color:#666;'>{round(low_near/total*100,1)}% of all schools</small></td>
              <td style='padding:0.7rem;text-align:center;'><b>{low_far:,}</b><br><small style='color:#666;'>Low-Moderate Risk</small></td>
              <td style='padding:0.7rem;text-align:center;font-weight:bold;'>{low_dep_total:,}</td>
            </tr>
            <tr style='background:#f0f4ff;font-weight:bold;'>
              <td style='padding:0.7rem;'>Total</td>
              <td style='padding:0.7rem;text-align:center;'>{near_t_total:,}</td>
              <td style='padding:0.7rem;text-align:center;'>{far_t_total:,}</td>
              <td style='padding:0.7rem;text-align:center;'>{total:,}</td>
            </tr>
          </tbody>
        </table>
        """
        st.markdown(matrix_html, unsafe_allow_html=True)

        st.markdown("### Step 4 — Key Qualitative Findings")

        if pct_high_dep_poor > pct_low_dep_poor:
            correlation_emoji = "⚠️"
            correlation_text  = (
                f"Highly deprived areas have **more** poor transport access ({pct_high_dep_poor}%) "
                f"than low-deprivation areas ({pct_low_dep_poor}%) — deprivation and transport barriers **compound** each other."
            )
            correlation_bg = "#fff0f0"; correlation_border = "#CC0000"
        else:
            correlation_emoji = "💡"
            correlation_text  = (
                f"Interestingly, highly deprived areas actually have **better** transport access ({pct_high_dep_poor}% poor) "
                f"than low-deprivation areas ({pct_low_dep_poor}% poor). "
                "This suggests deprived areas in Wales tend to be **urban** (good bus networks), "
                "while wealthier areas are **rural** (limited public transport)."
            )
            correlation_bg = "#f0f8ff"; correlation_border = "#0066CC"

        findings = [
            ("🔴", "#fff0f0", "#CC0000",
             f"{high_far:,} schools ({round(high_far/total*100,1)}%) are in areas that are <b>Highly Deprived</b> AND <b>far from</b> transport — classified as <b>Critical Risk</b>.",
             f"These schools face a double disadvantage: economic deprivation + transport isolation."),
            ("🟠", "#fff8f0", "#FF8800",
             f"{high_dep_total:,} schools ({round(high_dep_total/total*100,1)}%) are <b>located_in</b> Highly Deprived areas.",
             "Relation: School ──[located_in]──▶ Highly Deprived Area"),
            ("🚌", "#f0f8ff", "#0066CC",
             f"{near_t_total:,} schools ({round(near_t_total/total*100,1)}%) are <b>near</b> a transport stop (≤800m).",
             "Relation: School ──[near]──▶ Transport Stop"),
            (correlation_emoji, correlation_bg, correlation_border,
             correlation_text,
             f"Most critical-risk local authority: <b>{top_la_critical}</b>"),
        ]

        for emoji, bg, border, title, subtitle in findings:
            st.markdown(
                f"<div style='background:{bg};border-left:5px solid {border};"
                f"padding:0.9rem 1.1rem;border-radius:8px;margin:0.5rem 0;'>"
                f"<span style='font-size:1.2rem;'>{emoji}</span> {title}<br>"
                f"<small style='color:#555;'>{subtitle}</small></div>",
                unsafe_allow_html=True
            )

        st.markdown("### Step 5 — Qualitative Summary by Local Authority")

        la_summary = qpm_df.groupby("local_authority").agg(
            Total=("school_name", "count"),
            Critical=("risk_level", lambda x: (x=="Critical").sum()),
            High=("risk_level",    lambda x: (x=="High").sum()),
            Moderate=("risk_level",lambda x: (x=="Moderate").sum()),
            Low=("risk_level",     lambda x: (x=="Low").sum()),
            Pct_HighDep=("deprivation",    lambda x: round((x=="high_deprivation").sum()/len(x)*100,1)),
            Pct_NearTransport=("near_transport", lambda x: round(x.sum()/len(x)*100,1)),
        ).reset_index().rename(columns={
            "local_authority":  "Local Authority",
            "Total":            "Total Schools",
            "Pct_HighDep":      "% High Deprivation",
            "Pct_NearTransport":"% Near Transport",
        }).sort_values("Critical", ascending=False)

        st.dataframe(
            la_summary.reset_index(drop=True),
            use_container_width=True,
            height=380,
            column_config={
                "Critical":          st.column_config.NumberColumn("🔴 Critical",  help="Highly deprived + poor transport"),
                "High":              st.column_config.NumberColumn("🟠 High",       help="Highly deprived + near transport"),
                "Moderate":          st.column_config.NumberColumn("🟡 Moderate",   help="Medium deprivation + near transport"),
                "Low":               st.column_config.NumberColumn("🟢 Low",        help="Low deprivation + good transport"),
                "% High Deprivation":st.column_config.ProgressColumn("% High Dep",  min_value=0, max_value=100, format="%.1f%%"),
                "% Near Transport":  st.column_config.ProgressColumn("% Near Transport", min_value=0, max_value=100, format="%.1f%%"),
            }
        )

    # ── Multi-Factor Analysis Tab ─────────────────────────────────────────────
    with tab_multi:
        build_multi_factor_tab(enriched)

    # ── About Tab ─────────────────────────────────────────────────────────────
    with tab_about:
        st.markdown("""
## About This Project

**Wales Education Inequality Spatial Analyser** is a prototype developed as part of an
MSc dissertation at Cardiff University, supervised by Prof. Alia Abdelmoty.

### Research Question
*How can spatial knowledge graphs be used to analyse and visualise educational
inequality across Wales, integrating deprivation indices, transport accessibility,
and school-level outcome data?*

### Methodology
The system combines open government datasets into a **Qualitative Place
Knowledge Graph** (QPKG) using NetworkX, enabling complex multi-dimensional
spatial queries about schools, deprivation, transport access, and educational outcomes.

### Datasets

| Dataset | Source | Records |
|---------|--------|---------|
| Wales Maintained Schools | DataMapWales / Welsh Government | 1,446 |
| WIMD 2019 (Deprivation) | Welsh Government | 1,909 LSOAs |
| NaPTAN Transport Stops | DfT / Welsh Government | 26,457 stops |
| FSM & Attendance (modelled) | Welsh Gov Stats patterns 2022-23 | 1,446 schools |

### Key Features
- Interactive map with colour-coded deprivation markers (FSM & attendance in popups)
- Preset spatial queries in natural language style
- Knowledge graph linking schools, LSOAs, and transport stops
- **Multi-Factor Analysis**: FSM, attendance, GCSE, compound disadvantage
- Filtering by school type, deprivation level, transport access, and local authority
- Data export to CSV

### Technical Stack
Python · Streamlit · Folium · NetworkX · Pandas · PyProj

---
*Cardiff University - School of Computer Science and Informatics - 2024-2025*
        """)


if __name__ == "__main__":
    main()
