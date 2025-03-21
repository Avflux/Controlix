import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class AuthObserver:
    def __init__(self):
        self._current_user: Optional[Dict] = None
        self._auth_status: bool = False
        self._last_login: Optional[datetime] = None
        self._observers = []
        
    def set_auth_status(self, status: bool, user_data: Optional[Dict] = None):
        """Atualiza o status de autenticação"""
        self._auth_status = status
        if status and user_data:
            self._current_user = user_data
            self._last_login = datetime.now()
            logger.info(f"Usuário {user_data['name_id']} autenticado")
        else:
            self._current_user = None
            logger.info("Usuário desconectado")
            
        self._notify_observers()
    
    def get_current_user(self) -> Optional[Dict]:
        """Retorna dados do usuário atual"""
        return self._current_user
    
    def is_authenticated(self) -> bool:
        """Verifica se há usuário autenticado"""
        return self._auth_status
    
    def add_observer(self, callback):
        """Adiciona um observer"""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback):
        """Remove um observer"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self):
        """Notifica os observers sobre mudanças"""
        for observer in self._observers:
            observer(self._auth_status, self._current_user)

# Instância global do observer
auth_observer = AuthObserver() 