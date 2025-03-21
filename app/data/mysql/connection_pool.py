#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para gerenciamento de pools de conexões MySQL.
Implementa um pool de conexões com suporte para health check e reconexão automática.
"""

import os
import sys
import time
import logging
import threading
import mysql.connector
from mysql.connector import Error, pooling
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime, timedelta
from app.config.settings import DATABASE, MYSQL_DIR
import queue

# Configuração de logging
logger = logging.getLogger(__name__)

class MySQLPool:
    """
    Implementa um pool de conexões MySQL com suporte para health check e reconexão automática.
    
    Atributos:
        max_connections (int): Número máximo de conexões no pool
        config (dict): Configurações de conexão MySQL
        pool_name (str): Nome do pool de conexões
        connection_timeout (int): Timeout para obtenção de conexão em segundos
        idle_timeout (int): Tempo máximo que uma conexão pode ficar ociosa em segundos
        health_check_interval (int): Intervalo para verificação de saúde das conexões em segundos
    """
    
    def __init__(self, 
                 max_connections: int = 5, 
                 config: Dict[str, Any] = None,
                 pool_name: str = "mysql_pool",
                 connection_timeout: int = 30,
                 idle_timeout: int = 600,
                 health_check_interval: int = 60):
        """
        Inicializa o pool de conexões MySQL.
        
        Args:
            max_connections: Número máximo de conexões no pool
            config: Configurações de conexão MySQL (host, user, password, database, etc.)
            pool_name: Nome do pool de conexões
            connection_timeout: Timeout para obtenção de conexão em segundos
            idle_timeout: Tempo máximo que uma conexão pode ficar ociosa em segundos
            health_check_interval: Intervalo para verificação de saúde das conexões em segundos
        """
        self.max_connections = max_connections
        self.config = config or {}
        self.pool_name = pool_name
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.health_check_interval = health_check_interval
        
        self._lock = threading.RLock()
        self._pool = None
        self._health_check_thread = None
        self._stop_health_check = threading.Event()
        
        # Inicializar o pool
        self._create_pool()
        
        # Iniciar thread de health check
        self._start_health_check()
        
    def _create_pool(self) -> None:
        """Cria o pool de conexões MySQL."""
        try:
            with self._lock:
                if self._pool is None:
                    logger.info(f"Criando pool de conexões MySQL '{self.pool_name}' com {self.max_connections} conexões")
                    self._pool = mysql.connector.pooling.MySQLConnectionPool(
                        pool_name=self.pool_name,
                        pool_size=self.max_connections,
                        pool_reset_session=True,
                        **self.config
                    )
                    logger.info(f"Pool de conexões MySQL '{self.pool_name}' criado com sucesso")
        except Error as e:
            logger.error(f"Erro ao criar pool de conexões MySQL: {e}")
            raise
    
    def _start_health_check(self) -> None:
        """Inicia a thread de health check para verificar a saúde das conexões periodicamente."""
        if self._health_check_thread is None or not self._health_check_thread.is_alive():
            self._stop_health_check.clear()
            self._health_check_thread = threading.Thread(
                target=self._health_check_worker,
                daemon=True,
                name=f"mysql-pool-health-check-{self.pool_name}"
            )
            self._health_check_thread.start()
            logger.debug(f"Thread de health check iniciada para o pool '{self.pool_name}'")
    
    def _health_check_worker(self) -> None:
        """Worker para verificação periódica da saúde das conexões."""
        logger.info(f"Health check worker iniciado para o pool '{self.pool_name}'")
        while not self._stop_health_check.is_set():
            try:
                # Esperar pelo intervalo de health check
                if self._stop_health_check.wait(self.health_check_interval):
                    break
                
                # Verificar a saúde do pool
                self._check_pool_health()
            except Exception as e:
                logger.error(f"Erro no health check do pool '{self.pool_name}': {e}")
        
        logger.info(f"Health check worker finalizado para o pool '{self.pool_name}'")
    
    def _check_pool_health(self) -> None:
        """Verifica a saúde do pool de conexões e reconecta se necessário."""
        try:
            # Obter uma conexão do pool para testar
            conn = self.get_connection()
            try:
                # Executar uma query simples para verificar a conexão
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logger.debug(f"Health check do pool '{self.pool_name}' bem-sucedido")
            finally:
                # Devolver a conexão ao pool
                self.release_connection(conn)
        except Exception as e:
            logger.warning(f"Health check do pool '{self.pool_name}' falhou: {e}")
            # Tentar recriar o pool
            self._recreate_pool()
    
    def _recreate_pool(self) -> None:
        """Recria o pool de conexões em caso de falha."""
        logger.info(f"Recriando pool de conexões '{self.pool_name}'")
        try:
            with self._lock:
                # Fechar o pool atual se existir
                if self._pool is not None:
                    # Não há método direto para fechar o pool, mas podemos limpar a referência
                    self._pool = None
                
                # Criar um novo pool
                self._create_pool()
                logger.info(f"Pool de conexões '{self.pool_name}' recriado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao recriar pool de conexões '{self.pool_name}': {e}")
    
    def get_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão do pool.
        
        Returns:
            MySQLConnection: Uma conexão MySQL do pool
            
        Raises:
            Error: Se não for possível obter uma conexão
        """
        start_time = time.time()
        last_error = None
        
        while time.time() - start_time < self.connection_timeout:
            try:
                with self._lock:
                    if self._pool is None:
                        self._create_pool()
                    
                    conn = self._pool.get_connection()
                    logger.debug(f"Conexão obtida do pool '{self.pool_name}'")
                    return conn
            except Error as e:
                last_error = e
                logger.warning(f"Erro ao obter conexão do pool '{self.pool_name}': {e}")
                
                # Esperar um pouco antes de tentar novamente
                time.sleep(0.5)
                
                # Se o erro for de conexão, tentar recriar o pool
                if "Connection refused" in str(e) or "Connection timed out" in str(e):
                    self._recreate_pool()
        
        # Se chegou aqui, não foi possível obter uma conexão dentro do timeout
        error_msg = f"Timeout ao obter conexão do pool '{self.pool_name}' após {self.connection_timeout}s"
        logger.error(error_msg)
        if last_error:
            raise Error(f"{error_msg}: {last_error}")
        else:
            raise Error(error_msg)
    
    def release_connection(self, connection: mysql.connector.MySQLConnection) -> None:
        """
        Libera uma conexão de volta para o pool.
        
        Args:
            connection: A conexão MySQL a ser liberada
        """
        try:
            if connection and connection.is_connected():
                connection.close()
                logger.debug(f"Conexão liberada de volta para o pool '{self.pool_name}'")
        except Exception as e:
            logger.warning(f"Erro ao liberar conexão para o pool '{self.pool_name}': {e}")
    
    def close(self) -> None:
        """Fecha o pool de conexões e libera recursos."""
        logger.info(f"Fechando pool de conexões '{self.pool_name}'")
        
        # Parar a thread de health check
        self._stop_health_check.set()
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        # Não há método direto para fechar o pool no mysql-connector-python
        # Apenas limpamos a referência e deixamos o garbage collector fazer o resto
        with self._lock:
            self._pool = None
        
        logger.info(f"Pool de conexões '{self.pool_name}' fechado")
    
    def __del__(self):
        """Destrutor da classe, garante que os recursos sejam liberados."""
        try:
            self.close()
        except:
            pass


class MySQLConnectionManager:
    """
    Gerencia pools de conexão MySQL local e remoto.
    Implementa singleton para garantir uma única instância dos pools.
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            logger.info("Inicializando gerenciador de conexões MySQL")
            self.local_pool = None
            self.remote_pool = None
            self.initialized = True
            self._ensure_app_directories()
            self._initialize_pools()
    
    def _ensure_app_directories(self):
        """Verifica se todos os diretórios necessários para o banco de dados existem."""
        try:
            # Verificar se o diretório do MySQL existe
            if not os.path.exists(MYSQL_DIR):
                logger.warning(f"Diretório do banco de dados não existe: {MYSQL_DIR}")
            else:
                logger.info(f"Diretório do banco de dados verificado: {MYSQL_DIR}")
        except Exception as e:
            logger.error(f"Erro ao verificar diretórios necessários: {str(e)}")
    
    def _initialize_pools(self):
        """Inicializa os pools de conexão local e remoto com as configurações padrão"""
        try:
            # Configurações do banco local
            local_config = DATABASE['mysql']['local']
            
            # Configurações do banco remoto
            remote_config = DATABASE['mysql']['remote']
            
            # Inicializar pools
            self.initialize_pools(local_config, remote_config)
        except Exception as e:
            logger.error(f"Erro ao inicializar pools de conexão MySQL: {e}")
    
    def initialize_pools(self, 
                         local_config: Dict[str, Any], 
                         remote_config: Dict[str, Any]) -> None:
        """
        Inicializa os pools de conexão local e remoto.
        
        Args:
            local_config (Dict[str, Any]): Configuração do banco local
            remote_config (Dict[str, Any]): Configuração do banco remoto
        """
        with self._lock:
            # Fechar pools existentes
            if self.local_pool:
                self.local_pool.close()
            
            if self.remote_pool:
                self.remote_pool.close()
            
            # Criar novos pools
            self.local_pool = MySQLPool(
                pool_name="mysql_local_pool",
                **local_config
            )
            
            self.remote_pool = MySQLPool(
                pool_name="mysql_remote_pool",
                **remote_config
            )
            
            logger.info("Pools de conexão MySQL inicializados com sucesso")
    
    def get_local_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão do pool local.
        
        Returns:
            mysql.connector.MySQLConnection: Conexão MySQL local
        """
        if not self.local_pool:
            raise ValueError("Pool de conexão local não inicializado")
        
        return self.local_pool.get_connection()
    
    def get_remote_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão do pool remoto.
        
        Returns:
            mysql.connector.MySQLConnection: Conexão MySQL remota
        """
        if not self.remote_pool:
            raise ValueError("Pool de conexão remoto não inicializado")
        
        return self.remote_pool.get_connection()
    
    def close_pools(self) -> None:
        """Fecha todos os pools de conexão"""
        with self._lock:
            if self.local_pool:
                self.local_pool.close()
                self.local_pool = None
            
            if self.remote_pool:
                self.remote_pool.close()
                self.remote_pool = None
            
            logger.info("Pools de conexão MySQL fechados")


# Instância global do gerenciador de conexões
mysql_connection_manager = MySQLConnectionManager()

# Funções de conveniência para obter conexões
def get_local_connection() -> mysql.connector.MySQLConnection:
    """
    Obtém uma conexão do pool local.
    
    Returns:
        mysql.connector.MySQLConnection: Conexão MySQL local
    """
    return mysql_connection_manager.get_local_connection()

def get_remote_connection() -> mysql.connector.MySQLConnection:
    """
    Obtém uma conexão do pool remoto.
    
    Returns:
        mysql.connector.MySQLConnection: Conexão MySQL remota
    """
    return mysql_connection_manager.get_remote_connection()

def initialize_mysql_pools(local_config: Dict[str, Any], remote_config: Dict[str, Any]) -> None:
    """
    Inicializa os pools de conexão MySQL.
    
    Args:
        local_config (Dict[str, Any]): Configuração do banco local
        remote_config (Dict[str, Any]): Configuração do banco remoto
    """
    mysql_connection_manager.initialize_pools(local_config, remote_config)

def close_mysql_pools() -> None:
    """Fecha todos os pools de conexão MySQL"""
    mysql_connection_manager.close_pools() 