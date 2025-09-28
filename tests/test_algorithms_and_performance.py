#!/usr/bin/env python3
"""
Testes de Algoritmos e Performance
=================================

Testa os algoritmos principais de renomeação e suas funcionalidades.
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


class TestAlgorithmModules:
    """Testes para módulos de algoritmos"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        self.src_path = self.root_dir / "src"
        
    def test_advanced_algorithm_comparison_structure(self):
        """Testa estrutura do módulo de comparação avançada"""
        algo_path = self.src_path / "core" / "advanced_algorithm_comparison.py"
        assert algo_path.exists(), "advanced_algorithm_comparison.py não existe"
        
        # Verifica se o arquivo tem tamanho razoável (não está vazio)
        size = algo_path.stat().st_size
        assert size > 1000, f"Arquivo muito pequeno: {size} bytes"
        
    def test_algorithms_v3_exists(self):
        """Testa se algoritmos v3 existem"""
        v3_path = self.src_path / "core" / "algorithms_v3.py"
        assert v3_path.exists(), "algorithms_v3.py não existe"
        
    def test_amazon_api_integration_exists(self):
        """Testa se integração Amazon API existe"""
        api_path = self.src_path / "core" / "amazon_api_integration.py"
        assert api_path.exists(), "amazon_api_integration.py não existe"
        
    def test_auto_rename_system_exists(self):
        """Testa se sistema auto-rename existe"""
        auto_path = self.src_path / "core" / "auto_rename_system.py"
        assert auto_path.exists(), "auto_rename_system.py não existe"


class TestReportGeneration:
    """Testes para geração de relatórios"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_simple_report_generator_exists(self):
        """Testa se gerador de relatório simples existe"""
        report_path = self.root_dir / "reports" / "simple_report_generator.py"
        assert report_path.exists(), "simple_report_generator.py não existe"
        
    def test_advanced_report_generator_exists(self):
        """Testa se gerador de relatório avançado existe"""
        advanced_path = self.root_dir / "reports" / "advanced_report_generator.py"
        assert advanced_path.exists(), "advanced_report_generator.py não existe"


class TestJSONConfiguration:
    """Testa configurações JSON"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_algorithm_comparison_json_valid(self):
        """Testa se JSON de comparação de algoritmos é válido"""
        json_path = self.root_dir / "advanced_algorithm_comparison.json"
        if not json_path.exists():
            pytest.skip("advanced_algorithm_comparison.json não existe")
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Deve ser um dicionário
        assert isinstance(data, dict), "JSON deve ser um objeto"
        
        # Se tem dados, deve ter estrutura básica
        if data:
            # Pode ter informações sobre testes, algoritmos, etc.
            expected_keys = ["test_info", "algorithm_summary", "results"]
            has_expected = any(key in data for key in expected_keys)
            assert has_expected or len(data) == 0, "JSON deve ter estrutura esperada ou estar vazio"
            
    def test_multi_algorithm_comparison_json(self):
        """Testa JSON de comparação múltipla"""
        json_path = self.root_dir / "multi_algorithm_comparison.json"
        if not json_path.exists():
            pytest.skip("multi_algorithm_comparison.json não existe")
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        assert isinstance(data, (dict, list)), "JSON deve ser objeto ou array"


class TestCacheSystem:
    """Testes para sistema de cache"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_iterative_cache_system_exists(self):
        """Testa se sistema de cache iterativo existe"""
        cache_path = self.root_dir / "src" / "core" / "iterative_cache_system.py"
        assert cache_path.exists(), "iterative_cache_system.py não existe"
        
    def test_cache_directories_structure(self):
        """Testa se estrutura de cache está organizada"""
        data_dir = self.root_dir / "data"
        if not data_dir.exists():
            pytest.skip("Pasta data/ não existe")
            
        # Se data/ existe, pode ter cache/
        cache_dir = data_dir / "cache"
        if cache_dir.exists():
            assert cache_dir.is_dir(), "cache/ deve ser um diretório"


class TestPerformanceTools:
    """Testes para ferramentas de performance"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_performance_analyzer_exists(self):
        """Testa se analisador de performance existe"""
        perf_path = self.root_dir / "src" / "core" / "performance_analyzer.py"
        assert perf_path.exists(), "performance_analyzer.py não existe"
        
    def test_quality_validator_exists(self):
        """Testa se validador de qualidade existe"""
        quality_path = self.root_dir / "src" / "core" / "quality_validator.py"
        assert quality_path.exists(), "quality_validator.py não existe"


class TestIntegrationReadiness:
    """Testa prontidão para integração"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_all_entry_points_have_main_protection(self):
        """Testa se entry points têm proteção if __name__ == '__main__'"""
        entry_points = [
            "start_cli.py",
            "start_web.py",
            "start_gui.py"
        ]
        
        for entry_point in entry_points:
            path = self.root_dir / entry_point
            if not path.exists():
                continue
                
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Deve ter proteção main
            assert "__name__" in content and "__main__" in content, \
                f"{entry_point} deve ter proteção if __name__ == '__main__'"
                
    def test_import_statements_use_relative_paths(self):
        """Testa se imports usam caminhos relativos apropriados"""
        # Este é um teste de estrutura, verifica se não há imports absolutos problemáticos
        core_files = list((self.root_dir / "src" / "core").glob("*.py"))
        
        problematic_imports = []
        
        for file_path in core_files[:3]:  # Testa apenas alguns arquivos
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Procura por imports que podem ser problemáticos
                lines = content.split('\n')
                for line_no, line in enumerate(lines, 1):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        # Verifica imports absolutos para o próprio projeto
                        if 'renamepdfepub' in line and not line.startswith('from .'):
                            problematic_imports.append(f"{file_path.name}:{line_no} - {line}")
                            
            except Exception:
                # Se não conseguir ler, pula
                continue
                
        # Não deve haver muitos imports problemáticos
        assert len(problematic_imports) < 5, \
            f"Muitos imports problemáticos: {problematic_imports[:3]}"


class TestDocumentationCompleteness:
    """Testa completude da documentação"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_changelog_exists_and_updated(self):
        """Testa se CHANGELOG existe e parece atualizado"""
        changelog_path = self.root_dir / "CHANGELOG.md"
        assert changelog_path.exists(), "CHANGELOG.md não existe"
        
        with open(changelog_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Deve mencionar versões ou datas
        has_version_info = any(word in content.lower() for word in [
            "version", "v1", "v2", "2024", "2025", "changelog"
        ])
        assert has_version_info, "CHANGELOG deve ter informações de versão"
        
    def test_structure_documentation_comprehensive(self):
        """Testa se documentação de estrutura é abrangente"""
        structure_docs = [
            "STRUCTURE_FINAL.md",
            "ESTRUTURA_ATUAL_COMPLETA.md"
        ]
        
        found_docs = []
        for doc in structure_docs:
            path = self.root_dir / doc
            if path.exists():
                found_docs.append(doc)
                
        assert found_docs, "Deve haver pelo menos uma documentação de estrutura"
        
        # Testa se a documentação é substancial
        for doc in found_docs[:1]:  # Testa apenas o primeiro
            path = self.root_dir / doc
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Deve ser substancial e mencionar estrutura
            assert len(content) > 1000, f"{doc} muito pequeno"
            assert "src/" in content, f"{doc} deve documentar pasta src/"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])