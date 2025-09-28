#!/usr/bin/env python3
"""
Interface Web Streamlit - RenamePDFEPUB
=====================================

Interface moderna e interativa para o sistema de algoritmos
"""

import streamlit as st
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Configuração da página
st.set_page_config(
    page_title="RenamePDFEPUB - Sistema de Algoritmos",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para interface mais bonita
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .algorithm-card {
        border: 2px solid #e1e8ed;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .success-card {
        border-left: 5px solid #27ae60;
        background-color: #d5f4e6;
    }
    
    .warning-card {
        border-left: 5px solid #f39c12;
        background-color: #fef5e7;
    }
    
    .info-card {
        border-left: 5px solid #3498db;
        background-color: #ebf3fd;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

class StreamlitInterface:
    """Interface Streamlit para o sistema de algoritmos"""
    
    def __init__(self):
        self.algorithm_colors = {
            'Basic Parser': '#FF6B6B',
            'Enhanced Parser': '#4ECDC4', 
            'Smart Inferencer': '#45B7D1',
            'Hybrid Orchestrator': '#96CEB4',
            'Brazilian Specialist': '#FFEAA7'
        }
        
        self.algorithm_descriptions = {
            'Basic Parser': 'Extração básica de metadados usando regex e parsing simples',
            'Enhanced Parser': 'Parser aprimorado com limpeza de dados e validação',
            'Smart Inferencer': 'Inferência inteligente usando padrões e heurísticas',
            'Hybrid Orchestrator': 'Combina múltiplas técnicas para máxima precisão',
            'Brazilian Specialist': 'Especializado em livros nacionais e editoras brasileiras'
        }

    def load_results(self) -> Dict[str, Any]:
        """Carrega resultados mais recentes"""
        json_files = [
            'advanced_algorithm_comparison.json',
            'multi_algorithm_comparison.json',
            'final_v3_results.json'
        ]
        
        for json_file in json_files:
            if Path(json_file).exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    st.error(f"Erro ao carregar {json_file}: {e}")
        
        return {}

    def render_header(self):
        """Renderiza o cabeçalho principal"""
        st.markdown("""
        <div class="main-header">
            <h1> RenamePDFEPUB</h1>
            <h3>Sistema Avançado de Algoritmos para Metadados</h3>
            <p>Interface moderna para análise e comparação de algoritmos</p>
        </div>
        """, unsafe_allow_html=True)

    def render_sidebar(self, results: Dict[str, Any]):
        """Renderiza a barra lateral com controles"""
        st.sidebar.header("🎛 Controles")
        
        # Seleção de visualização
        view_mode = st.sidebar.selectbox(
            "Modo de Visualização",
            ["Dashboard Geral", "Análise por Algoritmo", "Análise por Livro", "Comparação Avançada"]
        )
        
        # Filtros
        st.sidebar.header("🔍 Filtros")
        
        if results and 'algorithm_summary' in results:
            selected_algorithms = st.sidebar.multiselect(
                "Algoritmos",
                list(results['algorithm_summary'].keys()),
                default=list(results['algorithm_summary'].keys())
            )
        else:
            selected_algorithms = []
        
        # Controles de execução
        st.sidebar.header("⚡ Ações")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🔄 Atualizar Dados"):
                st.rerun()
        
        with col2:
            if st.button("📊 Executar Teste"):
                self.run_algorithm_test()
        
        return view_mode, selected_algorithms

    def render_metrics_overview(self, results: Dict[str, Any]):
        """Renderiza visão geral das métricas"""
        if not results or 'algorithm_summary' not in results:
            st.warning("⚠ Dados não disponíveis")
            return
        
        st.header("📊 Métricas Gerais")
        
        # Calcula métricas
        total_algorithms = len(results['algorithm_summary'])
        avg_accuracy = 0
        avg_confidence = 0
        total_books = results.get('test_info', {}).get('total_books', 0)
        
        for summary in results['algorithm_summary'].values():
            if 'avg_accuracy' in summary:
                avg_accuracy += summary['avg_accuracy']
                avg_confidence += summary['avg_confidence']
        
        if total_algorithms > 0:
            avg_accuracy = (avg_accuracy / total_algorithms) * 100
            avg_confidence = (avg_confidence / total_algorithms) * 100
        
        # Exibe métricas em colunas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🔬 Algoritmos",
                value=total_algorithms,
                delta="5 disponíveis"
            )
        
        with col2:
            st.metric(
                label="📚 Livros Testados",
                value=total_books,
                delta="Dataset completo"
            )
        
        with col3:
            st.metric(
                label="🎯 Accuracy Média",
                value=f"{avg_accuracy:.1f}%",
                delta="Excelente" if avg_accuracy > 85 else "Bom"
            )
        
        with col4:
            st.metric(
                label="💡 Confiança Média",
                value=f"{avg_confidence:.1f}%",
                delta="Alta confiança"
            )

    def render_algorithm_comparison(self, results: Dict[str, Any], selected_algorithms: List[str]):
        """Renderiza comparação entre algoritmos"""
        if not results or 'algorithm_summary' not in results:
            return
        
        st.header("🔬 Comparação de Algoritmos")
        
        # Filtra algoritmos selecionados
        filtered_data = {
            name: data for name, data in results['algorithm_summary'].items()
            if name in selected_algorithms and 'avg_accuracy' in data
        }
        
        if not filtered_data:
            st.warning("⚠ Nenhum algoritmo selecionado ou dados insuficientes")
            return
        
        # Cria cards para cada algoritmo
        for alg_name, summary in filtered_data.items():
            accuracy = summary['avg_accuracy'] * 100
            confidence = summary['avg_confidence'] * 100
            time_ms = summary['avg_time'] * 1000
            success_rate = summary['success_rate'] * 100
            
            # Define cor do card baseada na performance
            if accuracy >= 90:
                card_class = "success-card"
                emoji = "🏆"
            elif accuracy >= 70:
                card_class = "warning-card"
                emoji = "⚡"
            else:
                card_class = "info-card"
                emoji = "🔧"
            
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="algorithm-card {card_class}">
                        <h4>{emoji} {alg_name}</h4>
                        <p>{self.algorithm_descriptions.get(alg_name, 'Algoritmo especializado')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.write("")  # Espaçamento
                
                # Métricas detalhadas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Accuracy", f"{accuracy:.2f}%")
                    st.progress(accuracy / 100)
                
                with col2:
                    st.metric("Confiança", f"{confidence:.2f}%")
                    st.progress(confidence / 100)
                
                with col3:
                    st.metric("Tempo", f"{time_ms:.2f}ms")
                
                with col4:
                    st.metric("Sucesso", f"{success_rate:.1f}%")
                    st.progress(success_rate / 100)
                
                st.divider()

    def render_book_analysis(self, results: Dict[str, Any]):
        """Renderiza análise detalhada por livro"""
        if not results or 'detailed_results' not in results:
            return
        
        st.header("📚 Análise por Livro")
        
        # Configurações
        num_books = st.slider("Número de livros para exibir", 5, 50, 15)
        
        # Análise dos livros
        books_data = []
        for i, result in enumerate(results['detailed_results'][:num_books], 1):
            filename = result['filename']
            best_alg = result['best_algorithm']
            
            # Accuracy do melhor algoritmo
            best_accuracy = 0
            if 'accuracies' in result:
                best_accuracy = max(result['accuracies'].values()) * 100
            
            books_data.append({
                'Posição': i,
                'Arquivo': filename[:60] + "..." if len(filename) > 60 else filename,
                'Melhor Algoritmo': best_alg,
                'Accuracy': f"{best_accuracy:.1f}%",
                'Status': " Sucesso" if best_accuracy > 80 else "⚠ Revisão"
            })
        
        # Exibe como dataframe
        if books_data:
            st.dataframe(
                books_data,
                use_container_width=True,
                hide_index=True
            )
        
        # Estatísticas adicionais
        st.subheader("📈 Estatísticas")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_accuracy = sum(1 for book in books_data if float(book['Accuracy'].replace('%', '')) > 90)
            st.metric("Alta Accuracy (>90%)", high_accuracy)
        
        with col2:
            brazilian_books = sum(1 for result in results['detailed_results'][:num_books] 
                                if result['best_algorithm'] == 'Brazilian Specialist')
            st.metric("Livros Brasileiros", brazilian_books)
        
        with col3:
            avg_book_accuracy = sum(float(book['Accuracy'].replace('%', '')) for book in books_data) / len(books_data)
            st.metric("Accuracy Média", f"{avg_book_accuracy:.1f}%")

    def render_advanced_comparison(self, results: Dict[str, Any]):
        """Renderiza comparação avançada com visualizações"""
        if not results or 'algorithm_summary' not in results:
            return
        
        st.header(" Comparação Avançada")
        
        tab1, tab2, tab3 = st.tabs(["Performance", "Distribuição", "Correlações"])
        
        with tab1:
            st.subheader("⚡ Performance por Algoritmo")
            
            # Dados para gráfico
            alg_names = []
            accuracies = []
            times = []
            
            for name, data in results['algorithm_summary'].items():
                if 'avg_accuracy' in data:
                    alg_names.append(name)
                    accuracies.append(data['avg_accuracy'] * 100)
                    times.append(data['avg_time'] * 1000)
            
            if alg_names:
                # Simula gráfico com barras de progresso
                for i, (name, acc, time_ms) in enumerate(zip(alg_names, accuracies, times)):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**{name}**")
                        st.progress(acc / 100)
                    
                    with col2:
                        st.metric("Accuracy", f"{acc:.1f}%")
                    
                    with col3:
                        st.metric("Tempo", f"{time_ms:.1f}ms")
        
        with tab2:
            st.subheader("📊 Distribuição de Resultados")
            
            # Análise de distribuição
            if 'detailed_results' in results:
                algorithm_counts = {}
                for result in results['detailed_results']:
                    best_alg = result['best_algorithm']
                    algorithm_counts[best_alg] = algorithm_counts.get(best_alg, 0) + 1
                
                st.write("**Algoritmo mais usado por livro:**")
                for alg, count in sorted(algorithm_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(results['detailed_results'])) * 100
                    st.write(f"• {alg}: {count} livros ({percentage:.1f}%)")
                    st.progress(percentage / 100)
        
        with tab3:
            st.subheader("🔗 Análise de Correlações")
            
            st.write("**Insights do Sistema:**")
            
            insights = [
                "🎯 **Hybrid Orchestrator** combina as melhores técnicas de todos os algoritmos",
                "🇧🇷 **Brazilian Specialist** é otimizado para editoras nacionais (Casa do Código, Novatec, etc)",
                "⚡ **Smart Inferencer** usa heurísticas avançadas para inferir dados ausentes",
                "🔧 **Enhanced Parser** melhora a qualidade dos dados extraídos",
                "📝 **Basic Parser** oferece extração rápida e confiável"
            ]
            
            for insight in insights:
                st.markdown(insight)

    def run_algorithm_test(self):
        """Executa teste de algoritmos"""
        with st.spinner('Executando teste de algoritmos...'):
            try:
                # Simula execução
                time.sleep(2)
                
                # Tenta executar o script real
                import subprocess
                result = subprocess.run([
                    sys.executable, 'advanced_algorithm_comparison.py'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    st.success(" Teste executado com sucesso!")
                    st.rerun()
                else:
                    st.error(f" Erro na execução: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                st.warning("⏱ Teste em execução (tempo limite atingido)")
            except Exception as e:
                st.error(f" Erro: {e}")

    def run(self):
        """Executa a interface principal"""
        # Cabeçalho
        self.render_header()
        
        # Carrega dados
        results = self.load_results()
        
        # Sidebar
        view_mode, selected_algorithms = self.render_sidebar(results)
        
        # Conteúdo principal baseado no modo
        if view_mode == "Dashboard Geral":
            self.render_metrics_overview(results)
            self.render_algorithm_comparison(results, selected_algorithms)
            
        elif view_mode == "Análise por Algoritmo":
            self.render_algorithm_comparison(results, selected_algorithms)
            
        elif view_mode == "Análise por Livro":
            self.render_book_analysis(results)
            
        elif view_mode == "Comparação Avançada":
            self.render_advanced_comparison(results)
        
        # Rodapé
        st.divider()
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 20px;">
            <p> <strong>RenamePDFEPUB</strong> - Sistema Avançado de Algoritmos</p>
            <p>Desenvolvido com ❤ para otimização de metadados de livros</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Função principal"""
    interface = StreamlitInterface()
    interface.run()

if __name__ == "__main__":
    main()