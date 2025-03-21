#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para executar o teste de conexão MySQL.
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/mysql_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cria diretório de logs se não existir
os.makedirs('logs', exist_ok=True)

def run_tests():
    """Executa os testes de conexão MySQL."""
    from tests.test_mysql_connection import TestMySQLConnection
    from tests.test_redis_adapter import TestRedisAdapter, TestCacheFactory, TestNullCache
    
    # Criar suite de testes
    suite = unittest.TestSuite()
    
    # Adicionar testes de conexão MySQL
    suite.addTest(unittest.makeSuite(TestMySQLConnection))
    
    # Adicionar testes de cache
    suite.addTest(unittest.makeSuite(TestCacheFactory))
    suite.addTest(unittest.makeSuite(TestNullCache))
    
    # Adicionar testes de Redis se disponível
    try:
        from app.data.cache.redis_adapter import RedisAdapter
        suite.addTest(unittest.makeSuite(TestRedisAdapter))
        logger.info("Testes de Redis incluídos")
    except ImportError:
        logger.warning("Redis não disponível, testes de Redis serão ignorados")
    
    # Executar testes
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Retornar resultado
    return result.wasSuccessful()

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("INICIANDO TESTES DE CONEXÃO MYSQL")
    logger.info("="*50)
    
    success = run_tests()
    
    logger.info("="*50)
    logger.info(f"TESTES {'CONCLUÍDOS COM SUCESSO' if success else 'FALHARAM'}")
    logger.info("="*50)
    
    # Sair com código de erro se os testes falharem
    sys.exit(0 if success else 1) 