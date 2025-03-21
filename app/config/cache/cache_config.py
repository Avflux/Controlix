"""
Configurações do sistema de cache.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging
from app.config.settings import DynamicSettings

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Configuração do sistema de cache."""
    
    # Tipo de cache (memory, redis)
    cache_type: str = "memory"
    
    # Tempo de vida padrão do cache em segundos (1 hora)
    default_ttl: int = 3600
    
    # Configurações do Redis (se usado)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Tamanho máximo do cache em memória (em itens)
    memory_max_size: int = 1000
    
    # Prefixo para chaves de cache
    key_prefix: str = "controlix:"
    
    @classmethod
    def from_settings(cls) -> 'CacheConfig':
        """
        Carrega configurações do arquivo user_settings.json.
        
        Returns:
            CacheConfig: Instância com as configurações carregadas.
        """
        try:
            settings = DynamicSettings()
            cache_settings = settings.get_setting(['performance', 'cache'], {})
            
            # Criar instância com valores padrão
            config = cls()
            
            # Atualizar configurações
            config.cache_type = cache_settings.get('type', config.cache_type)
            config.default_ttl = cache_settings.get('default_ttl', config.default_ttl)
            config.key_prefix = cache_settings.get('key_prefix', config.key_prefix)
            
            # Configurações do Redis
            redis_settings = cache_settings.get('redis', {})
            if redis_settings.get('enabled', False):
                config.cache_type = 'redis'
                config.redis_host = redis_settings.get('host', config.redis_host)
                config.redis_port = redis_settings.get('port', config.redis_port)
                config.redis_db = redis_settings.get('db', config.redis_db)
                config.redis_password = redis_settings.get('password', config.redis_password)
            
            # Configurações de memória
            memory_settings = cache_settings.get('memory', {})
            config.memory_max_size = memory_settings.get('max_size', config.memory_max_size)
            
            logger.info(f"Configurações de cache carregadas: tipo={config.cache_type}")
            return config
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações de cache: {e}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a configuração para um dicionário.
        
        Returns:
            Dict[str, Any]: Dicionário com as configurações.
        """
        return {
            'type': self.cache_type,
            'default_ttl': self.default_ttl,
            'redis': {
                'enabled': self.cache_type == 'redis',
                'host': self.redis_host,
                'port': self.redis_port,
                'db': self.redis_db,
                'password': self.redis_password
            },
            'memory': {
                'max_size': self.memory_max_size
            },
            'key_prefix': self.key_prefix
        }
    
    def save(self) -> None:
        """Salva as configurações no arquivo user_settings.json."""
        try:
            settings = DynamicSettings()
            settings.set_setting(['performance', 'cache'], self.to_dict())
            settings.save()
            logger.info("Configurações de cache salvas")
            
        except Exception as e:
            logger.error(f"Erro ao salvar configurações de cache: {e}")
            raise 