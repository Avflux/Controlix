import logging
from typing import Any
from datetime import datetime, timedelta
from app.core.cache.cache_manager import cache_manager
from app.config.settings import dynamic_settings

# Adiciona logger
logger = logging.getLogger(__name__)

class SettingsCache:
    def __init__(self):
        self.reload_interval = timedelta(minutes=5)
        self.last_reload = None
        self.cache_prefix = "settings:"
        
    def get_setting(self, key: str) -> Any:
        """Obtém configuração do cache"""
        self._check_reload()
        cache_key = f"{self.cache_prefix}{key}"
        return cache_manager.get(cache_key)
        
    def _check_reload(self):
        """Verifica se precisa recarregar configurações"""
        now = datetime.now()
        if not self.last_reload or (now - self.last_reload) > self.reload_interval:
            self._reload_settings()
            
    def _reload_settings(self):
        """Recarrega configurações com tratamento robusto"""
        try:
            if not dynamic_settings:
                raise ValueError("DynamicSettings não inicializado")
                
            settings = dynamic_settings._settings.get('window', {})
            
            if not isinstance(settings, dict):
                raise TypeError("Configurações devem ser um dicionário")
                
            # Atualiza o timestamp da última recarga
            self.last_reload = datetime.now()
            
            # Armazena cada configuração individualmente no cache
            for key, value in settings.items():
                cache_key = f"{self.cache_prefix}{key}"
                cache_manager.set(
                    cache_key, 
                    value, 
                    timeout=int(self.reload_interval.total_seconds())
                )
                
            logger.debug("Configurações recarregadas no cache")
            
        except Exception as e:
            logger.critical("Falha crítica no recarregamento de configurações", exc_info=True)
            raise RuntimeError("Não foi possível recarregar configurações") from e
            
    def invalidate_cache(self):
        """Invalida o cache de configurações"""
        try:
            # Força recarga no próximo acesso
            self.last_reload = None
            
            # Remove todas as entradas com o prefixo de configurações
            keys_to_delete = [
                key for key in cache_manager.cache.keys()
                if key.startswith(self.cache_prefix)
            ]
            
            for key in keys_to_delete:
                cache_manager.delete(key)
                
            logger.debug("Cache de configurações invalidado")
            
        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}", exc_info=True)
            raise

# Instância global
settings_cache = SettingsCache() 