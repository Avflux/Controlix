from typing import Any, Optional, Dict, Pattern, List, Union
from datetime import datetime, timedelta
import logging
import json
import hashlib
import re
from .cache_invalidator import cache_invalidator
from .memory_monitor import memory_monitor

logger = logging.getLogger(__name__)

class QueryCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.default_timeout = timedelta(minutes=5)  # Timeout padrão
        self.memory_monitor = memory_monitor
        self.memory_monitor.start_monitoring()
        
    def get_query_result(self, query: str, params: tuple) -> Optional[dict]:
        """Obtém resultado de query do cache"""
        key = self._make_key(query, params)
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                self.hits += 1
                return entry['result']
            else:
                self.delete(key)
        self.misses += 1
        return None
        
    def set_query_result(self, query: str, params: tuple, result: dict, timeout: Optional[timedelta] = None):
        """Armazena resultado de query"""
        if self.memory_monitor.should_clear_cache():
            self.clear()
            return
            
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        key = self._make_key(query, params)
        self.cache[key] = {
            'result': result,
            'query': query,
            'timestamp': datetime.now(),
            'expires': datetime.now() + (timeout or self.default_timeout)
        }
        
    def invalidate_patterns(self, patterns: List[Union[str, Pattern]]):
        """Invalida cache baseado em padrões de query"""
        invalidated = 0
        for key, entry in list(self.cache.items()):
            query = entry['query']
            for pattern in patterns:
                # Compila o padrão se for string
                if isinstance(pattern, str):
                    pattern = re.compile(pattern, re.IGNORECASE)
                if pattern.match(query):
                    self.delete(key)
                    invalidated += 1
                    break
        
        if invalidated:
            self.invalidations += invalidated
            logger.debug(f"Invalidadas {invalidated} entradas de cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        self._increment_cleanup()
        
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if datetime.now() > entry['expires']:
            del self.cache[key]
            return None
            
        entry['hits'] += 1
        return entry['value']
        
    def set(self, key: str, value: Any, timeout: Optional[timedelta] = None):
        """Armazena valor no cache"""
        # Verifica uso de memória antes de cachear
        if self.memory_monitor.should_clear_cache():
            self.clear()
            return
            
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        expires = datetime.now() + (timeout or self.default_timeout)
        self.cache[key] = {
            'value': value,
            'expires': expires,
            'hits': 0,
            'created': datetime.now()
        }
        
    def delete(self, key: str):
        """Remove item do cache"""
        if key in self.cache:
            del self.cache[key]
            
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()
        
    def _cleanup_least_used(self):
        """Remove itens menos usados"""
        if not self.cache:
            return
            
        # Remove 10% dos itens menos usados
        items = sorted(
            self.cache.items(),
            key=lambda x: (x[1]['hits'], x[1]['created'])
        )
        
        to_remove = max(len(self.cache) // 10, 1)
        for key, _ in items[:to_remove]:
            del self.cache[key]
            
    def _increment_cleanup(self):
        """Controle de limpeza periódica"""
        self._cleanup_counter += 1
        if self._cleanup_counter >= 1000:
            self._cleanup_expired()
            self._cleanup_counter = 0
            
    def _cleanup_expired(self):
        """Remove itens expirados"""
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if v['expires'] < now]
        for key in expired:
            del self.cache[key]

    def _make_key(self, query: str, params: tuple) -> str:
        """Cria chave única para query"""
        # Usa hash para evitar chaves muito longas
        params_str = '_'.join(map(str, params)) if params else ''
        key_str = f"{query}_{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, entry: Dict) -> bool:
        """Verifica se entrada está expirada"""
        return datetime.now() > entry['expires']
    
    def _evict_oldest(self):
        """Remove entrada mais antiga do cache"""
        if not self.cache:
            return
            
        oldest_key = min(self.cache.keys(), 
                        key=lambda k: self.cache[k]['timestamp'])
        self.delete(oldest_key)
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        cache_stats = {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_ratio': self.hits / (self.hits + self.misses) * 100 if (self.hits + self.misses) > 0 else 0,
            'invalidations': self.invalidations
        }
        
        # Adiciona estatísticas de memória
        memory_stats = self.memory_monitor.get_stats_summary()
        return {**cache_stats, 'memory': memory_stats}

# Instância global
query_cache = QueryCache() 