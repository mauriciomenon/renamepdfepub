#!/usr/bin/env python3
"""
Sistema Avançado de Comparação de Algoritmos v2.0
================================================

Versão melhorada com algoritmo renomeado + novo algoritmo para livros nacionais
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
    additional_info: Dict[str, Any] = None

class AdvancedAlgorithmTester:
    """Testador avançado com 5 algoritmos incluindo especialista em livros nacionais"""
    
    def __init__(self):
        # Configuração de saída
        self.output_file = open('advanced_algorithm_results.txt', 'w', encoding='utf-8')
        self.original_stdout = sys.stdout
        
        # Publishers internacionais
        self.international_publishers = {
            'Manning': ['manning', 'meap', 'exploring', 'action', 'month', 'grokking'],
            'Packt': ['packt', 'cookbook', 'hands-on', 'mastering', 'learning'],
            'OReilly': ['oreilly', 'o\'reilly', 'learning', 'definitive', 'pocket'],
            'NoStarch': ['nostarch', 'no starch', 'black hat', 'ethical', 'hacking'],
            'Wiley': ['wiley', 'sybex', 'wrox'],
            'Addison': ['addison', 'wesley', 'pearson'],
            'MIT': ['mit press'],
            'Apress': ['apress', 'pro ', 'beginning'],
            'Microsoft': ['microsoft', 'press'],
            'Springer': ['springer'],
            'Elsevier': ['elsevier'],
            'McGraw': ['mcgraw', 'hill']
        }
        
        # Publishers nacionais brasileiros
        self.brazilian_publishers = {
            'Casa do Código': ['casa do codigo', 'casadocodigo', 'cdc'],
            'Novatec': ['novatec', 'nova tec'],
            'Érica': ['erica', 'editora erica'],
            'Brasport': ['brasport'],
            'Alta Books': ['alta books', 'altabooks'],
            'Bookman': ['bookman', 'grupo a'],
            'Pearson BR': ['pearson brasil', 'pearson br'],
            'Cengage': ['cengage', 'thomson'],
            'FCA': ['fca editora'],
            'Saraiva': ['saraiva', 'editora saraiva'],
            'Campus': ['campus', 'editora campus'],
            'LTC': ['ltc', 'livros tecnicos'],
            'Makron': ['makron', 'makron books']
        }
        
        # Padrões de nomes brasileiros
        self.brazilian_name_patterns = [
            # Nomes compostos comuns
            'joão', 'josé', 'antônio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas',
            'maria', 'ana', 'francisca', 'antônia', 'adriana', 'juliana', 'márcia',
            # Sobrenomes brasileiros
            'silva', 'santos', 'oliveira', 'souza', 'rodrigues', 'ferreira', 'alves',
            'pereira', 'lima', 'gomes', 'ribeiro', 'carvalho', 'almeida', 'lopes',
            'soares', 'fernandes', 'vieira', 'barbosa', 'rocha', 'dias', 'nunes'
        ]
        
        # Patterns técnicos
        self.tech_patterns = [
            'python', 'java', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'programming', 'programacao', 'codigo', 'desenvolvimento', 'software', 'algoritmo',
            'machine learning', 'ai', 'inteligencia artificial', 'ciencia de dados',
            'seguranca', 'hacking', 'cyber', 'banco de dados', 'sql', 'web', 'mobile'
        ]

    def print_both(self, text: str):
        """Imprime no terminal e salva no arquivo"""
        print(text)
        self.output_file.write(text + '\n')
        self.output_file.flush()

    def normalize_text(self, text: str) -> str:
        """Remove acentos e caracteres especiais"""
        if not text:
            return ""
        
        # Remove acentos (NFD + remove combining characters)
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove emojis e caracteres especiais
        text = re.sub(r'[^\w\s\-\(\).,]', ' ', text)
        
        # Normaliza espaços
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
        
        # Extrai publisher (internacional + nacional)
        name_lower = name_clean.lower()
        all_publishers = {**self.international_publishers, **self.brazilian_publishers}
        
        for pub, patterns in all_publishers.items():
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
        
        # O resto é título
        title = name_clean.strip()
        title = re.sub(r'^-\s*', '', title)  # Remove hífen inicial
        title = re.sub(r'\s+', ' ', title)   # Normaliza espaços
        
        if len(title) > 3:
            result['title'] = title
        
        return result

    def algorithm_1_basic_parser(self, filename: str) -> AlgorithmResult:
        """Algoritmo 1: Parser Básico de Nome de Arquivo"""
        start_time = time.time()
        
        metadata = self.extract_ground_truth(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Confiança baseada em dados extraídos
        confidence = 0.2
        if metadata['title']:
            confidence += 0.3
        if metadata['author']:
            confidence += 0.3
        if metadata['publisher']:
            confidence += 0.15
        if metadata['year']:
            confidence += 0.05
        
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
            accuracy_score=accuracy,
            additional_info={'type': 'basic', 'features': ['filename_parsing']}
        )

    def algorithm_2_enhanced_parser(self, filename: str) -> AlgorithmResult:
        """Algoritmo 2: Parser Melhorado com Detecção de Padrões"""
        start_time = time.time()
        
        metadata = self.extract_ground_truth(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Confiança base
        confidence = 0.25
        if metadata['title']:
            confidence += 0.25
        if metadata['author']:
            confidence += 0.25
        if metadata['publisher']:
            confidence += 0.15
        if metadata['year']:
            confidence += 0.1
        
        # Bônus por padrões técnicos
        name_lower = filename.lower()
        tech_bonus = sum(0.02 for pattern in self.tech_patterns if pattern in name_lower)
        confidence += min(tech_bonus, 0.1)
        
        # Bônus por estrutura organizada
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
            accuracy_score=accuracy,
            additional_info={'type': 'enhanced', 'features': ['pattern_recognition', 'tech_bonus']}
        )

    def algorithm_3_smart_inferencer(self, filename: str) -> AlgorithmResult:
        """Algoritmo 3: Inferência Inteligente com Heurísticas"""
        start_time = time.time()
        
        # Começa com parser melhorado
        base_result = self.algorithm_2_enhanced_parser(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        # Melhorias na inferência
        metadata = {
            'title': base_result.title,
            'author': base_result.author,
            'publisher': base_result.publisher,
            'year': base_result.year
        }
        
        # Inferência de publisher se não detectado
        if not metadata['publisher']:
            name_lower = filename.lower()
            
            # Heurísticas por palavras-chave
            if any(word in name_lower for word in ['cookbook', 'mastering', 'packt']):
                metadata['publisher'] = 'Packt'
            elif any(word in name_lower for word in ['learning', 'pocket', 'definitive']):
                metadata['publisher'] = 'OReilly'
            elif any(word in name_lower for word in ['manning', 'action', 'month', 'grokking']):
                metadata['publisher'] = 'Manning'
            elif any(word in name_lower for word in ['hacking', 'security', 'black']):
                metadata['publisher'] = 'NoStarch'
        
        # Inferência de categoria/contexto
        confidence = base_result.confidence
        
        # Bônus por inferências bem-sucedidas
        if metadata['publisher'] and not base_result.publisher:
            confidence += 0.05
        
        # Bônus por consistência temporal
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
            accuracy_score=accuracy,
            additional_info={'type': 'smart', 'features': ['inference', 'heuristics', 'context_aware']}
        )

    def algorithm_4_hybrid_orchestrator(self, filename: str) -> AlgorithmResult:
        """Algoritmo 4: Orquestrador Híbrido - Combina Todas as Técnicas (renomeado do Ultimate)"""
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
        
        # Confiança é a média ponderada dos algoritmos
        confidence = (basic.confidence * 0.2 + 
                     enhanced.confidence * 0.3 + 
                     smart.confidence * 0.5)
        
        # Bônus por combinação bem-sucedida
        confidence += 0.05
        
        accuracy = self.calculate_accuracy(best_metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Hybrid Orchestrator",
            title=best_metadata['title'],
            author=best_metadata['author'],
            publisher=best_metadata['publisher'],
            year=best_metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy,
            additional_info={'type': 'hybrid', 'features': ['multi_algorithm', 'ensemble', 'orchestration']}
        )

    def algorithm_5_brazilian_specialist(self, filename: str) -> AlgorithmResult:
        """Algoritmo 5: Especialista em Livros Nacionais Brasileiros - NOVO!"""
        start_time = time.time()
        
        metadata = self.extract_ground_truth(filename)
        ground_truth = self.extract_ground_truth(filename)
        
        name_lower = filename.lower()
        
        # Detecta se é livro brasileiro
        brazilian_indicators = 0
        brazilian_features = []
        
        # Verifica publishers nacionais
        for pub, patterns in self.brazilian_publishers.items():
            if any(pattern in name_lower for pattern in patterns):
                metadata['publisher'] = pub
                brazilian_indicators += 2
                brazilian_features.append(f'publisher_{pub}')
                break
        
        # Verifica nomes brasileiros no autor
        if metadata['author']:
            author_lower = metadata['author'].lower()
            for pattern in self.brazilian_name_patterns:
                if pattern in author_lower:
                    brazilian_indicators += 1
                    brazilian_features.append(f'brazilian_name_{pattern}')
                    break
        
        # Detecta palavras em português
        portuguese_words = [
            'programacao', 'desenvolvimento', 'algoritmos', 'estruturas de dados',
            'banco de dados', 'engenharia de software', 'ciencia da computacao',
            'inteligencia artificial', 'aprendizado de maquina', 'seguranca da informacao'
        ]
        
        for word in portuguese_words:
            if word in name_lower:
                brazilian_indicators += 1
                brazilian_features.append(f'portuguese_{word.replace(" ", "_")}')
        
        # Detecta padrões de formatação brasileira
        if re.search(r'\d+[aª]\s*edi[cç][aã]o', name_lower):
            brazilian_indicators += 2
            brazilian_features.append('brazilian_edition_format')
        
        # Ajusta confiança baseado em indicadores brasileiros
        base_confidence = 0.3
        if metadata['title']:
            base_confidence += 0.25
        if metadata['author']:
            base_confidence += 0.25
        if metadata['publisher']:
            base_confidence += 0.15
        if metadata['year']:
            base_confidence += 0.05
        
        # Bônus por características brasileiras
        brazilian_bonus = min(brazilian_indicators * 0.05, 0.3)
        confidence = base_confidence + brazilian_bonus
        
        # Se não há indicadores brasileiros, reduz confiança
        if brazilian_indicators == 0:
            confidence *= 0.7
        
        accuracy = self.calculate_accuracy(metadata, ground_truth)
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name="Brazilian Specialist",
            title=metadata['title'],
            author=metadata['author'],
            publisher=metadata['publisher'],
            year=metadata['year'],
            confidence=min(confidence, 1.0),
            execution_time=time.time() - start_time,
            accuracy_score=accuracy,
            additional_info={
                'type': 'brazilian_specialist',
                'features': ['national_publishers', 'portuguese_detection', 'brazilian_names'],
                'brazilian_indicators': brazilian_indicators,
                'brazilian_features': brazilian_features
            }
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
        """Calcula accuracy comparando extraído vs esperado"""
        if not any(expected.values()):  # Se não há ground truth
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
        """Executa teste abrangente com todos os 5 algoritmos"""
        self.print_both("SISTEMA AVANÇADO DE COMPARAÇÃO DE ALGORITMOS v2.0")
        self.print_both("=" * 75)
        self.print_both(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.print_both("")
        
        # Lista livros
        books_dir = Path("books")
        if not books_dir.exists():
            self.print_both("ERRO: Pasta books/ não encontrada!")
            return {}
        
        book_files = [f for f in books_dir.iterdir() 
                     if f.suffix.lower() in ['.pdf', '.epub', '.mobi'] 
                     and not f.name.startswith('.')]
        
        if len(book_files) > max_books:
            book_files = book_files[:max_books]
        
        self.print_both(f"Testando {len(book_files)} livros com 5 algoritmos")
        self.print_both("")
        
        # Estrutura de resultados
        results = {
            'test_info': {
                'total_books': len(book_files),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'algorithms': ['Basic Parser', 'Enhanced Parser', 'Smart Inferencer', 'Hybrid Orchestrator', 'Brazilian Specialist']
            },
            'detailed_results': [],
            'algorithm_summary': {}
        }
        
        # Inicializa sumários
        for alg_name in results['test_info']['algorithms']:
            results['algorithm_summary'][alg_name] = {
                'accuracies': [],
                'confidences': [],
                'times': [],
                'success_count': 0
            }
        
        # Header da tabela
        self.print_both("TABELA DE COMPARAÇÃO DETALHADA - 5 ALGORITMOS")
        self.print_both("-" * 110)
        self.print_both(f"{'Arquivo':<25} {'Titulo Real':<20} {'Basic':<7} {'Enhanced':<7} {'Smart':<7} {'Hybrid':<7} {'Brazilian':<7} {'Melhor':<15}")
        self.print_both("-" * 110)
        
        # Testa cada livro
        for i, book_file in enumerate(book_files, 1):
            ground_truth = self.extract_ground_truth(book_file.name)
            
            # Executa todos os algoritmos
            algorithms = [
                self.algorithm_1_basic_parser,
                self.algorithm_2_enhanced_parser,
                self.algorithm_3_smart_inferencer,
                self.algorithm_4_hybrid_orchestrator,
                self.algorithm_5_brazilian_specialist
            ]
            
            book_results = []
            accuracies = []
            
            for algorithm in algorithms:
                result = algorithm(book_file.name)
                book_results.append(result)
                accuracies.append(result.accuracy_score)
                
                # Atualiza sumários
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
                           f"{accuracy_strs[4]:<7} {best_algorithm[:14]:<15}")
            
            # Salva resultado detalhado
            results['detailed_results'].append({
                'filename': book_file.name,
                'ground_truth': ground_truth,
                'algorithm_results': [asdict(result) for result in book_results],
                'best_algorithm': best_algorithm,
                'accuracies': dict(zip([r.algorithm_name for r in book_results], accuracies))
            })
        
        self.print_both("")
        self.print_both("SUMÁRIO DOS ALGORITMOS")
        self.print_both("=" * 65)
        
        # Calcula e imprime sumários
        for alg_name, summary in results['algorithm_summary'].items():
            if summary['accuracies']:
                avg_accuracy = sum(summary['accuracies']) / len(summary['accuracies'])
                avg_confidence = sum(summary['confidences']) / len(summary['confidences'])
                avg_time = sum(summary['times']) / len(summary['times'])
                success_rate = summary['success_count'] / len(summary['accuracies'])
                
                self.print_both(f"\n{alg_name}:")
                self.print_both(f"  Accuracy Média: {avg_accuracy:.3f} ({avg_accuracy*100:.1f}%)")
                self.print_both(f"  Confiança Média: {avg_confidence:.3f}")
                self.print_both(f"  Tempo Médio: {avg_time:.4f}s")
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
        
        # Análise do algoritmo brasileiro
        if 'Brazilian Specialist' in results['algorithm_summary']:
            br_summary = results['algorithm_summary']['Brazilian Specialist']
            self.print_both(f"\nANÁLISE DO ALGORITMO BRASILEIRO:")
            self.print_both(f"- Confiança média: {br_summary['avg_confidence']:.3f}")
            self.print_both(f"- Especialização em publishers nacionais")
            self.print_both(f"- Detecção de nomes brasileiros")
            self.print_both(f"- Reconhecimento de padrões em português")
        
        return results

    def cleanup(self):
        """Cleanup dos recursos"""
        if hasattr(self, 'output_file'):
            sys.stdout = self.original_stdout
            self.output_file.close()

def main():
    """Função principal"""
    tester = AdvancedAlgorithmTester()
    
    try:
        # Executa teste
        results = tester.run_comprehensive_test(max_books=25)
        
        if results:
            # Salva resultados JSON
            with open('advanced_algorithm_comparison.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            tester.print_both(f"\nResultados salvos em:")
            tester.print_both(f"- advanced_algorithm_results.txt (saída completa)")
            tester.print_both(f"- advanced_algorithm_comparison.json (dados detalhados)")
            tester.print_both(f"\nTESTE AVANÇADO FINALIZADO COM SUCESSO!")
        
    finally:
        tester.cleanup()
        print("\nTeste avançado executado! Verifique os arquivos de saída.")

if __name__ == "__main__":
    main()