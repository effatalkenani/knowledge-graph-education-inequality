import pandas as pd
import os

print("=" * 55)
print("  DATA VALIDATION CHECK — Wales Education Project")
print("=" * 55)

DATA_DIR = "data"
all_ok = True

# ─────────────────────────────────────────────────────
# 1. SCHOOLS
# ─────────────────────────────────────────────────────
print("\n📁 FILE 1: schools_wales_clean.csv")
path = os.path.join(DATA_DIR, "schools_wales_clean.csv")

if not os.path.exists(path):
    print("  ❌ FILE NOT FOUND!")
    all_ok = False
else:
    df = pd.read_csv(path)
    print(f"  ✅ Loaded — {len(df)} rows, {len(df.columns)} columns")

    # Check required columns
    required = ["school_name", "latitude", "longitude", "school_type", "local_authority"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ❌ Missing columns: {missing}")
        all_ok = False
    else:
        print(f"  ✅ All required columns present")

    # Check coordinates
    lat_ok = df["latitude"].between(51.3, 53.5).all()
    lon_ok = df["longitude"].between(-5.5, -2.6).all()
    nulls  = df[["latitude","longitude","school_name"]].isnull().sum().sum()
    print(f"  {'✅' if lat_ok else '❌'} Latitude range (51.3–53.5): {'OK' if lat_ok else 'PROBLEM'}")
    print(f"  {'✅' if lon_ok else '❌'} Longitude range (-5.5 to -2.6): {'OK' if lon_ok else 'PROBLEM'}")
    print(f"  {'✅' if nulls==0 else '⚠️'} Null values in key columns: {nulls}")

    # Sample
    print(f"\n  Sample school:")
    row = df.iloc[0]
    print(f"    Name : {row['school_name']}")
    print(f"    Type : {row.get('school_type','N/A')}")
    print(f"    LA   : {row.get('local_authority','N/A')}")
    print(f"    Lat  : {row['latitude']:.4f}  Lon: {row['longitude']:.4f}")
    if "near_transport" in df.columns:
        pct = df["near_transport"].mean() * 100
        print(f"    Near transport: {int(df['near_transport'].sum())} schools ({pct:.0f}%)")

# ─────────────────────────────────────────────────────
# 2. WIMD
# ─────────────────────────────────────────────────────
print("\n📁 FILE 2: wimd_2019.ods")
path_ods = os.path.join(DATA_DIR, "wimd_2019.ods")

if not os.path.exists(path_ods):
    print("  ❌ FILE NOT FOUND!")
    all_ok = False
else:
    try:
        wimd = pd.read_excel(path_ods, engine="odf",
                             sheet_name="WIMD_2019_ranks", header=2)
        wimd.columns = [str(c).strip() for c in wimd.columns]
        wimd = wimd[["LSOA code","LSOA name (Eng)","Local Authority name (Eng)","WIMD 2019"]].dropna()
        wimd.columns = ["LSOA_Code","LSOA_Name","Local_Authority","WIMD_2019_Rank"]
        wimd["WIMD_2019_Rank"] = pd.to_numeric(wimd["WIMD_2019_Rank"], errors="coerce")
        wimd["WIMD_2019_Decile"] = pd.cut(wimd["WIMD_2019_Rank"], bins=10, labels=range(1,11)).astype(int)
        wimd = wimd.dropna()

        print(f"  ✅ Loaded — {len(wimd)} LSOAs")
        print(f"  ✅ Rank range: {int(wimd['WIMD_2019_Rank'].min())} – {int(wimd['WIMD_2019_Rank'].max())}")

        high   = len(wimd[wimd["WIMD_2019_Decile"] <= 3])
        medium = len(wimd[(wimd["WIMD_2019_Decile"] > 3) & (wimd["WIMD_2019_Decile"] <= 7)])
        low    = len(wimd[wimd["WIMD_2019_Decile"] > 7])
        print(f"  ✅ Deprivation split:")
        print(f"     🔴 High   (decile 1-3) : {high} LSOAs")
        print(f"     🟠 Medium (decile 4-7) : {medium} LSOAs")
        print(f"     🟢 Low    (decile 8-10): {low} LSOAs")

        las = wimd["Local_Authority"].nunique()
        print(f"  ✅ Local Authorities covered: {las}")

        print(f"\n  Sample LSOA:")
        row = wimd.iloc[0]
        print(f"    Code : {row['LSOA_Code']}")
        print(f"    Name : {row['LSOA_Name']}")
        print(f"    LA   : {row['Local_Authority']}")
        print(f"    Rank : {int(row['WIMD_2019_Rank'])}  Decile: {int(row['WIMD_2019_Decile'])}")

    except Exception as e:
        print(f"  ❌ Error reading WIMD: {e}")
        all_ok = False

# ─────────────────────────────────────────────────────
# 3. TRANSPORT
# ─────────────────────────────────────────────────────
print("\n📁 FILE 3: transport_stops_wales.csv")
path = os.path.join(DATA_DIR, "transport_stops_wales.csv")

if not os.path.exists(path):
    print("  ❌ FILE NOT FOUND!")
    all_ok = False
else:
    transport = pd.read_csv(path, low_memory=False)
    print(f"  ✅ Loaded — {len(transport)} rows, {len(transport.columns)} columns")

    if "Latitude" in transport.columns and "Longitude" in transport.columns:
        transport["Latitude"]  = pd.to_numeric(transport["Latitude"],  errors="coerce")
        transport["Longitude"] = pd.to_numeric(transport["Longitude"], errors="coerce")
        wales = transport[
            (transport["Latitude"]  > 51.3) & (transport["Latitude"]  < 53.5) &
            (transport["Longitude"] > -5.5) & (transport["Longitude"] < -2.6)
        ]
        print(f"  ✅ Stops within Wales bounding box: {len(wales)}")
        if len(wales) > 1000:
            print(f"  ✅ Sufficient transport data for proximity analysis")
        else:
            print(f"  ⚠️  Low number of stops — check file content")

        if "StopType" in transport.columns:
            types = transport["StopType"].value_counts().head(3)
            print(f"  ✅ Top stop types: {dict(types)}")
    else:
        print(f"  ⚠️  Latitude/Longitude columns not found")
        print(f"      Available columns: {list(transport.columns[:8])}")

# ─────────────────────────────────────────────────────
# FINAL VERDICT
# ─────────────────────────────────────────────────────
print("\n" + "=" * 55)
if all_ok:
    print("  🎉 ALL FILES OK — Ready to run: streamlit run app.py")
else:
    print("  ⚠️  Some issues found — check messages above")
print("=" * 55)
