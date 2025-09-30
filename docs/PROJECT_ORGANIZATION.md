# ORGANIZACAO DO PROJETO RENAMEPDFEPUB

## Estrutura Organizacional Profissional

### Diretorio Raiz
```
renamepdfepub/
├── README.md                    # Documentacao principal
├── CHANGELOG.md                 # Historico de mudancas
├── requirements.txt             # Dependencias
├── pytest.ini                  # Configuracao de testes
├── start_*.py                   # Scripts de inicializacao
└── ATUALIZACAO_MD_COMPLETA.md   # Log da ultima atualizacao
```

### Codigo Fonte - src/
```
src/
├── core/                        # Logica principal do sistema
│   ├── enhanced_algorithms.py   # Algoritmos melhorados (ex: improved_algorithms_v2.py)
│   └── advanced_algorithm_comparison.py
├── cli/                         # Interface linha de comando
├── gui/                         # Interfaces graficas
└── renamepdfepub/               # Modulo principal
```

### Documentacao - docs/
```
docs/
├── structure/                   # Documentacao da estrutura
│   ├── project_structure.md     # Ex: STRUCTURE_FINAL.md
│   ├── repository_layout.md     # Ex: STRUCTURE.md
│   └── complete_analysis.md     # Ex: ESTRUTURA_ATUAL_COMPLETA.md
├── testing/                     # Documentacao de testes
│   ├── test_suite_report.md     # Ex: TESTE_SUITE_FINAL_CLEAN.md
│   ├── final_test_report.md     # Ex: RELATORIO_FINAL_TESTES.md
│   ├── comprehensive_test_report.md # Ex: RELATORIO_TESTES_COMPLETO.md
│   └── test_analysis.md         # Ex: RELATORIO_TESTES.md
├── reports/                     # Relatorios de implementacao
│   ├── reference_validation.md  # Ex: VALIDACAO_FINAL_REFERENCIAS.md
│   ├── reorganization_summary.md # Ex: REORGANIZATION_COMPLETE.md
│   └── implementation_fixes.md  # Ex: CORRECOES_IMPLEMENTADAS.md
└── releases/                    # Notas de release
```

### Dados e Resultados - data/
```
data/
├── results/                     # Resultados de analises
│   ├── algorithm_comparison.json # Ex: advanced_algorithm_comparison.json
│   └── multi_algorithm_analysis.json # Ex: multi_algorithm_comparison.json
├── algorithm_results/           # Ex: algorithm_test_results/
├── enhanced_results/            # Ex: improved_test_results/
├── basic_results/               # Ex: simple_test_results/
├── executive_analysis/          # Ex: executive_results/
├── validation/                  # Dados de validacao
└── cache/                       # Cache de metadados
```

### Utilitarios - utils/
```
utils/
├── simple_test_runner.py        # Ex: quick_test_simple.py
├── system_validator.py          # Ex: quick_validation.py
├── organize_docs.py             # Organizacao de documentos
└── README.md                    # Documentacao dos utilitarios
```

### Logs - logs/
```
logs/
├── dependency_manager.log       # Movido da raiz
└── outros_logs.log
```

## Melhorias Implementadas

### Nomenclatura Profissional
- ❌ **executive_results** → ✅ **executive_analysis**
- ❌ **improved_test_results** → ✅ **enhanced_results**
- ❌ **simple_test_results** → ✅ **basic_results**
- ❌ **improved_algorithms_v2.py** → ✅ **enhanced_algorithms.py**

### Organizacao por Categoria
- **Estrutura**: `docs/structure/`
- **Testes**: `docs/testing/`
- **Relatorios**: `docs/reports/`
- **Resultados**: `data/results/`
- **Utilitarios**: `utils/`
- **Logs**: `logs/`

### Beneficios da Reorganizacao
1. **Localizacao Intuitiva**: Arquivos agrupados por funcao
2. **Nomenclatura Clara**: Nomes descritivos e profissionais
3. **Manutencao Facilitada**: Estrutura logica e organizada
4. **Escalabilidade**: Facil adicao de novos componentes
5. **Padrao Industrial**: Segue boas praticas de organizacao

## Arquivos Movidos

### Da Raiz para docs/structure/
- `STRUCTURE_FINAL.md` → `docs/structure/project_structure.md`
- `STRUCTURE.md` → `docs/structure/repository_layout.md`
- `ESTRUTURA_ATUAL_COMPLETA.md` → `docs/structure/complete_analysis.md`

### Da Raiz para docs/testing/
- `TESTE_SUITE_FINAL_CLEAN.md` → `docs/testing/test_suite_report.md`
- `RELATORIO_FINAL_TESTES.md` → `docs/testing/final_test_report.md`
- `RELATORIO_TESTES_COMPLETO.md` → `docs/testing/comprehensive_test_report.md`
- `RELATORIO_TESTES.md` → `docs/testing/test_analysis.md`

### Da Raiz para docs/reports/
- `VALIDACAO_FINAL_REFERENCIAS.md` → `docs/reports/reference_validation.md`
- `REORGANIZATION_COMPLETE.md` → `docs/reports/reorganization_summary.md`
- `CORRECOES_IMPLEMENTADAS.md` → `docs/reports/implementation_fixes.md`

### Da Raiz para data/results/
- `advanced_algorithm_comparison.json` → `data/results/algorithm_comparison.json`
- `multi_algorithm_comparison.json` → `data/results/multi_algorithm_analysis.json`

### Da Raiz para utils/
- `quick_test_simple.py` → `utils/simple_test_runner.py`
- `quick_validation.py` → `utils/system_validator.py`

### Renomeacoes de Diretorios
- `executive_results/` → `data/executive_analysis/`
- `improved_test_results/` → `data/enhanced_results/`
- `simple_test_results/` → `data/basic_results/`
- `algorithm_test_results/` → `data/algorithm_results/`

## Status
**ORGANIZACAO CONCLUIDA** - Estrutura profissional e intuitiva implementada.

## Core vs Algorithms

Entrada canônica (Core)
----------------------
- CLI `start_cli.py` chama o pipeline do core em `src/core/renomeia_livro.py`
  nos comandos `scan` e `scan-cycles`.
- O pipeline gera relatórios HTML/JSON e exporta métricas ao vivo em `reports/`.

Algoritmos (comparação/tuning)
------------------------------
- O subcomando `algorithms` utiliza `src/core/advanced_algorithm_comparison.py`
  para avaliar heurísticas e estratégias — não substitui o fluxo canônico de
  varredura.
Deprecated (Legacy) Runners
---------------------------
- legacy/renomeia_livro_renew_v2.py
- legacy/renomeia_livro_renew_v3.py
- legacy/renomeia_livro_renew_v5.py

Estes arquivos foram mantidos apenas para referência histórica. O pipeline
canônico encontra-se em `src/core/renomeia_livro.py` e é chamado pelo CLI
(`start_cli.py`) nos comandos `scan` e `scan-cycles`.

Não modifique os arquivos legacy. Toda melhoria deve ser aplicada no core.
Se for necessário portar uma solução antiga, copie-a para o core em forma
modular (utils) e mantenha a documentação atualizada.
