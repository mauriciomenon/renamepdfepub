#!/usr/bin/env python3
"""
Gerador de Relatórios Simplificado
=================================

Gera relatórios HTML interativos sem dependências externas
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any

class SimpleReportGenerator:
    """Gerador de relatórios HTML simples e elegante"""
    
    def __init__(self):
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

    def generate_html_report(self, results: Dict[str, Any]) -> str:
        """Gera relatório HTML completo"""
        
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Algoritmos - RenamePDFEPUB</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.2em;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }}
        
        .card h2 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            display: block;
        }}
        
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .algorithm-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .algorithm-table th,
        .algorithm-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        .algorithm-table th {{
            background: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        .algorithm-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .algorithm-table tr:hover {{
            background-color: #e3f2fd;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        
        .book-analysis {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        
        .book-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        
        .book-row:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9em;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            color: white;
        }}
        
        .badge-success {{ background-color: #27ae60; }}
        .badge-warning {{ background-color: #f39c12; }}
        .badge-info {{ background-color: #3498db; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Relatório de Algoritmos</h1>
            <div class="subtitle">Sistema RenamePDFEPUB - Análise Avançada</div>
            <div class="subtitle">Gerado em: {time.strftime('%d/%m/%Y às %H:%M:%S')}</div>
        </div>
        
        {self.generate_metrics_section(results)}
        {self.generate_algorithms_section(results)}
        {self.generate_book_analysis_section(results)}
        
        <div class="footer">
            <p>© 2025 RenamePDFEPUB - Sistema de Análise de Algoritmos</p>
            <p>Desenvolvido com ❤ para otimização de metadados de livros</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content

    def generate_metrics_section(self, results: Dict[str, Any]) -> str:
        """Gera seção de métricas gerais"""
        if not results or 'algorithm_summary' not in results:
            return "<div class='card'><h2>Métricas Gerais</h2><p>Dados não disponíveis</p></div>"
        
        # Calcula métricas gerais
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
        
        return f"""
        <div class="card">
            <h2>📊 Métricas Gerais</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="metric-value">{total_algorithms}</span>
                    <span class="metric-label">Algoritmos Testados</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{total_books}</span>
                    <span class="metric-label">Livros Analisados</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{avg_accuracy:.1f}%</span>
                    <span class="metric-label">Accuracy Média</span>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{avg_confidence:.1f}%</span>
                    <span class="metric-label">Confiança Média</span>
                </div>
            </div>
        </div>
        """

    def generate_algorithms_section(self, results: Dict[str, Any]) -> str:
        """Gera seção de análise dos algoritmos"""
        if not results or 'algorithm_summary' not in results:
            return "<div class='card'><h2>Algoritmos</h2><p>Dados não disponíveis</p></div>"
        
        table_rows = ""
        for alg_name, summary in results['algorithm_summary'].items():
            if 'avg_accuracy' in summary:
                accuracy = summary['avg_accuracy'] * 100
                confidence = summary['avg_confidence'] * 100
                time_ms = summary['avg_time'] * 1000
                success_rate = summary['success_rate'] * 100
                
                # Define cor da barra de progresso baseada na accuracy
                if accuracy >= 90:
                    bar_class = "badge-success"
                elif accuracy >= 70:
                    bar_class = "badge-warning"
                else:
                    bar_class = "badge-info"
                
                table_rows += f"""
                <tr>
                    <td><strong>{alg_name}</strong></td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill {bar_class}" style="width: {accuracy}%; background-color: {self.algorithm_colors.get(alg_name, '#3498db')};"></div>
                        </div>
                        {accuracy:.2f}%
                    </td>
                    <td>{confidence:.2f}%</td>
                    <td>{time_ms:.3f}ms</td>
                    <td>
                        <span class="badge {bar_class}">{success_rate:.1f}%</span>
                    </td>
                </tr>
                """
        
        return f"""
        <div class="card">
            <h2>🔬 Análise Detalhada dos Algoritmos</h2>
            <table class="algorithm-table">
                <thead>
                    <tr>
                        <th>Algoritmo</th>
                        <th>Accuracy</th>
                        <th>Confiança</th>
                        <th>Tempo Médio</th>
                        <th>Taxa de Sucesso</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

    def generate_book_analysis_section(self, results: Dict[str, Any]) -> str:
        """Gera seção de análise por livro"""
        if not results or 'detailed_results' not in results:
            return "<div class='card'><h2>Análise por Livro</h2><p>Dados não disponíveis</p></div>"
        
        book_rows = ""
        for i, result in enumerate(results['detailed_results'][:15], 1):  # Primeiros 15
            filename = result['filename'][:50] + "..." if len(result['filename']) > 50 else result['filename']
            best_alg = result['best_algorithm']
            
            # Pega a melhor accuracy
            best_accuracy = 0
            if 'accuracies' in result:
                best_accuracy = max(result['accuracies'].values()) * 100
            
            book_rows += f"""
            <div class="book-row">
                <div>
                    <strong>#{i}</strong> {filename}
                </div>
                <div>
                    <span class="badge badge-info">{best_alg}</span>
                    <span class="badge badge-success">{best_accuracy:.1f}%</span>
                </div>
            </div>
            """
        
        return f"""
        <div class="card">
            <h2>📚 Análise por Livro (Top 15)</h2>
            <div class="book-analysis">
                {book_rows}
            </div>
        </div>
        """

    def generate_comprehensive_report(self) -> str:
        """Gera relatório abrangente"""
        print("Gerando relatório HTML abrangente...")
        
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
            return ""
        
        # Gera HTML
        html_content = self.generate_html_report(results)
        
        # Salva arquivo
        report_path = "advanced_algorithms_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Relatório HTML gerado: {report_path}")
        return report_path

def main():
    """Função principal"""
    generator = SimpleReportGenerator()
    report_file = generator.generate_comprehensive_report()
    
    if report_file:
        print(f"\n🎉 RELATÓRIO GERADO COM SUCESSO!")
        print(f"📄 Arquivo: {report_file}")
        print(f" Abra o arquivo no navegador para visualizar")
    else:
        print(" Erro ao gerar relatório")

if __name__ == "__main__":
    main()