"""Check earliest available date for each BLS series."""
import json
from models.real_data import fetch_bls_data

# All series we use
SERIES = {
    "UR (CPS)":       "LNS14000000",
    "LFPR (CPS)":     "LNS11300000",
    "EPOP (CPS)":     "LNS12300000",
    "JO Rate (JOLTS)": "JTS000000000000000JOR",
    "Hires Rate (JOLTS)": "JTS000000000000000HIR",   # rate version
    "Hires Level (JOLTS)": "JTS000000000000000HIL",
    "Quits Rate (JOLTS)": "JTS000000000000000QUR",
    "Layoffs Rate (JOLTS)": "JTS000000000000000LDR",
}

# Fetch with wide range
print("Fetching BLS data from 2000 to 2025...")
raw = fetch_bls_data(list(SERIES.values()), start_year=2000, end_year=2025)

print(f"\n{'Series':<25} {'ID':<35} {'Earliest':<12} {'Latest':<12} {'N months':>8}")
print("-" * 95)
for name, sid in SERIES.items():
    if sid in raw and raw[sid]:
        data = sorted(raw[sid], key=lambda x: (x[0], x[1]))
        earliest = f"{data[0][0]}-{data[0][1]:02d}"
        latest = f"{data[-1][0]}-{data[-1][1]:02d}"
        n = len(data)
    else:
        earliest = latest = "N/A"
        n = 0
    print(f"{name:<25} {sid:<35} {earliest:<12} {latest:<12} {n:>8}")

# Calculate three history definitions
print("\n\n=== History Definitions ===")

# Collect earliest dates
starts = {}
for name, sid in SERIES.items():
    if sid in raw and raw[sid]:
        data = sorted(raw[sid])
        starts[name] = (data[0][0], data[0][1])

if starts:
    # Definition A: All targets common
    all_start = max(starts.values())
    print(f"\nA (All targets): starts {all_start[0]}-{all_start[1]:02d}")
    
    # Definition B: Macro core only (UR, LFPR, EPOP)
    macro = {k: v for k, v in starts.items() if "CPS" in k}
    macro_start = max(macro.values()) if macro else (2014, 1)
    print(f"B (Macro core UR/LFPR/EPOP): starts {macro_start[0]}-{macro_start[1]:02d}")
    
    # Definition C: ABM experiment (CPS + JOLTS env)
    abm = {k: v for k, v in starts.items() if k in ["UR (CPS)", "LFPR (CPS)", "EPOP (CPS)",
                                                       "JO Rate (JOLTS)", "Layoffs Rate (JOLTS)"]}
    abm_start = max(abm.values()) if abm else (2014, 1)
    print(f"C (ABM experiment): starts {abm_start[0]}-{abm_start[1]:02d}")
    
    # Common end
    all_end = min(max(sorted(raw[sid])[-1] for sid in raw if raw[sid]),
                  (2025, 3))
    print(f"\nCommon end: ~{all_end[0]}-{all_end[1]:02d}")
