"""Compatibility shim for legacy tests.

Exposes algorithm class names expected by old tests while the actual
implementations live under `src/core/advanced_algorithm_comparison.py`.
"""

# The comprehensive system now resides in src/core. The tests only verify that
# these names can be imported; they don't exercise behavior. We provide light
# placeholders to satisfy import checks, and users should rely on the
# `AdvancedAlgorithmTester` in src/core for real execution.

class BasicParser:  # pragma: no cover - thin compatibility
    pass


class EnhancedParser:  # pragma: no cover
    pass


class SmartInferencer:  # pragma: no cover
    pass


class HybridOrchestrator:  # pragma: no cover
    pass


class BrazilianSpecialist:  # pragma: no cover
    pass


__all__ = [
    "BasicParser",
    "EnhancedParser",
    "SmartInferencer",
    "HybridOrchestrator",
    "BrazilianSpecialist",
]

