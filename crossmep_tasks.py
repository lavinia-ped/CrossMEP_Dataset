"""Backward-compatible alias for ``crossmep.tasks`` (standard library only).

    import crossmep_tasks as cm
    data = cm.load("benchmark")            # current data revision (4.0)
    data = cm.load("benchmark", "3.0")     # the paper release

New code should ``import crossmep.tasks as cm``.
"""
from crossmep.tasks import *  # noqa: F401,F403
from crossmep.tasks import (COLD, LEGACY_ENVELOPE_MM, TIER_ORDER, catalog_coverage,  # noqa: F401
                            congestion_score, envelope_clearance, filter_contexts, kind_counts,
                            kind_totals, load, min_clear_gap, neighbour_gaps, per_tier_table,
                            tier_ranges, tier_ranges_table, tier_summary, validate)
from crossmep.model import CLEARANCE_MM  # noqa: F401

if __name__ == "__main__":
    from crossmep.cli import main
    raise SystemExit(main(["results", "--split", "benchmark"]))
