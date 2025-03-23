"""
Módulo para gerenciamento de conexões com bancos de dados.
Implementa conexões com MySQL local e remoto.
"""

# Interface gráfica
import customtkinter as ctk
from tkinter import messagebox

# Importações locais
from app.config.settings import DATABASE, IS_DEVELOPMENT, SECURITY_DIR
from app.config.encrypted_settings import EncryptedSettings, ConfigError
from app.core.observer.auth_observer import auth_observer
from app.data.mysql.mysql_connection import MySQLConnection
from app.data.cache.query_cache import QueryCache
from app.data.cache.cache_invalidator import cache_invalidator
from app.data.cache.cache_factory import CacheFactory, CacheType

# Banco de dados
import mysql.connector
from mysql.connector import Error
import threading
import logging
from typing import Optional, Union, Dict, List
from pathlib import Path
import tempfile
import atexit
import time
import hashlib
import os
import shutil

# Logger específico para conexão com banco
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """
    Gerencia conexões com bancos de dados MySQL.
    Implementa padrão Singleton para garantir uma única instância.
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Implementa o padrão Singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa o gerenciador de conexões."""
        if not hasattr(self, 'initialized'):
            logger.info("Inicializando gerenciador de conexões de banco de dados")
            
            # Configurações criptografadas para cada banco
            self.local_settings = EncryptedSettings(SECURITY_DIR / 'mysql_local')
            self.remote_settings = EncryptedSettings(SECURITY_DIR / 'mysql_remoto')
            
            # Conexão MySQL
            self.mysql_connection = MySQLConnection(
                local_settings=self.local_settings,
                remote_settings=self.remote_settings
            )
            self.current_connection = None
            
            # Cache de consultas
            cache_type_str = os.environ.get('CACHE_TYPE', 'MEMORY')
            cache_type = CacheFactory.get_cache_type_from_string(cache_type_str)
            self.query_cache = CacheFactory.create(cache_type)
            
            logger.info(f"Usando cache do tipo: {cache_type}")
            
            # Inicializar o status label como None
            self.status_label = None
            
            # Registrar para limpeza de recursos
            atexit.register(self.close)
            
            # Marcar como inicializado
            self.initialized = True
            logger.info("Gerenciador de conexões de banco de dados inicializado")
    
    def set_status_label(self, label: ctk.CTkLabel) -> None:
        """
        Define o label para exibir mensagens de status da conexão.
        
        Args:
            label: CTkLabel onde as mensagens de status serão exibidas
        """
        logger.debug("Status label configurado para conexão de banco de dados")
        self.status_label = label
        
        # Atualiza o status inicial se necessário
        if hasattr(self, 'mysql_connection') and self.mysql_connection.is_connected():
            self.status_label.configure(text="Conectado ao banco de dados", text_color="green")
        else:
            self.status_label.configure(text="Desconectado do banco de dados", text_color="gray")
    
    def get_connection(self, is_local: bool = True) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão com o banco de dados MySQL.
        
        Args:
            is_local: Se True, retorna conexão com o banco local, caso contrário com o remoto
            
        Returns:
            MySQLConnection: Conexão com o banco de dados
        """
        try:
            if is_local:
                return self.mysql_connection.get_local_connection()
            else:
                return self.mysql_connection.get_remote_connection()
        except Exception as e:
            logger.error(f"Erro ao obter conexão MySQL: {e}")
            # Atualiza o status label se estiver configurado
            if self.status_label:
                self.status_label.configure(text=f"Erro de conexão: {str(e)}", text_color="red")
            raise
    
    def release_connection(self, connection: mysql.connector.MySQLConnection) -> None:
        """
        Libera uma conexão de volta para o pool.
        
        Args:
            connection: Conexão a ser liberada
        """
        try:
            self.mysql_connection.release_connection(connection)
        except Exception as e:
            logger.error(f"Erro ao liberar conexão: {e}")
            # Atualiza o status label se estiver configurado
            if self.status_label:
                self.status_label.configure(text=f"Erro ao liberar conexão: {str(e)}", text_color="orange")
    
    def execute_query(self, query: str, params: tuple = None, is_local: bool = True, use_cache: bool = False) -> List[Dict]:
        """
        Executa uma consulta SQL e retorna os resultados.
        
        Args:
            query: Consulta SQL
            params: Parâmetros para a consulta
            is_local: Se True, usa o banco local, caso contrário o remoto
            use_cache: Se True, usa cache para consultas de leitura
            
        Returns:
            List[Dict]: Lista de resultados como dicionários
        """
        # Verificar se pode usar cache
        if use_cache and query.strip().upper().startswith("SELECT"):
            cache_key = self._generate_cache_key(query, params)
            cached_result = self.query_cache.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Usando resultado em cache para query: {query[:50]}...")
                return cached_result
        
        # Executar consulta
        result = self.mysql_connection.execute_query(query, params, is_local)
        
        # Armazenar em cache se necessário
        if use_cache and query.strip().upper().startswith("SELECT"):
            cache_key = self._generate_cache_key(query, params)
            self.query_cache.set(cache_key, result)
        
        return result
    
    def execute_update(self, query: str, params: tuple = None, is_local: bool = True) -> int:
        """
        Executa uma operação de atualização (INSERT, UPDATE, DELETE).
        
        Args:
            query: Consulta SQL
            params: Parâmetros para a consulta
            is_local: Se True, usa o banco local, caso contrário o remoto
            
        Returns:
            int: Número de linhas afetadas
        """
        # Invalidar cache para operações de escrita
        if not query.strip().upper().startswith("SELECT"):
            self._invalidate_cache_for_table(self._extract_table_from_query(query))
        
        # Executar operação
        return self.mysql_connection.execute_update(query, params, is_local)
    
    def execute_batch(self, query: str, params_list: List[tuple], is_local: bool = True) -> int:
        """
        Executa uma operação em lote (batch).
        
        Args:
            query: Consulta SQL
            params_list: Lista de tuplas de parâmetros
            is_local: Se True, usa o banco local, caso contrário o remoto
            
        Returns:
            int: Número total de linhas afetadas
        """
        # Invalidar cache para operações de escrita
        if not query.strip().upper().startswith("SELECT"):
            self._invalidate_cache_for_table(self._extract_table_from_query(query))
        
        # Executar operação em lote
        return self.mysql_connection.execute_batch(query, params_list, is_local)
    
    def _generate_cache_key(self, query: str, params: tuple = None) -> str:
        """
        Gera uma chave de cache para uma consulta.
        
        Args:
            query: Consulta SQL
            params: Parâmetros para a consulta
            
        Returns:
            str: Chave de cache
        """
        # Normalizar query (remover espaços extras)
        normalized_query = " ".join(query.split())
        
        # Gerar hash da query e parâmetros
        key = f"{normalized_query}:{str(params)}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _extract_table_from_query(self, query: str) -> Optional[str]:
        """
        Extrai o nome da tabela de uma consulta SQL.
        Implementação simplificada, pode não funcionar para consultas complexas.
        
        Args:
            query: Consulta SQL
            
        Returns:
            Optional[str]: Nome da tabela ou None se não for possível extrair
        """
        query = query.strip().upper()
        
        if query.startswith("INSERT INTO"):
            parts = query.split("INSERT INTO")[1].strip().split()
            return parts[0].strip('`"\'')
        elif query.startswith("UPDATE"):
            parts = query.split("UPDATE")[1].strip().split()
            return parts[0].strip('`"\'')
        elif query.startswith("DELETE FROM"):
            parts = query.split("DELETE FROM")[1].strip().split()
            return parts[0].strip('`"\'')
        
            return None
    
    def _invalidate_cache_for_table(self, table_name: Optional[str]) -> None:
        """
        Invalida o cache para uma tabela específica.
        
        Args:
            table_name: Nome da tabela
        """
        if table_name:
            logger.debug(f"Invalidando cache para tabela: {table_name}")
            cache_invalidator.invalidate_table(table_name)
    
    def close(self) -> None:
        """Fecha todas as conexões e libera recursos."""
        logger.info("Fechando conexões de banco de dados")
        
        try:
            # Fechar conexão MySQL
            if hasattr(self, 'mysql_connection'):
                self.mysql_connection.close()
                logger.info("Conexões MySQL fechadas")
        except Exception as e:
            logger.error(f"Erro ao fechar conexões: {e}")
    
    def __del__(self):
        """Destrutor da classe, garante que os recursos sejam liberados."""
        try:
            self.close()
        except:
            pass

    def test_connection(self, credentials: Optional[Dict] = None) -> bool:
        """
        Testa a conexão com o banco de dados.
        
        Args:
            credentials: Credenciais para testar (opcional)
            
        Returns:
            bool: True se a conexão for bem-sucedida, False caso contrário
        """
        try:
            if self.status_label:
                self.status_label.configure(text="Testando conexão...", text_color="blue")
            
            # Usar o método test_connection da classe MySQLConnection
            result = self.mysql_connection.test_connection(credentials)
            
            # Atualizar o status label
            if self.status_label:
                if result:
                    self.status_label.configure(text="Conexão bem-sucedida", text_color="green")
                else:
                    self.status_label.configure(text="Falha na conexão", text_color="red")
            
            return result
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            if self.status_label:
                self.status_label.configure(text=f"Erro: {str(e)}", text_color="red")
            return False


# Função auxiliar para obter instância do gerenciador de conexões
def get_db_connection() -> DatabaseConnection:
    """
    Obtém a instância do gerenciador de conexões.
    
    Returns:
        DatabaseConnection: Instância do gerenciador de conexões
    """
    return DatabaseConnection()

# Alias para compatibilidade
db = get_db_connection()

# Funções auxiliares para executar consultas
def execute_query(query: str, params: tuple = None, is_local: bool = True, use_cache: bool = False) -> List[Dict]:
    """
    Executa uma consulta SQL e retorna os resultados.
    
    Args:
        query: Consulta SQL
        params: Parâmetros para a consulta
        is_local: Se True, usa o banco local, caso contrário o remoto
        use_cache: Se True, usa cache para consultas de leitura
        
        Returns:
        List[Dict]: Lista de resultados como dicionários
    """
    db = get_db_connection()
    return db.execute_query(query, params, is_local, use_cache)


def execute_update(query: str, params: tuple = None, is_local: bool = True) -> int:
    """
    Executa uma operação de atualização (INSERT, UPDATE, DELETE).
    
    Args:
        query: Consulta SQL
        params: Parâmetros para a consulta
        is_local: Se True, usa o banco local, caso contrário o remoto
        
        Returns:
        int: Número de linhas afetadas
    """
    db = get_db_connection()
    return db.execute_update(query, params, is_local)


def execute_batch(query: str, params_list: List[tuple], is_local: bool = True) -> int:
    """
    Executa uma operação em lote (batch).
    
    Args:
        query: Consulta SQL
        params_list: Lista de tuplas de parâmetros
        is_local: Se True, usa o banco local, caso contrário o remoto
        
        Returns:
        int: Número total de linhas afetadas
    """
    db = get_db_connection()
    return db.execute_batch(query, params_list, is_local)
