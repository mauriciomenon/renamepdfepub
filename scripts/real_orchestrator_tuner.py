#!/usr/bin/env python3
"""Itera combinacoes de pesos do orquestrador usando livros reais."""
from __future__ import annotations

import itertools
import json
import logging
import sys
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.comprehensive_real_test import AlgorithmTester  # noqa: E402


def evaluate_config(config: Dict[str, Dict[str, float]], max_books: int) -> Dict[str, float]:
    tester = AlgorithmTester(orchestrator_config=config, silent=True)
    results = tester.run_comprehensive_test(max_books=max_books)
    summary = results['algorithm_summary']['V3 Ultimate Orchestrator']
    return {
        'average_accuracy': summary['average_accuracy'],
        'success_rate': summary['success_rate'],
        'average_time': summary['average_time']
    }


def main() -> None:
    logging.getLogger().setLevel(logging.ERROR)

    fuzzy_weights = [0.9, 1.0, 1.1]
    semantic_weights = [0.9, 1.0, 1.1]
    consensus_steps = [0.15, 0.25]
    multi_bonus_values = [0.0, 0.05]
    max_books = 30

    results = []
    for fw, sw, consensus, multi in itertools.product(
        fuzzy_weights, semantic_weights, consensus_steps, multi_bonus_values
    ):
        config = {
            'weights': {
                'v3_enhanced_fuzzy': fw,
                'v3_super_semantic': sw,
            },
            'consensus_bonus': consensus,
            'multi_algo_bonus': multi,
        }
        stats = evaluate_config(config, max_books=max_books)
        results.append({
            'config': config,
            **stats,
        })
        print(
            f"fw={fw:.2f} sw={sw:.2f} consensus={consensus:.2f} multi={multi:.2f} "
            f"-> accuracy={stats['average_accuracy']:.3f} success={stats['success_rate']:.2f}"
        )

    results.sort(key=lambda item: (item['average_accuracy'], item['success_rate']), reverse=True)

    output_path = ROOT_DIR / 'reports' / 'orchestrator_tuning_results.json'
    output_path.write_text(json.dumps(results, indent=2), encoding='utf-8')

    print('\nMelhores configuracoes:')
    for entry in results[:5]:
        cfg = entry['config']
        print(
            f"accuracy={entry['average_accuracy']:.3f} success={entry['success_rate']:.2f} "
            f"fw={cfg['weights']['v3_enhanced_fuzzy']} sw={cfg['weights']['v3_super_semantic']} "
            f"consensus={cfg['consensus_bonus']} multi={cfg['multi_algo_bonus']}"
        )


if __name__ == '__main__':
    main()
