from typing import Optional

_PUBLISHER_MAPPING = {
    # Casa do Código (accent/variants)
    'EDITORA CASA DO CÓDIGO': 'Casa do Código',
    'CASA DO CÓDIGO': 'Casa do Código',
    'CASA DO CODIGO': 'Casa do Código',
    'CDC': 'Casa do Código',
    'CASADOCODIGO': 'Casa do Código',

    # Novatec
    'NOVATEC EDITORA': 'Novatec',
    'EDITORA NOVATEC': 'Novatec',
    'NOVATEC': 'Novatec',

    # Alta Books
    'ALTA BOOKS EDITORA': 'Alta Books',
    'ALTABOOKS': 'Alta Books',
    'ALTA BOOKS': 'Alta Books',

    # Manning
    'MANNING PUBLICATIONS': 'Manning',
    'MANNING PRESS': 'Manning',
    'MANNING': 'Manning',

    # O'Reilly (normalize to OReilly without apostrophe)
    "O'REILLY MEDIA INC": 'OReilly',
    "O'REILLY MEDIA, INC": 'OReilly',
    "O'REILLY MEDIA": 'OReilly',
    'OREILLY MEDIA': 'OReilly',
    'OREILLY': 'OReilly',

    # Packt
    'PACKT PUBLISHING': 'Packt',
    'PACKT PUB': 'Packt',
    'PACKT': 'Packt',
}


def canonical_publisher(name: Optional[str]) -> str:
    if not name:
        return ''
    n = name.strip()
    if not n:
        return ''
    if n.lower() == 'unknown':
        return ''
    u = n.upper()
    return _PUBLISHER_MAPPING.get(u, n)

