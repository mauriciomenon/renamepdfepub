"""Core V3 metadata search system shared by CLI, GUI, and tests.

Extracted from the historic test harness so production code no longer imports
modules from the test tree. Provides combined fuzzy and semantic ranking
utilities for book metadata lists.
"""
from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Dict, List, Any
from difflib import SequenceMatcher


class V3CompleteSystem:
    """Composed search/orchestration helpers for the V3 algorithms."""

    def __init__(self, books_data: List[Dict[str, Any]], orchestrator_config: Dict[str, Any] | None = None) -> None:
        self.books_data = books_data
        orchestrator_config = orchestrator_config or {}
        weights = orchestrator_config.get('weights', {})
        self.fuzzy_weight = weights.get('v3_enhanced_fuzzy', 0.9)
        self.semantic_weight = weights.get('v3_super_semantic', 0.9)
        self.consensus_bonus_step = orchestrator_config.get('consensus_bonus', 0.2)
        self.multi_algo_bonus = orchestrator_config.get('multi_algo_bonus', 0.05)
        self.publisher_patterns = {
            'Manning': [r'\bmanning\b', r'\bmeap\b', r'month.*lunches'],
            'Packt': [r'\bpackt\b', r'cookbook', r'hands[\s\-]on', r'mastering'],
            'NoStarch': [r'no\s*starch', r'black\s*hat', r'ethical\s*hacking'],
            'OReilly': [r'o\'?reilly', r'learning', r'definitive\s+guide'],
            'Wiley': [r'\bwiley\b', r'\bsybex\b'],
            'Addison': [r'addison', r'wesley'],
            'MIT': [r'mit\s*press'],
            'Apress': [r'\bapress\b'],
        }

        self.super_categories = {
            'Programming': [
                'python', 'java', 'javascript', 'js', 'typescript', 'react', 'vue',
                'angular', 'programming', 'code', 'coding', 'development',
                'software', 'algorithm', 'algorithms', 'c++', 'golang', 'rust',
                'kotlin', 'swift', 'php', 'ruby'
            ],
            'Security': [
                'security', 'hacking', 'hack', 'cyber', 'cybersecurity', 'malware',
                'forensics', 'penetration', 'pentest', 'ethical', 'cryptography',
                'encryption', 'vulnerability', 'threat', 'incident'
            ],
            'Database': [
                'database', 'db', 'sql', 'mysql', 'postgresql', 'mongo', 'mongodb',
                'redis', 'data', 'analytics', 'warehouse', 'big data'
            ],
            'AI_ML': [
                'machine learning', 'ml', 'ai', 'artificial intelligence',
                'data science', 'deep learning', 'neural', 'tensorflow', 'pytorch',
                'pandas', 'numpy'
            ],
            'Web': [
                'web', 'website', 'html', 'css', 'frontend', 'backend', 'fullstack',
                'ui', 'ux', 'api', 'rest', 'graphql', 'http'
            ],
            'DevOps': [
                'devops', 'docker', 'kubernetes', 'k8s', 'cloud', 'aws', 'azure',
                'deployment', 'automation', 'ci/cd', 'jenkins', 'ansible'
            ],
            'Mobile': [
                'mobile', 'android', 'ios', 'app', 'application', 'swift', 'kotlin',
                'react native', 'flutter'
            ],
            'Systems': [
                'linux', 'windows', 'system', 'network'
            ],
        }
        self.known_publishers = {
            'manning': 'Manning',
            'packt': 'Packt',
            "o'reilly": "O'Reilly",
            'oreilly': "O'Reilly",
            'nostarch': 'No Starch',
            'no starch': 'No Starch',
            'wiley': 'Wiley',
            'addison': 'Addison-Wesley',
            'pearson': 'Pearson',
            'apress': 'Apress',
            'springer': 'Springer',
            'mcgraw': 'McGraw-Hill'
        }

    # --- Core search helpers -----------------------------------------------------

    def v3_enhanced_fuzzy_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_clean = query.lower().strip()
        query_words = set(query_clean.split())
        query_category = self._detect_category(query)
        query_keywords = self._extract_keywords(query)

        results: List[Dict[str, Any]] = []
        for book in self.books_data:
            enriched_book = self._fill_metadata(book)
            title = enriched_book.get('title')
            if not title:
                continue

            title_clean = title.lower()
            title_words = set(title_clean.split())

            base_similarity = SequenceMatcher(None, query_clean, title_clean).ratio()
            common_words = query_words.intersection(title_words)
            word_bonus = len(common_words) / len(query_words) * 0.5 if query_words else 0
            category_bonus = 0.3 if enriched_book.get('category') == query_category and query_category != 'General' else 0
            book_keywords = set(enriched_book.get('keywords', []))
            keyword_overlap = len(set(query_keywords).intersection(book_keywords))
            keyword_bonus = keyword_overlap * 0.1
            publisher_bonus = 0.15 if enriched_book.get('publisher') in ['Manning', 'Packt', "O'Reilly"] else 0
            phrase_bonus = 0.4 if query_clean in title_clean else 0
            len_diff = abs(len(query_clean) - len(title_clean))
            len_bonus = max(0, 0.1 - len_diff / 200)

            total_score = min(base_similarity + word_bonus + category_bonus + keyword_bonus + publisher_bonus + phrase_bonus + len_bonus, 1.0)
            if total_score > 0.2:
                results.append({
                    'title': title,
                    'author': enriched_book.get('author', ''),
                    'publisher': enriched_book.get('publisher', ''),
                    'year': enriched_book.get('year', ''),
                    'category': enriched_book.get('category', ''),
                    'filename': enriched_book.get('filename', ''),
                    'similarity_score': total_score,
                    'confidence': total_score * enriched_book.get('confidence', 0.5),
                    'algorithm': 'v3_enhanced_fuzzy',
                    'score_breakdown': {
                        'base': base_similarity,
                        'words': word_bonus,
                        'category': category_bonus,
                        'keywords': keyword_bonus,
                        'publisher': publisher_bonus,
                        'phrase': phrase_bonus,
                        'length': len_bonus,
                    },
                })

        results.sort(key=lambda item: item['similarity_score'], reverse=True)
        return results[:limit]

    def v3_super_semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_clean = query.lower().strip()
        query_words = set(query_clean.split())
        query_category = self._detect_category(query)
        query_keywords = set(self._extract_keywords(query))

        results: List[Dict[str, Any]] = []
        for book in self.books_data:
            enriched_book = self._fill_metadata(book)
            title = enriched_book.get('title')
            if not title:
                continue

            title_words = set(title.lower().split())
            book_keywords = set(enriched_book.get('keywords', []))
            book_category = enriched_book.get('category', 'General')

            score = 0.0
            if query_words and title_words:
                common_words = query_words.intersection(title_words)
                word_weight = 0.0
                for word in common_words:
                    if word in {'python', 'java', 'javascript', 'react', 'security', 'database'}:
                        word_weight += 2.0
                    elif len(word) > 4:
                        word_weight += 1.5
                    else:
                        word_weight += 1.0
                denominator = len(query_words) + len(title_words) - len(common_words)
                word_score = word_weight / denominator if denominator else 0.0
                score += word_score * 0.4

            if query_category != 'General' and book_category == query_category:
                score += 0.35
            elif query_category != 'General' and book_category != 'General':
                score += 0.1

            if query_keywords and book_keywords:
                common_keywords = query_keywords.intersection(book_keywords)
                union_keywords = query_keywords.union(book_keywords)
                keyword_score = len(common_keywords) / len(union_keywords) if union_keywords else 0.0
                score += keyword_score * 0.3

            publisher = enriched_book.get('publisher', '')
            if publisher in {'Manning', 'Packt', 'OReilly', 'NoStarch'}:
                score += 0.15
            elif publisher:
                score += 0.05

            for query_word in query_words:
                if len(query_word) > 6 and query_word in title.lower():
                    score += 0.05

            results.append({
                'title': title,
                'author': enriched_book.get('author', ''),
                'publisher': publisher,
                'year': enriched_book.get('year', ''),
                'category': book_category,
                'filename': enriched_book.get('filename', ''),
                'similarity_score': min(score, 1.0),
                'confidence': min(score, 1.0) * enriched_book.get('confidence', 0.5),
                'algorithm': 'v3_super_semantic',
            })

        results.sort(key=lambda item: item['similarity_score'], reverse=True)
        return results[:limit]

    def orchestrate(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        fuzzy_results = self.v3_enhanced_fuzzy_search(query, limit)
        semantic_results = self.v3_super_semantic_search(query, limit)

        combined: Dict[str, Dict[str, Any]] = {}
        for item in fuzzy_results + semantic_results:
            key = item.get('filename') or item.get('title')
            if not key:
                continue
            entry = combined.setdefault(key, item.copy())
            entry['similarity_score'] = max(entry.get('similarity_score', 0.0), item.get('similarity_score', 0.0))
            entry['confidence'] = max(entry.get('confidence', 0.0), item.get('confidence', 0.0))

        ordered = sorted(combined.values(), key=lambda item: item['similarity_score'], reverse=True)
        return ordered[:limit]

    # Legacy API expected by the comprehensive real tests
    def v3_ultimate_orchestrator(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        fuzzy_results = self.v3_enhanced_fuzzy_search(query, limit * 2)
        semantic_results = self.v3_super_semantic_search(query, limit * 2)

        weights = {
            'v3_enhanced_fuzzy': self.fuzzy_weight,
            'v3_super_semantic': self.semantic_weight,
        }

        combined: Dict[str, Dict[str, Any]] = {}

        for results, algo_name in (
            (fuzzy_results, 'v3_enhanced_fuzzy'),
            (semantic_results, 'v3_super_semantic'),
        ):
            weight = weights[algo_name]
            for result in results:
                title_key = result['title'].lower().strip()
                if title_key not in combined:
                    entry = self._fill_metadata(result)
                    entry['combined_score'] = min(entry['similarity_score'] * weight, 1.0)
                    entry['algorithms_used'] = [algo_name]
                    entry['algorithm_count'] = 1
                    entry['consensus_bonus'] = 0.0
                    combined[title_key] = entry
                else:
                    existing = combined[title_key]
                    existing['algorithm_count'] += 1
                    existing['algorithms_used'].append(algo_name)
                    consensus_bonus = self.consensus_bonus_step * (existing['algorithm_count'] - 1)
                    existing['consensus_bonus'] = consensus_bonus
                    new_contribution = min(result['similarity_score'] * weight, 1.0)
                    base_score = max(existing['combined_score'], new_contribution)
                    combined_score = base_score + consensus_bonus
                    existing['combined_score'] = min(combined_score, 1.0)
                    if not existing.get('publisher') and result.get('publisher'):
                        existing['publisher'] = result['publisher']
                    if not existing.get('author') and result.get('author'):
                        existing['author'] = result['author']

        final_results = []
        for entry in combined.values():
            entry = self._fill_metadata(entry.copy())
            entry['similarity_score'] = entry['combined_score']
            if entry.get('algorithm_count', 1) > 1:
                entry['similarity_score'] = min(entry['similarity_score'] + self.multi_algo_bonus, 1.0)
            entry['algorithm'] = 'v3_ultimate_orchestrator'
            final_results.append(entry)

        final_results.sort(key=lambda item: item['similarity_score'], reverse=True)
        return final_results[:limit]

    # --- Helpers ----------------------------------------------------------------

    def _fill_metadata(self, book: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(book)
        filename = enriched.get('filename') or enriched.get('title', '')
        fallback = self._extract_from_filename(filename)

        author = enriched.get('author') or enriched.get('authors')
        if isinstance(author, list):
            author = ', '.join(author)
        if not author:
            author = fallback.get('author', '')
        enriched['author'] = author
        enriched['authors'] = [author] if author else []

        if not enriched.get('title'):
            enriched['title'] = fallback.get('title', '')
        if not enriched.get('publisher'):
            enriched['publisher'] = fallback.get('publisher', '')
        if not enriched.get('year'):
            enriched['year'] = fallback.get('year', '')
        if not enriched.get('filename'):
            enriched['filename'] = filename
        if not enriched.get('confidence'):
            enriched['confidence'] = 0.6
        if not enriched.get('category'):
            enriched['category'] = self._detect_category(enriched.get('title', ''))
        return enriched

    def _extract_from_filename(self, filename: str) -> Dict[str, str]:
        if not filename:
            return {'title': '', 'author': '', 'publisher': '', 'year': ''}

        stem = Path(filename).stem
        cleaned = re.sub(r'[\s_]+', ' ', stem).strip()

        parts = [part.strip() for part in cleaned.split(' - ') if part.strip()]
        author = parts[0] if len(parts) >= 2 else ''
        title = ' - '.join(parts[1:]) if len(parts) >= 2 else cleaned

        year_match = re.search(r'(19|20)\d{2}', cleaned)
        year = year_match.group() if year_match else ''

        publisher = ''
        lower = cleaned.lower()
        for key, value in self.known_publishers.items():
            if key in lower:
                publisher = value
                break

        return {
            'title': title,
            'author': author,
            'publisher': publisher,
            'year': year,
        }

    def _detect_category(self, query: str) -> str:
        lowered = query.lower()
        for category, keywords in self.super_categories.items():
            if any(keyword in lowered for keyword in keywords):
                return category
        return 'General'

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r'[a-z0-9]+', query.lower())
        stopwords = {'the', 'and', 'for', 'with', 'from', 'into', 'your'}
        return [word for word in words if len(word) > 2 and word not in stopwords]

    # Convenience hook kept from the original helper, currently unused.
    def load_books_from_file(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)  # type: ignore[arg-type]


__all__ = ['V3CompleteSystem']
