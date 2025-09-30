#!/usr/bin/env python3
import importlib.util
from pathlib import Path


def _import_script(mod_path: Path):
    spec = importlib.util.spec_from_file_location('normalize_publishers', str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_normalize_name_variants(tmp_path: Path):
    mod = _import_script(Path(__file__).parent.parent / 'scripts' / 'normalize_publishers.py')
    nn = mod.normalize_name
    assert nn('CASA DO CÓDIGO') == 'Casa do Código'
    assert nn('cdc') == 'Casa do Código'
    assert nn("O'Reilly Media, Inc") == 'OReilly'
    assert nn('manning publications') == 'Manning'
    assert nn('unknown') == ''
    assert nn('') == ''

