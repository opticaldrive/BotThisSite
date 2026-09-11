# The graphs used to group millions of per-solve rows by a computed strftime
# expression on every cache rebuild, which no index can help with. They read
# SolveBucket instead: the same history pre-aggregated into 5-minute cells,
# roughly three orders of magnitude fewer rows. 79 days of history is 27k
# buckets.
#
# The rollup used to be derived from a SolveEvent log, with a backfill() that
# could recompute any cell from it. The log is gone: at solver load it took a
# million rows an hour to describe what the buckets already say, and nothing
# read it. The writer bumps cells in the same transaction as the tallies, so
# the rollup is now primary data rather than a cache of something else.
GRAIN = 300  # seconds; the finest bucket the graphs offer ("5min")


def bucket_of(ts: int) -> int:
    """Floor a unix timestamp to the start of its rollup cell."""
    return ts - (ts % GRAIN)
