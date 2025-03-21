"""
Módulo para gerenciar conexões MySQL.
"""

import mysql.connector
from mysql.connector import Error, pooling
import logging
from typing import Optional, Dict, List, Any, Set, Tuple
from app.config.encrypted_settings import EncryptedSettings
from app.config.cache.cache_factory import CacheFactory

logger = logging.getLogger(__name__)

class MySQLConnection:
    """Gerencia conexões com bancos MySQL local e remoto."""
    
    def __init__(self, local_settings: EncryptedSettings, remote_settings: EncryptedSettings):
        """
        Inicializa o gerenciador de conexões MySQL.
        
        Args:
            local_settings: Configurações do banco local
            remote_settings: Configurações do banco remoto
        """
        self.local_settings = local_settings
        self.remote_settings = remote_settings
        
        # Pools de conexão
        self.local_pool = None
        self.remote_pool = None
        
        # Cache
        self.cache_factory = CacheFactory()
        self.cache = self.cache_factory.get_cache()
        
        # Inicializar pools
        self._init_local_pool()
        self._init_remote_pool()
    
    def _get_db_config(self, is_local: bool = True) -> Dict[str, Any]:
        """
        Obtém configurações do banco de dados.
        
        Args:
            is_local: Se True, retorna configurações do banco local
            
        Returns:
            Dict[str, Any]: Configurações do banco
        """
        settings = self.local_settings if is_local else self.remote_settings
        
        try:
            config = settings.decrypt_env()
            return {
                'host': config.get('DB_HOST', 'localhost'),
                'port': int(config.get('DB_PORT', '3306')),
                'user': config.get('DB_USER', 'root'),
                'password': config.get('DB_PASSWORD', ''),
                'database': config.get('DB_NAME', ''),
                'pool_name': 'local_pool' if is_local else 'remote_pool',
                'pool_size': 5
            }
        except Exception as e:
            logger.error(f"Erro ao obter configurações do banco {'local' if is_local else 'remoto'}: {e}")
            raise
    
    def _init_local_pool(self) -> None:
        """Inicializa o pool de conexões local."""
        try:
            if not self.local_pool:
                config = self._get_db_config(is_local=True)
                self.local_pool = mysql.connector.pooling.MySQLConnectionPool(**config)
                logger.info("Pool de conexões local inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar pool local: {e}")
            raise
    
    def _init_remote_pool(self) -> None:
        """Inicializa o pool de conexões remoto."""
        try:
            if not self.remote_pool:
                config = self._get_db_config(is_local=False)
                self.remote_pool = mysql.connector.pooling.MySQLConnectionPool(**config)
                logger.info("Pool de conexões remoto inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar pool remoto: {e}")
            raise
    
    def get_local_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão do pool local.
        
        Returns:
            MySQLConnection: Conexão com o banco local
        """
        try:
            if not self.local_pool:
                self._init_local_pool()
            return self.local_pool.get_connection()
        except Exception as e:
            logger.error(f"Erro ao obter conexão local: {e}")
            raise
    
    def get_remote_connection(self) -> mysql.connector.MySQLConnection:
        """
        Obtém uma conexão do pool remoto.
        
        Returns:
            MySQLConnection: Conexão com o banco remoto
        """
        try:
            if not self.remote_pool:
                self._init_remote_pool()
            return self.remote_pool.get_connection()
        except Exception as e:
            logger.error(f"Erro ao obter conexão remota: {e}")
            raise
    
    def release_connection(self, connection: mysql.connector.MySQLConnection) -> None:
        """
        Libera uma conexão de volta para o pool.
        
        Args:
            connection: Conexão a ser liberada
        """
        try:
            if connection and not connection.is_closed():
                connection.close()
        except Exception as e:
            logger.error(f"Erro ao liberar conexão: {e}")
    
    def _get_cache_key(self, query: str, params: tuple = None, is_local: bool = True) -> str:
        """
        Gera uma chave de cache para a consulta.
        
        Args:
            query: Consulta SQL
            params: Parâmetros da consulta
            is_local: Se True, usa o banco local
            
        Returns:
            str: Chave de cache
        """
        key = f"mysql_{'local' if is_local else 'remote'}_{hash(query)}"
        if params:
            key += f"_{hash(str(params))}"
        return key
    
    def execute_query(self, query: str, params: tuple = None, is_local: bool = True,
                     use_cache: bool = True, cache_ttl: Optional[int] = None) -> List[Dict]:
        """
        Executa uma consulta SQL e retorna os resultados.
        
        Args:
            query: Consulta SQL
            params: Parâmetros para a consulta
            is_local: Se True, usa o banco local
            use_cache: Se True, usa cache
            cache_ttl: Tempo de vida do cache em segundos
            
        Returns:
            List[Dict]: Lista de resultados
        """
        # Verificar cache
        if use_cache:
            cache_key = self._get_cache_key(query, params, is_local)
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit para query: {query}")
                return cached_result
        
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Criar cursor que retorna dicionários
            cursor = connection.cursor(dictionary=True)
            
            # Executar consulta
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            
            # Armazenar em cache se necessário
            if use_cache:
                self.cache.set(cache_key, result, ttl=cache_ttl)
            
            return result
            
        except Error as e:
            logger.error(f"Erro ao executar query: {e}")
            raise
        finally:
            if connection:
                self.release_connection(connection)
    
    def execute_update(self, query: str, params: tuple = None, is_local: bool = True,
                      invalidate_cache: bool = True) -> int:
        """
        Executa uma operação de atualização.
        
        Args:
            query: Consulta SQL
            params: Parâmetros para a consulta
            is_local: Se True, usa o banco local
            invalidate_cache: Se True, invalida o cache
            
        Returns:
            int: Número de linhas afetadas
        """
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Criar cursor
            cursor = connection.cursor()
            
            # Executar operação
            cursor.execute(query, params or ())
            connection.commit()
            
            # Invalidar cache se necessário
            if invalidate_cache:
                self.cache.clear()
            
            return cursor.rowcount
            
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Erro ao executar update: {e}")
            raise
        finally:
            if connection:
                self.release_connection(connection)
    
    def execute_batch(self, query: str, params_list: List[tuple], is_local: bool = True,
                     invalidate_cache: bool = True) -> int:
        """
        Executa uma operação em lote.
        
        Args:
            query: Consulta SQL
            params_list: Lista de parâmetros
            is_local: Se True, usa o banco local
            invalidate_cache: Se True, invalida o cache
            
        Returns:
            int: Número total de linhas afetadas
        """
        connection = None
        try:
            # Obter conexão apropriada
            connection = self.get_local_connection() if is_local else self.get_remote_connection()
            
            # Criar cursor
            cursor = connection.cursor()
            
            # Executar operações em lote
            cursor.executemany(query, params_list)
            connection.commit()
            
            # Invalidar cache se necessário
            if invalidate_cache:
                self.cache.clear()
            
            return cursor.rowcount
            
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Erro ao executar batch: {e}")
            raise
        finally:
            if connection:
                self.release_connection(connection)
    
    def close(self) -> None:
        """Fecha todas as conexões."""
        logger.info("Fechando conexões MySQL")
        
        try:
            # Fechar pools
            if self.local_pool:
                for cnx in self.local_pool._cnx_queue:
                    cnx.close()
            if self.remote_pool:
                for cnx in self.remote_pool._cnx_queue:
                    cnx.close()
            
            # Fechar cache
            if hasattr(self.cache, 'close'):
                self.cache.close()
                    
            logger.info("Todas as conexões MySQL fechadas")
            
        except Exception as e:
            logger.error(f"Erro ao fechar conexões: {e}")
    
    def get_table_structure(self, table_name: str, is_local: bool = True) -> Dict[str, Any]:
        """
        Obtém a estrutura de uma tabela usando SHOW CREATE TABLE.
        
        Args:
            table_name: Nome da tabela
            is_local: Se True, usa o banco local
            
        Returns:
            Dict[str, Any]: Estrutura da tabela
        """
        try:
            query = f"SHOW CREATE TABLE {table_name}"
            result = self.execute_query(query, is_local=is_local, use_cache=False)
            if result:
                return {
                    'table_name': table_name,
                    'create_statement': result[0]['Create Table']
                }
            return None
        except Error as e:
            logger.error(f"Erro ao obter estrutura da tabela {table_name}: {e}")
            return None

    def get_all_tables(self, is_local: bool = True) -> List[str]:
        """
        Obtém lista de todas as tabelas no banco.
        
        Args:
            is_local: Se True, usa o banco local
            
        Returns:
            List[str]: Lista de nomes de tabelas
        """
        try:
            query = "SHOW TABLES"
            result = self.execute_query(query, is_local=is_local, use_cache=False)
            return [list(row.values())[0] for row in result]
        except Error as e:
            logger.error(f"Erro ao obter lista de tabelas: {e}")
            return []

    def compare_table_structures(self, table_name: str) -> Tuple[bool, Optional[str]]:
        """
        Compara a estrutura de uma tabela entre os bancos local e remoto.
        
        Args:
            table_name: Nome da tabela
            
        Returns:
            Tuple[bool, Optional[str]]: (são_iguais, diferenças)
        """
        try:
            local_structure = self.get_table_structure(table_name, is_local=True)
            remote_structure = self.get_table_structure(table_name, is_local=False)
            
            if not local_structure or not remote_structure:
                return False, "Tabela não encontrada em um dos bancos"
            
            if local_structure['create_statement'] == remote_structure['create_statement']:
                return True, None
            
            return False, "Estruturas diferentes"
            
        except Error as e:
            logger.error(f"Erro ao comparar estruturas da tabela {table_name}: {e}")
            return False, str(e)

    def sync_table_structure(self, table_name: str, source_is_local: bool = True) -> bool:
        """
        Sincroniza a estrutura de uma tabela entre os bancos.
        
        Args:
            table_name: Nome da tabela
            source_is_local: Se True, usa estrutura local como fonte
            
        Returns:
            bool: True se sincronização foi bem sucedida
        """
        try:
            source_structure = self.get_table_structure(table_name, is_local=source_is_local)
            if not source_structure:
                logger.error(f"Tabela {table_name} não encontrada no banco {'local' if source_is_local else 'remoto'}")
                return False
            
            # Criar tabela no destino se não existir
            create_statement = source_structure['create_statement']
            self.execute_update(create_statement, is_local=not source_is_local)
            
            logger.info(f"Estrutura da tabela {table_name} sincronizada com sucesso")
            return True
            
        except Error as e:
            logger.error(f"Erro ao sincronizar estrutura da tabela {table_name}: {e}")
            return False

    def check_and_sync_structures(self, source_is_local: bool = True) -> Dict[str, Any]:
        """
        Verifica e sincroniza estruturas de todas as tabelas.
        
        Args:
            source_is_local: Se True, usa estruturas locais como fonte
            
        Returns:
            Dict[str, Any]: Relatório da sincronização
        """
        report = {
            'success': True,
            'synced_tables': [],
            'failed_tables': [],
            'errors': []
        }
        
        try:
            # Obter lista de tabelas da fonte
            source_tables = self.get_all_tables(is_local=source_is_local)
            
            for table in source_tables:
                try:
                    if self.sync_table_structure(table, source_is_local):
                        report['synced_tables'].append(table)
                    else:
                        report['failed_tables'].append(table)
                except Exception as e:
                    report['failed_tables'].append(table)
                    report['errors'].append(f"Erro na tabela {table}: {str(e)}")
            
            if report['failed_tables']:
                report['success'] = False
                
            return report
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar estruturas: {e}")
            report['success'] = False
            report['errors'].append(str(e))
            return report 