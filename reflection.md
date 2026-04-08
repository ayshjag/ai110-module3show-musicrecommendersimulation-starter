# Reflection: Music Recommender Simulation

## Profile Comparisons

### chill_lofi_fan vs pop_party_goer

These two profiles produced the clearest contrast. The lofi fan got *Library Rain*
and *Midnight Coding* at the top — both quiet, acoustic, low-energy tracks perfect
for background studying. The pop fan got *Sunrise City* — upbeat, high-energy, and
fully electronic. The swap in energy (0.40 vs 0.85) and acoustic preference (True
vs False) reversed almost every position in the list. This makes sense: these
profiles represent genuinely opposite listening contexts. One person is winding
down, the other is getting pumped up. The system correctly sent them to opposite
ends of the catalog.

### late_night_driver vs chill_lofi_fan

Both want relatively low-to-mid energy and prefer a single-genre catalog, but the
results barely overlap. The driver's #1 (*Night Drive Loop*, synthwave/moody)
scores 6.36 while the lofi fan's #1 (*Library Rain*) scores 6.29 — similar
confidence, completely different songs. What changes the list is the mood signal:
"moody" vs "chill" are both calm labels, but they pull in different directions.
Moody rewards darker, atmospheric tracks; chill rewards soft and warm ones. The
system correctly separates these two "quiet" listeners because mood is a distinct
signal from energy level.

### high_energy_sad (adversarial) vs pop_party_goer

Both want high energy (0.9 vs 0.85) but the sad profile asks for a genre
(classical) that barely exists in the catalog. The pop fan's top result is a
confident 6.40/6.6. The sad fan's best result is only 2.64/6.6 — less than half
the max score. More importantly, the #1 result (*Storm Runner*, rock/intense) is
not classical and not sad — it just happened to have the right energy. The genre
and mood signals both missed, so energy became the only differentiator. This
exposed how the system degrades when the catalog lacks representation: without
matching genre songs to choose from, the recommendations are basically just
"songs with similar energy," which is a much weaker signal on its own.

### nostalgia_seeker vs underground_digger

Both have acoustic/electronic preferences on opposite ends and target different
eras (2000s vs 2020s). The nostalgia seeker correctly surfaces *Harvest Moon Walk*
(folk/nostalgic/2000) first and fills the rest of the list with acoustic
country/jazz/lofi tracks. The underground digger gets *Neon Sermon*
(electronic/moody/2020) first and fills out with synthwave and hip-hop. The era
and acoustic signals work exactly as designed here — they quietly nudge the list
without dominating it. Neither profile's result would feel right for the other
listener.

## Weight Experiment: energy ×2, genre ×0.5

Switching from `genre=2.0, energy=1.0` to `genre=1.0, energy=2.0` had a small
effect on well-matched profiles and a large effect on the adversarial ones.

For `chill_lofi_fan`: the top 2 stayed the same. Position #3 shifted from
*Focus Flow* (lofi/focused) to *Spacewalk Thoughts* (ambient/chill) — because
energy closeness now outweighed the genre bonus for the third slot.

For `high_energy_sad`: *Sonata in Grey* (the classical song that was #3 by
genre match alone) completely disappeared from the top 5. High-energy tracks
(*Storm Runner*, *Gym Hero*, *Pulse Protocol*) took every slot. The system now
correctly prioritized what the user *felt* they wanted (intense energy) over
what the genre label said they should want.

**What this tells me:** the default genre weight of 2.0 encodes a design
assumption — "genre loyalty matters most." That assumption is valid for most
users. But it fails badly when the catalog is sparse for a genre, because the
only representative song gets promoted regardless of fit. A weight is not just a
number; it is a value judgment about what the user cares about. Getting that
judgment wrong causes real failures.

## What I Learned

The most important thing I learned is that a recommender system's behavior is
determined as much by the *data* as by the *algorithm*. I could tune the weights
endlessly and still produce bad recommendations for any genre that had only one
song in the catalog. The algorithm always did exactly what it was told — but
what it was told was limited by what data existed.

I also learned that "the algorithm worked" and "the results were good" are two
different things. The `high_energy_sad` case produced a technically correct score
for every song. The math was right. The output was wrong. That gap only became
visible when I tested an adversarial profile. Without deliberate stress testing,
I would have shipped a system I thought was working fine.

## How AI Tools Helped (and Where I Double-Checked)

AI tools accelerated everything structural: drafting the `_compute_score`
function, suggesting `sorted()` vs `.sort()`, the tabulate table format, and the
Mermaid flowchart. These are pattern-matching tasks where the AI has seen
thousands of examples and gives correct answers quickly.

Where I had to verify manually: the weight values themselves. The AI's first
suggestion for weights was plausible but arbitrary — there was no way for it to
know that genre=2.0 would catastrophically override energy for a sparse-catalog
user until I ran the adversarial profiles. The AI can propose a formula; only
running the code against real inputs tells you whether the formula was wise.

## What I Would Try Next

The single most valuable improvement would be a **diversity re-ranker**: after
scoring, before returning the top 5, enforce that no more than 2 songs share the
same genre. This would fix the filter-bubble problem without changing any
scoring logic. It is already partially implemented as the `--diversity` flag, but
I would make it the default behavior rather than an opt-in.

The second thing I would try is replacing the manually assigned energy and
acousticness values with real data from the Spotify audio features API. The
current values were assigned by hand during design, which means the "energy
proximity" signal is only as accurate as my judgment about what 0.82 energy
feels like. Real audio analysis would make that signal much more meaningful.
