#!/usr/bin/env python3
"""Import local benchmarks to server database with full data including frametimes."""

import json
import sqlite3
import gzip
import base64
import hashlib
from pathlib import Path

# Server database path
DB_PATH = "/opt/lgb/benchmarks.db"
LOCAL_RESULTS = Path("/home/derbe/benchmark_results")

# Resolution mapping
RES_MAP = {
    "3840x2160": "UHD",
    "2560x1440": "WQHD",
    "1920x1080": "FHD",
}

# Steam App IDs
STEAM_APP_IDS = {
    "7 Days to Die": 251570,
    "Cities Skylines": 255710,
    "Cyberpunk 2077": 1091500,
    "Path of Exile": 238960,
    "Path of Exile 2": 2694490,
    "Rise of the Tomb Raider": 391220,
    "Shadow of the Tomb Raider": 750920,
    "Metro Exodus": 412020,
    "Factorio": 427520,
}


def shorten_gpu(model):
    """Shorten GPU name."""
    if not model:
        return "Unknown"
    if "7900 XTX" in model:
        return "RX 7900 XTX"
    if "7900 XT" in model and "XTX" not in model:
        return "RX 7900 XT"
    if "7800 XT" in model:
        return "RX 7800 XT"
    if "Iris" in model and "Xe" in model:
        if "TGL" in model:
            return "Iris Xe (TGL)"
        return "Iris Xe"
    if "RTX 4090" in model:
        return "RTX 4090"
    if "RTX 4080" in model:
        return "RTX 4080"
    if "RTX 4070" in model:
        return "RTX 4070"
    parts = model.split("(")[0].strip()
    return parts[:40] if len(parts) > 40 else parts


def shorten_cpu(model):
    """Shorten CPU name."""
    if not model:
        return "Unknown"
    if "9800X3D" in model:
        return "Ryzen 7 9800X3D"
    if "i5-1135G7" in model:
        return "i5-1135G7"
    return " ".join(model.split()[:4])


def compress_frametimes(frametimes):
    """Compress frametimes for storage."""
    if not frametimes:
        return ""
    json_data = json.dumps(frametimes)
    compressed = gzip.compress(json_data.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')


def init_db(cursor):
    """Initialize database tables."""
    # Games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            steam_app_id INTEGER DEFAULT 0
        )
    """)

    # Systems table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_hash TEXT NOT NULL UNIQUE,
            os TEXT,
            kernel TEXT,
            gpu TEXT,
            gpu_driver TEXT,
            cpu TEXT,
            ram_gb INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Benchmark groups
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            system_id INTEGER NOT NULL,
            resolution TEXT NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (system_id) REFERENCES systems(id),
            UNIQUE(game_id, system_id, resolution)
        )
    """)

    # Runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            run_number INTEGER NOT NULL,
            timestamp TEXT,
            fps_avg REAL,
            fps_min REAL,
            fps_max REAL,
            fps_median REAL,
            fps_1low REAL,
            fps_01low REAL,
            fps_std_dev REAL,
            frame_count INTEGER,
            duration_seconds REAL,
            stutter_rating TEXT,
            stutter_index REAL,
            stutter_event_count INTEGER,
            consistency_rating TEXT,
            consistency_score REAL,
            cv_percent REAL,
            fps_stability REAL,
            frametimes_compressed TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES benchmark_groups(id)
        )
    """)


def import_benchmarks():
    """Import all benchmarks from local results with full data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Initialize tables
    init_db(cursor)

    # Clear existing data
    cursor.execute("DELETE FROM runs")
    cursor.execute("DELETE FROM benchmark_groups")
    cursor.execute("DELETE FROM systems")
    cursor.execute("DELETE FROM games")
    conn.commit()
    print("Cleared existing data")

    games_cache = {}
    systems_cache = {}
    groups_cache = {}
    imported_runs = 0

    # Iterate through game directories
    for game_dir in LOCAL_RESULTS.iterdir():
        if not game_dir.is_dir():
            continue
        if game_dir.name.startswith('.'):
            continue
        if game_dir.name in ('recording_session',):
            continue
        if '_session_' in game_dir.name:
            continue

        game_name = game_dir.name.replace('_', ' ')
        steam_app_id = STEAM_APP_IDS.get(game_name, 0)

        # Get or create game
        if game_name not in games_cache:
            cursor.execute("INSERT OR IGNORE INTO games (name, steam_app_id) VALUES (?, ?)",
                          (game_name, steam_app_id))
            cursor.execute("SELECT id FROM games WHERE name = ?", (game_name,))
            games_cache[game_name] = cursor.fetchone()[0]

        game_id = games_cache[game_name]

        # Look for system directories
        for system_dir in game_dir.iterdir():
            if not system_dir.is_dir():
                continue

            # Read system info
            sys_info_path = system_dir / "system_info.json"
            if not sys_info_path.exists():
                continue

            with open(sys_info_path) as f:
                sys_info = json.load(f)

            gpu_info = sys_info.get("gpu", {})
            cpu_info = sys_info.get("cpu", {})
            os_info = sys_info.get("os", {})

            gpu = shorten_gpu(gpu_info.get("model", "Unknown"))
            cpu = shorten_cpu(cpu_info.get("model", "Unknown"))
            os_name = os_info.get("name", "Linux")
            kernel = os_info.get("kernel", "").split("-")[0]
            mesa = gpu_info.get("driver_version", "")
            ram_gb = int(sys_info.get("ram", {}).get("total_gb", 0))

            # Create system hash
            system_hash = hashlib.md5(f"{os_name}_{gpu}_{cpu}".encode()).hexdigest()[:8]

            # Get or create system
            if system_hash not in systems_cache:
                cursor.execute("""
                    INSERT OR IGNORE INTO systems (system_hash, os, kernel, gpu, gpu_driver, cpu, ram_gb)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (system_hash, os_name, kernel, gpu, mesa, cpu, ram_gb))
                cursor.execute("SELECT id FROM systems WHERE system_hash = ?", (system_hash,))
                systems_cache[system_hash] = cursor.fetchone()[0]

            system_id = systems_cache[system_hash]

            # Look for resolution directories
            for res_dir in system_dir.iterdir():
                if not res_dir.is_dir():
                    continue
                if res_dir.name not in ('FHD', 'WQHD', 'UHD', '1920x1080', '2560x1440', '3840x2160'):
                    continue

                resolution = res_dir.name
                if resolution not in RES_MAP.values():
                    resolution = RES_MAP.get(resolution, resolution)

                # Get or create benchmark group
                group_key = (game_id, system_id, resolution)
                if group_key not in groups_cache:
                    cursor.execute("""
                        INSERT OR IGNORE INTO benchmark_groups (game_id, system_id, resolution)
                        VALUES (?, ?, ?)
                    """, group_key)
                    cursor.execute("""
                        SELECT id FROM benchmark_groups
                        WHERE game_id = ? AND system_id = ? AND resolution = ?
                    """, group_key)
                    groups_cache[group_key] = cursor.fetchone()[0]

                group_id = groups_cache[group_key]

                # Find all run files
                for run_file in sorted(res_dir.glob("run_*.json")):
                    with open(run_file) as f:
                        run_data = json.load(f)

                    run_number = run_data.get("run_number", 1)
                    timestamp = run_data.get("timestamp", "")
                    metrics = run_data.get("metrics", {})
                    fps = metrics.get("fps", {})
                    stutter = metrics.get("stutter", {})
                    frame_pacing = metrics.get("frame_pacing", {})
                    frametimes = run_data.get("frametimes", [])

                    # Compress frametimes
                    frametimes_compressed = compress_frametimes(frametimes)

                    cursor.execute("""
                        INSERT INTO runs (
                            group_id, run_number, timestamp,
                            fps_avg, fps_min, fps_max, fps_median, fps_1low, fps_01low, fps_std_dev,
                            frame_count, duration_seconds,
                            stutter_rating, stutter_index, stutter_event_count,
                            consistency_rating, consistency_score, cv_percent, fps_stability,
                            frametimes_compressed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        group_id,
                        run_number,
                        timestamp,
                        fps.get("average"),
                        fps.get("minimum"),
                        fps.get("maximum"),
                        fps.get("median"),
                        fps.get("1_percent_low"),
                        fps.get("0.1_percent_low"),
                        fps.get("std_dev"),
                        fps.get("frame_count"),
                        fps.get("duration_seconds"),
                        (stutter.get("stutter_rating") or "").capitalize(),
                        stutter.get("stutter_index"),
                        stutter.get("event_count"),
                        (frame_pacing.get("consistency_rating") or "").capitalize(),
                        frame_pacing.get("consistency_score"),
                        frame_pacing.get("cv_percent"),
                        frame_pacing.get("fps_stability"),
                        frametimes_compressed,
                    ))
                    imported_runs += 1

    conn.commit()
    conn.close()

    print(f"Imported {len(games_cache)} games, {len(systems_cache)} systems, {len(groups_cache)} groups, {imported_runs} runs")


if __name__ == "__main__":
    import_benchmarks()
