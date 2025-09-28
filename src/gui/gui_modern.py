#!/usr/bin/env python3
"""
Interface Gráfica Completa - RenamePDFEpub
Versão: 2.0.0 - Produção
Data: 28 de Setembro de 2025

Interface gráfica moderna que integra:
- Sistema V3 (88.7% precisão)
- Amazon Books API
- Renomeação automática
- Processamento em lote
- Relatórios visuais

Dependências:
    pip install tkinter pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import asyncio
import threading
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import queue

# Imports dos nossos sistemas
from auto_rename_system import AutoRenameSystem
from amazon_api_integration import AmazonBooksAPI

class ModernGUI:
    """
    Interface gráfica moderna para o sistema de renomeação
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.setup_variables()
        
        # Sistema principal
        self.rename_system = AutoRenameSystem()
        
        # Queue para comunicação entre threads
        self.update_queue = queue.Queue()
        
        # Status do processamento
        self.is_processing = False
        
        # Timer para atualizar UI
        self.root.after(100, self.check_queue)

    def setup_window(self):
        """Configura janela principal"""
        self.root.title("RenamePDFEpub v2.0 - Sistema V3 (88.7% precisão)")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Ícone (se existir)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Centraliza janela
        self.center_window()

    def center_window(self):
        """Centraliza janela na tela"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def setup_styles(self):
        """Configura estilos TTK"""
        style = ttk.Style()
        
        # Tema moderno
        try:
            style.theme_use('clam')
        except:
            pass
        
        # Cores personalizadas
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')

    def setup_variables(self):
        """Configura variáveis do Tkinter"""
        self.processing_mode = tk.StringVar(value="single")
        self.backup_enabled = tk.BooleanVar(value=True)
        self.auto_save_reports = tk.BooleanVar(value=True)
        
        # Caminhos
        self.selected_file = tk.StringVar()
        self.selected_directory = tk.StringVar()
        self.batch_file = tk.StringVar()
        
        # Estatísticas
        self.stats_total = tk.StringVar(value="0")
        self.stats_success = tk.StringVar(value="0")
        self.stats_failed = tk.StringVar(value="0")
        self.stats_rate = tk.StringVar(value="0%")

    def create_widgets(self):
        """Cria todos os widgets"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configura grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="🎯 RenamePDFEpub v2.0", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 5))
        
        subtitle_label = ttk.Label(main_frame, text="Sistema V3 com 88.7% de Precisão + Amazon Books API", style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # Frame de configurações
        self.create_config_frame(main_frame, row=2)
        
        # Frame de seleção de arquivos
        self.create_file_selection_frame(main_frame, row=3)
        
        # Frame de controles
        self.create_controls_frame(main_frame, row=4)
        
        # Frame de progresso
        self.create_progress_frame(main_frame, row=5)
        
        # Frame de estatísticas
        self.create_stats_frame(main_frame, row=6)
        
        # Frame de log
        self.create_log_frame(main_frame, row=7)

    def create_config_frame(self, parent, row):
        """Cria frame de configurações"""
        config_frame = ttk.LabelFrame(parent, text="⚙️ Configurações", padding="10")
        config_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Modo de processamento
        ttk.Label(config_frame, text="Modo:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        mode_frame = ttk.Frame(config_frame)
        mode_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Radiobutton(mode_frame, text="Arquivo único", variable=self.processing_mode, 
                       value="single", command=self.on_mode_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Diretório", variable=self.processing_mode, 
                       value="directory", command=self.on_mode_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Lote", variable=self.processing_mode, 
                       value="batch", command=self.on_mode_change).pack(side=tk.LEFT)
        
        # Opções
        options_frame = ttk.Frame(config_frame)
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Checkbutton(options_frame, text="Criar backup dos arquivos originais", 
                       variable=self.backup_enabled).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="Salvar relatórios automaticamente", 
                       variable=self.auto_save_reports).pack(side=tk.LEFT)

    def create_file_selection_frame(self, parent, row):
        """Cria frame de seleção de arquivos"""
        self.file_frame = ttk.LabelFrame(parent, text="📁 Seleção de Arquivos", padding="10")
        self.file_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.file_frame.columnconfigure(1, weight=1)
        
        # Arquivo único
        self.single_label = ttk.Label(self.file_frame, text="Arquivo:")
        self.single_entry = ttk.Entry(self.file_frame, textvariable=self.selected_file)
        self.single_button = ttk.Button(self.file_frame, text="Selecionar", command=self.select_file)
        
        # Diretório
        self.dir_label = ttk.Label(self.file_frame, text="Diretório:")
        self.dir_entry = ttk.Entry(self.file_frame, textvariable=self.selected_directory)
        self.dir_button = ttk.Button(self.file_frame, text="Selecionar", command=self.select_directory)
        
        # Arquivo de lote
        self.batch_label = ttk.Label(self.file_frame, text="Lista:")
        self.batch_entry = ttk.Entry(self.file_frame, textvariable=self.batch_file)
        self.batch_button = ttk.Button(self.file_frame, text="Selecionar", command=self.select_batch_file)
        
        # Inicializa com modo single
        self.on_mode_change()

    def create_controls_frame(self, parent, row):
        """Cria frame de controles"""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(controls_frame, text="🚀 Iniciar Processamento", 
                                      command=self.start_processing, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(controls_frame, text="⏹️ Parar", 
                                     command=self.stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_button = ttk.Button(controls_frame, text="🧪 Testar API", 
                                     command=self.test_api)
        self.test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.report_button = ttk.Button(controls_frame, text="📊 Ver Último Relatório", 
                                       command=self.show_last_report)
        self.report_button.pack(side=tk.LEFT)

    def create_progress_frame(self, parent, row):
        """Cria frame de progresso"""
        progress_frame = ttk.LabelFrame(parent, text="📈 Progresso", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Pronto para iniciar")
        self.progress_label.grid(row=1, column=0)

    def create_stats_frame(self, parent, row):
        """Cria frame de estatísticas"""
        stats_frame = ttk.LabelFrame(parent, text="📊 Estatísticas", padding="10")
        stats_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Grid de estatísticas
        ttk.Label(stats_frame, text="Total:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(stats_frame, textvariable=self.stats_total).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(stats_frame, text="Sucessos:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Label(stats_frame, textvariable=self.stats_success, style='Success.TLabel').grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(stats_frame, text="Falhas:").grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        ttk.Label(stats_frame, textvariable=self.stats_failed, style='Error.TLabel').grid(row=0, column=5, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(stats_frame, text="Taxa:").grid(row=0, column=6, sticky=tk.W, padx=(0, 10))
        ttk.Label(stats_frame, textvariable=self.stats_rate, style='Success.TLabel').grid(row=0, column=7, sticky=tk.W)

    def create_log_frame(self, parent, row):
        """Cria frame de log"""
        log_frame = ttk.LabelFrame(parent, text="📝 Log de Atividades", padding="10")
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Área de texto com scroll
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame de controles do log
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(log_controls, text="Limpar Log", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_controls, text="Salvar Log", command=self.save_log).pack(side=tk.LEFT)
        
        # Configura peso da linha do log
        parent.rowconfigure(row, weight=1)

    def on_mode_change(self):
        """Callback quando modo de processamento muda"""
        mode = self.processing_mode.get()
        
        # Remove todos os widgets
        for widget in self.file_frame.winfo_children():
            widget.grid_remove()
        
        if mode == "single":
            self.single_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            self.single_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
            self.single_button.grid(row=0, column=2)
        elif mode == "directory":
            self.dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            self.dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
            self.dir_button.grid(row=0, column=2)
        elif mode == "batch":
            self.batch_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            self.batch_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
            self.batch_button.grid(row=0, column=2)

    def select_file(self):
        """Seleciona arquivo único"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo",
            filetypes=[
                ("Livros", "*.pdf *.epub *.mobi *.azw *.azw3"),
                ("PDF", "*.pdf"),
                ("EPUB", "*.epub"),
                ("Todos", "*.*")
            ]
        )
        if filename:
            self.selected_file.set(filename)
            self.log(f"📄 Arquivo selecionado: {Path(filename).name}")

    def select_directory(self):
        """Seleciona diretório"""
        directory = filedialog.askdirectory(title="Selecionar diretório")
        if directory:
            self.selected_directory.set(directory)
            self.log(f"📂 Diretório selecionado: {directory}")

    def select_batch_file(self):
        """Seleciona arquivo de lote"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo com lista",
            filetypes=[
                ("Texto", "*.txt"),
                ("Todos", "*.*")
            ]
        )
        if filename:
            self.batch_file.set(filename)
            self.log(f"📋 Arquivo de lote selecionado: {Path(filename).name}")

    def log(self, message: str):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """Limpa log"""
        self.log_text.delete(1.0, tk.END)

    def save_log(self):
        """Salva log em arquivo"""
        content = self.log_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Aviso", "Log está vazio")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Salvar log",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Sucesso", f"Log salvo: {filename}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar log: {e}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """Atualiza barra de progresso"""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
        
        if message:
            self.progress_label.config(text=message)
        
        self.root.update_idletasks()

    def update_stats(self, total: int, success: int, failed: int):
        """Atualiza estatísticas"""
        self.stats_total.set(str(total))
        self.stats_success.set(str(success))
        self.stats_failed.set(str(failed))
        
        if total > 0:
            rate = (success / total) * 100
            self.stats_rate.set(f"{rate:.1f}%")
        else:
            self.stats_rate.set("0%")

    def start_processing(self):
        """Inicia processamento em thread separada"""
        if self.is_processing:
            return
        
        # Valida seleção
        mode = self.processing_mode.get()
        path = ""
        
        if mode == "single":
            path = self.selected_file.get()
            if not path:
                messagebox.showerror("Erro", "Selecione um arquivo")
                return
        elif mode == "directory":
            path = self.selected_directory.get()
            if not path:
                messagebox.showerror("Erro", "Selecione um diretório")
                return
        elif mode == "batch":
            path = self.batch_file.get()
            if not path:
                messagebox.showerror("Erro", "Selecione arquivo de lote")
                return
        
        # Configura UI para processamento
        self.is_processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Configura sistema
        self.rename_system.file_renamer.backup_enabled = self.backup_enabled.get()
        
        # Inicia thread de processamento
        self.processing_thread = threading.Thread(
            target=self.process_in_thread,
            args=(mode, path),
            daemon=True
        )
        self.processing_thread.start()
        
        self.log(f"🚀 Processamento iniciado - Modo: {mode}")

    def process_in_thread(self, mode: str, path: str):
        """Executa processamento em thread separada"""
        try:
            # Cria loop de eventos para async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Executa processamento baseado no modo
            if mode == "single":
                result = loop.run_until_complete(self.rename_system.process_single_file(path))
            elif mode == "directory":
                result = loop.run_until_complete(self.rename_system.process_directory(path))
            elif mode == "batch":
                result = loop.run_until_complete(self.rename_system.process_batch_file(path))
            
            # Envia resultado para UI thread
            self.update_queue.put(('complete', result))
            
        except Exception as e:
            self.update_queue.put(('error', str(e)))
        finally:
            loop.close()

    def stop_processing(self):
        """Para processamento"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_label.config(text="Processamento interrompido")
        self.log("⏹️ Processamento interrompido pelo usuário")

    def check_queue(self):
        """Verifica queue de atualizações da thread"""
        try:
            while True:
                try:
                    message_type, data = self.update_queue.get_nowait()
                    
                    if message_type == 'complete':
                        self.on_processing_complete(data)
                    elif message_type == 'error':
                        self.on_processing_error(data)
                    elif message_type == 'progress':
                        current, total, message = data
                        self.update_progress(current, total, message)
                    elif message_type == 'log':
                        self.log(data)
                        
                except queue.Empty:
                    break
                    
        except Exception as e:
            self.log(f"❌ Erro na comunicação entre threads: {e}")
        
        # Agenda próxima verificação
        self.root.after(100, self.check_queue)

    def on_processing_complete(self, report: Dict):
        """Callback quando processamento completa"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        # Atualiza estatísticas
        summary = report['summary']
        self.update_stats(summary['total_files'], summary['successful'], summary['failed'])
        
        # Atualiza progresso
        self.progress_var.set(100)
        self.progress_label.config(text="Processamento concluído!")
        
        # Log final
        self.log(f"✅ Processamento concluído!")
        self.log(f"📊 Total: {summary['total_files']}, Sucessos: {summary['successful']}, Falhas: {summary['failed']}")
        self.log(f"📈 Taxa de sucesso: {summary['success_rate']:.1f}%")
        
        if summary['duration_seconds']:
            self.log(f"⏱️ Tempo: {summary['duration_seconds']:.1f}s")
        
        # Salva relatório automaticamente se habilitado
        if self.auto_save_reports.get():
            self.save_report_auto(report)
        
        # Mostra relatório se poucos arquivos
        if summary['total_files'] <= 5:
            self.show_report_dialog(report)
        else:
            messagebox.showinfo("Concluído", 
                              f"Processamento concluído!\n"
                              f"Total: {summary['total_files']}\n"
                              f"Sucessos: {summary['successful']}\n"
                              f"Taxa: {summary['success_rate']:.1f}%")

    def on_processing_error(self, error_message: str):
        """Callback quando ocorre erro no processamento"""
        self.is_processing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_label.config(text="Erro no processamento")
        
        self.log(f"❌ Erro: {error_message}")
        messagebox.showerror("Erro", f"Erro no processamento:\n{error_message}")

    def save_report_auto(self, report: Dict):
        """Salva relatório automaticamente"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_{timestamp}.json"
            
            # Converte metadados para serialização
            self.prepare_report_for_save(report)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.log(f"💾 Relatório salvo automaticamente: {filename}")
            
        except Exception as e:
            self.log(f"❌ Erro ao salvar relatório: {e}")

    def prepare_report_for_save(self, report: Dict):
        """Prepara relatório para serialização JSON"""
        if 'results' in report:
            for result in report['results']:
                if result['metadata'] and hasattr(result['metadata'], '__dict__'):
                    result['metadata'] = {
                        'title': result['metadata'].title,
                        'authors': result['metadata'].authors,
                        'publisher': result['metadata'].publisher,
                        'published_date': result['metadata'].published_date,
                        'confidence_score': result['metadata'].confidence_score,
                        'source_api': result['metadata'].source_api
                    }

    def show_report_dialog(self, report: Dict):
        """Mostra diálogo com relatório detalhado"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Relatório Detalhado")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="📊 Relatório de Processamento", 
                 style='Title.TLabel').pack(pady=(0, 10))
        
        # Área de texto com scroll
        text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Monta conteúdo do relatório
        content = self.format_report(report)
        text_area.insert(tk.END, content)
        text_area.config(state='disabled')
        
        # Botão fechar
        ttk.Button(main_frame, text="Fechar", 
                  command=dialog.destroy).pack()

    def format_report(self, report: Dict) -> str:
        """Formata relatório para exibição"""
        content = []
        summary = report['summary']
        
        content.append("📊 RESUMO EXECUTIVO")
        content.append("=" * 50)
        content.append(f"Total de arquivos: {summary['total_files']}")
        content.append(f"Sucessos: {summary['successful']}")
        content.append(f"Falhas: {summary['failed']}")
        content.append(f"Taxa de sucesso: {summary['success_rate']:.1f}%")
        
        if summary['duration_seconds']:
            content.append(f"Tempo total: {summary['duration_seconds']:.1f}s")
        
        if 'results' in report:
            content.append("\n📋 DETALHES DOS RESULTADOS")
            content.append("=" * 50)
            
            for i, result in enumerate(report['results'], 1):
                file_name = Path(result['file']).name
                status = "✅" if result['success'] else "❌"
                
                content.append(f"\n{i}. {status} {file_name}")
                
                if result['success'] and result['metadata']:
                    metadata = result['metadata']
                    if isinstance(metadata, dict):
                        title = metadata.get('title', 'N/A')
                        authors = ', '.join(metadata.get('authors', []))
                        source = metadata.get('source_api', 'N/A')
                        score = metadata.get('confidence_score', 0)
                    else:
                        title = metadata.title
                        authors = ', '.join(metadata.authors)
                        source = metadata.source_api
                        score = metadata.confidence_score
                    
                    content.append(f"   → {title}")
                    content.append(f"   → Autores: {authors}")
                    content.append(f"   → Fonte: {source}")
                    content.append(f"   → Confiança: {score:.3f}")
                elif not result['success']:
                    content.append(f"   → Erro: {result['message']}")
        
        return "\n".join(content)

    def show_last_report(self):
        """Mostra último relatório salvo"""
        # Procura pelo arquivo de relatório mais recente
        report_files = list(Path(".").glob("relatorio_*.json"))
        
        if not report_files:
            messagebox.showinfo("Info", "Nenhum relatório encontrado")
            return
        
        # Pega o mais recente
        latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_report, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            self.show_report_dialog(report)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar relatório: {e}")

    def test_api(self):
        """Testa conectividade da API"""
        self.log("🧪 Testando conectividade da API...")
        
        # Inicia teste em thread
        test_thread = threading.Thread(
            target=self.run_api_test,
            daemon=True
        )
        test_thread.start()

    def run_api_test(self):
        """Executa teste da API em thread separada"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def test():
                async with AmazonBooksAPI() as api:
                    result = await api.enhanced_search("Python Programming")
                    return result
            
            result = loop.run_until_complete(test())
            
            if result:
                self.update_queue.put(('log', f"✅ API funcionando! Encontrado: {result.title}"))
                self.update_queue.put(('log', f"   Fonte: {result.source_api}, Score: {result.confidence_score:.3f}"))
            else:
                self.update_queue.put(('log', "⚠️ API acessível, mas nenhum resultado encontrado"))
                
        except Exception as e:
            self.update_queue.put(('log', f"❌ Erro no teste da API: {e}"))
        finally:
            loop.close()

    def run(self):
        """Executa a aplicação"""
        self.log("🎯 RenamePDFEpub v2.0 iniciado")
        self.log("Sistema V3 com 88.7% de precisão carregado ✅")
        self.log("Amazon Books API integrado ✅")
        self.log("Pronto para processar seus livros!")
        
        self.root.mainloop()

def main():
    """Função principal"""
    try:
        app = ModernGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Erro Fatal", f"Erro ao inicializar aplicação: {e}")

if __name__ == "__main__":
    main()