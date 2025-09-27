"""
Dependency Manager - Gerenciamento de dependências opcionais para renamepdfepub.

Este módulo verifica e gerencia as dependências opcionais do projeto,
permitindo que o sistema funcione com diferentes combinações de bibliotecas instaladas.

Originalmente extraído de renomeia_livro.py para modularização da arquitetura.
"""

import logging
from typing import List


class DependencyManager:
    """
    Gerencia dependências opcionais e verifica disponibilidade de bibliotecas.
    
    Esta classe centraliza a detecção de dependências opcionais como pdfplumber,
    pdfminer, tesseract, etc., permitindo que o sistema se adapte às bibliotecas
    disponíveis no ambiente.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de dependências."""
        # Initialize a logger early so helper methods can use it safely
        self._init_logging()

        self.available_extractors = {
            'pypdf2': True,  # Já sabemos que está disponível pois é requisito
            'pdfplumber': False,
            'pdfminer': False,
            'tesseract': False,
            'pdf2image': False
        }
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Verifica quais dependências estão disponíveis."""
        # Verifica pdfplumber
        try:
            import pdfplumber
            self.available_extractors['pdfplumber'] = True
        except ImportError:
            self.logger.debug("pdfplumber não está instalado. Usando alternativas.")

        # Verifica pdfminer
        try:
            from pdfminer.high_level import extract_text
            self.available_extractors['pdfminer'] = True
        except ImportError:
            self.logger.debug("pdfminer.six não está instalado. Usando alternativas.")

        # Verifica Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.available_extractors['tesseract'] = True
        except:
            self.logger.debug("Tesseract OCR não está instalado/configurado.")

        # Verifica pdf2image
        try:
            import pdf2image
            self.available_extractors['pdf2image'] = True
        except ImportError:
            self.logger.debug("pdf2image não está instalado.")

    def _init_logging(self):
        """Initialize a simple logger for the DependencyManager."""
        self.logger = logging.getLogger('dependency_manager')
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            fh = logging.FileHandler('dependency_manager.log')
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            fh.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            ch.setLevel(logging.WARNING)
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def get_available_extractors(self) -> List[str]:
        """Retorna lista de extractors disponíveis."""
        return [k for k, v in self.available_extractors.items() if v]

    @property
    def has_ocr_support(self) -> bool:
        """Verifica se o suporte a OCR está disponível."""
        return self.available_extractors['tesseract'] and self.available_extractors['pdf2image']
    
    def check_extractor_availability(self, extractor_name: str) -> bool:
        """
        Verifica se um extractor específico está disponível.
        
        Args:
            extractor_name: Nome do extractor ('pypdf2', 'pdfplumber', etc.)
            
        Returns:
            bool: True se o extractor está disponível
        """
        return self.available_extractors.get(extractor_name, False)
    
    def get_best_pdf_extractor(self) -> str:
        """
        Retorna o melhor extractor de PDF disponível.
        
        Returns:
            str: Nome do melhor extractor disponível
        """
        # Ordem de preferência baseada na qualidade de extração
        preference_order = ['pdfplumber', 'pdfminer', 'pypdf2']
        
        for extractor in preference_order:
            if self.available_extractors.get(extractor, False):
                return extractor
        
        # Fallback para pypdf2 que é obrigatório
        return 'pypdf2'
    
    def get_dependency_report(self) -> dict:
        """
        Gera relatório completo das dependências.
        
        Returns:
            dict: Relatório com status de todas as dependências
        """
        return {
            'available_extractors': self.available_extractors.copy(),
            'best_pdf_extractor': self.get_best_pdf_extractor(),
            'ocr_support': self.has_ocr_support,
            'total_available': len(self.get_available_extractors()),
            'total_possible': len(self.available_extractors)
        }