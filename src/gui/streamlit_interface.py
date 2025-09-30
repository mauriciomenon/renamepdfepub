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
        self.db_path = self.project_root / "metadata_cache.db"

    # --------------------------- DB helpers ---------------------------------
    def _connect_db(self):
        import sqlite3
        return sqlite3.connect(str(self.db_path))

    def _canonical_publisher(self, name: str) -> str:
        try:
            # Prefer shared normalization
            from core.normalization import canonical_publisher
            return canonical_publisher(name)
        except Exception:
            # Fallback minimal
            if not name:
                return ""
            n = name.strip()
            if not n or n.lower() == 'unknown':
                return ""
            return n

    def _query_catalog(self, filters: dict, limit: int = 200, offset: int = 0):
        if not self.db_path.exists():
            return []

    # --------------------------- Naming helpers -----------------------------
    @staticmethod
    def _clean_string_name(s: str, underscore: bool = False) -> str:
        import unicodedata
        if not s:
            return ''
        s = unicodedata.normalize('NFKD', s)
        s = s.encode('ASCII', 'ignore').decode('ASCII')
        out = ''.join(ch if (ch.isalnum() or ch in (' ', '-', '_')) else ' ' for ch in s)
        out = ' '.join(out.split())
        if underscore:
            out = out.replace(' ', '_')
        return out.strip()

    @staticmethod
    def _first_two_authors_str(authors: str) -> str:
        parts = [a.strip() for a in (authors or '').split(',') if a.strip()]
        return ', '.join(parts[:2]) if parts else ''

    def _build_name_from_row(self, row: dict, pattern: str, underscore: bool) -> str:
        title = row.get('Título') or ''
        if str(title).lower() == 'unknown':
            title = ''
        authors = row.get('Autores') or ''
        if str(authors).lower() == 'unknown':
            authors = ''
        publisher = row.get('Editora') or ''
        if str(publisher).lower() == 'unknown':
            publisher = ''
        year = row.get('Ano') or ''
        if str(year).lower() == 'unknown':
            year = ''
        isbn = row.get('ISBN-13') or row.get('ISBN-10') or ''
        author_disp = self._first_two_authors_str(authors)
        return pattern.format(
            title=self._clean_string_name(title, underscore),
            author=self._clean_string_name(author_disp, underscore),
            year=self._clean_string_name(year, underscore),
            publisher=self._clean_string_name(publisher, underscore),
            isbn=self._clean_string_name(isbn, underscore)
        ).strip()
        where = []
        params = []
        def like(field, value):
            where.append(f"{field} LIKE ?")
            params.append(f"%{value}%")
        if filters.get('q_title'):
            like('title', filters['q_title'])
        if filters.get('q_author'):
            like('authors', filters['q_author'])
        if filters.get('q_publisher'):
            like('publisher', filters['q_publisher'])
        if filters.get('q_year'):
            like('published_date', filters['q_year'])
        if filters.get('only_isbn'):
            where.append("(COALESCE(isbn_13,'') <> '' OR COALESCE(isbn_10,'') <> '')")
        if filters.get('only_incomplete'):
            where.append("(title IS NULL OR title='' OR publisher IS NULL OR publisher='' OR publisher='Unknown' OR authors IS NULL OR authors='' OR published_date IS NULL OR published_date='' OR published_date='Unknown')")
        sql = """
            SELECT isbn_10, isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp
            FROM metadata_cache
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        try:
            with self._connect_db() as conn:
                cur = conn.execute(sql, params)
                rows = cur.fetchall()
            results = []
            for r in rows:
                isbn10, isbn13, title, authors, publisher, published_date, conf, source, fpath, ts = r
                display_publisher = self._canonical_publisher(publisher or '')
                display_authors = authors or ''
                if display_authors.lower() == 'unknown':
                    display_authors = ''
                display_title = title or ''
                if display_title.lower() == 'unknown':
                    display_title = ''
                display_year = (published_date or '')
                if display_year.lower() == 'unknown':
                    display_year = ''
                results.append({
                    'ISBN-13': isbn13 or '',
                    'ISBN-10': isbn10 or '',
                    'Título': display_title,
                    'Autores': display_authors,
                    'Editora': display_publisher,
                    'Ano': display_year,
                    'Confiança': conf or 0.0,
                    'Fonte': source or '',
                    'Arquivo': fpath or ''
                })
            return results
        except Exception:
            return []

    @staticmethod
    def _open_in_os(path: str) -> bool:
        """Abre a pasta do arquivo no SO (local)."""
        import platform, subprocess
        try:
            p = Path(path)
            if not p.exists():
                return False
            system = platform.system().lower()
            folder = str(p.parent)
            if 'darwin' in system or 'mac' in system:
                subprocess.Popen(['open', folder])
            elif 'windows' in system:
                subprocess.Popen(['explorer', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
            return True
        except Exception:
            return False

    @staticmethod
    def _open_file_os(path: str) -> bool:
        """Abre o arquivo no SO (local)."""
        import platform, subprocess
        try:
            p = Path(path)
            if not p.exists():
                return False
            system = platform.system().lower()
            if 'darwin' in system or 'mac' in system:
                subprocess.Popen(['open', str(p)])
            elif 'windows' in system:
                subprocess.Popen(['explorer', str(p)])
            else:
                subprocess.Popen(['xdg-open', str(p)])
            return True
        except Exception:
            return False

    def _query_incomplete(self, limit: int = 200, pub_filter: str = '', year_filter: str = '', title_filter: str = '', author_filter: str = ''):
        """Retorna registros com campos faltantes (para export/inspeção)."""
        if not self.db_path.exists():
            return []
        where = (
            "SELECT isbn_13, isbn_10, title, authors, publisher, published_date, "
            "confidence_score, source, file_path, timestamp "
            "FROM metadata_cache WHERE "
            "(title IS NULL OR title='' OR title='Unknown' "
            "OR authors IS NULL OR authors='' OR authors='Unknown' "
            "OR publisher IS NULL OR publisher='' OR publisher='Unknown' "
            "OR published_date IS NULL OR published_date='' OR published_date='Unknown')"
        )
        filters = []
        params = []
        if pub_filter.strip():
            filters.append("publisher LIKE ?")
            params.append(f"%{pub_filter.strip()}%")
        if year_filter.strip():
            filters.append("published_date LIKE ?")
            params.append(f"%{year_filter.strip()}%")
        if title_filter.strip():
            filters.append("title LIKE ?")
            params.append(f"%{title_filter.strip()}%")
        if author_filter.strip():
            filters.append("authors LIKE ?")
            params.append(f"%{author_filter.strip()}%")
        sql = " ".join([where, ("AND " + " AND ".join(filters)) if filters else "", "ORDER BY timestamp DESC LIMIT ?"]).strip()
        params.append(int(limit))
        try:
            with self._connect_db() as conn:
                rows = conn.execute(sql, params).fetchall()
            out = []
            for r in rows:
                out.append({
                    'ISBN-13': r[0] or '',
                    'ISBN-10': r[1] or '',
                    'Título': '' if not r[2] or str(r[2]).lower() == 'unknown' else r[2],
                    'Autores': '' if not r[3] or str(r[3]).lower() == 'unknown' else r[3],
                    'Editora': self._canonical_publisher(r[4] or ''),
                    'Ano': '' if not r[5] or str(r[5]).lower() == 'unknown' else r[5],
                    'Confiança': r[6] or 0.0,
                    'Fonte': r[7] or '',
                    'Arquivo': r[8] or '',
                    'Timestamp': r[9] or 0,
                })
            return out
        except Exception:
            return []

    @staticmethod
    def _rows_to_csv(rows: list) -> str:
        if not rows:
            return ''
        import csv
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return buf.getvalue()

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
            # Mesmo sem relatório, mostrar atalhos de geração/relatórios
        else:
            # Se existir relatório, oferecer download rápido do último HTML/JSON
            try:
                htmls = sorted(self.reports_dir.glob("report_*.html"))
                jsons = sorted(self.reports_dir.glob("report_*.json"))
                st.subheader("Relatórios recentes")
                colh, colj = st.columns(2)
                with colh:
                    if htmls:
                        latest_html = htmls[-1]
                        st.caption(f"Último HTML: {latest_html.name}")
                        st.download_button(
                            label="Baixar HTML",
                            data=latest_html.read_bytes(),
                            file_name=latest_html.name,
                            mime="text/html"
                        )
                with colj:
                    if jsons:
                        latest_json = jsons[-1]
                        st.caption(f"Último JSON: {latest_json.name}")
                        st.download_button(
                            label="Baixar JSON",
                            data=latest_json.read_bytes(),
                            file_name=latest_json.name,
                            mime="application/json"
                        )
            except Exception:
                pass
            
            # Sem retorno antecipado – prossegue com estatísticas do relatório
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
        disabled_apis = live.get("disabled_apis") or []

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
        if disabled_apis:
            st.warning("APIs desabilitadas: " + ", ".join(sorted(disabled_apis)))

        st.write("Fontes")
        # Tabela simples com os principais campos
        for api, stats in sorted(per_api.items()):
            st.write(f"- {api}: {stats.get('success',0)}/{stats.get('total',0)} ({stats.get('success_rate',0.0):.1f}%) - {stats.get('avg_time',0.0):.2f}s")
            errs = stats.get('errors') or {}
            recents = stats.get('recent_errors') or []
            rfail = stats.get('recent_failures') or []
            if errs or recents or rfail:
                with st.expander(f"Detalhes de {api}"):
                    if errs:
                        st.write("Erros (contagem):")
                        for et, cnt in sorted(errs.items(), key=lambda x: x[1], reverse=True):
                            st.write(f"  - {et}: {cnt}")
                    if recents:
                        from datetime import datetime
                        st.write("Recentes:")
                        for r in recents[-10:]:
                            ts = int(r.get('ts', 0))
                            ts_h = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else '—'
                            st.write(f"  - {r.get('type','?')} @ {ts_h}")
                    if rfail:
                        from datetime import datetime
                        st.write("Falhas recentes:")
                        cols = st.columns([2,1,5,3])
                        with cols[0]:
                            st.caption("Tipo")
                        with cols[1]:
                            st.caption("Status")
                        with cols[2]:
                            st.caption("Mensagem")
                        with cols[3]:
                            st.caption("ISBN")
                        for f in rfail[-10:]:
                            c = st.columns([2,1,5,3])
                            with c[0]:
                                st.write(f.get('type',''))
                            with c[1]:
                                st.write(f.get('status',''))
                            with c[2]:
                                st.write(f.get('msg',''))
                            with c[3]:
                                st.write(f.get('isbn',''))

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

    def render_catalog(self):
        """Navegador do banco de dados (metadata_cache.db)."""
        st.header("Catálogo (DB)")
        if not self.db_path.exists():
            st.info("Banco metadata_cache.db não encontrado. Rode uma varredura para gerar dados.")
            return
        with st.expander("Filtros"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                q_title = st.text_input("Título contém", value="")
            with c2:
                q_author = st.text_input("Autor contém", value="")
            with c3:
                q_publisher = st.text_input("Editora contém", value="")
            with c4:
                q_year = st.text_input("Ano contém", value="")
            c5, c6, c7 = st.columns(3)
            with c5:
                only_isbn = st.checkbox("Somente com ISBN", value=False)
            with c6:
                only_incomplete = st.checkbox("Somente incompletos", value=False)
            with c7:
                limit = st.number_input("Limite", min_value=10, max_value=2000, value=200, step=10)
        filters = {
            'q_title': q_title.strip(),
            'q_author': q_author.strip(),
            'q_publisher': q_publisher.strip(),
            'q_year': q_year.strip(),
            'only_isbn': only_isbn,
            'only_incomplete': only_incomplete,
        }
        rows = self._query_catalog(filters, limit=int(limit), offset=0)
        st.caption(f"{len(rows)} registros")
        if rows:
            try:
                import pandas as pd
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception:
                for r in rows[:200]:
                    st.write(f"- {r['Título']} | {r['Autores']} | {r['Editora']} | {r['Ano']} | {r['ISBN-13']}")
            # Export
            csv_data = self._rows_to_csv(rows)
            st.download_button(
                label="Exportar CSV (filtros aplicados)",
                data=csv_data,
                file_name="catalogo_filtrado.csv",
                mime="text/csv"
            )
            # Pré-visualização de renome (lote)
            with st.expander("Pré-visualizar renome (lote)"):
                patt = st.text_input("Padrão", value="{title} - {author} - {year}", key="catalog_batch_pattern")
                und = st.checkbox("Usar underscore", value=False, key="catalog_batch_underscore")
                try:
                    preview_rows = []
                    for r in rows[:500]:
                        newbase = self._build_name_from_row(r, patt, und)
                        ext = Path(r.get('Arquivo','')).suffix
                        preview_rows.append({'Arquivo': r.get('Arquivo',''), 'Proposto': (newbase + ext) if newbase else ''})
                    prev_csv = self._rows_to_csv(preview_rows)
                    st.download_button(
                        label=f"Baixar pré-visualização ({len(preview_rows)} itens)",
                        data=prev_csv,
                        file_name="preview_renome.csv",
                        mime="text/csv"
                    )
                    # Aplicar a partir de CSV enviado
                    up = st.file_uploader("Enviar CSV de renome (Arquivo,Proposto)", type=['csv'])
                    if up is not None:
                        try:
                            # Salva temporário em reports/
                            save_dir = self.reports_dir
                            save_dir.mkdir(exist_ok=True)
                            tmp_csv = save_dir / 'apply_batch_renames.csv'
                            tmp_csv.write_bytes(up.read())
                            st.success(f"CSV salvo em {tmp_csv}")
                            if st.button("Aplicar renomes do CSV (em background)"):
                                script = self.project_root / 'scripts' / 'apply_renames_from_csv.py'
                                subprocess.Popen([sys.executable, str(script), '--csv', str(tmp_csv), '--apply'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                st.info("Renomeação em lote iniciada.")
                        except Exception as e:
                            st.warning(f"Falha ao processar CSV: {e}")
                except Exception as e:
                    st.caption(f"Falha na pré-visualização: {e}")
            # Abrir pasta do arquivo (por seleção)
            try:
                file_choices = [r['Arquivo'] for r in rows if r.get('Arquivo')]
                if file_choices:
                    c1, c2, c3 = st.columns([3,1,1])
                    with c1:
                        sel = st.selectbox("Selecionar arquivo:", file_choices)
                        st.text_input("Caminho (copiar)", value=sel, key="catalog_path_copy", disabled=True)
                    with c2:
                        if st.button("Abrir pasta"):
                            ok = self._open_in_os(sel)
                            if not ok:
                                st.warning("Não foi possível abrir a pasta. Verifique o caminho.")
                    with c3:
                        # Renomear agora (DB)
                        patt = st.text_input("Padrão de nome", value="{title} - {author} - {year}")
                        und = st.checkbox("Usar underscore", value=False)
                        if st.button("Renomear (DB)"):
                            script = self.project_root / 'scripts' / 'rename_from_db.py'
                            cmd = [sys.executable, str(script), '--file', sel, '--apply', '--pattern', patt]
                            if und:
                                cmd.append('--underscore')
                            try:
                                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                st.info("Renomeação iniciada (verifique pasta).")
                            except Exception as e:
                                st.warning(f"Falha ao acionar renomeação: {e}")
                        # Pré-visualizar novo nome
                        if st.button("Pré-visualizar nome"):
                            script = self.project_root / 'scripts' / 'rename_from_db.py'
                            cmd = [sys.executable, str(script), '--file', sel, '--pattern', patt]
                            if und:
                                cmd.append('--underscore')
                            try:
                                res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                                out = (res.stdout or '') + (res.stderr or '')
                                st.code(out.strip() or '(sem saída)')
                            except Exception as e:
                                st.warning(f"Falha na pré-visualização: {e}")
            except Exception:
                pass
        st.subheader("Operações")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            if st.button("Rescan cache (core)"):
                start_cli = self.project_root / 'start_cli.py'
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--rescan-cache'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Rescan iniciado em background")
        with cc2:
            thr = st.number_input("Confiança < para update-cache", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
            if st.button("Update cache (core)"):
                start_cli = self.project_root / 'start_cli.py'
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--update-cache', '--confidence-threshold', str(thr)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Update-cache iniciado em background")
        with cc3:
            if st.button("Normalizar editoras no DB"):
                try:
                    updated = 0
                    with self._connect_db() as conn:
                        cur = conn.execute("SELECT rowid, publisher FROM metadata_cache")
                        rows = cur.fetchall()
                        for rowid, pub in rows:
                            canon = self._canonical_publisher(pub or '')
                            if canon and canon != (pub or ''):
                                conn.execute("UPDATE metadata_cache SET publisher=? WHERE rowid=?", (canon, rowid))
                                updated += 1
                        conn.commit()
                    st.success(f"Editoras normalizadas: {updated} registros atualizados")
                except Exception as e:
                    st.error(f"Falha na normalização: {e}")
    
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
            [
                "Dashboard",
                "Catálogo (DB)",
                "Scan Avançado",
                "Operações em Lote",
                "Processar Livros",
                "Algoritmos",
                "Launchers",
                "Sistema"
            ]
        )
        
        if page == "Dashboard":
            self.render_dashboard()
        elif page == "Catálogo (DB)":
            self.render_catalog()
        elif page == "Scan Avançado":
            self.render_scan_advanced()
        elif page == "Operações em Lote":
            self.render_batch_ops()
        elif page == "Processar Livros":
            self.render_books_section()
        elif page == "Algoritmos":
            self.render_algorithms_info()
        elif page == "Launchers":
            self.render_launchers()
        elif page == "Sistema":
            st.header("Sistema")
            st.write(f"Pasta de livros: `{self.books_dir}`")
            st.write(f"Total de livros: {len(self.get_books_list())}")
            if not self.books_dir.exists():
                st.warning("Pasta nao encontrada. Ajuste o caminho na barra lateral.")

    def _run_scan(self, directory: Path, recursive: bool = False, threads: int = 4):
        """Executa varredura de metadados sem renomear e atualiza os relatorios."""
        try:
            start_cli = self.project_root / "start_cli.py"
            if not start_cli.exists():
                st.error("start_cli.py nao encontrado.")
                return
            args = [sys.executable, str(start_cli), 'scan', str(directory)]
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

    def render_db_gaps(self):
        """Resumo de campos faltantes + ações de recuperação"""
        st.header("Caça-Furos (DB)")
        if not self.db_path.exists():
            st.info("Banco metadata_cache.db não encontrado. Rode uma varredura para gerar dados.")
            return
        try:
            with self._connect_db() as conn:
                def _count(sql: str) -> int:
                    return conn.execute(sql).fetchone()[0]
                total = _count("SELECT COUNT(*) FROM metadata_cache")
                missing_title = _count("SELECT COUNT(*) FROM metadata_cache WHERE title IS NULL OR title='' OR title='Unknown'")
                missing_auth = _count("SELECT COUNT(*) FROM metadata_cache WHERE authors IS NULL OR authors='' OR authors='Unknown'")
                missing_pub = _count("SELECT COUNT(*) FROM metadata_cache WHERE publisher IS NULL OR publisher='' OR publisher='Unknown'")
                missing_year = _count("SELECT COUNT(*) FROM metadata_cache WHERE published_date IS NULL OR published_date='' OR published_date='Unknown'")
                missing_isbn = _count("SELECT COUNT(*) FROM metadata_cache WHERE (COALESCE(isbn_13,'')='' AND COALESCE(isbn_10,'')='')")
        except Exception as e:
            st.error(f"Erro ao consultar DB: {e}")
            return
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Registros", total)
        c2.metric("Sem título", missing_title)
        c3.metric("Sem autores", missing_auth)
        c4.metric("Sem editora", missing_pub)
        c5.metric("Sem ano", missing_year)
        st.metric(label="Sem ISBN (10/13)", value=missing_isbn)

        st.subheader("Ações de recuperação")
        a1, a2, a3 = st.columns(3)
        start_cli = self.project_root / 'start_cli.py'
        with a1:
            if st.button("Tentar completar (update-cache, confiança<0.99)"):
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--update-cache', '--confidence-threshold', '0.99'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Atualização iniciada. Acompanhe no Dashboard.")
        with a2:
            if st.button("Reprocessar tudo (rescan-cache)"):
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--rescan-cache'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Rescan-cache iniciado.")
        with a3:
            limit = st.number_input("Limite (apenas mostrados)", min_value=10, max_value=5000, value=500, step=10)
            f1, f2 = st.columns(2)
            with f1:
                f_pub = st.text_input("Filtro editora contém", value="")
            with f2:
                f_year = st.text_input("Filtro ano contém", value="")
            f3, f4 = st.columns(2)
            with f3:
                f_title = st.text_input("Filtro título contém", value="")
            with f4:
                f_author = st.text_input("Filtro autor contém", value="")
            if st.button("Atualizar apenas mostrados"):
                script = self.project_root / 'scripts' / 'update_cache_filtered.py'
                cmd = [sys.executable, str(script), '--only-incomplete', '--limit', str(int(limit))]
                if f_pub.strip():
                    cmd += ['--publisher', f_pub.strip()]
                if f_year.strip():
                    cmd += ['--year', f_year.strip()]
                if f_title.strip():
                    cmd += ['--title', f_title.strip()]
                if f_author.strip():
                    cmd += ['--author', f_author.strip()]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Atualização filtrada iniciada.")
        st.subheader("Exportar incompletos")
        # Export respects the same filters
        inc_rows = self._query_incomplete(
            limit=2000,
            pub_filter=f_pub if 'f_pub' in locals() else '',
            year_filter=f_year if 'f_year' in locals() else '',
            title_filter=f_title if 'f_title' in locals() else '',
            author_filter=f_author if 'f_author' in locals() else ''
        )
        if inc_rows:
            csv_inc = self._rows_to_csv(inc_rows)
            st.download_button(
                label=f"Exportar {len(inc_rows)} registros incompletos (CSV)",
                data=csv_inc,
                file_name="incompletos.csv",
                mime="text/csv"
            )
            # Abrir pasta/arquivo
            try:
                file_choices = [r['Arquivo'] for r in inc_rows if r.get('Arquivo')]
                if file_choices:
                    c1, c2, c3, c4 = st.columns([3,1,1,1])
                    with c1:
                        sel = st.selectbox("Selecionar arquivo:", file_choices)
                        st.text_input("Caminho (copiar)", value=sel, key="gaps_path_copy", disabled=True)
                    with c2:
                        if st.button("Abrir pasta"):
                            ok = self._open_in_os(sel)
                            if not ok:
                                st.warning("Não foi possível abrir a pasta.")
                    with c3:
                        if st.button("Abrir arquivo"):
                            ok = self._open_file_os(sel)
                            if not ok:
                                st.warning("Não foi possível abrir o arquivo.")
                    with c4:
                        # Ações de renome
                        script = self.project_root / 'scripts' / 'rename_from_db.py'
                        b1, b2 = st.columns(2)
                        with b1:
                            patt2 = st.text_input("Padrão de nome", value="{title} - {author} - {year}", key="gaps_pattern")
                            und2 = st.checkbox("Usar underscore", value=False, key="gaps_underscore")
                            if st.button("Pré-visualizar nome (DB)"):
                                try:
                                    cmd = [sys.executable, str(script), '--file', sel, '--pattern', patt2]
                                    if und2:
                                        cmd.append('--underscore')
                                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                                    out = (res.stdout or '') + (res.stderr or '')
                                    st.code(out.strip() or '(sem saída)')
                                except Exception as e:
                                    st.warning(f"Falha na pré-visualização: {e}")
                        with b2:
                            if st.button("Renomear (DB)"):
                                try:
                                    cmd = [sys.executable, str(script), '--file', sel, '--apply', '--pattern', patt2]
                                    if und2:
                                        cmd.append('--underscore')
                                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    st.info("Renomeação iniciada (verifique pasta).")
                                except Exception as e:
                                    st.warning(f"Falha ao acionar renomeação: {e}")
            except Exception:
                pass
            # Pré-visualização de renome (lote)
            with st.expander("Pré-visualizar renome (lote)"):
                patt = st.text_input("Padrão", value="{title} - {author} - {year}", key="gaps_batch_pattern")
                und = st.checkbox("Usar underscore", value=False, key="gaps_batch_underscore2")
                try:
                    preview_rows = []
                    for r in inc_rows[:500]:
                        newbase = self._build_name_from_row(r, patt, und)
                        ext = Path(r.get('Arquivo','')).suffix
                        preview_rows.append({'Arquivo': r.get('Arquivo',''), 'Proposto': (newbase + ext) if newbase else ''})
                    prev_csv = self._rows_to_csv(preview_rows)
                    st.download_button(
                        label=f"Baixar pré-visualização ({len(preview_rows)} itens)",
                        data=prev_csv,
                        file_name="preview_renome_incompletos.csv",
                        mime="text/csv"
                    )
                    up = st.file_uploader("Enviar CSV de renome (Arquivo,Proposto)", type=['csv'], key="gaps_upload_csv")
                    if up is not None:
                        try:
                            save_dir = self.reports_dir
                            save_dir.mkdir(exist_ok=True)
                            tmp_csv = save_dir / 'apply_batch_renames_incompletos.csv'
                            tmp_csv.write_bytes(up.read())
                            st.success(f"CSV salvo em {tmp_csv}")
                            if st.button("Aplicar renomes do CSV (em background)", key="gaps_apply_csv_btn"):
                                script = self.project_root / 'scripts' / 'apply_renames_from_csv.py'
                                subprocess.Popen([sys.executable, str(script), '--csv', str(tmp_csv), '--apply'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                st.info("Renomeação em lote iniciada.")
                        except Exception as e:
                            st.warning(f"Falha ao processar CSV: {e}")
                except Exception as e:
                    st.caption(f"Falha na pré-visualização: {e}")
        else:
            st.caption("Nenhum registro incompleto encontrado (ou DB ausente)")

    # ----------------------- New advanced/ops pages -------------------------
    def render_scan_advanced(self):
        st.header("Scan Avançado (Core)")
        c1, c2, c3 = st.columns(3)
        with c1:
            directory = st.text_input("Diretório", value=str(self.books_dir))
            recursive = st.checkbox("Recursivo", value=False)
            subdirs = st.text_input("Subdirs (sep por vírgula)", value="")
        with c2:
            threads = st.number_input("Threads", min_value=1, max_value=32, value=4)
            output = st.text_input("JSON de saída (opcional)", value="")
            rename = st.checkbox("Renomear após scan", value=False)
        with c3:
            cycles = st.number_input("scan-cycles: ciclos", min_value=1, max_value=100, value=3)
            time_secs = st.number_input("scan-cycles: tempo (s)", min_value=0, max_value=36000, value=0)

        start_cli = self.project_root / 'start_cli.py'
        if not start_cli.exists():
            st.error("start_cli.py não encontrado")
            return

        def _args_base():
            args = [sys.executable, str(start_cli), 'scan', directory]
            if recursive:
                args.append('-r')
            if subdirs.strip():
                args += ['--subdirs', subdirs]
            args += ['-t', str(int(threads))]
            if output.strip():
                args += ['-o', output]
            if rename:
                args.append('--rename')
            return args

        st.subheader("Executar")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Scan agora"):
                subprocess.Popen(_args_base(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Scan iniciado em background")
        with b2:
            if st.button("Scan-cycles agora"):
                cyc = [sys.executable, str(start_cli), 'scan-cycles', directory, '--cycles', str(int(cycles)), '-t', str(int(threads))]
                if time_secs > 0:
                    cyc += ['--time-seconds', str(int(time_secs))]
                subprocess.Popen(cyc, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Scan-cycles iniciado em background")
        with b3:
            if st.button("Abrir relatório (último)"):
                st.write("Abra a aba Dashboard; ele busca o JSON/HTML mais recente em reports/.")

        st.subheader("Manutenção do Cache")
        m1, m2 = st.columns(2)
        with m1:
            if st.button("Rescan-cache (core)"):
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--rescan-cache'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Rescan-cache iniciado.")
        with m2:
            thr = st.number_input("Update-cache: confiança <", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
            if st.button("Update-cache (core)"):
                subprocess.Popen([sys.executable, str(start_cli), 'scan', '--update-cache', '--confidence-threshold', str(thr)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Update-cache iniciado.")

    def render_batch_ops(self):
        st.header("Operações em Lote")
        st.caption("Ações de batch para muitos arquivos/relatórios, sem precisar saber comandos.")
        # Rename-existing
        re_col1, re_col2 = st.columns([3,1])
        with re_col1:
            report_path = st.text_input("Relatório JSON para renomear (rename-existing)", value="")
        with re_col2:
            apply = st.checkbox("Aplicar (mover)", value=False)
            copy = st.checkbox("Copiar", value=False)
        if st.button("Executar rename-existing"):
            if not report_path.strip():
                st.warning("Informe o caminho do relatório JSON.")
            else:
                cmd = [sys.executable, str(self.project_root / 'start_cli.py'), 'rename-existing', '--report', report_path]
                if apply:
                    cmd.append('--apply')
                if copy:
                    cmd.append('--copy')
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("rename-existing iniciado em background")

        st.markdown("---")
        # Rename-search
        rs_col1, rs_col2 = st.columns([3,1])
        with rs_col1:
            rs_dir = st.text_input("Diretório para rename-search", value=str(self.books_dir))
        with rs_col2:
            rs_rename = st.checkbox("Renomear", value=True)
        if st.button("Executar rename-search"):
            cmd = [sys.executable, str(self.project_root / 'start_cli.py'), 'rename-search', rs_dir]
            if rs_rename:
                cmd.append('--rename')
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            st.info("rename-search iniciado em background")

        st.markdown("---")
        # Normalizar editoras
        st.subheader("Normalização de Editoras (DB)")
        nb1, nb2 = st.columns(2)
        with nb1:
            if st.button("Dry-run (mostrar alterações)"):
                subprocess.Popen([sys.executable, str(self.project_root / 'scripts' / 'normalize_publishers.py'), '--dry-run'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Dry-run iniciado (veja saída no terminal).")
        with nb2:
            if st.button("Aplicar (backup automático)"):
                subprocess.Popen([sys.executable, str(self.project_root / 'scripts' / 'normalize_publishers.py'), '--apply'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info("Normalização iniciada.")

    def render_launchers(self):
        st.header("Launchers")
        st.caption("Acesso fácil a todas as interfaces e ferramentas.")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Abrir Streamlit (este)"):
                st.info("Você já está na interface Streamlit.")
        with c2:
            if st.button("Launcher Web"):
                subprocess.Popen([sys.executable, str(self.project_root / 'start_web.py')])
        with c3:
            if st.button("Launcher PyQt6"):
                subprocess.Popen([sys.executable, str(self.project_root / 'scripts' / 'launcher_pyqt6.py')])

def main():
    interface = RenamePDFEPUBInterface()
    interface.run()

if __name__ == "__main__":
    main()
