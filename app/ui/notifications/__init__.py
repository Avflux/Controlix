import logging
logger = logging.getLogger(__name__)

logger.debug("Iniciando importação do notification_manager...")

from app.ui.notifications.notification_manager import NotificationManager
logger.debug("NotificationManager importado")

# Instância global do gerenciador de notificações
notifications = NotificationManager()
logger.debug("notifications inicializado")

__all__ = ['notifications']
