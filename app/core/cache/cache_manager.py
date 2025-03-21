import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import json
from pathlib import Path
from app.config.settings import CACHE_DIR, CACHE_SETTINGS

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        """Inicializa o gerenciador de cache"""
        self.cache: Dict[str, Dict] = {}
        self.max_size = CACHE_SETTINGS['max_size']
        self.default_timeout = CACHE_SETTINGS['default_timeout']
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
    def get(self, key: str) -> Optional[Any]:
        """Obtém um valor do cache com tratamento de erro detalhado"""
        try:
            if not isinstance(key, str):
                raise TypeError(f"Chave deve ser string, recebido: {type(key)}")
                
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
                
            entry = self.cache[key]
            if datetime.now() > entry['expires']:
                self.delete(key)
                self.stats['misses'] += 1
                return None
                
            self.stats['hits'] += 1
            return entry['value']
            
        except Exception as e:
            logger.error(f"Falha ao recuperar chave '{key}': {str(e)}", exc_info=True)
            return None
            
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Armazena um valor no cache com validação de entrada"""
        try:
            if not isinstance(key, str):
                raise TypeError(f"Chave inválida: {type(key)}")
                
            if timeout is not None and (not isinstance(timeout, int) or timeout < 0):
                raise ValueError(f"Timeout inválido: {timeout}")
                
            # Limpa cache se necessário
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
                
            expires = datetime.now() + timedelta(
                seconds=timeout or self.default_timeout
            )
            
            self.cache[key] = {
                'value': value,
                'expires': expires,
                'created': datetime.now()
            }
            return True
            
        except Exception as e:
            logger.error(f"Falha ao armazenar '{key}': {str(e)}", exc_info=True)
            return False
            
    def delete(self, key: str):
        """Remove um item do cache"""
        if key in self.cache:
            del self.cache[key]
            
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()
        
    def _evict_oldest(self):
        """Remove o item mais antigo do cache"""
        if not self.cache:
            return
            
        oldest = min(
            self.cache.items(),
            key=lambda x: x[1]['created']
        )[0]
        
        self.delete(oldest)
        self.stats['evictions'] += 1
        
    def get_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        total = self.stats['hits'] + self.stats['misses']
        hit_ratio = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_ratio': f"{hit_ratio:.1f}%"
        }

# Instância global
cache_manager = CacheManager() 