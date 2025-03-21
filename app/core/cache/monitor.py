import logging
from datetime import datetime
from typing import Dict
import json
from pathlib import Path
from app.config.settings import CACHE_DIR
from app.core.cache.cache_manager import cache_manager

logger = logging.getLogger(__name__)

class CacheMonitor:
    def __init__(self):
        self.stats_file = CACHE_DIR / 'cache_stats.json'
        self.last_check = datetime.now()
        
    def collect_stats(self) -> Dict:
        """Coleta estatísticas do cache"""
        current_stats = cache_manager.get_stats()
        
        # Adiciona timestamp
        stats = {
            'timestamp': datetime.now().isoformat(),
            'stats': current_stats
        }
        
        # Salva estatísticas
        self._save_stats(stats)
        return stats
        
    def _save_stats(self, stats: Dict):
        """Salva estatísticas em arquivo"""
        try:
            # Carrega estatísticas anteriores
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
                
            # Adiciona novas estatísticas
            history.append(stats)
            
            # Mantém apenas últimas 1000 amostras
            if len(history) > 1000:
                history = history[-1000:]
                
            # Salva arquivo
            with open(self.stats_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Erro ao salvar estatísticas: {e}")
            
    def get_performance_metrics(self) -> Dict:
        """Calcula métricas de performance"""
        stats = cache_manager.get_stats()
        return {
            'hit_ratio': stats['hit_ratio'],
            'cache_size': stats['size'],
            'memory_usage': f"{stats['size'] * 1024 / (1024*1024):.2f}MB",
            'evictions': stats['evictions']
        }

# Instância global
cache_monitor = CacheMonitor() 