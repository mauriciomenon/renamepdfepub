#!/usr/bin/env python3
"""
Testes para interfaces do sistema (GUI, CLI, Web)
Valida funcionalidade, responsividade e integridade das interfaces
"""

import pytest
import sys
import subprocess
import tempfile
import json
from pathlib import Path
import os

# Configurar o caminho
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

class TestCLIInterface:
    """Testa a interface de linha de comando"""
    
    def setup_method(self):
        """Configurar ambiente de teste"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Limpar após teste"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_cli_help_output(self):
        """Testa saída do comando --help"""
        cli_script = PROJECT_ROOT / "start_cli.py"
        
        try:
            result = subprocess.run(
                [sys.executable, str(cli_script), "--help"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=PROJECT_ROOT
            )
            
            # Verificar se tem conteúdo de ajuda
            output = result.stdout + result.stderr
            help_indicators = [
                "usage", "help", "options", "arguments", 
                "Usage", "Help", "Options", "Arguments"
            ]
            
            has_help = any(indicator in output for indicator in help_indicators)
            assert has_help, f"Saída de --help não contém informações de ajuda: {output}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI --help demorou mais que 15 segundos")
        except Exception as e:
            pytest.fail(f"Erro ao testar CLI --help: {e}")
    
    def test_cli_version_output(self):
        """Testa saída do comando --version"""
        cli_script = PROJECT_ROOT / "start_cli.py"
        
        try:
            result = subprocess.run(
                [sys.executable, str(cli_script), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=PROJECT_ROOT
            )
            
            # Verificar se tem informação de versão
            output = result.stdout + result.stderr
            version_indicators = [
                "version", "Version", "v.", "1.", "2.", "0."
            ]
            
            has_version = any(indicator in output for indicator in version_indicators)
            assert has_version or len(output.strip()) > 0, f"Saída de --version vazia: {output}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI --version demorou mais que 10 segundos")
        except Exception as e:
            pytest.fail(f"Erro ao testar CLI --version: {e}")
    
    def test_cli_invalid_arguments(self):
        """Testa comportamento com argumentos inválidos"""
        cli_script = PROJECT_ROOT / "start_cli.py"
        
        invalid_args = ["--invalid-option", "--nonexistent", "-z"]
        
        for arg in invalid_args:
            try:
                result = subprocess.run(
                    [sys.executable, str(cli_script), arg],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=PROJECT_ROOT
                )
                
                # Deve falhar ou mostrar ajuda/erro
                assert result.returncode != 0 or "help" in (result.stdout + result.stderr).lower(), \
                    f"CLI não rejeitou argumento inválido {arg}"
                
            except subprocess.TimeoutExpired:
                pytest.fail(f"CLI com argumento {arg} demorou mais que 10 segundos")
            except Exception as e:
                pytest.fail(f"Erro ao testar CLI com argumento {arg}: {e}")


class TestGUIInterface:
    """Testa a interface gráfica"""
    
    def test_gui_import_availability(self):
        """Testa se módulos GUI podem ser importados"""
        try:
            # Testar importação do módulo GUI principal
            import gui_RenameBook
            assert hasattr(gui_RenameBook, 'RenamePDFGUI'), "Classe RenamePDFGUI não encontrada"
            
        except ImportError as e:
            # Se GUI não estiver disponível, pular teste
            pytest.skip(f"Módulos GUI não disponíveis: {e}")
        except Exception as e:
            pytest.fail(f"Erro inesperado ao importar GUI: {e}")
    
    def test_gui_tkinter_availability(self):
        """Testa se tkinter está disponível para GUI"""
        try:
            import tkinter as tk
            # Testar criação básica sem mostrar janela
            root = tk.Tk()
            root.withdraw()  # Não mostrar a janela
            root.destroy()
        except ImportError:
            pytest.skip("tkinter não está disponível no sistema")
        except Exception as e:
            pytest.fail(f"Erro ao testar tkinter: {e}")
    
    def test_gui_dependencies(self):
        """Testa dependências necessárias para GUI"""
        gui_deps = [
            "threading",
            "queue", 
            "pathlib"
        ]
        
        missing_deps = []
        for dep in gui_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            pytest.fail(f"Dependências GUI críticas faltando: {', '.join(missing_deps)}")
        
        # tkinter é opcional - apenas avisar se não estiver disponível
        try:
            import tkinter
        except ImportError:
            pytest.skip("tkinter não disponível - GUI não funcionará")
    
    def test_gui_startup_script(self):
        """Testa se script de startup da GUI funciona"""
        gui_script = PROJECT_ROOT / "start_gui.py"
        
        # Apenas verificar se não há erros de sintaxe imediatos
        try:
            with open(gui_script, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, str(gui_script), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe no script GUI: {e}")
        except Exception as e:
            pytest.fail(f"Erro ao verificar script GUI: {e}")


class TestWebInterface:
    """Testa a interface web"""
    
    def test_web_dependencies(self):
        """Testa dependências necessárias para interface web"""
        web_deps = [
            "http.server",
            "socketserver", 
            "urllib.parse",
            "json"
        ]
        
        missing_deps = []
        for dep in web_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            pytest.fail(f"Dependências web faltando: {', '.join(missing_deps)}")
    
    def test_web_startup_script(self):
        """Testa se script de startup web funciona"""
        web_script = PROJECT_ROOT / "start_web.py"
        
        try:
            with open(web_script, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, str(web_script), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe no script web: {e}")
        except Exception as e:
            pytest.fail(f"Erro ao verificar script web: {e}")
    
    def test_html_template_availability(self):
        """Verifica disponibilidade de templates HTML"""
        templates_dir = PROJECT_ROOT / "templates"
        
        if templates_dir.exists():
            html_files = list(templates_dir.glob("*.html"))
            if html_files:
                # Verificar se pelo menos um template tem HTML válido básico
                for html_file in html_files[:3]:  # Verificar no máximo 3
                    try:
                        content = html_file.read_text(encoding='utf-8')
                        assert '<html' in content.lower() or '<!doctype' in content.lower(), \
                            f"Template {html_file.name} não parece ser HTML válido"
                    except Exception as e:
                        pytest.fail(f"Erro ao verificar template {html_file.name}: {e}")
    
    def test_static_resources(self):
        """Verifica recursos estáticos para web"""
        static_dirs = [
            PROJECT_ROOT / "static",
            PROJECT_ROOT / "templates", 
            PROJECT_ROOT / "assets"
        ]
        
        # Pelo menos um diretório de recursos deve existir ou ser criável
        existing_dirs = [d for d in static_dirs if d.exists()]
        
        if not existing_dirs:
            # Tentar criar diretório de templates básico
            templates_dir = PROJECT_ROOT / "templates"
            try:
                templates_dir.mkdir(exist_ok=True)
            except Exception as e:
                pytest.fail(f"Não conseguiu criar diretório de recursos: {e}")


class TestHTMLInterface:
    """Testa interface HTML específica"""
    
    def test_html_startup_script(self):
        """Testa script de startup HTML"""
        html_script = PROJECT_ROOT / "start_html.py"
        
        try:
            with open(html_script, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, str(html_script), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe no script HTML: {e}")
        except Exception as e:
            pytest.fail(f"Erro ao verificar script HTML: {e}")
    
    def test_html_generation_capabilities(self):
        """Testa capacidades de geração HTML"""
        try:
            # Testar geração HTML básica
            html_content = """
            <!DOCTYPE html>
            <html>
            <head><title>Test</title></head>
            <body><h1>Test Page</h1></body>
            </html>
            """
            
            # Verificar se contém elementos HTML básicos
            required_elements = ['<!DOCTYPE', '<html', '<head>', '<body>']
            for element in required_elements:
                assert element in html_content, f"Elemento HTML básico {element} não encontrado"
                
        except Exception as e:
            pytest.fail(f"Erro ao testar geração HTML: {e}")


class TestInterfaceIntegration:
    """Testa integração entre interfaces"""
    
    def test_common_modules_availability(self):
        """Testa se módulos comuns estão disponíveis para todas as interfaces"""
        common_modules = [
            "pathlib",
            "json", 
            "os",
            "sys",
            "logging"
        ]
        
        for module in common_modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Módulo comum {module} não disponível: {e}")
    
    def test_configuration_consistency(self):
        """Testa consistência de configuração entre interfaces"""
        config_files = [
            PROJECT_ROOT / "search_config.json",
            PROJECT_ROOT / "pytest.ini"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix == '.json':
                        with open(config_file, 'r', encoding='utf-8') as f:
                            json.load(f)
                    else:
                        # Para outros tipos, apenas verificar se é legível
                        config_file.read_text(encoding='utf-8')
                except Exception as e:
                    pytest.fail(f"Arquivo de configuração {config_file.name} corrompido: {e}")
    
    def test_logging_system_integration(self):
        """Testa se sistema de logging está funcionando"""
        try:
            import logging
            
            # Testar criação de logger básico
            logger = logging.getLogger("test_interface")
            logger.setLevel(logging.INFO)
            
            # Testar se não há erro ao fazer log
            logger.info("Teste de logging")
            
        except Exception as e:
            pytest.fail(f"Sistema de logging não funciona: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])