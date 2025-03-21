#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testes para o adaptador Redis.
"""

import os
import sys
import unittest
import logging
import time
from datetime import timedelta
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações do projeto
try:
    from app.data.cache.redis_adapter import RedisAdapter
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis não disponível, alguns testes serão ignorados")
    REDIS_AVAILABLE = False

from app.data.cache.cache_factory import CacheFactory, CacheType, NullCache

@unittest.skipIf(not REDIS_AVAILABLE, "Redis não disponível")
class TestRedisAdapter(unittest.TestCase):
    """Testes para o adaptador Redis."""
    
    def setUp(self):
        """Configuração inicial para os testes."""
        # Verificar se o Redis está disponível
        try:
            self.redis = RedisAdapter(
                prefix="test_controlix:",
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', '6379')),
                db=int(os.environ.get('REDIS_TEST_DB', '1'))  # Usar DB 1 para testes
            )
            
            # Verificar conexão
            if not self.redis.health_check():
                self.skipTest("Redis não está disponível")
                
            # Limpar cache antes dos testes
            self.redis.clear()
        except Exception as e:
            self.skipTest(f"Erro ao conectar ao Redis: {e}")
    
    def test_basic_operations(self):
        """Testa operações básicas do Redis."""
        # Testar SET
        self.assertTrue(
            self.redis.set("test_key", "test_value"),
            "Falha ao armazenar valor no Redis"
        )
        
        # Testar GET
        self.assertEqual(
            self.redis.get("test_key"),
            "test_value",
            "Valor recuperado não corresponde ao armazenado"
        )
        
        # Testar DELETE
        self.redis.delete("test_key")
        self.assertIsNone(
            self.redis.get("test_key"),
            "Valor não foi deletado corretamente"
        )
    
    def test_complex_values(self):
        """Testa armazenamento de valores complexos."""
        # Testar dicionário
        test_dict = {"name": "Test", "value": 123, "nested": {"a": 1, "b": 2}}
        self.assertTrue(
            self.redis.set("test_dict", test_dict),
            "Falha ao armazenar dicionário no Redis"
        )
        
        # Testar recuperação
        result = self.redis.get("test_dict")
        self.assertEqual(
            result,
            test_dict,
            "Dicionário recuperado não corresponde ao armazenado"
        )
        
        # Testar lista
        test_list = [1, 2, 3, "test", {"a": 1}]
        self.assertTrue(
            self.redis.set("test_list", test_list),
            "Falha ao armazenar lista no Redis"
        )
        
        # Testar recuperação
        result = self.redis.get("test_list")
        self.assertEqual(
            result,
            test_list,
            "Lista recuperada não corresponde à armazenada"
        )
    
    def test_expiration(self):
        """Testa expiração de valores."""
        # Armazenar com timeout curto
        self.redis.set("expire_key", "expire_value", timeout=timedelta(seconds=1))
        
        # Verificar imediatamente
        self.assertEqual(
            self.redis.get("expire_key"),
            "expire_value",
            "Valor não disponível imediatamente"
        )
        
        # Aguardar expiração
        time.sleep(1.1)
        
        # Verificar após expiração
        self.assertIsNone(
            self.redis.get("expire_key"),
            "Valor não expirou corretamente"
        )
    
    def test_query_cache(self):
        """Testa cache de consultas."""
        # Testar armazenamento de resultado de consulta
        query = "SELECT * FROM test_table WHERE id = %s"
        params = (1,)
        result = [{"id": 1, "name": "Test"}]
        
        self.redis.set_query_result(query, params, result)
        
        # Testar recuperação
        cached_result = self.redis.get_query_result(query, params)
        self.assertEqual(
            cached_result,
            result,
            "Resultado de consulta recuperado não corresponde ao armazenado"
        )
        
        # Testar consulta diferente
        different_params = (2,)
        self.assertIsNone(
            self.redis.get_query_result(query, different_params),
            "Consulta com parâmetros diferentes não deveria estar em cache"
        )
    
    def test_pattern_invalidation(self):
        """Testa invalidação por padrões."""
        # Armazenar vários valores
        self.redis.set("user_1", {"id": 1, "name": "User 1"})
        self.redis.set("user_2", {"id": 2, "name": "User 2"})
        self.redis.set("product_1", {"id": 1, "name": "Product 1"})
        
        # Invalidar padrão "user_"
        invalidated = self.redis.invalidate_patterns(["user_"])
        self.assertEqual(
            invalidated,
            2,
            "Número incorreto de chaves invalidadas"
        )
        
        # Verificar que os valores foram removidos
        self.assertIsNone(
            self.redis.get("user_1"),
            "Valor user_1 não foi invalidado"
        )
        self.assertIsNone(
            self.redis.get("user_2"),
            "Valor user_2 não foi invalidado"
        )
        
        # Verificar que product_1 ainda existe
        self.assertIsNotNone(
            self.redis.get("product_1"),
            "Valor product_1 foi invalidado incorretamente"
        )
    
    def test_stats(self):
        """Testa estatísticas do cache."""
        # Limpar estatísticas
        self.redis.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
        
        # Gerar alguns hits e misses
        self.redis.set("stats_key", "stats_value")
        
        # Miss (chave inexistente)
        self.redis.get("nonexistent_key")
        
        # Hit (chave existente)
        self.redis.get("stats_key")
        
        # Verificar estatísticas
        stats = self.redis.get_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
    
    def tearDown(self):
        """Limpeza após os testes."""
        if hasattr(self, 'redis'):
            # Limpar cache após os testes
            self.redis.clear()

class TestCacheFactory(unittest.TestCase):
    """Testes para a fábrica de cache."""
    
    def test_create_memory_cache(self):
        """Testa criação de cache em memória."""
        cache = CacheFactory.create(CacheType.MEMORY)
        self.assertIsNotNone(cache)
        self.assertEqual(
            cache.__class__.__name__,
            "QueryCache",
            "Tipo de cache incorreto"
        )
    
    def test_create_null_cache(self):
        """Testa criação de cache nulo."""
        cache = CacheFactory.create(CacheType.NONE)
        self.assertIsNotNone(cache)
        self.assertEqual(
            cache.__class__.__name__,
            "NullCache",
            "Tipo de cache incorreto"
        )
    
    def test_create_redis_cache(self):
        """Testa criação de cache Redis."""
        # Se Redis não estiver disponível, deve retornar QueryCache
        cache = CacheFactory.create(CacheType.REDIS)
        self.assertIsNotNone(cache)
        
        # Verificar tipo de cache
        if REDIS_AVAILABLE:
            expected_class = "RedisAdapter"
        else:
            expected_class = "QueryCache"
            
        self.assertEqual(
            cache.__class__.__name__,
            expected_class,
            "Tipo de cache incorreto"
        )
    
    def test_get_default_cache(self):
        """Testa obtenção de cache padrão."""
        # Salvar valor original
        original_value = os.environ.get('USE_REDIS_CACHE')
        
        try:
            # Testar com Redis desativado
            os.environ['USE_REDIS_CACHE'] = 'false'
            cache = CacheFactory.get_default_cache()
            self.assertEqual(
                cache.__class__.__name__,
                "QueryCache",
                "Tipo de cache incorreto com Redis desativado"
            )
            
            # Testar com Redis ativado
            os.environ['USE_REDIS_CACHE'] = 'true'
            cache = CacheFactory.get_default_cache()
            
            # Verificar tipo de cache
            if REDIS_AVAILABLE:
                expected_class = "RedisAdapter"
            else:
                expected_class = "QueryCache"
                
            self.assertEqual(
                cache.__class__.__name__,
                expected_class,
                "Tipo de cache incorreto com Redis ativado"
            )
        finally:
            # Restaurar valor original
            if original_value is not None:
                os.environ['USE_REDIS_CACHE'] = original_value
            else:
                os.environ.pop('USE_REDIS_CACHE', None)
    
    def test_get_cache_type_from_string(self):
        """Testa conversão de string para tipo de cache."""
        self.assertEqual(
            CacheFactory.get_cache_type_from_string("MEMORY"),
            CacheType.MEMORY,
            "Conversão incorreta para MEMORY"
        )
        
        self.assertEqual(
            CacheFactory.get_cache_type_from_string("REDIS"),
            CacheType.REDIS,
            "Conversão incorreta para REDIS"
        )
        
        self.assertEqual(
            CacheFactory.get_cache_type_from_string("NONE"),
            CacheType.NONE,
            "Conversão incorreta para NONE"
        )
        
        self.assertEqual(
            CacheFactory.get_cache_type_from_string("INVALID"),
            CacheType.MEMORY,
            "Conversão incorreta para tipo inválido"
        )

class TestNullCache(unittest.TestCase):
    """Testes para o cache nulo."""
    
    def setUp(self):
        """Configuração inicial para os testes."""
        self.cache = NullCache()
    
    def test_basic_operations(self):
        """Testa operações básicas do cache nulo."""
        # Testar SET (sempre retorna True)
        self.assertTrue(self.cache.set("test_key", "test_value"))
        
        # Testar GET (sempre retorna None)
        self.assertIsNone(self.cache.get("test_key"))
        
        # Testar DELETE (sempre retorna True)
        self.assertTrue(self.cache.delete("test_key"))
        
        # Testar CLEAR (sempre retorna True)
        self.assertTrue(self.cache.clear())
    
    def test_query_cache(self):
        """Testa cache de consultas com cache nulo."""
        # Testar armazenamento de resultado de consulta (sempre retorna True)
        query = "SELECT * FROM test_table WHERE id = %s"
        params = (1,)
        result = [{"id": 1, "name": "Test"}]
        
        self.assertTrue(self.cache.set_query_result(query, params, result))
        
        # Testar recuperação (sempre retorna None)
        self.assertIsNone(self.cache.get_query_result(query, params))
    
    def test_stats(self):
        """Testa estatísticas do cache nulo."""
        stats = self.cache.get_stats()
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['misses'], 0)
        self.assertEqual(stats['invalidations'], 0)

if __name__ == '__main__':
    unittest.main() 