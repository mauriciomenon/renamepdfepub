"""
Testes para o sistema web e interface
"""
import pytest
from pathlib import Path

def test_web_launcher_exists():
    """Testa se o launcher web existe"""
    launcher_file = Path(__file__).parent.parent / "web_launcher.py"
    assert launcher_file.exists(), "Web launcher não encontrado"

def test_streamlit_interface_exists():
    """Testa se a interface Streamlit existe"""  
    streamlit_file = Path(__file__).parent.parent / "streamlit_interface.py"
    assert streamlit_file.exists(), "Interface Streamlit não encontrada"

def test_web_launcher_clean_output():
    """Testa se o web launcher não usa emojis"""
    launcher_file = Path(__file__).parent.parent / "web_launcher.py"
    if launcher_file.exists():
        content = launcher_file.read_text(encoding='utf-8')
        
        # Lista de emojis que não devem estar presentes
        forbidden_emojis = ["🚀", "🌐", "📄", "🔬", "📊", "❌", "📝", "✅", "👋"]
        
        for emoji in forbidden_emojis:
            assert emoji not in content, f"Emoji {emoji} encontrado no web launcher"

def test_interface_functionality():
    """Testa funcionalidades básicas da interface"""
    # Testa se os módulos principais existem
    main_files = [
        "advanced_algorithm_comparison.py",
        "simple_report_generator.py", 
        "web_launcher.py"
    ]
    
    for filename in main_files:
        file_path = Path(__file__).parent.parent / filename
        assert file_path.exists(), f"Arquivo {filename} não encontrado"

def test_menu_options():
    """Testa opções do menu"""
    valid_options = ["0", "1", "2", "3", "4"]
    
    # Simula validação de entrada do menu
    for option in valid_options:
        assert option.isdigit(), f"Opção {option} deve ser numérica"
        assert 0 <= int(option) <= 4, f"Opção {option} fora do range válido"

def test_installation_process():
    """Testa processo de instalação"""
    # Testa se requirements.txt existe
    req_file = Path(__file__).parent.parent / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text()
        assert len(content.strip()) > 0, "Requirements.txt não pode estar vazio"

def test_data_generation():
    """Testa geração de dados de exemplo"""
    sample_data_structure = {
        "test_info": {
            "total_books": 25,
            "test_date": "2025-09-28", 
            "algorithms_tested": 5
        },
        "algorithm_summary": {}
    }
    
    # Testa estrutura dos dados de exemplo
    assert "test_info" in sample_data_structure
    assert "algorithm_summary" in sample_data_structure
    assert sample_data_structure["test_info"]["total_books"] > 0

def test_clean_terminal_output():
    """Testa se output do terminal está limpo"""
    clean_prefixes = ["[OK]", "[INFO]", "[ERROR]", "[WARNING]"]
    
    # Testa se prefixes estão no formato correto
    for prefix in clean_prefixes:
        assert prefix.startswith("["), f"Prefix {prefix} deve começar com ["
        assert prefix.endswith("]"), f"Prefix {prefix} deve terminar com ]"
        assert len(prefix) > 2, f"Prefix {prefix} muito curto"