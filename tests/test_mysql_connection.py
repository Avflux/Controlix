#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes para o módulo de conexão MySQL.
"""

import os
import sys
import unittest
import logging
import time
from pathlib import Path
from app.config.encrypted_settings import EncryptedSettings
from app.data.mysql.mysql_connection import MySQLConnection
from app.config.cache.cache_config import CacheConfig
from app.config.cache.cache_factory import CacheFactory

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações do projeto
from app.data.mysql.credentials_loader import CredentialsLoader
from app.data.connection import DatabaseConnection

class TestMySQLConnection(unittest.TestCase):
    """Testes para a classe MySQLConnection."""
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes."""
        try:
            # Carregar configurações
            cls.local_settings = EncryptedSettings(Path('.security/mysql_local'))
            cls.remote_settings = EncryptedSettings(Path('.security/mysql_remoto'))
            
            # Criar instância de conexão
            cls.mysql = MySQLConnection(cls.local_settings, cls.remote_settings)
            
            logger.info("Configuração de teste inicializada")
            
        except Exception as e:
            logger.error(f"Erro na configuração dos testes: {e}")
            raise
    
    def test_local_connection(self):
        """Testa a conexão com o banco local."""
        try:
            # Obter conexão
            connection = self.mysql.get_local_connection()
            self.assertIsNotNone(connection)
            
            # Verificar se está conectado
            self.assertTrue(connection.is_connected())
            
            # Liberar conexão
            self.mysql.release_connection(connection)
            
            logger.info("Teste de conexão local passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de conexão local: {e}")
            raise
    
    def test_remote_connection(self):
        """Testa a conexão com o banco remoto."""
        try:
            # Obter conexão
            connection = self.mysql.get_remote_connection()
            self.assertIsNotNone(connection)
            
            # Verificar se está conectado
            self.assertTrue(connection.is_connected())
            
            # Liberar conexão
            self.mysql.release_connection(connection)
            
            logger.info("Teste de conexão remota passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de conexão remota: {e}")
            raise
    
    def test_execute_query(self):
        """Testa a execução de consultas."""
        try:
            # Testar no banco local
            result = self.mysql.execute_query("SELECT 1 as test", is_local=True)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['test'], 1)
            
            # Testar no banco remoto
            result = self.mysql.execute_query("SELECT 1 as test", is_local=False)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['test'], 1)
            
            logger.info("Teste de execução de consulta passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de execução de consulta: {e}")
            raise
    
    def test_execute_update(self):
        """Testa operações de atualização."""
        try:
            # Criar tabela de teste no banco local
            self.mysql.execute_update("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50)
                )
            """, is_local=True)
            
            # Inserir dados
            affected = self.mysql.execute_update(
                "INSERT INTO test_table (name) VALUES (%s)",
                ("test",),
                is_local=True
            )
            self.assertEqual(affected, 1)
            
            # Limpar tabela
            self.mysql.execute_update("DROP TABLE test_table", is_local=True)
            
            logger.info("Teste de operação de atualização passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de operação de atualização: {e}")
            raise
    
    def test_execute_batch(self):
        """Testa operações em lote."""
        try:
            # Criar tabela de teste
            self.mysql.execute_update("""
                CREATE TABLE IF NOT EXISTS test_batch (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50)
                )
            """, is_local=True)
            
            # Preparar dados
            data = [("name1",), ("name2",), ("name3",)]
            
            # Executar inserção em lote
            affected = self.mysql.execute_batch(
                "INSERT INTO test_batch (name) VALUES (%s)",
                data,
                is_local=True
            )
            self.assertEqual(affected, 3)
            
            # Verificar dados
            result = self.mysql.execute_query(
                "SELECT COUNT(*) as count FROM test_batch",
                is_local=True
            )
            self.assertEqual(result[0]['count'], 3)
            
            # Limpar tabela
            self.mysql.execute_update("DROP TABLE test_batch", is_local=True)
            
            logger.info("Teste de operação em lote passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de operação em lote: {e}")
            raise
    
    def test_cache(self):
        """Testa o sistema de cache."""
        try:
            # Criar tabela de teste
            self.mysql.execute_update("""
                CREATE TABLE IF NOT EXISTS test_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50)
                )
            """, is_local=True)
            
            # Inserir dados
            self.mysql.execute_update(
                "INSERT INTO test_cache (name) VALUES (%s)",
                ("test_cache",),
                is_local=True
            )
            
            # Primeira consulta (sem cache)
            start_time = time.time()
            result1 = self.mysql.execute_query(
                "SELECT * FROM test_cache",
                is_local=True,
                use_cache=True
            )
            no_cache_time = time.time() - start_time
            
            # Segunda consulta (com cache)
            start_time = time.time()
            result2 = self.mysql.execute_query(
                "SELECT * FROM test_cache",
                is_local=True,
                use_cache=True
            )
            cache_time = time.time() - start_time
            
            # Verificar resultados
            self.assertEqual(result1, result2)
            self.assertLess(cache_time, no_cache_time)
            
            # Atualizar dados
            self.mysql.execute_update(
                "UPDATE test_cache SET name = %s",
                ("updated",),
                is_local=True,
                invalidate_cache=True
            )
            
            # Consulta após atualização
            result3 = self.mysql.execute_query(
                "SELECT * FROM test_cache",
                is_local=True,
                use_cache=True
            )
            self.assertEqual(result3[0]['name'], "updated")
            
            # Limpar tabela
            self.mysql.execute_update("DROP TABLE test_cache", is_local=True)
            
            logger.info("Teste de cache passou")
            logger.info(f"Tempo sem cache: {no_cache_time:.4f}s")
            logger.info(f"Tempo com cache: {cache_time:.4f}s")
            
        except Exception as e:
            logger.error(f"Erro no teste de cache: {e}")
            raise
    
    def test_cache_invalidation(self):
        """Testa a invalidação do cache."""
        try:
            # Criar tabela de teste
            self.mysql.execute_update("""
                CREATE TABLE IF NOT EXISTS test_cache_invalidation (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    value INT
                )
            """, is_local=True)
            
            # Inserir dados iniciais
            self.mysql.execute_update(
                "INSERT INTO test_cache_invalidation (value) VALUES (%s)",
                (1,),
                is_local=True
            )
            
            # Primeira consulta (armazenar em cache)
            result1 = self.mysql.execute_query(
                "SELECT * FROM test_cache_invalidation",
                is_local=True,
                use_cache=True
            )
            self.assertEqual(result1[0]['value'], 1)
            
            # Atualizar sem invalidar cache
            self.mysql.execute_update(
                "UPDATE test_cache_invalidation SET value = %s",
                (2,),
                is_local=True,
                invalidate_cache=False
            )
            
            # Consulta deve retornar valor em cache
            result2 = self.mysql.execute_query(
                "SELECT * FROM test_cache_invalidation",
                is_local=True,
                use_cache=True
            )
            self.assertEqual(result2[0]['value'], 1)  # Valor em cache
            
            # Atualizar com invalidação de cache
            self.mysql.execute_update(
                "UPDATE test_cache_invalidation SET value = %s",
                (3,),
                is_local=True,
                invalidate_cache=True
            )
            
            # Consulta deve retornar novo valor
            result3 = self.mysql.execute_query(
                "SELECT * FROM test_cache_invalidation",
                is_local=True,
                use_cache=True
            )
            self.assertEqual(result3[0]['value'], 3)  # Novo valor
            
            # Limpar tabela
            self.mysql.execute_update("DROP TABLE test_cache_invalidation", is_local=True)
            
            logger.info("Teste de invalidação de cache passou")
            
        except Exception as e:
            logger.error(f"Erro no teste de invalidação de cache: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """Limpeza após os testes."""
        try:
            if hasattr(cls, 'mysql'):
                cls.mysql.close()
            logger.info("Limpeza dos testes concluída")
        except Exception as e:
            logger.error(f"Erro na limpeza dos testes: {e}")
            raise

if __name__ == '__main__':
    unittest.main() 