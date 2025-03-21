"""
Módulo para gerenciamento de conexões MySQL.
Implementa classes para conexão com bancos de dados MySQL locais e remotos.
"""

import mysql.connector
from mysql.connector import Error
import logging
import os
import json
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path
import threading
from app.data.mysql.connection_pool import MySQLPool
from app.data.mysql.credentials_loader import credentials_loader

# Logger específico para conexões MySQL
logger = logging.getLogger(__name__)

class MySQLConnection:
    """
    Gerencia conexões com bancos de dados MySQL locais e remotos.
    
    Atributos:
        local_config (dict): Configurações para o banco MySQL local
        remote_config (dict): Configurações para o banco MySQL remoto
        local_pool (MySQLPool): Pool de conexões para o banco local
        remote_pool (MySQLPool): Pool de conexões para o banco remoto
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Implementa o padrão Singleton para garantir uma única instância."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa a classe de conexão MySQL."""
        if not hasattr(self, 'initialized'):
            logger.info("Inicializando gerenciador de conexões MySQL")
            
            # Configurações padrão
            self.local_config = None
            self.remote_config = None
            self.local_pool = None
            self.remote_pool = None
            
            # Carregar configurações
            self._load_config()
            
            # Inicializar pools de conexão
            self._initialize_pools()
            
            # Marcar como inicializado
            self.initialized = True
            logger.info("Gerenciador de conexões MySQL inicializado")
    
    def _load_config(self) -> None:
        """Carrega as configurações de conexão MySQL."""
        try:
            # Configurar variáveis de ambiente
            credentials_loader.setup_environment_variables()
            
            # Configuração para MySQL local
            self.local_config = {
                'host': os.environ.get('MYSQL_LOCAL_HOST', 'localhost'),
                'port': int(os.environ.get('MYSQL_LOCAL_PORT', '3306')),
                'user': os.environ.get('MYSQL_LOCAL_USER', 'root'),
                'password': os.environ.get('MYSQL_LOCAL_PASSWORD', ''),
                'database': os.environ.get('MYSQL_LOCAL_DATABASE', 'controlix_local'),
                'charset': 'utf8mb4',
                'use_pure': True,
                'autocommit': False,
                'connection_timeout': 10
            }
            
            # Configuração para MySQL remoto
            self.remote_config = {
                'host': os.environ.get('MYSQL_REMOTE_HOST', ''),
                'port': int(os.environ.get('MYSQL_REMOTE_PORT', '3306')),
                'user': os.environ.get('MYSQL_REMOTE_USER', ''),
                'password': os.environ.get('MYSQL_REMOTE_PASSWORD', ''),
                'database': os.environ.get('MYSQL_REMOTE_DATABASE', 'controlix_remote'),
                'charset': 'utf8mb4',
                'use_pure': True,
                'autocommit': False,
                'connection_timeout': 15
            }
            
            logger.debug("Configurações MySQL carregadas")
        except Exception as e:
            logger.error(f"Erro ao carregar configurações MySQL: {e}")
            raise
    
    def _initialize_pools(self) -> None:
        """Inicializa os pools de conexão MySQL."""
        try:
            # Criar pool local
            if self.local_config and self.local_config['host']:
                self.local_pool = MySQLPool(
                    max_connections=5,
                    config=self.local_config,
                    pool_name="mysql_local_pool",
                    connection_timeout=30,
                    idle_timeout=600,
                    health_check_interval=60
                )
                logger.info("Pool de conexões MySQL local inicializado")
            else:
                logger.warning("Configuração de MySQL local incompleta, pool não inicializado")
            
            # Criar pool remoto se configurado
            if self.remote_config and self.remote_config['host']:
                self.remote_pool = MySQLPool(
                    max_connections=3,
                    config=self.remote_config,
                    pool_name="mysql_remote_pool",
                    connection_timeout=45,
                    idle_timeout=300,
                    health_check_interval=120
                )
                logger.info("Pool de conexões MySQL remoto inicializado")
            else:
                logger.warning("Configuração de MySQL remoto incompleta, pool não inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar pools de conexão MySQL: {e}")
            raise
    
    def get_local_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão com o banco MySQL local.
        
        Returns:
            MySQLConnection: Conexão com o banco local
            
        Raises:
            Error: Se não for possível obter uma conexão
        """
        if not self.local_pool:
            raise Error("Pool de conexões MySQL local não inicializado")
        
        return self.local_pool.get_connection()
    
    def get_remote_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão com o banco MySQL remoto.
        
        Returns:
            MySQLConnection: Conexão com o banco remoto
            
        Raises:
            Error: Se não for possível obter uma conexão
        """
        if not self.remote_pool:
            raise Error("Pool de conexões MySQL remoto não inicializado")
        
        return self.remote_pool.get_connection()
    
    def release_connection(self, connection: mysql.connector.MySQLConnection) -> None:
        """
        Libera uma conexão de volta para o pool.
        
        Args:
            connection: A conexão MySQL a ser liberada
        """
        if not connection:
            return
        
        try:
            if connection.is_connected():
                connection.close()
                logger.debug("Conexão MySQL liberada")
        except Exception as e:
            logger.warning(f"Erro ao liberar conexão MySQL: {e}")
    
    def execute_query(self, query: str, params: tuple = None, is_local: bool = True) -> List[Dict]:
        """
        Executa uma consulta SQL e retorna os resultados como lista de dicionários.
        
        Args:
            query: Consulta SQL a ser executada
            params: Parâmetros para a consulta (opcional)
            is_local: Se True, usa o banco local, caso contrário usa o remoto
            
        Returns:
            List[Dict]: Lista de resultados como dicionários
            
        Raises:
            Error: Se ocorrer um erro na execução da consulta
        """
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Configurar cursor para retornar dicionários
            cursor = connection.cursor(dictionary=True)
            
            # Executar consulta
            cursor.execute(query, params or ())
            
            # Obter resultados
            results = cursor.fetchall()
            
            # Fechar cursor
            cursor.close()
            
            return results
        except Error as e:
            logger.error(f"Erro ao executar consulta MySQL: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise
        finally:
            # Liberar conexão
            if connection:
                self.release_connection(connection)
    
    def execute_update(self, query: str, params: tuple = None, is_local: bool = True) -> int:
        """
        Executa uma operação de atualização (INSERT, UPDATE, DELETE) e retorna o número de linhas afetadas.
        
        Args:
            query: Consulta SQL a ser executada
            params: Parâmetros para a consulta (opcional)
            is_local: Se True, usa o banco local, caso contrário usa o remoto
            
        Returns:
            int: Número de linhas afetadas
            
        Raises:
            Error: Se ocorrer um erro na execução da operação
        """
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Criar cursor
            cursor = connection.cursor()
            
            # Executar operação
            cursor.execute(query, params or ())
            
            # Obter número de linhas afetadas
            row_count = cursor.rowcount
            
            # Commit da transação
            connection.commit()
            
            # Fechar cursor
            cursor.close()
            
            return row_count
        except Error as e:
            # Rollback em caso de erro
            if connection:
                connection.rollback()
            
            logger.error(f"Erro ao executar atualização MySQL: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise
        finally:
            # Liberar conexão
            if connection:
                self.release_connection(connection)
    
    def execute_batch(self, query: str, params_list: List[tuple], is_local: bool = True) -> int:
        """
        Executa uma operação em lote (batch) e retorna o número total de linhas afetadas.
        
        Args:
            query: Consulta SQL a ser executada
            params_list: Lista de tuplas de parâmetros
            is_local: Se True, usa o banco local, caso contrário usa o remoto
            
        Returns:
            int: Número total de linhas afetadas
            
        Raises:
            Error: Se ocorrer um erro na execução da operação
        """
        if not params_list:
            return 0
        
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Criar cursor
            cursor = connection.cursor()
            
            # Executar operações em lote
            row_count = 0
            for params in params_list:
                cursor.execute(query, params)
                row_count += cursor.rowcount
            
            # Commit da transação
            connection.commit()
            
            # Fechar cursor
            cursor.close()
            
            return row_count
        except Error as e:
            # Rollback em caso de erro
            if connection:
                connection.rollback()
            
            logger.error(f"Erro ao executar operação em lote MySQL: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Número de parâmetros: {len(params_list)}")
            raise
        finally:
            # Liberar conexão
            if connection:
                self.release_connection(connection)
    
    def close(self) -> None:
        """Fecha os pools de conexão e libera recursos."""
        logger.info("Fechando pools de conexão MySQL")
        
        if self.local_pool:
            try:
                self.local_pool.close()
                logger.info("Pool de conexões MySQL local fechado")
            except Exception as e:
                logger.error(f"Erro ao fechar pool de conexões MySQL local: {e}")
        
        if self.remote_pool:
            try:
                self.remote_pool.close()
                logger.info("Pool de conexões MySQL remoto fechado")
            except Exception as e:
                logger.error(f"Erro ao fechar pool de conexões MySQL remoto: {e}")
    
    def __del__(self):
        """Destrutor da classe, garante que os recursos sejam liberados."""
        try:
            self.close()
        except:
            pass 