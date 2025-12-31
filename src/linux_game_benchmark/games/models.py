"""
Game data models for the game finder system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GameSource(Enum):
    """Source where the game was found."""

    STEAM_LOCAL = "steam_local"  # Installed in local Steam library
    STEAM_STORE = "steam_store"  # Found via Steam Store API (not installed)
    IGDB = "igdb"  # Found via IGDB API
    STEAMGRIDDB = "steamgriddb"  # Found via SteamGridDB
    MANUAL = "manual"  # Manually entered by user


@dataclass
class GameInfo:
    """
    Unified game information from various sources.

    This class represents a game found from any source (Steam, IGDB, etc.)
    with all relevant metadata needed for benchmarking and reporting.
    """

    name: str
    source: GameSource

    # Steam-specific
    steam_app_id: Optional[int] = None
    install_dir: Optional[str] = None

    # IGDB-specific
    igdb_id: Optional[int] = None

    # Common metadata
    cover_url: Optional[str] = None
    is_installed: bool = False

    # Benchmark info
    has_builtin_benchmark: bool = False
    benchmark_args: list[str] = field(default_factory=list)

    # Search metadata
    similarity_score: float = 0.0

    def get_cover_url(self) -> Optional[str]:
        """
        Get the best available cover URL.

        Priority: Steam CDN > provided cover_url > None
        """
        if self.steam_app_id:
            return (
                f"https://cdn.cloudflare.steamstatic.com/steam/apps/"
                f"{self.steam_app_id}/header.jpg"
            )
        return self.cover_url

    def get_display_source(self) -> str:
        """Get human-readable source name."""
        source_names = {
            GameSource.STEAM_LOCAL: "Steam (installiert)",
            GameSource.STEAM_STORE: "Steam Store",
            GameSource.IGDB: "IGDB",
            GameSource.STEAMGRIDDB: "SteamGridDB",
            GameSource.MANUAL: "Manuell",
        }
        return source_names.get(self.source, str(self.source))

    @classmethod
    def from_steam_local(cls, steam_game: dict) -> "GameInfo":
        """Create GameInfo from local Steam library scanner result."""
        return cls(
            name=steam_game.get("name", "Unknown"),
            source=GameSource.STEAM_LOCAL,
            steam_app_id=steam_game.get("app_id"),
            install_dir=steam_game.get("install_dir"),
            is_installed=True,
            has_builtin_benchmark=steam_game.get("has_builtin_benchmark", False),
            benchmark_args=steam_game.get("benchmark_args", []),
        )

    @classmethod
    def from_steam_store(
        cls,
        app_id: int,
        name: str,
        similarity: float = 0.0,
    ) -> "GameInfo":
        """Create GameInfo from Steam Store API result."""
        return cls(
            name=name,
            source=GameSource.STEAM_STORE,
            steam_app_id=app_id,
            is_installed=False,
            similarity_score=similarity,
        )

    @classmethod
    def manual(cls, name: str) -> "GameInfo":
        """Create GameInfo for manually entered game."""
        return cls(
            name=name,
            source=GameSource.MANUAL,
            is_installed=False,
        )
