import logging
from pathlib import Path
import json
import time
from typing import Any, Optional
from app.config.settings import CACHE_DIR, PERFORMANCE_SETTINGS

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_timeout = PERFORMANCE_SETTINGS['cache_timeout']
        self.max_size = PERFORMANCE_SETTINGS['cache_size'] * 1024 * 1024  # Converte para bytes
        
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Armazena um valor no cache"""
        try:
            cache_file = self.cache_dir / f"{key}.cache"
            
            cache_data = {
                'value': value,
                'timestamp': time.time(),
                'timeout': timeout or self.cache_timeout
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
            logger.debug(f"Valor armazenado em cache: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar em cache: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Recupera um valor do cache"""
        try:
            cache_file = self.cache_dir / f"{key}.cache"
            
            if not cache_file.exists():
                return None
                
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Verifica se o cache expirou
            if time.time() - cache_data['timestamp'] > cache_data['timeout']:
                cache_file.unlink()  # Remove arquivo expirado
                return None
                
            logger.debug(f"Valor recuperado do cache: {key}")
            return cache_data['value']
            
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {e}")
            return None
    
    def clear(self, key: Optional[str] = None):
        """Limpa o cache"""
        try:
            if key:
                cache_file = self.cache_dir / f"{key}.cache"
                if cache_file.exists():
                    cache_file.unlink()
                    logger.debug(f"Cache limpo para: {key}")
            else:
                # Limpa todo o cache
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                logger.debug("Cache completamente limpo")
                
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
    
    def cleanup(self):
        """Remove arquivos de cache expirados e mantém o tamanho máximo"""
        try:
            current_size = 0
            files = []
            
            # Lista todos os arquivos de cache com seus timestamps
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    stat = cache_file.stat()
                    current_size += stat.st_size
                    files.append((cache_file, stat.st_mtime))
                except:
                    continue
            
            # Remove arquivos expirados
            for file, mtime in files:
                if time.time() - mtime > self.cache_timeout:
                    file.unlink()
                    current_size -= file.stat().st_size
            
            # Se ainda estiver acima do limite, remove os mais antigos
            if current_size > self.max_size:
                files.sort(key=lambda x: x[1])  # Ordena por timestamp
                for file, _ in files:
                    if current_size <= self.max_size:
                        break
                    current_size -= file.stat().st_size
                    file.unlink()
                    
            logger.debug(f"Limpeza de cache concluída. Tamanho atual: {current_size/1024/1024:.2f}MB")
            
        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {e}")

# Instância global do gerenciador de cache
cache_manager = CacheManager() 