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
            logger.debug(f"Chaves encontradas no arquivo .env.encrypted: {', '.join(config.keys())}")
            
            # Mapeamento de possíveis nomes de chaves para os nomes padrão
            key_mappings = {
                'host': ['DB_HOST', 'HOST', 'MYSQL_HOST', 'DATABASE_HOST'],
                'port': ['DB_PORT', 'PORT', 'MYSQL_PORT', 'DATABASE_PORT'],
                'user': ['DB_USER', 'USER', 'MYSQL_USER', 'DATABASE_USER', 'USERNAME'],
                'password': ['DB_PASSWORD', 'PASSWORD', 'MYSQL_PASSWORD', 'DATABASE_PASSWORD', 'PASSWD'],
                'database': ['DB_NAME', 'DATABASE', 'MYSQL_DATABASE', 'DATABASE_NAME', 'DB']
            }
            
            # Valores padrão para cada chave
            defaults = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': '',
                'pool_name': 'local_pool' if is_local else 'remote_pool',
                'pool_size': 5
            }
            
            # Construir configuração final
            final_config = {}
            for key, possible_names in key_mappings.items():
                # Procurar por qualquer uma das possíveis chaves no arquivo de configuração
                value = None
                for name in possible_names:
                    if name in config:
                        value = config[name]
                        logger.debug(f"Usando {name} para {key}: {value if 'PASSWORD' not in name else '***'}")
                        break
                
                # Se não encontrou, usa o valor padrão
                if value is None:
                    value = defaults[key]
                    logger.debug(f"Usando valor padrão para {key}: {value if key != 'password' else '***'}")
                
                # Converter porta para int se necessário
                if key == 'port' and isinstance(value, str):
                    try:
                        value = int(value)
                    except ValueError:
                        logger.warning(f"Valor de porta inválido: {value}, usando padrão: {defaults['port']}")
                        value = defaults['port']
                
                final_config[key] = value
            
            # Adicionar as chaves não mapeadas
            final_config['pool_name'] = defaults['pool_name']
            final_config['pool_size'] = defaults['pool_size']
            
            # Log da configuração final (sem senha)
            safe_config = {k: v if k != 'password' else '***' for k, v in final_config.items()}
            logger.info(f"Configuração final para banco {'local' if is_local else 'remoto'}: {safe_config}")
            
            return final_config
            
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
            # Fechar pools com tratamento adequado de erros
            if hasattr(self, 'local_pool') and self.local_pool:
                try:
                    # Verificar se _cnx_queue é acessível como uma lista
                    if hasattr(self.local_pool, '_cnx_queue'):
                        # Tenta converter para lista se for iterável
                        try:
                            connections = list(self.local_pool._cnx_queue)
                            for cnx in connections:
                                try:
                                    if hasattr(cnx, 'close') and not cnx.is_closed():
                                        cnx.close()
                                except:
                                    pass
                        except:
                            logger.debug("Não foi possível iterar sobre local_pool._cnx_queue")
                except Exception as e:
                    logger.debug(f"Erro ao fechar conexões do pool local: {e}")
            
            if hasattr(self, 'remote_pool') and self.remote_pool:
                try:
                    # Verificar se _cnx_queue é acessível como uma lista
                    if hasattr(self.remote_pool, '_cnx_queue'):
                        # Tenta converter para lista se for iterável
                        try:
                            connections = list(self.remote_pool._cnx_queue)
                            for cnx in connections:
                                try:
                                    if hasattr(cnx, 'close') and not cnx.is_closed():
                                        cnx.close()
                                except:
                                    pass
                        except:
                            logger.debug("Não foi possível iterar sobre remote_pool._cnx_queue")
                except Exception as e:
                    logger.debug(f"Erro ao fechar conexões do pool remoto: {e}")
            
            # Fechar cache
            if hasattr(self, 'cache') and hasattr(self.cache, 'close'):
                try:
                    self.cache.close()
                except Exception as e:
                    logger.debug(f"Erro ao fechar cache: {e}")
                    
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
            
    def test_connection(self, credentials: Optional[Dict] = None) -> bool:
        """
        Testa a conexão com o banco de dados MySQL.
        
        Args:
            credentials: Credenciais para testar (opcional)
            
        Returns:
            bool: True se a conexão for bem-sucedida, False caso contrário
        """
        try:
            logger.info("Testando conexão com o banco de dados MySQL")
            
            # Se foram fornecidas credenciais, usar conexão temporária
            if credentials and all(k in credentials for k in ['user', 'password']):
                logger.debug("Testando com credenciais fornecidas")
                
                # Obter configuração base do banco local
                config = self._get_db_config(is_local=True)
                
                # Sobrescrever credenciais
                config['user'] = credentials['user']
                config['password'] = credentials['password']
                
                # Remover configurações de pool para conexão única
                if 'pool_name' in config:
                    del config['pool_name']
                if 'pool_size' in config:
                    del config['pool_size']
                
                # Testar conexão
                try:
                    logger.debug(f"Tentando conectar com usuário: {config['user']}")
                    connection = mysql.connector.connect(**config)
                    connection.close()
                    
                    # Se autenticação bem-sucedida, notificar observer
                    from app.core.observer.auth_observer import auth_observer
                    auth_observer.notify_auth_success(user_data={
                        'name_id': credentials['user'],
                        'user': credentials['user']
                    })
                    
                    logger.info("Conexão de teste bem-sucedida")
                    return True
                except mysql.connector.Error as e:
                    logger.error(f"Falha na conexão de teste: {e}")
                    return False
            
            # Caso contrário, testar usando os pools existentes
            else:
                logger.debug("Testando conexão com os pools existentes")
                
                # Testar conexão local
                local_conn = None
                try:
                    local_conn = self.get_local_connection()
                    logger.info("Conexão local testada com sucesso")
                    local_ok = True
                except Exception as e:
                    logger.error(f"Falha no teste de conexão local: {e}")
                    local_ok = False
                finally:
                    if local_conn:
                        self.release_connection(local_conn)
                
                # Testar conexão remota
                remote_conn = None
                try:
                    remote_conn = self.get_remote_connection()
                    logger.info("Conexão remota testada com sucesso")
                    remote_ok = True
                except Exception as e:
                    logger.error(f"Falha no teste de conexão remota: {e}")
                    remote_ok = False
                finally:
                    if remote_conn:
                        self.release_connection(remote_conn)
                
                # Pelo menos uma conexão deve funcionar
                return local_ok or remote_ok
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
            
    def is_connected(self) -> bool:
        """
        Verifica se pelo menos uma das conexões (local ou remota) está funcionando.
        
        Returns:
            bool: True se alguma conexão estiver ativa
        """
        # Tenta obter e liberar uma conexão para verificar
        try:
            # Testar conexão local
            try:
                conn = self.get_local_connection()
                self.release_connection(conn)
                return True
            except:
                # Se falhar no local, tenta o remoto
                try:
                    conn = self.get_remote_connection()
                    self.release_connection(conn)
                    return True
                except:
                    return False
        except:
            return False 