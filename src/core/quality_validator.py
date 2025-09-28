#!/usr/bin/env python3
"""
Validador de Qualidade do Sistema v0.11.0
========================================

Valida qualidade de código, documentação e funcionalidades
antes do release final.
"""

import ast
import os
import sys
from pathlib import Path
import json
import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

class QualityValidator:
    """Validador de qualidade do sistema"""
    
    def __init__(self):
        self.root_path = Path('.')
        self.issues = defaultdict(list)
        self.metrics = defaultdict(int)
        
    def validate_python_files(self) -> Dict[str, Any]:
        """Valida arquivos Python do projeto"""
        print("🔍 Validando arquivos Python...")
        
        python_files = [
            'advanced_algorithm_comparison.py',
            'simple_report_generator.py',
            'streamlit_interface.py',
            'web_launcher.py',
            'demo_system.py',
            'comprehensive_test_suite.py'
        ]
        
        results = {}
        
        for filename in python_files:
            if not Path(filename).exists():
                self.issues['missing_files'].append(filename)
                continue
                
            file_metrics = self.analyze_python_file(filename)
            results[filename] = file_metrics
            
        return results
    
    def analyze_python_file(self, filename: str) -> Dict[str, Any]:
        """Analisa um arquivo Python específico"""
        metrics = {
            'lines': 0,
            'functions': 0,
            'classes': 0,
            'docstrings': 0,
            'comments': 0,
            'imports': 0,
            'syntax_ok': False,
            'encoding_ok': False
        }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                metrics['encoding_ok'] = True
        except UnicodeDecodeError:
            self.issues['encoding_errors'].append(filename)
            return metrics
        
        # Conta linhas
        lines = content.splitlines()
        metrics['lines'] = len(lines)
        
        # Conta comentários
        for line in lines:
            if line.strip().startswith('#'):
                metrics['comments'] += 1
        
        # Analisa AST
        try:
            tree = ast.parse(content, filename)
            metrics['syntax_ok'] = True
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics['functions'] += 1
                    if ast.get_docstring(node):
                        metrics['docstrings'] += 1
                        
                elif isinstance(node, ast.ClassDef):
                    metrics['classes'] += 1
                    if ast.get_docstring(node):
                        metrics['docstrings'] += 1
                        
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics['imports'] += 1
                    
        except SyntaxError as e:
            self.issues['syntax_errors'].append(f"{filename}: {e}")
            
        return metrics
    
    def validate_documentation(self) -> Dict[str, Any]:
        """Valida documentação do projeto"""
        print("📚 Validando documentação...")
        
        doc_files = [
            'README.md',
            'CHANGELOG.md',
            'RELEASE_NOTES_v0.11.0_ADVANCED_ALGORITHMS.md'
        ]
        
        results = {}
        
        for filename in doc_files:
            if Path(filename).exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                results[filename] = {
                    'exists': True,
                    'length': len(content),
                    'lines': len(content.splitlines()),
                    'has_headers': bool(re.search(r'^#+ ', content, re.MULTILINE)),
                    'has_code_blocks': bool(re.search(r'```', content)),
                    'has_emojis': bool(re.search(r'[📚🔍⚠🎉]', content))
                }
            else:
                results[filename] = {'exists': False}
                self.issues['missing_docs'].append(filename)
                
        return results
    
    def validate_functionality(self) -> Dict[str, Any]:
        """Valida funcionalidades principais"""
        print("⚙ Validando funcionalidades...")
        
        results = {
            'algorithm_system': self.test_algorithm_imports(),
            'report_generation': self.test_report_generation(),
            'web_interface': self.test_web_interface(),
            'brazilian_features': self.test_brazilian_features()
        }
        
        return results
    
    def test_algorithm_imports(self) -> Dict[str, bool]:
        """Testa importação dos algoritmos"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            
            # Testa importações principais
            imports = {}
            
            try:
                from advanced_algorithm_comparison import AlgorithmComparison
                imports['AlgorithmComparison'] = True
            except Exception:
                imports['AlgorithmComparison'] = False
                
            try:
                from advanced_algorithm_comparison import BrazilianSpecialist
                imports['BrazilianSpecialist'] = True
            except Exception:
                imports['BrazilianSpecialist'] = False
                
            try:
                from simple_report_generator import SimpleReportGenerator
                imports['SimpleReportGenerator'] = True
            except Exception:
                imports['SimpleReportGenerator'] = False
                
            return imports
            
        except Exception as e:
            self.issues['import_errors'].append(str(e))
            return {}
    
    def test_report_generation(self) -> bool:
        """Testa geração básica de relatórios"""
        try:
            from simple_report_generator import SimpleReportGenerator
            generator = SimpleReportGenerator()
            
            # Dados de teste
            test_data = {
                'test_info': {'total_books': 1},
                'algorithm_summary': {
                    'Test Algorithm': {
                        'avg_accuracy': 0.95,
                        'avg_confidence': 0.90,
                        'avg_time': 0.1,
                        'success_rate': 0.98
                    }
                },
                'detailed_results': []
            }
            
            html = generator.generate_html_report(test_data)
            return isinstance(html, str) and len(html) > 1000
            
        except Exception as e:
            self.issues['report_errors'].append(str(e))
            return False
    
    def test_web_interface(self) -> bool:
        """Testa interface web básica"""
        try:
            # Verifica se streamlit_interface.py existe e é válido
            if not Path('streamlit_interface.py').exists():
                return False
                
            with open('streamlit_interface.py', 'r') as f:
                content = f.read()
                
            # Verifica componentes principais
            required_components = [
                'StreamlitInterface',
                'st.set_page_config',
                'render_header',
                'render_metrics_overview'
            ]
            
            for component in required_components:
                if component not in content:
                    self.issues['web_interface'].append(f"Missing: {component}")
                    return False
                    
            return True
            
        except Exception as e:
            self.issues['web_interface'].append(str(e))
            return False
    
    def test_brazilian_features(self) -> Dict[str, bool]:
        """Testa funcionalidades brasileiras"""
        try:
            from advanced_algorithm_comparison import BrazilianSpecialist
            specialist = BrazilianSpecialist()
            
            tests = {
                'publisher_detection': False,
                'name_patterns': False,
                'portuguese_words': False
            }
            
            # Testa detecção de editora
            if hasattr(specialist, 'is_brazilian_publisher'):
                tests['publisher_detection'] = specialist.is_brazilian_publisher("Casa do Código")
                
            # Testa padrões de nome
            if hasattr(specialist, 'has_brazilian_name_pattern'):
                tests['name_patterns'] = specialist.has_brazilian_name_pattern("João Silva")
                
            # Testa palavras em português
            if hasattr(specialist, 'has_portuguese_words'):
                tests['portuguese_words'] = specialist.has_portuguese_words("programação")
                
            return tests
            
        except Exception as e:
            self.issues['brazilian_features'].append(str(e))
            return {}
    
    def generate_quality_report(self) -> str:
        """Gera relatório de qualidade"""
        print("📊 Gerando relatório de qualidade...")
        
        # Executa todas as validações
        python_results = self.validate_python_files()
        doc_results = self.validate_documentation()
        func_results = self.validate_functionality()
        
        # Calcula métricas
        total_files = len(python_results)
        valid_syntax = sum(1 for r in python_results.values() if r.get('syntax_ok', False))
        total_lines = sum(r.get('lines', 0) for r in python_results.values())
        total_functions = sum(r.get('functions', 0) for r in python_results.values())
        total_classes = sum(r.get('classes', 0) for r in python_results.values())
        
        # Gera relatório
        report = f"""
# 📊 RELATÓRIO DE QUALIDADE v0.11.0
## Gerado em: {Path.cwd()}

### 🔍 Análise de Código Python
- **Arquivos analisados**: {total_files}
- **Sintaxe válida**: {valid_syntax}/{total_files} ({(valid_syntax/total_files)*100:.1f}%)
- **Total de linhas**: {total_lines:,}
- **Funções**: {total_functions}
- **Classes**: {total_classes}

### 📚 Documentação
"""
        
        for filename, info in doc_results.items():
            status = "" if info.get('exists', False) else ""
            lines = info.get('lines', 0)
            report += f"- **{filename}**: {status} ({lines} linhas)\n"
        
        report += "\n### ⚙ Funcionalidades\n"
        
        for feature, result in func_results.items():
            if isinstance(result, dict):
                passed = sum(1 for v in result.values() if v)
                total = len(result)
                status = "" if passed == total else "⚠"
                report += f"- **{feature}**: {status} ({passed}/{total})\n"
            else:
                status = "" if result else ""
                report += f"- **{feature}**: {status}\n"
        
        # Issues encontrados
        if self.issues:
            report += "\n### ⚠ Issues Encontrados\n"
            for category, issues in self.issues.items():
                if issues:
                    report += f"\n**{category.replace('_', ' ').title()}:**\n"
                    for issue in issues:
                        report += f"- {issue}\n"
        
        # Pontuação geral
        score = self.calculate_quality_score(python_results, doc_results, func_results)
        report += f"\n### 🎯 Pontuação Geral: {score:.1f}/100\n"
        
        if score >= 80:
            report += " **APROVADO PARA RELEASE**\n"
        elif score >= 60:
            report += "⚠ **PRECISA DE MELHORIAS**\n"
        else:
            report += " **NÃO RECOMENDADO PARA RELEASE**\n"
        
        return report
    
    def calculate_quality_score(self, python_results, doc_results, func_results) -> float:
        """Calcula pontuação de qualidade (0-100)"""
        score = 0
        
        # Sintaxe Python (30 pontos)
        if python_results:
            valid_syntax = sum(1 for r in python_results.values() if r.get('syntax_ok', False))
            score += (valid_syntax / len(python_results)) * 30
        
        # Documentação (20 pontos)
        if doc_results:
            valid_docs = sum(1 for r in doc_results.values() if r.get('exists', False))
            score += (valid_docs / len(doc_results)) * 20
        
        # Funcionalidades (50 pontos)
        if func_results:
            total_tests = 0
            passed_tests = 0
            
            for result in func_results.values():
                if isinstance(result, dict):
                    total_tests += len(result)
                    passed_tests += sum(1 for v in result.values() if v)
                elif isinstance(result, bool):
                    total_tests += 1
                    passed_tests += 1 if result else 0
            
            if total_tests > 0:
                score += (passed_tests / total_tests) * 50
        
        return min(100, score)

def main():
    """Função principal"""
    print("🔍 VALIDADOR DE QUALIDADE RENAMEPDFEPUB v0.11.0")
    print("=" * 60)
    
    validator = QualityValidator()
    report = validator.generate_quality_report()
    
    # Salva relatório
    report_file = "QUALITY_REPORT_v0.11.0.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 Relatório salvo em: {report_file}")
    print("\n" + report)
    
    return 0

if __name__ == "__main__":
    exit(main())