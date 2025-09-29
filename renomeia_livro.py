"""Compatibility forwarder for core module `src.core.renomeia_livro`.

Avoids importing heavy optional dependencies at import time. Attributes are
resolved lazily on first access, so a plain `import renomeia_livro` succeeds
even when optional third-party packages are not installed.
"""

import importlib

_CORE_PATH = 'src.core.renomeia_livro'
_CORE_MOD = None


def __getattr__(name):  # pragma: no cover - thin shim
    global _CORE_MOD
    if _CORE_MOD is None:
        _CORE_MOD = importlib.import_module(_CORE_PATH)
    return getattr(_CORE_MOD, name)

