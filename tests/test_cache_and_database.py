#!/usr/bin/env python3
"""
Testes para cache e banco de dados
Valida integridade, performance e funcionalidade do sistema de cache
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
import sqlite3
import time

# Configurar o caminho
PROJECT_ROOT = Path(__file__).parent.parent

class TestCacheSystem:
    """Testa o sistema de cache do projeto"""
    
    def setup_method(self):
        """Configurar ambiente de teste"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
        self.cache_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Limpar após teste"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_directory_structure(self):
        """Verifica estrutura do diretório de cache"""
        cache_root = PROJECT_ROOT / "data" / "cache"
        
        # Verificar se diretório cache existe ou pode ser criado
        if not cache_root.exists():
            cache_root.mkdir(parents=True, exist_ok=True)
        
        assert cache_root.exists(), "Diretório de cache não existe"
        assert cache_root.is_dir(), "Cache path não é um diretório"
        
        # Verificar permissões de escrita
        test_file = cache_root / "test_write.tmp"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            pytest.fail(f"Não consegue escrever no diretório cache: {e}")
    
    def test_cache_json_operations(self):
        """Testa operações básicas com cache JSON"""
        cache_file = self.cache_dir / "test_cache.json"
        
        # Teste de escrita
        test_data = {
            "timestamp": time.time(),
            "data": {"key1": "value1", "key2": "value2"},
            "metadata": {"version": "1.0", "type": "test"}
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)
        except Exception as e:
            pytest.fail(f"Falha ao escrever cache JSON: {e}")
        
        # Teste de leitura
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_data, "Dados do cache não conferem"
        except Exception as e:
            pytest.fail(f"Falha ao ler cache JSON: {e}")
    
    def test_cache_sqlite_operations(self):
        """Testa operações básicas com cache SQLite"""
        db_file = self.cache_dir / "test_cache.db"
        
        try:
            # Criar conexão e tabela de teste
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_test (
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE,
                    value TEXT,
                    timestamp REAL
                )
            """)
            
            # Teste de inserção
            test_entries = [
                ("key1", "value1", time.time()),
                ("key2", "value2", time.time()),
                ("key3", "value3", time.time())
            ]
            
            cursor.executemany(
                "INSERT OR REPLACE INTO cache_test (key, value, timestamp) VALUES (?, ?, ?)",
                test_entries
            )
            conn.commit()
            
            # Teste de consulta
            cursor.execute("SELECT COUNT(*) FROM cache_test")
            count = cursor.fetchone()[0]
            assert count == 3, f"Esperado 3 entradas, encontrado {count}"
            
            # Teste de busca específica
            cursor.execute("SELECT value FROM cache_test WHERE key = ?", ("key2",))
            result = cursor.fetchone()
            assert result and result[0] == "value2", "Valor não encontrado corretamente"
            
            conn.close()
            
        except Exception as e:
            pytest.fail(f"Falha ao operar SQLite cache: {e}")
    
    def test_cache_performance(self):
        """Testa performance básica do cache"""
        cache_file = self.cache_dir / "performance_cache.json"
        
        # Teste de escrita de volume médio
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}
        
        start_time = time.time()
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(large_data, f)
        except Exception as e:
            pytest.fail(f"Falha no teste de performance de escrita: {e}")
        
        write_time = time.time() - start_time
        assert write_time < 5.0, f"Escrita muito lenta: {write_time:.2f}s"
        
        # Teste de leitura
        start_time = time.time()
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            assert len(loaded_data) == 1000, "Dados não carregados completamente"
        except Exception as e:
            pytest.fail(f"Falha no teste de performance de leitura: {e}")
        
        read_time = time.time() - start_time
        assert read_time < 2.0, f"Leitura muito lenta: {read_time:.2f}s"
    
    def test_cache_corruption_recovery(self):
        """Testa recuperação de cache corrompido"""
        cache_file = self.cache_dir / "corrupt_cache.json"
        
        # Criar arquivo JSON corrompido
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write('{"incomplete": "json"')  # JSON inválido
        
        # Testar detecção de corrupção
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                json.load(f)
            pytest.fail("JSON corrompido não foi detectado")
        except json.JSONDecodeError:
            pass  # Esperado
        
        # Testar recuperação (recriar arquivo)
        try:
            cache_file.unlink()
            new_data = {"recovered": True, "timestamp": time.time()}
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f)
            
            # Verificar recuperação
            with open(cache_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            assert loaded["recovered"] is True, "Recuperação falhou"
        except Exception as e:
            pytest.fail(f"Falha na recuperação do cache: {e}")
    
    def test_existing_cache_files(self):
        """Verifica integridade dos arquivos de cache existentes"""
        cache_root = PROJECT_ROOT / "data" / "cache"
        
        if not cache_root.exists():
            pytest.skip("Diretório de cache não existe ainda")
        
        json_files = list(cache_root.glob("*.json"))
        db_files = list(cache_root.glob("*.db"))
        
        # Testar arquivos JSON existentes
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Arquivo cache JSON corrompido {json_file}: {e}")
            except Exception as e:
                pytest.fail(f"Erro ao ler cache JSON {json_file}: {e}")
        
        # Testar arquivos SQLite existentes
        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                # Pelo menos deve conseguir ler a estrutura
                assert isinstance(tables, list), f"Estrutura SQLite inválida em {db_file}"
            except Exception as e:
                pytest.fail(f"Erro ao verificar SQLite cache {db_file}: {e}")


class TestDatabaseIntegrity:
    """Testa integridade do sistema de banco de dados"""
    
    def setup_method(self):
        """Configurar ambiente de teste"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
    
    def teardown_method(self):
        """Limpar após teste"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sqlite_basic_operations(self):
        """Testa operações básicas SQLite"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Criar tabela de teste
            cursor.execute("""
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    isbn TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Inserir dados de teste
            test_books = [
                ("Test Book 1", "Author 1", "123456789"),
                ("Test Book 2", "Author 2", "987654321"),
                ("Test Book 3", "Author 3", "456789123")
            ]
            
            cursor.executemany(
                "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
                test_books
            )
            conn.commit()
            
            # Verificar inserção
            cursor.execute("SELECT COUNT(*) FROM books")
            count = cursor.fetchone()[0]
            assert count == 3, f"Esperado 3 livros, encontrado {count}"
            
            # Testar consulta com filtro
            cursor.execute("SELECT title FROM books WHERE author = ?", ("Author 2",))
            result = cursor.fetchone()
            assert result and result[0] == "Test Book 2", "Consulta com filtro falhou"
            
            conn.close()
            
        except Exception as e:
            pytest.fail(f"Falha em operações SQLite básicas: {e}")
    
    def test_database_transaction_integrity(self):
        """Testa integridade de transações"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE transactions_test (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """)
            
            # Testar rollback
            cursor.execute("INSERT INTO transactions_test (data) VALUES (?)", ("before_rollback",))
            conn.commit()
            
            cursor.execute("INSERT INTO transactions_test (data) VALUES (?)", ("should_rollback",))
            conn.rollback()  # Cancelar última inserção
            
            cursor.execute("SELECT COUNT(*) FROM transactions_test")
            count = cursor.fetchone()[0]
            assert count == 1, f"Rollback falhou, encontrado {count} registros"
            
            # Testar commit explícito
            cursor.execute("INSERT INTO transactions_test (data) VALUES (?)", ("committed",))
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM transactions_test")
            count = cursor.fetchone()[0]
            assert count == 2, f"Commit falhou, encontrado {count} registros"
            
            conn.close()
            
        except Exception as e:
            pytest.fail(f"Falha em teste de transações: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])