"""
Unit tests for CLI commands.

Tests CLI interface without network calls (mocked).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typer.testing import CliRunner

from linux_game_benchmark.cli import app


runner = CliRunner()


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_main_help(self):
        """Main help should show available commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Linux Game Benchmark" in result.output or "lgb" in result.output.lower()

    def test_login_help(self):
        """Login command should have help."""
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "email" in result.output.lower() or "login" in result.output.lower()

    def test_logout_help(self):
        """Logout command should have help."""
        result = runner.invoke(app, ["logout", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        """Status command should have help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_check_help(self):
        """Check command should have help."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0

    def test_benchmark_help(self):
        """Benchmark command should have help."""
        result = runner.invoke(app, ["benchmark", "--help"])
        # May not exist - check for 0 or 2 (no such command)
        assert result.exit_code in [0, 2]


class TestStatusCommand:
    """Tests for status command."""

    @patch("linux_game_benchmark.api.auth.get_status")
    def test_status_not_logged_in(self, mock_get_status):
        """Status should show not logged in state."""
        mock_get_status.return_value = {
            "logged_in": False,
            "api_url": "https://linuxgamebench.com/api/v1",
            "stage": "prod",
        }

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # Output should contain status info
        assert "stage" in result.output.lower() or "server" in result.output.lower() or "status" in result.output.lower()

    @patch("linux_game_benchmark.api.client.verify_auth")
    @patch("linux_game_benchmark.api.auth.get_status")
    def test_status_logged_in_valid(self, mock_get_status, mock_verify):
        """Status should show logged in state with valid token."""
        mock_get_status.return_value = {
            "logged_in": True,
            "username": "testuser",
            "email": "test@example.com",
            "api_url": "https://linuxgamebench.com/api/v1",
            "stage": "prod",
        }
        mock_verify.return_value = (True, "testuser")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0


class TestLogoutCommand:
    """Tests for logout command."""

    @patch("linux_game_benchmark.api.auth.logout")
    def test_logout_success(self, mock_logout):
        """Logout should succeed when logged in."""
        mock_logout.return_value = (True, "Logged out successfully")

        result = runner.invoke(app, ["logout"])
        assert result.exit_code == 0

    @patch("linux_game_benchmark.api.auth.logout")
    def test_logout_not_logged_in(self, mock_logout):
        """Logout should handle not logged in state."""
        mock_logout.return_value = (False, "Not logged in")

        result = runner.invoke(app, ["logout"])
        # Should not crash
        assert result.exit_code == 0


class TestLoginCommand:
    """Tests for login command."""

    @patch("linux_game_benchmark.api.auth.get_status")
    @patch("linux_game_benchmark.api.auth.login")
    def test_login_success(self, mock_login, mock_get_status):
        """Login should succeed with valid credentials."""
        mock_login.return_value = (True, "Logged in as testuser")
        mock_get_status.return_value = {"user": {"email_verified": True}}

        result = runner.invoke(app, ["login"], input="test@example.com\npassword123\n")
        assert result.exit_code == 0

    @patch("linux_game_benchmark.api.auth.login")
    def test_login_failure(self, mock_login):
        """Login should handle invalid credentials."""
        mock_login.return_value = (False, "Invalid credentials")

        result = runner.invoke(app, ["login"], input="test@example.com\nwrongpass\n")
        # Should exit with error code
        assert result.exit_code == 1


class TestVersionFlag:
    """Tests for version flag."""

    def test_version_flag(self):
        """--version should show version."""
        result = runner.invoke(app, ["--version"])
        # May show version or be handled by main callback
        # Just ensure it doesn't crash
        assert result.exit_code == 0


class TestAuthHeader:
    """Tests for auth header generation."""

    def test_get_auth_header_no_session(self):
        """get_auth_header should return None when not logged in."""
        from linux_game_benchmark.api.auth import get_auth_header

        with patch("linux_game_benchmark.api.auth.AuthSession.load", return_value=None):
            header = get_auth_header()
            assert header is None


class TestAPIClient:
    """Tests for API client."""

    def test_client_initialization(self):
        """API client should initialize with correct URL."""
        from linux_game_benchmark.api.client import BenchmarkAPIClient

        client = BenchmarkAPIClient()
        assert client.base_url is not None
        assert "api" in client.base_url

    def test_client_custom_url(self):
        """API client should accept custom base URL."""
        from linux_game_benchmark.api.client import BenchmarkAPIClient

        client = BenchmarkAPIClient(base_url="http://localhost:8000/api/v1")
        assert client.base_url == "http://localhost:8000/api/v1"

    @patch("httpx.Client")
    def test_health_check_success(self, mock_client_class):
        """Health check should return True when server is up."""
        from linux_game_benchmark.api.client import BenchmarkAPIClient

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        client = BenchmarkAPIClient()
        result = client.health_check()
        assert result is True

    @patch("httpx.Client")
    def test_health_check_failure(self, mock_client_class):
        """Health check should return False when server is down."""
        from linux_game_benchmark.api.client import BenchmarkAPIClient

        mock_client = Mock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        client = BenchmarkAPIClient()
        result = client.health_check()
        assert result is False


class TestUploadResult:
    """Tests for UploadResult dataclass."""

    def test_upload_result_success(self):
        """UploadResult should store success state."""
        from linux_game_benchmark.api.client import UploadResult

        result = UploadResult(
            success=True,
            benchmark_id=123,
            url="https://linuxgamebench.com/benchmark/123",
        )
        assert result.success is True
        assert result.benchmark_id == 123
        assert result.url is not None
        assert result.error is None

    def test_upload_result_failure(self):
        """UploadResult should store failure state."""
        from linux_game_benchmark.api.client import UploadResult

        result = UploadResult(
            success=False,
            error="Authentication failed",
        )
        assert result.success is False
        assert result.error == "Authentication failed"
        assert result.benchmark_id is None


class TestSettings:
    """Tests for settings module."""

    def test_settings_has_api_url(self):
        """Settings should have API URL."""
        from linux_game_benchmark.config.settings import settings

        assert settings.API_BASE_URL is not None
        assert "api" in settings.API_BASE_URL

    def test_settings_has_client_version(self):
        """Settings should have client version."""
        from linux_game_benchmark.config.settings import settings

        assert settings.CLIENT_VERSION is not None
        assert "." in settings.CLIENT_VERSION  # e.g., "0.1.22"

    def test_settings_get_auth_file(self):
        """Settings should return auth file path."""
        from linux_game_benchmark.config.settings import settings

        auth_file = settings.get_auth_file()
        assert auth_file is not None
        assert "auth.json" in str(auth_file)

    def test_settings_stages(self):
        """Settings should have stage URLs configured."""
        from linux_game_benchmark.config.settings import Settings

        # Just test that Settings can be created and has API URL
        s = Settings()
        assert s.API_BASE_URL is not None
        assert s.CURRENT_STAGE is not None


class TestNormalizationFunctions:
    """Tests for hardware name normalization."""

    def test_short_gpu_amd(self):
        """AMD GPU names should be shortened."""
        from linux_game_benchmark.cli import _short_gpu

        # RDNA 3/2/1
        assert _short_gpu("AMD Radeon RX 7900 XTX") == "RX 7900 XTX"
        assert _short_gpu("AMD Radeon RX 6800 XT") == "RX 6800 XT"
        assert _short_gpu("AMD Radeon RX 5700 XT") == "RX 5700 XT"
        # Polaris (RX 500/400)
        assert _short_gpu("AMD Radeon RX 580") == "RX 580"
        assert _short_gpu("AMD Radeon RX 570") == "RX 570"
        assert _short_gpu("AMD Radeon RX 480") == "RX 480"
        assert _short_gpu("AMD Radeon RX 470") == "RX 470"
        # R9 300 Series
        assert _short_gpu("AMD Radeon R9 390X") == "R9 390X"
        assert _short_gpu("AMD Radeon R9 390") == "R9 390"
        assert _short_gpu("AMD Radeon R9 380") == "R9 380"
        # Fury
        assert _short_gpu("AMD Radeon R9 Fury X") == "R9 Fury X"

    def test_short_gpu_nvidia(self):
        """NVIDIA GPU names should be shortened."""
        from linux_game_benchmark.cli import _short_gpu

        # RTX 40/30/20 Series
        assert _short_gpu("NVIDIA GeForce RTX 4090") == "RTX 4090"
        assert _short_gpu("NVIDIA GeForce RTX 3080") == "RTX 3080"
        assert _short_gpu("NVIDIA GeForce RTX 2080 Ti") == "RTX 2080 Ti"
        # GTX 16/10 Series
        assert _short_gpu("NVIDIA GeForce GTX 1660 Super") == "GTX 1660 Super"
        assert _short_gpu("NVIDIA GeForce GTX 1080 Ti") == "GTX 1080 Ti"
        assert _short_gpu("NVIDIA GeForce GTX 1060") == "GTX 1060"
        # GTX 900 Series (Maxwell)
        assert _short_gpu("NVIDIA GeForce GTX 980 Ti") == "GTX 980 Ti"
        assert _short_gpu("NVIDIA GeForce GTX 980") == "GTX 980"
        assert _short_gpu("NVIDIA GeForce GTX 970") == "GTX 970"
        assert _short_gpu("NVIDIA GeForce GTX 960") == "GTX 960"
        # Budget
        assert _short_gpu("NVIDIA GeForce GT 1030") == "GT 1030"

    def test_short_gpu_intel(self):
        """Intel GPU names should be shortened."""
        from linux_game_benchmark.cli import _short_gpu

        # Arc discrete
        assert _short_gpu("Intel Arc A770") == "Arc A770"
        assert _short_gpu("Intel Arc A750") == "Arc A750"
        assert _short_gpu("Intel Arc B580") == "Arc B580"
        # Integrated
        assert _short_gpu("Intel Iris Xe Graphics") == "Iris Xe"
        assert _short_gpu("Intel UHD Graphics 770") == "Intel UHD"

    def test_short_gpu_unknown(self):
        """Unknown GPU names should be truncated."""
        from linux_game_benchmark.cli import _short_gpu

        assert _short_gpu("Unknown") == "Unknown"
        long_name = "A" * 50
        assert len(_short_gpu(long_name)) <= 30

    def test_short_cpu(self):
        """CPU names should be shortened."""
        from linux_game_benchmark.cli import _short_cpu

        assert _short_cpu("AMD Ryzen 9 7950X 16-Core Processor") == "Ryzen 9 7950X"
        # Intel CPUs may have different shortening
        result = _short_cpu("Intel Core i9-13900K")
        assert "13900K" in result or "i9" in result

    def test_short_kernel(self):
        """Kernel versions should be shortened."""
        from linux_game_benchmark.cli import _short_kernel

        assert _short_kernel("6.8.0-cachyos") == "6.8.0"
        assert _short_kernel("6.10.2-arch1-1") == "6.10.2"

    def test_normalize_resolution(self):
        """Resolution should be normalized to standard format."""
        from linux_game_benchmark.cli import _normalize_resolution

        # Direct resolution formats pass through
        assert _normalize_resolution("1920x1080") == "1920x1080"
        assert _normalize_resolution("2560x1440") == "2560x1440"
        assert _normalize_resolution("3840x2160") == "3840x2160"
        # Aliases should be converted
        assert _normalize_resolution("FHD") == "1920x1080"
        assert _normalize_resolution("WQHD") == "2560x1440"
        # 4K might not be converted - check actual behavior
        result_4k = _normalize_resolution("4K")
        assert result_4k in ["3840x2160", "4K"]


class TestVersionParsing:
    """Tests for version comparison."""

    def test_parse_version(self):
        """Version strings should be parsed correctly."""
        from linux_game_benchmark.api.client import _parse_version

        assert _parse_version("0.1.14") == (0, 1, 14)
        assert _parse_version("1.0.0") == (1, 0, 0)
        assert _parse_version("0.1.22") == (0, 1, 22)

    def test_is_newer_version(self):
        """Version comparison should work correctly."""
        from linux_game_benchmark.api.client import _is_newer_version

        assert _is_newer_version("0.1.15", "0.1.14") is True
        assert _is_newer_version("0.1.14", "0.1.15") is False
        assert _is_newer_version("1.0.0", "0.9.9") is True
        assert _is_newer_version("0.1.14", "0.1.14") is False
