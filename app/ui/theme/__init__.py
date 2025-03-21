import logging
logger = logging.getLogger(__name__)

logger.debug("Iniciando importação do theme_manager...")

from app.config.settings import ThemeMode
logger.debug("ThemeMode importado")

from .theme_manager import ThemeManager
logger.debug("ThemeManager importado")

# Instância global do gerenciador de temas
theme_manager = ThemeManager()
logger.debug("theme_manager instanciado")

__all__ = ['theme_manager', 'ThemeMode'] 