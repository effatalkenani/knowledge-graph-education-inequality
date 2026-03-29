"""
Generate realistic supplementary educational data for Wales schools.

Methodology:
- Each school is assigned a WIMD decile based on its Local Authority's distribution
  (since we don't have postcode-to-LSOA lookup, we use LA-level distribution
   to assign individual deciles with realistic variance)
- FSM, attendance, and GCSE rates are derived from the assigned decile
  using patterns documented in Welsh Government statistics

Data validation sources:
- Welsh Government (2023) "Free School Meals" stats: ~35-40% in decile 1, ~5-8% in decile 10
- Welsh Government (2023) "Pupil Attendance": ~90% in most deprived, ~95.5% in least deprived
- Welsh Government (2023) "GCSE Results": ~50% in decile 1, ~72% in decile 10 (A*-C equivalent)
"""
import pandas as pd
import numpy as np

np.random.seed(42)

# ── Load base data ────────────────────────────────────────────────────────────
schools = pd.read_csv('data/schools_wales_clean.csv')
wimd    = pd.read_csv('data/wimd_clean.csv')

# Fix LA name mismatch
la_map = {'The Vale of Glamorgan': 'Vale of Glamorgan'}
schools['la_mapped'] = schools['local_authority'].replace(la_map)

# ── For each school, assign a realistic WIMD decile ──────────────────────────
# Use the distribution of LSOA deciles within each LA to sample a decile
la_decile_dist = wimd.groupby('Local_Authority')['WIMD_2019_Decile'].apply(list).to_dict()

def assign_wimd_decile(la):
    """Sample a WIMD decile from the LA's actual distribution."""
    if la in la_decile_dist:
        return int(np.random.choice(la_decile_dist[la]))
    return int(np.random.randint(1, 11))

schools['wimd_decile_assigned'] = schools['la_mapped'].apply(assign_wimd_decile)

# ── Generate FSM percentage ───────────────────────────────────────────────────
# Based on Welsh Gov data: decile 1 ~38%, decile 10 ~5%
# Regression: FSM = 41 - 3.6 * decile + noise
def gen_fsm(row):
    base = 41.0 - 3.6 * row['wimd_decile_assigned']
    if 'Secondary' in str(row['school_type']):
        base *= 0.90
    elif 'Special' in str(row['school_type']):
        base *= 1.20
    noise = np.random.normal(0, 4.0)
    return max(1.5, min(80.0, round(base + noise, 1)))

schools['fsm_pct'] = schools.apply(gen_fsm, axis=1)

# ── Generate attendance rate ──────────────────────────────────────────────────
# Welsh Gov data: national avg ~93.5%, range ~88-97%
# Decile 1 ~89.5%, decile 10 ~95.5%
def gen_attendance(row):
    base = 89.5 + (row['wimd_decile_assigned'] - 1) * 0.67
    if row['near_transport']:
        base += 0.4
    noise = np.random.normal(0, 1.3)
    return max(78.0, min(99.0, round(base + noise, 1)))

schools['attendance_pct'] = schools.apply(gen_attendance, axis=1)

# ── Generate GCSE pass rate (secondary schools only) ─────────────────────────
# Welsh Gov data: decile 1 ~50%, decile 10 ~72%
def gen_gcse(row):
    if 'Secondary' not in str(row['school_type']):
        return np.nan
    base = 50.0 + (row['wimd_decile_assigned'] - 1) * 2.44
    noise = np.random.normal(0, 4.5)
    return max(28.0, min(96.0, round(base + noise, 1)))

schools['gcse_pass_pct'] = schools.apply(gen_gcse, axis=1)

# ── Create deprivation label ──────────────────────────────────────────────────
def dep_label(d):
    if d <= 3:   return 'high_deprivation'
    elif d <= 7: return 'medium_deprivation'
    else:        return 'low_deprivation'

schools['deprivation'] = schools['wimd_decile_assigned'].apply(dep_label)

# ── Save ──────────────────────────────────────────────────────────────────────
output = schools[[
    'school_name', 'school_type', 'local_authority', 'sector',
    'pupils', 'postcode', 'latitude', 'longitude', 'near_transport',
    'wimd_decile_assigned', 'deprivation',
    'fsm_pct', 'attendance_pct', 'gcse_pass_pct'
]].rename(columns={'wimd_decile_assigned': 'wimd_decile'})

output.to_csv('data/schools_enriched.csv', index=False)
print(f"Saved {len(output)} rows to data/schools_enriched.csv")

# ── Validation summary ────────────────────────────────────────────────────────
print("\n=== Validation Summary ===")
print("\nFSM by deprivation band (expected: High ~30%, Medium ~20%, Low ~12%):")
print(output.groupby('deprivation')['fsm_pct'].mean().round(1))

print("\nAttendance by deprivation band (expected: High ~91%, Medium ~93%, Low ~95%):")
print(output.groupby('deprivation')['attendance_pct'].mean().round(1))

secondary = output[output['school_type'].str.contains('Secondary', na=False)]
print(f"\nGCSE by deprivation band (expected: High ~53%, Medium ~61%, Low ~68%):")
print(secondary.groupby('deprivation')['gcse_pass_pct'].mean().round(1))

print("\nDeprivation distribution:")
print(output['deprivation'].value_counts())

print("\nWIMD decile distribution:")
print(output['wimd_decile'].value_counts().sort_index())
