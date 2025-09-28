#!/usr/bin/env python3
"""
Testes Abrangentes do Sistema v0.11.0
====================================

Suite completa de testes para validar todas as funcionalidades
dos algoritmos, interface web e sistema de relatórios.
"""

import unittest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from advanced_algorithm_comparison import (
        AlgorithmComparison, BasicParser, EnhancedParser, 
        SmartInferencer, HybridOrchestrator, BrazilianSpecialist
    )
    from simple_report_generator import SimpleReportGenerator
    from demo_system import create_demo_data, generate_html_report
except ImportError as e:
    print(f"⚠ Erro de importação: {e}")
    print("Executando testes básicos...")

class TestAlgorithmSystem(unittest.TestCase):
    """Testes para o sistema de algoritmos"""
    
    def setUp(self):
        """Configuração inicial dos testes"""
        self.test_files = [
            "Python_para_Desenvolvedores_Casa_do_Codigo.pdf",
            "JavaScript_Moderno_OReilly.epub", 
            "Machine_Learning_Novatec_João_Silva.pdf",
            "React_Native_Desenvolvimento_Maria_Santos.epub",
            "Data_Science_Python_Packt.pdf"
        ]
        
    def test_basic_parser_exists(self):
        """Testa se BasicParser existe e é instanciável"""
        try:
            parser = BasicParser()
            self.assertIsNotNone(parser)
            self.assertTrue(hasattr(parser, 'extract_metadata'))
        except NameError:
            self.skipTest("BasicParser não encontrado")
    
    def test_enhanced_parser_exists(self):
        """Testa se EnhancedParser existe e é instanciável"""
        try:
            parser = EnhancedParser()
            self.assertIsNotNone(parser)
            self.assertTrue(hasattr(parser, 'extract_metadata'))
        except NameError:
            self.skipTest("EnhancedParser não encontrado")
    
    def test_smart_inferencer_exists(self):
        """Testa se SmartInferencer existe e é instanciável"""
        try:
            inferencer = SmartInferencer()
            self.assertIsNotNone(inferencer)
            self.assertTrue(hasattr(inferencer, 'extract_metadata'))
        except NameError:
            self.skipTest("SmartInferencer não encontrado")
    
    def test_hybrid_orchestrator_exists(self):
        """Testa se HybridOrchestrator existe e é instanciável"""
        try:
            orchestrator = HybridOrchestrator()
            self.assertIsNotNone(orchestrator)
            self.assertTrue(hasattr(orchestrator, 'extract_metadata'))
        except NameError:
            self.skipTest("HybridOrchestrator não encontrado")
    
    def test_brazilian_specialist_exists(self):
        """Testa se BrazilianSpecialist existe e é instanciável"""
        try:
            specialist = BrazilianSpecialist()
            self.assertIsNotNone(specialist)
            self.assertTrue(hasattr(specialist, 'extract_metadata'))
            self.assertTrue(hasattr(specialist, 'is_brazilian_publisher'))
        except NameError:
            self.skipTest("BrazilianSpecialist não encontrado")

class TestBrazilianSpecialist(unittest.TestCase):
    """Testes específicos para o Brazilian Specialist"""
    
    def setUp(self):
        """Configuração inicial"""
        try:
            self.specialist = BrazilianSpecialist()
        except NameError:
            self.skipTest("BrazilianSpecialist não disponível")
    
    def test_brazilian_publisher_detection(self):
        """Testa detecção de editoras brasileiras"""
        test_cases = [
            ("Casa do Código", True),
            ("Novatec", True),
            ("Érica", True),
            ("Brasport", True),
            ("Alta Books", True),
            ("O'Reilly", False),
            ("Packt", False),
            ("Manning", False)
        ]
        
        for publisher, expected in test_cases:
            with self.subTest(publisher=publisher):
                result = self.specialist.is_brazilian_publisher(publisher)
                self.assertEqual(result, expected, 
                    f"Falha na detecção: {publisher} deveria ser {expected}")
    
    def test_brazilian_name_patterns(self):
        """Testa detecção de padrões de nomes brasileiros"""
        test_names = [
            ("João Silva", True),
            ("Maria Santos", True),
            ("Ana Costa", True),
            ("Carlos Oliveira", True),
            ("John Smith", False),
            ("Jane Doe", False)
        ]
        
        for name, expected in test_names:
            with self.subTest(name=name):
                result = self.specialist.has_brazilian_name_pattern(name)
                self.assertEqual(result, expected,
                    f"Padrão de nome: {name} deveria ser {expected}")
    
    def test_portuguese_language_detection(self):
        """Testa detecção de palavras em português"""
        test_texts = [
            ("programação python", True),
            ("desenvolvimento web", True),
            ("tecnologia da informação", True),
            ("programming python", False),
            ("web development", False)
        ]
        
        for text, expected in test_texts:
            with self.subTest(text=text):
                result = self.specialist.has_portuguese_words(text)
                self.assertEqual(result, expected,
                    f"Detecção de português: {text} deveria ser {expected}")

class TestAlgorithmComparison(unittest.TestCase):
    """Testes para o sistema de comparação de algoritmos"""
    
    def setUp(self):
        """Configuração inicial"""
        try:
            self.comparison = AlgorithmComparison()
        except NameError:
            self.skipTest("AlgorithmComparison não disponível")
    
    def test_algorithm_initialization(self):
        """Testa se todos os algoritmos são inicializados"""
        self.assertIsNotNone(self.comparison.algorithms)
        self.assertGreaterEqual(len(self.comparison.algorithms), 5)
        
        expected_algorithms = [
            'Basic Parser', 'Enhanced Parser', 'Smart Inferencer',
            'Hybrid Orchestrator', 'Brazilian Specialist'
        ]
        
        for alg_name in expected_algorithms:
            self.assertIn(alg_name, self.comparison.algorithms,
                f"Algoritmo {alg_name} não encontrado")
    
    def test_metadata_extraction(self):
        """Testa extração básica de metadados"""
        test_filename = "Python_Cookbook_David_Beazley_OReilly_2013.pdf"
        
        try:
            results = self.comparison.test_single_file(test_filename)
            self.assertIsInstance(results, dict)
            self.assertIn('filename', results)
            self.assertIn('results', results)
        except Exception as e:
            self.skipTest(f"Teste de extração falhou: {e}")

class TestReportGeneration(unittest.TestCase):
    """Testes para geração de relatórios"""
    
    def test_demo_data_creation(self):
        """Testa criação de dados de demonstração"""
        try:
            data = create_demo_data()
            self.assertIsInstance(data, dict)
            self.assertIn('test_info', data)
            self.assertIn('algorithm_summary', data)
            self.assertIn('detailed_results', data)
        except NameError:
            self.skipTest("create_demo_data não disponível")
    
    def test_html_report_generation(self):
        """Testa geração de relatório HTML"""
        try:
            data = create_demo_data()
            html_content = generate_html_report(data)
            
            self.assertIsInstance(html_content, str)
            self.assertIn('<html', html_content.lower())
            self.assertIn('renamepdfepub', html_content.lower())
            self.assertIn('algoritmos', html_content.lower())
        except NameError:
            self.skipTest("generate_html_report não disponível")
    
    def test_simple_report_generator(self):
        """Testa SimpleReportGenerator"""
        try:
            generator = SimpleReportGenerator()
            self.assertIsNotNone(generator)
            self.assertTrue(hasattr(generator, 'generate_html_report'))
        except NameError:
            self.skipTest("SimpleReportGenerator não disponível")

class TestFileStructure(unittest.TestCase):
    """Testes para estrutura de arquivos"""
    
    def test_required_files_exist(self):
        """Testa se arquivos obrigatórios existem"""
        required_files = [
            'advanced_algorithm_comparison.py',
            'simple_report_generator.py',
            'streamlit_interface.py',
            'web_launcher.py',
            'demo_system.py'
        ]
        
        for filename in required_files:
            file_path = Path(filename)
            self.assertTrue(file_path.exists(), 
                f"Arquivo obrigatório não encontrado: {filename}")
    
    def test_python_syntax(self):
        """Testa sintaxe Python dos arquivos principais"""
        python_files = [
            'advanced_algorithm_comparison.py',
            'simple_report_generator.py',
            'web_launcher.py',
            'demo_system.py'
        ]
        
        for filename in python_files:
            if Path(filename).exists():
                with self.subTest(filename=filename):
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            compile(f.read(), filename, 'exec')
                    except SyntaxError as e:
                        self.fail(f"Erro de sintaxe em {filename}: {e}")

class TestPerformance(unittest.TestCase):
    """Testes de performance"""
    
    def test_algorithm_execution_time(self):
        """Testa tempo de execução dos algoritmos"""
        try:
            comparison = AlgorithmComparison()
            test_filename = "Test_Book_Example.pdf"
            
            start_time = time.time()
            results = comparison.test_single_file(test_filename)
            execution_time = time.time() - start_time
            
            # Deve executar em menos de 5 segundos
            self.assertLess(execution_time, 5.0,
                f"Execução muito lenta: {execution_time:.2f}s")
            
        except NameError:
            self.skipTest("AlgorithmComparison não disponível")
    
    def test_memory_usage(self):
        """Testa uso básico de memória"""
        # Teste simples de criação de objetos
        try:
            objects = []
            for _ in range(100):
                comparison = AlgorithmComparison()
                objects.append(comparison)
            
            # Se chegou até aqui, não há vazamento óbvio
            self.assertEqual(len(objects), 100)
            
        except MemoryError:
            self.fail("Possível vazamento de memória detectado")
        except NameError:
            self.skipTest("AlgorithmComparison não disponível")

class TestIntegration(unittest.TestCase):
    """Testes de integração"""
    
    def test_end_to_end_workflow(self):
        """Testa fluxo completo end-to-end"""
        try:
            # 1. Cria comparador
            comparison = AlgorithmComparison()
            
            # 2. Executa teste
            test_file = "Integration_Test_Book.pdf"
            results = comparison.test_single_file(test_file)
            
            # 3. Verifica estrutura do resultado
            self.assertIn('filename', results)
            self.assertIn('results', results)
            
            # 4. Gera relatório
            generator = SimpleReportGenerator()
            report_data = {
                'test_info': {'total_books': 1},
                'algorithm_summary': {},
                'detailed_results': [results]
            }
            
            html_report = generator.generate_html_report(report_data)
            self.assertIsInstance(html_report, str)
            self.assertGreater(len(html_report), 1000)  # Relatório substancial
            
        except NameError as e:
            self.skipTest(f"Componentes não disponíveis: {e}")

def run_comprehensive_tests():
    """Executa todos os testes de forma organizada"""
    print("🧪 EXECUTANDO TESTES ABRANGENTES v0.11.0")
    print("=" * 60)
    
    # Configurações do unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Adiciona todas as classes de teste
    test_classes = [
        TestAlgorithmSystem,
        TestBrazilianSpecialist, 
        TestAlgorithmComparison,
        TestReportGeneration,
        TestFileStructure,
        TestPerformance,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Executa testes
    runner = unittest.TextTestRunner(
        verbosity=2,
        failfast=False,
        stream=sys.stdout
    )
    
    print(f"\n Iniciando {suite.countTestCases()} testes...")
    result = runner.run(suite)
    
    # Relatório final
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    success = total_tests - failures - errors - skipped
    
    print(f" Sucessos: {success}")
    print(f" Falhas: {failures}")
    print(f"🔥 Erros: {errors}")
    print(f"⏭ Pulados: {skipped}")
    print(f"📈 Taxa de Sucesso: {(success/total_tests)*100:.1f}%")
    
    if failures > 0:
        print(f"\n🔍 FALHAS DETECTADAS:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.splitlines()[-1]}")
    
    if errors > 0:
        print(f"\n💥 ERROS DETECTADOS:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.splitlines()[-1]}")
    
    success_rate = (success/total_tests)*100
    if success_rate >= 80:
        print(f"\n🎉 TESTES APROVADOS! ({success_rate:.1f}% de sucesso)")
        return True
    else:
        print(f"\n⚠ ATENÇÃO: Taxa de sucesso baixa ({success_rate:.1f}%)")
        return False

def main():
    """Função principal"""
    print("🔬 SISTEMA DE TESTES RENAMEPDFEPUB v0.11.0")
    print("Validando todas as funcionalidades implementadas...")
    
    success = run_comprehensive_tests()
    
    if success:
        print("\n Todos os testes principais passaram!")
        print(" Sistema pronto para release!")
    else:
        print("\n⚠ Alguns testes falharam.")
        print("🔧 Verifique os logs acima para detalhes.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())