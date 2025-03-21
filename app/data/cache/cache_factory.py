"""
Fábrica para criar instâncias de cache.
Permite escolher entre diferentes implementações de cache.
"""

import logging
import os
from typing import Any, Dict, Optional, Union
from enum import Enum, auto
from app.config.settings import CACHE_DIR

logger = logging.getLogger(__name__)

class CacheType(Enum):
    """Tipos de cache suportados."""
    MEMORY = auto()  # Cache em memória
    REDIS = auto()   # Cache Redis
    NONE = auto()    # Sem cache

class CacheFactory:
    """
    Fábrica para criar instâncias de cache.
    
    Esta classe permite escolher entre diferentes implementações de cache,
    como cache em memória ou Redis.
    """
    
    @staticmethod
    def create(cache_type: CacheType = CacheType.MEMORY, **kwargs) -> Any:
        """
        Cria uma instância de cache do tipo especificado.
        
        Args:
            cache_type: Tipo de cache a ser criado
            **kwargs: Argumentos adicionais para o construtor do cache
            
        Returns:
            Any: Instância do cache
        """
        if cache_type == CacheType.MEMORY:
            from app.data.cache.query_cache import QueryCache
            return QueryCache(**kwargs)
            
        elif cache_type == CacheType.REDIS:
            try:
                from app.data.cache.redis_adapter import RedisAdapter
                
                # Configurações padrão
                config = {
                    'prefix': 'controlix:',
                    'host': os.environ.get('REDIS_HOST', 'localhost'),
                    'port': int(os.environ.get('REDIS_PORT', '6379')),
                    'db': int(os.environ.get('REDIS_DB', '0')),
                    'password': os.environ.get('REDIS_PASSWORD', None),
                    'socket_timeout': int(os.environ.get('REDIS_TIMEOUT', '5'))
                }
                
                # Sobrescrever com argumentos fornecidos
                config.update(kwargs)
                
                return RedisAdapter(**config)
            except ImportError:
                logger.warning("Redis não disponível, usando cache em memória")
                from app.data.cache.query_cache import QueryCache
                return QueryCache(**kwargs)
                
        elif cache_type == CacheType.NONE:
            from app.data.cache.null_cache import NullCache
            return NullCache()
            
        else:
            logger.warning(f"Tipo de cache desconhecido: {cache_type}, usando cache em memória")
            from app.data.cache.query_cache import QueryCache
            return QueryCache(**kwargs)
            
    @staticmethod
    def get_default_cache():
        """
        Obtém o cache padrão com base nas configurações do ambiente.
        
        Returns:
            Any: Instância do cache padrão
        """
        # Verificar se Redis está configurado
        if os.environ.get('USE_REDIS_CACHE', 'false').lower() == 'true':
            return CacheFactory.create(CacheType.REDIS)
        else:
            return CacheFactory.create(CacheType.MEMORY)
            
    @staticmethod
    def get_cache_type_from_string(cache_type_str: str) -> CacheType:
        """
        Converte uma string para o tipo de cache correspondente.
        
        Args:
            cache_type_str: String representando o tipo de cache
            
        Returns:
            CacheType: Tipo de cache correspondente
        """
        cache_type_str = cache_type_str.upper()
        
        if cache_type_str == 'MEMORY':
            return CacheType.MEMORY
        elif cache_type_str == 'REDIS':
            return CacheType.REDIS
        elif cache_type_str == 'NONE':
            return CacheType.NONE
        else:
            logger.warning(f"Tipo de cache desconhecido: {cache_type_str}, usando MEMORY")
            return CacheType.MEMORY

# Cache nulo para quando não queremos usar cache
class NullCache:
    """
    Implementação de cache que não faz nada.
    Útil quando queremos desabilitar o cache.
    """
    
    def __init__(self, **kwargs):
        """Inicializa o cache nulo."""
        self.stats = {'hits': 0, 'misses': 0, 'invalidations': 0}
        
    def get(self, key: str) -> None:
        """Sempre retorna None."""
        return None
        
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Não faz nada e retorna True."""
        return True
        
    def delete(self, key: str) -> bool:
        """Não faz nada e retorna True."""
        return True
        
    def clear(self) -> bool:
        """Não faz nada e retorna True."""
        return True
        
    def get_stats(self) -> Dict:
        """Retorna estatísticas vazias."""
        return self.stats
        
    def invalidate_patterns(self, patterns: list) -> int:
        """Não faz nada e retorna 0."""
        return 0
        
    def get_query_result(self, query: str, params: tuple) -> None:
        """Sempre retorna None."""
        return None
        
    def set_query_result(self, query: str, params: tuple, result: dict, timeout: Optional[int] = None) -> bool:
        """Não faz nada e retorna True."""
        return True

# Exemplo de uso:
# cache = CacheFactory.create(CacheType.REDIS, host='localhost', port=6379)
# ou
# cache = CacheFactory.get_default_cache() 