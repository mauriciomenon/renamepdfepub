#!/usr/bin/env python3
"""
Sistema de Relatórios Avançado
=============================

Gerador de relatórios visuais e interativos para análise dos algoritmos
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from typing import Dict, List, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class AdvancedReportGenerator:
    """Gerador de relatórios avançados com visualizações"""
    
    def __init__(self):
        # Configura estilo dos gráficos
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Cores para cada algoritmo
        self.algorithm_colors = {
            'Basic Parser': '#FF6B6B',
            'Enhanced Parser': '#4ECDC4', 
            'Smart Inferencer': '#45B7D1',
            'Hybrid Orchestrator': '#96CEB4',
            'Brazilian Specialist': '#FFEAA7'
        }

    def load_results(self, json_file: str) -> Dict[str, Any]:
        """Carrega resultados do arquivo JSON"""
        if Path(json_file).exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def create_accuracy_comparison_chart(self, results: Dict[str, Any]) -> str:
        """Cria gráfico de comparação de accuracy"""
        if not results or 'algorithm_summary' not in results:
            return "Dados não disponíveis"
        
        algorithms = []
        accuracies = []
        confidences = []
        
        for alg_name, summary in results['algorithm_summary'].items():
            if 'avg_accuracy' in summary:
                algorithms.append(alg_name)
                accuracies.append(summary['avg_accuracy'] * 100)
                confidences.append(summary['avg_confidence'] * 100)
        
        # Cria gráfico com Plotly
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Accuracy por Algoritmo', 'Confiança por Algoritmo'),
            vertical_spacing=0.1
        )
        
        # Gráfico de accuracy
        fig.add_trace(
            go.Bar(
                x=algorithms,
                y=accuracies,
                name='Accuracy (%)',
                marker_color=[self.algorithm_colors.get(alg, '#333333') for alg in algorithms],
                text=[f'{acc:.1f}%' for acc in accuracies],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # Gráfico de confiança
        fig.add_trace(
            go.Bar(
                x=algorithms,
                y=confidences,
                name='Confiança (%)',
                marker_color=[self.algorithm_colors.get(alg, '#666666') for alg in algorithms],
                text=[f'{conf:.1f}%' for conf in confidences],
                textposition='auto',
                opacity=0.8
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=600,
            title_text="Comparação de Performance dos Algoritmos",
            showlegend=False
        )
        
        fig.update_xaxes(title_text="Algoritmos", row=2, col=1)
        fig.update_yaxes(title_text="Accuracy (%)", row=1, col=1)
        fig.update_yaxes(title_text="Confiança (%)", row=2, col=1)
        
        # Salva como HTML
        chart_path = "accuracy_comparison_chart.html"
        fig.write_html(chart_path)
        
        return chart_path

    def create_performance_radar_chart(self, results: Dict[str, Any]) -> str:
        """Cria gráfico radar com múltiplas métricas"""
        if not results or 'algorithm_summary' not in results:
            return "Dados não disponíveis"
        
        # Prepara dados para o radar
        algorithms = []
        accuracy_scores = []
        confidence_scores = []
        speed_scores = []  # Inverso do tempo (maior = mais rápido)
        success_scores = []
        
        for alg_name, summary in results['algorithm_summary'].items():
            if 'avg_accuracy' in summary:
                algorithms.append(alg_name)
                accuracy_scores.append(summary['avg_accuracy'] * 100)
                confidence_scores.append(summary['avg_confidence'] * 100)
                
                # Score de velocidade (inverso do tempo normalizado)
                avg_time = summary['avg_time']
                speed_score = (1 / (avg_time + 0.001)) * 10  # Normaliza para escala 0-100
                speed_scores.append(min(speed_score, 100))
                
                success_scores.append(summary['success_rate'] * 100)
        
        # Cria gráfico radar
        fig = go.Figure()
        
        categories = ['Accuracy', 'Confiança', 'Velocidade', 'Taxa Sucesso']
        
        for i, alg in enumerate(algorithms):
            values = [
                accuracy_scores[i],
                confidence_scores[i], 
                speed_scores[i],
                success_scores[i]
            ]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=alg,
                line_color=self.algorithm_colors.get(alg, '#333333')
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="Radar de Performance dos Algoritmos"
        )
        
        # Salva como HTML
        radar_path = "performance_radar_chart.html"
        fig.write_html(radar_path)
        
        return radar_path

    def create_detailed_analysis_table(self, results: Dict[str, Any]) -> pd.DataFrame:
        """Cria tabela detalhada de análise"""
        if not results or 'algorithm_summary' not in results:
            return pd.DataFrame()
        
        data = []
        
        for alg_name, summary in results['algorithm_summary'].items():
            if 'avg_accuracy' in summary:
                data.append({
                    'Algoritmo': alg_name,
                    'Accuracy (%)': f"{summary['avg_accuracy']*100:.2f}%",
                    'Confiança (%)': f"{summary['avg_confidence']*100:.2f}%", 
                    'Tempo Médio (ms)': f"{summary['avg_time']*1000:.3f}ms",
                    'Taxa Sucesso (%)': f"{summary['success_rate']*100:.2f}%",
                    'Livros Processados': len(summary['accuracies']),
                    'Score Geral': f"{(summary['avg_accuracy'] + summary['avg_confidence'] + summary['success_rate'])/3*100:.1f}"
                })
        
        df = pd.DataFrame(data)
        
        # Salva como CSV e HTML
        df.to_csv('detailed_analysis_table.csv', index=False, encoding='utf-8')
        df.to_html('detailed_analysis_table.html', index=False, escape=False,
                   table_id='analysis-table', classes='table table-striped')
        
        return df

    def create_book_by_book_analysis(self, results: Dict[str, Any]) -> str:
        """Cria análise livro por livro"""
        if not results or 'detailed_results' not in results:
            return "Dados não disponíveis"
        
        # Prepara dados para visualização
        books = []
        best_algorithms = []
        accuracy_data = []
        
        for result in results['detailed_results'][:15]:  # Primeiros 15 livros
            filename = result['filename'][:30]  # Trunca nome
            books.append(filename)
            best_algorithms.append(result['best_algorithm'])
            
            # Coleta accuracies de todos os algoritmos para este livro
            book_accuracies = []
            algorithm_names = []
            for alg_result in result['algorithm_results']:
                algorithm_names.append(alg_result['algorithm_name'])
                book_accuracies.append(alg_result['accuracy_score'])
            
            accuracy_data.append(book_accuracies)
        
        # Cria heatmap
        df_heatmap = pd.DataFrame(accuracy_data, 
                                 index=books,
                                 columns=algorithm_names)
        
        fig = px.imshow(
            df_heatmap.values,
            labels=dict(x="Algoritmos", y="Livros", color="Accuracy"),
            x=algorithm_names,
            y=books,
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )
        
        fig.update_layout(
            title="Heatmap de Accuracy por Livro e Algoritmo",
            height=800
        )
        
        # Salva como HTML
        heatmap_path = "book_analysis_heatmap.html"
        fig.write_html(heatmap_path)
        
        return heatmap_path

    def generate_comprehensive_report(self) -> Dict[str, str]:
        """Gera relatório abrangente com todas as visualizações"""
        print("Gerando relatório abrangente...")
        
        # Carrega resultados mais recentes
        json_files = [
            'advanced_algorithm_comparison.json',
            'multi_algorithm_comparison.json'
        ]
        
        results = {}
        for json_file in json_files:
            if Path(json_file).exists():
                results = self.load_results(json_file)
                print(f"Dados carregados de: {json_file}")
                break
        
        if not results:
            print("Nenhum arquivo de resultados encontrado!")
            return {}
        
        # Gera visualizações
        report_files = {}
        
        try:
            # Gráfico de comparação de accuracy
            accuracy_chart = self.create_accuracy_comparison_chart(results)
            report_files['accuracy_chart'] = accuracy_chart
            print(f"✓ Gráfico de accuracy criado: {accuracy_chart}")
            
            # Gráfico radar de performance
            radar_chart = self.create_performance_radar_chart(results)
            report_files['radar_chart'] = radar_chart
            print(f"✓ Gráfico radar criado: {radar_chart}")
            
            # Tabela detalhada
            analysis_df = self.create_detailed_analysis_table(results)
            if not analysis_df.empty:
                report_files['analysis_table'] = 'detailed_analysis_table.html'
                print(f"✓ Tabela detalhada criada: detailed_analysis_table.html")
            
            # Análise livro por livro
            heatmap_chart = self.create_book_by_book_analysis(results)
            report_files['heatmap_chart'] = heatmap_chart
            print(f"✓ Heatmap criado: {heatmap_chart}")
            
        except Exception as e:
            print(f"Erro ao gerar visualizações: {e}")
            # Fallback para relatório textual
            report_files = self.generate_text_report(results)
        
        return report_files

    def generate_text_report(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Gera relatório textual como fallback"""
        report_content = []
        
        report_content.append("RELATÓRIO AVANÇADO DE ALGORITMOS")
        report_content.append("=" * 50)
        report_content.append("")
        
        if 'algorithm_summary' in results:
            report_content.append("RESUMO DOS ALGORITMOS:")
            report_content.append("-" * 30)
            
            for alg_name, summary in results['algorithm_summary'].items():
                if 'avg_accuracy' in summary:
                    report_content.append(f"\n{alg_name}:")
                    report_content.append(f"  • Accuracy: {summary['avg_accuracy']*100:.2f}%")
                    report_content.append(f"  • Confiança: {summary['avg_confidence']*100:.2f}%")
                    report_content.append(f"  • Tempo: {summary['avg_time']*1000:.3f}ms")
                    report_content.append(f"  • Taxa Sucesso: {summary['success_rate']*100:.2f}%")
        
        # Salva relatório textual
        with open('advanced_text_report.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        return {'text_report': 'advanced_text_report.txt'}

def main():
    """Função principal"""
    generator = AdvancedReportGenerator()
    report_files = generator.generate_comprehensive_report()
    
    print("\nRELATÓRIO AVANÇADO GERADO!")
    print("=" * 35)
    
    for report_type, filename in report_files.items():
        print(f"• {report_type}: {filename}")
    
    print("\nArquivos prontos para visualização!")

if __name__ == "__main__":
    main()