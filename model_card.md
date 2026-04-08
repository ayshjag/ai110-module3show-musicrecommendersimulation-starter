# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use and Non-Intended Use

### Intended use

VibeFinder 1.0 suggests up to 5 songs from a 20-song catalog based on a
listener's preferred genre, mood, energy level, and acoustic texture. It is
designed for **classroom exploration** — to show how a content-based recommender
translates user preferences into ranked song lists.

Assumptions it makes about the user:
- The user can describe their taste with a single genre and a single mood label.
- They have one target energy level (a number from 0 to 1) that stays constant.
- Their preference for acoustic vs. electronic sound is a simple yes/no flag.

It does **not** use listening history, skip data, time of day, social context,
or any form of collaborative signal.

### Non-intended use

- **Not for real listeners.** The 20-song catalog is far too small to serve actual
  music discovery needs. Recommendations after rank #2 are often poor because most
  genres appear only once.
- **Not for production deployment.** There is no user authentication, no
  persistence, no rate limiting, and no safety review. It should not be embedded
  in any app that real users interact with.
- **Not a fair representation of global music taste.** The catalog is
  Western-centric and English-language. Using this system to make decisions about
  what music to promote or license would unfairly exclude non-Western genres and
  artists.
- **Not suitable for personalization at scale.** Static weights hard-coded in a
  Python dict cannot adapt to individual users over time the way a trained model
  can. Treating these scores as ground-truth relevance signals would be incorrect.

---

## 3. How the Model Works

Imagine a music critic who has been given a single index card describing your
taste: *"You like lofi, you want it to feel chill, keep the energy low, and lean
acoustic."* That critic then goes through every song in a stack of 20 records and
gives each one a score out of 5.

The score is built from four checks:

1. **Genre** — Does the song's genre match yours? If yes, it earns 2 points
   (the biggest reward).
2. **Mood** — Does the song's mood label match yours? If yes, 1.5 points.
3. **Energy closeness** — How close is the song's energy to your target? A
   perfect match earns 1 point; the further apart, the fewer points (down to 0).
4. **Acoustic texture** — If you like acoustic music, songs with more acoustic
   instrumentation earn up to 0.5 points. If you prefer electronic, the reward
   flips.

After every song is scored, the critic hands you the top 5 in order from highest
to lowest. That list is your recommendation.

| Signal | Max points | Weight |
|---|---|---|
| Genre match | 2.00 | 2.0 |
| Mood match | 1.50 | 1.5 |
| Energy proximity | 1.00 | 1.0 |
| Acoustic texture | 0.50 | 0.5 |
| **Total possible** | **5.00** | |

---

## 4. Data

- **Catalog size:** 20 songs in `data/songs.csv`
- **Added in Phase 2:** 10 new songs (IDs 11–20) to increase genre and mood
  diversity beyond the 10-song starter set.

**Genres represented:** pop, lofi, rock, ambient, jazz, synthwave, indie pop,
country, hip-hop, r&b, edm, classical, metal, folk, reggae, electronic

**Moods represented:** happy, chill, intense, relaxed, focused, moody,
nostalgic, romantic, energetic, peaceful, angry, sad

**Gaps and caveats:**
- Most genres appear only once or twice. Pop has 2 songs, lofi has 3,
  everything else has 1.
- The catalog reflects a Western, English-language taste palette. No K-pop,
  Latin, Afrobeats, or global genres are present.
- Song attributes (energy, valence, etc.) were manually assigned during design —
  they are not derived from real audio analysis tools like Spotify's API.

---

## 5. Strengths

**Well-matched profiles get very accurate results.**
When a user's genre and mood exist prominently in the catalog, the top results
feel correct. The `chill_lofi_fan` profile consistently surfaced *Library Rain*
and *Midnight Coding* at scores above 4.8/5.0 — both of which fit the brief
perfectly. The `late_night_driver` (synthwave/moody) put *Night Drive Loop*
first at 4.89/5.0 with a perfect energy score.

**The "reasons" string makes the score transparent.**
Every recommendation comes with a plain-language explanation. A non-programmer
can read `"genre match 'lofi' (+2.0) | mood match 'chill' (+1.5)"` and
immediately understand why a song was chosen — a significant advantage over
black-box systems.

**Graceful fallback when genre is absent.**
The `genre_not_in_catalog` profile (bluegrass — not in the dataset) still
surfaced reasonable results: *Back Porch Blues* (country/nostalgic/acoustic)
and *Harvest Moon Walk* (folk/nostalgic/acoustic) rose to the top purely on
mood and texture. The system didn't crash or return garbage.

---

## 6. Limitations and Bias

### L1 — Genre weight is too dominant

With genre worth 2.0 out of 5.0 total points, a single genre match
outweighs a near-perfect mood + energy combination from a different genre.
The starkest example: the `high_energy_sad` profile wanted energy=0.9 but was
given *Sonata in Grey* (classical, energy=0.20) as its **#1 result** — the
slowest song in the entire catalog — purely because it was the only classical
song. The genre bonus (2.0) beat a 0.70-point energy penalty by a wide margin.
In a real product this would be a user-experience failure.

### L2 — Catalog sparsity creates filter bubbles

For any genre with only one representative song, that song will always appear
at the top of a matching profile's list regardless of how poorly it fits the
other signals. The `perfectly_average` (r&b/romantic) profile saw *Velvet
Undertow* score 4.84 — but the #2 result dropped to 1.29. There is no
alternative r&b song to recommend, so the list fills with poor
mood/genre-mismatched filler. This is the definition of a filter bubble:
the system cannot surface diverse recommendations because diversity is not
present in the data.

### L3 — Binary categorical matching misses genre relationships

The system treats "pop" and "indie pop" as completely unrelated genres. A pop
fan who might enjoy an indie pop track with identical energy and mood will never
have *Rooftop Lights* ranked higher than a pop track with worse energy fit,
because there is no concept of genre adjacency. Real recommenders use
embeddings or genre hierarchies to express that "indie pop is closer to pop
than to metal."

### L4 — `likes_acoustic` is all-or-nothing

A user who enjoys acoustic guitar for studying but prefers electronic beats for
exercising gets one flag that applies uniformly. The system has no way to
represent context-dependent preferences.

### L5 — No diversity enforcement

The top 5 results can all be the same genre. A `chill_lofi_fan` gets three
lofi tracks in a row, which might cause fatigue in a real listening session.
A production system would apply a diversity penalty to avoid over-concentrating
a single genre in the returned list.

---

## 7. Evaluation

### Profiles tested

| Profile | Genre | Mood | Energy | Acoustic |
|---|---|---|---|---|
| chill_lofi_fan | lofi | chill | 0.40 | True |
| pop_party_goer | pop | happy | 0.85 | False |
| late_night_driver | synthwave | moody | 0.75 | False |
| high_energy_sad *(adversarial)* | classical | sad | 0.90 | False |
| genre_not_in_catalog *(adversarial)* | bluegrass | nostalgic | 0.45 | True |
| perfectly_average *(adversarial)* | r&b | romantic | 0.55 | False |

### Key observations

**chill_lofi_fan vs pop_party_goer**
Both profiles had their genre represented in the catalog and produced high-scoring
top results (4.88 each). The lofi fan got 3 lofi tracks in the top 5; the pop fan
got 2 pop tracks. The difference is that pop has slightly fewer catalog entries,
so genre-less tracks (*Rooftop Lights*, *Crown Heights Summer*) had to fill the
bottom slots. This shows that catalog distribution directly shapes diversity.

**late_night_driver — confident but narrow**
Synthwave has only one song (*Night Drive Loop*), which scored 4.89. The #2
result (*Neon Sermon*) scored only 2.90 — a 2-point drop. The top result is
excellent; the rest of the list is mediocre because no other songs share the
genre. A real synthwave fan would be poorly served after the first track.

**high_energy_sad — the most revealing failure**
This adversarial profile exposed the genre-weight bug described in L1.
The system recommended *Sonata in Grey* (energy 0.20, peaceful classical) to
a listener who explicitly wanted high-energy (0.90) music. The explanation
string makes the failure readable: the genre bonus alone carried it to #1 despite
the near-zero energy score. This is a case where the algorithm's math is
technically correct but the result is wrong.

**genre_not_in_catalog — surprisingly decent**
Without a genre match available, the system relied entirely on mood + energy +
acoustic texture. It surfaced *Back Porch Blues* and *Harvest Moon Walk* — both
country/folk/nostalgic/acoustic, which is exactly what a bluegrass fan would
likely enjoy. This suggests the secondary signals are meaningful; it is the
genre bonus that distorts results when the catalog is sparse.

### Weight-shift experiment (energy ×2, genre ×0.5)

Default: `genre=2.0, mood=1.5, energy=1.0, acoustic=0.5`
Experiment: `genre=1.0, mood=1.5, energy=2.0, acoustic=0.5`

**chill_lofi_fan result:** Top 2 unchanged. Position #3 shifted from *Focus Flow*
(lofi/focused) to *Spacewalk Thoughts* (ambient/chill) because the energy
proximity now carries more weight than the genre bonus. The mood match on
Spacewalk (+1.5) combined with strong energy closeness outranked a genre match
with a mood mismatch.

**high_energy_sad result:** *Sonata in Grey* (the classical song) completely
disappeared from the top 5. *Storm Runner*, *Gym Hero*, and *Crown Heights
Summer* — all high-energy tracks — took the top spots. The system now correctly
prioritized energy over genre label, which feels more intuitive for this profile.

**Conclusion:** Doubling the energy weight makes recommendations feel more
"vibe-accurate" but less genre-specific. There is a real design tradeoff here:
genre weight makes the system feel predictable and on-brand; energy weight makes
it feel sonically accurate. The right balance depends on what the user values
most.

---

## 8. Future Work

- **Genre proximity / embeddings:** Replace exact-match genre scoring with a
  similarity measure. "Indie pop" should be closer to "pop" than to "metal."
- **Diversity enforcement:** After ranking, apply a penalty for consecutive
  same-genre results so the top 5 includes at least 2–3 different genres.
- **Context-aware profiles:** Allow energy and mood preferences to vary by time
  of day or listening session type (study, workout, sleep).
- **Larger catalog:** 20 songs is too small for meaningful diversity. A 200-song
  catalog would let the secondary signals (energy, acoustic) differentiate within
  each genre rather than defaulting to the single available track.
- **Valence and danceability signals:** These attributes are in the CSV but unused
  in scoring. Adding valence (musical positivity) would help distinguish "happy
  rock" from "moody rock" beyond the mood label alone.

---

## 9. Personal Reflection

**Biggest learning moment**

The clearest "aha" moment came when the adversarial `high_energy_sad` profile
produced *Sonata in Grey* — a peaceful classical piano piece — as the top
recommendation for a listener who explicitly asked for energy=0.9. The math was
correct. The code ran without errors. The score formula did exactly what it was
told. And yet the output was obviously wrong to any human. That gap between
"technically correct" and "actually useful" is something I had read about in
AI ethics discussions, but seeing it happen inside four lines of Python made it
concrete in a way that no description could. A model can be consistent and still
be broken.

**How AI tools helped — and where I had to check them**

AI tools accelerated the structural parts of this project significantly: drafting
the `_compute_score` function signature, suggesting the `sorted()` vs `.sort()`
distinction, and proposing the Mermaid flowchart format. These are exactly the
kinds of tasks where AI shines — well-known patterns with clear right answers.

Where I had to slow down and verify: the weight values themselves. When I asked
for suggestions on how to balance genre vs. mood vs. energy, the AI's first
response was confident but arbitrary — it had no way to know that a 2.0 genre
weight would catastrophically override energy in sparse-catalog edge cases. The
numbers looked reasonable on paper and only revealed their flaw when I ran the
adversarial profiles. The AI can generate a formula; only running the code
against real inputs tells you whether the formula was wise.

**What surprised me about how "simple" this still feels like a recommendation**

Even with just four signals and twenty songs, the output genuinely feels
personalized when the profile is well-matched. When I ran the `chill_lofi_fan`
profile and *Library Rain* appeared first with a 4.88/5.00 score, it looked
exactly like something Spotify would put at the top of a "Focus" playlist. The
system is doing nothing sophisticated — it is adding four numbers — but the
result reads as intelligent. That was unsettling in a productive way. It suggests
that a lot of what feels like "the algorithm knows me" in real apps might be
simpler than we assume, and that the *presentation* of a ranked list (title,
artist, score, reason) does significant cognitive work in making it feel smart.

**What I would try next**

The most important extension would be adding a **diversity re-ranker**: after
scoring all 20 songs, before returning the top 5, check whether too many results
share the same genre and, if so, swap in the best-scoring song from a different
genre. That one change would fix the filter-bubble problem without touching the
scoring math at all. The second thing I would try is pulling real song data from
the Spotify API — not to use their recommender, but to replace the manually
assigned energy/valence values with real audio features, which would make the
energy proximity signal far more meaningful.
