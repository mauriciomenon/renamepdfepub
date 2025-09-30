#!/usr/bin/env python3
"""
Interface Web Streamlit - RenamePDFEPUB (ASCII only)
Sistema para renomeacao automatica de livros PDF/EPUB
"""

import streamlit as st
import os
import sys
import subprocess
from pathlib import Path

# Configuracao da pagina
st.set_page_config(
    page_title="RenamePDFEPUB - Renomeador de Livros",
    layout="wide"
)

class RenamePDFEPUBInterface:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.books_dir = self.project_root / "books"
        self.reports_dir = self.project_root / "reports"
        self.live_stats_file = self.reports_dir / "live_api_stats.json"
        self.default_scan_path = str(self.books_dir)

    def _tail_file(self, path: Path, max_lines: int = 200):
        try:
            if not path.exists():
                return []
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()
            return lines[-max_lines:]
        except Exception:
            return []

    def start_scan_background(self, target_dir: str, recursive: bool = False, extra_args: list = None, command: str = "scan"):
        try:
            script = self.project_root / "start_cli.py"
            args = [sys.executable, str(script), command, target_dir]
            if recursive:
                args.append("-r")
            if extra_args:
                args += extra_args
            # inicia em background
            import subprocess
            p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, p.pid
        except Exception as e:
            return False, str(e)
        
    def get_books_list(self):
        """Lista todos os livros PDF e EPUB"""
        books = []
        if self.books_dir.exists():
            pdf_files = list(self.books_dir.glob("*.pdf"))
            epub_files = list(self.books_dir.glob("*.epub"))
            books = pdf_files + epub_files
        return sorted(books)
    
    def run_algorithm(self, algorithm, book_path=None):
        """Executa algoritmo de renomeacao"""
        try:
            algorithm_script = self.project_root / "src" / "core" / "advanced_algorithm_comparison.py"
            
            if not algorithm_script.exists():
                return False, f"Arquivo nao encontrado: {algorithm_script}"
            
            cmd = [sys.executable, str(algorithm_script)]
            if book_path:
                cmd.extend(["--file", str(book_path)])
            if algorithm != "all":
                cmd.extend(["--algorithm", algorithm])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
                
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def render_header(self):
        """Cabecalho principal"""
        st.title("RenamePDFEPUB - Renomeador de Livros")
        st.markdown("Sistema para renomeacao automatica de arquivos PDF e EPUB")
        st.markdown("---")

    def _load_latest_report(self):
        """Carrega o relatorio JSON mais recente em reports/ (se existir)."""
        try:
            if not self.reports_dir.exists():
                return None
            candidates = sorted(self.reports_dir.glob("metadata_report_*.json"))
            if not candidates:
                return None
            latest = candidates[-1]
            import json
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return None

    def render_dashboard(self):
        """Exibe metricas reais a partir do relatorio em reports/."""
        st.header("Dashboard")
        with st.expander("Iniciar varredura (background)"):
            colx1, colx2 = st.columns([3,1])
            with colx1:
                target = st.text_input("Diretório a varrer", value=self.default_scan_path)
            with colx2:
                recursive = st.checkbox("Recursivo", value=False)
            mode = st.selectbox("Modo", ["scan", "scan-cycles"], index=0)
            cycles = 1
            if mode == "scan-cycles":
                cycles = st.number_input("Ciclos", min_value=1, max_value=50, value=3)
            if st.button("Iniciar scan agora"):
                extra = []
                if mode == "scan-cycles":
                    extra = ["--cycles", str(int(cycles))]
                cmd = mode if mode in ("scan", "scan-cycles") else "scan"
                ok, info = self.start_scan_background(target, recursive, extra_args=(extra if mode=="scan-cycles" else None), command=cmd)
                if ok:
                    st.success(f"Scan iniciado (PID {info}). Acompanhe métricas abaixo.")
                else:
                    st.error(f"Falha ao iniciar scan: {info}")
        data = self._load_latest_report()
        if not data:
            st.info("Nenhum relatorio encontrado em reports/. Gere um relatorio para visualizar metricas reais.")
            return
        # Estrutura esperada: chaves comuns usadas no projeto
        summary = data.get("summary") or {}
        # Metricas basicas
        total = summary.get("total_files") or summary.get("total_books") or summary.get("total") or 0
        success = summary.get("successful") or summary.get("success") or 0
        failed = summary.get("failed") or summary.get("failures") or 0
        with st.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de arquivos", total)
            c2.metric("Processados com sucesso", success)
            c3.metric("Falhas", failed)
        # Faltas por campo
        missing = summary.get("missing_fields") or {}
        if missing:
            st.subheader("Campos ausentes")
            for field, count in missing.items():
                st.write(f"- {field}: {count}")
        # Estatisticas por editora
        pub_stats = data.get("publisher_stats") or {}
        if pub_stats:
            st.subheader("Distribuicao por editora")
            for pub, cnt in list(pub_stats.items())[:15]:
                st.write(f"- {pub}: {cnt}")

        # Tempo real (se arquivo de métricas estiver disponível)
        st.subheader("Tempo real - Fontes de metadados")
        cols = st.columns([1,1,2])
        with cols[0]:
            if st.button("Atualizar agora"):
                st.experimental_rerun()
        with cols[1]:
            st.caption("Atualize enquanto a varredura estiver em execucao.")

        live = None
        try:
            if self.live_stats_file.exists():
                import json
                with open(self.live_stats_file, 'r', encoding='utf-8') as f:
                    live = json.load(f)
        except Exception:
            live = None

        if not live:
            st.info("Métricas em tempo real indisponíveis. Inicie uma varredura para gerar live_api_stats.json.")
            return

        overall = live.get("overall") or {}
        per_api = live.get("per_api") or {}
        open_circuits = live.get("open_circuits") or []
        open_detail = live.get("open_circuits_detail") or {}

        c1, c2, c3 = st.columns(3)
        c1.metric("Chamadas (total)", overall.get("total", 0))
        c2.metric("Sucessos", overall.get("success", 0))
        c3.metric("Taxa de sucesso", f"{overall.get('success_rate', 0.0):.1f}%")

        if open_circuits:
            items = []
            for api in open_circuits:
                secs = float(open_detail.get(api, 0.0))
                items.append(f"{api} (~{int(secs)}s)")
            st.warning("Circuito aberto: " + ", ".join(items))

        st.write("Fontes")
        # Tabela simples com os principais campos
        for api, stats in sorted(per_api.items()):
            st.write(f"- {api}: {stats.get('success',0)}/{stats.get('total',0)} ({stats.get('success_rate',0.0):.1f}%) - {stats.get('avg_time',0.0):.2f}s")

        # Visualizacao rapida (top 10 por volume de chamadas)
        if per_api:
            try:
                import pandas as pd
                rows = []
                for api, s in per_api.items():
                    rows.append({
                        'API': api,
                        'Chamadas': int(s.get('total', 0)),
                        'Sucesso %': float(s.get('success_rate', 0.0)),
                        'Tempo Médio (s)': float(s.get('avg_time', 0.0)),
                    })
                df = pd.DataFrame(rows)
                df_sorted = df.sort_values('Chamadas', ascending=False).head(10)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.caption("Top 10 por chamadas")
                    st.bar_chart(data=df_sorted.set_index('API')[['Chamadas']])
                with col_b:
                    st.caption("Taxa de sucesso (%)")
                    st.bar_chart(data=df_sorted.set_index('API')[['Sucesso %']])
            except Exception:
                pass

        # Logs recentes
        st.subheader("Logs recentes")
        log_choices = []
        candidate_logs = [
            (self.project_root / 'book_metadata.log', 'book_metadata.log'),
            (self.project_root / 'metadata_fetcher.log', 'metadata_fetcher.log'),
        ]
        for p, name in candidate_logs:
            if p.exists():
                log_choices.append((name, p))
        if not log_choices:
            st.caption("Nenhum log encontrado no diretório do projeto.")
        else:
            names = [n for n, _ in log_choices]
            sel = st.selectbox("Arquivo de log", names)
            path = next(p for n, p in log_choices if n == sel)
            tail_lines = self._tail_file(path, max_lines=200)
            st.code("\n".join(tail_lines) if tail_lines else "(vazio)")
    
    def render_books_section(self):
        """Secao principal: livros"""
        st.header("Biblioteca de Livros")
        
        books = self.get_books_list()
        
        if not books:
            st.warning("Nenhum livro encontrado na pasta 'books/'. Adicione arquivos PDF ou EPUB.")
            return
        
        st.info(f"{len(books)} arquivos encontrados")
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["Lista", "Individual", "Lote"])
        
        with tab1:
            self.show_books_list(books)
        
        with tab2:
            self.process_individual(books)
        
        with tab3:
            self.process_batch(books)
    
    def show_books_list(self, books):
        """Mostra lista de livros"""
        # Filtros simples
        colf1, colf2, colf3 = st.columns([3, 1, 1])
        with colf1:
            q = st.text_input("Filtro por nome", value="")
        with colf2:
            ext = st.selectbox("Extensao", ["Todos", "pdf", "epub"], index=0)
        with colf3:
            page_size = st.number_input("Itens/pagina", min_value=10, max_value=200, value=50, step=10)

        filtered = []
        q_lower = (q or "").lower()
        for b in books:
            if ext != "Todos" and b.suffix.lower() != f".{ext}":
                continue
            if q_lower and q_lower not in b.name.lower():
                continue
            filtered.append(b)

        total = len(filtered)
        page_count = max(1, (total + int(page_size) - 1) // int(page_size))
        page = st.slider("Pagina", min_value=1, max_value=page_count, value=1)
        start = (page - 1) * int(page_size)
        end = min(total, start + int(page_size))

        for i, book in enumerate(filtered[start:end], start=start):
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                st.write(f"**{book.name}**")
            with col2:
                size_mb = book.stat().st_size / (1024 * 1024)
                st.write(f"{size_mb:.1f} MB")
            with col3:
                if st.button("Processar", key=f"btn_{i}"):
                    self.process_single_book(book)
    
    def process_individual(self, books):
        """Processamento individual"""
        selected_book = st.selectbox(
            "Selecione um livro:",
            books,
            format_func=lambda x: x.name
        )
        
        algorithm = st.selectbox(
            "Algoritmo:",
            ["hybrid_orchestrator", "brazilian_specialist", "smart_inferencer"],
            format_func=lambda x: {
                "hybrid_orchestrator": "Hybrid (orquestrador)",
                "brazilian_specialist": "Brazilian (especialista)", 
                "smart_inferencer": "Smart (inferencia)"
            }[x]
        )
        
        if st.button("Processar Livro", type="primary"):
            self.process_single_book(selected_book, algorithm)
    
    def process_batch(self, books):
        """Processamento em lote"""
        st.write("Processamento em lote de todos os livros")
        
        algorithm = st.selectbox(
            "Algoritmo para todos:",
            ["hybrid_orchestrator", "brazilian_specialist"],
            key="batch_algo"
        )
        
        if st.button("Processar Todos", type="primary"):
            progress_bar = st.progress(0)
            
            for i, book in enumerate(books):
                st.write(f"Processando: {book.name}")
                success, result = self.run_algorithm(algorithm, book)
                
                if success:
                    st.success(f"Processado: {book.name}")
                else:
                    st.error(f"Erro: {book.name}: {result}")
                
                progress_bar.progress((i + 1) / len(books))
    
    def process_single_book(self, book_path, algorithm="hybrid_orchestrator"):
        """Processa um livro"""
        with st.spinner(f"Processando {book_path.name}..."):
            success, result = self.run_algorithm(algorithm, book_path)
            
            if success:
                st.success("Processado com sucesso.")
                st.code(result)
            else:
                st.error(f"Erro: {result}")
    
    def render_algorithms_info(self):
        """Info sobre algoritmos"""
        st.header("Algoritmos Disponiveis")
        
        algorithms = {
            "Hybrid Orchestrator": "Combina tecnicas e heuristicas",
            "Brazilian Specialist": "Foco em caracteristicas nacionais",
            "Smart Inferencer": "Inferencia e padroes no nome"
        }
        
        for name, desc in algorithms.items():
            st.info(f"**{name}**: {desc}")
    
    def run(self):
        """Interface principal"""
        self.render_header()

        # Menu lateral
        st.sidebar.title("Menu")
        # Permite definir a pasta de livros
        default_dir = str(self.books_dir)
        chosen_dir = st.sidebar.text_input("Pasta de livros", value=default_dir)
        chosen_path = Path(chosen_dir).expanduser()
        if chosen_path != self.books_dir:
            self.books_dir = chosen_path

        # Opcoes de varredura (scan)
        st.sidebar.subheader("Varredura (scan)")
        recursive = st.sidebar.checkbox("Recursivo", value=False)
        threads = st.sidebar.number_input("Threads", min_value=1, max_value=16, value=4)
        if st.sidebar.button("Executar varredura"):
            self._run_scan(self.books_dir, recursive=recursive, threads=int(threads))

        page = st.sidebar.radio(
            "Navegacao:",
            ["Dashboard", "Processar Livros", "Algoritmos", "Sistema"]
        )
        
        if page == "Dashboard":
            self.render_dashboard()
        elif page == "Processar Livros":
            self.render_books_section()
        elif page == "Algoritmos":
            self.render_algorithms_info()
        elif page == "Sistema":
            st.header("Sistema")
            st.write(f"Pasta de livros: `{self.books_dir}`")
            st.write(f"Total de livros: {len(self.get_books_list())}")
            if not self.books_dir.exists():
                st.warning("Pasta nao encontrada. Ajuste o caminho na barra lateral.")

    def _run_scan(self, directory: Path, recursive: bool = False, threads: int = 4):
        """Executa varredura de metadados sem renomear e atualiza os relatorios."""
        try:
            extractor = self.project_root / "src" / "gui" / "renomeia_livro_renew_v2.py"
            if not extractor.exists():
                st.error("Ferramenta de varredura nao encontrada.")
                return
            args = [sys.executable, str(extractor), str(directory)]
            if recursive:
                args.append("-r")
            args.extend(["-t", str(threads)])
            # Sem --rename: gera apenas relatorios JSON/HTML
            with st.spinner("Executando varredura..."):
                result = subprocess.run(args, capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                st.success("Varredura concluida. Atualize o Dashboard para ver os resultados.")
            else:
                st.error("Falha na varredura. Verifique os logs.")
                st.code(result.stderr or result.stdout)
        except Exception as e:
            st.error(f"Erro ao executar varredura: {e}")

def main():
    interface = RenamePDFEPUBInterface()
    interface.run()

if __name__ == "__main__":
    main()
