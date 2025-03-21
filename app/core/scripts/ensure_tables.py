#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar se todas as tabelas necessárias existem no banco de dados MySQL.
Útil para diagnóstico e verificação de integridade do banco.
"""

import argparse
import logging
import sys
from pathlib import Path
import mysql.connector
from mysql.connector import Error

# Adiciona o diretório raiz ao path para importar módulos do projeto
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from app.data.connection import get_db_connection
from app.config.settings import DATABASE

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Tabelas necessárias para o funcionamento do sistema
REQUIRED_TABLES = [
    'users',
    'products',
    'customers',
    'orders',
    'inventory',
    'sync_metadata',
    'sync_log',
    'sync_conflicts',
    'migrations'
]

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Verifica se as tabelas necessárias existem no banco MySQL.'
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Exibe informações detalhadas')
    
    return parser.parse_args()

def check_mysql_tables():
    """Verifica se as tabelas necessárias existem no banco MySQL."""
    logger.info("Verificando tabelas no MySQL...")
    
    try:
        # Obtém conexão com o banco MySQL
        db_conn = get_db_connection()
        
        # Verifica tabelas existentes
        result = db_conn.execute_query("SHOW TABLES")
        existing_tables = [row[f'Tables_in_{DATABASE["mysql"]["local"]["database"]}'] for row in result]
        
        logger.info(f"Tabelas existentes no MySQL: {existing_tables}")
        
        # Verifica tabelas faltantes
        missing_tables = []
        for table in REQUIRED_TABLES:
            if table not in existing_tables:
                missing_tables.append(table)
                logger.warning(f"Tabela {table} não encontrada no MySQL")
        
        if missing_tables:
            logger.error(f"Tabelas faltando no MySQL: {missing_tables}")
            return missing_tables
        
        logger.info("Todas as tabelas necessárias existem no MySQL.")
        return []
        
    except Exception as e:
        logger.error(f"Erro ao verificar tabelas MySQL: {e}")
        return REQUIRED_TABLES  # Assume que todas estão faltando em caso de erro

def check_table_columns(table_name):
    """Verifica se a tabela possui todas as colunas necessárias."""
    # Esta função pode ser expandida para verificar colunas específicas
    # por enquanto, apenas verifica se a tabela existe
    return []

def main():
    """Função principal."""
    args = parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Verifica tabelas no MySQL
        missing_tables_mysql = check_mysql_tables()
        
        # Exibe resultado final
        if missing_tables_mysql:
            logger.error("Há tabelas faltando no banco de dados.")
            logger.error("Execute o script de criação de tabelas para corrigir o problema.")
            return 1
        else:
            logger.info("Todos os bancos de dados estão com as tabelas necessárias.")
            return 0
            
    except Exception as e:
        logger.error(f"Erro ao verificar tabelas: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 