#!/usr/bin/env python3
"""
Sistema de Validacao de Referencias Cruzadas
============================================

Valida imports, referencias de arquivos e estrutura do repositorio.
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Set

def analyze_python_imports(file_path: Path) -> Dict[str, List[str]]:
    """Analisa imports de um arquivo Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        imports = {
            'standard': [],
            'relative': [],
            'absolute': [],
            'errors': []
        }
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if line.startswith('from ') and ' import ' in line:
                # from module import something
                parts = line.replace('from ', '').split(' import ')
                if len(parts) == 2:
                    module = parts[0].strip()
                    if module.startswith('.'):
                        imports['relative'].append(f"Line {line_num}: {line}")
                    else:
                        imports['absolute'].append(f"Line {line_num}: {line}")
            
            elif line.startswith('import '):
                # import module
                module = line.replace('import ', '').strip()
                if '.' in module and not module.startswith('.'):
                    imports['absolute'].append(f"Line {line_num}: {line}")
                else:
                    imports['standard'].append(f"Line {line_num}: {line}")
    
    except Exception as e:
        imports['errors'] = [str(e)]
    
    return imports

def find_file_references(file_path: Path) -> List[str]:
    """Encontra referencias a outros arquivos no codigo"""
    references = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Padrao comum: Path(...) / "arquivo.py"
        import re
        
        # Referencias de arquivos Python
        py_refs = re.findall(r'["\']([^"\']*\.py)["\']', content)
        for ref in py_refs:
            if ref not in references:
                references.append(ref)
        
        # Referencias de pastas comuns
        folder_refs = re.findall(r'["\']([^"\']*/(src|reports|utils|docs|tests)/[^"\']*)["\']', content)
        for ref_tuple in folder_refs:
            ref = ref_tuple[0] if isinstance(ref_tuple, tuple) else ref_tuple
            if ref not in references:
                references.append(ref)
    
    except Exception as e:
        references.append(f"ERROR: {e}")
    
    return references

def validate_file_exists(base_path: Path, reference: str) -> bool:
    """Verifica se um arquivo referenciado existe"""
    # Tenta diferentes combinacoes de caminho
    possible_paths = [
        base_path / reference,
        base_path / reference.replace('src/', ''),
        Path(reference),  # caminho absoluto
        base_path.parent / reference  # um nivel acima
    ]
    
    for path in possible_paths:
        if path.exists():
            return True
    return False

def scan_entry_points() -> Dict[str, Dict]:
    """Escaneia pontos de entrada do sistema"""
    entry_points = {
        'start_cli.py': {'type': 'CLI', 'status': 'unknown'},
        'start_web.py': {'type': 'Web', 'status': 'unknown'},
        'start_gui.py': {'type': 'GUI', 'status': 'unknown'},
        'start_html.py': {'type': 'HTML', 'status': 'unknown'},
        'start_iterative_cache.py': {'type': 'Cache', 'status': 'unknown'}
    }
    
    base_path = Path('.')
    
    for entry_file, info in entry_points.items():
        file_path = base_path / entry_file
        
        if not file_path.exists():
            info['status'] = 'missing'
            continue
        
        # Analisa o arquivo
        imports = analyze_python_imports(file_path)
        references = find_file_references(file_path)
        
        info.update({
            'status': 'exists',
            'imports': imports,
            'file_references': references,
            'broken_refs': []
        })
        
        # Verifica referencias quebradas
        for ref in references:
            if ref.endswith('.py') and not validate_file_exists(file_path.parent, ref):
                info['broken_refs'].append(ref)
    
    return entry_points

def scan_core_modules() -> Dict[str, Dict]:
    """Escaneia modulos principais do sistema"""
    core_paths = [
        'src/core',
        'src/gui', 
        'src/cli',
        'reports',
        'utils'
    ]
    
    modules = {}
    
    for path_str in core_paths:
        path = Path(path_str)
        if not path.exists():
            modules[path_str] = {'status': 'missing', 'files': []}
            continue
        
        files = list(path.glob('*.py'))
        modules[path_str] = {
            'status': 'exists',
            'file_count': len(files),
            'files': []
        }
        
        for file_path in files[:5]:  # Limita a 5 arquivos por pasta
            file_info = {
                'name': file_path.name,
                'imports': analyze_python_imports(file_path),
                'references': find_file_references(file_path)
            }
            modules[path_str]['files'].append(file_info)
    
    return modules

def check_standard_imports() -> Dict[str, str]:
    """Verifica imports padrao do Python"""
    standard_modules = [
        'tkinter', 'sqlite3', 'json', 'pathlib', 'os', 'sys',
        'subprocess', 'argparse', 'asyncio', 're', 'datetime'
    ]
    
    results = {}
    
    for module in standard_modules:
        try:
            importlib.import_module(module)
            results[module] = 'OK'
        except ImportError:
            results[module] = 'MISSING'
    
    return results

def generate_cross_reference_report() -> Dict:
    """Gera relatorio completo de referencias cruzadas"""
    print("Executando analise de referencias cruzadas...")
    
    report = {
        'timestamp': '2025-09-28',
        'entry_points': scan_entry_points(),
        'core_modules': scan_core_modules(),  
        'standard_imports': check_standard_imports(),
        'summary': {}
    }
    
    # Calcula resumo
    total_entry_points = len(report['entry_points'])
    working_entry_points = sum(1 for ep in report['entry_points'].values() 
                              if ep['status'] == 'exists' and not ep.get('broken_refs', []))
    
    total_modules = sum(info.get('file_count', 0) for info in report['core_modules'].values())
    
    working_imports = sum(1 for status in report['standard_imports'].values() if status == 'OK')
    total_imports = len(report['standard_imports'])
    
    report['summary'] = {
        'entry_points_ok': f"{working_entry_points}/{total_entry_points}",
        'modules_scanned': total_modules,
        'standard_imports_ok': f"{working_imports}/{total_imports}",
        'overall_status': 'OK' if working_entry_points == total_entry_points else 'ISSUES_FOUND'
    }
    
    return report

def print_readable_report(report: Dict):
    """Imprime relatorio em formato legivel"""
    print("\n" + "="*60)
    print("RELATORIO DE REFERENCIAS CRUZADAS")
    print("="*60)
    
    # Resumo geral
    summary = report['summary']
    print(f"\nRESUMO GERAL:")
    print(f"  Entry Points: {summary['entry_points_ok']}")
    print(f"  Modulos Escaneados: {summary['modules_scanned']}")
    print(f"  Imports Padrao: {summary['standard_imports_ok']}")
    print(f"  Status Geral: {summary['overall_status']}")
    
    # Entry Points detalhado
    print(f"\nENTRY POINTS:")
    for name, info in report['entry_points'].items():
        status_icon = "✅" if info['status'] == 'exists' and not info.get('broken_refs', []) else "❌"
        print(f"  {status_icon} {name:<25} {info['status']}")
        
        if info.get('broken_refs'):
            for ref in info['broken_refs']:
                print(f"    ❌ Referencia quebrada: {ref}")
    
    # Modulos principais
    print(f"\nMODULOS PRINCIPAIS:")
    for path, info in report['core_modules'].items():
        if info['status'] == 'exists':
            print(f"  ✅ {path:<20} {info['file_count']} arquivos")
        else:
            print(f"  ❌ {path:<20} PASTA MISSING")
    
    # Imports padrao
    print(f"\nIMPORTS PADRAO:")
    for module, status in report['standard_imports'].items():
        icon = "✅" if status == 'OK' else "❌"
        print(f"  {icon} {module:<15} {status}")
    
    # Problemas criticos
    print(f"\nPROBLEMAS CRITICOS:")
    issues = []
    
    for name, info in report['entry_points'].items():
        if info['status'] != 'exists':
            issues.append(f"  - Entry point ausente: {name}")
        elif info.get('broken_refs'):
            for ref in info['broken_refs']:
                issues.append(f"  - Referencia quebrada em {name}: {ref}")
    
    for module, status in report['standard_imports'].items():
        if status != 'OK':
            issues.append(f"  - Import padrao falhou: {module}")
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("  Nenhum problema critico encontrado!")

def main():
    """Funcao principal"""
    print("Sistema de Validacao de Referencias Cruzadas")
    print("==========================================")
    
    # Gera relatorio
    report = generate_cross_reference_report()
    
    # Salva relatorio detalhado
    report_file = Path('cross_reference_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Imprime relatorio legivel
    print_readable_report(report)
    
    print(f"\nRelatorio detalhado salvo em: {report_file}")
    
    # Codigo de saida
    if report['summary']['overall_status'] == 'OK':
        print("\n✅ VALIDACAO CONCLUIDA - Sistema integro")
        return 0
    else:
        print("\n❌ VALIDACAO FALHOU - Correcoes necessarias")
        return 1

if __name__ == '__main__':
    sys.exit(main())