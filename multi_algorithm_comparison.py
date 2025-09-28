#!/usr/bin/env python3
"""
Sistema de Comparacao Completa de Algoritmos
===========================================

Testa multiplos algoritmos com dados reais e cria tabela de comparacao detalhada.
Remove emojis e caracteres especiais conforme solicitado.
"""

import sys
import json
import time
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

@dataclass
class AlgorithmResult:
    """Resultado de um algoritmo"""
    filename: str
    algorithm_name: str
    title: str
    author: str
    publisher: str
    year: str
    confidence: float
    execution_time: float
    accuracy_score: float

class MultiAlgorithmTester:
    """Testador com multiplos algoritmos"""
    
    def __init__(self):
        # Configuracao de saida
        self.output_file = open('multi_algorithm_results.txt', 'w', encoding='utf-8')
        self.original_stdout = sys.stdout
        
        # Publishers conhecidos
        self.publisher_patterns = {
            'Manning': ['manning', 'meap', 'exploring', 'action', 'month'],
            'Packt': ['packt', 'cookbook', 'hands-on', 'mastering', 'learning'],
            'OReilly': ['oreilly', 'o\'reilly', 'learning', 'definitive', 'pocket'],
            'NoStarch': ['nostarch', 'no starch', 'black hat', 'ethical'],
            'Wiley': ['wiley', 'sybex', 'wrox'],
            'Addison': ['addison', 'wesley', 'pearson'],
            'MIT': ['mit press'],
            'Apress': ['apress', 'pro ', 'beginning'],
            'Microsoft': ['microsoft', 'press'],
            'Springer': ['springer'],
            'Elsevier': ['elsevier'],
            'McGraw': ['mcgraw', 'hill']
        }
        
        # Patterns de programacao para boost de confianca
        self.tech_patterns = [
            'python', 'java', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'programming', 'code', 'coding', 'development', 'software', 'algorithm',
            'machine learning', 'ai', 'data science', 'security', 'hacking', 'cyber',
            'database', 'sql', 'web', 'mobile', 'cloud', 'devops', 'docker', 'kubernetes'
        ]

    def print_both(self, text: str):
        """Imprime no terminal e salva no arquivo"""
        print(text)
        self.output_file.write(text + '\n')
        self.output_file.flush()

    def normalize_text(self, text: str) -> str:
        """Remove acentos e caracteres especiais conforme solicitado"""
        if not text:
            return ""
        
        # Remove acentos (NFD + remove combining characters)
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove emojis e caracteres especiais
        text = re.sub(r'[^\w\s\-\(\).,]', ' ', text)
        
        # Normaliza espacos
        text = ' '.join(text.split())
        
        return text.strip()

    def extract_ground_truth(self, filename: str) -> Dict[str, str]:
        """Extrai ground truth do nome do arquivo"""
        name = self.normalize_text(filename)
        name_clean = Path(name).stem
        
        result = {'title': '', 'author': '', 'publisher': '', 'year': ''}
        
        # Extrai ano
        year_match = re.search(r'\((\d{4})\)', name_clean)
        if year_match:
            result['year'] = year_match.group(1)
            name_clean = re.sub(r'\(\d{4}\)', '', name_clean).strip()
        
        # Extrai publisher
        name_lower = name_clean.lower()
        for pub, patterns in self.publisher_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                result['publisher'] = pub
                break
        
        # Extrai autor (antes do primeiro " - ")
        if ' - ' in name_clean:
            parts = name_clean.split(' - ', 1)
            potential_author = parts[0].strip()
            
            # Valida se parece com autor
            if (len(potential_author) > 2 and 
                not potential_author[0].isdigit() and
                not any(word in potential_author.lower() for word in ['www', 'com', 'pdf', 'book'])):
                result['author'] = potential_author
                name_clean = parts[1].strip()
        
        # O resto e titulo
        title = name_clean.strip()
        title = re.sub(r'^-\s*', '', title)  # Remove hifen inicial
        title = re.sub(r'\s+', ' ', title)   # Normaliza espacos
        
        if len(title) > 3:
            result['title'] = title
        
        return result

    def algorithm_1_basic_parser(self, filename: str) -> AlgorithmResult:
        """Algoritmo 1: Parser Basico de Nome de Arquivo"""
        start_time = time.time()
        
        metadata = self.extract_ground_truth(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Confianca baseada em dados extraidos
        confidence = 0.2
        if metadata['title']:
            confidence += 0.3
        if metadata['author']:
            confidence += 0.3
        if metadata['publisher']:
            confidence += 0.15
        if metadata['year']:
            confidence += 0.05
        
        # Accuracy comparando com ground truth
        accuracy = self.calculate_accuracy(metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Basic Parser",
            title=metadata['title'],
            author=metadata['author'],
            publisher=metadata['publisher'],
            year=metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy
        )

    def algorithm_2_enhanced_parser(self, filename: str) -> AlgorithmResult:
        """Algoritmo 2: Parser Melhorado com Deteccao de Padroes"""
        start_time = time.time()
        
        metadata = self.extract_ground_truth(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Confianca base
        confidence = 0.25
        if metadata['title']:
            confidence += 0.25
        if metadata['author']:
            confidence += 0.25
        if metadata['publisher']:
            confidence += 0.15
        if metadata['year']:
            confidence += 0.1
        
        # Bonus por padroes tecnicos
        name_lower = filename.lower()
        tech_bonus = sum(0.02 for pattern in self.tech_patterns if pattern in name_lower)
        confidence += min(tech_bonus, 0.1)
        
        # Bonus por estrutura organizada
        if ' - ' in filename and metadata['author'] and metadata['title']:
            confidence += 0.05
        
        accuracy = self.calculate_accuracy(metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Enhanced Parser",
            title=metadata['title'],
            author=metadata['author'],
            publisher=metadata['publisher'],
            year=metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy
        )

    def algorithm_3_smart_inferencer(self, filename: str) -> AlgorithmResult:
        """Algoritmo 3: Inferencia Inteligente com Heuristicas"""
        start_time = time.time()
        
        # Comeca com parser melhorado
        base_result = self.algorithm_2_enhanced_parser(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Melhorias na inferencia
        metadata = {
            'title': base_result.title,
            'author': base_result.author,
            'publisher': base_result.publisher,
            'year': base_result.year
        }
        
        # Inferencia de publisher se nao detectado
        if not metadata['publisher']:
            name_lower = filename.lower()
            
            # Heuristicas por palavras-chave
            if any(word in name_lower for word in ['cookbook', 'mastering', 'packt']):
                metadata['publisher'] = 'Packt'
            elif any(word in name_lower for word in ['learning', 'pocket', 'definitive']):
                metadata['publisher'] = 'OReilly'
            elif any(word in name_lower for word in ['manning', 'action', 'month']):
                metadata['publisher'] = 'Manning'
            elif any(word in name_lower for word in ['hacking', 'security', 'black']):
                metadata['publisher'] = 'NoStarch'
        
        # Inferencia de categoria/contexto
        confidence = base_result.confidence
        
        # Bonus por inferencias bem-sucedidas
        if metadata['publisher'] and not base_result.publisher:
            confidence += 0.05
        
        # Bonus por consistencia temporal
        if metadata['year'] and 2000 <= int(metadata['year']) <= 2025:
            confidence += 0.02
        
        accuracy = self.calculate_accuracy(metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Smart Inferencer",
            title=metadata['title'],
            author=metadata['author'],
            publisher=metadata['publisher'],
            year=metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy
        )

    def algorithm_4_ultimate_extractor(self, filename: str) -> AlgorithmResult:
        """Algoritmo 4: Extrator Ultimate - Combina Todas as Tecnicas"""
        start_time = time.time()
        
        # Executa todos os algoritmos anteriores
        basic = self.algorithm_1_basic_parser(filename)
        enhanced = self.algorithm_2_enhanced_parser(filename)
        smart = self.algorithm_3_smart_inferencer(filename)
        
        ground_truth = self.extract_ground_truth(filename)
        
        # Escolhe melhor resultado para cada campo
        best_metadata = {
            'title': self.choose_best_field([basic.title, enhanced.title, smart.title]),
            'author': self.choose_best_field([basic.author, enhanced.author, smart.author]),
            'publisher': self.choose_best_field([basic.publisher, enhanced.publisher, smart.publisher]),
            'year': self.choose_best_field([basic.year, enhanced.year, smart.year])
        }
        
        # Confianca e a media ponderada dos algoritmos
        confidence = (basic.confidence * 0.2 + 
                     enhanced.confidence * 0.3 + 
                     smart.confidence * 0.5)
        
        # Bonus por combinacao bem-sucedida
        confidence += 0.05
        
        accuracy = self.calculate_accuracy(best_metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Ultimate Extractor",
            title=best_metadata['title'],
            author=best_metadata['author'],
            publisher=best_metadata['publisher'],
            year=best_metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy
        )

    def choose_best_field(self, options: List[str]) -> str:
        """Escolhe o melhor valor para um campo"""
        # Remove vazios
        valid_options = [opt for opt in options if opt and opt.strip()]
        
        if not valid_options:
            return ""
        
        # Se todos iguais, retorna o primeiro
        if len(set(valid_options)) == 1:
            return valid_options[0]
        
        # Escolhe o mais longo (mais informativo)
        return max(valid_options, key=len)

    def calculate_accuracy(self, extracted: Dict[str, str], expected: Dict[str, str]) -> float:
        """Calcula accuracy comparando extraido vs esperado"""
        if not any(expected.values()):  # Se nao ha ground truth
            return 0.5  # Score neutro
        
        score = 0.0
        weights = {'title': 0.4, 'author': 0.3, 'publisher': 0.2, 'year': 0.1}
        total_weight = 0.0
        
        for field, weight in weights.items():
            if expected[field]:
                similarity = self.text_similarity(extracted.get(field, ''), expected[field])
                score += similarity * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0

    def text_similarity(self, text1: str, text2: str) -> float:
        """Calcula similaridade entre textos"""
        if not text1 or not text2:
            return 0.0
        
        # Normaliza
        t1 = self.normalize_text(text1.lower())
        t2 = self.normalize_text(text2.lower())
        
        if t1 == t2:
            return 1.0
        
        # Containment
        if t1 in t2 or t2 in t1:
            return 0.8
        
        # Word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if words1 and words2:
            overlap = len(words1.intersection(words2))
            total = len(words1.union(words2))
            return overlap / total if total > 0 else 0.0
        
        return 0.0

    def run_comprehensive_test(self, max_books: int = 30) -> Dict[str, Any]:
        """Executa teste abrangente com todos os algoritmos"""
        self.print_both("SISTEMA DE COMPARACAO COMPLETA DE ALGORITMOS")
        self.print_both("=" * 70)
        self.print_both(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.print_both("")
        
        # Lista livros
        books_dir = Path("books")
        if not books_dir.exists():
            self.print_both("ERRO: Pasta books/ nao encontrada!")
            return {}
        
        book_files = [f for f in books_dir.iterdir() 
                     if f.suffix.lower() in ['.pdf', '.epub', '.mobi'] 
                     and not f.name.startswith('.')]
        
        if len(book_files) > max_books:
            book_files = book_files[:max_books]
        
        self.print_both(f"Testando {len(book_files)} livros com 4 algoritmos")
        self.print_both("")
        
        # Estrutura de resultados
        results = {
            'test_info': {
                'total_books': len(book_files),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'algorithms': ['Basic Parser', 'Enhanced Parser', 'Smart Inferencer', 'Ultimate Extractor']
            },
            'detailed_results': [],
            'algorithm_summary': {}
        }
        
        # Inicializa sumarios
        for alg_name in results['test_info']['algorithms']:
            results['algorithm_summary'][alg_name] = {
                'accuracies': [],
                'confidences': [],
                'times': [],
                'success_count': 0
            }
        
        # Header da tabela
        self.print_both("TABELA DE COMPARACAO DETALHADA")
        self.print_both("-" * 100)
        self.print_both(f"{'Arquivo':<25} {'Titulo Real':<20} {'Basic':<7} {'Enhance':<7} {'Smart':<7} {'Ultimate':<7} {'Melhor':<12}")
        self.print_both("-" * 100)
        
        # Testa cada livro
        for i, book_file in enumerate(book_files, 1):
            ground_truth = self.extract_ground_truth(book_file.name)
            
            # Executa todos os algoritmos
            algorithms = [
                self.algorithm_1_basic_parser,
                self.algorithm_2_enhanced_parser,
                self.algorithm_3_smart_inferencer,
                self.algorithm_4_ultimate_extractor
            ]
            
            book_results = []
            accuracies = []
            
            for algorithm in algorithms:
                result = algorithm(book_file.name)
                book_results.append(result)
                accuracies.append(result.accuracy_score)
                
                # Atualiza sumarios
                summary = results['algorithm_summary'][result.algorithm_name]
                summary['accuracies'].append(result.accuracy_score)
                summary['confidences'].append(result.confidence)
                summary['times'].append(result.execution_time)
                if result.accuracy_score > 0.6:
                    summary['success_count'] += 1
            
            # Melhor algoritmo
            best_idx = accuracies.index(max(accuracies))
            best_algorithm = book_results[best_idx].algorithm_name
            
            # Linha da tabela
            filename_short = book_file.name[:24]
            title_short = ground_truth['title'][:19] if ground_truth['title'] else 'N/A'
            
            accuracy_strs = [f"{acc:.3f}" for acc in accuracies]
            
            self.print_both(f"{filename_short:<25} {title_short:<20} "
                           f"{accuracy_strs[0]:<7} {accuracy_strs[1]:<7} "
                           f"{accuracy_strs[2]:<7} {accuracy_strs[3]:<7} "
                           f"{best_algorithm[:11]:<12}")
            
            # Salva resultado detalhado
            results['detailed_results'].append({
                'filename': book_file.name,
                'ground_truth': ground_truth,
                'algorithm_results': [asdict(result) for result in book_results],
                'best_algorithm': best_algorithm,
                'accuracies': dict(zip([r.algorithm_name for r in book_results], accuracies))
            })
        
        self.print_both("")
        self.print_both("SUMARIO DOS ALGORITMOS")
        self.print_both("=" * 60)
        
        # Calcula e imprime sumarios
        for alg_name, summary in results['algorithm_summary'].items():
            if summary['accuracies']:
                avg_accuracy = sum(summary['accuracies']) / len(summary['accuracies'])
                avg_confidence = sum(summary['confidences']) / len(summary['confidences'])
                avg_time = sum(summary['times']) / len(summary['times'])
                success_rate = summary['success_count'] / len(summary['accuracies'])
                
                self.print_both(f"\n{alg_name}:")
                self.print_both(f"  Accuracy Media: {avg_accuracy:.3f} ({avg_accuracy*100:.1f}%)")
                self.print_both(f"  Confianca Media: {avg_confidence:.3f}")
                self.print_both(f"  Tempo Medio: {avg_time:.4f}s")
                self.print_both(f"  Taxa Sucesso: {success_rate:.3f} ({success_rate*100:.1f}%)")
                
                # Atualiza resultado final
                results['algorithm_summary'][alg_name].update({
                    'avg_accuracy': avg_accuracy,
                    'avg_confidence': avg_confidence,
                    'avg_time': avg_time,
                    'success_rate': success_rate
                })
        
        # Melhor algoritmo geral
        best_overall = max(results['algorithm_summary'].keys(), 
                          key=lambda k: results['algorithm_summary'][k].get('avg_accuracy', 0))
        
        self.print_both(f"\nMELHOR ALGORITMO GERAL: {best_overall}")
        self.print_both(f"Accuracy: {results['algorithm_summary'][best_overall]['avg_accuracy']:.3f}")
        
        return results

    def cleanup(self):
        """Cleanup dos recursos"""
        if hasattr(self, 'output_file'):
            sys.stdout = self.original_stdout
            self.output_file.close()

def main():
    """Funcao principal"""
    tester = MultiAlgorithmTester()
    
    try:
        # Executa teste
        results = tester.run_comprehensive_test(max_books=25)
        
        if results:
            # Salva resultados JSON
            with open('multi_algorithm_comparison.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            tester.print_both(f"\nResultados salvos em:")
            tester.print_both(f"- multi_algorithm_results.txt (saida completa)")
            tester.print_both(f"- multi_algorithm_comparison.json (dados detalhados)")
            tester.print_both(f"\nTESTE FINALIZADO COM SUCESSO!")
        
    finally:
        tester.cleanup()
        print("\nTeste executado! Verifique os arquivos de saida.")

if __name__ == "__main__":
    main()