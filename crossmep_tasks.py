"""Backward-compatible alias for ``crossmep.tasks`` (standard library only).

    import crossmep_tasks as cm
    data = cm.load("benchmark")

New code should ``import crossmep.tasks as cm``.
"""
from crossmep.tasks import *  # noqa: F401,F403
from crossmep.tasks import (CLEARANCE_MM, COLD, TIER_ORDER, catalog_coverage, congestion_score,  # noqa: F401
                            envelope_clearance, filter_contexts, kind_counts, kind_totals, load,
                            min_clear_gap, neighbour_gaps, per_tier_table, tier_summary, validate)

if __name__ == "__main__":
    from crossmep.cli import main
    raise SystemExit(main(["results", "--split", "benchmark"]))
