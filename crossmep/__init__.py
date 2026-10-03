"""CrossMEP: a tiered synthetic dataset of multi-trade MEP cross-sections.

Public API::

    from crossmep import generate_dataset, generate_custom, generate_split, validate_context
    from crossmep import load_contexts, MEPContext, Element, MountingSurface
    import crossmep.tasks as cm            # stdlib-only loader and benchmark metrics

Modules: ``model`` (data model + validator), ``library`` (sourced constants and
derived loads), ``layout`` (row / gap / stagger engine), ``generate`` (tiers and
the custom-composition API), ``io`` (release file format), ``tasks`` (loader and
metrics, no NumPy), ``render`` (SVG gallery), ``cli``.

``model``, ``io`` and ``tasks`` import only the standard library; the generator
(``generate``, ``layout``, ``library``) needs NumPy and is imported lazily so
that consumers of the JSON files never pay for it.
"""
from __future__ import annotations

__version__ = "3.5.0"

from .model import (CLEARANCE_MM, ContextValidationError, Element, MEPContext,  # noqa: F401
                    MountingSurface, depth_out, is_valid, pair_clearance, span_along,
                    validate_context)
from .io import DATA_VERSION, build_payload, load_contexts, read_payload, write_payload  # noqa: F401

_LAZY = {
    "generate_context": "generate", "generate_dataset": "generate", "generate_split": "generate",
    "generate_custom": "generate", "CANONICAL_SPLITS": "generate", "TIERS": "generate",
}


def __getattr__(name: str):
    if name in _LAZY:
        import importlib
        return getattr(importlib.import_module(f".{_LAZY[name]}", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__", "CLEARANCE_MM", "ContextValidationError", "Element", "MEPContext",
           "MountingSurface", "depth_out", "is_valid", "pair_clearance", "span_along",
           "validate_context", "DATA_VERSION", "build_payload", "load_contexts",
           "read_payload", "write_payload", *_LAZY]
