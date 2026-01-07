"""
Pytest configuration and fixtures for Linux Game Benchmark client tests.

These are UNIT tests only - they test client-side functionality without
requiring a server connection.

For integration/E2E tests, see the server repository:
https://github.com/taaderbe/linuxgamebenchserver
"""

import pytest
from pathlib import Path


# =============================================================================
# Local Benchmark Results Fixtures
# =============================================================================

@pytest.fixture
def benchmark_results_dir() -> Path:
    """Path to the benchmark results directory."""
    return Path.home() / "benchmark_results"


@pytest.fixture
def sample_frametime_data() -> list:
    """Sample frametime data for testing analysis functions."""
    # Simulates 60 FPS with some variation
    return [16.67, 16.5, 16.8, 16.67, 16.9, 16.4, 16.67, 16.67, 16.8, 16.5] * 100


@pytest.fixture
def sample_benchmark_result() -> dict:
    """Sample benchmark result data structure."""
    return {
        "game": "Test Game",
        "steam_app_id": "12345",
        "fps_avg": 60.0,
        "fps_min": 45.0,
        "fps_max": 75.0,
        "fps_1low": 52.0,
        "fps_01low": 48.0,
        "stutter_rating": "good",
        "consistency_rating": "excellent",
        "resolution": "FHD",
        "duration_seconds": 120,
    }


# =============================================================================
# Pytest Hooks
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (may be skipped with -m 'not slow')"
    )
