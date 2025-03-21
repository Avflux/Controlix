from functools import wraps
from typing import Optional
import hashlib
import json
from .cache_manager import cache_manager

def cached(timeout: Optional[int] = None):
    """Decorador para cachear resultados de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Cria chave única baseada na função e argumentos
            key = f"{func.__module__}.{func.__name__}"
            args_key = hashlib.md5(
                json.dumps((args, kwargs), sort_keys=True).encode()
            ).hexdigest()
            cache_key = f"{key}:{args_key}"
            
            # Tenta obter do cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
                
            # Se não encontrou, executa função
            result = func(*args, **kwargs)
            
            # Armazena resultado no cache
            cache_manager.set(cache_key, result, timeout)
            return result
            
        return wrapper
    return decorator 