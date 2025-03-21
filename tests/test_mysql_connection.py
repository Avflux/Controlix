#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes para conexão com bancos MySQL local e remoto.
"""

import os
import sys
import unittest
import logging
import time
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações do projeto
from app.data.mysql.credentials_loader import CredentialsLoader
from app.data.mysql.mysql_connection import MySQLConnection
from app.data.connection import DatabaseConnection

class TestMySQLConnection(unittest.TestCase):
    """Testes para conexão com bancos MySQL local e remoto."""
    
    def setUp(self):
        """Configuração inicial para os testes."""
        # Configurar variáveis de ambiente
        CredentialsLoader.setup_environment_variables()
        
        # Instanciar conexões
        self.mysql_connection = MySQLConnection()
        self.db_connection = DatabaseConnection()
        
    def test_credentials_loader(self):
        """Testa o carregador de credenciais."""
        # Testar carregamento de credenciais locais
        local_credentials = CredentialsLoader.load_credentials(is_local=True)
        self.assertIsNotNone(local_credentials)
        self.assertIn('host', local_credentials)
        self.assertIn('user', local_credentials)
        self.assertIn('password', local_credentials)
        self.assertIn('database', local_credentials)
        
        # Testar carregamento de credenciais remotas
        remote_credentials = CredentialsLoader.load_credentials(is_local=False)
        self.assertIsNotNone(remote_credentials)
        self.assertIn('host', remote_credentials)
        self.assertIn('user', remote_credentials)
        self.assertIn('password', remote_credentials)
        self.assertIn('database', remote_credentials)
        
    def test_local_connection(self):
        """Testa a conexão com o banco local."""
        # Testar conexão direta
        status, message = CredentialsLoader.test_connection(is_local=True)
        self.assertTrue(status, message)
        logger.info(f"Conexão local: {message}")
        
        # Testar conexão via MySQLConnection
        try:
            connection = self.mysql_connection.get_local_connection()
            self.assertTrue(connection.is_connected())
            self.mysql_connection.release_connection(connection)
            logger.info("Conexão local via MySQLConnection bem-sucedida")
        except Exception as e:
            self.fail(f"Erro na conexão local via MySQLConnection: {e}")
            
        # Testar conexão via DatabaseConnection
        try:
            result = self.db_connection.execute_query("SELECT VERSION()", is_local=True)
            self.assertIsNotNone(result)
            logger.info(f"Conexão local via DatabaseConnection bem-sucedida: {result}")
        except Exception as e:
            self.fail(f"Erro na conexão local via DatabaseConnection: {e}")
            
    def test_remote_connection(self):
        """Testa a conexão com o banco remoto."""
        # Testar conexão direta
        status, message = CredentialsLoader.test_connection(is_local=False)
        self.assertTrue(status, message)
        logger.info(f"Conexão remota: {message}")
        
        # Testar conexão via MySQLConnection
        try:
            connection = self.mysql_connection.get_remote_connection()
            self.assertTrue(connection.is_connected())
            self.mysql_connection.release_connection(connection)
            logger.info("Conexão remota via MySQLConnection bem-sucedida")
        except Exception as e:
            self.fail(f"Erro na conexão remota via MySQLConnection: {e}")
            
        # Testar conexão via DatabaseConnection
        try:
            result = self.db_connection.execute_query("SELECT VERSION()", is_local=False)
            self.assertIsNotNone(result)
            logger.info(f"Conexão remota via DatabaseConnection bem-sucedida: {result}")
        except Exception as e:
            self.fail(f"Erro na conexão remota via DatabaseConnection: {e}")
            
    def test_query_execution(self):
        """Testa a execução de consultas nos bancos local e remoto."""
        # Testar consulta no banco local
        try:
            result_local = self.db_connection.execute_query(
                "SHOW TABLES", 
                is_local=True
            )
            self.assertIsNotNone(result_local)
            logger.info(f"Tabelas no banco local: {len(result_local)}")
            for table in result_local:
                logger.info(f"  - {list(table.values())[0]}")
        except Exception as e:
            self.fail(f"Erro ao listar tabelas no banco local: {e}")
            
        # Testar consulta no banco remoto
        try:
            result_remote = self.db_connection.execute_query(
                "SHOW TABLES", 
                is_local=False
            )
            self.assertIsNotNone(result_remote)
            logger.info(f"Tabelas no banco remoto: {len(result_remote)}")
            for table in result_remote:
                logger.info(f"  - {list(table.values())[0]}")
        except Exception as e:
            self.fail(f"Erro ao listar tabelas no banco remoto: {e}")
            
    def test_cache_with_mysql(self):
        """Testa o sistema de cache com MySQL."""
        # Executar consulta sem cache
        start_time = time.time()
        result1 = self.db_connection.execute_query(
            "SELECT * FROM information_schema.tables LIMIT 100", 
            is_local=True,
            use_cache=False
        )
        no_cache_time = time.time() - start_time
        
        # Executar consulta com cache
        start_time = time.time()
        result2 = self.db_connection.execute_query(
            "SELECT * FROM information_schema.tables LIMIT 100", 
            is_local=True,
            use_cache=True
        )
        cache_time = time.time() - start_time
        
        # Executar novamente com cache
        start_time = time.time()
        result3 = self.db_connection.execute_query(
            "SELECT * FROM information_schema.tables LIMIT 100", 
            is_local=True,
            use_cache=True
        )
        cached_time = time.time() - start_time
        
        # Verificar resultados
        self.assertEqual(len(result1), len(result2))
        self.assertEqual(len(result2), len(result3))
        
        # Verificar tempos
        logger.info(f"Tempo sem cache: {no_cache_time:.4f}s")
        logger.info(f"Tempo com cache (primeira vez): {cache_time:.4f}s")
        logger.info(f"Tempo com cache (segunda vez): {cached_time:.4f}s")
        
        # A segunda consulta com cache deve ser mais rápida
        self.assertLess(cached_time, no_cache_time)
        
    def tearDown(self):
        """Limpeza após os testes."""
        # Fechar conexões
        self.mysql_connection.close()
        self.db_connection.close()

if __name__ == '__main__':
    unittest.main() 