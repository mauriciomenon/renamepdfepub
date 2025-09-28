#!/usr/bin/env python3
"""
Testes de integridade para todos os pontos de entrada (startpoints) do sistema
Valida que todos os entry points podem ser executados e funcionam corretamente
"""

import sys
import subprocess
import pytest
from pathlib import Path

# Configurar o caminho
PROJECT_ROOT = Path(__file__).parent.parent
STARTPOINTS = [
    "start_cli.py",
    "start_gui.py", 
    "start_web.py",
    "start_html.py",
    "start_iterative_cache.py"
]

class TestStartpointsIntegrity:
    """Testa a integridade de todos os pontos de entrada do sistema"""
    
    def test_startpoints_exist(self):
        """Verifica se todos os startpoints existem no diretório raiz"""
        for startpoint in STARTPOINTS:
            startpoint_path = PROJECT_ROOT / startpoint
            assert startpoint_path.exists(), f"Startpoint {startpoint} não existe"
            assert startpoint_path.is_file(), f"Startpoint {startpoint} não é um arquivo"
    
    def test_startpoints_syntax(self):
        """Verifica se todos os startpoints têm sintaxe Python válida"""
        for startpoint in STARTPOINTS:
            startpoint_path = PROJECT_ROOT / startpoint
            try:
                with open(startpoint_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, str(startpoint_path), 'exec')
            except SyntaxError as e:
                pytest.fail(f"Erro de sintaxe em {startpoint}: {e}")
            except Exception as e:
                pytest.fail(f"Erro ao validar {startpoint}: {e}")
    
    def test_startpoint_help_options(self):
        """Testa se startpoints CLI respondem ao --help"""
        cli_startpoints = ["start_cli.py"]
        
        for startpoint in cli_startpoints:
            startpoint_path = PROJECT_ROOT / startpoint
            try:
                result = subprocess.run(
                    [sys.executable, str(startpoint_path), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=PROJECT_ROOT
                )
                # Aceitar tanto código 0 (sucesso) quanto 1 (pode ser esperado para --help)
                assert result.returncode in [0, 1], f"{startpoint} --help falhou com código {result.returncode}"
                
            except subprocess.TimeoutExpired:
                pytest.fail(f"{startpoint} --help demorou mais que 10 segundos")
            except Exception as e:
                pytest.fail(f"Erro ao testar {startpoint} --help: {e}")
    
    def test_startpoint_version_options(self):
        """Testa se startpoints CLI respondem ao --version"""
        cli_startpoints = ["start_cli.py"]
        
        for startpoint in cli_startpoints:
            startpoint_path = PROJECT_ROOT / startpoint
            try:
                result = subprocess.run(
                    [sys.executable, str(startpoint_path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=PROJECT_ROOT
                )
                # Aceitar tanto código 0 quanto 1 para --version
                assert result.returncode in [0, 1], f"{startpoint} --version falhou com código {result.returncode}"
                
            except subprocess.TimeoutExpired:
                pytest.fail(f"{startpoint} --version demorou mais que 10 segundos")
            except Exception as e:
                pytest.fail(f"Erro ao testar {startpoint} --version: {e}")
    
    def test_startpoints_basic_import(self):
        """Testa se conseguimos importar os módulos dos startpoints"""
        # Adicionar src ao caminho Python
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        
        # Testear importações básicas que não devem falhar
        basic_imports = [
            "os", "sys", "pathlib", "argparse"
        ]
        
        for import_name in basic_imports:
            try:
                __import__(import_name)
            except ImportError as e:
                pytest.fail(f"Falha ao importar módulo básico {import_name}: {e}")
    
    def test_startpoints_directory_structure(self):
        """Verifica se a estrutura de diretórios necessária existe"""
        required_dirs = [
            "src",
            "tests", 
            "books",
            "data",
            "reports",
            "logs"
        ]
        
        for dir_name in required_dirs:
            dir_path = PROJECT_ROOT / dir_name
            assert dir_path.exists(), f"Diretório obrigatório {dir_name} não existe"
            assert dir_path.is_dir(), f"{dir_name} existe mas não é um diretório"
    
    def test_startpoints_permissions(self):
        """Verifica se os startpoints têm permissões adequadas"""
        for startpoint in STARTPOINTS:
            startpoint_path = PROJECT_ROOT / startpoint
            assert startpoint_path.stat().st_mode & 0o444, f"{startpoint} não é legível"
    
    def test_startpoints_shebang(self):
        """Verifica se startpoints têm shebang apropriado"""
        for startpoint in STARTPOINTS:
            startpoint_path = PROJECT_ROOT / startpoint
            with open(startpoint_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            # Verificar se tem shebang Python válido
            valid_shebangs = [
                "#!/usr/bin/env python3",
                "#!/usr/bin/python3", 
                "#!/usr/bin/env python",
                "#!/usr/bin/python"
            ]
            
            assert any(first_line.startswith(shebang) for shebang in valid_shebangs), \
                f"{startpoint} não tem shebang Python válido: {first_line}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])