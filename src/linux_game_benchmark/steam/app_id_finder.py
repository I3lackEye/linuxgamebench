"""Find Steam App IDs by game name."""

import requests
from typing import Optional
from difflib import SequenceMatcher
import re

# Cache for Steam app details to avoid repeated API calls
_app_details_cache: dict[int, dict] = {}


def similarity(a: str, b: str) -> float:
    """Calculate string similarity (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_steam_app_details(app_id: int) -> Optional[dict]:
    """
    Get detailed information about a Steam app.

    Uses the Steam Store API to fetch app details including:
    - name, type, header_image, short_description
    - developers, publishers
    - categories, genres

    Args:
        app_id: The Steam App ID

    Returns:
        Dictionary with app details or None if not found
    """
    # Check cache first
    if app_id in _app_details_cache:
        return _app_details_cache[app_id]

    try:
        url = f"https://store.steampowered.com/api/appdetails"
        params = {"appids": app_id, "l": "english"}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        app_data = data.get(str(app_id), {})

        if not app_data.get("success"):
            return None

        details = app_data.get("data", {})

        # Cache the result
        _app_details_cache[app_id] = details
        return details

    except Exception:
        return None


def get_header_image_url(app_id: int) -> str:
    """
    Get the header image URL for a Steam app.

    Args:
        app_id: The Steam App ID

    Returns:
        URL to the header image (460x215)
    """
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"


def get_capsule_image_url(app_id: int, size: str = "small") -> str:
    """
    Get the capsule image URL for a Steam app.

    Args:
        app_id: The Steam App ID
        size: "small" (231x87) or "large" (616x353)

    Returns:
        URL to the capsule image
    """
    if size == "large":
        return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/capsule_616x353.jpg"
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/capsule_231x87.jpg"


def verify_steam_app_exists(app_id: int) -> bool:
    """
    Verify that a Steam app exists and is accessible.

    Args:
        app_id: The Steam App ID to verify

    Returns:
        True if the app exists, False otherwise
    """
    details = get_steam_app_details(app_id)
    return details is not None


def find_steam_app_id(game_name: str, min_similarity: float = 0.7) -> Optional[int]:
    """
    Find Steam App ID by searching the Steam Store.

    Uses Steam Store search to find matching games.

    Args:
        game_name: The game name to search for
        min_similarity: Minimum similarity score (0-1) for fuzzy matching

    Returns:
        Steam App ID if found, None otherwise
    """
    try:
        # Use Steam Store search
        url = "https://store.steampowered.com/api/storesearch/"
        params = {
            "term": game_name,
            "l": "english",
            "cc": "US"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        items = data.get("items", [])

        if not items:
            return None

        # First item is usually the best match
        # Check if it's a good enough match
        best_item = items[0]
        item_name = best_item.get("name", "")

        score = similarity(game_name, item_name)
        if score >= min_similarity:
            return best_item.get("id")

        return None

    except Exception:
        return None


def get_multiple_matches(game_name: str, limit: int = 5) -> list[dict]:
    """
    Get multiple potential matches for a game name.

    Returns:
        List of dicts with 'appid', 'name', and 'similarity' keys
    """
    try:
        # Use Steam Store search
        url = "https://store.steampowered.com/api/storesearch/"
        params = {
            "term": game_name,
            "l": "english",
            "cc": "US"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()
        items = data.get("items", [])

        # Convert to our format with similarity scores
        matches = []
        for item in items[:limit]:
            item_name = item.get("name", "")
            score = similarity(game_name, item_name)
            matches.append({
                "appid": item.get("id"),
                "name": item_name,
                "similarity": score
            })

        # Already sorted by Steam's relevance, but add similarity scores
        return matches

    except Exception:
        return []
