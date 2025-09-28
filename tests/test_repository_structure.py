#!/usr/bin/env python3
"""
Testes de Estrutura do Repositório
=================================

Verifica se a estrutura de pastas e arquivos está correta
e se as referências cruzadas funcionam.
"""

import sys
import pytest
from pathlib import Path


class TestRepositoryStructure:
    """Testes de estrutura do repositório"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_src_structure_exists(self):
        """Testa se a estrutura src/ existe"""
        src_dir = self.root_dir / "src"
        assert src_dir.exists(), "Pasta src/ não existe"
        assert src_dir.is_dir(), "src/ não é um diretório"
        
        # Testa subpastas principais
        core_dir = src_dir / "core"
        gui_dir = src_dir / "gui"
        cli_dir = src_dir / "cli"
        
        assert core_dir.exists(), "Pasta src/core/ não existe"
        assert gui_dir.exists(), "Pasta src/gui/ não existe"
        assert cli_dir.exists(), "Pasta src/cli/ não existe"
        
    def test_core_modules_exist(self):
        """Testa se módulos principais existem"""
        core_modules = [
            "src/core/advanced_algorithm_comparison.py",
            "src/core/algorithms_v3.py",
            "src/core/amazon_api_integration.py",
            "src/core/auto_rename_system.py"
        ]
        
        missing_modules = []
        for module in core_modules:
            path = self.root_dir / module
            if not path.exists():
                missing_modules.append(module)
        
        assert not missing_modules, f"Módulos core ausentes: {missing_modules}"
        
    def test_gui_modules_exist(self):
        """Testa se módulos GUI existem"""
        gui_modules = [
            "src/gui/web_launcher.py",
            "src/gui/streamlit_interface.py",
            "src/gui/gui_modern.py"
        ]
        
        missing_modules = []
        for module in gui_modules:
            path = self.root_dir / module
            if not path.exists():
                missing_modules.append(module)
                
        assert not missing_modules, f"Módulos GUI ausentes: {missing_modules}"
        
    def test_reports_structure(self):
        """Testa estrutura da pasta reports"""
        reports_dir = self.root_dir / "reports"
        assert reports_dir.exists(), "Pasta reports/ não existe"
        
        # Testa se simple_report_generator existe
        simple_gen = reports_dir / "simple_report_generator.py"
        assert simple_gen.exists(), "simple_report_generator.py não existe em reports/"
        
    def test_utils_structure(self):
        """Testa estrutura da pasta utils"""
        utils_dir = self.root_dir / "utils"
        assert utils_dir.exists(), "Pasta utils/ não existe"
        
        # Testa alguns utilitários importantes
        validators = [
            "cross_reference_validator.py",
            "quick_validation.py"
        ]
        
        for validator in validators:
            path = utils_dir / validator
            assert path.exists(), f"Utilitário {validator} não existe"
            
    def test_documentation_exists(self):
        """Testa se documentação principal existe"""
        docs = [
            "README.md",
            "CHANGELOG.md", 
            "STRUCTURE_FINAL.md",
            ".copilot-instructions.md"
        ]
        
        missing_docs = []
        for doc in docs:
            path = self.root_dir / doc
            if not path.exists():
                missing_docs.append(doc)
                
        assert not missing_docs, f"Documentação ausente: {missing_docs}"
        
    def test_config_files_exist(self):
        """Testa se arquivos de configuração existem"""
        config_files = [
            "requirements.txt",
            "pytest.ini",
            ".gitignore"
        ]
        
        missing_configs = []
        for config in config_files:
            path = self.root_dir / config
            if not path.exists():
                missing_configs.append(config)
                
        assert not missing_configs, f"Configs ausentes: {missing_configs}"


class TestCrossReferences:
    """Testa referências cruzadas entre arquivos"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_web_launcher_references(self):
        """Testa se web_launcher.py pode encontrar seus arquivos referenciados"""
        web_launcher = self.root_dir / "src" / "gui" / "web_launcher.py"
        if not web_launcher.exists():
            pytest.skip("web_launcher.py não existe")
            
        # Arquivos que devem existir para web_launcher funcionar
        required_files = [
            self.root_dir / "src" / "gui" / "streamlit_interface.py",
            self.root_dir / "reports" / "simple_report_generator.py",
            self.root_dir / "src" / "core" / "advanced_algorithm_comparison.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path.relative_to(self.root_dir)))
                
        assert not missing_files, f"Arquivos referenciados ausentes: {missing_files}"
        
    def test_start_cli_references(self):
        """Testa se start_cli.py pode encontrar seus módulos"""
        start_cli = self.root_dir / "start_cli.py"
        if not start_cli.exists():
            pytest.skip("start_cli.py não existe")
            
        # Módulos que start_cli tenta importar
        required_modules = [
            self.root_dir / "src" / "core" / "advanced_algorithm_comparison.py",
            self.root_dir / "src" / "cli" / "launch_system.py"
        ]
        
        missing_modules = []
        for module_path in required_modules:
            if not module_path.exists():
                missing_modules.append(str(module_path.relative_to(self.root_dir)))
                
        assert not missing_modules, f"Módulos referenciados ausentes: {missing_modules}"
        
    def test_import_structure(self):
        """Testa se a estrutura permite imports corretos"""
        # Adiciona src ao path temporariamente
        src_path = str(self.root_dir / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            
        try:
            # Tenta imports básicos que devem funcionar
            import importlib.util
            
            # Testa se conseguimos carregar módulos principais
            modules_to_test = [
                self.root_dir / "src" / "gui" / "web_launcher.py",
                self.root_dir / "reports" / "simple_report_generator.py"
            ]
            
            import_errors = []
            for module_path in modules_to_test:
                if not module_path.exists():
                    continue
                    
                spec = importlib.util.spec_from_file_location(
                    module_path.stem, module_path
                )
                if spec is None:
                    import_errors.append(f"Não conseguiu criar spec para {module_path.name}")
                    continue
                    
                try:
                    module = importlib.util.module_from_spec(spec)
                    # Não executa o módulo, apenas testa se pode ser carregado
                except Exception as e:
                    import_errors.append(f"Erro ao carregar {module_path.name}: {e}")
                    
            assert not import_errors, f"Erros de import: {import_errors}"
            
        finally:
            # Remove src do path
            if src_path in sys.path:
                sys.path.remove(src_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])