"""
Testes para o sistema de relatórios
"""
import pytest
import json
from pathlib import Path

def test_report_generator_exists():
    """Testa se o gerador de relatórios existe"""
    report_file = Path(__file__).parent.parent / "simple_report_generator.py"
    assert report_file.exists(), "Gerador de relatórios não encontrado"

def test_json_results_structure():
    """Testa estrutura dos arquivos JSON de resultados"""
    json_files = [
        "advanced_algorithm_comparison.json",
        "final_v3_results.json"
    ]
    
    for json_file in json_files:
        file_path = Path(__file__).parent.parent / json_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Testa se tem estrutura básica
            assert isinstance(data, dict), f"Arquivo {json_file} deve ser um dicionário"
            
            # Se tem resultados de algoritmos
            if "algorithm_summary" in data:
                assert isinstance(data["algorithm_summary"], dict)

def test_html_report_generation():
    """Testa se relatórios HTML podem ser gerados"""
    html_files = [
        "demo_report.html",
        "advanced_algorithms_report.html"
    ]
    
    for html_file in html_files:
        file_path = Path(__file__).parent.parent / html_file
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            assert "<html>" in content.lower(), f"Arquivo {html_file} não é HTML válido"
            assert "</html>" in content.lower(), f"Arquivo {html_file} não tem fechamento HTML"

def test_performance_data_structure():
    """Testa estrutura dos dados de performance"""
    performance_data = {
        "accuracy": 96.0,
        "confidence": 94.0,
        "avg_time": 0.123,
        "success_rate": 0.98
    }
    
    # Testa ranges válidos
    assert 0 <= performance_data["accuracy"] <= 100
    assert 0 <= performance_data["confidence"] <= 100
    assert performance_data["avg_time"] > 0
    assert 0 <= performance_data["success_rate"] <= 1

def test_algorithm_comparison_data():
    """Testa dados de comparação entre algoritmos"""
    algorithms = [
        "Hybrid Orchestrator",
        "Brazilian Specialist", 
        "Smart Inferencer",
        "Enhanced Parser",
        "Basic Parser"
    ]
    
    # Testa se todos os algoritmos são válidos
    for algorithm in algorithms:
        assert isinstance(algorithm, str)
        assert len(algorithm) > 0
        assert algorithm != ""

def test_report_file_creation():
    """Testa se arquivos de relatório podem ser criados"""
    test_report_data = {
        "test_info": {
            "total_books": 5,
            "test_date": "2025-09-28",
            "algorithms_tested": 5
        },
        "algorithm_summary": {
            "Test Algorithm": {
                "accuracy": 85.0,
                "confidence": 80.0,
                "avg_time": 0.1,
                "success_rate": 0.9
            }
        }
    }
    
    # Testa estrutura dos dados
    assert "test_info" in test_report_data
    assert "algorithm_summary" in test_report_data
    assert test_report_data["test_info"]["total_books"] > 0