from typing import Dict, Optional
from datetime import datetime, timedelta

class AuthCache:
    def __init__(self, ttl: int = 300):  # 5 minutos
        self.cache: Dict[str, dict] = {}
        self.ttl = ttl
        
    def get_user(self, name_id: str) -> Optional[dict]:
        """Obtém usuário do cache"""
        if name_id in self.cache:
            user_data = self.cache[name_id]
            if datetime.now() < user_data['expires']:
                return user_data['data']
            else:
                del self.cache[name_id]
        return None
        
    def set_user(self, name_id: str, user_data: dict):
        """Armazena usuário no cache"""
        self.cache[name_id] = {
            'data': user_data,
            'expires': datetime.now() + timedelta(seconds=self.ttl)
        } 