import pandas as pd
from scipy.spatial import cKDTree
import numpy as np
import re
import os

print("=" * 50)
print("Wales Education Inequality — Data Cleaning")
print("=" * 50)

DATA_DIR = "data"

# ── 1. SCHOOLS ──────────────────────────────────────
print("\n[1/3] Loading schools data...")
schools = pd.read_csv(os.path.join(DATA_DIR, "schools_wales.csv"))

# geom column format: POINT (-3.39001 51.94967)  -> lon lat (WGS84 already!)
def extract_lonlat(geom_str):
    try:
        m = re.search(r'POINT\s*\(([-\d.]+)\s+([-\d.]+)\)', str(geom_str))
        if m:
            lon = float(m.group(1))
            lat = float(m.group(2))
            return lon, lat
    except Exception:
        pass
    return (None, None)

coords = schools['geom'].apply(extract_lonlat)
schools['longitude'] = [c[0] for c in coords]
schools['latitude']  = [c[1] for c in coords]

# Drop rows where geom could not be parsed
before = len(schools)
schools = schools.dropna(subset=['longitude', 'latitude'])
dropped = before - len(schools)
if dropped > 0:
    print(f"  Dropped {dropped} rows with missing coordinates")

# Keep only needed columns
keep = ['school_name', 'school_type', 'local_authority', 'sector',
        'pupils', 'postcode', 'latitude', 'longitude']
keep = [c for c in keep if c in schools.columns]
schools = schools[keep].copy()
schools['latitude']  = pd.to_numeric(schools['latitude'],  errors='coerce')
schools['longitude'] = pd.to_numeric(schools['longitude'], errors='coerce')
schools = schools.dropna(subset=['latitude', 'longitude', 'school_name'])

print(f"  Schools cleaned: {len(schools)} records")
if len(schools) > 0:
    row = schools.iloc[0]
    print(f"  Sample: {row['school_name']} -> ({row['latitude']:.4f}, {row['longitude']:.4f})")

# ── 2. WIMD ──────────────────────────────────────────
print("\n[2/3] Loading WIMD 2019 deprivation data...")
wimd = pd.read_excel(
    os.path.join(DATA_DIR, "wimd_2019.ods"),
    engine='odf',
    sheet_name='WIMD_2019_ranks',
    header=2
)
wimd.columns = [str(c).strip() for c in wimd.columns]
wimd = wimd[['LSOA code', 'LSOA name (Eng)', 'Local Authority name (Eng)', 'WIMD 2019']].dropna()
wimd.columns = ['LSOA_Code', 'LSOA_Name', 'Local_Authority', 'WIMD_2019_Rank']
wimd['WIMD_2019_Rank']   = pd.to_numeric(wimd['WIMD_2019_Rank'], errors='coerce')
wimd['WIMD_2019_Decile'] = pd.cut(wimd['WIMD_2019_Rank'], bins=10, labels=range(1, 11)).astype(int)
wimd = wimd.dropna()
print(f"  WIMD cleaned: {len(wimd)} LSOAs")
print(f"  High deprivation LSOAs (decile 1-3): {len(wimd[wimd['WIMD_2019_Decile'] <= 3])}")

# ── 3. TRANSPORT ─────────────────────────────────────
print("\n[3/3] Loading transport stops data...")
transport_path = os.path.join(DATA_DIR, "transport_stops_wales.csv")

if os.path.exists(transport_path):
    transport = pd.read_csv(transport_path, low_memory=False)
    transport['Latitude']  = pd.to_numeric(transport.get('Latitude',  pd.Series()), errors='coerce')
    transport['Longitude'] = pd.to_numeric(transport.get('Longitude', pd.Series()), errors='coerce')

    # Filter Wales bounding box
    transport = transport[
        (transport['Latitude']  > 51.3) & (transport['Latitude']  < 53.5) &
        (transport['Longitude'] > -5.5) & (transport['Longitude'] < -2.6)
    ].dropna(subset=['Latitude', 'Longitude'])
    print(f"  Transport stops in Wales: {len(transport)}")

    # Fast proximity: ~500m radius using cKDTree
    if len(transport) > 0 and len(schools) > 0:
        tree = cKDTree(transport[['Latitude', 'Longitude']].values)
        distances, _ = tree.query(schools[['latitude', 'longitude']].values, k=1)
        schools['near_transport'] = distances < 0.0045  # ~500m
        print(f"  Schools near transport: {int(schools['near_transport'].sum())} / {len(schools)}")
    else:
        schools['near_transport'] = False
else:
    print("  Transport file not found — near_transport set to False")
    schools['near_transport'] = False

# ── SAVE ─────────────────────────────────────────────
schools.to_csv(os.path.join(DATA_DIR, "schools_wales_clean.csv"), index=False)
wimd.to_csv(os.path.join(DATA_DIR, "wimd_clean.csv"), index=False)

print("\n" + "=" * 50)
print("ALL DONE! Files saved:")
print(f"   data/schools_wales_clean.csv  ({len(schools)} schools)")
print(f"   data/wimd_clean.csv           ({len(wimd)} LSOAs)")
print("=" * 50)
print("\nNext step: run  ->  streamlit run app.py")
