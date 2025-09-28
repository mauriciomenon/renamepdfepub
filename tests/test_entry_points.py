#!/usr/bin/env python3
"""
Testes para Entry Points do Sistema
==================================

Testa todos os pontos de entrada do sistema para garantir
que funcionam corretamente com argumentos CLI.
"""

import sys
import subprocess
import pytest
from pathlib import Path


class TestEntryPoints:
    """Testes para pontos de entrada do sistema"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.root_dir = Path(__file__).parent.parent
        self.python_exec = sys.executable
        
    def test_start_cli_help(self):
        """Testa se start_cli.py responde ao --help"""
        script_path = self.root_dir / "start_cli.py"
        if not script_path.exists():
            pytest.skip("start_cli.py não existe")
            
        result = subprocess.run([
            self.python_exec, str(script_path), "--help"
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"
        assert "RenamePDFEPUB" in result.stdout
        assert "--help" in result.stdout or "help" in result.stdout
        
    def test_start_cli_version(self):
        """Testa se start_cli.py responde ao --version"""
        script_path = self.root_dir / "start_cli.py"
        if not script_path.exists():
            pytest.skip("start_cli.py não existe")
            
        result = subprocess.run([
            self.python_exec, str(script_path), "--version"
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, f"CLI version failed: {result.stderr}"
        assert any(word in result.stdout.lower() for word in ["version", "v1", "v2", "renamepdfepub"])
        
    def test_start_web_help(self):
        """Testa se start_web.py responde ao --help"""
        script_path = self.root_dir / "start_web.py"
        if not script_path.exists():
            pytest.skip("start_web.py não existe")
            
        result = subprocess.run([
            self.python_exec, str(script_path), "--help"
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, f"Web help failed: {result.stderr}"
        assert any(word in result.stdout.lower() for word in ["web", "streamlit", "interface"])
        
    def test_start_gui_help(self):
        """Testa se start_gui.py responde ao --help"""
        script_path = self.root_dir / "start_gui.py"
        if not script_path.exists():
            pytest.skip("start_gui.py não existe")
            
        result = subprocess.run([
            self.python_exec, str(script_path), "--help"
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, f"GUI help failed: {result.stderr}"
        assert any(word in result.stdout.lower() for word in ["gui", "grafica", "interface"])
        
    def test_start_gui_check_deps(self):
        """Testa verificação de dependências do GUI"""
        script_path = self.root_dir / "start_gui.py"
        if not script_path.exists():
            pytest.skip("start_gui.py não existe")
            
        result = subprocess.run([
            self.python_exec, str(script_path), "--check-deps"
        ], capture_output=True, text=True, timeout=10)
        
        # Deve executar sem erro, mesmo que falte alguma dependência
        assert result.returncode in [0, 1], f"Check deps failed: {result.stderr}"
        assert any(word in result.stdout.lower() for word in ["tkinter", "dependencia", "gui"])

    def test_entry_points_exist(self):
        """Testa se todos os entry points existem"""
        entry_points = [
            "start_cli.py",
            "start_web.py", 
            "start_gui.py",
            "start_html.py"
        ]
        
        missing_files = []
        for entry_point in entry_points:
            path = self.root_dir / entry_point
            if not path.exists():
                missing_files.append(entry_point)
        
        assert not missing_files, f"Entry points ausentes: {missing_files}"
        
    def test_entry_points_are_executable(self):
        """Testa se entry points são executáveis Python válidos"""
        entry_points = [
            "start_cli.py",
            "start_web.py",
            "start_gui.py"
        ]
        
        for entry_point in entry_points:
            path = self.root_dir / entry_point
            if not path.exists():
                continue
                
            # Testa se o arquivo é sintaxe Python válida
            result = subprocess.run([
                self.python_exec, "-m", "py_compile", str(path)
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, f"{entry_point} tem erro de sintaxe: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])