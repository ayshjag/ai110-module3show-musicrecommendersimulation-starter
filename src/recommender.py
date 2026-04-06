import csv
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """Represents a single song and its audio attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    # Challenge 1: advanced features (defaults keep existing tests working)
    popularity: int = 50        # 0–100 chart/stream popularity
    release_decade: int = 2020  # decade of release: 1960, 1970, … 2020
    sub_mood: str = ""          # fine-grained mood tag e.g. euphoric, dreamy


@dataclass
class UserProfile:
    """Stores a listener's taste preferences used for scoring."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    # Challenge 1: advanced preferences (all optional with safe defaults)
    preferred_sub_mood: str = ""  # "" = no sub-mood preference
    preferred_decade: int = 0     # 0  = no era preference
    min_popularity: int = 0       # 0  = no popularity floor


# ---------------------------------------------------------------------------
# Challenge 2 — Scoring modes (Strategy pattern)
#
# Each mode is a complete weight dictionary.  Swap the mode name in
# recommend_songs() or Recommender.recommend() to change ranking behaviour.
# ---------------------------------------------------------------------------

SCORING_MODES: Dict[str, Dict[str, float]] = {
    # All signals in play; genre slightly dominant
    "balanced": {
        "genre":      2.0,
        "mood":       1.5,
        "energy":     1.0,
        "acoustic":   0.5,
        "sub_mood":   1.0,
        "popularity": 0.3,
        "decade":     0.3,
    },
    # Genre label overrides everything — strong genre loyalty
    "genre_first": {
        "genre":      4.0,
        "mood":       1.0,
        "energy":     0.5,
        "acoustic":   0.2,
        "sub_mood":   0.5,
        "popularity": 0.2,
        "decade":     0.2,
    },
    # Mood + sub-mood dominate — context-driven listening (study, workout)
    "mood_first": {
        "genre":      1.0,
        "mood":       3.0,
        "energy":     0.5,
        "acoustic":   0.3,
        "sub_mood":   2.0,
        "popularity": 0.2,
        "decade":     0.2,
    },
    # Energy proximity dominates — pure sonic intensity matching
    "energy_focused": {
        "genre":      0.5,
        "mood":       0.5,
        "energy":     3.5,
        "acoustic":   0.5,
        "sub_mood":   0.3,
        "popularity": 0.2,
        "decade":     0.2,
    },
    # Discovery mode — surfaces obscure gems; penalises high-popularity tracks
    "discovery": {
        "genre":      1.5,
        "mood":       1.5,
        "energy":     1.0,
        "acoustic":   0.5,
        "sub_mood":   1.0,
        "popularity": -0.5,  # negative weight: popular songs score lower
        "decade":     0.3,
    },
}

# WEIGHTS references the default mode so the experiment runner in main.py
# can still mutate individual keys without importing SCORING_MODES directly.
WEIGHTS = SCORING_MODES["balanced"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _max_score(weights: Dict[str, float]) -> float:
    """Returns the theoretical maximum score for a given weight set."""
    return sum(v for v in weights.values() if v > 0)


def _compute_score(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    fav_genre: str,
    fav_mood: str,
    target_energy: float,
    likes_acoustic: bool,
    # Challenge 1 — advanced signals
    sub_mood: str = "",
    popularity: int = 50,
    release_decade: int = 2020,
    preferred_sub_mood: str = "",
    preferred_decade: int = 0,
    weights: Dict[str, float] = None,
) -> Tuple[float, List[str]]:
    """
    Returns (total_score, reasons) for one song against one user profile.

    Scoring formula
    ---------------
    genre match       +w if song.genre == user.favorite_genre
    mood match        +w if song.mood  == user.favorite_mood
    energy proximity  +w * (1 - |song.energy - target_energy|)
    acoustic texture  +w * (acousticness or 1-acousticness)
    sub_mood match    +w if song.sub_mood == preferred_sub_mood (when set)
    popularity        +w * (popularity / 100)  [negative w = discovery mode]
    decade proximity  +w * (1 - |song_decade - preferred_decade| / 60)  (when set)
    """
    if weights is None:
        weights = SCORING_MODES["balanced"]

    score = 0.0
    reasons: List[str] = []

    # --- genre ---
    if genre == fav_genre:
        pts = weights["genre"]
        score += pts
        reasons.append(f"genre '{genre}' (+{pts:.1f})")

    # --- mood ---
    if mood == fav_mood:
        pts = weights["mood"]
        score += pts
        reasons.append(f"mood '{mood}' (+{pts:.1f})")

    # --- energy proximity ---
    proximity = 1.0 - abs(energy - target_energy)
    pts = weights["energy"] * proximity
    score += pts
    reasons.append(f"energy {energy:.2f}→{target_energy:.2f} (+{pts:.2f})")

    # --- acoustic texture ---
    raw = acousticness if likes_acoustic else (1.0 - acousticness)
    pts = weights["acoustic"] * raw
    score += pts
    label = "acoustic" if likes_acoustic else "electronic"
    reasons.append(f"{label} {acousticness:.2f} (+{pts:.2f})")

    # --- sub-mood (Challenge 1) ---
    if preferred_sub_mood and sub_mood == preferred_sub_mood:
        pts = weights["sub_mood"]
        score += pts
        reasons.append(f"sub-mood '{sub_mood}' (+{pts:.1f})")

    # --- popularity (Challenge 1) ---
    pop_raw = popularity / 100.0
    pts = weights["popularity"] * pop_raw
    score += pts
    sign = "+" if pts >= 0 else ""
    reasons.append(f"popularity {popularity} ({sign}{pts:.2f})")

    # --- release decade (Challenge 1, only when user has a preference) ---
    if preferred_decade != 0:
        max_gap = 60.0  # 1960 → 2020
        decade_proximity = max(0.0, 1.0 - abs(release_decade - preferred_decade) / max_gap)
        pts = weights["decade"] * decade_proximity
        score += pts
        reasons.append(f"decade {release_decade}→{preferred_decade} (+{pts:.2f})")

    return round(score, 4), reasons


# ---------------------------------------------------------------------------
# Challenge 3 — Diversity re-ranker
# ---------------------------------------------------------------------------

def _apply_diversity(
    scored: List[Tuple[Dict, float, str]],
    k: int,
    max_per_artist: int = 2,
    max_per_genre: int = 2,
) -> List[Tuple[Dict, float, str]]:
    """
    Greedy diversity filter: iterates the score-sorted list and skips any song
    that would push a single artist or genre past its allowed quota.

    This runs *after* scoring, so it never changes scores — only selection.
    """
    results: List[Tuple[Dict, float, str]] = []
    artist_counts: Dict[str, int] = {}
    genre_counts: Dict[str, int] = {}

    for item in scored:
        song, _, _ = item
        artist, genre = song["artist"], song["genre"]

        if artist_counts.get(artist, 0) >= max_per_artist:
            continue
        if genre_counts.get(genre, 0) >= max_per_genre:
            continue

        results.append(item)
        artist_counts[artist] = artist_counts.get(artist, 0) + 1
        genre_counts[genre] = genre_counts.get(genre, 0) + 1

        if len(results) == k:
            break

    return results


# ---------------------------------------------------------------------------
# Functional API  (used by src/main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Reads songs.csv and returns a list of dicts with correctly typed values."""
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":             int(row["id"]),
                "title":          row["title"],
                "artist":         row["artist"],
                "genre":          row["genre"],
                "mood":           row["mood"],
                "energy":         float(row["energy"]),
                "tempo_bpm":      float(row["tempo_bpm"]),
                "valence":        float(row["valence"]),
                "danceability":   float(row["danceability"]),
                "acousticness":   float(row["acousticness"]),
                "popularity":     int(row.get("popularity", 50)),
                "release_decade": int(row.get("release_decade", 2020)),
                "sub_mood":       row.get("sub_mood", ""),
            })
    print(f"Loaded songs: {len(songs)}")
    return songs


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
    diverse: bool = False,
    max_per_artist: int = 2,
    max_per_genre: int = 2,
) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song against user_prefs and returns the top-k results.

    Parameters
    ----------
    mode          : one of the keys in SCORING_MODES (default 'balanced')
    diverse       : if True, apply the diversity re-ranker after scoring
    max_per_artist: max songs from one artist in the final list (diversity only)
    max_per_genre : max songs from one genre in the final list (diversity only)

    Returns a list of (song_dict, score, explanation) tuples.
    Uses sorted() so the original list is never mutated.
    """
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    min_pop = int(user_prefs.get("min_popularity", 0))

    # Optional hard filter: exclude songs below the user's popularity floor
    catalog = [s for s in songs if s["popularity"] >= min_pop]

    scored: List[Tuple[Dict, float, str]] = []
    for song in catalog:
        total, reasons = _compute_score(
            genre=song["genre"],
            mood=song["mood"],
            energy=song["energy"],
            acousticness=song["acousticness"],
            fav_genre=user_prefs.get("genre", ""),
            fav_mood=user_prefs.get("mood", ""),
            target_energy=float(user_prefs.get("target_energy", 0.5)),
            likes_acoustic=bool(user_prefs.get("likes_acoustic", False)),
            sub_mood=song.get("sub_mood", ""),
            popularity=song.get("popularity", 50),
            release_decade=song.get("release_decade", 2020),
            preferred_sub_mood=user_prefs.get("preferred_sub_mood", ""),
            preferred_decade=int(user_prefs.get("preferred_decade", 0)),
            weights=weights,
        )
        scored.append((song, total, " | ".join(reasons)))

    ranked = sorted(scored, key=lambda x: x[1], reverse=True)

    if diverse:
        return _apply_diversity(ranked, k, max_per_artist, max_per_genre)
    return ranked[:k]


# ---------------------------------------------------------------------------
# OOP API  (used by tests/test_recommender.py)
# ---------------------------------------------------------------------------

class Recommender:
    """Wraps a song catalog and exposes recommend / explain methods."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score_song(
        self,
        user: UserProfile,
        song: Song,
        mode: str = "balanced",
    ) -> Tuple[float, List[str]]:
        """Returns (score, reasons) for a single Song dataclass."""
        weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
        return _compute_score(
            genre=song.genre,
            mood=song.mood,
            energy=song.energy,
            acousticness=song.acousticness,
            fav_genre=user.favorite_genre,
            fav_mood=user.favorite_mood,
            target_energy=user.target_energy,
            likes_acoustic=user.likes_acoustic,
            sub_mood=song.sub_mood,
            popularity=song.popularity,
            release_decade=song.release_decade,
            preferred_sub_mood=user.preferred_sub_mood,
            preferred_decade=user.preferred_decade,
            weights=weights,
        )

    def recommend(
        self,
        user: UserProfile,
        k: int = 5,
        mode: str = "balanced",
        diverse: bool = False,
        max_per_artist: int = 2,
        max_per_genre: int = 2,
    ) -> List[Song]:
        """Returns the top-k Song objects ranked by relevance score."""
        ranked = sorted(
            self.songs,
            key=lambda s: self._score_song(user, s, mode)[0],
            reverse=True,
        )
        if diverse:
            # Build a lightweight dict representation for _apply_diversity
            scored = [
                ({"artist": s.artist, "genre": s.genre, "_song": s},
                 self._score_song(user, s, mode)[0], "")
                for s in ranked
            ]
            diverse_items = _apply_diversity(scored, k, max_per_artist, max_per_genre)
            return [item[0]["_song"] for item in diverse_items]
        return ranked[:k]

    def explain_recommendation(
        self,
        user: UserProfile,
        song: Song,
        mode: str = "balanced",
    ) -> str:
        """Returns a human-readable explanation of why a song was recommended."""
        _, reasons = self._score_song(user, song, mode)
        return " | ".join(reasons)
