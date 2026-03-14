"""
Mutation Lanes

Different mutation classes evolve at different speeds.

art_lane          -> art style mutation
language_lane     -> grammar / vocab scoring mutation
scheduler_lane    -> curiosity / recovery tuning
protected_core    -> never mutated automatically
"""

LANES = {
    "art_lane": {},
    "language_lane": {},
    "scheduler_lane": {},
    "protected_core": {},
}
