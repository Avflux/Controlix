import logging
import psutil
import threading
from typing import Dict
from datetime import datetime, timedelta
import json
from pathlib import Path
from app.config.settings import CACHE_DIR

logger = logging.getLogger(__name__)

class MemoryMonitor:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def __init__(self, warning_threshold: float = 75.0, critical_threshold: float = 90.0):
        if not hasattr(self, 'initialized'):
            super().__init__()
            self.initialized = True
            self.warning_threshold = warning_threshold  # % de memória
            self.critical_threshold = critical_threshold
            self.stats_file = CACHE_DIR / 'memory_stats.json'
            self.stats_history = []
            self.max_history = 1000
            self._monitor_thread = None
            self._stop_monitor = False
            self._load_stats()
        
    def start_monitoring(self):
        """Inicia monitoramento em thread separada"""
        self._stop_monitor = False
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="Memory-Monitor"
        )
        self._monitor_thread.start()
        logger.info("Monitor de memória iniciado")
        
    def stop_monitoring(self):
        """Para o monitoramento"""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join()
        self._save_stats()
        
    def get_memory_usage(self) -> Dict:
        """Retorna uso atual de memória"""
        process = psutil.Process()
        mem_info = process.memory_info()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'rss': mem_info.rss / 1024 / 1024,  # MB
            'vms': mem_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent(),
            'system_percent': psutil.virtual_memory().percent
        }
        
    def should_clear_cache(self) -> bool:
        """Verifica se deve limpar cache baseado no uso de memória"""
        mem_usage = self.get_memory_usage()
        
        if mem_usage['system_percent'] > self.critical_threshold:
            logger.warning(f"Uso crítico de memória: {mem_usage['system_percent']}%")
            return True
            
        if mem_usage['system_percent'] > self.warning_threshold:
            logger.info(f"Uso alto de memória: {mem_usage['system_percent']}%")
            return True
            
        return False
        
    def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while not self._stop_monitor:
            try:
                stats = self.get_memory_usage()
                self.stats_history.append(stats)
                
                # Mantém histórico limitado
                if len(self.stats_history) > self.max_history:
                    self.stats_history.pop(0)
                
                # Salva estatísticas periodicamente
                if len(self.stats_history) % 100 == 0:
                    self._save_stats()
                
                # Verifica uso crítico
                if stats['system_percent'] > self.critical_threshold:
                    logger.critical(
                        f"Uso crítico de memória: {stats['system_percent']}% "
                        f"RSS: {stats['rss']:.1f}MB"
                    )
                
            except Exception as e:
                logger.error(f"Erro no monitor de memória: {e}")
                
            threading.Event().wait(60)  # Monitora a cada 1 minuto
            
    def get_stats_summary(self) -> Dict:
        """Retorna resumo das estatísticas"""
        if not self.stats_history:
            return {}
            
        rss_values = [s['rss'] for s in self.stats_history]
        percent_values = [s['percent'] for s in self.stats_history]
        
        return {
            'current': self.get_memory_usage(),
            'avg_rss': sum(rss_values) / len(rss_values),
            'max_rss': max(rss_values),
            'avg_percent': sum(percent_values) / len(percent_values),
            'max_percent': max(percent_values),
            'samples': len(self.stats_history)
        }
        
    def _save_stats(self):
        """Salva estatísticas em arquivo"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats_history[-100:], f)  # Salva últimas 100 amostras
        except Exception as e:
            logger.error(f"Erro ao salvar estatísticas: {e}")
            
    def _load_stats(self):
        """Carrega estatísticas salvas"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file) as f:
                    self.stats_history = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar estatísticas: {e}")

# Instância global
memory_monitor = MemoryMonitor() 