"""
Adaptador para Redis como sistema de cache distribuído.
Implementa a mesma interface que o sistema de cache em memória.
"""

import logging
import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RedisAdapter:
    """
    Adaptador para Redis como sistema de cache distribuído.
    
    Esta classe implementa a mesma interface que o sistema de cache em memória,
    permitindo que seja usada como substituto direto.
    
    Requer a biblioteca redis instalada: pip install redis
    """
    
    def __init__(self, prefix: str = "controlix:", host: str = "localhost", port: int = 6379, 
                 db: int = 0, password: Optional[str] = None, socket_timeout: int = 5):
        """
        Inicializa o adaptador Redis.
        
        Args:
            prefix: Prefixo para as chaves no Redis
            host: Host do servidor Redis
            port: Porta do servidor Redis
            db: Número do banco de dados Redis
            password: Senha para autenticação no Redis
            socket_timeout: Timeout para conexão com o Redis
        """
        self.prefix = prefix
        self.redis_config = {
            'host': host,
            'port': port,
            'db': db,
            'password': password,
            'socket_timeout': socket_timeout,
            'decode_responses': True  # Para retornar strings em vez de bytes
        }
        self.client = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
        self._connect()
        
    def _connect(self) -> bool:
        """
        Conecta ao servidor Redis.
        
        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário
        """
        try:
            import redis
            self.client = redis.Redis(**self.redis_config)
            # Testar conexão
            self.client.ping()
            logger.info(f"Conectado ao Redis em {self.redis_config['host']}:{self.redis_config['port']}")
            return True
        except ImportError:
            logger.error("Biblioteca redis não instalada. Use: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}")
            self.client = None
            return False
            
    def _get_full_key(self, key: str) -> str:
        """
        Obtém a chave completa com prefixo para uso no Redis.
        
        Args:
            key: Chave base
            
        Returns:
            str: Chave completa com prefixo
        """
        return f"{self.prefix}{key}"
        
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do valor
            
        Returns:
            Optional[Any]: Valor armazenado ou None se não encontrado
        """
        if not self.client:
            return None
            
        try:
            full_key = self._get_full_key(key)
            value = self.client.get(full_key)
            
            if value is None:
                self.stats['misses'] += 1
                return None
                
            # Deserializar o valor
            try:
                result = json.loads(value)
                self.stats['hits'] += 1
                return result
            except json.JSONDecodeError:
                # Se não for JSON, retorna o valor como string
                self.stats['hits'] += 1
                return value
                
        except Exception as e:
            logger.error(f"Erro ao obter valor do Redis: {e}")
            return None
            
    def set(self, key: str, value: Any, timeout: Optional[timedelta] = None) -> bool:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do valor
            value: Valor a ser armazenado
            timeout: Tempo de expiração (opcional)
            
        Returns:
            bool: True se o valor foi armazenado com sucesso, False caso contrário
        """
        if not self.client:
            return False
            
        try:
            full_key = self._get_full_key(key)
            
            # Serializar o valor
            serialized = json.dumps(value)
            
            # Calcular tempo de expiração em segundos
            expiration = int(timeout.total_seconds()) if timeout else None
            
            # Armazenar no Redis
            if expiration:
                result = self.client.setex(full_key, expiration, serialized)
            else:
                result = self.client.set(full_key, serialized)
                
            return bool(result)
            
        except Exception as e:
            logger.error(f"Erro ao armazenar valor no Redis: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do valor
            
        Returns:
            bool: True se o valor foi removido com sucesso, False caso contrário
        """
        if not self.client:
            return False
            
        try:
            full_key = self._get_full_key(key)
            result = self.client.delete(full_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Erro ao remover valor do Redis: {e}")
            return False
            
    def clear(self) -> bool:
        """
        Limpa todo o cache.
        
        Returns:
            bool: True se o cache foi limpo com sucesso, False caso contrário
        """
        if not self.client:
            return False
            
        try:
            # Limpar apenas as chaves com o prefixo
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor, f"{self.prefix}*", 100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache no Redis: {e}")
            return False
            
    def get_stats(self) -> Dict:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dict: Estatísticas do cache
        """
        if not self.client:
            return self.stats
            
        try:
            # Adicionar informações do servidor Redis
            info = self.client.info()
            memory_info = {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'used_memory_peak': info.get('used_memory_peak_human', 'N/A'),
                'total_system_memory': info.get('total_system_memory_human', 'N/A'),
                'maxmemory': info.get('maxmemory_human', 'N/A')
            }
            
            # Contar chaves com o prefixo
            keys_count = self.client.dbsize()
            
            return {
                **self.stats,
                'keys_count': keys_count,
                'memory': memory_info,
                'uptime_days': info.get('uptime_in_days', 0)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do Redis: {e}")
            return self.stats
            
    def invalidate_patterns(self, patterns: List[str]) -> int:
        """
        Invalida cache baseado em padrões.
        
        Args:
            patterns: Lista de padrões para invalidar
            
        Returns:
            int: Número de chaves invalidadas
        """
        if not self.client:
            return 0
            
        try:
            invalidated = 0
            for pattern in patterns:
                # Usar scan para encontrar chaves que correspondem ao padrão
                cursor = 0
                while True:
                    cursor, keys = self.client.scan(cursor, f"{self.prefix}{pattern}*", 100)
                    if keys:
                        invalidated += len(keys)
                        self.client.delete(*keys)
                    if cursor == 0:
                        break
                        
            if invalidated:
                self.stats['invalidations'] += invalidated
                logger.debug(f"Invalidadas {invalidated} entradas de cache no Redis")
                
            return invalidated
        except Exception as e:
            logger.error(f"Erro ao invalidar padrões no Redis: {e}")
            return 0
            
    def get_query_result(self, query: str, params: tuple) -> Optional[dict]:
        """
        Obtém resultado de query do cache.
        
        Args:
            query: Consulta SQL
            params: Parâmetros da consulta
            
        Returns:
            Optional[dict]: Resultado da consulta ou None se não encontrado
        """
        key = self._make_key(query, params)
        return self.get(key)
        
    def set_query_result(self, query: str, params: tuple, result: dict, timeout: Optional[timedelta] = None):
        """
        Armazena resultado de query no cache.
        
        Args:
            query: Consulta SQL
            params: Parâmetros da consulta
            result: Resultado da consulta
            timeout: Tempo de expiração (opcional)
        """
        key = self._make_key(query, params)
        self.set(key, result, timeout)
        
    def _make_key(self, query: str, params: tuple) -> str:
        """
        Cria chave única para query.
        
        Args:
            query: Consulta SQL
            params: Parâmetros da consulta
            
        Returns:
            str: Chave única
        """
        # Normalizar query (remover espaços extras)
        normalized_query = " ".join(query.split())
        
        # Gerar hash da query e parâmetros
        key_str = f"{normalized_query}:{str(params)}"
        return hashlib.md5(key_str.encode()).hexdigest()
        
    def health_check(self) -> bool:
        """
        Verifica se o Redis está disponível.
        
        Returns:
            bool: True se o Redis está disponível, False caso contrário
        """
        if not self.client:
            return self._connect()
            
        try:
            return bool(self.client.ping())
        except Exception:
            # Tentar reconectar
            return self._connect()
            
    def __del__(self):
        """Destrutor da classe, fecha a conexão com o Redis."""
        try:
            if self.client:
                self.client.close()
        except:
            pass

# Exemplo de uso:
# redis_cache = RedisAdapter(prefix="controlix:", host="localhost", port=6379) 