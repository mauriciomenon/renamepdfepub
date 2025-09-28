#!/usr/bin/env python3
"""
Launcher para Interface Web
===========================

Instala dependências e executa a interface Streamlit
"""

import subprocess
import sys
import os
from pathlib import Path

def install_streamlit():
    """Instala Streamlit se não estiver disponível"""
    try:
        import streamlit
        print("[OK] Streamlit já está instalado")
        return True
    except ImportError:
        print("[INFO] Instalando Streamlit...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "streamlit"
            ])
            print("[OK] Streamlit instalado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Erro ao instalar Streamlit: {e}")
            return False

def generate_sample_data():
    """Gera dados de exemplo se não existirem"""
    import json
    import random
    
    sample_file = "advanced_algorithm_comparison.json"
    
    if Path(sample_file).exists():
        print(f"[OK] Arquivo de dados encontrado: {sample_file}")
        return
    
    print("[INFO] Gerando dados de exemplo...")
    
    # Dados de exemplo
    sample_data = {
        "test_info": {
            "total_books": 25,
            "test_date": "2025-01-08",
            "algorithms_tested": 5
        },
        "algorithm_summary": {
            "Basic Parser": {
                "avg_accuracy": 0.78,
                "avg_confidence": 0.82,
                "avg_time": 0.045,
                "success_rate": 0.85
            },
            "Enhanced Parser": {
                "avg_accuracy": 0.85,
                "avg_confidence": 0.88, 
                "avg_time": 0.067,
                "success_rate": 0.92
            },
            "Smart Inferencer": {
                "avg_accuracy": 0.91,
                "avg_confidence": 0.89,
                "avg_time": 0.089,
                "success_rate": 0.94
            },
            "Hybrid Orchestrator": {
                "avg_accuracy": 0.96,
                "avg_confidence": 0.94,
                "avg_time": 0.123,
                "success_rate": 0.98
            },
            "Brazilian Specialist": {
                "avg_accuracy": 0.93,
                "avg_confidence": 0.91,
                "avg_time": 0.078,
                "success_rate": 0.95
            }
        },
        "detailed_results": []
    }
    
    # Gera resultados detalhados de exemplo
    book_names = [
        "Python_para_Desenvolvedores.pdf",
        "JavaScript_Moderno.epub",
        "Machine_Learning_Casa_do_Codigo.pdf", 
        "React_Native_Novatec.epub",
        "Docker_Containers.pdf",
        "AWS_Cloud_Computing.epub",
        "Data_Science_Python.pdf",
        "Vue.js_Desenvolvimento.epub",
        "Kubernetes_Pratico.pdf",
        "TensorFlow_Deep_Learning.epub",
        "NodeJS_APIs.pdf",
        "Angular_Completo.epub",
        "PostgreSQL_Banco_Dados.pdf",
        "Redis_Cache.epub",
        "GraphQL_API.pdf",
        "Flutter_Mobile.epub",
        "Go_Programming.pdf",
        "Rust_Systems.epub",
        "C++_Moderno.pdf",
        "Java_Spring_Boot.epub",
        "PHP_Laravel.pdf",
        "Ruby_Rails.epub",
        "Swift_iOS.pdf",
        "Kotlin_Android.epub",
        "Unity_Game_Dev.pdf"
    ]
    
    algorithms = list(sample_data["algorithm_summary"].keys())
    
    for i, book in enumerate(book_names):
        # Seleciona melhor algoritmo baseado no tipo de livro
        if "Casa_do_Codigo" in book or "Novatec" in book:
            best_alg = "Brazilian Specialist"
        elif "Machine_Learning" in book or "TensorFlow" in book:
            best_alg = "Hybrid Orchestrator"
        elif "JavaScript" in book or "React" in book or "Vue" in book:
            best_alg = "Smart Inferencer"
        else:
            best_alg = random.choice(algorithms)
        
        # Gera accuracies
        accuracies = {}
        for alg in algorithms:
            base_acc = sample_data["algorithm_summary"][alg]["avg_accuracy"]
            variation = random.uniform(-0.1, 0.1)
            accuracies[alg] = max(0.1, min(1.0, base_acc + variation))
        
        result = {
            "filename": book,
            "best_algorithm": best_alg,
            "accuracies": accuracies,
            "confidences": {alg: acc * random.uniform(0.9, 1.1) for alg, acc in accuracies.items()},
            "execution_time": random.uniform(0.03, 0.15)
        }
        
        sample_data["detailed_results"].append(result)
    
    # Salva arquivo
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f" Dados de exemplo gerados: {sample_file}")

def launch_streamlit():
    """Executa a interface Streamlit"""
    print("Iniciando interface Streamlit...")
    print("A interface sera aberta no navegador automaticamente")
    print("Pressione Ctrl+C para parar o servidor")
    
    # Caminho correto para o arquivo
    streamlit_file = Path(__file__).parent / "streamlit_interface.py"
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(streamlit_file),
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false"
        ])
    except KeyboardInterrupt:
        print("\nInterface encerrada")
    except Exception as e:
        print(f"Erro ao executar Streamlit: {e}")

def generate_simple_report():
    """Gera relatorio HTML simples"""
    print("[INFO] Gerando relatorio HTML...")
    try:
        # Caminho correto para o gerador
        report_generator = Path(__file__).parent.parent.parent / "reports" / "simple_report_generator.py"
        subprocess.run([sys.executable, str(report_generator)])
    except Exception as e:
        print(f"[WARNING] Erro ao gerar relatorio: {e}")

def main():
    """Função principal"""
    print("=" * 60)
    print("RENAMEPDFEPUB - INTERFACE WEB LAUNCHER")
    print("=" * 60)
    
    # Menu de opções
    print("\nEscolha uma opção:")
    print("1. Iniciar Interface Streamlit (Recomendado)")
    print("2. Gerar Relatório HTML")
    print("3. Executar Teste de Algoritmos")
    print("4. Gerar Dados de Exemplo")
    print("0. Sair")
    
    try:
        choice = input("\nDigite sua escolha (0-4): ").strip()
        
        if choice == "1":
            # Instala Streamlit se necessário
            if not install_streamlit():
                print("[ERROR] Não foi possível instalar Streamlit")
                return
            
            # Gera dados de exemplo se necessário
            generate_sample_data()
            
            # Executa interface
            launch_streamlit()
            
        elif choice == "2":
            generate_sample_data()
            generate_simple_report()
            
        elif choice == "3":
            print("[INFO] Executando teste de algoritmos...")
            try:
                # Caminho correto para o algoritmo
                algorithm_file = Path(__file__).parent.parent / "core" / "advanced_algorithm_comparison.py"
                subprocess.run([sys.executable, str(algorithm_file)])
            except Exception as e:
                print(f"[ERROR] Erro: {e}")
                
        elif choice == "4":
            generate_sample_data()
            
        elif choice == "0":
            print("Até logo!")
            
        else:
            print("[ERROR] Opção inválida")
            
    except KeyboardInterrupt:
        print("\nOperação cancelada")
    except Exception as e:
        print(f"[ERROR] Erro: {e}")

if __name__ == "__main__":
    main()