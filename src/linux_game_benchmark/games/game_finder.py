"""
Unified Game Finder.

Searches for games across multiple sources with fallback chain:
1. Local Steam library (installed games)
2. Steam Store API (all Steam games)
3. IGDB API (optional, for non-Steam games)
4. Manual entry (fallback)
"""

from typing import Optional, Callable
from rich.console import Console
from rich.table import Table

from linux_game_benchmark.games.models import GameInfo, GameSource
from linux_game_benchmark.steam.library_scanner import SteamLibraryScanner
from linux_game_benchmark.steam.app_id_finder import (
    find_steam_app_id,
    get_multiple_matches,
    similarity,
)


class GameFinder:
    """
    Unified game finder that searches multiple sources.

    Usage:
        finder = GameFinder()
        game = finder.find("Baldur's Gate 3")
        if game:
            print(f"Found: {game.name} (App ID: {game.steam_app_id})")
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the game finder.

        Args:
            console: Rich console for output (optional)
            on_status: Callback for status messages (optional)
        """
        self.console = console or Console()
        self.on_status = on_status
        self._steam_scanner: Optional[SteamLibraryScanner] = None
        self._local_games_cache: Optional[list[dict]] = None

    def _log(self, message: str) -> None:
        """Log a status message."""
        if self.on_status:
            self.on_status(message)

    @property
    def steam_scanner(self) -> SteamLibraryScanner:
        """Lazy-load Steam scanner."""
        if self._steam_scanner is None:
            try:
                self._steam_scanner = SteamLibraryScanner()
            except FileNotFoundError:
                pass
        return self._steam_scanner

    @property
    def local_games(self) -> list[dict]:
        """Get cached list of locally installed games."""
        if self._local_games_cache is None:
            if self.steam_scanner:
                try:
                    self._local_games_cache = self.steam_scanner.scan()
                except Exception:
                    self._local_games_cache = []
            else:
                self._local_games_cache = []
        return self._local_games_cache

    def find(
        self,
        query: str,
        interactive: bool = True,
        auto_select_threshold: float = 0.95,
    ) -> Optional[GameInfo]:
        """
        Find a game by name or App ID.

        Search order:
        1. Local Steam library (installed games)
        2. Steam Store API (all Steam games)
        3. Manual entry (fallback)

        Args:
            query: Game name or Steam App ID
            interactive: If True, show selection menu for multiple matches
            auto_select_threshold: Auto-select if similarity >= this value

        Returns:
            GameInfo if found, None if user cancelled
        """
        # Try to parse as App ID first
        try:
            app_id = int(query)
            return self._find_by_app_id(app_id)
        except ValueError:
            pass

        # Search by name
        self._log(f"Suche nach '{query}'...")

        # 1. Check local Steam library
        local_result = self._search_local(query)
        if local_result:
            self._log("Gefunden in lokaler Steam-Bibliothek")
            return local_result

        # 2. Search Steam Store
        steam_results = self._search_steam_store(query)
        if steam_results:
            self._log(f"Gefunden im Steam Store ({len(steam_results)} Treffer)")

            # Auto-select if high confidence match
            if steam_results[0].similarity_score >= auto_select_threshold:
                return steam_results[0]

            # Interactive selection
            if interactive and len(steam_results) > 1:
                return self._interactive_select(steam_results, query)

            return steam_results[0]

        # 3. Fallback to manual
        self._log("Nicht gefunden - manueller Eintrag")
        return GameInfo.manual(query)

    def _find_by_app_id(self, app_id: int) -> Optional[GameInfo]:
        """Find game by Steam App ID."""
        # Check local first
        if self.steam_scanner:
            local = self.steam_scanner.get_game_by_id(app_id)
            if local:
                return GameInfo.from_steam_local(local)

        # Otherwise create from App ID
        return GameInfo(
            name=f"Steam App {app_id}",
            source=GameSource.STEAM_STORE,
            steam_app_id=app_id,
            is_installed=False,
        )

    def _search_local(self, query: str) -> Optional[GameInfo]:
        """Search local Steam library."""
        query_lower = query.lower()

        best_match: Optional[dict] = None
        best_score = 0.0

        for game in self.local_games:
            game_name = game.get("name", "").lower()

            # Exact match
            if query_lower == game_name:
                return GameInfo.from_steam_local(game)

            # Partial match
            if query_lower in game_name:
                score = similarity(query, game.get("name", ""))
                if score > best_score:
                    best_score = score
                    best_match = game

        if best_match and best_score >= 0.6:
            result = GameInfo.from_steam_local(best_match)
            result.similarity_score = best_score
            return result

        return None

    def _search_steam_store(self, query: str) -> list[GameInfo]:
        """Search Steam Store API."""
        matches = get_multiple_matches(query, limit=5)

        results = []
        for match in matches:
            game = GameInfo.from_steam_store(
                app_id=match["appid"],
                name=match["name"],
                similarity=match["similarity"],
            )
            results.append(game)

        return results

    def _interactive_select(
        self,
        games: list[GameInfo],
        original_query: str,
    ) -> Optional[GameInfo]:
        """
        Show interactive selection menu.

        Args:
            games: List of games to choose from
            original_query: Original search query

        Returns:
            Selected GameInfo or None if cancelled
        """
        self.console.print(f"\n[bold]Mehrere Treffer für '{original_query}':[/bold]")

        # Build selection table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Num", style="cyan", width=4)
        table.add_column("Name", style="white")
        table.add_column("ID", style="dim")
        table.add_column("Match", style="green")

        for i, game in enumerate(games, 1):
            match_pct = f"{game.similarity_score * 100:.0f}%"
            app_id = str(game.steam_app_id) if game.steam_app_id else "-"
            table.add_row(f"[{i}]", game.name, app_id, match_pct)

        table.add_row("[0]", "Manuell eingeben", "", "")

        self.console.print(table)

        # Get selection
        try:
            choice = input("\nAuswahl [1]: ").strip() or "1"
            choice_idx = int(choice)

            if choice_idx == 0:
                # Manual entry
                name = input("Spielname: ").strip()
                if not name:
                    name = original_query
                return GameInfo.manual(name)

            if 1 <= choice_idx <= len(games):
                return games[choice_idx - 1]

            # Invalid choice, return first match
            return games[0]

        except (ValueError, KeyboardInterrupt):
            return games[0] if games else None

    def find_all_local(self) -> list[GameInfo]:
        """Get all locally installed games as GameInfo objects."""
        return [GameInfo.from_steam_local(g) for g in self.local_games]

    def get_existing_game_names(self) -> list[str]:
        """Get list of game names from existing benchmark data."""
        from linux_game_benchmark.benchmark.storage import BenchmarkStorage

        try:
            storage = BenchmarkStorage()
            return storage.get_all_games()
        except Exception:
            return []

    def find_or_select_existing(
        self,
        query: str,
        existing_games: Optional[list[str]] = None,
    ) -> Optional[GameInfo]:
        """
        Find a game or let user select from existing benchmarked games.

        This is useful for the record_manual flow where we want to
        suggest previously benchmarked games.

        Args:
            query: Search query or selection from existing
            existing_games: List of existing game names (auto-fetched if None)

        Returns:
            GameInfo or None if cancelled
        """
        if existing_games is None:
            existing_games = self.get_existing_game_names()

        # Check if query is a number (selection from existing list)
        try:
            idx = int(query)
            if 1 <= idx <= len(existing_games):
                # User selected existing game
                game_name = existing_games[idx - 1]
                # Try to find full info for this game
                return self.find(game_name, interactive=False)
            elif idx == 0:
                # User wants to enter new game
                return None  # Signal to prompt for new name
        except ValueError:
            pass

        # Query is a game name, search for it
        return self.find(query, interactive=True)
