"""
Fábrica para criar instâncias de cache.
"""

from typing import Optional, Dict, Any, Protocol
import logging
import redis
from pathlib import Path
from .cache_config import CacheConfig

logger = logging.getLogger(__name__)

class Cache(Protocol):
    """Interface para implementações de cache."""
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do valor.
            
        Returns:
            Any: Valor armazenado ou None se não encontrado.
        """
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave para o valor.
            value: Valor a ser armazenado.
            ttl: Tempo de vida em segundos (opcional).
        """
        ...
    
    def delete(self, key: str) -> None:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do valor a ser removido.
        """
        ...
    
    def clear(self) -> None:
        """Remove todos os valores do cache."""
        ...
    
    def close(self) -> None:
        """Fecha a conexão com o cache (se aplicável)."""
        ...

class MemoryCache:
    """Implementação de cache em memória."""
    
    def __init__(self, config: CacheConfig):
        """
        Inicializa o cache em memória.
        
        Args:
            config: Configurações do cache.
        """
        self.config = config
        self.data: Dict[str, Any] = {}
        self.ttls: Dict[str, float] = {}
        logger.info("Cache em memória inicializado")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do valor.
            
        Returns:
            Any: Valor armazenado ou None se não encontrado.
        """
        import time
        
        if key not in self.data:
            return None
        
        # Verificar TTL
        if key in self.ttls and time.time() > self.ttls[key]:
            self.delete(key)
            return None
        
        return self.data[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave para o valor.
            value: Valor a ser armazenado.
            ttl: Tempo de vida em segundos (opcional).
        """
        import time
        
        # Verificar tamanho máximo
        if len(self.data) >= self.config.memory_max_size:
            # Remover item mais antigo
            oldest_key = next(iter(self.data))
            self.delete(oldest_key)
        
        self.data[key] = value
        
        # Definir TTL
        if ttl is not None:
            self.ttls[key] = time.time() + ttl
        elif self.config.default_ttl > 0:
            self.ttls[key] = time.time() + self.config.default_ttl
    
    def delete(self, key: str) -> None:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do valor a ser removido.
        """
        self.data.pop(key, None)
        self.ttls.pop(key, None)
    
    def clear(self) -> None:
        """Remove todos os valores do cache."""
        self.data.clear()
        self.ttls.clear()
    
    def close(self) -> None:
        """Fecha a conexão com o cache (não aplicável para cache em memória)."""
        self.clear()

class RedisCache:
    """Implementação de cache usando Redis."""
    
    def __init__(self, config: CacheConfig):
        """
        Inicializa o cache Redis.
        
        Args:
            config: Configurações do cache.
        """
        self.config = config
        self.client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True
        )
        logger.info("Cache Redis inicializado")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do valor.
            
        Returns:
            Any: Valor armazenado ou None se não encontrado.
        """
        import json
        
        try:
            key = f"{self.config.key_prefix}{key}"
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Erro ao obter valor do Redis: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave para o valor.
            value: Valor a ser armazenado.
            ttl: Tempo de vida em segundos (opcional).
        """
        import json
        
        try:
            key = f"{self.config.key_prefix}{key}"
            value = json.dumps(value)
            
            if ttl is not None:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
                
                if self.config.default_ttl > 0:
                    self.client.expire(key, self.config.default_ttl)
                    
        except Exception as e:
            logger.error(f"Erro ao armazenar valor no Redis: {e}")
    
    def delete(self, key: str) -> None:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do valor a ser removido.
        """
        try:
            key = f"{self.config.key_prefix}{key}"
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Erro ao remover valor do Redis: {e}")
    
    def clear(self) -> None:
        """Remove todos os valores do cache com o prefixo configurado."""
        try:
            pattern = f"{self.config.key_prefix}*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Erro ao limpar cache Redis: {e}")
    
    def close(self) -> None:
        """Fecha a conexão com o Redis."""
        try:
            self.client.close()
            logger.info("Conexão com Redis fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar conexão com Redis: {e}")

class CacheFactory:
    """Fábrica para criar instâncias de cache."""
    
    @staticmethod
    def create() -> Cache:
        """
        Cria uma instância de cache com base nas configurações do user_settings.json.
        
        Returns:
            Cache: Instância de cache configurada.
        """
        # Carregar configurações do user_settings.json
        config = CacheConfig.from_settings()
        
        # Criar instância apropriada
        if config.cache_type == "redis":
            try:
                return RedisCache(config)
            except Exception as e:
                logger.error(f"Erro ao criar cache Redis: {e}")
                logger.warning("Usando cache em memória como fallback")
                return MemoryCache(config)
        else:
            return MemoryCache(config)
    
    @staticmethod
    def create_from_config(config: CacheConfig) -> Cache:
        """
        Cria uma instância de cache com base em uma configuração existente.
        
        Args:
            config: Configurações do cache.
            
        Returns:
            Cache: Instância de cache configurada.
        """
        if config.cache_type == "redis":
            try:
                return RedisCache(config)
            except Exception as e:
                logger.error(f"Erro ao criar cache Redis: {e}")
                logger.warning("Usando cache em memória como fallback")
                return MemoryCache(config)
        else:
            return MemoryCache(config) 