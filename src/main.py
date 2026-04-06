"""
Command line runner for the Music Recommender Simulation.

Usage
-----
python -m src.main                   # default: all profiles, balanced mode
python -m src.main --modes           # compare all scoring modes for one profile
python -m src.main --diversity       # show diversity penalty in action
"""

import os
import sys

try:
    from tabulate import tabulate
    _HAS_TABULATE = True
except ImportError:
    _HAS_TABULATE = False

from src.recommender import load_songs, recommend_songs, SCORING_MODES, _max_score

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

# ---------------------------------------------------------------------------
# User profiles — standard + adversarial + advanced (Challenge 1 fields added)
# ---------------------------------------------------------------------------

PROFILES = {
    "chill_lofi_fan": {
        "genre":              "lofi",
        "mood":               "chill",
        "target_energy":      0.40,
        "likes_acoustic":     True,
        "preferred_sub_mood": "dreamy",
        "preferred_decade":   2020,
        "min_popularity":     0,
    },
    "pop_party_goer": {
        "genre":              "pop",
        "mood":               "happy",
        "target_energy":      0.85,
        "likes_acoustic":     False,
        "preferred_sub_mood": "euphoric",
        "preferred_decade":   2020,
        "min_popularity":     60,   # only wants well-known tracks
    },
    "late_night_driver": {
        "genre":              "synthwave",
        "mood":               "moody",
        "target_energy":      0.75,
        "likes_acoustic":     False,
        "preferred_sub_mood": "melancholic",
        "preferred_decade":   2020,
        "min_popularity":     0,
    },
    "high_energy_sad": {
        "genre":              "classical",
        "mood":               "sad",
        "target_energy":      0.90,
        "likes_acoustic":     False,
        "preferred_sub_mood": "aggressive",
        "preferred_decade":   0,
        "min_popularity":     0,
    },
    "nostalgia_seeker": {
        "genre":              "folk",
        "mood":               "nostalgic",
        "target_energy":      0.35,
        "likes_acoustic":     True,
        "preferred_sub_mood": "nostalgic",
        "preferred_decade":   2000,
        "min_popularity":     0,
    },
    "underground_digger": {
        "genre":              "electronic",
        "mood":               "moody",
        "target_energy":      0.65,
        "likes_acoustic":     False,
        "preferred_sub_mood": "melancholic",
        "preferred_decade":   2020,
        "min_popularity":     0,
    },
}

ACTIVE_PROFILE = "chill_lofi_fan"  # default for --modes and --diversity demos


# ---------------------------------------------------------------------------
# Challenge 4 — Visual summary table
# ---------------------------------------------------------------------------

def _shorten_reasons(explanation: str, max_len: int = 55) -> str:
    """Keeps only the first two reason tokens and trims to max_len characters."""
    parts = explanation.split(" | ")
    short = " | ".join(parts[:2])
    if len(short) > max_len:
        short = short[:max_len - 1] + "…"
    return short


def print_table(
    profile_name: str,
    user_prefs: dict,
    songs: list,
    k: int = 5,
    mode: str = "balanced",
    diverse: bool = False,
) -> None:
    """Prints recommendations as a formatted table (tabulate or ASCII fallback)."""
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    max_s = _max_score(weights)
    results = recommend_songs(user_prefs, songs, k=k, mode=mode, diverse=diverse)

    diversity_tag = " + diversity" if diverse else ""
    header = (
        f"\n  Profile : {profile_name}  |  Mode : {mode}{diversity_tag}\n"
        f"  Genre   : {user_prefs['genre']}  Mood : {user_prefs['mood']}  "
        f"Energy : {user_prefs['target_energy']}  "
        f"Sub-mood : {user_prefs.get('preferred_sub_mood', '—')}  "
        f"Decade : {user_prefs.get('preferred_decade') or '—'}"
    )
    print(header)

    rows = []
    for rank, (song, score, explanation) in enumerate(results, start=1):
        rows.append([
            f"#{rank}",
            song["title"],
            song["artist"],
            f"{song['genre']} / {song['mood']}",
            song.get("sub_mood", ""),
            song.get("popularity", ""),
            song.get("release_decade", ""),
            f"{score:.2f}/{max_s:.1f}",
            _shorten_reasons(explanation),
        ])

    headers = ["#", "Title", "Artist", "Genre/Mood", "Sub-mood", "Pop", "Era", "Score", "Top reasons"]

    if _HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    else:
        # Plain ASCII fallback
        col_w = [max(len(str(r[i])) for r in rows + [headers]) for i in range(len(headers))]
        sep = "  ".join("-" * w for w in col_w)
        fmt = "  ".join(f"{{:<{w}}}" for w in col_w)
        print("  " + fmt.format(*headers))
        print("  " + sep)
        for row in rows:
            print("  " + fmt.format(*[str(c) for c in row]))
    print()


# ---------------------------------------------------------------------------
# Demo runners
# ---------------------------------------------------------------------------

def run_all_profiles(songs: list) -> None:
    """Default run: every profile in balanced mode."""
    for name, prefs in PROFILES.items():
        print_table(name, prefs, songs, mode="balanced")


def run_mode_comparison(songs: list) -> None:
    """Challenge 2: show how all five scoring modes re-rank one profile."""
    prefs = PROFILES[ACTIVE_PROFILE]
    print(f"\n{'='*66}")
    print(f"  MODE COMPARISON  —  profile: {ACTIVE_PROFILE}")
    print(f"{'='*66}")
    for mode_name in SCORING_MODES:
        print_table(ACTIVE_PROFILE, prefs, songs, k=5, mode=mode_name)


def run_diversity_demo(songs: list) -> None:
    """Challenge 3: show top-5 with and without the diversity re-ranker."""
    # Use chill_lofi_fan because lofi has 3 songs → tends to cluster
    prefs = PROFILES["chill_lofi_fan"]
    print(f"\n{'='*66}")
    print("  DIVERSITY DEMO  —  profile: chill_lofi_fan")
    print(f"{'='*66}")
    print_table("chill_lofi_fan", prefs, songs, mode="balanced", diverse=False)
    print_table("chill_lofi_fan", prefs, songs, mode="balanced", diverse=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs(CSV_PATH)

    if "--modes" in sys.argv:
        run_mode_comparison(songs)
    elif "--diversity" in sys.argv:
        run_diversity_demo(songs)
    else:
        run_all_profiles(songs)


if __name__ == "__main__":
    main()
