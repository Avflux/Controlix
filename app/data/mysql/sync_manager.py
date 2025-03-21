"""
Módulo para sincronização entre bancos de dados MySQL local e remoto.
Implementa sincronização bidirecional com prioridade para o banco remoto.
"""

import logging
import json
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set

from app.data.mysql.mysql_connection import MySQLConnection

# Configuração de logging
logger = logging.getLogger(__name__)

class SyncDirection(Enum):
    """Direção da sincronização entre bancos MySQL."""
    LOCAL_TO_REMOTE = "local_to_remote"
    REMOTE_TO_LOCAL = "remote_to_local"
    BIDIRECTIONAL = "bidirectional"

class ConflictResolutionStrategy(Enum):
    """Estratégias de resolução de conflitos durante a sincronização."""
    REMOTE_WINS = "remote_wins"  # Prioridade para o banco remoto
    LOCAL_WINS = "local_wins"    # Prioridade para o banco local
    MANUAL = "manual"            # Resolução manual pelo usuário
    NEWEST_WINS = "newest_wins"  # Prioridade para a versão mais recente

class TableConfig:
    """
    Configuração para sincronização de uma tabela.
    
    Atributos:
        name (str): Nome da tabela
        primary_key (str): Nome da coluna de chave primária
        version_column (str): Nome da coluna de versão
        timestamp_column (str): Nome da coluna de timestamp
        conflict_strategy (ConflictResolutionStrategy): Estratégia de resolução de conflitos
        sync_columns (List[str]): Lista de colunas a serem sincronizadas (None = todas)
    """
    
    def __init__(
        self,
        name: str,
        primary_key: str = "id",
        version_column: str = "version",
        timestamp_column: str = "last_modified",
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.REMOTE_WINS,
        sync_columns: Optional[List[str]] = None
    ):
        self.name = name
        self.primary_key = primary_key
        self.version_column = version_column
        self.timestamp_column = timestamp_column
        self.conflict_strategy = conflict_strategy
        self.sync_columns = sync_columns

# Tabelas padrão para sincronização
DEFAULT_TABLES = {
    "equipes": TableConfig(
        name="equipes",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "usuarios": TableConfig(
        name="usuarios",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "funcionarios": TableConfig(
        name="funcionarios",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "atividades": TableConfig(
        name="atividades",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "user_lock_unlock": TableConfig(
        name="user_lock_unlock",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "logs_sistema": TableConfig(
        name="logs_sistema",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    ),
    "system_config": TableConfig(
        name="system_config",
        primary_key="id",
        conflict_strategy=ConflictResolutionStrategy.REMOTE_WINS
    )
}

class MySQLSyncManager:
    """
    Gerenciador de sincronização entre bancos MySQL local e remoto.
    
    Atributos:
        db_connection (MySQLConnection): Conexão com os bancos MySQL
        tables_config (Dict[str, TableConfig]): Configuração das tabelas a serem sincronizadas
        sync_interval (int): Intervalo entre sincronizações automáticas (em segundos)
        auto_sync (bool): Se True, realiza sincronização automática periódica
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        """Implementa o padrão Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        db_connection: Optional[MySQLConnection] = None,
        tables_config: Optional[Dict[str, TableConfig]] = None,
        sync_interval: int = 300,
        auto_sync: bool = False
    ):
        """
        Inicializa o gerenciador de sincronização.
        
        Args:
            db_connection: Conexão com os bancos MySQL (se None, cria uma nova)
            tables_config: Configuração das tabelas a serem sincronizadas (se None, usa DEFAULT_TABLES)
            sync_interval: Intervalo entre sincronizações automáticas em segundos (padrão: 300s = 5min)
            auto_sync: Se True, inicia thread de sincronização automática
        """
        # Evitar reinicialização se já inicializado (padrão Singleton)
        if hasattr(self, 'initialized'):
            return
        
        logger.info("Inicializando gerenciador de sincronização MySQL")
        
        # Conexão com os bancos
        self.db_connection = db_connection or MySQLConnection()
        
        # Configuração das tabelas
        self.tables_config = tables_config or DEFAULT_TABLES
        
        # Configuração de sincronização automática
        self.sync_interval = sync_interval
        self.auto_sync = auto_sync
        self.sync_thread = None
        self.stop_sync = threading.Event()
        
        # Verificar tabelas de controle
        self.verify_tables_exist()
        
        # Iniciar sincronização automática se configurado
        if self.auto_sync:
            self._start_auto_sync()
        
        # Marcar como inicializado
        self.initialized = True
        logger.info("Gerenciador de sincronização MySQL inicializado")
    
    def _ensure_sync_tables(self) -> None:
        """Verifica se as tabelas de controle de sincronização existem."""
        try:
            # Verificar tabela sync_log
            sync_log_exists = self._table_exists("sync_log", is_local=True) and self._table_exists("sync_log", is_local=False)
            if not sync_log_exists:
                logger.warning("Tabela sync_log não existe em um ou ambos os bancos. A sincronização pode não funcionar corretamente.")
            
            # Verificar tabela sync_conflicts
            sync_conflicts_exists = self._table_exists("sync_conflicts", is_local=True) and self._table_exists("sync_conflicts", is_local=False)
            if not sync_conflicts_exists:
                logger.warning("Tabela sync_conflicts não existe em um ou ambos os bancos. A resolução de conflitos pode não funcionar corretamente.")
            
            # Verificar tabela sync_metadata
            sync_metadata_exists = self._table_exists("sync_metadata", is_local=True) and self._table_exists("sync_metadata", is_local=False)
            if not sync_metadata_exists:
                logger.warning("Tabela sync_metadata não existe em um ou ambos os bancos. O controle de sincronização pode não funcionar corretamente.")
            else:
                # Verificar metadados apenas se a tabela existir
                self._check_metadata_exists("last_sync")
            
            logger.info("Verificação das tabelas de controle de sincronização concluída")
        except Exception as e:
            logger.error(f"Erro ao verificar tabelas de controle de sincronização: {e}")
            raise
    
    def _ensure_table_exists(self, table_name: str, create_sql: str) -> None:
        """
        Verifica se uma tabela existe e loga um aviso se não existir.
        
        Args:
            table_name: Nome da tabela
            create_sql: SQL para criar a tabela (não utilizado, mantido para compatibilidade)
        """
        try:
            # Verificar se a tabela existe no banco local
            local_exists = self._table_exists(table_name, is_local=True)
            if not local_exists:
                logger.warning(f"Tabela {table_name} não existe no banco local. A sincronização pode não funcionar corretamente.")
            
            # Verificar se a tabela existe no banco remoto
            remote_exists = self._table_exists(table_name, is_local=False)
            if not remote_exists:
                logger.warning(f"Tabela {table_name} não existe no banco remoto. A sincronização pode não funcionar corretamente.")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela {table_name}: {e}")
            raise
    
    def _check_metadata_exists(self, key: str) -> bool:
        """
        Verifica se um registro de metadados existe.
        
        Args:
            key: Chave do metadado
            
        Returns:
            bool: True se o metadado existe em ambos os bancos, False caso contrário
        """
        try:
            # Verificar se o metadado existe no banco local
            query = "SELECT COUNT(*) as count FROM sync_metadata WHERE key_name = %s"
            local_result = self.db_connection.execute_query(query, (key,), is_local=True)
            local_exists = local_result[0]["count"] > 0
            
            # Verificar se o metadado existe no banco remoto
            remote_result = self.db_connection.execute_query(query, (key,), is_local=False)
            remote_exists = remote_result[0]["count"] > 0
            
            if not local_exists:
                logger.warning(f"Metadado {key} não existe no banco local. A sincronização pode não funcionar corretamente.")
            
            if not remote_exists:
                logger.warning(f"Metadado {key} não existe no banco remoto. A sincronização pode não funcionar corretamente.")
            
            return local_exists and remote_exists
        except Exception as e:
            logger.error(f"Erro ao verificar metadado {key}: {e}")
            return False
    
    def _table_exists(self, table_name: str, is_local: bool = True) -> bool:
        """
        Verifica se uma tabela existe no banco de dados.
        
        Args:
            table_name: Nome da tabela
            is_local: Se True, verifica no banco local, caso contrário no remoto
            
        Returns:
            bool: True se a tabela existe, False caso contrário
        """
        try:
            # Obter nome do banco de dados
            db_name = self.db_connection.local_config["database"] if is_local else self.db_connection.remote_config["database"]
            
            # Consultar tabela no banco
            query = """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            """
            result = self.db_connection.execute_query(query, (db_name, table_name), is_local=is_local)
            
            return result[0]["count"] > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência da tabela {table_name}: {e}")
            return False
    
    def _ensure_metadata_exists(self, key: str, default_value: Any) -> None:
        """
        Verifica se um registro de metadados existe.
        
        Args:
            key: Chave do metadado
            default_value: Valor padrão (não utilizado, mantido para compatibilidade)
        """
        try:
            # Verificar se o metadado existe no banco local
            query = "SELECT COUNT(*) as count FROM sync_metadata WHERE key_name = %s"
            result = self.db_connection.execute_query(query, (key,), is_local=True)
            
            if result[0]["count"] == 0:
                logger.warning(f"Metadado {key} não existe no banco local. A sincronização pode não funcionar corretamente.")
            
            # Verificar se o metadado existe no banco remoto
            result = self.db_connection.execute_query(query, (key,), is_local=False)
            
            if result[0]["count"] == 0:
                logger.warning(f"Metadado {key} não existe no banco remoto. A sincronização pode não funcionar corretamente.")
        except Exception as e:
            logger.error(f"Erro ao verificar metadado {key}: {e}")
            # Não propagar erro para não interromper a inicialização
    
    def _start_auto_sync(self) -> None:
        """Inicia a thread de sincronização automática."""
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.stop_sync.clear()
            self.sync_thread = threading.Thread(
                target=self._auto_sync_worker,
                daemon=True,
                name="mysql-sync-thread"
            )
            self.sync_thread.start()
            logger.info(f"Thread de sincronização automática iniciada (intervalo: {self.sync_interval}s)")
    
    def _auto_sync_worker(self) -> None:
        """Worker para sincronização automática periódica."""
        logger.info("Worker de sincronização automática iniciado")
        
        while not self.stop_sync.is_set():
            try:
                # Sincronizar
                self.synchronize(SyncDirection.BIDIRECTIONAL)
                
                # Aguardar até o próximo intervalo ou até o evento de parada
                self.stop_sync.wait(self.sync_interval)
            except Exception as e:
                logger.error(f"Erro na sincronização automática: {e}")
                # Aguardar um pouco antes de tentar novamente
                time.sleep(10)
        
        logger.info("Worker de sincronização automática finalizado")
    
    def stop_auto_sync(self) -> None:
        """Para a thread de sincronização automática."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.info("Parando thread de sincronização automática")
            self.stop_sync.set()
            self.sync_thread.join(timeout=10)
            if self.sync_thread.is_alive():
                logger.warning("Thread de sincronização não finalizou dentro do timeout")
            else:
                logger.info("Thread de sincronização finalizada")
    
    def verify_tables_exist(self) -> Dict[str, Dict[str, bool]]:
        """
        Verifica se todas as tabelas configuradas para sincronização existem nos bancos local e remoto.
        
        Returns:
            Dict[str, Dict[str, bool]]: Dicionário com o status de existência de cada tabela
        """
        result = {}
        
        # Verificar tabelas de controle de sincronização
        sync_tables = ["sync_log", "sync_conflicts", "sync_metadata"]
        for table in sync_tables:
            local_exists = self._table_exists(table, is_local=True)
            remote_exists = self._table_exists(table, is_local=False)
            
            result[table] = {
                "local": local_exists,
                "remote": remote_exists
            }
            
            if not local_exists:
                logger.warning(f"Tabela de controle {table} não existe no banco local")
            if not remote_exists:
                logger.warning(f"Tabela de controle {table} não existe no banco remoto")
        
        # Verificar tabelas configuradas para sincronização
        for table_name in self.tables_config.keys():
            local_exists = self._table_exists(table_name, is_local=True)
            remote_exists = self._table_exists(table_name, is_local=False)
            
            result[table_name] = {
                "local": local_exists,
                "remote": remote_exists
            }
            
            if not local_exists:
                logger.warning(f"Tabela {table_name} não existe no banco local")
            if not remote_exists:
                logger.warning(f"Tabela {table_name} não existe no banco remoto")
        
        return result
    
    def synchronize(self, direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> Dict[str, Any]:
        """
        Sincroniza os bancos de dados MySQL local e remoto.
        
        Args:
            direction: Direção da sincronização
            
        Returns:
            Dict[str, Any]: Estatísticas da sincronização
        """
        logger.info(f"Iniciando sincronização ({direction.value})")
        
        # Verificar se todas as tabelas existem
        tables_status = self.verify_tables_exist()
        missing_tables = [table for table, status in tables_status.items() 
                         if not status["local"] or not status["remote"]]
        
        if missing_tables:
            logger.warning(f"As seguintes tabelas não existem em um ou ambos os bancos: {', '.join(missing_tables)}")
            logger.warning("A sincronização pode não funcionar corretamente ou pode falhar para estas tabelas")
        
        stats = {
            "start_time": datetime.now(),
            "end_time": None,
            "direction": direction.value,
            "tables_synced": 0,
            "records_synced": 0,
            "conflicts": 0,
            "errors": 0,
            "tables": {}
        }
        
        try:
            # Sincronizar do remoto para o local (prioridade para o remoto)
            if direction in [SyncDirection.REMOTE_TO_LOCAL, SyncDirection.BIDIRECTIONAL]:
                remote_to_local_stats = self._sync_remote_to_local()
                stats["tables_synced"] += remote_to_local_stats["tables_synced"]
                stats["records_synced"] += remote_to_local_stats["records_synced"]
                stats["conflicts"] += remote_to_local_stats["conflicts"]
                stats["errors"] += remote_to_local_stats["errors"]
                
                for table, table_stats in remote_to_local_stats["tables"].items():
                    if table not in stats["tables"]:
                        stats["tables"][table] = {"remote_to_local": table_stats}
                    else:
                        stats["tables"][table]["remote_to_local"] = table_stats
            
            # Sincronizar do local para o remoto
            if direction in [SyncDirection.LOCAL_TO_REMOTE, SyncDirection.BIDIRECTIONAL]:
                local_to_remote_stats = self._sync_local_to_remote()
                stats["tables_synced"] += local_to_remote_stats["tables_synced"]
                stats["records_synced"] += local_to_remote_stats["records_synced"]
                stats["conflicts"] += local_to_remote_stats["conflicts"]
                stats["errors"] += local_to_remote_stats["errors"]
                
                for table, table_stats in local_to_remote_stats["tables"].items():
                    if table not in stats["tables"]:
                        stats["tables"][table] = {"local_to_remote": table_stats}
                    else:
                        stats["tables"][table]["local_to_remote"] = table_stats
            
            # Atualizar metadados de última sincronização
            self._update_last_sync_metadata()
            
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
            
            logger.info(f"Sincronização concluída: {stats['records_synced']} registros sincronizados, "
                       f"{stats['conflicts']} conflitos, {stats['errors']} erros")
            
            return stats
        except Exception as e:
            logger.error(f"Erro durante sincronização: {e}")
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
            stats["error"] = str(e)
            return stats

    def _sync_remote_to_local(self) -> Dict[str, Any]:
        """
        Sincroniza dados do banco remoto para o local.
        
        Returns:
            Dict[str, Any]: Estatísticas da sincronização
        """
        logger.info("Sincronizando do banco remoto para o local")
        
        stats = {
            "tables_synced": 0,
            "records_synced": 0,
            "conflicts": 0,
            "errors": 0,
            "tables": {}
        }
        
        # Obter última sincronização
        last_sync = self._get_last_sync_timestamp()
        
        # Sincronizar cada tabela configurada
        for table_name, config in self.tables_config.items():
            try:
                table_stats = self._sync_table_remote_to_local(table_name, config, last_sync)
                
                stats["records_synced"] += table_stats["records_synced"]
                stats["conflicts"] += table_stats["conflicts"]
                stats["errors"] += table_stats["errors"]
                stats["tables"][table_name] = table_stats
                stats["tables_synced"] += 1
                
                logger.info(f"Tabela {table_name} sincronizada do remoto para o local: "
                           f"{table_stats['records_synced']} registros, "
                           f"{table_stats['conflicts']} conflitos, "
                           f"{table_stats['errors']} erros")
            except Exception as e:
                logger.error(f"Erro ao sincronizar tabela {table_name} do remoto para o local: {e}")
                stats["errors"] += 1
                stats["tables"][table_name] = {
                    "error": str(e),
                    "records_synced": 0,
                    "conflicts": 0,
                    "errors": 1
                }
        
        return stats
    
    def _sync_local_to_remote(self) -> Dict[str, Any]:
        """
        Sincroniza dados do banco local para o remoto.
        
        Returns:
            Dict[str, Any]: Estatísticas da sincronização
        """
        logger.info("Sincronizando do banco local para o remoto")
        
        stats = {
            "tables_synced": 0,
            "records_synced": 0,
            "conflicts": 0,
            "errors": 0,
            "tables": {}
        }
        
        # Obter última sincronização
        last_sync = self._get_last_sync_timestamp()
        
        # Sincronizar cada tabela configurada
        for table_name, config in self.tables_config.items():
            try:
                table_stats = self._sync_table_local_to_remote(table_name, config, last_sync)
                
                stats["records_synced"] += table_stats["records_synced"]
                stats["conflicts"] += table_stats["conflicts"]
                stats["errors"] += table_stats["errors"]
                stats["tables"][table_name] = table_stats
                stats["tables_synced"] += 1
                
                logger.info(f"Tabela {table_name} sincronizada do local para o remoto: "
                           f"{table_stats['records_synced']} registros, "
                           f"{table_stats['conflicts']} conflitos, "
                           f"{table_stats['errors']} erros")
            except Exception as e:
                logger.error(f"Erro ao sincronizar tabela {table_name} do local para o remoto: {e}")
                stats["errors"] += 1
                stats["tables"][table_name] = {
                    "error": str(e),
                    "records_synced": 0,
                    "conflicts": 0,
                    "errors": 1
                }
        
        return stats
    
    def _sync_table_remote_to_local(self, table_name: str, config: TableConfig, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """
        Sincroniza uma tabela específica do banco remoto para o local.
        
        Args:
            table_name: Nome da tabela
            config: Configuração da tabela
            last_sync: Timestamp da última sincronização
            
        Returns:
            Dict[str, Any]: Estatísticas da sincronização da tabela
        """
        logger.debug(f"Sincronizando tabela {table_name} do remoto para o local")
        
        stats = {
            "records_synced": 0,
            "conflicts": 0,
            "errors": 0
        }
        
        try:
            # Verificar se a tabela existe em ambos os bancos
            local_exists = self._table_exists(table_name, is_local=True)
            remote_exists = self._table_exists(table_name, is_local=False)
            
            if not local_exists:
                logger.warning(f"Tabela {table_name} não existe no banco local. Sincronização ignorada.")
                stats["errors"] += 1
                return stats
                
            if not remote_exists:
                logger.warning(f"Tabela {table_name} não existe no banco remoto. Sincronização ignorada.")
                stats["errors"] += 1
                return stats
            
            # Obter colunas da tabela
            columns = self._get_table_columns(table_name, is_local=False)
            
            # Filtrar colunas se especificado na configuração
            if config.sync_columns:
                columns = [col for col in columns if col in config.sync_columns]
            
            # Garantir que as colunas de controle estejam incluídas
            required_columns = [config.primary_key, config.version_column, config.timestamp_column]
            for col in required_columns:
                if col not in columns:
                    logger.warning(f"Coluna de controle {col} não encontrada na tabela {table_name}. A sincronização pode falhar.")
                    columns.append(col)
            
            # Construir consulta para obter registros alterados no remoto
            columns_str = ", ".join(columns)
            where_clause = ""
            params = []
            
            if last_sync:
                where_clause = f"WHERE {config.timestamp_column} >= %s"
                params = [last_sync]
            
            query = f"SELECT {columns_str} FROM {table_name} {where_clause}"
            
            # Obter registros alterados no remoto
            remote_records = self.db_connection.execute_query(query, tuple(params), is_local=False)
            
            # Processar cada registro
            for remote_record in remote_records:
                try:
                    # Obter ID do registro
                    record_id = remote_record[config.primary_key]
                    
                    # Verificar se o registro existe no banco local
                    local_record = self._get_record_by_id(table_name, config.primary_key, record_id, is_local=True)
                    
                    if not local_record:
                        # Registro não existe no local, inserir
                        self._insert_record(table_name, remote_record, is_local=True)
                        stats["records_synced"] += 1
                        logger.debug(f"Registro {record_id} da tabela {table_name} inserido no banco local")
                    else:
                        # Registro existe, verificar versões
                        remote_version = remote_record[config.version_column]
                        local_version = local_record[config.version_column]
                        
                        if remote_version > local_version:
                            # Versão remota é mais recente, atualizar local
                            self._update_record(table_name, config.primary_key, record_id, remote_record, is_local=True)
                            stats["records_synced"] += 1
                            logger.debug(f"Registro {record_id} da tabela {table_name} atualizado no banco local")
                        elif remote_version < local_version:
                            # Conflito: versão local é mais recente que a remota
                            # Mas como a prioridade é do remoto, atualizamos o local mesmo assim
                            if config.conflict_strategy == ConflictResolutionStrategy.REMOTE_WINS:
                                self._update_record(table_name, config.primary_key, record_id, remote_record, is_local=True)
                                stats["records_synced"] += 1
                                stats["conflicts"] += 1
                                logger.debug(f"Conflito resolvido para registro {record_id} da tabela {table_name} (REMOTE_WINS)")
                            else:
                                # Registrar conflito para resolução manual ou outra estratégia
                                self._register_conflict(table_name, record_id, local_record, remote_record, config)
                                stats["conflicts"] += 1
                                logger.debug(f"Conflito registrado para registro {record_id} da tabela {table_name}")
                except Exception as e:
                    logger.error(f"Erro ao processar registro {remote_record.get(config.primary_key)} da tabela {table_name}: {e}")
                    stats["errors"] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Erro ao sincronizar tabela {table_name} do remoto para o local: {e}")
            stats["errors"] += 1
            return stats
    
    def _sync_table_local_to_remote(self, table_name: str, config: TableConfig, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """
        Sincroniza uma tabela específica do banco local para o remoto.
        
        Args:
            table_name: Nome da tabela
            config: Configuração da tabela
            last_sync: Timestamp da última sincronização
            
        Returns:
            Dict[str, Any]: Estatísticas da sincronização da tabela
        """
        logger.debug(f"Sincronizando tabela {table_name} do local para o remoto")
        
        stats = {
            "records_synced": 0,
            "conflicts": 0,
            "errors": 0
        }
        
        try:
            # Verificar se a tabela existe em ambos os bancos
            local_exists = self._table_exists(table_name, is_local=True)
            remote_exists = self._table_exists(table_name, is_local=False)
            
            if not local_exists:
                logger.warning(f"Tabela {table_name} não existe no banco local. Sincronização ignorada.")
                stats["errors"] += 1
                return stats
                
            if not remote_exists:
                logger.warning(f"Tabela {table_name} não existe no banco remoto. Sincronização ignorada.")
                stats["errors"] += 1
                return stats
            
            # Obter colunas da tabela
            columns = self._get_table_columns(table_name, is_local=True)
            
            # Filtrar colunas se especificado na configuração
            if config.sync_columns:
                columns = [col for col in columns if col in config.sync_columns]
            
            # Garantir que as colunas de controle estejam incluídas
            required_columns = [config.primary_key, config.version_column, config.timestamp_column]
            for col in required_columns:
                if col not in columns:
                    logger.warning(f"Coluna de controle {col} não encontrada na tabela {table_name}. A sincronização pode falhar.")
                    columns.append(col)
            
            # Construir consulta para obter registros alterados no local
            columns_str = ", ".join(columns)
            where_clause = ""
            params = []
            
            if last_sync:
                where_clause = f"WHERE {config.timestamp_column} >= %s"
                params = [last_sync]
            
            query = f"SELECT {columns_str} FROM {table_name} {where_clause}"
            
            # Obter registros alterados no local
            local_records = self.db_connection.execute_query(query, tuple(params), is_local=True)
            
            # Processar cada registro
            for local_record in local_records:
                try:
                    # Obter ID do registro
                    record_id = local_record[config.primary_key]
                    
                    # Verificar se o registro existe no banco remoto
                    remote_record = self._get_record_by_id(table_name, config.primary_key, record_id, is_local=False)
                    
                    if not remote_record:
                        # Registro não existe no remoto, inserir
                        self._insert_record(table_name, local_record, is_local=False)
                        stats["records_synced"] += 1
                        logger.debug(f"Registro {record_id} da tabela {table_name} inserido no banco remoto")
                    else:
                        # Registro existe, verificar versões
                        local_version = local_record[config.version_column]
                        remote_version = remote_record[config.version_column]
                        
                        if local_version > remote_version:
                            # Versão local é mais recente, atualizar remoto
                            self._update_record(table_name, config.primary_key, record_id, local_record, is_local=False)
                            stats["records_synced"] += 1
                            logger.debug(f"Registro {record_id} da tabela {table_name} atualizado no banco remoto")
                        elif local_version < remote_version:
                            # Conflito: versão remota é mais recente que a local
                            # Como a prioridade é do remoto, não fazemos nada aqui
                            # O registro será atualizado na sincronização remoto -> local
                            stats["conflicts"] += 1
                            logger.debug(f"Conflito ignorado para registro {record_id} da tabela {table_name} (REMOTE_WINS)")
                except Exception as e:
                    logger.error(f"Erro ao processar registro {local_record.get(config.primary_key)} da tabela {table_name}: {e}")
                    stats["errors"] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Erro ao sincronizar tabela {table_name} do local para o remoto: {e}")
            stats["errors"] += 1
            return stats
    
    def _get_table_columns(self, table_name: str, is_local: bool = True) -> List[str]:
        """
        Obtém as colunas de uma tabela.
        
        Args:
            table_name: Nome da tabela
            is_local: Se True, consulta o banco local, caso contrário o remoto
            
        Returns:
            List[str]: Lista de nomes das colunas
        """
        try:
            # Obter nome do banco de dados
            db_name = self.db_connection.local_config["database"] if is_local else self.db_connection.remote_config["database"]
            
            # Consultar colunas da tabela
            query = """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """
            result = self.db_connection.execute_query(query, (db_name, table_name), is_local=is_local)
            
            return [row["COLUMN_NAME"] for row in result]
        except Exception as e:
            logger.error(f"Erro ao obter colunas da tabela {table_name}: {e}")
            raise
    
    def _get_record_by_id(self, table_name: str, id_column: str, record_id: Any, is_local: bool = True) -> Optional[Dict[str, Any]]:
        """
        Obtém um registro pelo ID.
        
        Args:
            table_name: Nome da tabela
            id_column: Nome da coluna de ID
            record_id: Valor do ID
            is_local: Se True, consulta o banco local, caso contrário o remoto
            
        Returns:
            Optional[Dict[str, Any]]: Registro encontrado ou None se não existir
        """
        try:
            query = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
            result = self.db_connection.execute_query(query, (record_id,), is_local=is_local)
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Erro ao obter registro {record_id} da tabela {table_name}: {e}")
            raise
    
    def _insert_record(self, table_name: str, record: Dict[str, Any], is_local: bool = True) -> None:
        """
        Insere um registro na tabela.
        
        Args:
            table_name: Nome da tabela
            record: Dados do registro
            is_local: Se True, insere no banco local, caso contrário no remoto
        """
        try:
            # Verificar se a tabela existe
            if not self._table_exists(table_name, is_local=is_local):
                logger.warning(f"Tabela {table_name} não existe no banco {'local' if is_local else 'remoto'}. Inserção ignorada.")
                return
                
            # Verificar se as colunas existem
            table_columns = self._get_table_columns(table_name, is_local=is_local)
            record_columns = list(record.keys())
            missing_columns = [col for col in record_columns if col not in table_columns]
            
            if missing_columns:
                logger.warning(f"Colunas {', '.join(missing_columns)} não existem na tabela {table_name}. Inserção pode falhar.")
            
            # Remover campos que não devem ser inseridos manualmente
            record_copy = record.copy()
            auto_fields = ["id"]  # Campos que são gerados automaticamente
            
            for field in auto_fields:
                if field in record_copy and field != record_copy.get("primary_key"):
                    del record_copy[field]
            
            # Construir query de inserção
            columns = list(record_copy.keys())
            placeholders = ["%s"] * len(columns)
            
            columns_str = ", ".join(columns)
            placeholders_str = ", ".join(placeholders)
            
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders_str})"
            
            # Executar inserção
            values = tuple(record_copy[col] for col in columns)
            self.db_connection.execute_update(query, values, is_local=is_local)
        except Exception as e:
            logger.error(f"Erro ao inserir registro na tabela {table_name}: {e}")
            raise
    
    def _update_record(self, table_name: str, id_column: str, record_id: Any, record: Dict[str, Any], is_local: bool = True) -> None:
        """
        Atualiza um registro na tabela.
        
        Args:
            table_name: Nome da tabela
            id_column: Nome da coluna de ID
            record_id: Valor do ID
            record: Dados do registro
            is_local: Se True, atualiza no banco local, caso contrário no remoto
        """
        try:
            # Verificar se a tabela existe
            if not self._table_exists(table_name, is_local=is_local):
                logger.warning(f"Tabela {table_name} não existe no banco {'local' if is_local else 'remoto'}. Atualização ignorada.")
                return
                
            # Verificar se as colunas existem
            table_columns = self._get_table_columns(table_name, is_local=is_local)
            record_columns = list(record.keys())
            missing_columns = [col for col in record_columns if col not in table_columns]
            
            if missing_columns:
                logger.warning(f"Colunas {', '.join(missing_columns)} não existem na tabela {table_name}. Atualização pode falhar.")
            
            # Remover campos que não devem ser atualizados
            record_copy = record.copy()
            if id_column in record_copy:
                del record_copy[id_column]
            
            # Construir query de atualização
            set_clauses = [f"{col} = %s" for col in record_copy.keys()]
            set_clause = ", ".join(set_clauses)
            
            query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = %s"
            
            # Executar atualização
            values = tuple(record_copy[col] for col in record_copy.keys())
            values = values + (record_id,)
            
            self.db_connection.execute_update(query, values, is_local=is_local)
        except Exception as e:
            logger.error(f"Erro ao atualizar registro {record_id} na tabela {table_name}: {e}")
            raise
    
    def _register_conflict(self, table_name: str, record_id: Any, local_record: Dict[str, Any], remote_record: Dict[str, Any], config: TableConfig) -> None:
        """
        Registra um conflito de sincronização.
        
        Args:
            table_name: Nome da tabela
            record_id: ID do registro
            local_record: Dados do registro local
            remote_record: Dados do registro remoto
            config: Configuração da tabela
        """
        try:
            # Verificar se a tabela sync_conflicts existe
            if not self._table_exists("sync_conflicts", is_local=True):
                logger.warning(f"Tabela sync_conflicts não existe no banco local. O conflito não será registrado.")
                return
            
            # Converter registros para JSON
            local_data = json.dumps(local_record)
            remote_data = json.dumps(remote_record)
            
            # Obter versões e timestamps
            local_version = local_record[config.version_column]
            remote_version = remote_record[config.version_column]
            local_modified = local_record[config.timestamp_column]
            remote_modified = remote_record[config.timestamp_column]
            
            # Inserir conflito na tabela de conflitos
            query = """
                INSERT INTO sync_conflicts (
                    table_name, record_id, local_data, remote_data,
                    local_version, remote_version, local_modified, remote_modified,
                    resolution_strategy, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                table_name, str(record_id), local_data, remote_data,
                local_version, remote_version, local_modified, remote_modified,
                config.conflict_strategy.value
            )
            
            # Inserir no banco local
            self.db_connection.execute_update(query, params, is_local=True)
            
            logger.info(f"Conflito registrado para o registro {record_id} da tabela {table_name}")
        except Exception as e:
            logger.error(f"Erro ao registrar conflito para o registro {record_id} da tabela {table_name}: {e}")
            # Não propagar o erro para não interromper a sincronização
    
    def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Obtém o timestamp da última sincronização.
        
        Returns:
            Optional[datetime]: Timestamp da última sincronização ou None se nunca sincronizado
        """
        try:
            query = "SELECT value FROM sync_metadata WHERE key_name = 'last_sync'"
            result = self.db_connection.execute_query(query, is_local=True)
            
            if result and result[0]["value"]:
                return datetime.fromisoformat(json.loads(result[0]["value"]))
            
            return None
        except Exception as e:
            # Se ocorrer erro (como coluna não encontrada), apenas retorna None
            logger.warning(f"Erro ao obter timestamp da última sincronização: {e}")
            return None
    
    def _update_last_sync_metadata(self) -> None:
        """Verifica e atualiza o metadado de última sincronização se existir."""
        try:
            now = datetime.now().isoformat()
            
            # Verificar se a tabela sync_metadata existe e tem a coluna key_name
            try:
                # Verificar se o registro existe
                query = "SELECT id FROM sync_metadata WHERE key_name = 'last_sync'"
                local_result = self.db_connection.execute_query(query, is_local=True)
                remote_result = self.db_connection.execute_query(query, is_local=False)
                
                # Atualizar apenas se o registro existir
                if local_result:
                    # Atualizar registro existente no banco local
                    query = "UPDATE sync_metadata SET value = %s, updated_at = NOW() WHERE key_name = 'last_sync'"
                    self.db_connection.execute_update(query, (json.dumps(now),), is_local=True)
                    logger.debug(f"Metadado de última sincronização atualizado no banco local: {now}")
                else:
                    logger.warning("Metadado 'last_sync' não existe no banco local. A sincronização pode não funcionar corretamente.")
                
                if remote_result:
                    # Atualizar registro existente no banco remoto
                    query = "UPDATE sync_metadata SET value = %s, updated_at = NOW() WHERE key_name = 'last_sync'"
                    self.db_connection.execute_update(query, (json.dumps(now),), is_local=False)
                    logger.debug(f"Metadado de última sincronização atualizado no banco remoto: {now}")
                else:
                    logger.warning("Metadado 'last_sync' não existe no banco remoto. A sincronização pode não funcionar corretamente.")
            except Exception as e:
                logger.warning(f"Erro ao verificar/atualizar metadado de última sincronização: {e}")
                # Não propagar o erro para não interromper a sincronização
        except Exception as e:
            logger.warning(f"Erro ao atualizar metadado de última sincronização: {e}")
            # Não propagar o erro para não interromper a sincronização
    
    def close(self) -> None:
        """Fecha o gerenciador de sincronização e libera recursos."""
        logger.info("Fechando gerenciador de sincronização MySQL")
        
        # Parar sincronização automática
        self.stop_auto_sync()
        
        logger.info("Gerenciador de sincronização MySQL fechado")
    
    def __del__(self):
        """Destrutor da classe, garante que os recursos sejam liberados."""
        try:
            self.close()
        except:
            pass


# Função auxiliar para obter instância do gerenciador de sincronização
def get_sync_manager() -> MySQLSyncManager:
    """
    Obtém a instância do gerenciador de sincronização MySQL.
    
    Returns:
        MySQLSyncManager: Instância do gerenciador de sincronização
    """
    return MySQLSyncManager()
