"""
Testes para o sistema de cache.
"""

import unittest
import logging
from app.config.cache.cache_config import CacheConfig
from app.config.cache.cache_factory import CacheFactory, MemoryCache, RedisCache
from app.config.settings import DynamicSettings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCacheConfig(unittest.TestCase):
    """Testes para a classe CacheConfig."""
    
    def setUp(self):
        """Configuração inicial dos testes."""
        self.settings = DynamicSettings()
        self.original_cache_settings = self.settings.get_setting(['performance', 'cache'], {})
        self.config = CacheConfig.from_settings()
    
    def tearDown(self):
        """Limpeza após os testes."""
        # Restaurar configurações originais
        self.settings.set_setting(['performance', 'cache'], self.original_cache_settings)
        self.settings.save()
    
    def test_default_config(self):
        """Testa configurações padrão."""
        # Configurar cache padrão
        cache_settings = {
            'type': 'memory',
            'default_ttl': 3600,
            'redis': {
                'enabled': False,
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None
            },
            'memory': {
                'max_size': 1000
            },
            'key_prefix': 'controlix:'
        }
        self.settings.set_setting(['performance', 'cache'], cache_settings)
        self.settings.save()
        
        # Recarregar configurações
        config = CacheConfig.from_settings()
        
        # Verificar valores
        self.assertEqual(config.cache_type, 'memory')
        self.assertEqual(config.default_ttl, 3600)
        self.assertEqual(config.memory_max_size, 1000)
        self.assertEqual(config.key_prefix, 'controlix:')
    
    def test_redis_config(self):
        """Testa configurações do Redis."""
        # Configurar Redis
        cache_settings = {
            'type': 'redis',
            'default_ttl': 1800,
            'redis': {
                'enabled': True,
                'host': 'redis.local',
                'port': 6380,
                'db': 1,
                'password': 'secret'
            },
            'memory': {
                'max_size': 500
            },
            'key_prefix': 'test:'
        }
        self.settings.set_setting(['performance', 'cache'], cache_settings)
        self.settings.save()
        
        # Recarregar configurações
        config = CacheConfig.from_settings()
        
        # Verificar valores
        self.assertEqual(config.cache_type, 'redis')
        self.assertEqual(config.default_ttl, 1800)
        self.assertEqual(config.redis_host, 'redis.local')
        self.assertEqual(config.redis_port, 6380)
        self.assertEqual(config.redis_db, 1)
        self.assertEqual(config.redis_password, 'secret')
        self.assertEqual(config.key_prefix, 'test:')

class TestMemoryCache(unittest.TestCase):
    """Testes para o cache em memória."""
    
    def setUp(self):
        """Configuração inicial dos testes."""
        self.settings = DynamicSettings()
        self.original_cache_settings = self.settings.get_setting(['performance', 'cache'], {})
        
        # Configurar cache em memória
        cache_settings = {
            'type': 'memory',
            'default_ttl': 60,
            'memory': {
                'max_size': 2
            },
            'key_prefix': 'test:'
        }
        self.settings.set_setting(['performance', 'cache'], cache_settings)
        self.settings.save()
        
        self.config = CacheConfig.from_settings()
        self.cache = MemoryCache(self.config)
    
    def tearDown(self):
        """Limpeza após os testes."""
        self.cache.clear()
        self.settings.set_setting(['performance', 'cache'], self.original_cache_settings)
        self.settings.save()
    
    def test_basic_operations(self):
        """Testa operações básicas do cache."""
        # Set e Get
        self.cache.set('key1', 'value1')
        self.assertEqual(self.cache.get('key1'), 'value1')
        
        # Delete
        self.cache.delete('key1')
        self.assertIsNone(self.cache.get('key1'))
    
    def test_max_size(self):
        """Testa limite de tamanho do cache."""
        # Adicionar itens além do limite
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.set('key3', 'value3')
        
        # Verificar que o item mais antigo foi removido
        self.assertIsNone(self.cache.get('key1'))
        self.assertIsNotNone(self.cache.get('key2'))
        self.assertIsNotNone(self.cache.get('key3'))
    
    def test_ttl(self):
        """Testa tempo de vida do cache."""
        import time
        
        # Adicionar item com TTL curto
        self.cache.set('key1', 'value1', ttl=1)
        self.assertEqual(self.cache.get('key1'), 'value1')
        
        # Esperar expirar
        time.sleep(1.1)
        self.assertIsNone(self.cache.get('key1'))

class TestCacheFactory(unittest.TestCase):
    """Testes para a fábrica de cache."""
    
    def setUp(self):
        """Configuração inicial dos testes."""
        self.settings = DynamicSettings()
        self.original_cache_settings = self.settings.get_setting(['performance', 'cache'], {})
    
    def tearDown(self):
        """Limpeza após os testes."""
        self.settings.set_setting(['performance', 'cache'], self.original_cache_settings)
        self.settings.save()
    
    def test_memory_cache_creation(self):
        """Testa criação de cache em memória."""
        # Configurar cache em memória
        cache_settings = {
            'type': 'memory',
            'default_ttl': 3600,
            'memory': {
                'max_size': 1000
            }
        }
        self.settings.set_setting(['performance', 'cache'], cache_settings)
        self.settings.save()
        
        # Criar cache
        cache = CacheFactory.create()
        self.assertIsInstance(cache, MemoryCache)
    
    def test_redis_cache_creation(self):
        """Testa criação de cache Redis."""
        # Configurar Redis
        cache_settings = {
            'type': 'redis',
            'default_ttl': 3600,
            'redis': {
                'enabled': True,
                'host': 'localhost',
                'port': 6379,
                'db': 0
            }
        }
        self.settings.set_setting(['performance', 'cache'], cache_settings)
        self.settings.save()
        
        try:
            # Tentar criar cache Redis
            cache = CacheFactory.create()
            
            # Se Redis estiver disponível
            if isinstance(cache, RedisCache):
                # Testar operações básicas
                cache.set('test_key', 'test_value')
                self.assertEqual(cache.get('test_key'), 'test_value')
                cache.delete('test_key')
                
                # Fechar conexão
                cache.close()
            else:
                # Se Redis não estiver disponível, deve usar fallback
                self.assertIsInstance(cache, MemoryCache)
                logger.warning("Redis não disponível, usando cache em memória")
        except Exception as e:
            logger.error(f"Erro ao testar Redis: {e}")
            self.skipTest("Redis não disponível")

if __name__ == '__main__':
    unittest.main() 