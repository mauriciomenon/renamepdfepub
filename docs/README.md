# Documentação – Guia Rápido

Este guia resume as operações principais para varrer metadados (scan), repetir varreduras, renomear com dados existentes e renomear buscando metadados. Funciona para pastas locais e sincronizadas (OneDrive/Google Drive).

## TL;DR – Operações Principais

```bash
# Instalar dependências
pip install -r requirements.txt

# Scan (gera JSON/HTML em reports/, não renomeia)
python3 start_cli.py scan "/caminho/livros"
python3 start_cli.py scan "/caminho/livros" -r
python3 start_cli.py scan "/caminho/livros" -t 8 -o relatorio.json

# Scan por ciclos/tempo
python3 start_cli.py scan-cycles "/caminho/livros" --cycles 3
python3 start_cli.py scan-cycles "/caminho/livros" --time-seconds 120

# Renomear com relatório existente
python3 start_cli.py rename-existing --report relatorio.json --apply [--copy]

# Renomear fazendo a procura (scan + rename)
python3 start_cli.py rename-search "/caminho/livros" --rename

# Streamlit (dashboard + scan pela barra lateral)
python3 start_web.py --auto-start

# GUI (botão "Gerar relatório da pasta")
python3 start_gui.py --dir "/caminho/inicial"
```

## Detalhes

- Os relatórios de scan são salvos em `reports/metadata_report_*.json` e `.html`.
- O Dashboard do Streamlit lê automaticamente o último JSON.
- A renomeação por relatório usa `src/renamepdfepub/renamer.py`.

## Diretrizes para IAs e Contribuição

Para manter a qualidade e consistência do projeto, consulte:
- AGENTS (regras para Codex/Copilot e outros): `AGENTS.md`
- Guia de Contribuição (padrões de código/UX/testes): `CONTRIBUTING.md`
- Orientações práticas para IAs (checklists): `docs/AI_GUIDELINES.md`
- Instruções do Copilot (VS Code/GitHub): `.copilot-instructions.md` e `.github/copilot-instructions.md`

Resumo rápido:
- Sem emojis; linguagem sóbria e profissional; evitar termos promocionais (final/ultra/definitivo/melhorado/refinado/superior).
- Funções modulares e descritivas; imports no topo; docstrings curtas.
- Tratamento de erros significativo e logging centralizado (não silenciar exceções).
- Teste para cada funcionalidade adicionada; validação semântica e de interface.
- UI responsiva (tarefas longas em background) com feedback claro; preview vs apply sempre que possível.
