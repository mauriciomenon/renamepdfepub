"""
Publisher Configuration - Configurações específicas de editoras.

Contém padrões de regex, normalizações e configurações específicas
para diferentes editoras, incluindo publishers brasileiros e internacionais.

Originalmente extraído de renomeia_livro.py para modularização.
"""

# Configurações de editoras brasileiras
BRAZILIAN_PUBLISHERS = {
    'casa do codigo': {
        'pattern': r'Casa do [cC]ódigo.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'novatec': {
        'pattern': r'Novatec\s+Editora.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'alta books': {
        'pattern': r'Alta\s+Books.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    }
}

# Configurações de editoras internacionais
INTERNATIONAL_PUBLISHERS = {
    'packt': {
        'pattern': r'Packt\s+Publishing.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1,
        'corrupted_chars': {'@': '9', '>': '7', '?': '8', '_': '-'}
    },
    'oreilly': {
        'pattern': r"O'Reilly\s+Media.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)",
        'confidence_boost': 0.1
    },
    'wiley': {
        'pattern': r'(?:John\s+)?Wiley\s+&\s+Sons.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'apress': {
        'pattern': r'Apress.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'manning': {
        'pattern': r'Manning\s+Publications.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'pragmatic': {
        'pattern': r'Pragmatic\s+Bookshelf.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    }
}

# Normalização de nomes de editoras
NORMALIZED_PUBLISHERS = {
    # O'Reilly variants
    "O'REILLY": "OReilly",
    "O'REILLY": "OReilly",
    "O'REILLY MEDIA": "OReilly",
    "O'REILLY MEDIA": "OReilly",
    "O'REILLY MEDIA, INC": "OReilly",
    "O'REILLY MEDIA, INC.": "OReilly",
    "O'REILLY MEDIA INC": "OReilly",
    "O'REILLY PUBLISHING": "OReilly",
    "O'REILLY & ASSOCIATES": "OReilly",
    "OREILLY": "OReilly",
    "OREILLY MEDIA": "OReilly",
    "OREILLY MEDIA INC": "OReilly",
    "OREILLY MEDIA, INC": "OReilly",
    
    # Manning variants
    "MANNING PUBLICATIONS": "Manning",
    "MANNING PRESS": "Manning",
    
    # Packt variants
    "PACKT PUBLISHING": "Packt",
    "PACKT PUB": "Packt",
    
    # Brazilian publishers
    "CASA DO CÓDIGO": "Casa do Codigo",
    "CDC": "Casa do Codigo",
    "CASADOCODIGO": "Casa do Codigo",
    
    "NOVATEC EDITORA": "Novatec",
    "EDITORA NOVATEC": "Novatec",
    
    "ALTA BOOKS EDITORA": "Alta Books",
    "ALTABOOKS": "Alta Books",
    
    # Additional common variations
    "ADDISON-WESLEY": "Addison Wesley",
    "ADDISON WESLEY": "Addison Wesley",
    "PEARSON": "Pearson",
    "PEARSON EDUCATION": "Pearson",
    "MCGRAW-HILL": "McGraw Hill",
    "MCGRAW HILL": "McGraw Hill"
}

def get_all_publishers():
    """Retorna dicionário com todas as editoras configuradas."""
    all_publishers = {}
    all_publishers.update(BRAZILIAN_PUBLISHERS)
    all_publishers.update(INTERNATIONAL_PUBLISHERS)
    return all_publishers

def normalize_publisher_name(publisher_name: str) -> str:
    """
    Normaliza nome de editora usando tabela de normalizações.
    
    Args:
        publisher_name: Nome da editora para normalizar
        
    Returns:
        str: Nome normalizado da editora
    """
    if not publisher_name:
        return publisher_name
        
    normalized = publisher_name.upper().strip()
    return NORMALIZED_PUBLISHERS.get(normalized, publisher_name)

def get_publisher_config(publisher_key: str) -> dict:
    """
    Obtém configuração de uma editora específica.
    
    Args:
        publisher_key: Chave da editora (ex: 'packt', 'oreilly')
        
    Returns:
        dict: Configuração da editora ou dicionário vazio se não encontrada
    """
    all_publishers = get_all_publishers()
    return all_publishers.get(publisher_key.lower(), {})