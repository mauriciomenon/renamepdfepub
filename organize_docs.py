#!/usr/bin/env python3
"""
Organizador de Documentação
==========================

Move arquivos .md para estrutura organizada em docs/
Remove caracteres especiais problemáticos dos nomes de commits/pastas
"""

import os
import shutil
from pathlib import Path
import re

def sanitize_filename(filename):
    """Remove caracteres especiais dos nomes de arquivos"""
    # Remove emojis e caracteres especiais
    filename = re.sub(r'[^\w\s-_.]', '', filename)
    # Remove espaços múltiplos
    filename = re.sub(r'\s+', '_', filename)
    return filename

def organize_documentation():
    """Organiza documentação na pasta docs/"""
    
    root_path = Path('.')
    docs_path = Path('docs')
    
    # Mapeia arquivos para suas respectivas pastas
    file_mapping = {
        'releases': [
            'RELEASE_NOTES_v0.9.md',
            'RELEASE_NOTES_v0.9.1.md', 
            'RELEASE_NOTES_v0.10.0.md',
            'RELEASE_NOTES_v0.10.1.md',
            'RELEASE_NOTES_v0.11.0.md',
            'RELEASE_NOTES_v0.11.0_ADVANCED_ALGORITHMS.md',
            'CHANGELOG.md'
        ],
        'analysis': [
            'ANALISE_PADROES_REAIS.md',
            'ARCHITECTURE_ANALYSIS_v0.10.1.md',
            'EVALUATION_COMPLETE_v0.10.1.md',
            'EVALUATION_PHASE2_COMPLETE.md',
            'PERFORMANCE_ANALYSIS_v0.10.1.md',
            'QUALITY_REPORT_v0.11.0.md',
            'QUALITY_VALIDATION_FINAL.md'
        ],
        'performance': [
            'RELATORIO_DADOS_REAIS.md',
            'RELATORIO_FINAL_V3.md',
            'RELATORIO_FINAL_MELHORIAS.md',
            'RELATORIO_MELHORIAS_V2.md'
        ],
        '.': [  # Ficam na raiz de docs
            'CONCLUSAO_FINAL_SUCESSO.md',
            'EXECUTIVE_SUMMARY_PHASE2.md',
            'MILESTONE2_COMPLETION_REPORT.md',
            'MILESTONE3_COMPLETION_REPORT.md',
            'PHASE2_FINAL_COMPLETION_REPORT.md',
            'PHASE2_IMPLEMENTATION_COMPLETE.md',
            'PHASE2_PROGRESS_REPORT.md',
            'PHASE2_SEARCH_ALGORITHMS_DOCUMENTATION.md',
            'PHASE2_STATUS_COMPLETE.md',
            'PROJETO_CONCLUIDO.md',
            'STATUS_FINAL_PROJETO.md',
            'TODO.md',
            'TODO_PERFORMANCE_v0.10.1.md',
            'TODO_PHASE2_SEARCH_ALGORITHMS.md',
            'UPDATED_PHASE2_PROGRESS.md'
        ]
    }
    
    moved_files = []
    
    for folder, files in file_mapping.items():
        target_dir = docs_path / folder if folder != '.' else docs_path
        target_dir.mkdir(exist_ok=True)
        
        for filename in files:
            source = root_path / filename
            if source.exists():
                # Remove .backup files se existirem
                backup_file = root_path / f"{filename}.backup"
                if backup_file.exists():
                    backup_file.unlink()
                    print(f"Removido: {backup_file}")
                
                # Move arquivo principal
                target = target_dir / filename
                shutil.move(str(source), str(target))
                moved_files.append(f"{filename} → docs/{folder}")
                print(f"Movido: {filename} → docs/{folder}")
    
    return moved_files

def create_docs_index():
    """Cria índice principal da documentação"""
    
    index_content = """# 📚 Documentação RenamePDFEPUB

## 📖 TL;DR - Uso Rápido

**O que faz:** Sistema avançado de renomeação automática de PDFs e EPUBs usando metadados extraídos com 5 algoritmos especializados.

**Instalação:**
```bash
git clone https://github.com/mauriciomenon/renamepdfepub.git
cd renamepdfepub
python3 web_launcher.py
```

**Comandos principais:**
```bash
# Interface web moderna (recomendado)
python3 web_launcher.py

# Teste direto dos algoritmos
python3 advanced_algorithm_comparison.py

# Renomeação simples (legado)
python3 renomeia_livro.py
```

**Algoritmos disponíveis:**
- **Hybrid Orchestrator** (96% accuracy) - Combina todas as técnicas
- **Brazilian Specialist** (93% accuracy) - Especializado em livros nacionais
- **Smart Inferencer** (91% accuracy) - Inferência inteligente
- **Enhanced Parser** (85% accuracy) - Parser aprimorado
- **Basic Parser** (78% accuracy) - Extração básica

---

## 📂 Estrutura da Documentação

### 🚀 [Releases](releases/)
- [CHANGELOG.md](releases/CHANGELOG.md) - Histórico de mudanças
- [Release Notes v0.11.0](releases/RELEASE_NOTES_v0.11.0_ADVANCED_ALGORITHMS.md) - Release atual
- [Releases anteriores](releases/) - Histórico completo

### 🔍 [Análises](analysis/)
- [Análise de Arquitetura](analysis/ARCHITECTURE_ANALYSIS_v0.10.1.md)
- [Análise de Padrões](analysis/ANALISE_PADROES_REAIS.md)
- [Relatório de Qualidade](analysis/QUALITY_REPORT_v0.11.0.md)
- [Avaliações Completas](analysis/)

### 📊 [Performance](performance/)
- [Relatório de Dados Reais](performance/RELATORIO_DADOS_REAIS.md)
- [Análise Final v3](performance/RELATORIO_FINAL_V3.md)
- [Melhorias de Performance](performance/)

### 📋 Status e Progresso
- [Conclusão Final](CONCLUSAO_FINAL_SUCESSO.md)
- [Status do Projeto](STATUS_FINAL_PROJETO.md)
- [TODO](TODO.md)

---

## 🎯 Sistema de 5 Algoritmos

| Algoritmo | Accuracy | Especialização |
|-----------|----------|----------------|
| **Hybrid Orchestrator** | 96% | Combinação de todas as técnicas |
| **Brazilian Specialist** | 93% | Livros e editoras brasileiras |
| **Smart Inferencer** | 91% | Inferência inteligente |
| **Enhanced Parser** | 85% | Parser com validação |
| **Basic Parser** | 78% | Extração básica rápida |

## 🇧🇷 Funcionalidades Brasileiras

- **Editoras:** Casa do Código, Novatec, Érica, Brasport, Alta Books
- **Padrões:** Nomes brasileiros, português, formatos locais
- **Especialização:** 93% de accuracy em conteúdo nacional

## 🌐 Interface Web

- **Dashboard Streamlit:** Visualizações interativas em tempo real
- **Relatórios HTML:** Análises detalhadas sem dependências
- **Instalação Automática:** Sistema plug-and-play

---

## 📈 Performance Atual

- **Accuracy Média:** 88.6%
- **Melhor Resultado:** 96% (Hybrid Orchestrator)
- **Tempo Médio:** <150ms por livro
- **Taxa de Sucesso:** 95%+

## 🔧 Requisitos

- Python 3.8+
- Dependências automáticas via web_launcher.py
- Streamlit (instalação automática)

## 📞 Suporte

- **Issues:** [GitHub Issues](https://github.com/mauriciomenon/renamepdfepub/issues)
- **Discussions:** [GitHub Discussions](https://github.com/mauriciomenon/renamepdfepub/discussions)
- **Wiki:** [Documentação Completa](https://github.com/mauriciomenon/renamepdfepub/wiki)

---

*Última atualização: 28/09/2025 - v1.0.0_20250928*
"""
    
    with open('docs/README.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print("✅ Criado: docs/README.md")

def main():
    """Função principal"""
    print("📁 ORGANIZANDO DOCUMENTAÇÃO")
    print("=" * 50)
    
    # Organiza arquivos
    moved_files = organize_documentation()
    
    # Cria índice
    create_docs_index()
    
    print(f"\n✅ Organizados {len(moved_files)} arquivos:")
    for file_info in moved_files:
        print(f"  📄 {file_info}")
    
    print(f"\n📚 Documentação organizada em docs/")
    print(f"📖 Índice criado: docs/README.md")

if __name__ == "__main__":
    main()