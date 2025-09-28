#!/usr/bin/env python3
"""
Testes de Utilitários e Ferramentas
===================================

Testa os utilitários de validação e ferramentas auxiliares.
"""

import sys
import json
import pytest
from pathlib import Path


class TestValidationTools:
    """Testes para ferramentas de validação"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_cross_reference_validator_exists(self):
        """Testa se validador de referências existe e é executável"""
        validator_path = self.root_dir / "utils" / "cross_reference_validator.py"
        assert validator_path.exists(), "cross_reference_validator.py não existe"
        
        # Testa se é Python válido
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "py_compile", str(validator_path)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Validador tem erro de sintaxe: {result.stderr}"
        
    def test_quick_validation_exists(self):
        """Testa se validação rápida existe"""
        quick_val_path = self.root_dir / "utils" / "quick_validation.py"
        assert quick_val_path.exists(), "quick_validation.py não existe"
        
    def test_validation_tools_no_emojis(self):
        """Testa se ferramentas de validação não têm emojis"""
        validation_files = [
            self.root_dir / "utils" / "cross_reference_validator.py",
            self.root_dir / "utils" / "quick_validation.py"
        ]
        
        emoji_patterns = ["✅", "❌", "🎯", "🚀", "⚠️"]
        
        for file_path in validation_files:
            if not file_path.exists():
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            found_emojis = []
            for emoji in emoji_patterns:
                if emoji in content:
                    found_emojis.append(emoji)
                    
            assert not found_emojis, f"Emojis encontrados em {file_path.name}: {found_emojis}"


class TestDocumentationQuality:
    """Testes de qualidade da documentação"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_readme_exists_and_not_empty(self):
        """Testa se README existe e não está vazio"""
        readme_path = self.root_dir / "README.md"
        assert readme_path.exists(), "README.md não existe"
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        assert len(content) > 100, "README muito pequeno (menos de 100 caracteres)"
        assert "RenamePDFEPUB" in content or "renamepdfepub" in content, "README não menciona o projeto"
        
    def test_copilot_instructions_exists(self):
        """Testa se instruções do Copilot existem"""
        instructions_path = self.root_dir / ".copilot-instructions.md"
        assert instructions_path.exists(), ".copilot-instructions.md não existe"
        
        with open(instructions_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Deve conter regras sobre emojis
        assert "emoji" in content.lower(), "Instruções devem mencionar política de emojis"
        assert "ascii" in content.lower(), "Instruções devem mencionar ASCII"
        
    def test_structure_documentation_updated(self):
        """Testa se documentação de estrutura está atualizada"""
        structure_docs = [
            self.root_dir / "STRUCTURE_FINAL.md",
            self.root_dir / "ESTRUTURA_ATUAL_COMPLETA.md"
        ]
        
        existing_docs = [doc for doc in structure_docs if doc.exists()]
        assert existing_docs, "Nenhuma documentação de estrutura encontrada"
        
        # Testa se pelo menos uma tem conteúdo recente
        for doc in existing_docs:
            with open(doc, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Deve mencionar estrutura atual
            assert "src/" in content, f"{doc.name} deve documentar pasta src/"
            assert any(word in content for word in ["entry", "point", "start_"]), \
                f"{doc.name} deve mencionar entry points"


class TestConfigurationFiles:
    """Testes de arquivos de configuração"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_requirements_txt_exists(self):
        """Testa se requirements.txt existe e tem conteúdo"""
        req_path = self.root_dir / "requirements.txt"
        assert req_path.exists(), "requirements.txt não existe"
        
        with open(req_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        assert len(lines) > 0, "requirements.txt está vazio"
        
    def test_pytest_ini_exists(self):
        """Testa se configuração pytest existe"""
        pytest_path = self.root_dir / "pytest.ini"
        assert pytest_path.exists(), "pytest.ini não existe"
        
    def test_gitignore_covers_basics(self):
        """Testa se .gitignore cobre o básico"""
        gitignore_path = self.root_dir / ".gitignore"
        assert gitignore_path.exists(), ".gitignore não existe"
        
        with open(gitignore_path, 'r') as f:
            content = f.read()
            
        # Deve ignorar arquivos Python básicos
        essential_ignores = ["__pycache__", "*.pyc", ".venv"]
        missing_ignores = []
        
        for ignore in essential_ignores:
            if ignore not in content:
                missing_ignores.append(ignore)
                
        assert not missing_ignores, f"Faltam ignores essenciais: {missing_ignores}"


class TestJSONFiles:
    """Testes para arquivos JSON do sistema"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        
    def test_json_files_valid(self):
        """Testa se arquivos JSON são válidos"""
        json_files = [
            self.root_dir / "advanced_algorithm_comparison.json",
            self.root_dir / "multi_algorithm_comparison.json",
            self.root_dir / "search_config.json"
        ]
        
        json_errors = []
        for json_file in json_files:
            if not json_file.exists():
                continue
                
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                json_errors.append(f"{json_file.name}: {e}")
                
        assert not json_errors, f"Erros em arquivos JSON: {json_errors}"
        
    def test_search_config_structure(self):
        """Testa estrutura do search_config.json"""
        config_path = self.root_dir / "search_config.json"
        if not config_path.exists():
            pytest.skip("search_config.json não existe")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Deve ser um dicionário
        assert isinstance(config, dict), "search_config deve ser um objeto JSON"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])