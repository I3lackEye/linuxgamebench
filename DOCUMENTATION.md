# Linux Game Benchmark - Documentation

## Overview

A Python-based benchmarking system for Linux gaming that uses MangoHud to capture frametime data and generates interactive HTML reports.

---

## Project Structure

```
bechmark_gaming_linux/
├── src/linux_game_benchmark/
│   ├── analysis/
│   │   ├── analyzer.py          # Calculates FPS metrics from frametimes
│   │   └── report_generator.py  # Generates HTML reports (4000+ lines)
│   ├── benchmark/
│   │   ├── runner.py            # Main benchmark runner
│   │   ├── storage.py           # Saves/loads benchmark data
│   │   └── game_launcher.py     # Launches games via Steam
│   ├── mangohud/
│   │   ├── config_manager.py    # Configures MangoHud for logging
│   │   └── log_parser.py        # Parses MangoHud CSV logs
│   ├── steam/
│   │   ├── library_scanner.py   # Finds installed Steam games
│   │   └── launch_options.py    # Modifies Steam launch options
│   └── system/
│       └── hardware_info.py     # Detects GPU, CPU, Mesa, Vulkan, etc.
├── regenerate_simple.py         # Quick script to regenerate all reports
└── DOCUMENTATION.md             # This file
```

---

## Data Storage Structure

All benchmark data is stored in `~/benchmark_results/`:

```
~/benchmark_results/
├── index.html                    # Overview report (all games)
├── {GameName}/
│   ├── report.html               # Game-specific report
│   ├── {SystemID}/               # e.g., "CachyOS_f4ee4bd2"
│   │   ├── fingerprint.json      # Hardware hash for deduplication
│   │   ├── system_info.json      # Full system details
│   │   ├── FHD/                  # 1920x1080
│   │   │   ├── run_001.json      # Metrics for run 1
│   │   │   └── run_001.csv       # Raw MangoHud frametime data
│   │   ├── WQHD/                 # 2560x1440
│   │   └── UHD/                  # 3840x2160
│   └── {AnotherSystemID}/
└── recording_session/            # Temporary MangoHud logs
```

### System ID Format
`{OS_Name}_{hash}` - e.g., `CachyOS_f4ee4bd2`

The hash is generated from: GPU, CPU, Mesa version, Vulkan version, Kernel, RAM

---

## Key Files

### 1. `report_generator.py` - The Heart of Reports

**Location:** `src/linux_game_benchmark/analysis/report_generator.py`

**Key Functions:**
- `generate_game_report()` - Single game report
- `generate_multi_system_report()` - Compare systems for one game
- `generate_overview_report()` - Main overview with all games (line ~2600)

**Important Code Sections:**

| Line Range | Purpose |
|------------|---------|
| 1-50 | Imports, STEAM_APP_IDS dict (game icons) |
| 2600-2720 | Overview data collection |
| 2760-3130 | CSS styles |
| 3130-3150 | Hover effects for Stutter/Consistency |
| 3260-3360 | Filter dropdowns (Game, Resolution, GPU, OS) |
| 3380-3450 | Detail panel stats (AVG FPS, 1% Low, etc.) |
| 3480-3530 | Run selector dropdowns (Main, Compare) |
| 3550-3600 | JavaScript: applyFilters() |
| 3830-4050 | JavaScript: updateChart() - Updates chart AND stats |
| 4050-4120 | JavaScript: updateComparisonMetrics() |

**Adding a New Game Icon:**
```python
# Line ~15-50
STEAM_APP_IDS = {
    "7 Days to Die": 251570,
    "Cities Skylines": 255710,
    "Cyberpunk 2077": 1091500,
    # Add new games here:
    "New Game Name": 123456,  # Steam App ID
}
```

### 2. `storage.py` - Data Management

**Location:** `src/linux_game_benchmark/benchmark/storage.py`

**Key Classes:**
- `SystemFingerprint` - Unique system identifier
- `BenchmarkStorage` - Save/load benchmark data

**Key Methods:**
- `save_run()` - Saves a benchmark run (auto-regenerates overview!)
- `get_all_systems_data()` - Gets all data for a game
- `regenerate_overview_report()` - Called after each save

**Resolution Mapping (line ~77):**
```python
RESOLUTION_MAP = {
    "1920x1080": "FHD",
    "2560x1440": "WQHD",
    "3840x2160": "UHD",
}
```

### 3. `hardware_info.py` - System Detection

**Location:** `src/linux_game_benchmark/system/hardware_info.py`

**Detects:**
- GPU (model, VRAM, driver, Mesa version, Vulkan version)
- CPU (model, cores, threads)
- RAM
- OS, Kernel, Desktop Environment
- Steam path, installed Proton versions

### 4. `analyzer.py` - Metrics Calculation

**Location:** `src/linux_game_benchmark/analysis/analyzer.py`

**Calculates from frametimes:**
- Average FPS
- 1% Low, 0.1% Low
- Stutter rating (Excellent/Good/Moderate/Poor)
- Consistency rating (Frame pacing)

---

## Report Features

### Overview Report (`index.html`)

- **Filters:** Game, Resolution, GPU, OS, Kernel, Mesa
- **Table:** Click row to expand details
- **Detail Panel:**
  - Stats: AVG FPS, 1% Low, 0.1% Low, Stutter, Consistency
  - FPS Timeline chart (Chart.js)
  - Run comparison (select two runs)
  - FPS reference lines (60, 120, 144, 180, 240, 360)

### Dynamic Stats Update

When selecting a different run in "Main" dropdown:
- Chart updates
- Stats (AVG FPS, 1% Low, etc.) update
- Stutter/Consistency colors update

**Implementation:** `updateChart()` function (line ~3830-4050)

---

## How Benchmarks Work

1. **MangoHud logs frametimes** to CSV during gameplay
2. **Log parser** extracts frametime values
3. **Analyzer** calculates FPS metrics
4. **Storage** saves data with system fingerprint
5. **Report generator** creates HTML reports
6. **Overview auto-regenerates** after each save

---

## Configuration

### MangoHud Config (during benchmark)

Created by `config_manager.py`:
```ini
output_folder=/home/user/benchmark_results/recording_session
log_interval=0
log_duration=0
fps
frametime
cpu_stats
gpu_stats
ram
vram
cpu_temp
gpu_temp
```

---

## Regenerating Reports

```bash
# From project root:
python regenerate_simple.py
```

Or use the storage method:
```python
from linux_game_benchmark.benchmark.storage import BenchmarkStorage
storage = BenchmarkStorage()
storage.regenerate_overview_report()
```

---

## CSS Variables (Dark Theme)

```css
:root {
    --bg: #1a1a2e;
    --card: #25274d;
    --card-alt: #2d2f5a;
    --card-hover: #2d2f5a;
    --text: #eaeaea;
    --text-muted: #a0a0a0;
    --green: #66bb6a;
    --yellow: #fdd835;
    --red: #ef5350;
    --accent: #4fc3f7;
}
```

---

## Stutter/Consistency Ratings

### Stutter Rating
| Rating | Criteria |
|--------|----------|
| Excellent | <0.2 events per 1000 frames |
| Good | <0.5 events per 1000 frames |
| Moderate | <2.0 events per 1000 frames |
| Poor | >=2.0 events or >3 sequences |

### Consistency Rating
Based on frametime variance (CV%) and FPS stability (1% Low vs Average).
Stricter at higher FPS (120+ vs 60).

---

## Common Modifications

### Add New Game Icon
Edit `report_generator.py` line ~15-50, add to `STEAM_APP_IDS` dict.

### Change Theme Colors
Edit CSS in `generate_overview_report()` around line 2760-2780.

### Add New Metric to Stats
1. Add HTML element with ID in detail-stats section (~line 3388)
2. Update `updateChart()` to set the value (~line 4010-4050)

### Add New Filter
1. Add set collection (e.g., `all_newfilter = set()`)
2. Populate in data loop
3. Add HTML select element
4. Update `applyFilters()` JavaScript

---

## Dependencies

```
Python 3.10+
MangoHud (for logging)
Steam (for game launching)
Chart.js (loaded from CDN in reports)
```

---

## File Locations Quick Reference

| What | Where |
|------|-------|
| Overview report | `~/benchmark_results/index.html` |
| Game reports | `~/benchmark_results/{Game}/report.html` |
| Raw data | `~/benchmark_results/{Game}/{SystemID}/{Resolution}/run_*.json` |
| MangoHud logs | `~/benchmark_results/recording_session/*.csv` |
| Main code | `src/linux_game_benchmark/` |
| Report generator | `src/linux_game_benchmark/analysis/report_generator.py` |

---

## Troubleshooting

### New benchmark doesn't appear
- Check if `save_run()` was called (auto-regenerates report)
- Run `python regenerate_simple.py`

### Missing game icon
- Add Steam App ID to `STEAM_APP_IDS` dict in `report_generator.py`
- Find App ID: Store page URL `store.steampowered.com/app/{APP_ID}/`

### Filter missing resolution
- Bug was fixed: All resolutions are now collected during data iteration
- Check line 2627 in `report_generator.py`

### Stats don't update on dropdown change
- Fixed: `updateChart()` now updates stats elements (line 4010-4050)
- Stats have IDs: `stat-avg-{row_id}`, `stat-low1-{row_id}`, etc.
