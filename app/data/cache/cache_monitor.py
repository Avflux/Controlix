class CacheMonitor:
    def __init__(self):
        self.stats = {
            'hits': 0,
            'misses': 0,
            'size': 0,
            'evictions': 0
        }
        
    def get_stats(self) -> dict:
        """Retorna estatísticas do cache"""
        return {
            **self.stats,
            'hit_ratio': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) * 100
            if (self.stats['hits'] + self.stats['misses']) > 0 else 0
        } 