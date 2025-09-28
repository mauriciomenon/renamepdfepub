#!/usr/bin/env python3
"""
Algoritmos V3 - Correções Críticas
==================================

Versão V3 focada em corrigir os problemas identificados:
1. Author extraction (0% → target 40%+)
2. Year extraction (0% → target 30%+)  
3. Semantic algorithm (39.7% → target 60%+)
4. Publisher detection (11.2% → target 25%+)
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class AdvancedMetadataExtractor:
    """Extrator V3 com foco em author/year detection"""
    
    def __init__(self):
        # Patterns de autores expandidos e melhorados
        self.advanced_author_patterns = [
            # Padrão "by Author Name"
            r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[|,|-)',
            # Padrão "Author Name presents"
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+presents\b',
            # Padrão "Author Name -"
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*-\s*(?!.*\d{4})',
            # Padrão "with Author Name"
            r'\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[)',
            # Padrão no início do nome
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:\s*-|\s*\(|\s*\[)',
            # Padrão após vírgula
            r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[)',
            # Padrão "Author:" ou "Author -"
            r'(?:Author|Written|Created)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        
        # Patterns de anos expandidos
        self.advanced_year_patterns = [
            # Anos básicos
            r'\b(20[0-2]\d)\b',  # 2000-2029
            r'\b(19[89]\d)\b',   # 1980-1999
            # Anos em contexto
            r'Edition[\s\-_]*(\d{4})',
            r'(\d{4})[\s\-_]*Edition',
            r'Copyright[\s\-_]*(\d{4})',
            r'Published[\s\-_]*(\d{4})',
            r'Release[\s\-_]*(\d{4})',
            r'(\d{4})[\s\-_]*Release',
            # Padrões específicos observados
            r'v\d+[\s\-_]*(\d{4})',
            r'(\d{4})[\s\-_]*v\d+',
        ]
        
        # Publishers expandidos com mais padrões
        self.enhanced_publisher_patterns = {
            'Manning': [
                r'\bmanning\b', r'\bmeap\b', r'month.*lunches', r'exploring',
                r'in\s+action', r'quick\s+start', r'microservices'
            ],
            'Packt': [
                r'\bpackt\b', r'cookbook', r'hands[\s\-]on', r'mastering',
                r'learning.*path', r'practical'
            ],
            'NoStarch': [
                r'no\s*starch', r'black\s*hat', r'ethical\s*hacking',
                r'penetration', r'hacking', r'security'
            ],
            'OReilly': [
                r'o\'?reilly', r'learning', r'definitive\s+guide',
                r'pocket\s+reference', r'animal\s+book'
            ],
            'Wiley': [
                r'\bwiley\b', r'\bsybex\b', r'professional',
                r'certification', r'exam\s+guide'
            ],
            'Addison': [
                r'addison', r'wesley', r'pearson'
            ],
            'Pragmatic': [
                r'pragmatic', r'programmer', r'bookshelf'
            ],
            'MIT': [r'mit\s*press'],
            'Cambridge': [r'cambridge\s*university'],
            'Apress': [r'\bapress\b', r'definitive\s+guide'],
            'Syngress': [r'\bsyngress\b'],
            'Microsoft': [r'\bmicrosoft\b', r'\bms\b', r'azure'],
            'IBM': [r'\bibm\b', r'redbooks'],
            'Cisco': [r'\bcisco\b', r'networking']
        }
        
        # Categorias super expandidas
        self.super_categories = {
            'Programming': [
                'python', 'java', 'javascript', 'js', 'typescript', 'react', 'vue', 'angular',
                'programming', 'code', 'coding', 'development', 'dev', 'software',
                'algorithm', 'algorithms', 'data structures', 'functional', 'oop',
                'object oriented', 'design patterns', 'clean code', 'refactoring',
                'c++', 'cpp', 'c#', 'csharp', 'golang', 'go', 'rust', 'kotlin',
                'swift', 'php', 'ruby', 'perl', 'scala', 'clojure', 'haskell'
            ],
            'Security': [
                'security', 'hacking', 'hack', 'cyber', 'cybersecurity',
                'malware', 'forensics', 'forensic', 'penetration', 'pentest',
                'ethical', 'bug bounty', 'vulnerability', 'exploitation',
                'incident', 'analysis', 'investigation', 'cryptography',
                'encryption', 'privacy', 'authentication', 'authorization',
                'firewall', 'intrusion', 'detection', 'threat'
            ],
            'Database': [
                'database', 'db', 'sql', 'mysql', 'postgresql', 'postgres',
                'mongo', 'mongodb', 'redis', 'cassandra', 'data',
                'analytics', 'analysis', 'warehouse', 'engineering',
                'oracle', 'sqlite', 'mariadb', 'nosql', 'big data',
                'hadoop', 'spark', 'kafka', 'elasticsearch'
            ],
            'AI_ML': [
                'machine learning', 'ml', 'ai', 'artificial intelligence',
                'data science', 'deep learning', 'neural', 'tensorflow',
                'pytorch', 'scikit', 'pandas', 'numpy', 'statistics',
                'computer vision', 'nlp', 'natural language', 'chatbot',
                'recommendation', 'clustering', 'classification', 'regression'
            ],
            'Web': [
                'web', 'website', 'html', 'css', 'frontend', 'backend',
                'full stack', 'fullstack', 'responsive', 'ui', 'ux',
                'design', 'user experience', 'bootstrap', 'jquery',
                'ajax', 'api', 'rest', 'graphql', 'http', 'https'
            ],
            'DevOps': [
                'devops', 'docker', 'kubernetes', 'k8s', 'cloud',
                'aws', 'azure', 'gcp', 'infrastructure', 'deployment',
                'automation', 'ci/cd', 'continuous integration',
                'jenkins', 'ansible', 'terraform', 'vagrant', 'puppet'
            ],
            'Mobile': [
                'mobile', 'android', 'ios', 'app', 'application',
                'swift', 'kotlin', 'react native', 'flutter',
                'xamarin', 'cordova', 'phonegap'
            ],
            'Systems': [
                'linux', 'windows', 'unix', 'system', 'systems',
                'network', 'networking', 'server', 'administration',
                'bash', 'shell', 'powershell', 'ubuntu', 'debian',
                'centos', 'redhat', 'sysadmin'
            ],
            'Cloud': [
                'cloud', 'aws', 'amazon web services', 'azure', 'gcp',
                'google cloud', 'serverless', 'lambda', 'ec2', 's3',
                'kubernetes', 'docker', 'containers', 'microservices'
            ]
        }
        
    def extract_v3_metadata(self, filename: str) -> Dict[str, Any]:
        """Extração V3 com melhorias críticas"""
        
        metadata = {
            'filename': filename,
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'edition': '',
            'version': '',
            'category': '',
            'subcategory': '',
            'keywords': [],
            'language': 'English',
            'confidence': 0.0,
            'extraction_details': {}
        }
        
        # Limpeza avançada
        clean_name = self._super_clean(filename)
        metadata['extraction_details']['original'] = filename
        metadata['extraction_details']['cleaned'] = clean_name
        
        # Extrações V3
        metadata['title'] = self._extract_v3_title(clean_name)
        metadata['author'] = self._extract_v3_author(clean_name)  # FOCO CRÍTICO
        metadata['publisher'] = self._detect_v3_publisher(clean_name)  # MELHORADO
        metadata['year'] = self._extract_v3_year(clean_name)  # FOCO CRÍTICO
        metadata['edition'] = self._extract_v3_edition(clean_name)
        metadata['version'] = self._extract_v3_version(clean_name)
        metadata['category'] = self._detect_v3_category(clean_name)
        metadata['subcategory'] = self._detect_v3_subcategory(clean_name, metadata['category'])
        metadata['keywords'] = self._extract_v3_keywords(clean_name)
        metadata['language'] = self._detect_v3_language(clean_name)
        
        # Confiança V3
        metadata['confidence'] = self._calculate_v3_confidence(metadata)
        
        return metadata
    
    def _super_clean(self, filename: str) -> str:
        """Limpeza super avançada mantendo informações de autor/ano"""
        name = Path(filename).stem
        
        # Preservar informações importantes antes da limpeza
        potential_authors = []
        potential_years = []
        
        # Capturar possíveis autores antes da limpeza
        for pattern in self.advanced_author_patterns:
            matches = re.findall(pattern, name, re.IGNORECASE)
            potential_authors.extend(matches)
        
        # Capturar possíveis anos antes da limpeza
        for pattern in self.advanced_year_patterns:
            matches = re.findall(pattern, name, re.IGNORECASE)
            potential_years.extend(matches)
        
        # Limpeza padrão
        extensions = ['.pdf', '.epub', '.mobi', '.azw3', '.txt']
        for ext in extensions:
            while name.lower().endswith(ext):
                name = name[:-len(ext)]
        
        # Padrões específicos
        name = re.sub(r'_v\d+_MEAP', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_V\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_MEAP\d*', '', name, flags=re.IGNORECASE)
        
        # Preservar estrutura de autor/ano onde possível
        name = name.replace('_', ' ').replace('-', ' ')
        name = re.sub(r'\s+', ' ', name)
        name = name.strip()
        
        # Armazenar informações capturadas para uso posterior
        self._temp_authors = potential_authors
        self._temp_years = potential_years
        
        return name
    
    def _extract_v3_author(self, text: str) -> str:
        """Extração de autor V3 - CRÍTICA"""
        # Primeiro, usar informações capturadas na limpeza
        if hasattr(self, '_temp_authors') and self._temp_authors:
            for author in self._temp_authors:
                if self._validate_author_name(author):
                    return author.strip()
        
        # Aplicar patterns diretamente no texto atual
        for pattern in self.advanced_author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if self._validate_author_name(author):
                    return author
        
        # Patterns específicos para casos especiais
        special_patterns = [
            r'\b([A-Z]\w+\s+[A-Z]\w+)\s+(?:Manning|Packt|OReilly)',
            r'(?:Manning|Packt|OReilly)\s+([A-Z]\w+\s+[A-Z]\w+)',
            r'\b([A-Z]\w+\s+[A-Z]\w+)\s+(?:presents|introduces)',
        ]
        
        for pattern in special_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if self._validate_author_name(author):
                    return author
        
        return ''
    
    def _validate_author_name(self, name: str) -> bool:
        """Validar se string parece nome de autor"""
        if not name or len(name) < 3:
            return False
        
        # Deve ter pelo menos 2 palavras
        words = name.split()
        if len(words) < 2:
            return False
        
        # Não pode ter números
        if any(char.isdigit() for char in name):
            return False
        
        # Palavras muito comuns que não são nomes
        invalid_words = [
            'edition', 'second', 'third', 'fourth', 'version',
            'programming', 'guide', 'manual', 'book', 'learning',
            'complete', 'practical', 'introduction', 'advanced'
        ]
        
        if any(word.lower() in invalid_words for word in words):
            return False
        
        # Deve começar com maiúscula
        if not all(word[0].isupper() for word in words if word):
            return False
        
        return True
    
    def _extract_v3_year(self, text: str) -> str:
        """Extração de ano V3 - CRÍTICA"""
        # Primeiro, usar informações capturadas na limpeza
        if hasattr(self, '_temp_years') and self._temp_years:
            for year in self._temp_years:
                if self._validate_year(year):
                    return year
        
        # Aplicar patterns no texto atual
        for pattern in self.advanced_year_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                year = match if isinstance(match, str) else match[0] if match else None
                if year and self._validate_year(year):
                    return year
        
        return ''
    
    def _validate_year(self, year: str) -> bool:
        """Validar se ano é razoável"""
        try:
            year_int = int(year)
            return 1990 <= year_int <= 2030
        except (ValueError, TypeError):
            return False
    
    def _detect_v3_publisher(self, text: str) -> str:
        """Detecção de publisher V3 - MELHORADA"""
        text_lower = text.lower()
        
        # Score system para publishers
        publisher_scores = {}
        
        for publisher, patterns in self.enhanced_publisher_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Peso baseado na especificidade do pattern
                    weight = 2.0 if len(pattern) > 10 else 1.0
                    score += weight
            
            if score > 0:
                publisher_scores[publisher] = score
        
        if publisher_scores:
            best_publisher = max(publisher_scores.items(), key=lambda x: x[1])
            return best_publisher[0]
        
        return ''
    
    def _extract_v3_title(self, text: str) -> str:
        """Extração de título V3"""
        title = text
        
        # Remover autor identificado
        author = self._extract_v3_author(text)
        if author:
            title = title.replace(author, '').strip()
        
        # Remover publisher identificado
        publisher = self._detect_v3_publisher(text)
        if publisher:
            for pattern in self.enhanced_publisher_patterns[publisher]:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remover ano identificado
        year = self._extract_v3_year(text)
        if year:
            title = title.replace(year, '').strip()
        
        # Limpeza final
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'^[\-\s]+|[\-\s]+$', '', title)
        
        return title
    
    def _extract_v3_edition(self, text: str) -> str:
        """Extração de edição V3"""
        patterns = [
            r'(Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Edition',
            r'(\d+)(st|nd|rd|th)\s+Edition',
            r'Edition\s+(\d+)',
            r'(\d+)e\s+Edition'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def _extract_v3_version(self, text: str) -> str:
        """Extração de versão V3"""
        if re.search(r'meap', text, re.IGNORECASE):
            version_match = re.search(r'v(\d+)', text, re.IGNORECASE)
            if version_match:
                return f"v{version_match.group(1)} MEAP"
            else:
                return "MEAP"
        
        return ''
    
    def _detect_v3_category(self, text: str) -> str:
        """Detecção de categoria V3"""
        text_lower = text.lower()
        category_scores = {}
        
        for category, keywords in self.super_categories.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # Peso baseado na especificidade
                    weight = 3.0 if len(keyword.split()) > 1 else 1.0  
                    if keyword in ['python', 'java', 'javascript']:  # Keywords muito específicas
                        weight = 4.0
                    score += weight
            
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return 'General'
        
        best_category = max(category_scores.items(), key=lambda x: x[1])
        return best_category[0]
    
    def _detect_v3_subcategory(self, text: str, main_category: str) -> str:
        """Detectar subcategoria V3"""
        text_lower = text.lower()
        
        subcategories = {
            'Programming': {
                'Python': ['python'],
                'JavaScript': ['javascript', 'js', 'react', 'vue', 'angular'],
                'Java': ['java'],
                'C/C++': ['c++', 'cpp', 'c programming'],
                'Go': ['golang', 'go'],
                'Rust': ['rust'],
                'Functional': ['functional', 'haskell', 'lisp', 'scala']
            },
            'Security': {
                'Ethical Hacking': ['ethical', 'penetration', 'pentest'],
                'Malware': ['malware', 'virus', 'trojan'],
                'Forensics': ['forensic', 'investigation', 'incident'],
                'Cryptography': ['cryptography', 'encryption', 'crypto']
            },
            'Database': {
                'SQL': ['sql', 'mysql', 'postgresql'],
                'NoSQL': ['mongo', 'redis', 'cassandra'],
                'Analytics': ['analytics', 'analysis', 'science'],
                'Big Data': ['hadoop', 'spark', 'kafka']
            }
        }
        
        if main_category in subcategories:
            for subcat, keywords in subcategories[main_category].items():
                if any(keyword in text_lower for keyword in keywords):
                    return subcat
        
        return ''
    
    def _extract_v3_keywords(self, text: str) -> List[str]:
        """Extração de palavras-chave V3"""
        text_lower = text.lower()
        keywords = set()
        
        # Buscar em todas as categorias
        for category_keywords in self.super_categories.values():
            for keyword in category_keywords:
                if keyword in text_lower:
                    keywords.add(keyword)
        
        # Termos técnicos específicos expandidos
        tech_terms = [
            'api', 'rest', 'graphql', 'microservices', 'container',
            'kubernetes', 'docker', 'cloud', 'aws', 'azure', 'gcp',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scipy',
            'react', 'vue', 'angular', 'node', 'express',
            'mysql', 'postgresql', 'mongodb', 'redis',
            'linux', 'windows', 'ubuntu', 'debian'
        ]
        
        for term in tech_terms:
            if term in text_lower:
                keywords.add(term)
        
        return sorted(list(keywords))
    
    def _detect_v3_language(self, text: str) -> str:
        """Detectar idioma V3"""
        portuguese_indicators = [
            'aprenda', 'programar', 'com', 'desenvolvimento',
            'orientacao', 'objetos', 'conceitos', 'aplicabilidades',
            'guia', 'completo', 'pratico'
        ]
        
        if any(indicator in text.lower() for indicator in portuguese_indicators):
            return 'Portuguese'
        
        return 'English'
    
    def _calculate_v3_confidence(self, metadata: Dict[str, Any]) -> float:
        """Calcular confiança V3"""
        score = 0.0
        
        # Título sempre presente
        if metadata['title']:
            score += 0.25
        
        # Metadados críticos com pesos ajustados
        if metadata['author']:
            score += 0.20  # Peso alto para autor
        if metadata['publisher']:
            score += 0.15  # Peso alto para publisher
        if metadata['year']:
            score += 0.15  # Peso alto para ano
        if metadata['edition']:
            score += 0.08
        
        # Categorização
        if metadata['category'] != 'General':
            score += 0.12
        if metadata['subcategory']:
            score += 0.05
        
        # Keywords abundance bonus
        if len(metadata['keywords']) > 0:
            keyword_bonus = min(len(metadata['keywords']) * 0.01, 0.1)
            score += keyword_bonus
        
        return min(score, 1.0)

def main():
    """Teste V3 focado nas correções críticas"""
    logger.info("=== ALGORITMOS V3 - CORREÇÕES CRÍTICAS ===")
    
    # Testar extração V3
    books_dir = Path("books")
    extractor = AdvancedMetadataExtractor()
    
    sample_files = [
        "Python_Workout.pdf",
        "JavaScript_React_Development.pdf", 
        "Machine_Learning_2023.pdf",
        "Database_SQL_Manning_2022.pdf",
        "Ethical_Hacking_by_John_Smith.pdf"
    ]
    
    logger.info("=== TESTE DE EXTRAÇÃO V3 ===")
    
    # Testar com arquivos reais limitados
    count = 0
    for file_path in books_dir.iterdir():
        if count >= 10:
            break
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
            metadata = extractor.extract_v3_metadata(file_path.name)
            
            logger.info(f"\nArquivo: {file_path.name}")
            logger.info(f"  Título: {metadata['title']}")
            logger.info(f"  Autor: '{metadata['author']}'")
            logger.info(f"  Publisher: '{metadata['publisher']}'")
            logger.info(f"  Ano: '{metadata['year']}'")
            logger.info(f"  Categoria: {metadata['category']}")
            logger.info(f"  Confiança: {metadata['confidence']:.3f}")
            
            count += 1
    
    logger.info("\n=== FOCOS DE MELHORIA V3 ===")
    logger.info(" Author extraction patterns expandidos")
    logger.info(" Year extraction patterns robustos")
    logger.info(" Publisher detection melhorado")
    logger.info(" Validation functions implementadas")
    logger.info(" Super categories expandidas")
    
if __name__ == "__main__":
    main()