"""
Pytest configuration and fixtures for Linux Game Benchmark tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def benchmark_results_dir() -> Path:
    """Path to the benchmark results directory."""
    return Path("/home/derbe/benchmark_results")


@pytest.fixture
def overview_report_path(benchmark_results_dir: Path) -> Path:
    """Path to the overview report HTML file."""
    return benchmark_results_dir / "index.html"


@pytest.fixture
def overview_report_url(overview_report_path: Path) -> str:
    """URL to the overview report for browser testing."""
    return f"file://{overview_report_path}"
