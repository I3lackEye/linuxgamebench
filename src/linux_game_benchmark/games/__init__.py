"""Game definitions, registry, and finder."""

from linux_game_benchmark.games.models import GameInfo, GameSource
from linux_game_benchmark.games.game_finder import GameFinder

__all__ = ["GameInfo", "GameSource", "GameFinder"]
