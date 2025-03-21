import unittest
import logging
import time
from pathlib import Path
import sys

# Configura logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona diretório raiz ao PYTHONPATH
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from app.core.cache.cache_manager import cache_manager
from app.core.cache.decorators import cached

class TestCacheSystem(unittest.TestCase):
    def setUp(self):
        """Prepara o ambiente para cada teste"""
        self.cache_manager = cache_manager
        self.cache_manager.clear()  # Limpa o cache antes de cada teste
        
    def test_basic_cache_operations(self):
        """Testa operações básicas do cache"""
        # Teste SET
        self.assertTrue(
            self.cache_manager.set("test_key", "test_value"),
            "Falha ao armazenar valor no cache"
        )
        
        # Teste GET
        self.assertEqual(
            self.cache_manager.get("test_key"),
            "test_value",
            "Valor recuperado não corresponde ao armazenado"
        )
        
        # Teste DELETE
        self.cache_manager.delete("test_key")
        self.assertIsNone(
            self.cache_manager.get("test_key"),
            "Valor não foi deletado corretamente"
        )
        
    def test_cache_expiration(self):
        """Testa expiração do cache"""
        # Armazena com timeout curto
        self.cache_manager.set("expire_key", "expire_value", timeout=1)
        
        # Verifica imediatamente
        self.assertEqual(
            self.cache_manager.get("expire_key"),
            "expire_value",
            "Valor não disponível imediatamente"
        )
        
        # Aguarda expiração
        time.sleep(1.1)
        
        # Verifica após expiração
        self.assertIsNone(
            self.cache_manager.get("expire_key"),
            "Valor não expirou corretamente"
        )
        
    def test_cache_decorator(self):
        """Testa o decorador de cache"""
        self.call_count = 0
        
        @cached(timeout=5)
        def test_function(x, y):
            self.call_count += 1
            return x + y
        
        # Primeira chamada (deve executar a função)
        result1 = test_function(2, 3)
        self.assertEqual(result1, 5)
        self.assertEqual(self.call_count, 1)
        
        # Segunda chamada (deve usar cache)
        result2 = test_function(2, 3)
        self.assertEqual(result2, 5)
        self.assertEqual(self.call_count, 1)  # Não deve incrementar
        
        # Chamada com parâmetros diferentes (deve executar a função)
        result3 = test_function(3, 4)
        self.assertEqual(result3, 7)
        self.assertEqual(self.call_count, 2)
        
    def test_cache_stats(self):
        """Testa estatísticas do cache"""
        # Limpa estatísticas
        self.cache_manager.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
        # Gera alguns hits e misses
        self.cache_manager.set("stats_key", "stats_value")
        
        # Miss (chave inexistente)
        self.cache_manager.get("nonexistent_key")
        
        # Hit (chave existente)
        self.cache_manager.get("stats_key")
        
        # Verifica estatísticas
        stats = self.cache_manager.get_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        
    def test_cache_max_size(self):
        """Testa limite máximo do cache"""
        # Força o limite máximo para teste
        original_max_size = self.cache_manager.max_size
        self.cache_manager.max_size = 3
        
        try:
            # Adiciona itens até exceder o limite
            for i in range(5):
                self.cache_manager.set(f"key_{i}", f"value_{i}")
            
            # Verifica se manteve apenas os últimos 3
            self.assertEqual(
                len(self.cache_manager.cache),
                3,
                "Cache excedeu o tamanho máximo"
            )
            
            # Verifica se os itens mais antigos foram removidos
            self.assertIsNone(
                self.cache_manager.get("key_0"),
                "Item antigo não foi removido"
            )
            self.assertIsNone(
                self.cache_manager.get("key_1"),
                "Item antigo não foi removido"
            )
            
        finally:
            # Restaura o tamanho máximo original
            self.cache_manager.max_size = original_max_size
            
    def test_cache_clear(self):
        """Testa limpeza completa do cache"""
        # Adiciona alguns itens
        for i in range(5):
            self.cache_manager.set(f"clear_key_{i}", f"value_{i}")
        
        # Limpa o cache
        self.cache_manager.clear()
        
        # Verifica se está vazio
        self.assertEqual(
            len(self.cache_manager.cache),
            0,
            "Cache não foi limpo corretamente"
        )

if __name__ == '__main__':
    unittest.main() 