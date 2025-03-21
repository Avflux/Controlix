"""
Adaptador Redis para o sistema de cache.
"""

import redis
import logging
import json
from typing import Any, Dict, Optional, Union
from app.config.cache.cache_config import CacheConfig

logger = logging.getLogger(__name__)

class RedisAdapter:
    """Adaptador para usar Redis como cache."""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Inicializa o adaptador Redis.
        
        Args:
            config: Configurações de cache (opcional)
        """
        self.config = config or CacheConfig()
        self._client = None
        self._connect()
    
    def _connect(self) -> None:
        """Estabelece conexão com o Redis."""
        try:
            if not self._client:
                redis_config = self.config.get_redis_config()
                self._client = redis.Redis(
                    host=redis_config['host'],
                    port=redis_config['port'],
                    db=redis_config['db'],
                    password=redis_config['password'],
                    ssl=redis_config['ssl'],
                    socket_timeout=redis_config['socket_timeout'],
                    retry_on_timeout=redis_config['retry_on_timeout'],
                    max_connections=redis_config['max_connections']
                )
                logger.info("Conexão com Redis estabelecida")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}")
            raise
    
    def _serialize(self, value: Any) -> str:
        """
        Serializa um valor para armazenamento.
        
        Args:
            value: Valor a ser serializado
            
        Returns:
            str: Valor serializado
        """
        try:
            return json.dumps(value)
        except Exception as e:
            logger.error(f"Erro ao serializar valor: {e}")
            raise
    
    def _deserialize(self, value: Optional[bytes]) -> Any:
        """
        Deserializa um valor do armazenamento.
        
        Args:
            value: Valor a ser deserializado
            
        Returns:
            Any: Valor deserializado
        """
        if value is None:
            return None
        try:
            return json.loads(value.decode('utf-8'))
        except Exception as e:
            logger.error(f"Erro ao deserializar valor: {e}")
            raise
    
    def get(self, key: str) -> Any:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do valor
            
        Returns:
            Any: Valor armazenado ou None se não encontrado
        """
        try:
            value = self._client.get(key)
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Erro ao obter valor do Redis: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do valor
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos (opcional)
            
        Returns:
            bool: True se armazenado com sucesso
        """
        try:
            serialized = self._serialize(value)
            if ttl is None:
                ttl = self.config.get_ttl()
            return self._client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Erro ao armazenar valor no Redis: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do valor
            
        Returns:
            bool: True se removido com sucesso
        """
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.error(f"Erro ao remover valor do Redis: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Limpa todo o cache.
        
        Returns:
            bool: True se limpo com sucesso
        """
        try:
            return self._client.flushdb()
        except Exception as e:
            logger.error(f"Erro ao limpar Redis: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Verifica se uma chave existe no cache.
        
        Args:
            key: Chave a verificar
            
        Returns:
            bool: True se a chave existe
        """
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Erro ao verificar existência no Redis: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        Obtém o tempo de vida restante de uma chave.
        
        Args:
            key: Chave a verificar
            
        Returns:
            int: Tempo restante em segundos ou -1 se não existe
        """
        try:
            return self._client.ttl(key)
        except Exception as e:
            logger.error(f"Erro ao obter TTL do Redis: {e}")
            return -1
    
    def keys(self, pattern: str = '*') -> list:
        """
        Lista chaves que correspondem ao padrão.
        
        Args:
            pattern: Padrão de busca (default: '*')
            
        Returns:
            list: Lista de chaves encontradas
        """
        try:
            return [key.decode('utf-8') for key in self._client.keys(pattern)]
        except Exception as e:
            logger.error(f"Erro ao listar chaves do Redis: {e}")
            return []
    
    def info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre o servidor Redis.
        
        Returns:
            Dict[str, Any]: Informações do servidor
        """
        try:
            info = self._client.info()
            return {
                'version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'uptime': info.get('uptime_in_seconds'),
                'total_keys': len(self.keys())
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do Redis: {e}")
            return {}
    
    def close(self) -> None:
        """Fecha a conexão com o Redis."""
        try:
            if self._client:
                self._client.close()
                logger.info("Conexão com Redis fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar conexão com Redis: {e}")
    
    def __del__(self):
        """Destrutor da classe."""
        self.close() 